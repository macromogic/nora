---
name: nora-project-manager
description: Start, recover, maintain, and update research project state across agent sessions. Use this skill when starting a brand-new research project, rebooting a stale one, tracking progress, or preparing session state updates.
---

# Nora Project Lifecycle

## Purpose

Help maintain research project continuity across sessions by reading local `.nora/` state files, reconstructing project status, identifying blockers, and proposing concrete next actions.

This skill currently supports four workflows:

- `new`: bootstrap a brand-new project with no prior state
- `reboot`: recover a stale or long-inactive project
- `session-update`: summarize the current session and propose project state updates
- `sync-agents`: check the project's `AGENTS.md` against the current template and propose an update

## Precondition: Nora state must exist

Before running any workflow, check whether `.nora/` exists in the current project.

- If it does not exist, ask the user whether you should run `nora init` to create the file skeleton first. Do not proceed with a workflow, and do not create `.nora/*` files yourself, until the user answers.
- If the user agrees, run `nora init`, then continue with the requested workflow.

## Argument routing

- If `$ARGUMENTS` is `help` → print this skill's usage: the supported workflows (`new`, `reboot`, `session-update`, `sync-agents`) and their invocation form (e.g. `/nora-project-manager reboot`). Do not run any workflow.
- If `$ARGUMENTS` starts with `new` → follow `workflows/new.md`.
- If `$ARGUMENTS` starts with `reboot` → follow `workflows/reboot.md`.
- If `$ARGUMENTS` starts with `session-update` → follow `workflows/session-update.md`.
- If `$ARGUMENTS` starts with `sync-agents` → follow `workflows/sync-agents.md`.
- Otherwise (empty, or any unrecognized argument) → this is not a request to run `new`, `reboot`, `session-update`, or `sync-agents`. Follow the Startup protocol to load `.nora/*` context, then continue the conversation normally: if `$ARGUMENTS` has text, treat it as the user's actual request evaluated against that loaded context (e.g. deciding what to do next, discussing a design change); if empty, summarize the current state and ask what they want to do. Do not run one of the four named workflows unless the user's request clearly calls for it or they explicitly name one.

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

For the `new`, `reboot`, and `session-update` workflows, always end with:

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
