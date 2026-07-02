# Workflow: New Project

Use this workflow when the user wants to start a brand-new research project that has no prior state and no stale artifacts to recover.

## Goal

Establish an initial project scaffold with:

1. A one-sentence project summary
2. An initial goal or research question
3. A realistic stage classification (`idea`, `prototype`, etc. — never `stale / rebooting`)
4. The first concrete next action

## Procedure

### 1. Capture the initial idea

Ask the user, or use available conversation context, for:

- What is the project about?
- What is the target output (paper, tool, experiment, dataset, ...)?
- What is the actual current stage: `idea`, `prototype`, or `experiment`?

### 2. Do not invent history

Unlike `reboot`, there is no existing state to reconstruct. Do not invent artifacts, blockers, or past progress that don't exist yet. Leave `known_artifacts` entries as `unknown` / `null` unless the user names something concrete that already exists.

### 3. Define the first action

Same bar as `reboot`: the next action should be concrete, small, and doable in one session. Prefer "Draft a one-paragraph problem statement" over "start research."

### 4. End with proposed Nora updates

Always propose (never silently write) initial values for:

- `.nora/PROJECT_STATE.yaml` — stage should reflect the real stage (e.g. `idea`), not `stale / rebooting`.
- `.nora/CONTEXT_BRIEF.md` — situation should say this is a new project just starting, not a reboot.
- `.nora/NEXT_ACTIONS.md` — first action only; leave the backlog empty.
- `.nora/OPEN_LOOPS.md` — leave categories empty unless the user already raised open questions.
- `.nora/SESSION_LOG.md` — first entry should record that the project was created and why.
