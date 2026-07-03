# Workflow: Check LaTeX Citations

Use this workflow to cross-reference citation keys used in `.tex` files against the project's `.bib` file(s).

## Goal

1. Find LaTeX citation keys used in `.tex` files but missing from the `.bib` file(s).
2. Find BibTeX entries never cited from any `.tex` file.

## Procedure

### 1. Locate sources

Follow `SKILL.md`'s file-discovery rules for both `.tex` and `.bib` files. If the project has a clear main/entry `.tex` file (e.g. via `\input`/`\include`/`\subfile`), consider following those to build the full set of compiled sources, but include any `.tex` file in scope if the include graph is unclear rather than silently excluding it.

### 2. Extract cited keys

Extract citation keys from LaTeX citation commands, e.g. `\cite{...}`, `\citep{...}`, `\citet{...}`, `\citeauthor{...}`, `\parencite{...}`, `\textcite{...}`, and other `\cite*`/`\*cite` variants actually used in the project. A single command may cite multiple comma-separated keys.

### 3. Extract defined keys

Reuse the citation keys already collected by `check-bibtex` if that workflow ran earlier in this session; otherwise parse the `.bib` file(s) directly for defined keys.

### 4. Missing citations (used but not defined)

For every cited key with no matching `.bib` entry:

- Label: `BLOCKED` — the audit cannot resolve this without either the correct `.bib` entry or a correction to the `.tex` key. Report the `.tex` file and line/command where it's used.

### 5. Unused entries (defined but not cited)

For every `.bib` entry not cited anywhere in scope:

- Label: `REVIEW_REQUIRED` — it may be intentionally kept (e.g. for a related-work list maintained outside LaTeX, or a future draft section). Check for `\nocite{...}` first — `\nocite{*}` means "treat all entries as cited"; if present, skip this check entirely and say so in the output.

### 6. Output

Summarize missing and unused citations with HITL labels, per `SKILL.md`'s output requirements. Propose (do not write) an append to `.nora/citation/CITATION_REVIEW_QUEUE.yaml`.
