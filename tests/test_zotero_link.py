"""Project linking, three-way synchronization, and schema compatibility."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from nora_cli import literature as lit, papers as ps, zotero as z, zotero_link as zl
from nora_cli.cli import main


def remote(key="PAPER001", version=1, **fields):
    data = {"itemType": "journalArticle", "title": "Shared Research Paper", "DOI": "10.1000/example",
            "creators": [{"creatorType": "author", "lastName": "Lee", "firstName": "Ada"}],
            "date": "2024-01-01", "collections": ["COLLECT1"], "url": "https://example.org/paper"}
    data.update(fields)
    return {"key": key, "version": version, "data": data}


def snapshot(items=None):
    return {"schema_version": 1, "library": "user:123", "version": 20, "fetched_at": "2026-10-28T12:00:00Z",
            "items": [remote()] if items is None else items, "total_api_items": 1,
            "collections": [{"key": "COLLECT1", "version": 1, "data": {"name": "Parent"}},
                            {"key": "COLLECT2", "version": 1, "data": {"name": "Child", "parentCollection": "COLLECT1"}}]}


def args(*argv):
    return lit.build_parser().parse_args(["zotero", *argv])


def imported():
    updated, _, blocked = zl.plan([], snapshot(), args("import", "--item", "PAPER001"))
    assert not blocked
    return updated


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    for key in list(z.ENV_FIELDS) + ["ZOTERO_API_KEY", "XDG_CONFIG_HOME"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123")
    (tmp_path / ".nora/literature/PAPER_NOTES").mkdir(parents=True)
    ps.save(tmp_path, [])
    monkeypatch.setattr(z.Client, "snapshot", lambda self: snapshot())
    return tmp_path


def test_preview_has_no_side_effect_apply_idempotent_and_backup(project):
    before = ps.papers_path(project).read_bytes()
    command = ["lit", "zotero", "import", "--item", "PAPER001"]
    assert main(command) == 0
    assert ps.papers_path(project).read_bytes() == before
    assert not (project / ".nora/literature/backups").exists()
    assert main(command + ["--apply"]) == 0
    first = ps.papers_path(project).read_bytes()
    paper = ps.load(project)[0]
    assert paper["status"] == "candidate" and paper["roles"] == [] and paper["decision"] is None
    assert ps.zotero_link(paper)["library"] == "user:123"
    assert b"schema_version: 2" in first
    backups = list((project / ".nora/literature/backups").glob("*.yaml"))
    assert len(backups) == 1 and backups[0].read_bytes() == before
    assert main(command + ["--apply"]) == 0
    assert ps.papers_path(project).read_bytes() == first
    assert len(list((project / ".nora/literature/backups").glob("*.yaml"))) == 1


def test_schema1_stays_schema1_and_v2_survives_regular_mark(project):
    ordinary = []
    lit._add_paper(ordinary, {"title": "Local paper", "authors": []}, "manual")
    text = ps.emit(ordinary)
    assert "schema_version: 1" in text and ps.parse(text) == ordinary
    linked = imported()
    ps.save(project, linked + ordinary)
    original_link = ps.load(project)[0]["zotero"]
    assert main(["lit", "mark", linked[0]["id"], "queued", "--role", "background"]) == 0
    assert ps.load(project)[0]["zotero"] == original_link
    assert main(["lit", "doctor"]) == 0
    assert main(["lit", "ingest", "--title", "Third paper"]) == 0
    assert ps.load(project)[0]["zotero"] == original_link


def test_two_projects_sync_title_preserves_each_research_state(tmp_path):
    projects = []
    for number, status in enumerate(["reading", "cited"]):
        root = tmp_path / str(number)
        notes = root / ".nora/literature/PAPER_NOTES"
        notes.mkdir(parents=True)
        papers = imported()
        p = papers[0]
        p.update(status=status, roles=["background" if number == 0 else "methodology"],
                 note=f"Project {number} rationale", decision="D001" if number else None)
        (notes / (p["id"] + ".md")).write_text(f"Project {number} full note")
        ps.save(root, papers)
        projects.append((root, copy.deepcopy(p)))
    changed = snapshot([remote(version=2, title="Revised Shared Research Paper")])
    for root, before in projects:
        papers = ps.load(root)
        after, _, problems = zl.plan(papers, changed, args("sync"))
        assert not problems and after[0]["title"] == "Revised Shared Research Paper"
        for field in ("id", "status", "roles", "note", "decision", "added", "source"):
            assert after[0][field] == before[field]
        ps.save(root, after)
        assert (root / ".nora/literature/PAPER_NOTES" / (before["id"] + ".md")).read_text().startswith("Project")


def test_initial_doi_match_keeps_id_source_and_missing_remote_fields():
    existing = []
    paper = lit._add_paper(existing, {"title": "Previous title", "authors": ["Lee, Ada"],
                                    "doi": "https://doi.org/10.1000/EXAMPLE", "venue": "Local venue"}, "bibtex")
    paper.update(status="read", decision="D007", note="Keep this", roles=["background"])
    result, _, blocked = zl.plan(existing, snapshot(), args("import", "--item", "PAPER001"))
    assert not blocked and len(result) == 1
    assert result[0]["id"] == paper["id"] and result[0]["source"] == "bibtex"
    assert result[0]["venue"] == "Local venue" and result[0]["decision"] == "D007"
    assert result[0]["title"] == "Shared Research Paper"


def test_ambiguous_matches_list_candidates_and_explicit_mapping():
    papers = []
    for title in ("First existing", "Second existing"):
        lit._add_paper(papers, {"title": title, "doi": "10.1000/example"}, "manual")
    result, _, blocked = zl.plan(papers, snapshot(), args("import", "--item", "PAPER001"))
    assert len(blocked) == 1 and all(p["id"] in blocked[0] for p in papers)
    chosen = papers[1]["id"]
    result, _, blocked = zl.plan(papers, snapshot(), args("import", "--item", "PAPER001", "--match", f"PAPER001={chosen}"))
    assert not blocked and "zotero" not in result[0] and "zotero" in result[1]


def test_same_title_conflicting_doi_requires_explicit_new():
    papers = []
    lit._add_paper(papers, {"title": "Shared Research Paper", "doi": "10.1000/other"}, "manual")
    _, _, blocked = zl.plan(papers, snapshot(), args("import", "--item", "PAPER001"))
    assert blocked
    result, _, blocked = zl.plan(papers, snapshot(), args("import", "--item", "PAPER001", "--new", "PAPER001"))
    assert not blocked and len(result) == 2


def test_three_way_keeps_local_only_change_and_blocks_both_sides():
    papers = imported()
    papers[0]["venue"] = "Local venue"
    incoming = snapshot([remote(version=2, title="New title")])
    after, _, blocked = zl.plan(papers, incoming, args("sync"))
    assert not blocked and after[0]["venue"] == "Local venue"
    papers[0]["title"] = "Local title"
    after, _, blocked = zl.plan(papers, incoming, args("sync"))
    assert blocked and "Local title" in blocked[0] and "New title" in blocked[0]
    after, _, blocked = zl.plan(papers, incoming, args("sync", "--prefer-zotero"))
    assert not blocked and after[0]["title"] == "New title" and after[0]["venue"] == "Local venue"


@pytest.mark.parametrize("change", ["older", "same_version", "missing"])
def test_stale_or_missing_remote_does_not_mutate_project(project, monkeypatch, change):
    papers = imported()
    ps.save(project, papers)
    before = ps.papers_path(project).read_bytes()
    incoming = [] if change == "missing" else [remote(version=0 if change == "older" else 1, title="Unexpected change")]
    monkeypatch.setattr(z.Client, "snapshot", lambda self: snapshot(incoming))
    assert main(["lit", "zotero", "sync", "--apply"]) == 1
    assert ps.papers_path(project).read_bytes() == before


def test_collection_direct_and_recursive_and_duplicate_source_block():
    snap = snapshot([remote(), remote("PAPER002", title="Different paper", DOI="10.1000/second", collections=["COLLECT2"])])
    result, _, blocked = zl.plan([], snap, args("import", "--collection", "COLLECT1"))
    assert not blocked and len(result) == 1
    result, _, blocked = zl.plan([], snap, args("import", "--collection", "COLLECT1", "--recursive"))
    assert not blocked and len(result) == 2
    duplicate = snapshot([remote(), remote("PAPER002")])
    _, _, blocked = zl.plan([], duplicate, args("import", "--collection", "COLLECT1"))
    assert blocked and "another Zotero item" in blocked[0]


def test_cross_library_never_silently_relinks():
    papers = imported()
    snap = snapshot()
    snap["library"] = "group:456"
    _, _, blocked = zl.plan(papers, snap, args("import", "--item", "PAPER001"))
    assert blocked
    result, _, blocked = zl.plan(papers, snap, args("sync"))
    assert not blocked and result == papers
    with pytest.raises(z.ZoteroError, match="configured"):
        zl.plan(papers, snap, args("sync", "--id", papers[0]["id"]))


def test_concurrent_local_edit_rejects_stale_plan(project, monkeypatch):
    def snapshot_with_edit(self):
        ps.save(project, imported())
        return snapshot()
    monkeypatch.setattr(z.Client, "snapshot", snapshot_with_edit)
    assert main(["lit", "zotero", "import", "--item", "PAPER001", "--apply"]) == 1
    assert len(ps.load(project)) == 1
    assert not (project / ".nora/literature/backups").exists()


def test_no_implicit_module_initialization(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert main(["lit", "zotero", "import", "--item", "PAPER001", "--apply"]) == 1
    assert not (tmp_path / ".nora").exists()


def test_offline_source_and_nested_workspace(project, monkeypatch):
    from nora_cli.zotero_audit import save_audit
    config = z.Config("123", data_dir=project / "shared-state")
    save_audit(config, snapshot(), [])
    nested = project / "chapters"
    nested.mkdir()
    monkeypatch.chdir(nested)
    def fail(self):
        raise AssertionError("network should not run")
    monkeypatch.setattr(z.Client, "snapshot", fail)
    assert main(["lit", "zotero", "import", "--item", "PAPER001", "--data-dir", str(config.data_dir), "--offline", "--apply"]) == 0
    assert len(ps.load(project)) == 1 and not (nested / ".nora").exists()


def test_bad_link_schema_and_duplicate_identity_fail_closed():
    papers = imported()
    text = ps.emit(papers)
    assert ps.parse(text) == papers
    with pytest.raises(ps.PapersError, match="schema_version 2"):
        ps.parse(text.replace("schema_version: 2", "schema_version: 1"))
    duplicate = copy.deepcopy(papers[0])
    duplicate["id"] = "another"
    with pytest.raises(ps.PapersError, match="duplicate Zotero"):
        ps.parse(ps.emit(papers + [duplicate]))
    papers[0]["zotero"] = json.dumps({"library": "user:123", "key": "PAPER001", "version": 1, "baseline": {}})
    with pytest.raises(ps.PapersError, match="invalid Zotero"):
        ps.parse(ps.emit(papers))


def test_mapping_corporate_author_arxiv_and_whitespace():
    fields = zl.metadata(remote(title="Title\nwith whitespace", DOI="https://doi.org/10.48550/arXiv.2401.12345",
                                creators=[{"creatorType": "author", "name": "Research\nInstitute"}]))
    assert fields["title"] == "Title with whitespace"
    assert fields["authors"] == ["Research Institute"] and fields["arxiv"] == "2401.12345"


def test_partial_batch_conflict_never_applies_other_changes(project, monkeypatch):
    papers = imported()
    papers[0]["title"] = "Local edit"
    ps.save(project, papers)
    before = ps.papers_path(project).read_bytes()
    monkeypatch.setattr(z.Client, "snapshot", lambda self: snapshot([
        remote(version=2, title="Remote edit"), remote("PAPER002", title="New item", DOI="10.1000/new")]))
    assert main(["lit", "zotero", "import", "--collection", "COLLECT1", "--apply"]) == 1
    assert ps.papers_path(project).read_bytes() == before


def test_regular_writer_cannot_erase_concurrently_added_links(project):
    stale = ps.load(project)
    ps.save(project, imported())
    lit._add_paper(stale, {"title": "Concurrent search result"}, "search")
    with pytest.raises(ps.PapersError, match="changed since planning"):
        ps.save(project, stale)
    assert len(ps.load(project)) == 1 and "zotero" in ps.load(project)[0]


def test_atomic_save_failure_preserves_old_project(project, monkeypatch):
    before = ps.papers_path(project).read_bytes()
    def fail(*args):
        raise OSError("replace failed")
    monkeypatch.setattr(ps.os, "replace", fail)
    with pytest.raises(OSError):
        ps.save(project, imported(), expected_text=before.decode(), backup=True)
    assert ps.papers_path(project).read_bytes() == before
    assert not (project / ".nora/literature/.papers.write.lock").exists()
    assert not list((project / ".nora/literature").glob(".papers-*"))


def test_ignore_blocks_explicit_import_and_skips_sync_without_deleting(project):
    from nora_cli import zotero_scope as scope
    command = ['lit', 'zotero', 'import', '--item', 'PAPER001', '--apply']
    assert main(command) == 0
    before = ps.papers_path(project).read_bytes()
    scope.change(z.load_config(), 'add', 'COLLECT1')
    assert main(command) == 1
    assert main(['lit', 'zotero', 'import', '--collection', 'COLLECT1', '--apply']) == 1
    assert main(['lit', 'zotero', 'sync', '--apply']) == 0
    assert ps.papers_path(project).read_bytes() == before


def test_recursive_import_skips_ignored_child(project, monkeypatch):
    from nora_cli import zotero_scope as scope
    snap = snapshot([remote(), remote('PAPER002', collections=['COLLECT2'], DOI='10.1000/other', title='Other')])
    monkeypatch.setattr(z.Client, 'snapshot', lambda self: snap)
    scope.change(z.load_config(), 'add', 'COLLECT2')
    assert main(['lit', 'zotero', 'import', '--collection', 'COLLECT1', '--recursive', '--apply']) == 0
    assert [ps.zotero_link(p)['key'] for p in ps.load(project)] == ['PAPER001']


def test_known_stale_offline_import_does_not_write(project):
    from nora_cli.zotero_audit import save_audit
    config = z.Config('123', data_dir=project / 'shared-state')
    save_audit(config, snapshot(), [])
    directory = config.state_dir / 'collection_operations'
    directory.mkdir()
    (directory / 'write.json').write_text(json.dumps(dict(
        library=config.identity, status='verified', verified_library_version=21)))
    path = project / '.nora/literature/papers.yaml'
    before = path.read_bytes()
    argv = ['lit', 'zotero', 'import', '--item', 'PAPER001', '--data-dir', str(config.data_dir), '--offline']
    assert main(argv) == 0
    assert main(argv + ['--apply']) == 1
    assert path.read_bytes() == before
