# Workflow: Session Update

Use this workflow at the end of a working session.

## Goal

Record what changed during the session and make the next session easy to resume.

## Procedure

### 1. Summarize session

Capture:

- Session goal
- Files or artifacts inspected
- Progress made
- Decisions made
- New blockers
- Open questions
- Next suggested action

### 2. Update task status

For each active task, classify status as:

- `open`
- `active`
- `blocked`
- `waiting`
- `done`
- `dropped`

Every blocked task must include a next unblock action.

### 3. Propose file updates

Do not silently overwrite files. Produce a patch-style proposal.

## Required output

```markdown
## Proposed Nora updates

### `.nora/SESSION_LOG.md`

Append:

...

### `.nora/NEXT_ACTIONS.md`

Mark done:

...

Add:

...

### `.nora/PROJECT_STATE.yaml`

Update:

...

### `.nora/OPEN_LOOPS.md`

Add / resolve:

...
```
