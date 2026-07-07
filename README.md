# Nora

[中文入口 →](README.zh-CN.md)

Nora is a personal research workflow system for maintaining project context, recovering stale research projects, and tracking progress across agent sessions — plus a set of optional modules for citation auditing, literature tracking, and writing assistance.

**Status: alpha.** Core project-state management, citation auditing, literature tracking, and writing assistance all exist and are usable; none have seen extensive real-world mileage yet (see Current limitations below).

## Core ideas

- Global Nora skills teach agents how to work; project-local state lives in `.nora/`.
- `nora-project-manager` owns project state, lifecycle, and session continuity. It is the only required skill.
- Citation, literature, and writing support are separate, optional modules — each its own skill, each with its own `.nora/<module>/` state, none required to use Nora at all.
- Agents should read project state at session start and propose (not silently apply) state updates at session end.
- Prefer Markdown/YAML files over databases; prefer review queues and proposed updates over silent mutation.
- Human review is required before overwriting important project or module state. Agent proposals that change research state go through the decision gate (`.nora/decisions/decisions.yaml`): agents append `pending` entries; only the user approves.
- Nora state stays local by default: `nora new` writes a `.nora/.gitignore` that keeps everything under `.nora/` out of git. Sharing happens by explicit export, not by committing state.
- One directory = one workspace, resolved like git resolves `.git`: the nearest ancestor with `.nora/` wins (`nora root`). Sibling workspaces of the same research project are normal, not conflicts; nested ones are conflicts.

## Alpha feature overview

- **Project management** (`nora-project-manager`) — bootstrap a new project, recover a stale one, summarize a session and propose state updates, and keep `AGENTS.md` in sync with the current template. This is the core of Nora; everything else is optional on top of it.
- **Citation auditing** (`nora-citation-auditor`) — mechanical BibTeX/LaTeX hygiene checks (duplicate keys/DOIs, missing fields, missing/unused citations, fuzzy duplicate-title and arXiv/journal-duplicate candidates), plus a bounded, human-in-the-loop first pass at whether a citation appears to support a specific claim. Never edits `.bib`/`.tex`, never claims full scientific verification.
- **Literature management** (`nora-literature-manager`) — search (if tools are available) or manually organize candidate papers, triage them, track a reading queue, take structured per-paper notes, and maintain a related-work map. Distinguishes candidates from papers actually read or cited.
- **Writing assistance** (`nora-writing-assistant`) — polish, restructure, and overclaim-check manuscript prose while preserving technical meaning and citation placement; diagnose why a paragraph isn't working; set up a project's writing style and phrase bank. Works with or without a Nora project.
- **Current limitations** — no figure-generation tooling, no Zotero (or any external) write-back, no database backend, no background daemon or web dashboard, no full paper generation, no automatic manuscript rewriting, no automatic BibTeX edits, and no unsupervised claim verification.

## Quick start

Requires Python 3.8+ (standard library only — no packages to install).

```bash
nora install-skills   # symlink all four skills into Claude Code / Codex
nora new               # scaffold core .nora/ project state + AGENTS.md
nora doctor            # check global install + core project state + optional modules

# enable whichever optional modules you actually need — none are required:
nora citation init
nora literature init
nora writing init
```

Modules are opt-in. `nora new` only creates the core project state; `nora doctor` will not fail just because citation/literature/writing modules are absent — it prints an `INFO` line for each uninitialized module and suggests the relevant `nora <module> init`.

## CLI

`bin/nora` provides:

- `nora new` (alias `nora init`) — scaffold core `.nora/` project state and `AGENTS.md` in the current directory: the five core state files plus `.nora/.gitignore` (state stays out of git), `.nora/config.yaml` (workspace identity: `project_id`/`workspace_id`/`workspace_type`), and the `.nora/decisions/` decision gate. Does not touch any optional module. Refuses to run inside an existing workspace (nested `.nora` directories conflict).
- `nora root` — resolve the active workspace: the nearest ancestor directory (including the current one) containing `.nora/`, stopping at `$HOME`/filesystem root. Prints the workspace path and, when `config.yaml` exists, its identity. Agents run this before reading state instead of assuming `./.nora`.
- `nora doctor` — global install check (Nora home, required skills present with `SKILL.md`, skill symlinks not broken) + core project-state check against the resolved workspace (`ERROR` if a core file is missing) + workspace layout (nested `.nora` inside the workspace = `WARNING`; sibling workspaces next to it = `INFO`, not a conflict; missing `config.yaml`/`.gitignore`/`decisions/` in older workspaces = `INFO`) + optional-module status (`INFO` if not initialized, `WARNING` if initialized but incomplete). Exits non-zero only on `ERROR`.
- `nora install-skills` (alias `nora install-skill`) — symlink all four skills (`nora-project-manager`, `nora-citation-auditor`, `nora-literature-manager`, `nora-writing-assistant`) into Claude Code (`~/.claude/skills`) and Codex (`~/.codex/skills`), with short aliases `nora`, `nora-citation`, `nora-literature`, `nora-writing`.
- `nora update` — pull the latest Nora CLI and skills from git (refuses if `$NORA_HOME` has uncommitted changes); if the `AGENTS.md` template changed, prints a note to run `/nora sync-agents` in projects you want to sync.
- `nora citation init|check|doctor` — citation/BibTeX audit module; see `nora-citation-auditor` below.
- `nora literature init|doctor` — literature tracking module; see `nora-literature-manager` below. Otherwise skill-driven (`/nora-literature-manager <workflow>`).
- `nora writing init|doctor` — writing assistant module; see `nora-writing-assistant` below. Otherwise skill-driven (`/nora-writing-assistant <workflow>`).

Each `<module> doctor` fails with a clear error and an init suggestion if that module's `.nora/<module>/` directory doesn't exist — unlike the default `nora doctor`, which only warns.

## Skill: `nora-project-manager` (alias `/nora`)

Four workflows:

- `new` — bootstrap a brand-new project with no prior state
- `reboot` — recover a stale or long-inactive project
- `session-update` — summarize the current session and propose project state updates
- `sync-agents` — check the project's `AGENTS.md` against the current template and propose an update

Invoke with `/nora <workflow>` (e.g. `/nora reboot`). A bare `/nora`, or one followed by text that doesn't match a workflow name, loads the project's `.nora/` context and continues the conversation normally — it does not guess and trigger one of the four workflows on its own.

## Skill: `nora-citation-auditor` (alias `/nora-citation`)

Mechanical and semi-mechanical BibTeX/LaTeX citation auditing, plus a bounded claim-support review pass. It never edits `.bib` or `.tex` files, never renames keys, and never claims to fully verify scientific correctness.

Four workflows:

- `check-bibtex` — duplicate keys, duplicate DOIs, missing important fields, possible duplicate titles (conservative fuzzy match), possible arXiv/journal duplicate candidates
- `check-latex-citations` — citation keys used in `.tex` but missing from `.bib`, and `.bib` entries never cited
- `report` — consolidate the above into `.nora/citation/CITATION_AUDIT_REPORT.md` and `.nora/citation/CITATION_REVIEW_QUEUE.yaml`
- `audit-claim-support` — for a specific claim–citation pair, a bounded read of the cited source's available material, classified as `SUPPORTED` / `PARTIALLY_SUPPORTED` / `WEAK_OR_INDIRECT` / `UNSUPPORTED` / `REVIEW_REQUIRED` / `BLOCKED`, written to `.nora/citation/CLAIM_SUPPORT_AUDIT.md`. This is a reading aid for a human reviewer, not automated verification.

Invoke with `/nora-citation-auditor <workflow>` or the short alias `/nora-citation <workflow>` (e.g. `/nora-citation check-bibtex`).

Unlike `nora-project-manager`, this skill does not require `.nora/` to exist. If it's missing, the skill runs in standalone citation-audit mode and says so explicitly, writing output only to `.nora/citation/`. If a full Nora project exists, it also reads `.nora/PROJECT_STATE.yaml` for context and may propose (never silently apply) a pointer in `.nora/OPEN_LOOPS.md`.

Mechanical findings are tagged `AUTO_SAFE`, `REVIEW_REQUIRED`, `BLOCKED`, or `DO_NOT_APPLY` — these describe confidence in the finding, not permission to auto-fix; nothing is ever applied automatically. `audit-claim-support` uses its own label set (above) since "how confident is this mechanical finding" and "does this source support this claim" are different kinds of judgment.

## Skill: `nora-literature-manager` (alias `/nora-literature`)

Search, triage, track, and organize research literature — literature *workflow management*, not a full search API client.

Five workflows:

- `search` — find candidate papers, using web/search tools if available in the session, or by organizing manually supplied titles/DOIs/BibTeX/PDFs/notes if not
- `triage` — review candidates and decide `screened` / `to-read` / `rejected`, always with a recorded rationale
- `reading-queue` — view/update the reading queue by status, with a required relevance note per entry
- `paper-note` — create/update a structured per-paper note under `.nora/literature/PAPER_NOTES/`
- `related-work-map` — organize tracked papers by topic, method, claim, or comparison axis

Invoke with `/nora-literature-manager <workflow>` or the short alias `/nora-literature <workflow>`.

Paper statuses: `candidate` → `screened` → `to-read` → `reading` → `read` → `cited` (or `rejected` / `replaced` at any point). The skill keeps candidates clearly distinct from papers actually read or cited — it never promotes a status without that having actually happened, and it never writes to `.bib`/`.tex` itself.

Works standalone (no `.nora/`) the same way `nora-citation-auditor` does: it says so explicitly and writes only to `.nora/literature/`. In a full Nora project, it also reads `.nora/CONTEXT_BRIEF.md`/`PROJECT_STATE.yaml` to ground relevance judgments.

## Skill: `nora-writing-assistant` (alias `/nora-writing`)

Academic writing improvement — polishing, restructuring, overclaim-checking, paragraph diagnosis, and style-profile setup — while preserving technical meaning, citation placement, and authorial caution. Does not generate full papers or invent claims/results/citations/mechanisms/novelty.

Five workflows:

- `polish` — improve wording/clarity/flow without changing technical content or claim strength (any strength change is called out explicitly)
- `restructure` — reorganize a passage/section (ordering, topic sentences, transitions) without changing technical content
- `overclaim-check` — flag overly strong/promotional language against what the evidence/citations actually support, and propose more cautious phrasing; marks uncertain citation support as `REVIEW_REQUIRED`
- `paragraph-diagnosis` — diagnose structural problems in a paragraph without necessarily rewriting it
- `style-profile` — establish/update the project's writing style (`WRITING_STYLE.md`) and phrase bank (`PHRASE_BANK.md`)

Invoke with `/nora-writing-assistant <workflow>` or the short alias `/nora-writing <workflow>`.

This skill is primarily skill-driven rather than CLI-driven — the CLI only scaffolds/checks `.nora/writing/*`. It explicitly supports two modes: **project-aware** (`.nora/` exists — reads `CONTEXT_BRIEF.md`, `PROJECT_STATE.yaml`, `NEXT_ACTIONS.md`, `OPEN_LOOPS.md`, and `.nora/writing/WRITING_STYLE.md` if present) and **standalone** (`.nora/` absent — uses default academic writing rules and says explicitly that no Nora project context was detected). A writing workspace doesn't need to contain project code or artifacts at all.

## Project-local state

Each project may contain:

```text
.nora/
  .gitignore                   # '*' — Nora state stays out of git by default
  config.yaml                  # workspace identity (project_id / workspace_id / workspace_type)
  PROJECT_STATE.yaml
  CONTEXT_BRIEF.md
  SESSION_LOG.md
  NEXT_ACTIONS.md
  OPEN_LOOPS.md
  decisions/
    decisions.yaml             # decision gate: agent proposals pending user approval
  citation/                    # optional — enabled via `nora citation init`
    CITATION_AUDIT_REPORT.md
    CITATION_REVIEW_QUEUE.yaml
    CLAIM_SUPPORT_AUDIT.md
  literature/                  # optional — enabled via `nora literature init`
    LITERATURE_LOG.md
    READING_QUEUE.md
    RELATED_WORK_MAP.md
    PAPER_NOTES/
  writing/                     # optional — enabled via `nora writing init`
    WRITING_STYLE.md
    STYLE_NOTES.md
    PHRASE_BANK.md
```

`nora new` creates only the core state (the five state files, `.gitignore`, `config.yaml`, `decisions/`) plus `AGENTS.md` — none of `citation/`, `literature/`, or `writing/`. Each module directory is created only by its own `nora <module> init`, and only when the user explicitly enables that module. A Nora-managed project is never forced to initialize any module it doesn't need. Module `init` commands resolve the workspace root first, so running them from a subdirectory targets the workspace's `.nora/`, never a new nested one. Workspaces created before 0.3.0 lack `.gitignore`/`config.yaml`/`decisions/`; `nora doctor` reports those as `INFO`, not errors.

`nora new` also copies an `AGENTS.md` into the project root, pointing any agent (Claude Code, Codex, or otherwise) at the Nora startup protocol, the four available skills, and the human-review policy, even if that agent doesn't use `nora-project-manager` directly.

## Standalone usage (no Nora project required)

Three of the four skills work without `.nora/PROJECT_STATE.yaml` ever existing — they say so explicitly and scope their output to just their own module directory:

- **Citation auditing in a plain LaTeX workspace**: run `nora citation init` in a directory that has `.tex`/`.bib` files but no other Nora state. The skill creates just `.nora/citation/` and runs its checks against the `.tex`/`.bib` files it finds — no project stage, goals, or other Nora files are required.
- **Writing assistance without `.nora/`**: paste a passage or point at a single file; `nora-writing-assistant` states that no Nora project context was detected, applies default academic writing rules instead of a project-specific style, and doesn't require any project artifacts.
- **Literature triage from manually supplied metadata**: if no web/search tools are available (or the workspace has no project at all), `nora-literature-manager` still organizes whatever the user pastes in — titles, DOIs, BibTeX entries, PDF text, notes — into the same reading-queue/triage/notes structure it would use with tool-assisted search.

## Human review policy

Agents propose updates to `.nora/*` files (core and module) and to `AGENTS.md`; they do not overwrite any of them silently. Low-stakes, purely additive actions (e.g. appending a new literature candidate found during `search`, or writing a brand-new per-paper note) may be written directly and then summarized — nothing existing is being changed. Anything that changes or removes existing content goes through a propose-then-confirm step.
