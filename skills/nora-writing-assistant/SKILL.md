---
name: nora-writing-assistant
description: Help with academic writing improvement — polishing, restructuring, overclaim-checking, paragraph diagnosis, and style-profile setup — while preserving technical meaning, citation intent, and authorial caution. Use this skill when revising manuscript prose, checking for overstated claims, diagnosing why a paragraph isn't working, or establishing a project's writing style. Works with or without a Nora project; does not generate full papers or invent claims/results/citations.
---

# Nora Writing Assistant

## Purpose

Help improve academic writing — clarity, structure, and claim calibration — while preserving technical meaning, citation placement, and appropriate authorial caution. This skill edits and advises on prose; it does not generate new scientific content.

This skill currently supports five workflows:

- `polish`: improve wording/clarity/flow of a passage without changing its technical content or claim strength (unless asked, and always with the change explained)
- `restructure`: reorganize a passage or section (ordering, topic sentences, transitions) without changing technical content
- `overclaim-check`: scan text for language that overstates what the evidence/citations actually support, and propose more cautious phrasing
- `paragraph-diagnosis`: diagnose structural problems in a paragraph (buried claim, unclear topic sentence, mixed ideas, orphaned citation) without necessarily rewriting it
- `style-profile`: establish or update the project's writing style (venue, tone, terminology) and phrase bank

## Scope

This skill does not:

- Generate full papers, sections, or novel scientific content from scratch.
- Invent claims, results, citations, mechanisms, or novelty that aren't already present in the source material or explicitly supplied by the user.
- Verify whether a citation actually supports a claim — that's `nora-citation-auditor`'s `audit-claim-support` workflow. This skill flags claim strength as `REVIEW_REQUIRED` when citation support looks uncertain, and suggests running that workflow; it doesn't do the verification itself.
- Modify `.bib` files or citation keys.
- Silently rewrite large files. Operate on the passage, paragraph, or section the user actually asked about; if given a whole file with no scope specified, ask which part to focus on rather than rewriting all of it.

## Two modes

Writing workspaces may or may not contain project code, artifacts, or `.nora/` state — this skill must work either way.

### Project-aware mode

If `.nora/` exists, read before writing:

1. `.nora/CONTEXT_BRIEF.md`
2. `.nora/PROJECT_STATE.yaml`
3. `.nora/NEXT_ACTIONS.md`
4. `.nora/OPEN_LOOPS.md`
5. `.nora/writing/WRITING_STYLE.md`, if present

Use this to calibrate: what's actually established vs. still in progress (don't let polished prose claim something `PROJECT_STATE.yaml` shows as `what_is_partial` or `what_is_blocked`), and any project-specific style preferences already recorded.

### Standalone mode

If `.nora/` does not exist:

- State this explicitly to the user before doing substantive work: no Nora project context was detected.
- Use default academic writing rules (see Writing rules below) instead of project-specific style.
- Do not require any project artifacts — a bare passage of text pasted by the user, or a single `.tex` file with no surrounding project, is a fully valid input.

Before writing to `.nora/writing/*` in either mode, check whether `.nora/writing/` exists; if not, ask whether to run `nora writing init` first (skip this if the user only wants a one-off edit with no persistent style state).

## Argument routing

- If `$ARGUMENTS` is `help` → print this skill's usage: the supported workflows (`polish`, `restructure`, `overclaim-check`, `paragraph-diagnosis`, `style-profile`) and their invocation form (e.g. `/nora-writing-assistant polish`). Do not run any workflow.
- If `$ARGUMENTS` starts with `polish` → follow `workflows/polish.md`.
- If `$ARGUMENTS` starts with `restructure` → follow `workflows/restructure.md`.
- If `$ARGUMENTS` starts with `overclaim-check` → follow `workflows/overclaim-check.md`.
- If `$ARGUMENTS` starts with `paragraph-diagnosis` → follow `workflows/paragraph-diagnosis.md`.
- If `$ARGUMENTS` starts with `style-profile` → follow `workflows/style-profile.md`.
- Otherwise (empty, or any unrecognized argument) → do not guess a workflow. Ask what the user wants help with (a passage to polish, a claim to check, a paragraph that isn't working, or setting up style preferences), loading `.nora/` context first per the two modes above if relevant.

## Writing rules

Apply these in every workflow:

1. Preserve technical meaning. A polished sentence must claim the same thing the original did, unless a claim-strength change is explicit and explained (see rule 6).
2. Preserve citations and citation placeholders (`\cite{...}`, `[CITATION NEEDED]`, etc.) — keep them attached to the claim they were attached to. Never remove, add, or move a citation to a different claim.
3. Do not invent claims, results, citations, mechanisms, or novelty. If something is unclear or missing, flag it — don't fill the gap with a plausible-sounding guess.
4. Avoid overly strong or promotional language ("novel", "state-of-the-art", "solves", "proves", "the first to") unless the source material already establishes it and the user isn't asking you to tone it down.
5. Prefer cautious academic phrasing when evidence is limited (e.g. "suggests" over "demonstrates", "may" over "will", scoped claims over universal ones).
6. When you change a claim's strength in either direction, explain the change explicitly — don't let a strength change hide inside a "polish" pass framed as pure wording.
7. When citation support for a claim is uncertain, mark it `REVIEW_REQUIRED` rather than silently softening or silently leaving it — this needs a human (or `nora-citation-auditor`'s `audit-claim-support`) to actually check the source.
8. Do not silently rewrite large files. Confirm scope before broad changes; default to the smallest unit the user actually asked about.

## Project-local output

```text
.nora/writing/
  WRITING_STYLE.md
  STYLE_NOTES.md
  PHRASE_BANK.md
  LATEX_CONVENTIONS.md   # project LaTeX conventions (lint checks the starred items)
  REVISION_CHECKLIST.md  # pre-submission pass: mechanical steps, then judgment steps
  LINT_REPORT.md         # generated by 'nora writing lint --write'
```

- `WRITING_STYLE.md` — project-specific writing style, venue, tone, terminology, and preferences.
- `STYLE_NOTES.md` — recurring project-specific writing issues and decisions (append-only log).
- `PHRASE_BANK.md` — reusable cautious phrasing, transition phrases, and response language.

Division of labor with the CLI (since 0.7.0): `nora writing lint` owns the mechanical prose checks — `\work[...]` placeholders (BLOCKED: removed, never formalized into real macros), leftover draft markup/markers, hand-written Figure/Table/Section references that should be `\cref`, straight `"..."` quotes that should be `` ``...'' `` (code contexts exempt), bold/italic overuse, overlong sentences, and non-ASCII punctuation. Lint is read-only — the writing domain has no auto-apply path; every fix goes through a human or a propose-then-confirm workflow. This skill owns everything requiring judgment: polishing, restructuring, claim calibration, diagnosis, style. Introducing a new LaTeX package or macro always requires explicit user approval.

## Output requirements

For `polish` and `restructure`, always show the original and proposed text side by side (or as a diff), with any claim-strength changes called out explicitly per Writing rule 6. Do not apply changes to the actual file unless the user confirms — treat this the same as any other propose-then-confirm Nora workflow, especially for anything beyond a small, clearly-scoped passage.

For `overclaim-check`, end with a findings list: each flagged phrase, why it's flagged, a proposed more cautious alternative, and `REVIEW_REQUIRED` where citation support is uncertain.

For `paragraph-diagnosis`, end with a diagnosis (not necessarily a rewrite) and a suggested next workflow (`polish` or `restructure`) if one is warranted.

For `style-profile`, end with:

```markdown
## Proposed Nora writing updates

### WRITING_STYLE.md
...

### PHRASE_BANK.md
...
```

If no update is needed, explicitly say so.
