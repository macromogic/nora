"""Deterministic library audit and atomic, machine-scoped review bookkeeping.

Review lifecycle adapted from Robo: detection and the user's disposition are
separate, so disappearance/reappearance never silently undoes an ignore.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .papers import normalize_doi, normalize_title
from .zotero import Config, ZoteroError, validate_objects


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def display(value) -> str:
    """Keep untrusted library strings on one line, without terminal controls/HTML."""
    text = " ".join(str(value).split())
    text = "".join(c for c in text if not unicodedata.category(c).startswith("C"))
    return text.replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _issue(library: str, kind: str, keys: list[str], summary: str, evidence: dict) -> dict:
    keys = sorted(keys)
    return {"issue_key": f"{library}:{kind}:{_digest(keys)[:16]}", "kind": kind,
            "item_keys": keys, "summary": summary, "evidence": evidence,
            "fingerprint": _digest(evidence)}


def collection_paths(collections: list) -> tuple[dict, list]:
    by_key = {c["key"]: c["data"] for c in collections}
    paths, warnings = {}, []
    # Iterative traversal avoids recursion limits on malformed/deep collection trees.
    for key in by_key:
        chain, seen = [], set()
        cursor = key
        while cursor and cursor not in paths:
            if cursor in seen or cursor not in by_key:
                warnings.append({"key": key, "reason": "cycle or missing parent"})
                break
            seen.add(cursor)
            chain.append(cursor)
            cursor = by_key[cursor].get("parentCollection") or None
        prefix = paths.get(cursor, "[unresolved]" if cursor else "")
        for part in reversed(chain):
            name = by_key[part].get("name") or part
            prefix = f"{prefix}/{name}" if prefix else name
            paths[part] = prefix
    return paths, warnings


def _local_attachment(data: dict, key: str, config: Config) -> str:
    """Return availability, never open files or store machine paths in reports."""
    mode = data.get("linkMode")
    if mode == "linked_file":
        raw = data.get("path", "")
        if raw.startswith("attachments:"):
            if config.pdf_dir is None:
                return "linked_root_unconfigured"
            root = config.pdf_dir.resolve()
            path = (root / raw[len("attachments:"):]).resolve()
            if root not in path.parents:
                return "unsafe_path"
        else:
            path = Path(raw)
            if not path.is_absolute():
                return "unresolved_linked_path"
    elif mode in {"imported_file", "imported_url"}:
        if config.storage_dir is None:
            return "stored_file_not_checked"
        filename = data.get("filename", "")
        if not filename or Path(filename).name != filename or filename in {".", ".."}:
            return "unsafe_path"
        root = config.storage_dir.resolve()
        path = (root / key / filename).resolve()
        if root not in path.parents:
            return "unsafe_path"
    else:
        return "remote_link_or_unknown"
    try:
        return "local_file_present" if path.is_file() else "local_file_missing"
    except OSError:
        return "local_file_unreadable"


def analyze(snapshot: dict, config: Config) -> dict:
    if snapshot.get("library") != config.identity:
        raise ZoteroError("Snapshot belongs to a different library.")
    items = snapshot["items"]
    bibliographic = [i for i in items if i["data"].get("itemType") not in {"attachment", "note", "annotation"}]
    attachments = [i for i in items if i["data"].get("itemType") == "attachment"]
    paths, path_warnings = collection_paths(snapshot["collections"])
    issues, collections, tags, tag_types = [], Counter(), Counter(), Counter()
    modes, availability, kinds, completeness = Counter(), Counter(), Counter(), Counter()
    doi_groups, title_groups, tag_variants = defaultdict(list), defaultdict(list), defaultdict(set)
    attached_pdfs = defaultdict(list)
    paper_keys = {i["key"] for i in bibliographic}
    attachment_keys = {i["key"] for i in attachments}
    for attachment in attachments:
        data, key = attachment["data"], attachment["key"]
        modes[data.get("linkMode") or "unknown"] += 1
        parent = data.get("parentItem")
        if not parent:
            issues.append(_issue(config.identity, "unparented_attachment", [key],
                                 "Attachment has no parent bibliographic item (may be intentional).",
                                 {"title": data.get("title", ""), "content_type": data.get("contentType", "")}))
        elif parent not in paper_keys:
            issues.append(_issue(config.identity, "missing_attachment_parent", [key],
                                 "Attachment's parent was not found in the full snapshot.", {"parent": parent}))
        if data.get("contentType", "").lower() != "application/pdf":
            continue
        if parent:
            attached_pdfs[parent].append(key)
        status = _local_attachment(data, key, config)
        availability[status] += 1
        if status in {"local_file_missing", "local_file_unreadable", "unsafe_path", "unresolved_linked_path"}:
            issues.append(_issue(config.identity, "pdf_local_access", [key],
                                 "PDF local access needs review; remote availability is unknown.",
                                 {"status": status, "parent": parent, "link_mode": data.get("linkMode")}))

    research_types = {"journalArticle", "conferencePaper", "preprint", "thesis", "report", "manuscript", "book", "bookSection"}
    for item in bibliographic:
        data, key = item["data"], item["key"]
        title = data.get("title", "").strip()
        item_type = data.get("itemType", "unknown")
        kinds[item_type] += 1
        authors = [c.get("name") or " ".join(filter(None, [c.get("firstName"), c.get("lastName")]))
                   for c in data.get("creators", []) if c.get("creatorType") == "author"]
        missing = []
        if not title:
            missing.append("title")
        if item_type in research_types:
            if not any(authors):
                missing.append("author")
            if not data.get("date", "").strip():
                missing.append("date")
        if missing:
            issues.append(_issue(config.identity, "missing_metadata", [key],
                                 "Metadata fields need review (some item types may legitimately omit them).",
                                 {"title": title, "item_type": item_type, "missing": missing}))
        for name, field in [("without_doi", "DOI"), ("without_abstract", "abstractNote"), ("without_date", "date")]:
            if not data.get(field, "").strip():
                completeness[name] += 1
        cols = data.get("collections", [])
        if not cols:
            issues.append(_issue(config.identity, "unfiled", [key], "Item has no collection.", {"title": title}))
        for col in set(cols):
            collections[col] += 1
            if col not in paths:
                issues.append(_issue(config.identity, "unknown_collection", [key, col],
                                     "Item references a missing collection.", {"collection_key": col, "title": title}))
        tag_names = set()
        for tag in data.get("tags", []):
            name = tag.get("tag", "")
            tag_names.add(name)
            tag_types["automatic" if tag.get("type") == 1 else "manual"] += 1
            normalized = " ".join(unicodedata.normalize("NFKC", name).casefold().split())
            tag_variants[normalized].add(name)
        tags.update(tag_names)
        doi = normalize_doi(data.get("DOI", ""))
        if doi:
            doi_groups[doi].append(key)
        norm_title = normalize_title(title)
        if len(norm_title) >= 12:
            title_groups[norm_title].append(key)
        if key not in attached_pdfs and item_type in research_types:
            issues.append(_issue(config.identity, "no_pdf_attachment", [key],
                                 "No PDF attachment metadata found; full text may exist elsewhere.", {"title": title}))
    for kind, groups in [("duplicate_doi", doi_groups), ("duplicate_title", title_groups)]:
        for value, keys in sorted(groups.items()):
            if len(keys) > 1:
                issues.append(_issue(config.identity, kind, keys, "Possible duplicate items; review editions/versions before merging.",
                                     {"match": value, "item_keys": sorted(keys)}))
    for normalized, variants in sorted(tag_variants.items()):
        if len(variants) > 1 or not normalized:
            issues.append(_issue(config.identity, "tag_variant", [normalized],
                                 "Tags differ only in case, spacing, or Unicode normalization, or are empty.",
                                 {"tags": sorted(variants)}))
    for warning in path_warnings:
        issues.append(_issue(config.identity, "collection_structure", [warning["key"]],
                             "Collection hierarchy could not be fully resolved.", warning))
    return {"issues": sorted(issues, key=lambda i: i["issue_key"]), "bibliographic_items": len(bibliographic),
            "attachments": len(attachment_keys), "pdf_attachments": sum(availability.values()),
            "collections": [{"key": k, "path": paths[k], "items": collections[k]} for k in sorted(paths)],
            "tags": dict(tags), "tag_assignments": dict(tag_types), "item_types": dict(kinds),
            "attachment_modes": dict(modes), "pdf_local_status": dict(availability), "completeness": dict(completeness)}


def issue_status(issue: dict) -> str:
    return issue["disposition"] if issue["detected"] else "cleared"


def reconcile(previous: list, findings: list, observed_at: str) -> list:
    old = {i["issue_key"]: dict(i) for i in previous}
    for issue in old.values():
        issue["detected"] = False
    for finding in findings:
        existing = old.get(finding["issue_key"], {})
        merged = dict(existing, **finding)
        merged.update(detected=True, first_seen=existing.get("first_seen", observed_at), last_seen=observed_at,
                      disposition=existing.get("disposition", "open"))
        reviewed = existing.get("reviewed_fingerprint")
        merged["evidence_changed"] = bool(reviewed and reviewed != finding["fingerprint"])
        old[finding["issue_key"]] = merged
    return sorted(old.values(), key=lambda i: i["issue_key"])


def read_state(config: Config) -> dict:
    path = config.state_dir / "state.json"
    if not path.exists():
        return {"schema_version": 1, "library": config.identity, "snapshot": None, "issues": []}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if state["schema_version"] != 1 or state["library"] != config.identity:
            raise ValueError()
        snapshot = state["snapshot"]
        if (snapshot["schema_version"] != 1 or snapshot["library"] != config.identity
                or type(snapshot["version"]) is not int or snapshot["version"] < 0
                or not isinstance(snapshot["fetched_at"], str) or not isinstance(state["issues"], list)):
            raise ValueError()
        validate_objects(snapshot["items"], "items")
        validate_objects(snapshot["collections"], "collections")
        seen = set()
        for issue in state["issues"]:
            if (not isinstance(issue["issue_key"], str) or not issue["issue_key"].startswith(config.identity + ":")
                    or issue["issue_key"] in seen or issue["disposition"] not in {"open", "ignored", "resolved"}
                    or not isinstance(issue["detected"], bool) or not isinstance(issue["evidence"], dict)
                    or not all(isinstance(issue[k], str) for k in ("fingerprint", "summary", "kind", "first_seen", "last_seen"))):
                raise ValueError()
            seen.add(issue["issue_key"])
        return state
    except (ValueError, KeyError, TypeError, ZoteroError):
        raise ZoteroError("Invalid or incompatible local audit state; preserved without overwriting.") from None


@contextmanager
def _locked(config: Config):
    config.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = config.state_dir / ".write.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ZoteroError("Local audit is locked by another writer. If a writer crashed, inspect .write.lock before removing it.") from None
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def _atomic(path: Path, text: str):
    fd, temporary = tempfile.mkstemp(prefix=".nora-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _save(config: Config, state: dict):
    _atomic(config.state_dir / "state.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def save_audit(config: Config, snapshot: dict, findings: list) -> list:
    with _locked(config):
        current = read_state(config)
        old_snapshot = current["snapshot"]
        if old_snapshot and old_snapshot["version"] > snapshot["version"]:
            raise ZoteroError("A newer snapshot was saved concurrently; retry. Existing state preserved.")
        issues = reconcile(current["issues"], findings, snapshot["fetched_at"])
        _save(config, {"schema_version": 1, "library": config.identity, "snapshot": snapshot, "issues": issues})
    return issues


def mark(config: Config, key: str, status: str, note: str):
    if status not in {"open", "ignored", "resolved"}:
        raise ZoteroError("Invalid review disposition.")
    # Do not create state for a mistyped review operation.
    if not (config.state_dir / "state.json").is_file():
        raise ZoteroError("No saved audit; run audit --write first.")
    with _locked(config):
        state = read_state(config)
        for issue in state["issues"]:
            if issue["issue_key"] == key:
                issue.update(disposition=status, review_note=note, reviewed_at=now(),
                             reviewed_fingerprint=issue["fingerprint"], evidence_changed=False)
                _save(config, state)
                return
        raise ZoteroError("Review issue not found in this library.")


def write_report(config: Config, report: str):
    # A generated view; state.json remains the sole authoritative artifact.
    with _locked(config):
        _atomic(config.state_dir / "AUDIT_REPORT.md", report + "\n")


def render(snapshot: dict, result: dict, issues: list, limit=20, offline=False) -> str:
    active = [i for i in issues if i["detected"]]
    by_kind = Counter(i["kind"] for i in active)
    by_disposition = Counter(i["disposition"] for i in active)
    lines = ["# Zotero library audit", "", f"Library: {snapshot['library']}; version: {snapshot['version']}; "
             f"snapshot: {snapshot['fetched_at']}",
             "Mode: saved snapshot (remote metadata may be stale)." if offline else "Mode: full online snapshot.",
             "Local PDF availability is checked on this machine at report time; remote file availability is not verified.", "",
             f"Bibliographic items: {result['bibliographic_items']}; attachments: {result['attachments']}; "
             f"PDF attachments: {result['pdf_attachments']}; collections: {len(result['collections'])}; tags: {len(result['tags'])}.",
             "All untrashed items, including unfiled and _inbox items, are included. Notes/annotations are excluded from saved content.",
             "Findings are review candidates, not instructions to merge, retag, or change research status.", ""]
    for title, counts in [("Item types", result["item_types"]), ("Metadata coverage (absence can be legitimate)", result["completeness"]),
                          ("Tag assignments", result["tag_assignments"]), ("Attachment modes", result["attachment_modes"]),
                          ("PDF local status", result["pdf_local_status"]), ("Detected findings", by_kind),
                          ("User dispositions for detected findings", by_disposition)]:
        lines += [f"## {title}", ""]
        lines += [f"- {display(k)}: {v}" for k, v in sorted(counts.items())] or ["- none"]
        lines += [""]

    def bounded(entries):
        return entries[:limit] if limit else entries

    def omitted(total):
        if limit and total > limit:
            lines.append(f"- … {total - limit} more; use --limit 0 for the complete report.")

    lines += ["## Collections (direct memberships; children are not rolled up)", ""]
    cols = sorted(result["collections"], key=lambda c: (-c["items"], c["path"], c["key"]))
    lines += [f"- {display(c['path'])} [{c['key']}]: {c['items']}" for c in bounded(cols)] or ["- none"]
    omitted(len(cols))
    lines += ["", "## Tags (number of bibliographic items)", ""]
    tag_counts = sorted(result["tags"].items(), key=lambda kv: (-kv[1], kv[0]))
    lines += [f"- {display(k)}: {v}" for k, v in bounded(tag_counts)] or ["- none"]
    omitted(len(tag_counts))
    lines += ["", "## Finding details", ""]
    # Human-actionable structural issues first, then ordinary incompleteness.
    ranked = sorted(active, key=lambda i: (i["kind"] in {"no_pdf_attachment", "missing_metadata", "unfiled"}, i["issue_key"]))
    for issue in bounded(ranked):
        changed = "; evidence changed since review" if issue.get("evidence_changed") else ""
        lines += [f"- {issue['issue_key']} [{issue['disposition']}{changed}]: {display(issue['summary'])}",
                  f"  Evidence: {display(json.dumps(issue['evidence'], ensure_ascii=False, sort_keys=True))}"]
    if not ranked:
        lines.append("- none")
    omitted(len(ranked))
    lines += ["", "Review dispositions are local. Ignored/resolved choices persist across audits; detection is tracked separately.",
              "A saved AUDIT_REPORT.md is a point-in-time view; rerun audit --offline after marking a review issue."]
    return "\n".join(lines)
