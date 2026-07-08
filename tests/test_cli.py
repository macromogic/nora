"""End-to-end tests for the Nora CLI, mirroring the manual bash test matrix
recorded in .nora/SESSION_LOG.md: doctor three tiers, init idempotency,
install-skills symlinks, module init/doctor including failure paths."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nora_cli.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated HOME + NORA_HOME (pointing at the real repo) + empty cwd."""
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("NORA_HOME", str(REPO_ROOT))
    monkeypatch.chdir(project)
    return tmp_path


def run(*args):
    return main(list(args))


# --- help / unknown ---------------------------------------------------------

def test_help_default_and_explicit(env, capsys):
    assert run() == 0
    default_out = capsys.readouterr().out
    assert run("help") == 0
    assert capsys.readouterr().out == default_out
    assert "nora install-skills" in default_out


def test_unknown_command_exits_1(env, capsys):
    assert run("frobnicate") == 1
    out = capsys.readouterr().out
    assert "Unknown command: frobnicate" in out


# --- new / init -------------------------------------------------------------

def test_new_creates_core_state(env, capsys):
    assert run("new") == 0
    out = capsys.readouterr().out
    assert "Initialized core Nora project state" in out
    for f in ["AGENTS.md", ".nora/PROJECT_STATE.yaml", ".nora/CONTEXT_BRIEF.md",
              ".nora/SESSION_LOG.md", ".nora/NEXT_ACTIONS.md", ".nora/OPEN_LOOPS.md"]:
        assert Path(f).is_file(), f
    # opt-in module design: no module dirs created by `nora new`
    for mod in ["citation", "literature", "writing"]:
        assert not (Path(".nora") / mod).exists()


def test_new_is_idempotent(env, capsys):
    assert run("new") == 0
    capsys.readouterr()
    assert run("new") == 0
    assert "already exists" in capsys.readouterr().out


def test_init_is_alias_for_new(env, capsys):
    assert run("init") == 0
    assert Path(".nora/PROJECT_STATE.yaml").is_file()


def test_new_creates_workspace_identity_and_gate(env, capsys):
    assert run("new") == 0
    gitignore = Path(".nora/.gitignore")
    assert gitignore.is_file() and gitignore.read_text().strip() == "*"
    config = Path(".nora/config.yaml").read_text()
    assert "project_id: project" in config  # slug of the test dir name
    assert "workspace_id: main" in config
    assert Path(".nora/decisions/decisions.yaml").is_file()


def test_new_refuses_nested_workspace(env, capsys):
    run("new")
    sub = Path("sub/dir")
    sub.mkdir(parents=True)
    os.chdir(sub)
    capsys.readouterr()
    assert run("new") == 1
    out = capsys.readouterr().out
    assert "Refusing to create nested Nora state" in out
    assert not Path(".nora").exists()


# --- root ---------------------------------------------------------------------

def test_root_resolves_from_subdir(env, capsys):
    run("new")
    project_root = Path.cwd()
    sub = Path("sections/deep")
    sub.mkdir(parents=True)
    os.chdir(sub)
    capsys.readouterr()
    assert run("root") == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == str(project_root)
    assert out[1].startswith("workspace: main")
    assert "project: project" in out[1]


def test_root_not_found_exits_1(env, capsys):
    assert run("root") == 1
    assert "No Nora workspace found" in capsys.readouterr().out


def test_root_does_not_cross_home_boundary(env, capsys, monkeypatch):
    # a stray .nora above $HOME must not capture directories inside $HOME
    (env / ".nora").mkdir()  # env is the parent of the fake home
    home = Path(os.environ["HOME"])
    inside = home / "some" / "dir"
    inside.mkdir(parents=True)
    monkeypatch.chdir(inside)
    assert run("root") == 1


def test_root_finds_nora_in_home_itself(env, capsys, monkeypatch):
    home = Path(os.environ["HOME"])
    (home / ".nora").mkdir()
    inside = home / "notes"
    inside.mkdir()
    monkeypatch.chdir(inside)
    assert run("root") == 0
    assert capsys.readouterr().out.splitlines()[0] == str(home)


# --- doctor: three tiers ----------------------------------------------------

def test_doctor_ok_outside_project(env, capsys):
    assert run("doctor") == 0
    out = capsys.readouterr().out
    assert "Not in a Nora-managed workspace" in out
    assert "no errors" in out


def test_doctor_ok_in_project_with_module_infos(env, capsys):
    run("new")
    capsys.readouterr()
    assert run("doctor") == 0
    out = capsys.readouterr().out
    assert "OK: .nora/PROJECT_STATE.yaml" in out
    for mod in ["citation", "literature", "writing"]:
        assert f"INFO: {mod} module not initialized" in out


def test_doctor_warning_on_incomplete_module_still_exit_0(env, capsys):
    run("new")
    run("citation", "init")
    Path(".nora/citation/CITATION_AUDIT_REPORT.md").unlink()
    capsys.readouterr()
    assert run("doctor") == 0
    out = capsys.readouterr().out
    assert "WARNING: .nora/citation/CITATION_AUDIT_REPORT.md missing" in out
    assert "no errors" in out


def test_doctor_error_on_missing_core_file(env, capsys):
    run("new")
    Path(".nora/OPEN_LOOPS.md").unlink()
    capsys.readouterr()
    assert run("doctor") == 1
    out = capsys.readouterr().out
    assert "ERROR: missing: .nora/OPEN_LOOPS.md" in out
    assert "found errors" in out


def test_doctor_error_on_broken_symlink(env, capsys):
    home = Path(os.environ["HOME"])
    skills = home / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "nora-project-manager").symlink_to(home / "does-not-exist")
    assert run("doctor") == 1
    out = capsys.readouterr().out
    assert "ERROR: broken symlink" in out


def test_doctor_reports_workspace_and_identity(env, capsys):
    run("new")
    capsys.readouterr()
    assert run("doctor") == 0
    out = capsys.readouterr().out
    assert f"Workspace: {Path.cwd()}" in out
    assert "Identity: workspace: main" in out


def test_doctor_works_from_subdir(env, capsys):
    run("new")
    sub = Path("chapters")
    sub.mkdir()
    os.chdir(sub)
    capsys.readouterr()
    assert run("doctor") == 0
    out = capsys.readouterr().out
    assert "OK: .nora/PROJECT_STATE.yaml" in out


def test_doctor_warns_on_nested_nora(env, capsys):
    run("new")
    (Path("experiments") / ".nora").mkdir(parents=True)
    capsys.readouterr()
    assert run("doctor") == 0  # nested is a WARNING, not an ERROR
    out = capsys.readouterr().out
    assert "WARNING: nested .nora inside this workspace" in out
    assert "experiments/.nora" in out


def test_doctor_reports_sibling_workspace_as_info(env, capsys):
    run("new")
    sibling = env / "paper-draft" / ".nora"
    sibling.mkdir(parents=True)
    capsys.readouterr()
    assert run("doctor") == 0
    out = capsys.readouterr().out
    assert "INFO: sibling workspace" in out
    assert "paper-draft/.nora" in out
    assert "not a conflict" in out


def test_doctor_skips_sibling_scan_directly_under_home(env, capsys, monkeypatch):
    home = Path(os.environ["HOME"])
    ws = home / "my-project"
    ws.mkdir()
    other = home / "other-project" / ".nora"
    other.mkdir(parents=True)
    monkeypatch.chdir(ws)
    run("new")
    capsys.readouterr()
    assert run("doctor") == 0
    assert "sibling workspace" not in capsys.readouterr().out


def test_doctor_legacy_workspace_infos(env, capsys):
    run("new")
    Path(".nora/config.yaml").unlink()
    Path(".nora/.gitignore").unlink()
    Path(".nora/decisions/decisions.yaml").unlink()
    capsys.readouterr()
    assert run("doctor") == 0  # legacy gaps are INFO, never ERROR
    out = capsys.readouterr().out
    assert "INFO: no .nora/config.yaml" in out
    assert "INFO: no .nora/.gitignore" in out
    assert "INFO: no .nora/decisions/decisions.yaml" in out


def test_doctor_error_on_bad_nora_home(env, capsys, monkeypatch):
    monkeypatch.setenv("NORA_HOME", str(env / "nowhere"))
    assert run("doctor") == 1
    out = capsys.readouterr().out
    assert "ERROR: NORA_HOME not found" in out


# --- install-skills ---------------------------------------------------------

def test_install_skills_symlinks_and_aliases(env, capsys):
    home = Path(os.environ["HOME"])
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()
    assert run("install-skills") == 0
    out = capsys.readouterr().out
    for base in [home / ".claude", home / ".codex"]:
        for skill in ["nora-project-manager", "nora-citation-auditor",
                      "nora-literature-manager", "nora-writing-assistant"]:
            link = base / "skills" / skill
            assert link.is_symlink() and link.exists(), link
        for alias, target in [("nora", "nora-project-manager"),
                              ("nora-citation", "nora-citation-auditor"),
                              ("nora-literature", "nora-literature-manager"),
                              ("nora-writing", "nora-writing-assistant")]:
            link = base / "skills" / alias
            assert link.is_symlink()
            assert link.resolve() == (REPO_ROOT / "skills" / target).resolve()
    assert "Restart your agent session" in out


def test_install_skills_idempotent(env, capsys):
    home = Path(os.environ["HOME"])
    (home / ".claude").mkdir()
    assert run("install-skills") == 0
    assert run("install-skills") == 0  # ln -sfn parity: re-link without error


def test_install_skill_alias(env, capsys):
    home = Path(os.environ["HOME"])
    (home / ".claude").mkdir()
    assert run("install-skill") == 0


def test_install_skills_no_agent_dirs_exits_1(env, capsys):
    assert run("install-skills") == 1
    assert "Nothing installed" in capsys.readouterr().out


# --- modules: init + doctor + help ------------------------------------------

# literature has its own backend and test section below (papers.yaml, Stage 3)
MODULE_FILES = {
    "citation": ["CITATION_AUDIT_REPORT.md", "CITATION_REVIEW_QUEUE.yaml",
                 "CLAIM_SUPPORT_AUDIT.md"],
    "writing": ["WRITING_STYLE.md", "STYLE_NOTES.md", "PHRASE_BANK.md"],
}


@pytest.mark.parametrize("mod", MODULE_FILES)
def test_module_init_project_mode(env, capsys, mod):
    run("new")
    capsys.readouterr()
    assert run(mod, "init") == 0
    out = capsys.readouterr().out
    assert "standalone" not in out
    for f in MODULE_FILES[mod]:
        assert (Path(".nora") / mod / f).is_file(), f


@pytest.mark.parametrize("mod", MODULE_FILES)
def test_module_init_standalone_mode(env, capsys, mod):
    assert run(mod, "init") == 0
    out = capsys.readouterr().out
    assert "no full Nora project state found" in out
    assert "(standalone)" in out


@pytest.mark.parametrize("mod", MODULE_FILES)
def test_module_init_idempotent(env, capsys, mod):
    run(mod, "init")
    capsys.readouterr()
    assert run(mod, "init") == 0
    assert "already exists" in capsys.readouterr().out


@pytest.mark.parametrize("mod", MODULE_FILES)
def test_module_doctor_ok(env, capsys, mod):
    run(mod, "init")
    capsys.readouterr()
    assert run(mod, "doctor") == 0
    assert "looks OK" in capsys.readouterr().out


@pytest.mark.parametrize("mod", MODULE_FILES)
def test_module_doctor_missing_dir_exits_1(env, capsys, mod):
    assert run(mod, "doctor") == 1
    out = capsys.readouterr().out
    assert f"ERROR: .nora/{mod}/ not found." in out
    assert f"Run 'nora {mod} init' first." in out


@pytest.mark.parametrize("mod", MODULE_FILES)
def test_module_doctor_incomplete_exits_1(env, capsys, mod):
    run(mod, "init")
    (Path(".nora") / mod / MODULE_FILES[mod][0]).unlink()
    capsys.readouterr()
    assert run(mod, "doctor") == 1
    out = capsys.readouterr().out
    assert "MISSING:" in out
    assert "initialized but incomplete" in out


def test_writing_help_on_unknown_subcommand(env, capsys):
    assert run("writing") == 0
    help_out = capsys.readouterr().out
    assert "nora writing init" in help_out
    assert run("writing", "bogus") == 0
    assert capsys.readouterr().out == help_out


def test_citation_help_and_argparse_usage_error(env, capsys):
    assert run("citation") == 0
    assert "nora citation lint" in capsys.readouterr().out
    assert run("citation", "bogus") == 2  # argparse usage error


def test_module_init_from_subdir_targets_workspace_root(env, capsys):
    run("new")
    project_root = Path.cwd()
    sub = Path("src/deep")
    sub.mkdir(parents=True)
    os.chdir(sub)
    capsys.readouterr()
    assert run("citation", "init") == 0
    assert (project_root / ".nora" / "citation").is_dir()
    assert not Path(".nora").exists()


def test_citation_check_is_lint_alias(env, capsys):
    run("new")
    Path("refs.bib").write_text("@article{a2020x, title={T}, author={A, B}, year={2020}, journal={J}}\n")
    Path("p.tex").write_text("\\cite{a2020x}\n")
    capsys.readouterr()
    assert run("citation", "check") == 0
    out = capsys.readouterr().out
    assert "finding(s)" in out  # lint ran, not the old notice


def test_lit_alias_routes_to_literature(env, capsys):
    assert run("lit") == 0
    assert "Nora literature manager" in capsys.readouterr().out


# --- literature backend (papers.yaml, Stage 3) --------------------------------

APPROVED_DECISIONS = """\
decisions:
  - id: D001
    date: 2026-07-07
    type: proposed_read
    summary: test approval
    status: approved
    resolved: 2026-07-07
    notes: null
  - id: D002
    date: 2026-07-07
    type: proposed_read
    summary: still pending
    status: pending
    resolved: null
    notes: null
"""


def lit_project(capsys):
    """nora new + literature init inside the env fixture's cwd."""
    run("new")
    run("literature", "init")
    Path(".nora/decisions/decisions.yaml").write_text(APPROVED_DECISIONS)
    capsys.readouterr()


def ingest_one(capsys, title="Probing Instruction Adherence in Long Dialogues",
               author="Lee, Carol", year="2022"):
    assert run("literature", "ingest", "--title", title,
               "--author", author, "--year", year) == 0
    out = capsys.readouterr().out
    assert "added:" in out
    return out.split("added: ")[1].split()[0]


def test_literature_init_creates_backend_layout(env, capsys):
    run("new")
    capsys.readouterr()
    assert run("literature", "init") == 0
    out = capsys.readouterr().out
    assert "papers.yaml" in out
    assert Path(".nora/literature/papers.yaml").is_file()
    assert Path(".nora/literature/PAPER_NOTES").is_dir()
    assert "standalone" not in out


def test_literature_init_standalone_note(env, capsys):
    assert run("literature", "init") == 0
    out = capsys.readouterr().out
    assert "no full Nora project state found" in out
    assert "(standalone)" in out


def test_literature_init_idempotent(env, capsys):
    lit_project(capsys)
    assert run("literature", "init") == 0
    assert "already exists" in capsys.readouterr().out


def test_literature_init_refuses_legacy_layout(env, capsys):
    run("new")
    legacy = Path(".nora/literature")
    legacy.mkdir()
    (legacy / "LITERATURE_LOG.md").write_text("# old\n")
    capsys.readouterr()
    assert run("literature", "init") == 1
    out = capsys.readouterr().out
    assert "pre-0.4" in out
    assert "no automatic migration" in out


def test_literature_ingest_manual_and_roundtrip(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)
    assert pid == "lee2022probing"
    text = Path(".nora/literature/papers.yaml").read_text()
    assert 'title: "Probing Instruction Adherence in Long Dialogues"' in text
    assert 'status: "candidate"' in text


def test_literature_ingest_dedup_on_entry(env, capsys):
    lit_project(capsys)
    ingest_one(capsys)
    assert run("literature", "ingest", "--title",
               "Probing  Instruction Adherence in Long Dialogues!") == 0
    out = capsys.readouterr().out
    assert "skipped (already present as lee2022probing)" in out
    assert "0 added" in out


def test_literature_ingest_bibtex(env, capsys, tmp_path):
    lit_project(capsys)
    bib = tmp_path / "refs.bib"
    bib.write_text("""
@article{smith2021deep,
  title = {Deep {Sequence} Models},
  author = {Smith, Alice and Jones, Bob},
  year = {2021},
  journal = {JAIR},
  doi = {https://doi.org/10.1000/XYZ.123}
}
@misc{chen2022drift,
  title = {Instruction Drift},
  author = {Chen, Erin},
  year = {2022},
  eprint = {2205.01234},
  archivePrefix = {arXiv}
}
""")
    assert run("literature", "ingest", "--bibtex", str(bib)) == 0
    out = capsys.readouterr().out
    assert "2 added" in out
    text = Path(".nora/literature/papers.yaml").read_text()
    assert 'doi: "10.1000/xyz.123"' in text          # normalized
    assert 'arxiv: "2205.01234"' in text
    assert 'venue: "arXiv"' in text
    assert 'authors: ["Smith, Alice", "Jones, Bob"]' in text


def test_literature_ingest_titles_file(env, capsys, tmp_path):
    lit_project(capsys)
    titles = tmp_path / "titles.txt"
    titles.write_text("# comment\nA Survey of Conversational Memory\n\nScaling Effects on Context Retention\n")
    assert run("literature", "ingest", "--titles", str(titles)) == 0
    assert "2 added" in capsys.readouterr().out


def test_literature_dedup_fuzzy_review_only(env, capsys):
    lit_project(capsys)
    ingest_one(capsys, title="Instruction Drift in Long Conversations", author="Chen, Erin")
    ingest_one(capsys, title="Instruction Drift in Long Conversation", author="Chen, E.")
    assert run("literature", "dedup") == 0
    out = capsys.readouterr().out
    assert "REVIEW_REQUIRED (near-identical titles)" in out
    assert "DUPLICATE" not in out  # near match is a candidate, not a fact


def test_literature_dedup_flags_trailing_subtitle(env, capsys):
    lit_project(capsys)
    ingest_one(capsys, title="Deep Sequence Models for Dialogue State Tracking", author="Smith, Alice")
    ingest_one(capsys, title="Deep Sequence Models for Dialogue State Tracking (Extended)",
               author="Smith, Alice")
    assert run("literature", "dedup") == 0
    assert "REVIEW_REQUIRED (near-identical titles)" in capsys.readouterr().out


def test_literature_queue_and_mark_free_transitions(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)
    assert run("literature", "mark", pid, "queued") == 0
    assert run("literature", "mark", pid, "reading") == 0
    capsys.readouterr()
    assert run("literature", "queue") == 0
    out = capsys.readouterr().out
    assert "reading:" in out and pid in out


def test_literature_mark_gated_refused_without_decision(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)
    assert run("literature", "mark", pid, "read") == 1
    out = capsys.readouterr().out
    assert "gated status" in out
    assert '"candidate"' not in out  # message, not a stack trace
    text = Path(".nora/literature/papers.yaml").read_text()
    assert 'status: "candidate"' in text  # unchanged


def test_literature_mark_gated_refused_pending_or_missing(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)
    assert run("literature", "mark", pid, "read", "--decision", "D002") == 1
    assert "not 'approved'" in capsys.readouterr().out
    assert run("literature", "mark", pid, "read", "--decision", "D999") == 1
    assert "not found" in capsys.readouterr().out


def test_literature_mark_gated_with_approved_decision(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)
    assert run("literature", "mark", pid, "read", "--decision", "D001") == 0
    assert "candidate -> read (decision D001)" in capsys.readouterr().out
    text = Path(".nora/literature/papers.yaml").read_text()
    assert 'status: "read"' in text
    assert 'decision: "D001"' in text


def test_literature_mark_roles_and_note(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)
    assert run("literature", "mark", pid, "--role", "background",
               "--role", "methodology", "--note", "grounds the probing setup") == 0
    out = capsys.readouterr().out
    assert "roles: [background, methodology]" in out and "note updated" in out
    text = Path(".nora/literature/papers.yaml").read_text()
    assert 'roles: ["background", "methodology"]' in text
    assert 'note: "grounds the probing setup"' in text
    assert 'status: "candidate"' in text  # status untouched


def test_literature_mark_nothing_to_change(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)
    assert run("literature", "mark", pid) == 1
    assert "Nothing to change" in capsys.readouterr().out


def test_literature_coverage_reports_gaps(env, capsys):
    lit_project(capsys)
    ingest_one(capsys)
    capsys.readouterr()
    assert run("literature", "coverage") == 0
    out = capsys.readouterr().out
    assert "Papers: 1 total" in out
    assert "unassigned (no roles yet): 1" in out
    assert "Gaps (roles with no papers)" in out


def test_literature_render_generates_views(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)
    run("literature", "mark", pid, "queued")
    capsys.readouterr()
    assert run("literature", "render") == 0
    queue_md = Path(".nora/literature/READING_QUEUE.md").read_text()
    map_md = Path(".nora/literature/RELATED_WORK_MAP.md").read_text()
    assert queue_md.startswith("<!-- Generated by 'nora literature render'")
    assert pid in queue_md
    assert "(no role assigned yet)" in map_md


def test_literature_doctor_ok_and_gate_violation(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)
    capsys.readouterr()
    assert run("literature", "doctor") == 0
    assert "decision gate consistent" in capsys.readouterr().out

    # simulate a hand-edited promotion bypassing the gate
    text = Path(".nora/literature/papers.yaml").read_text()
    Path(".nora/literature/papers.yaml").write_text(
        text.replace('status: "candidate"', 'status: "cited"'))
    assert run("literature", "doctor") == 1
    out = capsys.readouterr().out
    assert f"WARNING: {pid} is 'cited' (gated) with no decision recorded" in out


def test_literature_doctor_legacy_layout_is_info(env, capsys):
    run("new")
    legacy = Path(".nora/literature")
    legacy.mkdir()
    (legacy / "READING_QUEUE.md").write_text("# old\n")
    capsys.readouterr()
    assert run("literature", "doctor") == 0
    assert "INFO: pre-0.4 literature layout" in capsys.readouterr().out


def test_core_doctor_includes_literature_lines(env, capsys):
    lit_project(capsys)
    assert run("doctor") == 0
    out = capsys.readouterr().out
    assert "OK: papers.yaml parses (0 papers)" in out


def test_literature_unknown_subcommand_exits_2_with_usage(env, capsys):
    assert run("literature", "bogus") == 2  # argparse usage error


# --- literature search (external sources, mocked) ------------------------------

def _mock_single_source(monkeypatch, hits):
    """Make every source except dblp fail; dblp returns `hits`."""
    from nora_cli import sources as src

    def fake_search_all(query, limit, cache_dir, only=None, refresh=False):
        return [("dblp", hits)], ["arxiv: timed out"]

    monkeypatch.setattr(src, "search_all", fake_search_all)


SEARCH_HIT = {
    "title": "Instruction Drift in Long Conversations", "authors": ["Erin Chen"],
    "year": 2023, "venue": "ACL", "doi": "10.1000/drift.1", "arxiv": None,
    "url": "https://example.org", "citations": 41,
}


def test_literature_search_adds_candidates_and_top_view(env, capsys, monkeypatch):
    lit_project(capsys)
    _mock_single_source(monkeypatch, [SEARCH_HIT])
    assert run("literature", "search", "--query", "instruction drift") == 0
    out = capsys.readouterr().out
    assert "WARNING: arxiv: timed out (source skipped)" in out
    assert "added: chen2023instruction" in out
    text = Path(".nora/literature/papers.yaml").read_text()
    assert 'source: "search"' in text
    top = Path(".nora/literature/TOP_CANDIDATES.md").read_text()
    assert top.startswith("<!-- Generated")
    assert "chen2023instruction" in top


def test_literature_search_dedups_against_existing(env, capsys, monkeypatch):
    lit_project(capsys)
    ingest_one(capsys, title="Instruction Drift in Long Conversations", author="Chen, Erin")
    _mock_single_source(monkeypatch, [SEARCH_HIT])
    assert run("literature", "search", "--query", "instruction drift") == 0
    out = capsys.readouterr().out
    assert "0 added, 1 skipped" in out


def test_literature_search_all_sources_failed(env, capsys, monkeypatch):
    lit_project(capsys)
    from nora_cli import sources as src

    def all_fail(query, limit, cache_dir, only=None, refresh=False):
        return [], [f"{n}: unreachable" for n in src.SOURCE_NAMES]

    monkeypatch.setattr(src, "search_all", all_fail)
    assert run("literature", "search", "--query", "anything") == 1
    assert "All sources failed" in capsys.readouterr().out


EXPAND_HIT = {
    "title": "Foundations of Drift", "authors": ["Ada Base"], "year": 2019,
    "venue": "ICML", "doi": "10.1000/found.9", "arxiv": None,
    "url": None, "citations": 200,
}


def _mock_expand(monkeypatch, hits, warnings=None):
    from nora_cli import sources as src

    def fake_expand_all(seed, directions, limit, cache_dir, refresh=False):
        return ([{"seed": seed["id"], "direction": d, "source": "s2", "hits": hits}
                 for d in directions], warnings or [])

    monkeypatch.setattr(src, "expand_all", fake_expand_all)


def seeded_paper(capsys):
    pid = ingest_one(capsys)
    # give the seed a DOI so expand accepts it
    text = Path(".nora/literature/papers.yaml").read_text()
    Path(".nora/literature/papers.yaml").write_text(
        text.replace("doi: null", 'doi: "10.1000/probe.2"', 1))
    return pid


def test_literature_expand_adds_candidates_and_summary(env, capsys, monkeypatch):
    lit_project(capsys)
    pid = seeded_paper(capsys)
    _mock_expand(monkeypatch, [EXPAND_HIT])
    assert run("literature", "expand", "--seed", pid, "--direction", "refs") == 0
    out = capsys.readouterr().out
    assert "added: base2019foundations" in out
    assert "Graph summary:" in out
    text = Path(".nora/literature/papers.yaml").read_text()
    assert 'source: "expand"' in text
    summary = Path(".nora/literature/CITATION_GRAPH_SUMMARY.md").read_text()
    assert summary.startswith("<!-- Generated")


def test_literature_expand_unknown_seed(env, capsys, monkeypatch):
    lit_project(capsys)
    assert run("literature", "expand", "--seed", "nope2020x") == 1
    assert "No paper with id" in capsys.readouterr().out


def test_literature_expand_seed_without_ids_refused(env, capsys):
    lit_project(capsys)
    pid = ingest_one(capsys)  # no DOI, no arXiv
    assert run("literature", "expand", "--seed", pid) == 1
    assert "neither a DOI nor an arXiv id" in capsys.readouterr().out


def test_literature_expand_all_directions_failed(env, capsys, monkeypatch):
    lit_project(capsys)
    pid = seeded_paper(capsys)
    from nora_cli import sources as src
    monkeypatch.setattr(src, "expand_all",
                        lambda *a, **k: ([], ["s2 (refs): down", "openalex (refs): down"]))
    assert run("literature", "expand", "--seed", pid, "--direction", "refs") == 1
    assert "Expansion failed in every direction" in capsys.readouterr().out


def test_literature_coverage_write_report(env, capsys):
    lit_project(capsys)
    ingest_one(capsys)
    capsys.readouterr()
    assert run("literature", "coverage", "--write") == 0
    out = capsys.readouterr().out
    assert "Written:" in out
    report = Path(".nora/literature/COVERAGE_REPORT.md").read_text()
    assert report.startswith("<!-- Generated")
    assert "Papers: 1 total" in report


def test_literature_search_signals_ranking_uses_cache(env, capsys, monkeypatch):
    """TOP_CANDIDATES ranks by cached citation signals: cited paper first."""
    lit_project(capsys)
    import json as _json
    cache = Path(".nora/literature/cache")
    cache.mkdir(parents=True)
    (cache / "openalex-x.json").write_text(_json.dumps([
        {"title": "Highly Cited Paper", "doi": None, "arxiv": None, "citations": 100},
    ]))
    ingest_one(capsys, title="Obscure Paper", author="A, B", year="2024")
    ingest_one(capsys, title="Highly Cited Paper", author="C, D", year="2020")
    assert run("literature", "render") == 0
    top = Path(".nora/literature/TOP_CANDIDATES.md").read_text()
    assert top.index("Highly Cited Paper") < top.index("Obscure Paper")
    assert "citations: 100" in top


# --- citation backend (lint/normalize/fix/keygen, Stage 6+7) -------------------

SEEDED_BIB = """\
@article{smith2021deep,
  title   = {Deep Sequence Models},
  author  = {Alice Smith and Jones, Bob},
  year    = {2021},
  journal = {JAIR},
  doi     = {https://doi-org.proxy.lib.univ.edu/10.1000/xyz.123},
  pages   = {100-115}
}

@article{smith2021deep,
  title = {Deep Sequence Models (Extended)},
  author = {Smith, Alice},
  year = {2021},
  journal = {JAIR}
}

@article{wang_scaling,
  title  = {Scaling Effects on Context Retention},
  author = {Wang, Dan},
  year   = {2023}
}

@misc{rfc9110,
  title = {HTTP Semantics},
  year = {2022}
}

@article{unused2019entry,
  title   = {A Survey of Conversational Memory},
  author  = {Ueda, Hana},
  year    = {2019},
  journal = {ACM Computing Surveys},
  doi     = {10.1000/xyz.123}
}
"""

SEEDED_TEX = r"""\documentclass{article}
\begin{document}
Prior work demonstrates that models forget instructions.
Sequence models are well studied~\cite{smith2021deep}.
Scale matters~\cite{wang_scaling,ghost2024missing}.
A big cluster~\cite{a,b,c,d,e,f}.
An empty one~\cite{}.
Our method outperforms all baselines~\cite{smith2021deep}.
\end{document}
"""


def citation_project(capsys):
    run("new")
    Path("refs.bib").write_text(SEEDED_BIB)
    Path("paper.tex").write_text(SEEDED_TEX)
    capsys.readouterr()


def test_citation_lint_finds_all_seeded_defects(env, capsys):
    citation_project(capsys)
    assert run("citation", "lint") == 0
    out = capsys.readouterr().out
    assert "AUTO_SAFE [duplicate_key] key 'smith2021deep' defined 2 times" in out
    assert "REVIEW_REQUIRED [duplicate_doi] DOI 10.1000/xyz.123 appears on: smith2021deep, unused2019entry" in out
    assert "DO_NOT_APPLY [missing_fields] wang_scaling (@article): missing journal" in out
    assert "BLOCKED [undefined_key] 'ghost2024missing' cited at" in out
    assert "REVIEW_REQUIRED [unused_entry] 'unused2019entry' defined but never cited" in out
    assert "6 keys in one citation" in out
    assert "AUTO_SAFE [malformed_cite] empty citation command" in out
    assert 'heuristic: possible uncited claim' in out          # "demonstrates" sentence
    assert "outperforms" not in out.split("uncited_claim")[0]  # cited claim not flagged
    assert "SAFE_FIX [normalize]" in out
    assert "Nothing was modified" in out


def test_citation_lint_respects_nocite_star(env, capsys):
    citation_project(capsys)
    Path("paper.tex").write_text("\\nocite{*}\n\\cite{smith2021deep}\n")
    assert run("citation", "lint") == 0
    out = capsys.readouterr().out
    assert "unused-entry check skipped" in out
    assert "never cited" not in out


def test_citation_normalize_readonly_diff(env, capsys):
    citation_project(capsys)
    before = Path("refs.bib").read_text()
    assert run("citation", "normalize") == 0
    out = capsys.readouterr().out
    assert "read-only preview" in out
    assert "+  doi     = {https://doi.org/10.1000/xyz.123}" in out
    assert "+  pages   = {100--115}" in out
    assert Path("refs.bib").read_text() == before  # untouched


def test_citation_fix_dry_run_then_apply_with_backup(env, capsys):
    citation_project(capsys)
    before = Path("refs.bib").read_text()
    assert run("citation", "fix") == 0
    assert "Dry run" in capsys.readouterr().out
    assert Path("refs.bib").read_text() == before

    assert run("citation", "fix", "--apply") == 0
    out = capsys.readouterr().out
    assert "backup:" in out
    after = Path("refs.bib").read_text()
    assert "https://doi.org/10.1000/xyz.123" in after
    assert "100--115" in after
    assert "Smith, Alice and Jones, Bob" in after  # 'Alice Smith' reformatted
    backups = list(Path(".nora/citation/backups").iterdir())
    assert len(backups) == 1 and backups[0].read_text() == before


def test_citation_fix_never_touches_tex(env, capsys):
    citation_project(capsys)
    before = Path("paper.tex").read_text()
    run("citation", "fix", "--apply")
    assert Path("paper.tex").read_text() == before


def test_citation_keygen_proposals_only(env, capsys):
    citation_project(capsys)
    before = Path("refs.bib").read_text()
    assert run("citation", "keygen") == 0
    out = capsys.readouterr().out
    assert "wang_scaling -> wang2023scaling" in out
    assert "rfc9110" not in out          # @misc without author: stable product key allowed
    assert "NEVER applied automatically" in out
    assert Path("refs.bib").read_text() == before


def test_citation_lint_write_report(env, capsys):
    citation_project(capsys)
    assert run("citation", "lint", "--write") == 0
    report = Path(".nora/citation/LINT_REPORT.md").read_text()
    assert report.startswith("<!-- Generated")
    assert "duplicate_key" in report


def test_citation_lint_no_sources_found(env, capsys):
    run("new")
    capsys.readouterr()
    assert run("citation", "lint") == 1
    assert "No .bib or .tex files found" in capsys.readouterr().out


# --- update refusal paths ----------------------------------------------------

def test_update_refuses_non_git_nora_home(env, capsys, monkeypatch):
    fake = env / "fake-nora"
    fake.mkdir()
    monkeypatch.setenv("NORA_HOME", str(fake))
    assert run("update") == 1
    assert "not a git repository" in capsys.readouterr().out


def test_update_refuses_dirty_repo(env, capsys, monkeypatch, tmp_path):
    repo = tmp_path / "dirty-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "junk.txt").write_text("dirty\n")
    monkeypatch.setenv("NORA_HOME", str(repo))
    assert run("update") == 1
    assert "uncommitted changes" in capsys.readouterr().out


# --- launcher ----------------------------------------------------------------

def test_bin_nora_launcher_runs(env):
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "nora"), "help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Nora — personal research workflow system" in result.stdout
