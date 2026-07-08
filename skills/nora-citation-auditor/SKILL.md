---
name: nora-citation-auditor
description: Mechanically audit BibTeX and LaTeX citation usage in a research project — duplicate keys, duplicate DOIs, missing fields, missing/unused citations, possible duplicate entries, and a human-in-the-loop first pass at whether a citation appears to support the local claim it's attached to. Use this skill when checking a .bib file and .tex sources for citation hygiene, or when reviewing whether cited sources plausibly back a specific sentence. Does not claim to fully verify scientific correctness.
---

# Nora Citation Auditor

## Purpose

Perform mechanical and semi-mechanical auditing of a project's BibTeX (`.bib`) files and their usage in LaTeX (`.tex`) sources: catch structural and hygiene problems (duplicate keys, duplicate DOIs, missing required fields, citation/key mismatches, likely duplicate entries), plus a bounded, human-in-the-loop first pass at whether a citation plausibly supports the specific claim it's attached to — without claiming to fully verify scientific correctness.

Since 0.6.0 the deterministic checks live in the CLI: run `nora citation lint` first (the workflows do this), and keep the agent's effort for what scripts can't judge — fuzzy duplicates, false-positive filtering, claim-support review, and review-queue curation.

This skill currently supports four workflows:

- `check-bibtex`: audit `.bib` file(s) in isolation for duplicate keys, duplicate DOIs, missing fields, and possible duplicate entries
- `check-latex-citations`: cross-reference citation keys used in `.tex` files against the `.bib` file(s)
- `report`: consolidate findings from the above into `.nora/citation/CITATION_AUDIT_REPORT.md` and `.nora/citation/CITATION_REVIEW_QUEUE.yaml`
- `audit-claim-support`: for a given claim/citation pair, do a bounded read of the cited source's available metadata/abstract/text and classify how well it appears to support the claim — writing notes to `.nora/citation/CLAIM_SUPPORT_AUDIT.md`

## Scope

This skill audits citation *mechanics*, and — only in `audit-claim-support`, only ever as a human-assisted first pass — plausibility of *support*. It does not:

- Fully verify scientific correctness or claim-citation support. `audit-claim-support` is a reading aid for a human reviewer, not an automated verifier.
- Search the literature for missing citations (that's `nora-literature-manager`'s job).
- Fetch or verify metadata against Zotero, external DOI registries, or arXiv APIs.
- Modify `.bib` or `.tex` files. The skill never edits them; `nora citation fix --apply` (CLI, SAFE_FIX hygiene only, dry-run by default, backup first) edits `.bib` — running it needs the user's explicit go-ahead, and nothing edits `.tex`, ever.

These are out of scope for this iteration.

## Precondition: Nora state is optional

Unlike `nora-project-manager`, this skill does not require `.nora/` to exist.

- If `.nora/` exists, treat this as a Nora-enabled project: read `.nora/PROJECT_STATE.yaml` for context (e.g. paths to manuscript/references) if useful, and write citation output under `.nora/citation/`.
- If `.nora/` does not exist, run in **standalone citation-audit mode**: state this explicitly to the user, still write output under `.nora/citation/` (creating just that subdirectory, not a full Nora project scaffold), and do not suggest the workspace needs a full `nora init` unless the user asks.

Before running any workflow, check whether `.nora/citation/` exists.

- If it does not exist, ask the user whether you should run `nora citation init` to create the report/review-queue skeleton first. Do not create `.nora/citation/*` files yourself outside that skeleton until the user answers.
- If the user agrees, run `nora citation init`, then continue with the requested workflow.

## Argument routing

- If `$ARGUMENTS` is `help` → print this skill's usage: the supported workflows (`check-bibtex`, `check-latex-citations`, `report`, `audit-claim-support`) and their invocation form (e.g. `/nora-citation-auditor check-bibtex`). Do not run any workflow.
- If `$ARGUMENTS` starts with `check-bibtex` → follow `workflows/check-bibtex.md`.
- If `$ARGUMENTS` starts with `check-latex-citations` → follow `workflows/check-latex-citations.md`.
- If `$ARGUMENTS` starts with `report` → follow `workflows/report.md`.
- If `$ARGUMENTS` starts with `audit-claim-support` → follow `workflows/audit-claim-support.md`.
- Otherwise (empty, or any unrecognized argument) → do not guess a workflow. Locate `.bib` and `.tex` files in the project (ask the user if none are found or the location is ambiguous), summarize what's present, and ask what they want to do. If `$ARGUMENTS` has text, treat it as the user's actual request evaluated against that context.

## Core principles

1. Never modify `.bib` or `.tex` files. All findings are reported, not applied.
2. Never rename or delete citation keys.
3. Treat fuzzy/uncertain matches (duplicate titles, arXiv/journal duplicates) as review candidates, not facts.
4. Prefer false negatives over false positives for anything that would suggest deleting or merging a citation.
5. Do not silently overwrite `.nora/citation/*`.
6. Do not assume or write to any external system (Zotero, DOI registries, arXiv) — this is a purely local, file-based audit.

## File discovery

Unless the user specifies otherwise:

- Look for `.bib` files anywhere in the project, excluding common build/output directories (e.g. `build/`, `_minted*/`, `.git/`).
- Look for `.tex` files the same way.
- If multiple `.bib` files are found, ask the user which one(s) are canonical before treating any as authoritative, since duplicate-key/DOI checks are only meaningful within a merged view of the "real" bibliography.

## HITL policy

Use these labels for every mechanical finding (`check-bibtex`, `check-latex-citations`, `report`):

- `AUTO_SAFE`: mechanical and unambiguous (e.g. an exact duplicate BibTeX key — same key defined twice) — still reported, never auto-fixed
- `REVIEW_REQUIRED`: needs human judgment (e.g. fuzzy title match, possible arXiv/journal duplicate pair)
- `BLOCKED`: insufficient information to classify (e.g. a `.tex` citation key with no plausible `.bib` match)
- `DO_NOT_APPLY`: found but out of scope to fix here (e.g. a missing field that requires looking up the source)

No finding in this skill ever results in an automatic file edit — `AUTO_SAFE` describes confidence in the *finding*, not permission to act on it.

`audit-claim-support` uses a separate label set (see `workflows/audit-claim-support.md`) because "how confident is this mechanical finding" and "does this source support this claim" are different kinds of judgment and should not be conflated:

- `SUPPORTED`, `PARTIALLY_SUPPORTED`, `WEAK_OR_INDIRECT`, `UNSUPPORTED`, `REVIEW_REQUIRED`, `BLOCKED`

## Project-local output

```text
.nora/citation/
  CITATION_AUDIT_REPORT.md
  CITATION_REVIEW_QUEUE.yaml
  CLAIM_SUPPORT_AUDIT.md
  LINT_REPORT.md        # generated by 'nora citation lint --write'
  backups/              # originals saved by 'nora citation fix --apply'
```

- `CITATION_AUDIT_REPORT.md` — mechanical BibTeX/LaTeX citation audit report (`check-bibtex`, `check-latex-citations`, `report`).
- `CITATION_REVIEW_QUEUE.yaml` — human-review-required citation issues from the mechanical checks.
- `CLAIM_SUPPORT_AUDIT.md` — optional claim-citation support review notes (`audit-claim-support`). Untouched by the other three workflows.

## Output requirements

For `check-bibtex` and `check-latex-citations`, always end with a findings summary grouped by check type and HITL label, plus a proposed diff-style update to `CITATION_REVIEW_QUEUE.yaml` (append-only; do not renumber or remove existing entries).

For `report`, always end with:

```markdown
## Proposed Nora citation updates

### CITATION_AUDIT_REPORT.md
...

### CITATION_REVIEW_QUEUE.yaml
...
```

For `audit-claim-support`, always end with a proposed diff-style append to `CLAIM_SUPPORT_AUDIT.md`, per `workflows/audit-claim-support.md`.

If no update is needed, explicitly say so.
