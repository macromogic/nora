# Nora

Nora is a personal research workflow system for maintaining project context, recovering stale research projects, and tracking progress across agent sessions.

## Core ideas

- Global Nora skills teach agents how to work.
- Each research project keeps local state in `.nora/`.
- Agents should read project state at session start.
- Agents should propose state updates at session end.
- Human review is required before overwriting important project state.

## CLI

`bin/nora` provides:

- `nora init` — scaffold `.nora/` state files and `AGENTS.md` in the current project
- `nora doctor` — check whether the current project has all Nora state files
- `nora install-skill` — symlink the `nora-project-manager` skill into Claude Code (`~/.claude/skills`) and Codex (`~/.codex/skills`), installing both the full name and a short `/nora` alias
- `nora update` — pull the latest Nora CLI and skills from git (refuses if `$NORA_HOME` has uncommitted changes); if the `AGENTS.md` template changed, prints a note to run `/nora sync-agents` in projects you want to sync

## Skill: `nora-project-manager` (alias `/nora`)

Four workflows:

- `new` — bootstrap a brand-new project with no prior state
- `reboot` — recover a stale or long-inactive project
- `session-update` — summarize the current session and propose project state updates
- `sync-agents` — check the project's `AGENTS.md` against the current template and propose an update

Invoke with `/nora <workflow>` (e.g. `/nora reboot`). A bare `/nora`, or one followed by text that doesn't match a workflow name, loads the project's `.nora/` context and continues the conversation normally — it does not guess and trigger one of the four workflows on its own.

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

`nora init` also copies an `AGENTS.md` into the project root, pointing any agent (Claude Code, Codex, or otherwise) at the Nora startup protocol and human-review policy, even if that agent doesn't use the `nora-project-manager` skill directly.

## Human review policy

Agents propose updates to `.nora/*` files and to `AGENTS.md`; they do not overwrite either silently.
