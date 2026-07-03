# Agent Instructions

This project uses Nora for research project state tracking.

## Startup protocol

Before working on this project, read:

1. `.nora/CONTEXT_BRIEF.md`
2. `.nora/PROJECT_STATE.yaml`
3. `.nora/NEXT_ACTIONS.md`
4. `.nora/OPEN_LOOPS.md`

## Preferred skills

Use `nora-project-manager` for project state and session continuity. Additional Nora skills cover optional, separately-initialized modules — use them when the relevant work comes up, not by default:

- `nora-project-manager` — project state, lifecycle, and session continuity (this is the one to use at the start/end of every session)
- `nora-citation-auditor` — BibTeX hygiene, LaTeX citation checks, and claim-citation support review (`.nora/citation/`, enabled via `nora citation init`)
- `nora-literature-manager` — literature search, triage, reading queues, and related-work maps (`.nora/literature/`, enabled via `nora literature init`)
- `nora-writing-assistant` — polishing, restructuring, and overclaim checks for manuscript prose (`.nora/writing/`, enabled via `nora writing init`; also works standalone without any `.nora/` project)

Do not assume the citation, literature, or writing modules are initialized just because this project uses Nora — check for `.nora/citation/`, `.nora/literature/`, `.nora/writing/` (or run `nora doctor`) before using them, and ask before running the relevant `nora <module> init` if one is missing.

## Session behavior

At session start:

- Summarize current project status.
- Identify the active next action.
- Avoid expanding scope unless requested.

At session end:

- Propose updates to `.nora/SESSION_LOG.md`.
- Propose updates to `.nora/NEXT_ACTIONS.md`.
- Propose updates to `.nora/PROJECT_STATE.yaml`.
- Propose updates to `.nora/OPEN_LOOPS.md`.

## Human review policy

Do not silently overwrite Nora state files unless explicitly asked.

For uncertain or high-impact changes, propose updates first.
