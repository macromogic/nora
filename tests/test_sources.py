"""Tests for the external-source search layer — all network mocked."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nora_cli import sources as src

ARXIV_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2205.01234v2</id>
    <published>2022-05-03T00:00:00Z</published>
    <title>Instruction Drift in
      Long Conversations</title>
    <author><name>Erin Chen</name></author>
    <author><name>Gil Foster</name></author>
    <arxiv:doi>10.1000/drift.1</arxiv:doi>
  </entry>
</feed>"""

OPENALEX_JSON = json.dumps({"results": [{
    "display_name": "Instruction Drift in Long Conversations",
    "publication_year": 2023,
    "cited_by_count": 41,
    "doi": "https://doi.org/10.1000/DRIFT.1",
    "authorships": [{"author": {"display_name": "Erin Chen"}}],
    "primary_location": {"source": {"display_name": "ACL"},
                         "landing_page_url": "https://example.org/paper"},
    "ids": {"doi": "https://doi.org/10.1000/drift.1"},
}]})

S2_JSON = json.dumps({"data": [{
    "title": "Probing Instruction Adherence in Long Dialogues",
    "year": 2022,
    "venue": "CL Letters",
    "citationCount": 7,
    "externalIds": {"DOI": "10.1000/probe.2"},
    "authors": [{"name": "Carol Lee"}],
    "url": "https://www.semanticscholar.org/paper/x",
}]})

CROSSREF_JSON = json.dumps({"message": {"items": [{
    "title": ["Scaling Effects on Context Retention"],
    "author": [{"family": "Wang", "given": "Dan"}],
    "published-print": {"date-parts": [[2023, 6]]},
    "container-title": ["JMLR"],
    "DOI": "10.1000/scale.3",
    "URL": "https://doi.org/10.1000/scale.3",
    "is-referenced-by-count": 12,
}]}})

DBLP_JSON = json.dumps({"result": {"hits": {"hit": [{
    "info": {"title": "A Survey of Conversational Memory",
             "authors": {"author": {"text": "Hana Ueda"}},
             "year": "2019", "venue": "CSUR",
             "doi": "10.1145/999.888", "ee": "https://doi.org/10.1145/999.888"},
}]}}})

CANNED = {
    "arxiv.org": ARXIV_ATOM,
    "openalex.org": OPENALEX_JSON,
    "semanticscholar.org": S2_JSON,
    "crossref.org": CROSSREF_JSON,
    "dblp.org": DBLP_JSON,
}


@pytest.fixture
def canned_fetch(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        for host, payload in CANNED.items():
            if host in url:
                return payload.encode()
        raise src.SourceError("no canned response")

    monkeypatch.setattr(src, "_fetch", fake_fetch)
    return calls


def test_arxiv_parser(canned_fetch):
    hits = src.search_arxiv("drift", 5)
    assert hits == [{
        "title": "Instruction Drift in Long Conversations",
        "authors": ["Erin Chen", "Gil Foster"],
        "year": 2022, "venue": "arXiv",
        "doi": "10.1000/drift.1", "arxiv": "2205.01234",
        "url": "https://arxiv.org/abs/2205.01234", "citations": None,
    }]


def test_openalex_parser_normalizes_doi(canned_fetch):
    hits = src.search_openalex("drift", 5)
    assert hits[0]["doi"] == "10.1000/drift.1"
    assert hits[0]["citations"] == 41
    assert hits[0]["venue"] == "ACL"


def test_s2_crossref_dblp_parsers(canned_fetch):
    assert src.search_s2("probe", 5)[0]["citations"] == 7
    cr = src.search_crossref("scale", 5)[0]
    assert cr["authors"] == ["Wang, Dan"] and cr["year"] == 2023
    db = src.search_dblp("survey", 5)[0]
    assert db["authors"] == ["Hana Ueda"] and db["doi"] == "10.1145/999.888"


def test_search_all_caches_and_refreshes(canned_fetch, tmp_path):
    results, warnings = src.search_all("drift", 5, tmp_path)
    assert [name for name, _ in results] == src.SOURCE_NAMES
    assert warnings == []
    n_first = len(canned_fetch)
    # cache hit: no new requests
    src.search_all("drift", 5, tmp_path)
    assert len(canned_fetch) == n_first
    # refresh bypasses cache
    src.search_all("drift", 5, tmp_path, refresh=True)
    assert len(canned_fetch) == 2 * n_first


def test_search_all_source_failure_degrades(monkeypatch, tmp_path):
    def failing_fetch(url):
        if "arxiv.org" in url:
            raise src.SourceError("timed out")
        for host, payload in CANNED.items():
            if host in url:
                return payload.encode()
        raise src.SourceError("no canned response")

    monkeypatch.setattr(src, "_fetch", failing_fetch)
    results, warnings = src.search_all("drift", 5, tmp_path)
    assert [name for name, _ in results] == ["openalex", "s2", "crossref", "dblp"]
    assert warnings == ["arxiv: timed out"]
    # the failed source is not cached — a later run retries it
    results2, warnings2 = src.search_all("drift", 5, tmp_path)
    assert warnings2 == ["arxiv: timed out"]


def test_search_all_only_filter(canned_fetch, tmp_path):
    results, _ = src.search_all("drift", 5, tmp_path, only="dblp")
    assert [name for name, _ in results] == ["dblp"]


def test_merge_hits_across_sources():
    per_source, _ = None, None
    a = {"title": "Instruction Drift in Long Conversations", "authors": [],
         "year": 2022, "venue": "arXiv", "doi": "10.1000/drift.1",
         "arxiv": "2205.01234", "url": None, "citations": None}
    b = {"title": "Instruction Drift in Long Conversations!", "authors": ["Erin Chen"],
         "year": 2023, "venue": "ACL", "doi": "10.1000/drift.1",
         "arxiv": None, "url": "https://example.org", "citations": 41}
    c = {"title": "A Different Paper", "authors": [], "year": 2020,
         "venue": None, "doi": None, "arxiv": None, "url": None, "citations": 3}
    merged = src.merge_hits([("arxiv", [a]), ("openalex", [b, c])])
    assert len(merged) == 2
    first = merged[0]
    assert first["sources"] == ["arxiv", "openalex"]  # same DOI merged
    assert first["venue"] == "arXiv"                   # first source wins existing fields
    assert first["citations"] == 41                    # max citation count kept
    assert first["authors"] == ["Erin Chen"]           # empty filled from later source


def test_cached_signals(tmp_path):
    (tmp_path / "openalex-abc.json").write_text(json.dumps([
        {"title": "Some Paper", "doi": "10.1/x", "arxiv": None, "citations": 10},
    ]))
    (tmp_path / "s2-def.json").write_text(json.dumps([
        {"title": "Some Paper", "doi": "10.1/x", "arxiv": None, "citations": 25},
    ]))
    signals = src.cached_signals(tmp_path)
    entry = signals[("doi", "10.1/x")]
    assert entry["citations"] == 25
    assert entry["sources"] == {"openalex", "s2"}
