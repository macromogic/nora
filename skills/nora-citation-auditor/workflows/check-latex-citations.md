# Workflow: Check LaTeX Citations

Use this workflow to cross-reference citation keys used in `.tex` files against the project's `.bib` file(s). Since 0.6.0 this is fully scripted; the agent interprets and routes the findings.

## Goal

Findings for missing/unused/malformed citations and oversized cite clusters, interpreted in project context, plus a proposed append to `CITATION_REVIEW_QUEUE.yaml`.

## Procedure

### 1. Run the scripted checks

`nora citation lint [--tex FILE ...]` covers: keys cited but not defined (`BLOCKED`), entries defined but never cited (`REVIEW_REQUIRED`, with `\nocite{*}` detected and honored), malformed cite commands, cite clusters over the size limit, and the **heuristic** uncited-claim scan (a fixed verb list — its findings are leads, not verdicts).

### 2. Interpret

- `BLOCKED` undefined keys: check whether it's a typo of an existing key (suggest the likely match) or a genuinely missing entry (the user or a literature workflow supplies it — never invent a `.bib` entry).
- `REVIEW_REQUIRED` unused entries: they may be intentional (kept for a future section); say so rather than recommending deletion.
- `uncited_claim` heuristic hits: skim each sentence; drop obvious false positives, and route real candidates toward `audit-claim-support` once a citation is attached — or flag them as needing a citation.

### 3. Output

Summarize with HITL labels per `SKILL.md`. Propose (do not write) an append to `.nora/citation/CITATION_REVIEW_QUEUE.yaml`.
