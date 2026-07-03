# Workflow: Triage

Use this workflow to review `candidate` papers and decide whether they're worth reading.

## Goal

Move each candidate to `screened` (plausibly relevant, not yet queued), `to-read` (queued), or `rejected` (not relevant) — always with a recorded rationale.

## Procedure

### 1. Gather candidates in scope

Read `READING_QUEUE.md` for entries with status `candidate`. If the user named specific papers, scope to those; otherwise triage all current candidates.

### 2. Judge relevance

For each candidate, using whatever's available (title, abstract, venue, prior notes — do not invent content you don't have):

- Does it relate to the project's actual current goal (per `.nora/CONTEXT_BRIEF.md`/`PROJECT_STATE.yaml` if available, or the user's stated focus)?
- Is it a plausible related-work citation, a baseline, a method source, or background — or none of these?

### 3. Decide

For each candidate, assign exactly one:

- `screened`: plausibly relevant, worth a closer look later, but not queued yet.
- `to-read`: relevant enough to queue now.
- `rejected`: not relevant — record why (e.g. "off-topic", "superseded by X", "wrong problem setting").

If you genuinely can't tell from what's available, leave it as `candidate` and say so — don't force a decision without enough information.

### 4. Output

Propose the status changes as a diff against `READING_QUEUE.md` (this changes existing entries, so per `SKILL.md`'s core principles, propose rather than silently write). Append the rationale for each decision to `LITERATURE_LOG.md`.

```markdown
## Proposed Nora literature updates

### READING_QUEUE.md
...

### LITERATURE_LOG.md
...
```

Apply only on user confirmation.
