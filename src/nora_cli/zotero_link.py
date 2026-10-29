"""Project-local Zotero links: preview-first import and three-way metadata sync."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from . import papers as ps
from . import zotero as z
from .zotero_audit import display, read_state


def add_parser(sub):
    parser = sub.add_parser("zotero", help="link project papers to Zotero and sync metadata")
    commands = parser.add_subparsers(dest="zotero_command")
    for command in ("import", "sync"):
        child = commands.add_parser(command, help="preview changes; --apply writes local project state")
        child.add_argument("--config")
        child.add_argument("--env-file")
        child.add_argument("--data-dir")
        child.add_argument("--offline", action="store_true", help="use the saved full Zotero audit snapshot")
        child.add_argument("--apply", action="store_true", help="apply local metadata/link changes after previewing")
        child.add_argument("--prefer-zotero", action="store_true", help="explicitly resolve conflicting metadata fields in favor of Zotero")
        if command == "import":
            select = child.add_mutually_exclusive_group(required=True)
            select.add_argument("--item", action="append", metavar="KEY", help="Zotero item key; repeatable")
            select.add_argument("--collection", metavar="KEY", help="collection key, direct members by default")
            child.add_argument("--recursive", action="store_true", help="include descendant collections")
            child.add_argument("--match", action="append", default=[], metavar="KEY=LOCAL_ID",
                               help="explicitly choose an existing project paper for an ambiguous item")
            child.add_argument("--new", action="append", default=[], metavar="KEY",
                               help="explicitly treat a selected item as distinct from its local match candidates")
        else:
            child.add_argument("--id", action="append", help="restrict to linked local IDs; default: all links in configured library")


def metadata(item: dict) -> dict:
    data = item["data"]
    clean = lambda s: " ".join(s.split()) if s else None
    title = clean(data.get("title"))
    if not title:
        raise z.ZoteroError(f"Item {item['key']} has no title; fix it in Zotero before importing.")
    authors = []
    for creator in data.get("creators", []):
        if creator.get("creatorType") != "author":
            continue
        name = creator.get("name") or ", ".join(filter(None, [creator.get("lastName"), creator.get("firstName")]))
        if clean(name):
            authors.append(clean(name))
    date = re.search(r"\b([12][0-9]{3})\b", data.get("date", ""))
    doi = ps.normalize_doi(data.get("DOI", "")) or None
    url = clean(data.get("url"))
    arxiv = None
    for value in [doi or "", url or ""]:
        match = re.search(r"(?:10\.48550/arxiv\.|arxiv\.org/(?:abs|pdf)/)([a-z-]+(?:\.[A-Z]{2})?/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?", value, re.I)
        if match:
            arxiv = match[1]
            break
    return dict(title=title, authors=authors, year=int(date[1]) if date else None,
                venue=clean(data.get("publicationTitle") or data.get("proceedingsTitle")),
                doi=doi, arxiv=arxiv, url=url)


def _arxiv(value):
    return re.sub(r"v\d+$", "", value or "", flags=re.I).casefold()


def _candidates(papers, fields):
    """Return every plausible exact match; contradictions require human choice."""
    strong, titles = [], []
    for paper in papers:
        same_doi = fields["doi"] and paper["doi"] and ps.normalize_doi(paper["doi"]) == fields["doi"]
        same_arxiv = fields["arxiv"] and paper["arxiv"] and _arxiv(paper["arxiv"]) == _arxiv(fields["arxiv"])
        same_title = ps.normalize_title(paper["title"]) == ps.normalize_title(fields["title"])
        if same_doi or same_arxiv:
            strong.append(paper)
        elif same_title:
            titles.append(paper)
    # Don't silently discard a title match to a second local record in favor of DOI.
    return strong + titles


def _identifier_conflict(paper, fields):
    for name, normalize in [("doi", ps.normalize_doi), ("arxiv", _arxiv)]:
        if paper[name] and fields[name] and normalize(paper[name]) != normalize(fields[name]):
            return True
    return False


def _update(paper, item, library, prefer_remote):
    remote = metadata(item)
    link = ps.zotero_link(paper)
    old_link = paper.get("zotero")
    changes, conflicts = {}, []
    if link:
        if item["version"] < link["version"]:
            return {}, [f"{paper['id']}: incoming Zotero version is older than the linked version"], False
        if item["version"] == link["version"] and remote != link["baseline"]:
            return {}, [f"{paper['id']}: metadata changed without a Zotero version change"], False
    for name in ps.METADATA_FIELDS:
        current, incoming = paper[name], remote[name]
        if link:
            baseline = link["baseline"][name]
            if current != baseline and incoming != baseline and current != incoming:
                if not prefer_remote:
                    conflicts.append(f"{paper['id']}.{name}: local={current!r}; previous Zotero={baseline!r}; new Zotero={incoming!r}")
                    continue
            elif incoming == baseline:
                # Keep local-only edits, even when Zotero changed an unrelated field.
                continue
        elif incoming in (None, [], ""):
            # First linking must not erase metadata absent in Zotero.
            continue
        if current != incoming:
            changes[name] = (current, incoming)
    if conflicts:
        return changes, conflicts, False
    for name, (_, value) in changes.items():
        paper[name] = value
    paper["zotero"] = json.dumps({"library": library, "key": item["key"], "version": item["version"],
                                  "baseline": remote}, ensure_ascii=False, sort_keys=True)
    return changes, [], old_link != paper["zotero"]


def _selection(snapshot, args):
    all_items = {i["key"]: i for i in snapshot["items"]}
    bibliographic = {k: i for k, i in all_items.items() if i["data"].get("itemType") not in {"note", "annotation", "attachment"}}
    if args.item:
        keys = sorted(set(args.item))
        for key in keys:
            if key not in bibliographic:
                raise z.ZoteroError(f"Selected item {display(key)} is missing or is not a bibliographic item.")
        return [bibliographic[k] for k in keys]
    collections = {c["key"]: c for c in snapshot["collections"]}
    if args.collection not in collections:
        raise z.ZoteroError("Selected collection key does not exist in this snapshot.")
    keys = {args.collection}
    if args.recursive:
        while True:
            descendants = {k for k, c in collections.items() if c["data"].get("parentCollection") in keys}
            if descendants <= keys:
                break
            keys |= descendants
    return [i for _, i in sorted(bibliographic.items()) if keys.intersection(i["data"].get("collections", []))]


def plan(papers: list, snapshot: dict, args) -> tuple[list, list, list]:
    from .literature import _add_paper, _today
    result = copy.deepcopy(papers)
    if len({p["id"] for p in papers}) != len(papers):
        raise z.ZoteroError("Duplicate local paper IDs; resolve before linking Zotero items.")
    ps.validate_links(result)
    library = snapshot["library"]
    messages, blocked = [], []
    by_id = {p["id"]: p for p in result}
    links = {(l["library"], l["key"]): p for p in result if (l := ps.zotero_link(p))}
    if args.zotero_command == "sync":
        requested = set(args.id or [])
        if requested - set(by_id):
            raise z.ZoteroError("Some --id values do not exist in this project.")
        selected = [p for p in result if (not requested or p["id"] in requested)
                    and ps.zotero_link(p) and ps.zotero_link(p)["library"] == library]
        if requested != {p["id"] for p in selected} and requested:
            raise z.ZoteroError("Every selected ID must be linked to the configured Zotero library.")
        remote = {i["key"]: i for i in snapshot["items"] if i["data"].get("itemType") not in {"note", "annotation", "attachment"}}
        pairs = []
        for paper in selected:
            key = ps.zotero_link(paper)["key"]
            if key not in remote:
                blocked.append(f"{paper['id']}: Zotero item {key} is absent; local paper retained (possibly deleted/merged remotely)")
            else:
                pairs.append((paper, remote[key], "sync"))
    else:
        selected = _selection(snapshot, args)
        selected_keys = {i["key"] for i in selected}
        mappings = {}
        for spec in args.match:
            key, sep, local_id = spec.partition("=")
            if not sep or key not in selected_keys or local_id not in by_id or key in mappings:
                raise z.ZoteroError("Each --match must uniquely map a selected KEY to an existing LOCAL_ID.")
            mappings[key] = local_id
        force_new = set(args.new)
        if force_new - selected_keys or force_new.intersection(mappings):
            raise z.ZoteroError("--new must refer to selected items and cannot overlap --match.")
        pairs = []
        for item in selected:
            key = item["key"]
            fields = metadata(item)
            linked = links.get((library, key))
            if linked:
                if key in force_new:
                    blocked.append(f"{key}: already linked to {linked['id']}; --new cannot duplicate that identity")
                    continue
                if key in mappings and mappings[key] != linked["id"]:
                    blocked.append(f"{key}: already linked to {linked['id']}; cannot reassign")
                    continue
                paper = linked
                action = "sync"
            else:
                candidates = _candidates(result, fields)
                if key in force_new:
                    paper = _add_paper(result, fields, "zotero")
                    by_id[paper["id"]] = paper
                elif key in mappings:
                    paper = by_id[mappings[key]]
                elif len(candidates) == 1 and not _identifier_conflict(candidates[0], fields):
                    paper = candidates[0]
                elif candidates:
                    choices = ", ".join(f"{p['id']} ({p['title']})" for p in candidates)
                    blocked.append(f"{key}: ambiguous/conflicting identity; candidates: {choices}. Choose --match {key}=LOCAL_ID")
                    continue
                else:
                    paper = _add_paper(result, fields, "zotero")
                    by_id[paper["id"]] = paper
                old = ps.zotero_link(paper)
                # Also check pending pairs: a batch must not bind two remote items to one local ID.
                if old or any(p["id"] == paper["id"] for p, _, _ in pairs):
                    blocked.append(f"{key}: candidate {paper['id']} is already linked or selected for another Zotero item; review duplicates")
                    continue
                action = "link" if any(p["id"] == paper["id"] for p in papers) else "add"
            pairs.append((paper, item, action))
            links[(library, key)] = paper
    for paper, item, action in pairs:
        changes, conflicts, link_changed = _update(paper, item, library, args.prefer_zotero)
        blocked.extend(conflicts)
        if not conflicts and (changes or link_changed):
            paper["updated"] = _today()
        status = action if changes or link_changed else "unchanged"
        messages.append(f"{status}: {item['key']} -> {paper['id']} [Zotero version {item['version']}] {paper['title']}")
        for name, (before, after) in changes.items():
            messages.append(f"  {name}: {before!r} -> {after!r}")
        if action == "add":
            messages.append("  New project entry: candidate; no roles, notes, or research decision assigned.")
    return result, messages, blocked


def run(base: Path, args) -> int:
    if not args.zotero_command:
        print("Use: nora lit zotero import --item KEY | --collection KEY; or nora lit zotero sync")
        return 0
    try:
        path = ps.papers_path(base)
        if not path.is_file():
            raise z.ZoteroError("Literature module not initialized; initialize it explicitly before linking. No workspace was created.")
        original = path.read_text()
        papers = ps.parse(original)
        if args.zotero_command == "import" and args.recursive and not args.collection:
            raise z.ZoteroError("--recursive requires --collection.")
        config = z.load_config(args.config, args.env_file, args.data_dir)
        snapshot = read_state(config)["snapshot"] if args.offline else z.Client(config).snapshot()
        if snapshot is None:
            raise z.ZoteroError("No saved Zotero snapshot. Run nora zotero audit --write first, or omit --offline.")
        updated, messages, blocked = plan(papers, snapshot, args)
        print(f"Zotero {config.identity}; library version {snapshot['version']}; snapshot {snapshot['fetched_at']}")
        if args.offline:
            print("Using saved metadata; newer remote changes are not checked.")
        for message in messages:
            print(display(message))
        for problem in blocked:
            print("BLOCKED: " + display(problem))
        if blocked:
            print("Nothing applied. Resolve the reported identities/metadata conflicts and rerun preview.")
            return 1
        if not args.apply:
            print("Preview only; no local or remote state written. Use --apply to save project links/metadata.")
            return 0
        if updated == papers:
            print("No changes; project state is already current.")
            return 0
        ps.save(base, updated, expected_text=original, backup=True)
        print("Applied project links/metadata; backup saved under .nora/literature/backups/.")
        print("Existing IDs, roles, statuses, notes, and decisions preserved. Zotero unchanged.")
        from .literature import cmd_render
        cmd_render(base)
        return 0
    except (z.ZoteroError, ps.PapersError) as exc:
        print(f"ERROR: {exc}")
        return 1
    except OSError:
        print("ERROR: local file access failed. If state was saved before rendering failed, run nora lit render.")
        return 1
