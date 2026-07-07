# Workflow: Reading Queue

Use this workflow to view the reading queue or advance papers through the status machine.

## Goal

`papers.yaml` reflects reality: what's queued, what's being read, what's finished — with every gated promotion carrying an approved decision.

## Procedure

### 1. Determine intent

- Just viewing: run `nora literature queue` (and `nora literature render` if the user wants the markdown view refreshed), summarize, done.
- Updating statuses: proceed.

### 2. Apply status changes

- Free transitions (`candidate`/`queued`/`reading`, any direction): run `nora literature mark <id> <status>` directly.
- Finished reading (**gated**: `read`): append a proposal to `.nora/decisions/decisions.yaml` (typically one entry covering the session's finished papers, `type: proposed_read`), wait for approval, then `mark <id> read --decision <id>`. Prompt for a `paper-note` at the same time — don't let papers pile up as `read` with no note.
- Proposing a citation (**gated**: `proposed_cite`): same gate, `type: proposed_cite`; include in the proposal *which claim or section* the citation would support.
- Marking as cited (**gated**: `cited`): only after the citation actually exists in `.tex`/`.bib` — verify it (or suggest `nora-citation-auditor`'s `check-latex-citations`), then gate as above.
- If the CLI refuses a transition, that's the gate working: surface the refusal to the user, don't work around it.

### 3. Output

End with `nora literature queue` output, what changed this session, and any pending proposals awaiting the user.
