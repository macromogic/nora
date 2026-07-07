# Workflow: Search

Use this workflow to collect candidate papers and ingest them into `papers.yaml`.

## Goal

New `candidate` entries in `papers.yaml`, each ingested via the CLI with metadata as complete as the source material allows — plus a summary of what was searched and why.

## Procedure

### 1. Establish what you're searching for

Ask the user, or use conversation/project context, for the topic, method, claim, or comparison the search serves. If `.nora/CONTEXT_BRIEF.md` / `.nora/PROJECT_STATE.yaml` exist, ground relevance in them — don't search blind if the project's actual goal is on disk.

### 2. Check what tools are available

- **Web/search tools available**: use them, preferring precise queries over broad sweeps. Follow citation trails from known-relevant papers when useful.
- **No web/search tools**: say so explicitly and ask the user for material — titles, DOIs, arXiv IDs, BibTeX files, pasted abstracts. The workflow organizes those the same way.

Never fabricate search results. A tool call that returns nothing useful is a result — report it.

### 3. Ingest

For each candidate, run the matching ingest form:

- BibTeX file or pasted entries (save to a temp file first): `nora literature ingest --bibtex FILE`
- A bare list of titles: `nora literature ingest --titles FILE`
- A single paper with known metadata: `nora literature ingest --title ... --author "Lastname, Firstname" --year ... [--venue ... --doi ... --arxiv ... --url ...] --note "why it matters"`

The CLI dedups on entry (DOI / arXiv id / normalized title) and reports `skipped (already present as <id>)` — don't re-add those. For candidates ingested without `--note`, follow up with `nora literature mark <id> --note "..."` so every entry records why it might matter. "Came up in search" is not a reason; "proposes the baseline we compare against" is.

### 4. Output

End with the CLI's added/skipped summary, the note you attached to each new candidate, and the suggestion to run `triage` next. Ingest is additive and low-stakes — no confirmation gate needed, but summarize exactly what entered the state.
