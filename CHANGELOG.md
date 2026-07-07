# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- `nora root` — resolves the active workspace (nearest ancestor with `.nora/`, stopping at `$HOME`/filesystem root) and prints its path plus identity from `config.yaml`. Agents/skills now run this before reading state instead of assuming `./.nora`.
- `nora new` now also creates: `.nora/.gitignore` (containing `*` — Nora state stays out of git by default; sharing happens by explicit export), `.nora/config.yaml` (workspace identity: `project_id` derived from the directory name, `workspace_id`, `workspace_type`, `project_file`), and `.nora/decisions/decisions.yaml` (decision gate: agents append `pending` proposals; only the user approves/rejects)
- `nora doctor` workspace layout checks: reports the resolved workspace and its identity; nested `.nora` inside the workspace = `WARNING` (real conflict); sibling workspaces next to it = `INFO` (not a conflict; scan skipped when the parent is `$HOME`); missing `config.yaml`/`.gitignore`/`decisions/` in pre-0.3 workspaces = `INFO`, never an error
- `AGENTS.md` template: agent operating rules (resolve workspace via `nora root`, prefer CLI for state changes, one workspace at a time, never create `.nora/` by hand), decision-gate protocol, and an explicit list of actions requiring user approval
- Chinese entry-point README (`README.zh-CN.md`) — a thin introduction linking to the full English README

### Changed

- `nora new` refuses to run inside an existing workspace (nested `.nora` directories conflict); exits 1 with an explanation
- `nora <module> init` and `nora <module> doctor` now resolve the workspace root first: running them from a subdirectory targets the workspace's `.nora/` instead of creating a nested one
- `nora doctor` project checks now work from any subdirectory of a workspace
- `nora-project-manager` skill startup protocol and precondition now start with `nora root` instead of checking `./.nora`

## [0.2.0] - 2026-07-06

Alpha. Heads-up: the `.nora/literature/` layout will be redesigned in an
upcoming version (structured `papers.yaml` state with generated Markdown
views).

### Added

- pytest test suite (`tests/test_cli.py`, 41 tests) covering the full CLI surface: doctor three tiers, init idempotency, install-skills symlinks/aliases, module init/doctor including failure paths, update refusal paths
- `nora lit` accepted as a short alias for `nora literature`
- `nora-citation-auditor` skill (short alias `/nora-citation`) with four workflows: `check-bibtex`, `check-latex-citations`, `report`, `audit-claim-support` — mechanical/semi-mechanical BibTeX and LaTeX citation auditing (duplicate keys/DOIs, missing fields, missing/unused citations, conservative fuzzy duplicate-title and arXiv/journal-duplicate candidates), plus a bounded human-in-the-loop claim-support review pass (`SUPPORTED`/`PARTIALLY_SUPPORTED`/`WEAK_OR_INDIRECT`/`UNSUPPORTED`/`REVIEW_REQUIRED`/`BLOCKED`). Never edits `.bib`/`.tex` files, never claims full scientific verification; uncertain findings go into a review queue instead.
- `.nora/citation/` project-local output convention: `CITATION_AUDIT_REPORT.md`, `CITATION_REVIEW_QUEUE.yaml`, `CLAIM_SUPPORT_AUDIT.md`
- `nora-literature-manager` skill (short alias `/nora-literature`) with five workflows: `search`, `triage`, `reading-queue`, `paper-note`, `related-work-map` — literature workflow management (not a search API client): works with web/search tools if available, or with manually supplied titles/DOIs/BibTeX/PDFs/notes if not. Distinguishes `candidate`/`screened`/`to-read`/`reading`/`read`/`cited`/`rejected`/`replaced` papers and records why each one matters.
- `.nora/literature/` project-local output convention: `LITERATURE_LOG.md`, `READING_QUEUE.md`, `RELATED_WORK_MAP.md`, `PAPER_NOTES/`
- `nora-writing-assistant` skill (short alias `/nora-writing`) with five workflows: `polish`, `restructure`, `overclaim-check`, `paragraph-diagnosis`, `style-profile` — academic writing help that preserves technical meaning, citation placement, and authorial caution; never invents claims/results/citations/mechanisms/novelty. Supports project-aware mode (reads `.nora/` context) and standalone mode (no `.nora/` required, states this explicitly).
- `.nora/writing/` project-local output convention: `WRITING_STYLE.md`, `STYLE_NOTES.md`, `PHRASE_BANK.md`
- `nora literature init|doctor` and `nora writing init|doctor` CLI subcommands, matching the `nora citation` pattern; each `<module> doctor` fails clearly if its `.nora/<module>/` directory is missing and suggests the matching `init`
- `nora citation` CLI subcommand: `init`, `check`, `doctor`. `nora citation init` works standalone (without a full `.nora/` project scaffold) and says so explicitly when no `PROJECT_STATE.yaml` is found.

### Changed

- CLI rewritten from bash to Python (`src/nora_cli/`, Python 3.8+ stdlib only, verified by running the test suite under 3.8); the `bin/nora` launcher refuses to run on older interpreters with a clear error instead of a traceback; `bin/nora` is now a thin launcher. Output and exit codes verified byte-identical against the bash version across the full command matrix
- `nora init` renamed to `nora new` (old name kept as an alias) to match the `new` workflow terminology and distinguish core project initialization from optional `nora <module> init` commands
- `nora doctor` rewritten to distinguish three tiers: global Nora installation (home dir, required skills present with `SKILL.md`, skill symlinks not broken) — `ERROR` on failure; core project state (only checked when `.nora/` exists) — `ERROR` on missing file; optional modules (citation/literature/writing) — `INFO` if not initialized, `WARNING` if initialized but incomplete. Only `ERROR` causes a non-zero exit; an uninitialized optional module no longer fails `nora doctor`.
- `nora install-skill` renamed to `nora install-skills` (old name kept as an alias); now installs all four skills plus aliases `nora`, `nora-citation`, `nora-literature`, `nora-writing`
- `AGENTS.md` template now lists all four skills and when to use each, and warns not to assume a module is initialized just because the project uses Nora
- README.md restructured with an alpha feature overview, a quick-start sequence, explicit optional-module documentation, standalone-usage examples, and a non-goals list

### Removed

- Empty `scripts/` and `shared/` directories: deterministic logic lives in the Python package after the migration

## [0.1.0] - 2026-07-02

### Added

- `nora` CLI: `init`, `doctor`, `install-skill`, `update`, `help`
- `nora-project-manager` skill (short alias `/nora`) with four workflows: `new`, `reboot`, `session-update`, `sync-agents`
- `.nora/` project-state convention: `PROJECT_STATE.yaml`, `CONTEXT_BRIEF.md`, `SESSION_LOG.md`, `NEXT_ACTIONS.md`, `OPEN_LOOPS.md`
- `AGENTS.md` scaffolded into each initialized project, pointing any agent at the Nora startup protocol and human-review policy
- Skill installable into both Claude Code (`~/.claude/skills`) and Codex (`~/.codex/skills`) as symlinks, with a short `/nora` alias alongside the full skill name
- `nora update` detects changes to the `AGENTS.md` template and prompts to run `/nora sync-agents` in affected projects
- Default (argument-less, or unrecognized-argument) `/nora` invocation loads project context and responds conversationally instead of guessing a workflow
