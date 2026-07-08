"""Literature backend storage: .nora/literature/papers.yaml.

papers.yaml is the single source of truth for the literature module. It is
written and read exclusively by this module using a strict YAML subset —
there is no YAML library in the stdlib, so the parser accepts only what the
emitter produces (fixed two-space indentation, double-quoted strings with
backslash escapes, inline lists of quoted strings, bare ints and nulls).
Hand-edits outside that subset are rejected with a clear error instead of
being silently misread.
"""

from __future__ import annotations

import re
from pathlib import Path

SCHEMA_VERSION = 1

# Field order is fixed: the emitter always writes every field in this order,
# which keeps diffs stable and lets the parser stay simple.
FIELDS = [
    "id", "title", "authors", "year", "venue", "doi", "arxiv", "url",
    "source", "status", "roles", "decision", "added", "updated", "note",
]

LIST_FIELDS = {"authors", "roles"}
INT_FIELDS = {"year"}

SOURCES = ["manual", "bibtex", "title_list", "search", "expand"]

STATUSES = ["candidate", "queued", "reading", "read", "proposed_cite", "cited", "rejected"]

# Promotion to any of these requires an approved decision-gate entry;
# `nora literature mark` refuses otherwise.
GATED_STATUSES = ["read", "proposed_cite", "cited", "rejected"]

ROLES = [
    "direct_related", "background", "platform_spec", "threat_model",
    "methodology", "evaluation_tool", "dataset_benchmark",
    "defense_mitigation", "competing_system", "survey", "other",
]

# Skipped when picking the "first substantive title word" for local IDs.
_STOPWORDS = {
    "a", "an", "the", "on", "of", "for", "in", "to", "and", "or", "with",
    "from", "into", "via", "toward", "towards", "at", "by", "is", "are",
    "do", "does", "how", "what", "why", "can",
}


class PapersError(Exception):
    """Raised when papers.yaml cannot be parsed as the strict subset."""


def papers_path(base: Path) -> Path:
    return base / ".nora" / "literature" / "papers.yaml"


# --- strict YAML subset: emit ---------------------------------------------

def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _emit_value(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_quote(v) for v in value) + "]"
    return _quote(value)


def emit(papers: list[dict]) -> str:
    lines = [
        "# Literature state. Single source of truth for the literature module.",
        "# Written and parsed only by the nora CLI (strict YAML subset) — use",
        "# 'nora literature' commands instead of editing by hand.",
        f"schema_version: {SCHEMA_VERSION}",
        "papers:" if papers else "papers: []",
    ]
    for paper in papers:
        prefix = "  - "
        for field in FIELDS:
            lines.append(prefix + f"{field}: {_emit_value(paper.get(field))}")
            prefix = "    "
    return "\n".join(lines) + "\n"


# --- strict YAML subset: parse ---------------------------------------------

def _parse_quoted(text: str, lineno: int) -> tuple[str, str]:
    """Parse a leading double-quoted string; return (value, rest)."""
    if not text.startswith('"'):
        raise PapersError(f"papers.yaml:{lineno}: expected a double-quoted string, got: {text!r}")
    out = []
    i = 1
    while i < len(text):
        c = text[i]
        if c == "\\":
            if i + 1 >= len(text) or text[i + 1] not in '\\"':
                raise PapersError(f"papers.yaml:{lineno}: unsupported escape in: {text!r}")
            out.append(text[i + 1])
            i += 2
        elif c == '"':
            return "".join(out), text[i + 1:]
        else:
            out.append(c)
            i += 1
    raise PapersError(f"papers.yaml:{lineno}: unterminated string: {text!r}")


def _parse_value(field: str, raw: str, lineno: int):
    raw = raw.strip()
    if field in LIST_FIELDS:
        if not (raw.startswith("[") and raw.endswith("]")):
            raise PapersError(f"papers.yaml:{lineno}: field '{field}' must be an inline list")
        inner = raw[1:-1].strip()
        items = []
        while inner:
            value, inner = _parse_quoted(inner, lineno)
            items.append(value)
            inner = inner.strip()
            if inner.startswith(","):
                inner = inner[1:].strip()
            elif inner:
                raise PapersError(f"papers.yaml:{lineno}: malformed list near: {inner!r}")
        return items
    if raw == "null":
        return None
    if field in INT_FIELDS:
        if not re.fullmatch(r"-?\d+", raw):
            raise PapersError(f"papers.yaml:{lineno}: field '{field}' must be an integer or null")
        return int(raw)
    value, rest = _parse_quoted(raw, lineno)
    if rest.strip():
        raise PapersError(f"papers.yaml:{lineno}: trailing content after string: {rest!r}")
    return value


def parse(text: str) -> list[dict]:
    lines = text.splitlines()
    papers: list[dict] = []
    current: dict | None = None
    saw_version = False
    saw_papers = False

    for lineno, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("schema_version:"):
            raw = line.partition(":")[2].strip()
            if raw != str(SCHEMA_VERSION):
                raise PapersError(
                    f"papers.yaml:{lineno}: unsupported schema_version {raw} (expected {SCHEMA_VERSION})")
            saw_version = True
            continue
        if line.startswith("papers:"):
            saw_papers = True
            rest = line.partition(":")[2].strip()
            if rest not in ("", "[]"):
                raise PapersError(f"papers.yaml:{lineno}: unexpected content after 'papers:'")
            continue
        if line.startswith("  - "):
            current = {}
            papers.append(current)
            body = line[4:]
        elif line.startswith("    ") and current is not None:
            body = line[4:]
        else:
            raise PapersError(f"papers.yaml:{lineno}: unexpected line: {line!r}")
        field, sep, raw = body.partition(": ")
        if not sep and body.endswith(":"):
            field, raw = body[:-1], ""
        if field not in FIELDS:
            raise PapersError(f"papers.yaml:{lineno}: unknown field: {field!r}")
        if field in current:
            raise PapersError(f"papers.yaml:{lineno}: duplicate field: {field!r}")
        current[field] = _parse_value(field, raw, lineno)

    if not saw_version or not saw_papers:
        raise PapersError("papers.yaml: missing schema_version or papers key")
    for paper in papers:
        for field in FIELDS:
            if field not in paper:
                raise PapersError(f"papers.yaml: entry {paper.get('id', '?')!r} missing field {field!r}")
    return papers


def load(base: Path) -> list[dict]:
    path = papers_path(base)
    if not path.is_file():
        raise PapersError(f"{path} not found. Run 'nora literature init' first.")
    return parse(path.read_text())


def save(base: Path, papers: list[dict]) -> None:
    papers_path(base).write_text(emit(papers))


# --- normalization and IDs --------------------------------------------------

def normalize_title(title: str) -> str:
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in title.lower())
    return " ".join(cleaned.split())


def normalize_doi(doi: str) -> str:
    doi = doi.strip().lower()
    # any DOI-ish host counts: doi.org, dx.doi.org, library proxies like doi-org.proxy.*
    doi = re.sub(r"^https?://[^/]*doi[^/]*/", "", doi)
    for prefix in ("doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi


def _ascii_slug(text: str) -> str:
    return "".join(c for c in text.lower() if c.isascii() and c.isalnum())


def make_id(papers: list[dict], authors: list[str], year, title: str) -> str:
    """Lowercase first-author surname + year + first substantive title word.

    Same shape as the citation-key convention frozen for Stage 6, so a local
    ID can later double as a BibTeX key candidate. Collisions get b/c/...
    suffixes; IDs never change once assigned.
    """
    surname = "anon"
    if authors:
        first = authors[0]
        surname = _ascii_slug(first.split(",")[0] if "," in first else first.split()[-1]) or "anon"
    word = next(
        (w for w in normalize_title(title).split() if w not in _STOPWORDS and _ascii_slug(w)),
        "untitled",
    )
    stem = f"{surname}{year if year is not None else 'nd'}{_ascii_slug(word)}"
    existing = {p["id"] for p in papers}
    if stem not in existing:
        return stem
    for suffix in "bcdefghijklmnopqrstuvwxyz":
        if stem + suffix not in existing:
            return stem + suffix
    raise PapersError(f"could not allocate a unique id for stem {stem!r}")


# --- minimal BibTeX reader (ingest only; never writes .bib) -----------------

def parse_bibtex(text: str) -> list[dict]:
    """Extract (type, key, fields) from a .bib file — tolerant, read-only.

    Handles brace- and quote-delimited values with nested braces. Skips
    @comment/@string/@preamble. Not a validator: malformed trailing entries
    are dropped rather than raised, since ingest wants best-effort reading.
    """
    entries = []
    for match in re.finditer(r"@(\w+)\s*\{", text):
        kind = match.group(1).lower()
        if kind in ("comment", "string", "preamble"):
            continue
        i = match.end()
        depth = 1
        start = i
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        if depth:
            break
        body = text[start:i - 1]
        key, _, rest = body.partition(",")
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", rest):
            name = fm.group(1).lower()
            j = fm.end()
            if j >= len(rest):
                continue
            if rest[j] == "{":
                depth, j2 = 1, j + 1
                while j2 < len(rest) and depth:
                    if rest[j2] == "{":
                        depth += 1
                    elif rest[j2] == "}":
                        depth -= 1
                    j2 += 1
                value = rest[j + 1:j2 - 1]
            elif rest[j] == '"':
                j2 = rest.find('"', j + 1)
                value = rest[j + 1:j2 if j2 != -1 else len(rest)]
            else:
                j2 = rest.find(",", j)
                value = rest[j:j2 if j2 != -1 else len(rest)]
            fields[name] = " ".join(value.replace("{", "").replace("}", "").split())
        entries.append({"type": kind, "key": key.strip(), "fields": fields})
    return entries


def bibtex_to_paper_fields(entry: dict) -> dict:
    """Map a parsed BibTeX entry onto papers.yaml fields (no id/status yet)."""
    f = entry["fields"]
    authors = [a.strip() for a in f.get("author", "").split(" and ") if a.strip()]
    year = int(f["year"]) if re.fullmatch(r"\d{4}", f.get("year", "")) else None
    venue = f.get("journal") or f.get("booktitle") or f.get("publisher")
    if not venue and f.get("archiveprefix", "").lower() == "arxiv":
        venue = "arXiv"
    arxiv = f.get("eprint") if f.get("archiveprefix", "").lower() == "arxiv" else None
    return {
        "title": f.get("title") or entry["key"],
        "authors": authors,
        "year": year,
        "venue": venue,
        "doi": normalize_doi(f["doi"]) if f.get("doi") else None,
        "arxiv": arxiv,
        "url": f.get("url") or None,
    }
