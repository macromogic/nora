# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- `nora-citation-auditor` skill (short alias `/nora-citation`) with four workflows: `check-bibtex`, `check-latex-citations`, `report`, `audit-claim-support` — mechanical/semi-mechanical BibTeX and LaTeX citation auditing (duplicate keys/DOIs, missing fields, missing/unused citations, conservative fuzzy duplicate-title and arXiv/journal-duplicate candidates), plus a bounded human-in-the-loop claim-support review pass (`SUPPORTED`/`PARTIALLY_SUPPORTED`/`WEAK_OR_INDIRECT`/`UNSUPPORTED`/`REVIEW_REQUIRED`/`BLOCKED`). Never edits `.bib`/`.tex` files, never claims full scientific verification; uncertain findings go into a review queue instead.
- `.nora/citation/` project-local output convention: `CITATION_AUDIT_REPORT.md`, `CITATION_REVIEW_QUEUE.yaml`, `CLAIM_SUPPORT_AUDIT.md`
- `nora-literature-manager` skill (short alias `/nora-literature`) with five workflows: `search`, `triage`, `reading-queue`, `paper-note`, `related-work-map` — literature workflow management (not a search API client): works with web/search tools if available, or with manually supplied titles/DOIs/BibTeX/PDFs/notes if not. Distinguishes `candidate`/`screened`/`to-read`/`reading`/`read`/`cited`/`rejected`/`replaced` papers and records why each one matters.
- `.nora/literature/` project-local output convention: `LITERATURE_LOG.md`, `READING_QUEUE.md`, `RELATED_WORK_MAP.md`, `PAPER_NOTES/`
- `nora-writing-assistant` skill (short alias `/nora-writing`) with five workflows: `polish`, `restructure`, `overclaim-check`, `paragraph-diagnosis`, `style-profile` — academic writing help that preserves technical meaning, citation placement, and authorial caution; never invents claims/results/citations/mechanisms/novelty. Supports project-aware mode (reads `.nora/` context) and standalone mode (no `.nora/` required, states this explicitly).
- `.nora/writing/` project-local output convention: `WRITING_STYLE.md`, `STYLE_NOTES.md`, `PHRASE_BANK.md`
- `nora literature init|doctor` and `nora writing init|doctor` CLI subcommands, matching the `nora citation` pattern; each `<module> doctor` fails clearly if its `.nora/<module>/` directory is missing and suggests the matching `init`
- `nora citation` CLI subcommand: `init`, `check`, `doctor`. `nora citation init` works standalone (without a full `.nora/` project scaffold) and says so explicitly when no `PROJECT_STATE.yaml` is found.

### Changed

- `nora init` renamed to `nora new` (old name kept as an alias) to match the `new` workflow terminology and distinguish core project initialization from optional `nora <module> init` commands
- `nora doctor` rewritten to distinguish three tiers: global Nora installation (home dir, required skills present with `SKILL.md`, skill symlinks not broken) — `ERROR` on failure; core project state (only checked when `.nora/` exists) — `ERROR` on missing file; optional modules (citation/literature/writing) — `INFO` if not initialized, `WARNING` if initialized but incomplete. Only `ERROR` causes a non-zero exit; an uninitialized optional module no longer fails `nora doctor`.
- `nora install-skill` renamed to `nora install-skills` (old name kept as an alias); now installs all four skills plus aliases `nora`, `nora-citation`, `nora-literature`, `nora-writing`
- `AGENTS.md` template now lists all four skills and when to use each, and warns not to assume a module is initialized just because the project uses Nora
- README.md restructured with an alpha feature overview, a quick-start sequence, explicit optional-module documentation, standalone-usage examples, and a non-goals list

## [0.1.0] - 2026-07-02

### Added

- `nora` CLI: `init`, `doctor`, `install-skill`, `update`, `help`
- `nora-project-manager` skill (short alias `/nora`) with four workflows: `new`, `reboot`, `session-update`, `sync-agents`
- `.nora/` project-state convention: `PROJECT_STATE.yaml`, `CONTEXT_BRIEF.md`, `SESSION_LOG.md`, `NEXT_ACTIONS.md`, `OPEN_LOOPS.md`
- `AGENTS.md` scaffolded into each initialized project, pointing any agent at the Nora startup protocol and human-review policy
- Skill installable into both Claude Code (`~/.claude/skills`) and Codex (`~/.codex/skills`) as symlinks, with a short `/nora` alias alongside the full skill name
- `nora update` detects changes to the `AGENTS.md` template and prompts to run `/nora sync-agents` in affected projects
- Default (argument-less, or unrecognized-argument) `/nora` invocation loads project context and responds conversationally instead of guessing a workflow
