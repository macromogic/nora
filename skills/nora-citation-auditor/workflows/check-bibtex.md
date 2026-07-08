# Workflow: Check BibTeX

Use this workflow to audit `.bib` file(s). Since 0.6.0 the deterministic checks are scripted — the agent runs the CLI and only adds the judgment the CLI can't make.

## Goal

A findings summary combining `nora citation lint`'s mechanical output with the agent-side fuzzy checks, plus a proposed append to `CITATION_REVIEW_QUEUE.yaml`.

## Procedure

### 1. Run the scripted checks

`nora citation lint [--bib FILE]` covers: duplicate keys, duplicate DOIs (proxy hosts normalized), missing fields, and the SAFE_FIX hygiene groups (proxy DOIs, page dashes, author format). Don't re-derive these by reading the `.bib` yourself — the CLI is the source of truth for them. If multiple `.bib` files are found, the CLI treats them as one merged bibliography; confirm with the user if that's wrong for this project.

### 2. Agent-side checks (fuzzy, judgment-required — not scripted on purpose)

- **Possible duplicate titles**: compare normalized titles pairwise; flag only near-identical pairs (identical, or differing by a trailing subtitle/edition marker). Err toward under-flagging. Label: `REVIEW_REQUIRED`.
- **arXiv/journal duplicate candidates**: an `eprint`/`archivePrefix: arXiv` entry vs. a venue entry with near-identical title and authors. Label: `REVIEW_REQUIRED`, never treated as confirmed.

### 3. Hygiene follow-ups

- If lint reported SAFE_FIX groups, tell the user `nora citation fix --apply` will fix them (dry-run first; originals are backed up). Running `fix --apply` edits `.bib` — that requires the user's go-ahead, per the approval list in `AGENTS.md`.
- If keys look nonconforming, run `nora citation keygen` and relay the proposals — renames are never applied automatically (they touch `.tex`).

### 4. Output

Summarize findings grouped by check with HITL labels, per `SKILL.md`'s output requirements. Propose (do not write) an append to `.nora/citation/CITATION_REVIEW_QUEUE.yaml` for anything actionable.
