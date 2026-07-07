# Workflow: Paper Note

Use this workflow to create or update a per-paper note under `.nora/literature/PAPER_NOTES/`.

## Goal

A structured note capturing not just what the paper is, but why it matters to this project and how it might be used.

## Procedure

### 1. Identify the paper

The paper should already exist in `papers.yaml` (check `nora literature queue` / the ingest history). If it doesn't, ingest it first via the `search` workflow — notes attach to tracked papers, not free-floating titles.

### 2. Choose the file

Use `PAPER_NOTES/<id>.md`, where `<id>` is the paper's papers.yaml id (e.g. `lee2022probing.md`). One note per paper; update in place rather than creating duplicates.

### 3. Fill in the note

Follow `templates/literature/PAPER_NOTE_TEMPLATE.md`. Do not invent content for fields you lack information for — write `unknown` or `not yet read` instead.

The note duplicates nothing from `papers.yaml` except identity: status/roles live in the yaml (keep them there via `mark`); the note holds what yaml can't — contribution, method, evidence, limitations, how we'd use it.

### 4. Output

Write the note file directly (one file, one paper, additive — no confirmation gate), then summarize its path and contents. If writing the note coincides with a status change (e.g. finished reading), handle that via `workflows/reading-queue.md` — the gate applies there, not here.
