# Workflow: Reboot

Use this workflow when the user wants to restart a stale or long-inactive research project.

## Goal

Recover the project from an unclear state into a usable state with:

1. Current-state summary
2. Artifact map
3. Blocker list
4. Open-loop list
5. Next smallest action

## Procedure

### 1. Read Nora state

Read, if present:

- `.nora/CONTEXT_BRIEF.md`
- `.nora/PROJECT_STATE.yaml`
- `.nora/NEXT_ACTIONS.md`
- `.nora/OPEN_LOOPS.md`
- `.nora/SESSION_LOG.md`

### 2. Determine project stage

Classify the project as one of:

- `unknown`
- `idea`
- `prototype`
- `experiment`
- `manuscript`
- `revision`
- `stale / rebooting`
- `archived`

### 3. Recover known state

Summarize:

- What the project is about
- What artifacts exist
- What appears to be done
- What is partial
- What is stale
- What is missing
- What is currently blocking progress

### 4. Classify artifacts

Use these labels:

- `DONE`: usable as-is
- `PARTIAL`: useful but incomplete
- `STALE`: likely outdated and needs review
- `MISSING`: expected but absent
- `UNKNOWN`: cannot determine yet
- `OBSOLETE`: should probably not be used

### 5. Define next action

The next action should be:

- concrete
- small
- doable in one session
- clearly connected to project recovery

Avoid vague actions such as:

- "improve the project"
- "read more papers"
- "write the paper"
- "run experiments"

Prefer actions such as:

- "List all existing manuscript files and classify section status."
- "Find the script that generated Figure 3."
- "Check whether existing experiment results match current code."
- "Create an artifact map from the current repository tree."

### 6. End with proposed Nora updates

Always end with proposed updates to:

- `.nora/SESSION_LOG.md`
- `.nora/NEXT_ACTIONS.md`
- `.nora/PROJECT_STATE.yaml`
- `.nora/OPEN_LOOPS.md`
