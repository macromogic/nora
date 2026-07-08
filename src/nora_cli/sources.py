"""External literature sources for 'nora literature search' (Stage 4).

Five keyless metadata APIs, queried in the frozen preference order
arXiv -> OpenAlex -> Semantic Scholar -> Crossref -> DBLP. Design rules:

- stdlib only (urllib + json + xml.etree), 10s timeout per request
- at most one request per source per invocation; a failing source degrades
  to a WARNING and the next source is tried — never a retry loop
- responses are cached permanently under .nora/literature/cache/ keyed by
  source+query; '--refresh' bypasses the cache. Cache hits make repeated
  runs deterministic and offline-friendly.
- results are metadata "hits" (dicts shaped like papers.yaml fields plus
  'citations' and 'sources' signal fields); callers decide what to ingest.

Set NORA_MAILTO to join the polite pools of OpenAlex/Crossref.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from . import papers as ps

TIMEOUT = 10
USER_AGENT = "nora-cli (https://github.com/macromogic/nora)"


class SourceError(Exception):
    """One source failed (network, HTTP, or unparseable payload)."""


def _fetch(url: str) -> bytes:
    """Single HTTP GET. Kept module-level so tests can monkeypatch it."""
    headers = {"User-Agent": USER_AGENT}
    mailto = os.environ.get("NORA_MAILTO")
    if mailto:
        headers["User-Agent"] += f" (mailto:{mailto})"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except (urllib.error.URLError, OSError) as e:
        raise SourceError(str(e))


def _hit(title, authors=None, year=None, venue=None, doi=None, arxiv=None,
         url=None, citations=None) -> dict:
    return {
        "title": " ".join((title or "").split()),
        "authors": authors or [],
        "year": year,
        "venue": venue or None,
        "doi": ps.normalize_doi(doi) if doi else None,
        "arxiv": arxiv,
        "url": url or None,
        "citations": citations,
    }


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# --- per-source parsers -------------------------------------------------------

def search_arxiv(query: str, limit: int) -> list[dict]:
    url = ("https://export.arxiv.org/api/query?search_query="
           + urllib.parse.quote(f"all:{query}") + f"&max_results={limit}")
    try:
        root = ET.fromstring(_fetch(url))
    except ET.ParseError as e:
        raise SourceError(f"unparseable Atom feed: {e}")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    hits = []
    for entry in root.findall("a:entry", ns):
        raw_id = (entry.findtext("a:id", "", ns) or "").rsplit("/abs/", 1)[-1]
        arxiv_id = raw_id.split("v")[0] if raw_id else None
        year = _int_or_none((entry.findtext("a:published", "", ns) or "")[:4])
        doi = entry.findtext("{http://arxiv.org/schemas/atom}doi", None)
        hits.append(_hit(
            title=entry.findtext("a:title", "", ns),
            authors=[a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)],
            year=year, venue="arXiv", doi=doi, arxiv=arxiv_id,
            url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
        ))
    return hits


def search_openalex(query: str, limit: int) -> list[dict]:
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(query)
           + f"&per-page={limit}")
    try:
        data = json.loads(_fetch(url))
    except json.JSONDecodeError as e:
        raise SourceError(f"unparseable JSON: {e}")
    hits = []
    for work in data.get("results", []):
        loc = work.get("primary_location") or {}
        src = loc.get("source") or {}
        ids = work.get("ids") or {}
        arxiv = None
        if (loc.get("landing_page_url") or "").startswith("https://arxiv.org/abs/"):
            arxiv = loc["landing_page_url"].rsplit("/abs/", 1)[-1]
        hits.append(_hit(
            title=work.get("display_name") or work.get("title"),
            authors=[(a.get("author") or {}).get("display_name", "")
                     for a in work.get("authorships", [])],
            year=work.get("publication_year"),
            venue=src.get("display_name"),
            doi=ids.get("doi") or work.get("doi"),
            arxiv=arxiv,
            url=loc.get("landing_page_url"),
            citations=_int_or_none(work.get("cited_by_count")),
        ))
    return hits


def search_s2(query: str, limit: int) -> list[dict]:
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?query="
           + urllib.parse.quote(query) + f"&limit={limit}"
           + "&fields=title,year,venue,citationCount,externalIds,authors,url")
    try:
        data = json.loads(_fetch(url))
    except json.JSONDecodeError as e:
        raise SourceError(f"unparseable JSON: {e}")
    hits = []
    for paper in data.get("data", []):
        ext = paper.get("externalIds") or {}
        hits.append(_hit(
            title=paper.get("title"),
            authors=[a.get("name", "") for a in paper.get("authors", [])],
            year=paper.get("year"),
            venue=paper.get("venue"),
            doi=ext.get("DOI"),
            arxiv=ext.get("ArXiv"),
            url=paper.get("url"),
            citations=_int_or_none(paper.get("citationCount")),
        ))
    return hits


def search_crossref(query: str, limit: int) -> list[dict]:
    url = ("https://api.crossref.org/works?query=" + urllib.parse.quote(query)
           + f"&rows={limit}")
    try:
        data = json.loads(_fetch(url))
    except json.JSONDecodeError as e:
        raise SourceError(f"unparseable JSON: {e}")
    hits = []
    for item in (data.get("message") or {}).get("items", []):
        titles = item.get("title") or []
        authors = []
        for a in item.get("author", []):
            family, given = a.get("family"), a.get("given")
            if family:
                authors.append(f"{family}, {given}" if given else family)
        parts = ((item.get("published-print") or item.get("published-online")
                  or item.get("created") or {}).get("date-parts") or [[None]])
        containers = item.get("container-title") or []
        hits.append(_hit(
            title=titles[0] if titles else None,
            authors=authors,
            year=_int_or_none(parts[0][0] if parts[0] else None),
            venue=containers[0] if containers else None,
            doi=item.get("DOI"),
            url=item.get("URL"),
            citations=_int_or_none(item.get("is-referenced-by-count")),
        ))
    return [h for h in hits if h["title"]]


def search_dblp(query: str, limit: int) -> list[dict]:
    url = ("https://dblp.org/search/publ/api?q=" + urllib.parse.quote(query)
           + f"&format=json&h={limit}")
    try:
        data = json.loads(_fetch(url))
    except json.JSONDecodeError as e:
        raise SourceError(f"unparseable JSON: {e}")
    hits = []
    for hit in ((data.get("result") or {}).get("hits") or {}).get("hit", []):
        info = hit.get("info") or {}
        raw_authors = ((info.get("authors") or {}).get("author")) or []
        if isinstance(raw_authors, dict):
            raw_authors = [raw_authors]
        authors = [a.get("text", "") if isinstance(a, dict) else str(a)
                   for a in raw_authors]
        hits.append(_hit(
            title=info.get("title"),
            authors=authors,
            year=_int_or_none(info.get("year")),
            venue=info.get("venue"),
            doi=info.get("doi"),
            url=info.get("ee") or info.get("url"),
        ))
    return [h for h in hits if h["title"]]


# Frozen preference order.
SOURCES = [
    ("arxiv", search_arxiv),
    ("openalex", search_openalex),
    ("s2", search_s2),
    ("crossref", search_crossref),
    ("dblp", search_dblp),
]

SOURCE_NAMES = [name for name, _ in SOURCES]


# --- cache + orchestration ------------------------------------------------------

def _cache_file(cache_dir: Path, source: str, query: str, limit: int) -> Path:
    digest = hashlib.sha1(f"{query}\x00{limit}".encode()).hexdigest()[:16]
    return cache_dir / f"{source}-{digest}.json"


def search_all(query: str, limit: int, cache_dir: Path,
               only: str | None = None, refresh: bool = False):
    """Query sources in order; return (hits per source, warnings).

    Each source's mapped hits are cached permanently; a cache hit means no
    request at all. Failures produce warnings, never retries.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, list[dict]]] = []
    warnings: list[str] = []
    for name, fn in SOURCES:
        if only and name != only:
            continue
        cached = _cache_file(cache_dir, name, query, limit)
        if cached.is_file() and not refresh:
            results.append((name, json.loads(cached.read_text())))
            continue
        try:
            hits = fn(query, limit)
        except SourceError as e:
            warnings.append(f"{name}: {e}")
            continue
        cached.write_text(json.dumps(hits, ensure_ascii=False, indent=1))
        results.append((name, hits))
    return results, warnings


def merge_hits(per_source: list[tuple[str, list[dict]]]) -> list[dict]:
    """Merge hits across sources: same DOI / arXiv id / normalized title is
    one paper. Keeps the first source's metadata (frozen preference order),
    fills missing fields from later sources, records which sources agreed,
    and keeps the max citation count seen."""
    merged: list[dict] = []
    index: dict = {}

    def keys(h):
        out = []
        if h["doi"]:
            out.append(("doi", h["doi"]))
        if h["arxiv"]:
            out.append(("arxiv", h["arxiv"]))
        if h["title"]:
            out.append(("title", ps.normalize_title(h["title"])))
        return out

    for source, hits in per_source:
        for h in hits:
            existing = next((index[k] for k in keys(h) if k in index), None)
            if existing is None:
                h = dict(h)
                h["sources"] = [source]
                merged.append(h)
                existing = h
            else:
                if source not in existing["sources"]:
                    existing["sources"].append(source)
                for field in ("year", "venue", "doi", "arxiv", "url"):
                    if not existing[field] and h[field]:
                        existing[field] = h[field]
                if not existing["authors"] and h["authors"]:
                    existing["authors"] = h["authors"]
                if h["citations"] is not None and (
                        existing["citations"] is None or h["citations"] > existing["citations"]):
                    existing["citations"] = h["citations"]
            for k in keys(existing):
                index[k] = existing
    return merged


def cached_signals(cache_dir: Path) -> dict:
    """Signal map from every cached response: normalized key -> signals.

    Used to enrich TOP_CANDIDATES.md for candidates whose metadata came
    through search. Purely a view input — never written into papers.yaml.
    """
    signals: dict = {}
    if not cache_dir.is_dir():
        return signals
    for f in sorted(cache_dir.glob("*.json")):
        source = f.name.split("-")[0]
        try:
            hits = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for h in hits:
            for key in ([("doi", h["doi"])] if h.get("doi") else []) + \
                       ([("arxiv", h["arxiv"])] if h.get("arxiv") else []) + \
                       ([("title", ps.normalize_title(h["title"]))] if h.get("title") else []):
                entry = signals.setdefault(key, {"citations": None, "sources": set()})
                entry["sources"].add(source)
                c = h.get("citations")
                if c is not None and (entry["citations"] is None or c > entry["citations"]):
                    entry["citations"] = c
    return signals
