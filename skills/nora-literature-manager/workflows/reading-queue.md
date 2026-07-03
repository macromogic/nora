# Workflow: Reading Queue

Use this workflow to view or update the reading queue.

## Goal

Keep `READING_QUEUE.md` an accurate, status-grouped view of what's queued, in progress, and finished, each with a relevance note — and prompt the natural next step when a paper's status changes.

## Procedure

### 1. Determine intent

- If the user just wants to see the queue: read `READING_QUEUE.md` and summarize it grouped by status, in the lifecycle order from `SKILL.md`'s Paper statuses section.
- If the user wants to update one or more entries (e.g. "mark X as read", "move Y to reading", "reprioritize"): proceed to step 2.

### 2. Apply status changes

For each requested change:

- Validate the new status is one of the defined statuses.
- If moving to `read`: prompt the user to create a paper note via `paper-note` if one doesn't exist yet under `PAPER_NOTES/` — don't force it, but don't let papers silently pile up as `read` with no note either.
- If moving to `cited`: confirm with the user that the paper is actually cited in the project's `.tex`/`.bib` (this skill doesn't verify that itself — if `nora-citation-auditor` is available, suggest running `check-latex-citations` to confirm). Do not assign `cited` on the assumption that it will be cited later.
- If moving to `rejected` or `replaced`: require a one-line reason, logged to `LITERATURE_LOG.md`.

### 3. Output

This changes existing entries, so propose the diff rather than writing silently:

```markdown
## Proposed Nora literature updates

### READING_QUEUE.md
...

### LITERATURE_LOG.md (if a rejection/replacement reason was recorded)
...
```

Apply only on user confirmation.
