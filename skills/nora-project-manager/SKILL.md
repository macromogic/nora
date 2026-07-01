---
name: nora-project-manager
description: Recover, maintain, and update research project state across agent sessions. Use this skill when rebooting a stale research project, tracking progress, or preparing session state updates.
---

# Nora Project Lifecycle

## Purpose

Help maintain research project continuity across sessions by reading local `.nora/` state files, reconstructing project status, identifying blockers, and proposing concrete next actions.

This skill currently supports two workflows:

- `reboot`: recover a stale or long-inactive project
- `session-update`: summarize the current session and propose project state updates

## Argument routing

- If `$ARGUMENTS` is `help` → print this skill's usage: the supported workflows (`reboot`, `session-update`) and their invocation form (e.g. `/nora-project-manager reboot`). Do not run any workflow.
- If `$ARGUMENTS` starts with `reboot` → follow `workflows/reboot.md`.
- If `$ARGUMENTS` starts with `session-update` → follow `workflows/session-update.md`.
- Otherwise (empty, or any unrecognized argument) → infer the workflow from conversation context, or ask the user which one they want.

## Core principles

1. Do not expand project scope before recovering the current state.
2. Convert vague uncertainty into concrete next actions.
3. Prefer small, resumable steps over ambitious plans.
4. Preserve project history.
5. Do not silently overwrite project state.
6. For uncertain or high-impact changes, propose updates instead of applying them.

## Project-local state files

A Nora-enabled project should contain:

```text
.nora/
  PROJECT_STATE.yaml
  CONTEXT_BRIEF.md
  SESSION_LOG.md
  NEXT_ACTIONS.md
  OPEN_LOOPS.md
```

## Startup protocol

When working in a Nora-enabled project:

1. Read `.nora/CONTEXT_BRIEF.md` if it exists.
2. Read `.nora/PROJECT_STATE.yaml` if it exists.
3. Read `.nora/NEXT_ACTIONS.md` if it exists.
4. Read `.nora/OPEN_LOOPS.md` if it exists.
5. Identify the current session goal.
6. Recommend the smallest useful next action.

## HITL policy

The agent may propose updates to Nora state files, but should not overwrite important project state unless the user explicitly asks.

Use these labels:

- `AUTO_SAFE`: mechanical or low-risk update
- `REVIEW_REQUIRED`: requires human judgment
- `BLOCKED`: insufficient information
- `DO_NOT_APPLY`: risky or unsupported change

## Output requirements

For project lifecycle tasks, always end with:

``` markdown
## Proposed Nora updates

### SESSION_LOG.md
...

### NEXT_ACTIONS.md
...

### PROJECT_STATE.yaml
...

### OPEN_LOOPS.md
...
```

If no update is needed, explicitly say so.
