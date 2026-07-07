"""Round-trip and unit tests for the papers.yaml strict-subset storage."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nora_cli import papers as ps


def paper(**overrides):
    base = {
        "id": "lee2022probing",
        "title": "Probing Instruction Adherence in Long Dialogues",
        "authors": ["Lee, Carol"],
        "year": 2022,
        "venue": "CL Letters",
        "doi": "10.1000/xyz.123",
        "arxiv": None,
        "url": None,
        "source": "manual",
        "status": "candidate",
        "roles": ["background", "methodology"],
        "decision": None,
        "added": "2026-07-07",
        "updated": "2026-07-07",
        "note": None,
    }
    base.update(overrides)
    return base


NASTY_STRINGS = [
    'Title with "double quotes" inside',
    "Backslash \\ and \\\" mix",
    "Colons: everywhere: really",
    "Unicode – dashes — and 中文标题 and émojis ✓",
    "  [brackets], {braces}, #hashes and trailing spaces  ",
    "null",   # the string "null", not None
    "123",    # the string "123", not an int
    "- id: fake",  # looks like a new entry
]


def test_roundtrip_empty():
    assert ps.parse(ps.emit([])) == []


def test_roundtrip_nasty_strings():
    papers = [
        paper(id=f"p{i}", title=s, note=s, venue=s, authors=[s, "Plain, Name"])
        for i, s in enumerate(NASTY_STRINGS)
    ]
    assert ps.parse(ps.emit(papers)) == papers


def test_roundtrip_null_year_and_empty_lists():
    p = paper(year=None, authors=[], roles=[], doi=None)
    assert ps.parse(ps.emit([p])) == [p]


def test_parse_rejects_wrong_schema_version():
    text = ps.emit([paper()]).replace("schema_version: 1", "schema_version: 99")
    with pytest.raises(ps.PapersError, match="schema_version"):
        ps.parse(text)


def test_parse_rejects_unquoted_string():
    text = ps.emit([paper()]).replace('venue: "CL Letters"', "venue: CL Letters")
    with pytest.raises(ps.PapersError, match="double-quoted"):
        ps.parse(text)


def test_parse_rejects_unknown_field():
    text = ps.emit([paper()]) + "    surprise: \"x\"\n"
    with pytest.raises(ps.PapersError, match="unknown field"):
        ps.parse(text)


def test_parse_rejects_missing_field():
    text = ps.emit([paper()]).replace('    note: null\n', "")
    with pytest.raises(ps.PapersError, match="missing field"):
        ps.parse(text)


# --- IDs and normalization ----------------------------------------------------

def test_make_id_basic_and_stopwords():
    assert ps.make_id([], ["Lee, Carol"], 2022, "The Probing of Adherence") == "lee2022probing"


def test_make_id_no_author_no_year():
    assert ps.make_id([], [], None, "On the Nature of Things") == "anonndnature"


def test_make_id_collision_suffix():
    existing = [paper(id="lee2022probing"), paper(id="lee2022probingb")]
    assert ps.make_id(existing, ["Lee, Carol"], 2022, "Probing Again") == "lee2022probingc"


def test_make_id_space_separated_author():
    assert ps.make_id([], ["Carol Lee"], 2021, "Scaling Laws") == "lee2021scaling"


def test_normalize_doi_variants():
    for raw in ["10.1000/XYZ.123", "https://doi.org/10.1000/xyz.123",
                "doi:10.1000/Xyz.123", "DOI.ORG/10.1000/xyz.123".lower()]:
        assert ps.normalize_doi(raw) == "10.1000/xyz.123"


def test_normalize_title_strips_punctuation():
    assert ps.normalize_title("  Instruction—Drift: in LONG conversations!  ") == \
        "instruction drift in long conversations"


# --- BibTeX reader --------------------------------------------------------------

BIB = """
@comment{ignore me}
@article{smith2021deep,
  title = {Deep {Nested {Braces}} Models},
  author = {Smith, Alice and Jones, Bob},
  year = {2021},
  journal = "JAIR",
  doi = {10.1000/xyz.123},
}
@misc{chen2022drift,
  title = {Instruction Drift},
  author = {Chen, Erin},
  year = {2022},
  eprint = {2205.01234},
  archivePrefix = {arXiv},
}
"""


def test_parse_bibtex_entries_and_comment_skip():
    entries = ps.parse_bibtex(BIB)
    assert [e["key"] for e in entries] == ["smith2021deep", "chen2022drift"]
    assert entries[0]["fields"]["title"] == "Deep Nested Braces Models"
    assert entries[0]["fields"]["journal"] == "JAIR"


def test_bibtex_to_paper_fields_mapping():
    entries = ps.parse_bibtex(BIB)
    smith = ps.bibtex_to_paper_fields(entries[0])
    assert smith["authors"] == ["Smith, Alice", "Jones, Bob"]
    assert smith["year"] == 2021
    assert smith["venue"] == "JAIR"
    assert smith["doi"] == "10.1000/xyz.123"
    chen = ps.bibtex_to_paper_fields(entries[1])
    assert chen["arxiv"] == "2205.01234"
    assert chen["venue"] == "arXiv"
