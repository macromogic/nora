"""Read-only Zotero Web API v3 client and machine-scoped CLI.

No project initialization, implicit dotenv loading, or remote write methods.
Credentials stay in memory; saved state contains only normalized library data.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path


class ZoteroError(Exception):
    """An actionable, credential-free error safe to print."""


ENV_FIELDS = {
    "ZOTERO_LIBRARY_ID": "library_id",
    "ZOTERO_LIBRARY_TYPE": "library_type",
    "ZOTERO_PDF_DIR": "pdf_dir",
    "ZOTERO_STORAGE_DIR": "storage_dir",
}
CONFIG_FIELDS = set(ENV_FIELDS.values()) | {"data_dir"}


@dataclass
class Config:
    library_id: str
    library_type: str = "user"
    api_key: str = field(default="", repr=False)
    key_source: str = "none (public access)"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".local/share/nora/zotero")
    pdf_dir: Path | None = None
    storage_dir: Path | None = None

    @property
    def identity(self) -> str:
        return f"{self.library_type}:{self.library_id}"

    @property
    def state_dir(self) -> Path:
        return self.data_dir / f"{self.library_type}-{self.library_id}"


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ZoteroError("Cannot read JSON configuration; check the file and JSON syntax.") from None
    if not isinstance(value, dict) or set(value) - CONFIG_FIELDS:
        raise ZoteroError("Config must be an object containing only library_id, library_type, "
                          "data_dir, pdf_dir, storage_dir. Keep API keys in the environment or an explicit env file.")
    if any(not isinstance(v, str) for v in value.values()):
        raise ZoteroError("All configuration values must be strings (including library_id).")
    return value


def _env_file(path: Path) -> dict:
    """Read only supported literal assignments; never source or interpolate a file."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise ZoteroError("Cannot read the explicit env file.") from None
    result = {}
    for number, line in enumerate(lines, 1):
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)$", line)
        if not match or match[1] not in set(ENV_FIELDS) | {"ZOTERO_API_KEY"}:
            continue
        name, value = match.groups()
        value = value.strip()
        if value.startswith(("'", '"')):
            quote = value[0]
            end = value.find(quote, 1)
            if end < 0 or (value[end + 1:].strip() and not value[end + 1:].lstrip().startswith("#")):
                raise ZoteroError(f"Invalid literal Zotero assignment at env-file line {number}.")
            value = value[1:end]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        # Robo uses $HOME for its linked-PDF root. Support only this literal
        # prefix on path fields; do not evaluate arbitrary shell expressions.
        if name in {"ZOTERO_PDF_DIR", "ZOTERO_STORAGE_DIR"}:
            value = re.sub(r"^\$(?:HOME|\{HOME\})(?=/|$)", lambda _: str(Path.home()), value)
        if "$" in value or "`" in value or "\x00" in value:
            raise ZoteroError(f"Use literal Zotero values, without expansion, at env-file line {number}.")
        result[name] = value
    return result


def _absolute(value: str, name: str) -> Path:
    path = Path(value).expanduser()
    if not value or not path.is_absolute():
        raise ZoteroError(f"{name} must be an absolute path (or start with ~/).")
    return path


def load_config(config_file=None, env_file=None, data_dir=None) -> Config:
    default_config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "nora/zotero.json"
    path = Path(config_file).expanduser() if config_file else default_config
    values = _read_json(path) if config_file or path.exists() else {}
    dotenv = _env_file(Path(env_file).expanduser()) if env_file else {}
    for env, name in ENV_FIELDS.items():
        if env in dotenv:
            values[name] = dotenv[env]
        if env in os.environ:
            values[name] = os.environ[env]
    library_id = values.get("library_id", "")
    library_type = values.get("library_type", "user")
    if not re.fullmatch(r"[1-9][0-9]*", library_id):
        raise ZoteroError("Set ZOTERO_LIBRARY_ID or config library_id to a positive numeric user/group ID.")
    if library_type not in {"user", "group"}:
        raise ZoteroError("ZOTERO_LIBRARY_TYPE / library_type must be user or group.")
    api_key = os.environ.get("ZOTERO_API_KEY", dotenv.get("ZOTERO_API_KEY", ""))
    if api_key and not re.fullmatch(r"[A-Za-z0-9_-]+", api_key):
        raise ZoteroError("ZOTERO_API_KEY must be a literal key without whitespace or control characters.")
    source = "none (public access)"
    if api_key:
        source = "process environment" if "ZOTERO_API_KEY" in os.environ else "explicit env file"
    default_data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "nora/zotero"
    return Config(
        library_id, library_type, api_key, source,
        _absolute(str(data_dir or values.get("data_dir") or default_data), "data_dir"),
        _absolute(values["pdf_dir"], "pdf_dir") if values.get("pdf_dir") else None,
        _absolute(values["storage_dir"], "storage_dir") if values.get("storage_dir") else None,
    )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the API key to a redirect target.
        return None


def _get(url: str, api_key: str) -> tuple[list, dict]:
    headers = {"Zotero-API-Version": "3", "Accept": "application/json", "User-Agent": "nora-cli/zotero"}
    if api_key:
        headers["Zotero-API-Key"] = api_key
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=15) as response:
            body = response.read()
            response_headers = {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as exc:
        messages = {
            401: "Authentication failed; check the API key.",
            403: "Access denied; check the API key's read permission for this library.",
            404: "Library not found; check library type and numeric ID.",
            429: "Rate limited; retry later.",
            503: "Zotero is temporarily unavailable; retry later.",
        }
        message = messages.get(exc.code, "Request failed; no snapshot was accepted.")
        retry = exc.headers.get("Retry-After", "") if exc.headers else ""
        wait = f" Wait at least {retry} seconds." if re.fullmatch(r"[0-9]{1,8}", retry) else ""
        # Never print response bodies, exception URLs, or request headers.
        raise ZoteroError(f"Zotero HTTP {exc.code}: {message}{wait}") from None
    except (OSError, urllib.error.URLError, ValueError):
        raise ZoteroError("Zotero connection failed (network/TLS/timeout); retry later.") from None
    backoff = response_headers.get("backoff", "0")
    if backoff != "0":
        wait = f" for at least {backoff} seconds" if re.fullmatch(r"[0-9]{1,8}", backoff) else ""
        raise ZoteroError(f"Zotero requested backoff; stop and retry later{wait}. No snapshot accepted.")
    try:
        data = json.loads(body)
    except (ValueError, UnicodeError):
        raise ZoteroError("Zotero returned invalid JSON; no snapshot accepted.") from None
    if not isinstance(data, list):
        raise ZoteroError("Unexpected Zotero response shape; expected an array.")
    return data, response_headers


def _header_int(headers: dict, name: str) -> int:
    value = headers.get(name, "")
    if not re.fullmatch(r"[0-9]+", value):
        raise ZoteroError(f"Zotero response missing a valid {name} header; no snapshot accepted.")
    return int(value)


def validate_objects(records: list, resource: str):
    """Reject malformed API/cache data before it can clear previous findings."""
    if not isinstance(records, list):
        raise ZoteroError("Invalid Zotero objects; expected an array.")
    seen = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("data"), dict):
            raise ZoteroError("Invalid Zotero object shape.")
        key, version, data = record.get("key"), record.get("version"), record["data"]
        if (not isinstance(key, str) or not re.fullmatch(r"[A-Z0-9]{8}", key) or key in seen
                or type(version) is not int or version < 0):
            raise ZoteroError("Invalid Zotero object identity or version.")
        seen.add(key)
        strings = {"name"} if resource == "collections" else {
            "itemType", "title", "date", "DOI", "url", "publicationTitle", "proceedingsTitle",
            "abstractNote", "linkMode", "contentType", "path", "filename"}
        if any(k in data and not isinstance(data[k], str) for k in strings):
            raise ZoteroError("Invalid Zotero metadata field type.")
        for name in ("parentItem", "parentCollection"):
            value = data.get(name)
            if value and (not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9]{8}", value)):
                raise ZoteroError("Invalid Zotero parent reference.")
        if resource == "collections":
            continue
        if not data.get("itemType"):
            raise ZoteroError("Zotero item has no itemType.")
        for name in ("creators", "tags", "collections"):
            if not isinstance(data.get(name, []), list):
                raise ZoteroError("Invalid Zotero metadata list.")
        if any(not isinstance(k, str) or not re.fullmatch(r"[A-Z0-9]{8}", k) for k in data.get("collections", [])):
            raise ZoteroError("Invalid Zotero collection reference.")
        for creator in data.get("creators", []):
            if not isinstance(creator, dict) or any(not isinstance(v, str) for v in creator.values()):
                raise ZoteroError("Invalid Zotero creator record.")
        for tag in data.get("tags", []):
            if not isinstance(tag, dict) or not isinstance(tag.get("tag"), str):
                raise ZoteroError("Invalid Zotero tag record.")


class Client:
    def __init__(self, config: Config):
        self.config = config
        prefix = "users" if config.library_type == "user" else "groups"
        self.base = f"https://api.zotero.org/{prefix}/{config.library_id}"

    def page(self, resource: str, start=0, limit=100):
        if resource not in {"items", "collections"}:
            raise ZoteroError("Unsupported Zotero resource.")
        query = urllib.parse.urlencode({"format": "json", "limit": limit, "start": start,
                                       "sort": "dateAdded", "direction": "asc"})
        return _get(f"{self.base}/{resource}?{query}", self.config.api_key)

    def probe(self) -> tuple[int, int]:
        _, headers = self.page("items", limit=1)
        return _header_int(headers, "last-modified-version"), _header_int(headers, "total-results")

    def all(self, resource: str, expected_version=None) -> tuple[list, int]:
        result, seen = [], set()
        total = None
        for _ in range(10000):
            page, headers = self.page(resource, start=len(result))
            version = _header_int(headers, "last-modified-version")
            count = _header_int(headers, "total-results")
            if expected_version is None:
                expected_version = version
            if version != expected_version or (total is not None and total != count):
                raise ZoteroError("Library changed during download; retry for a consistent full snapshot.")
            total = count
            validate_objects(page, resource)
            for item in page:
                key = item.get("key", "")
                if key in seen or item["version"] > version:
                    raise ZoteroError("Invalid or repeated Zotero key during pagination; no snapshot accepted.")
                seen.add(key)
            result.extend(page)
            if len(result) == total:
                return result, expected_version
            if not page or len(result) > total:
                raise ZoteroError("Incomplete Zotero pagination; no snapshot accepted.")
        raise ZoteroError("Zotero pagination limit exceeded; no snapshot accepted.")

    def snapshot(self) -> dict:
        from .zotero_audit import now
        items, version = self.all("items")
        collections, _ = self.all("collections", version)
        # Whitelist library metadata. Never save note text, annotations, or credentials.
        item_fields = {"itemType", "title", "creators", "date", "DOI", "url", "publicationTitle",
                       "proceedingsTitle", "abstractNote", "tags", "collections", "parentItem",
                       "linkMode", "contentType", "path", "filename", "md5", "mtime"}
        kept = [{"key": i["key"], "version": i.get("version"),
                 "data": {k: v for k, v in i["data"].items() if k in item_fields}}
                for i in items if i["data"].get("itemType") not in {"note", "annotation"}]
        cols = [{"key": c["key"], "version": c.get("version"),
                 "data": {k: v for k, v in c["data"].items() if k in {"name", "parentCollection"}}}
                for c in collections]
        return {"schema_version": 1, "library": self.config.identity, "version": version,
                "fetched_at": now(), "total_api_items": len(items), "items": kept, "collections": cols}


def _parser():
    parser = argparse.ArgumentParser(prog="nora zotero", description=__doc__)
    parser.add_argument("--config", help="machine JSON config (default: $XDG_CONFIG_HOME/nora/zotero.json)")
    parser.add_argument("--env-file", help="explicit literal Zotero env file; never sourced or auto-discovered")
    parser.add_argument("--data-dir", help="persistent machine state root (absolute path)")
    sub = parser.add_subparsers(dest="command")
    doctor = sub.add_parser("doctor", help="check configuration and library read access")
    doctor.add_argument("--offline", action="store_true", help="configuration checks only")
    audit = sub.add_parser("audit", help="read all library metadata and report findings; remote is always read-only")
    audit.add_argument("--offline", action="store_true", help="use the last saved full snapshot")
    audit.add_argument("--write", action="store_true", help="save snapshot, reconcile local issues, and write report")
    audit.add_argument("--limit", type=int, default=20, help="maximum entries per report section; 0 means all")
    review = sub.add_parser("review", help="inspect or mark local review issues (never changes Zotero)")
    review_sub = review.add_subparsers(dest="review_command")
    listing = review_sub.add_parser("list")
    listing.add_argument("--status", choices=["all", "open", "ignored", "resolved", "cleared"], default="open")
    marking = review_sub.add_parser("mark")
    marking.add_argument("issue_key")
    marking.add_argument("status", choices=["open", "ignored", "resolved"])
    marking.add_argument("--note", default="", help="local explanation for the review decision")
    return parser


def cmd_zotero(argv: list[str]) -> int:
    parser = _parser()
    if not argv or argv == ["help"]:
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    if not args.command or (args.command == "review" and not args.review_command):
        parser.print_help()
        return 0
    if args.command == "audit" and (args.limit < 0 or (args.offline and args.write)):
        parser.error("--limit must be nonnegative; --offline cannot be combined with --write")
    from . import zotero_audit as audit
    try:
        config = load_config(args.config, args.env_file, args.data_dir)
        if args.command == "doctor":
            print(f"Library: {config.identity}")
            print(f"API key: {'configured' if config.api_key else 'not configured'} ({config.key_source})")
            print(f"Local state: {config.state_dir}")
            for name, path in [("Linked PDF root", config.pdf_dir), ("Zotero storage root", config.storage_dir)]:
                print(f"{name}: " + ("not configured" if path is None else "exists" if path.is_dir() else "missing on this machine"))
            if args.offline:
                print("OK: configuration valid; credentials and remote access have not been verified.")
            else:
                version, total = Client(config).probe()
                print(f"OK: library read access verified; version={version}, items={total} (including child items).")
            return 0
        if args.command == "review":
            if args.review_command == "mark":
                audit.mark(config, args.issue_key, args.status, args.note)
                print("Local review updated. Zotero and project research decisions are unchanged.")
            else:
                state = audit.read_state(config)
                if not state["snapshot"]:
                    raise ZoteroError("No saved audit; run audit --write first.")
                for issue in state["issues"]:
                    status = audit.issue_status(issue)
                    if args.status in {"all", status}:
                        changed = " [evidence changed since review]" if issue.get("evidence_changed") else ""
                        print(f"{issue['issue_key']} [{status}; detected={issue['detected']}] "
                              f"{audit.display(issue['summary'])}{changed}")
            return 0
        state = audit.read_state(config)
        snapshot = state["snapshot"] if args.offline else Client(config).snapshot()
        if snapshot is None:
            raise ZoteroError("No saved full snapshot; run audit --write online first.")
        result = audit.analyze(snapshot, config)
        issues = audit.reconcile(state["issues"], result["issues"], snapshot["fetched_at"])
        if args.write:
            issues = audit.save_audit(config, snapshot, result["issues"])
        report = audit.render(snapshot, result, issues, args.limit, offline=args.offline)
        print(report)
        if args.write:
            audit.write_report(config, report)
            print(f"Saved local audit: {config.state_dir / 'AUDIT_REPORT.md'}")
        else:
            print("Preview only; no local state written.")
        return 0
    except ZoteroError as exc:
        print(f"ERROR: {exc}")
        return 1
    except (OSError, UnicodeError):
        print("ERROR: local file access failed; check paths and permissions. No remote writes were made.")
        return 1
