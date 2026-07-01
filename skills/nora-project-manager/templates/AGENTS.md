# Agent Instructions

This project uses Nora for research project state tracking.

## Startup protocol

Before working on this project, read:

1. `.nora/CONTEXT_BRIEF.md`
2. `.nora/PROJECT_STATE.yaml`
3. `.nora/NEXT_ACTIONS.md`
4. `.nora/OPEN_LOOPS.md`

## Preferred skill

Use the global skill:

- `nora-project-manager`

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
