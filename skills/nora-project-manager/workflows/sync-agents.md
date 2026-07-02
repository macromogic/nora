# Workflow: Sync Agents

Use this workflow when the user explicitly asks to check whether the project's `AGENTS.md` is in sync with the current Nora template — typically after `nora update` printed a note that the template changed.

## Goal

Bring the project's `AGENTS.md` in line with the current template, without discarding project-specific content the user may have added.

## Procedure

### 1. Locate the template

Read `$NORA_HOME/skills/nora-project-manager/templates/AGENTS.md` (default `$NORA_HOME` to `~/nora` if the environment variable is unset).

### 2. Compare

Read the project's own `./AGENTS.md`.

- If `./AGENTS.md` does not exist, tell the user and stop — this project was never initialized with `nora init`. Do not create it as part of this workflow.
- If the two files are identical, tell the user `AGENTS.md` is already up to date. Stop here.
- If they differ, summarize what changed between the project's version and the template (e.g. new sections, reworded protocol steps).

### 3. Propose an update

- Never overwrite `AGENTS.md` silently.
- If the project's `AGENTS.md` contains content that is not present in the template (e.g. a project-specific notes section the user added), call this out explicitly and preserve it in the proposed new version.
- Ask the user to confirm before writing.

### 4. Apply only on confirmation

If the user agrees, write the updated `AGENTS.md`. If they decline, leave the file untouched.

This workflow does not touch `.nora/*` files and does not require the "Proposed Nora updates" output block — it only concerns `AGENTS.md`.
