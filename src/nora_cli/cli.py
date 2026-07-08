"""Nora CLI. Behavioral parity with the original bash bin/nora (0.1.0).

Deterministic scaffolding only: init/doctor/install/update. Agent-driven
work lives in the skills; this module must never write into .bib/.tex or
agent-owned state files.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILLS = [
    "nora-project-manager",
    "nora-citation-auditor",
    "nora-literature-manager",
    "nora-writing-assistant",
]

SKILL_ALIASES = {
    "nora": "nora-project-manager",
    "nora-citation": "nora-citation-auditor",
    "nora-literature": "nora-literature-manager",
    "nora-writing": "nora-writing-assistant",
}

CORE_FILES = [
    "AGENTS.md",
    ".nora/PROJECT_STATE.yaml",
    ".nora/CONTEXT_BRIEF.md",
    ".nora/SESSION_LOG.md",
    ".nora/NEXT_ACTIONS.md",
    ".nora/OPEN_LOOPS.md",
]

MODULES = {
    "citation": {
        "files": [
            ".nora/citation/CITATION_AUDIT_REPORT.md",
            ".nora/citation/CITATION_REVIEW_QUEUE.yaml",
            ".nora/citation/CLAIM_SUPPORT_AUDIT.md",
        ],
        "dirs": [],
        "state_name": "Citation audit",
        "doctor_intro": "Checking citation audit state...",
        "doctor_ok": "Citation audit state looks OK.",
        "doctor_incomplete": "Citation module is initialized but incomplete.",
    },
    # literature is handled by nora_cli.literature (papers.yaml backend);
    # it is intentionally absent here.
    "writing": {
        "files": [
            ".nora/writing/WRITING_STYLE.md",
            ".nora/writing/STYLE_NOTES.md",
            ".nora/writing/PHRASE_BANK.md",
            ".nora/writing/LATEX_CONVENTIONS.md",
            ".nora/writing/REVISION_CHECKLIST.md",
        ],
        "dirs": [],
        "state_name": "Writing",
        "doctor_intro": "Checking writing state...",
        "doctor_ok": "Writing state looks OK.",
        "doctor_incomplete": "Writing module is initialized but incomplete.",
    },
}

HELP_TEXT = """\
Nora — personal research workflow system

Core commands:
  nora new             Initialize core Nora project state in the current project (alias: nora init)
  nora root            Resolve the current workspace (nearest ancestor with .nora/) and its identity
  nora doctor          Check global install + core project state + optional module status
  nora install-skills  Symlink all Nora skills into Claude Code / Codex (alias: nora install-skill)
  nora update          Pull the latest nora CLI and skills from git

Optional module commands (each module is off until explicitly enabled):
  nora citation <subcommand>         Citation hygiene backend: lint/normalize/fix/keygen over .bib/.tex (run 'nora citation help')
  nora literature <subcommand>       Literature backend: papers.yaml state, ingest/dedup/queue/mark/coverage/render (run 'nora literature help')
  nora writing <subcommand>          Writing guardrails: lint over .tex prose (run 'nora writing help')"""

def nora_home() -> Path:
    return Path(os.environ.get("NORA_HOME") or Path.home() / "nora")


def agent_bases() -> list[Path]:
    return [Path.home() / ".claude", Path.home() / ".codex"]


def find_workspace_root(start: Path | None = None) -> Path | None:
    """Nearest ancestor (including start) containing .nora/.

    Stops at $HOME when start is inside it (a stray .nora above the home
    directory must not capture everything), otherwise at the filesystem root.
    """
    cur = (start or Path.cwd()).resolve()
    home = Path.home().resolve()
    while True:
        if (cur / ".nora").is_dir():
            return cur
        if cur == home or cur.parent == cur:
            return None
        cur = cur.parent


def read_workspace_config(root: Path) -> dict:
    """Parse the flat key: value pairs of .nora/config.yaml (stdlib only)."""
    config = {}
    path = root / ".nora" / "config.yaml"
    if not path.is_file():
        return config
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value and value != "null":
            config[key.strip()] = value
    return config


def _identity_line(config: dict) -> str | None:
    if "workspace_id" not in config:
        return None
    line = f"workspace: {config['workspace_id']}"
    if "workspace_type" in config:
        line += f" (type: {config['workspace_type']})"
    if "project_id" in config:
        line += f" project: {config['project_id']}"
    return line


def find_nested_nora(root: Path, max_depth: int = 3) -> list[Path]:
    """Other .nora dirs strictly inside the workspace subtree (conflicts)."""
    skip = {".git", ".nora", "node_modules", "__pycache__", ".venv", "venv"}
    nested = []

    def walk(d: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = sorted(p for p in d.iterdir() if p.is_dir())
        except OSError:
            return
        for child in children:
            if child.name == ".nora" and d != root:
                nested.append(child)
            if child.name not in skip and not child.is_symlink():
                walk(child, depth + 1)

    walk(root, 1)
    return nested


def find_sibling_nora(root: Path) -> list[Path]:
    """Workspaces next to this one (one-level heuristic; not conflicts).

    Skipped when the parent is $HOME: everything under the home directory
    would count as a sibling, which is noise, not project structure.
    """
    siblings = []
    if root.parent == Path.home().resolve():
        return siblings
    try:
        children = sorted(p for p in root.parent.iterdir() if p.is_dir())
    except OSError:
        return siblings
    for child in children:
        if child != root and (child / ".nora").is_dir():
            siblings.append(child / ".nora")
    return siblings


def cmd_root() -> int:
    root = find_workspace_root()
    if root is None:
        print(f"No Nora workspace found (no .nora/ in {Path.cwd()} or its ancestors).")
        return 1
    print(root)
    identity = _identity_line(read_workspace_config(root))
    if identity:
        print(identity)
    return 0


def _symlink_force(src: Path, dest: Path) -> None:
    if dest.is_symlink() or dest.exists():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    dest.symlink_to(src)


def cmd_help() -> int:
    print(HELP_TEXT)
    return 0


def cmd_update() -> int:
    home = nora_home()

    if not (home / ".git").is_dir():
        print(f"NORA_HOME is not a git repository: {home}")
        return 1

    status = subprocess.run(
        ["git", "-C", str(home), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    if status.stdout.strip():
        print(f"NORA_HOME has uncommitted changes, refusing to update: {home}")
        return 1

    agents_template = "skills/nora-project-manager/templates/AGENTS.md"

    def template_head() -> str:
        return subprocess.run(
            ["git", "-C", str(home), "log", "-1", "--format=%H", "--", agents_template],
            capture_output=True, text=True, check=True,
        ).stdout.strip()

    before = template_head()
    pull = subprocess.run(["git", "-C", str(home), "pull", "--ff-only"])
    if pull.returncode != 0:
        return pull.returncode
    after = template_head()

    if before != after:
        print(f"Note: {agents_template} changed.")
        print("Run '/nora sync-agents' in your agent session for any already-initialized project you want to sync.")
    return 0


def cmd_install_skills() -> int:
    home = nora_home()
    installed_any = False

    for skill in SKILLS:
        src = home / "skills" / skill

        if not src.is_dir():
            print(f"Skill source not found: {src}")
            continue

        for base, label in [(agent_bases()[0], "Claude Code"), (agent_bases()[1], "Codex")]:
            if base.is_dir():
                skills_dir = base / "skills"
                skills_dir.mkdir(parents=True, exist_ok=True)
                _symlink_force(src, skills_dir / skill)
                print(f"Installed for {label}: {skills_dir / skill}")
                installed_any = True

    for base in agent_bases():
        if base.is_dir():
            for alias, skill in SKILL_ALIASES.items():
                _symlink_force(home / "skills" / skill, base / "skills" / alias)
            print(f"Aliases in {base / 'skills'}: nora, nora-citation, nora-literature, nora-writing")

    if not installed_any:
        print("No ~/.claude or ~/.codex directory found. Nothing installed.")
        return 1

    print("Restart your agent session to pick up the new skill(s).")
    return 0


def _slug(name: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in name.lower())
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "project"


def cmd_new() -> int:
    if Path(".nora").is_dir():
        print("Nora state already exists: .nora/")
        return 0

    enclosing = find_workspace_root()
    if enclosing is not None:
        print(f"Refusing to create nested Nora state: an enclosing workspace exists at {enclosing}")
        print("Nested .nora directories conflict (two state roots would claim the same files).")
        print("Work in that workspace, or create the new one outside its tree.")
        return 1

    home = nora_home()
    templates = home / "skills" / "nora-project-manager" / "templates"

    Path(".nora").mkdir(parents=True)
    shutil.copy(templates / "AGENTS.md", Path("AGENTS.md"))
    for item in (templates / ".nora").iterdir():
        # Stored as "gitignore" so its `*` doesn't hide template files from this repo's git.
        name = ".gitignore" if item.name == "gitignore" else item.name
        if item.is_file():
            shutil.copy(item, Path(".nora") / name)
        else:
            shutil.copytree(item, Path(".nora") / name)

    project_id = _slug(Path.cwd().name)
    (Path(".nora") / "config.yaml").write_text(
        "# Nora workspace identity. Keep keys flat (parsed without a YAML library).\n"
        f"project_id: {project_id}\n"
        "workspace_id: main\n"
        "workspace_type: mixed  # code | paper | artifact | experiment | mixed\n"
        "project_file: null  # relative path to a .nora-project.yaml registry, once one exists\n"
    )

    print("Initialized core Nora project state in:")
    print(f"  {Path.cwd() / '.nora'}")
    print()
    print("Workspace identity written to .nora/config.yaml (edit project_id/workspace_id/workspace_type to taste).")
    print("Nora state stays local: .nora/.gitignore ignores everything under .nora/.")
    print()
    print("Optional modules are not enabled. Run any of the following if needed:")
    print("  nora citation init")
    print("  nora literature init")
    print("  nora writing init")
    return 0


def cmd_doctor() -> int:
    home = nora_home()
    error = False

    print("=== Global Nora installation ===")

    if home.is_dir():
        print(f"OK: NORA_HOME exists ({home})")
    else:
        print(f"ERROR: NORA_HOME not found ({home})")
        error = True

    for skill in SKILLS:
        skill_dir = home / "skills" / skill
        if skill_dir.is_dir():
            print(f"OK: skill present: {skill}")
            if (skill_dir / "SKILL.md").is_file():
                print(f"OK: {skill}/SKILL.md")
            else:
                print(f"ERROR: {skill}/SKILL.md missing")
                error = True
        else:
            print(f"ERROR: skill missing: {skill_dir}")
            error = True

    for base in agent_bases():
        if base.is_dir():
            for skill in SKILLS:
                link = base / "skills" / skill
                if link.is_symlink():
                    if link.exists():
                        print(f"OK: {link}")
                    else:
                        print(f"ERROR: broken symlink: {link}")
                        error = True
                elif link.exists():
                    print(f"OK: {link} (not a symlink)")
                else:
                    print(f"INFO: not installed: {link} (run 'nora install-skills')")

    print()
    print("=== Project core state ===")

    root = find_workspace_root()
    if root is not None:
        print(f"Workspace: {root}")
        identity = _identity_line(read_workspace_config(root))
        if identity:
            print(f"Identity: {identity}")
        else:
            print("INFO: no .nora/config.yaml (legacy workspace; add one to record workspace identity)")

        for f in CORE_FILES:
            if (root / f).is_file():
                print(f"OK: {f}")
            else:
                print(f"ERROR: missing: {f}")
                error = True

        if not (root / ".nora" / ".gitignore").is_file():
            print("INFO: no .nora/.gitignore (Nora state is meant to stay out of git; add one containing '*')")
        if not (root / ".nora" / "decisions" / "decisions.yaml").is_file():
            print("INFO: no .nora/decisions/decisions.yaml (decision gate not set up; copy it from the template if wanted)")

        for nested in find_nested_nora(root):
            print(f"WARNING: nested .nora inside this workspace: {nested} (two state roots claim the same files)")
        for sibling in find_sibling_nora(root):
            print(f"INFO: sibling workspace: {sibling} (not a conflict)")

        print()
        print("=== Optional modules ===")

        for name in ["citation", "literature", "writing"]:
            mod_dir = root / ".nora" / name
            if not mod_dir.is_dir():
                print(f"INFO: {name} module not initialized. Run 'nora {name} init' if needed.")
                continue
            if name == "literature":
                from . import literature as lit_mod
                for line in lit_mod.doctor_lines(root)[0]:
                    print(line)
                continue
            mod = MODULES[name]
            for f in mod["files"]:
                if (root / f).is_file():
                    print(f"OK: {f}")
                else:
                    print(f"WARNING: {f} missing ({name} module initialized but incomplete)")
            for d in mod["dirs"]:
                if (root / d).is_dir():
                    print(f"OK: {d}/")
                else:
                    print(f"WARNING: {d}/ missing ({name} module initialized but incomplete)")
    else:
        print("Not in a Nora-managed workspace (no .nora/ in the current directory or its ancestors).")
        print("Skipping project core state and optional module checks.")

    print()
    if not error:
        print("Nora doctor: no errors. See INFO/WARNING lines above for optional-module status.")
        return 0
    print("Nora doctor found errors. See ERROR lines above.")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    cmd = args[0] if args else "help"

    if cmd == "help":
        return cmd_help()
    if cmd == "update":
        return cmd_update()
    if cmd in ("install-skill", "install-skills"):
        return cmd_install_skills()
    if cmd in ("new", "init"):
        return cmd_new()
    if cmd == "root":
        return cmd_root()
    if cmd == "doctor":
        return cmd_doctor()
    if cmd in ("literature", "lit"):
        from . import literature as lit_mod
        return lit_mod.cmd_literature(args[1:])
    if cmd == "citation":
        from . import citation as cit_mod
        return cit_mod.cmd_citation(args[1:])
    if cmd == "writing":
        from . import writing as wri_mod
        return wri_mod.cmd_writing(args[1:])

    print(f"Unknown command: {cmd}")
    print("Run: nora help")
    return 1


if __name__ == "__main__":
    sys.exit(main())
