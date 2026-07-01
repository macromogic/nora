# Nora

Nora is a personal research workflow system for maintaining project context, recovering stale research projects, and tracking progress across agent sessions.

The first version focuses on project lifecycle management, especially rebooting long-inactive research projects.

## Core ideas

- Global Nora skills teach agents how to work.
- Each research project keeps local state in `.nora/`.
- Agents should read project state at session start.
- Agents should propose state updates at session end.
- Human review is required before overwriting important project state.

## Initial skill

- `nora-project-lifecycle`
  - `reboot`: recover a stale project
  - `session-update`: summarize a session and propose state updates

## Project-local state

Each project may contain:

```text
.nora/
  PROJECT_STATE.yaml
  CONTEXT_BRIEF.md
  SESSION_LOG.md
  NEXT_ACTIONS.md
  OPEN_LOOPS.md
```
