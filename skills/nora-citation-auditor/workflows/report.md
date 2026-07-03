# Workflow: Report

Use this workflow to consolidate findings from `check-bibtex` and `check-latex-citations` into the project-local citation audit output. This workflow does not touch `.nora/citation/CLAIM_SUPPORT_AUDIT.md` — that file is owned by `audit-claim-support`.

## Goal

Produce, as a proposal (never a silent write):

1. An updated `.nora/citation/CITATION_AUDIT_REPORT.md` — human-readable summary.
2. An updated `.nora/citation/CITATION_REVIEW_QUEUE.yaml` — structured, append-only queue of findings needing human review.

## Procedure

### 1. Gather findings

If `check-bibtex` and/or `check-latex-citations` already ran earlier in this session, reuse their findings. Otherwise, run whichever of them is needed first (ask the user if it's unclear whether both are in scope).

### 2. Read existing output

Read the current `.nora/citation/CITATION_AUDIT_REPORT.md` and `.nora/citation/CITATION_REVIEW_QUEUE.yaml` if they exist, so the update is additive: preserve prior review-queue entries and their resolution status, don't renumber them, and don't drop notes the user has added.

### 3. Update the report

Follow the structure in `templates/citation/CITATION_AUDIT_REPORT.md`. Include a run summary (date, files scanned, project vs. standalone mode) and one section per check type, each finding tagged with its HITL label.

### 4. Update the review queue

Follow the structure in `templates/citation/CITATION_REVIEW_QUEUE.yaml`. Append new findings as new entries; do not edit or remove existing entries' `status` field — that's for the user (or a future workflow explicitly asked to reconcile resolved items) to change.

### 5. Note Nora integration, if applicable

If `.nora/PROJECT_STATE.yaml` exists (full Nora project), propose — do not apply — a short pointer in `.nora/OPEN_LOOPS.md` under a relevant section (e.g. "Writing") noting that a citation audit was run and its headline numbers (e.g. "3 REVIEW_REQUIRED, 1 BLOCKED"). Do not propose changes to `PROJECT_STATE.yaml` unless the user asks; a citation audit is not itself a project-stage change.

If `.nora/` does not exist (standalone mode), skip this step entirely and say so.

### 6. End with proposed updates

```markdown
## Proposed Nora citation updates

### CITATION_AUDIT_REPORT.md
...

### CITATION_REVIEW_QUEUE.yaml
...
```

If in a full Nora project and step 5 applies, also include:

```markdown
### OPEN_LOOPS.md (optional pointer)
...
```

Apply only on user confirmation — never write `.nora/citation/*` files silently.
