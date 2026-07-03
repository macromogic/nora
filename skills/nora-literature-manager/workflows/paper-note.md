# Workflow: Paper Note

Use this workflow to create or update a per-paper note under `.nora/literature/PAPER_NOTES/`.

## Goal

Produce a structured note capturing not just what the paper is, but why it matters to this project and how it might be used.

## Procedure

### 1. Identify the paper

Get title, authors, year, venue, and DOI/arXiv/URL if available — from `READING_QUEUE.md` if it's already tracked, or from the user directly.

### 2. Choose the file

Use `PAPER_NOTES/<slug>.md`, where `<slug>` is a short, filesystem-safe identifier (prefer the BibTeX citation key if one exists and is known, otherwise `firstauthor-year-keyword`, e.g. `smith2020-attention.md`). If a note already exists for this paper, update it rather than creating a duplicate.

### 3. Fill in the note

Follow the structure below (also in `templates/literature/PAPER_NOTE_TEMPLATE.md`). Do not invent content for fields you don't have information for — write `unknown` or `not yet read` rather than guessing.

- **Title / Authors / Year / Venue**
- **DOI / arXiv / URL** (if available)
- **Status** — one of the statuses in `SKILL.md`
- **Relevance to project** — why this paper matters here, specifically
- **Main contribution** — what the paper actually claims to contribute
- **Method summary** — brief, only as detailed as useful for this project's purposes
- **Evidence / results** — what the paper's results actually show, not a restatement of its abstract's claims
- **Limitations** — the paper's own stated limitations, plus any you notice that are relevant to how we'd use it
- **Possible use in our project** — concrete: background citation, baseline, method inspiration, contrast case, etc.
- **Citation status** — is it in the `.bib` yet? Cited in `.tex` yet? (Don't assume — check, or say unknown.)
- **Related Nora tasks or open loops** — link to relevant `.nora/NEXT_ACTIONS.md` items or `.nora/OPEN_LOOPS.md` entries if `.nora/` exists and a connection is clear; omit this field in standalone mode.

### 4. Output

Write the note file (creating or updating one file under `PAPER_NOTES/` is additive/scoped to that one paper, so — per `SKILL.md`'s core principles — write it directly rather than proposing a diff, then summarize what was written). If updating an existing note, preserve prior content the user hasn't asked to change; don't silently drop earlier notes when only one field is being updated.

If the note's existence should also update `READING_QUEUE.md`'s status (e.g. finishing a note after reading), propose that queue update per `workflows/reading-queue.md` rather than changing it here silently.
