# Changelog

All notable changes to this project will be documented in this file.

## [0.7.0] - 2026-07-08

Alpha. This completes the system-centric main line (Stages 0–8): all three
optional modules now pair a deterministic CLI backend with a judgment-only
skill.

### Added

- `nora writing lint [--tex FILE ...] [--write]` — mechanical prose guardrails over `.tex` sources, all read-only (the writing domain has no auto-apply path — quote direction, punctuation, and reference style are context-sensitive enough that every change goes through a human):
  - `\work[...]`-style placeholder commands: `BLOCKED` (exit 1) — agent-misuse artifacts; removed, never formalized into real macros
  - leftover draft markup and markers: `\hl`/`\underline`/`\uline`/`\sout`/`\marginpar`, `TODO`/`FIXME`/`XXX`, and `??` (usually a broken `\ref`)
  - hand-written `Figure~\ref{...}`-style references and hard-coded "Figure 3" numbers — use `\cref` (adding cleveref is itself a user-approval item)
  - straight `"..."` quotes in prose — use `` ``...'' ``; code contexts (verbatim-family environments, `\verb`, `\lstinline`, `\texttt`) are exempt
  - bold/italic overuse (one summary finding per file over a word-count-scaled threshold), overlong sentences (>40 words, explicitly heuristic), and non-ASCII punctuation with suggested ASCII/LaTeX replacements (letters like naïve/Müller are untouched)
  - comments are stripped first; `--write` saves `.nora/writing/LINT_REPORT.md`
- `nora writing init` now also creates `LATEX_CONVENTIONS.md` (project LaTeX conventions, the mechanical ones cross-referenced with lint) and `REVISION_CHECKLIST.md` (pre-submission pass: mechanical CLI steps, then judgment workflows)
- `AGENTS.md` template approval list gains: introducing a new LaTeX package or macro (including formalizing placeholder commands) requires explicit user approval
- Test suite grew from 113 to 120: every check against seeded defects, code-context exemptions, comment stripping, blocking exit code, template completeness

### Changed

- `nora-writing-assistant` skill: `overclaim-check` clears the mechanical layer via `nora writing lint` before the semantic pass; SKILL.md documents the CLI/skill division of labor
- `nora writing` subcommands are parsed with argparse; the last generic module machinery in the CLI (`cmd_module`) is retired — all three modules now own their command trees

## [0.6.0] - 2026-07-08

Alpha. The citation module now follows the same shape as literature:
deterministic checks in the CLI, judgment in the skill.

### Added

- `nora citation lint` (alias: `check`) — all mechanical citation checks, scripted (migrated from the agent prompt): duplicate keys, duplicate DOIs (proxy hosts normalized before comparison), missing required fields per entry type, keys cited but undefined, entries defined but never cited (`\nocite{*}` detected and honored), malformed cite commands, cite clusters over 5 keys, and an explicitly-labeled **heuristic** scan for technical-claim sentences with no citation (fixed verb list; findings are leads, not verdicts). Read-only; `--write` saves `.nora/citation/LINT_REPORT.md`.
- `nora citation normalize` — read-only preview of hygiene normalization: proxy DOI hosts (`doi-org.proxy.*` etc.) → `https://doi.org/`, page ranges `-` → `--`, unambiguous `First Last` author names → `Lastname, Firstname`
- `nora citation fix` — applies those SAFE_FIX normalizations as targeted string substitutions (entries are never reordered or reformatted wholesale). Dry-run by default; `--apply` writes after backing the original up to `.nora/citation/backups/<timestamp>-<name>`. Never touches `.tex`.
- `nora citation keygen` — proposes convention-conforming keys (lowercase first-author surname + year + first substantive title word, same shape as papers.yaml local ids); product/spec-style entries (`@misc`/`@manual`/… without authors) may keep stable product keys. Report-only: key renames touch `.tex`, which the CLI never edits.
- DOI normalization now strips any DOI-ish host (doi.org, dx.doi.org, library proxies) — also improves `nora literature` dedup
- Test suite grew from 105 to 113: all lint checks against seeded defects, `\nocite{*}` path, normalize/fix dry-run/apply/backup, keygen skip rules, `.tex` untouchability

### Changed

- `nora citation check` no longer prints an "agent-driven" notice — it runs `lint`
- `nora-citation-auditor` skill workflows rewritten around the CLI: `check-bibtex`/`check-latex-citations` run `nora citation lint` first and keep for the agent only what scripts can't judge (fuzzy duplicate titles, arXiv/journal pairs, false-positive filtering, review-queue curation); `report` reuses `LINT_REPORT.md` when fresh
- Citation subcommands are parsed with argparse (like `nora literature`); unknown subcommands exit 2 with usage

## [0.5.0] - 2026-07-07

Alpha. First release that talks to external services: `nora literature
search` and `nora literature expand` query public metadata APIs (keyless,
cached, degrading gracefully). Everything else remains fully offline.

### Added

- `nora literature expand --seed <id> [--direction refs|cites|both] [--limit N] [--refresh]` — citation-graph expansion from a tracked paper: what it cites (`refs`) and who cites it (`cites`). Semantic Scholar is the primary graph source (one request per direction); OpenAlex is the automatic fallback (DOI lookup + one batched metadata request). The seed must have a DOI or arXiv id. Hits enter `candidate` state only (`source: "expand"`), deduped like everything else.
- `CITATION_GRAPH_SUMMARY.md` generated view — per-seed neighbor counts and papers reached from multiple seeds (a strong mechanical relevance signal); regenerated by `expand` and `render`
- `nora literature search --query "..." [--source S] [--limit N] [--refresh]` — query five keyless metadata sources in preference order (arXiv → OpenAlex → Semantic Scholar → Crossref → DBLP); hits are merged across sources (same DOI/arXiv id/normalized title = one paper), deduped against existing papers, and enter `candidate` state only (`source: "search"`). Never writes `.bib`/`.tex`.
- Network conduct: stdlib `urllib` only, 10s timeout, at most one request per source per invocation, a failing source degrades to a WARNING and the next is tried (no retries); responses are cached permanently under `.nora/literature/cache/` — a cache hit makes repeated runs instant, deterministic, and offline-capable; `--refresh` bypasses the cache; set `NORA_MAILTO` to join the OpenAlex/Crossref polite pools
- `TOP_CANDIDATES.md` generated view — candidate papers ranked by mechanical signals only (citation count, recency, how many sources agreed, from the search cache); relevance judgment stays with the triage workflow. Regenerated by `search` and `render`.
- `nora literature coverage --write` — also writes the report to `.nora/literature/COVERAGE_REPORT.md`
- Test suite grew from 84 to 105: per-source response parsers, cross-source merge, cache/refresh/degradation paths, S2→OpenAlex expand fallback, search/expand CLI surface (all network mocked)

## [0.4.0] - 2026-07-07

Alpha. This release delivers the literature redesign announced in 0.2.0:
`.nora/literature/` is now backed by structured state, and the old markdown
layout is not migrated automatically.

### Added

- `nora literature` structured backend (Stage 3 of the system-centric redesign): `.nora/literature/papers.yaml` is the single source of truth, written and parsed only by the CLI (strict YAML subset — no YAML library, the parser accepts exactly what the emitter produces, round-trip tested)
- `nora literature ingest` — add candidate papers from `--bibtex FILE`, `--titles FILE` (one per line), or manual flags (`--title/--author/--year/--venue/--doi/--arxiv/--url/--note`); dedups on entry against normalized DOI, arXiv id, and normalized title; assigns stable local ids (first-author surname + year + first substantive title word, matching the planned citation-key convention)
- `nora literature mark <id> [status] [--role ...] [--note ...]` — the only state-transition entry point. Free transitions (`candidate`/`queued`/`reading`) run directly; promotions to `read`/`proposed_cite`/`cited`/`rejected` are **mechanically refused** unless `--decision <id>` references an `approved` entry in `.nora/decisions/decisions.yaml`. The decision gate is now enforced by the CLI, not just by prompt-level convention.
- `nora literature dedup` — reports exact duplicates (DOI/arXiv/normalized title) and near-identical-title candidates (`REVIEW_REQUIRED`); never merges automatically
- `nora literature queue` / `coverage` / `render` — reading-queue listing, role × status coverage report with gap detection, and regeneration of the markdown views (`READING_QUEUE.md`, `RELATED_WORK_MAP.md`) from papers.yaml
- `nora literature doctor` — parses papers.yaml and cross-checks the decision gate: any paper in a gated status must reference an existing, approved decision; violations are reported as WARNINGs (also surfaced by the core `nora doctor`)
- Role taxonomy for papers (`direct_related`, `background`, `platform_spec`, `threat_model`, `methodology`, `evaluation_tool`, `dataset_benchmark`, `defense_mitigation`, `competing_system`, `survey`, `other`)
- Test suite grew from 54 to 83: papers.yaml round-trip (including hostile strings), gate refusal paths, dedup conservatism, BibTeX reader, full CLI surface of the new subcommands

### Changed

- **BREAKING**: the literature module is redesigned around the structured backend. `LITERATURE_LOG.md` is gone; `READING_QUEUE.md` and `RELATED_WORK_MAP.md` are now generated views (do not edit); paper statuses changed from `candidate/screened/to-read/reading/read/cited/rejected/replaced` to `candidate/queued/reading/read/proposed_cite/cited/rejected`; per-paper notes are keyed by local id (`PAPER_NOTES/<id>.md`). There is no automatic migration: pre-0.4 layouts get an `INFO` from doctor and re-init instructions, and `nora literature init` refuses to overwrite them.
- `nora-literature-manager` skill rewritten to drive the CLI: the skill supplies judgment (triage rationale, roles, notes, gap analysis), the CLI owns all state mutations; workflows now route gated promotions through decisions.yaml proposals
- `nora literature` subcommands are parsed with argparse (first argparse subtree in the CLI; other commands keep the original dispatch)

## [0.3.0] - 2026-07-07

Alpha. Heads-up still applies: the `.nora/literature/` layout will be
redesigned in the next iteration (structured `papers.yaml` state with
generated Markdown views).

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
- `nora-project-manager` SKILL.md now lists the other three Nora skills and their modules (previously only the `AGENTS.md` template did), so agents discover them in standalone setups without an `AGENTS.md`

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
