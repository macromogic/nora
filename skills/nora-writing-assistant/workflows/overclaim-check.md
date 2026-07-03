# Workflow: Overclaim Check

Use this workflow to scan text for language that overstates what the evidence or citations actually support.

## Goal

Find instances of overly strong or promotional phrasing, propose more cautious alternatives, and flag anything where citation support is uncertain enough to need human (or `nora-citation-auditor`) review.

## Procedure

### 1. Establish scope

Take the passage, section, or file the user specifies. This workflow can reasonably run over a larger scope than `polish`/`restructure` since it's read-only (findings, not automatic rewrites) — but still ask if scope is ambiguous.

### 2. Scan for overclaiming patterns

Look for:

- Absolute/universal language without support: "always", "never", "guarantees", "proves" (vs. "shows", "suggests", "is consistent with").
- Superlatives and novelty claims: "state-of-the-art", "the first", "novel", "best" — check whether the text actually substantiates these or just asserts them.
- Causal language where the evidence only supports correlation or association.
- Claims whose scope is broader than what was actually tested/shown (e.g. a claim about "all X" when the evidence covers one dataset or setting).
- Strong claims with no citation, or a citation whose relevance/strength you can't verify without reading it.

### 3. Classify each finding

For each flagged instance:

- Quote the phrase and its location.
- Explain what makes it an overclaim (which of the patterns above, and why).
- Propose a more cautious alternative phrasing, per Writing rule 5 in `SKILL.md`.
- If the issue is about citation support specifically (not just wording), mark it `REVIEW_REQUIRED` and suggest running `nora-citation-auditor`'s `audit-claim-support` workflow on that claim–citation pair rather than judging support yourself here.

### 4. Output

End with a findings list grouped by severity or location, each with: quote, issue, proposed rewrite, and label (`flag` for a pure wording issue, `REVIEW_REQUIRED` for uncertain citation support). Do not apply any rewrite to the actual file — this workflow reports, it doesn't edit. If the user wants the proposed rewrites applied, hand off to `polish` for that passage.
