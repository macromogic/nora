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

MODULE_FILES = {
    "citation": ["CITATION_AUDIT_REPORT.md", "CITATION_REVIEW_QUEUE.yaml",
                 "CLAIM_SUPPORT_AUDIT.md"],
    "literature": ["LITERATURE_LOG.md", "READING_QUEUE.md", "RELATED_WORK_MAP.md"],
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
    if mod == "literature":
        assert Path(".nora/literature/PAPER_NOTES/.gitkeep").is_file()


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


@pytest.mark.parametrize("mod", MODULE_FILES)
def test_module_help_on_unknown_subcommand(env, capsys, mod):
    assert run(mod) == 0
    help_out = capsys.readouterr().out
    assert f"nora {mod} init" in help_out
    assert run(mod, "bogus") == 0
    assert capsys.readouterr().out == help_out


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


def test_citation_check_is_agent_driven_notice(env, capsys):
    assert run("citation", "check") == 0
    assert "agent-driven" in capsys.readouterr().out


def test_lit_alias_routes_to_literature(env, capsys):
    assert run("lit") == 0
    assert "Nora literature manager" in capsys.readouterr().out


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
