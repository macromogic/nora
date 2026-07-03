# Workflow: Audit Claim Support

Use this workflow when the user wants a first-pass check on whether a specific citation appears to support the specific claim it's attached to in the manuscript.

## Goal

Help a human reviewer decide, for one claim–citation pair at a time, whether the cited source plausibly backs the claim as written — without pretending this is automated scientific verification.

## Non-goal (read this before starting)

This workflow does **not**:

- Verify scientific correctness.
- Replace a human reading the source.
- Guarantee that a `SUPPORTED` classification means the claim is true — only that the cited source's available text appears to say something consistent with it.

State this limitation to the user before or alongside the first classification in a session, not just once in a template file nobody reads.

## Procedure

### 1. Identify the claim–citation pair(s) in scope

Ask the user for, or locate from `$ARGUMENTS`/conversation context:

- The specific sentence or clause making the claim (quote it verbatim from the `.tex` source, with file and line).
- The citation key(s) attached to it.

If the user gives a whole section or file instead of a specific claim, extract individual `\cite{...}`-adjacent sentences as separate claim–citation pairs rather than producing one vague judgment for the whole block.

### 2. Gather what's actually available about the source

Use whatever is at hand, in this order of preference, and record which you used:

1. Text already in the project (e.g. a downloaded PDF, notes in `.nora/literature/PAPER_NOTES/`, an abstract already pasted into the `.bib` `abstract` field or elsewhere in the project).
2. If web/search tools are available in this session, the source's abstract or a relevant excerpt (title, venue, and abstract are usually enough for a first pass; do not fabricate a full-text read you didn't actually do).
3. If neither is available, work from the BibTeX metadata alone (title, venue, year) and say explicitly that this is metadata-only and therefore a weaker basis for judgment.

Never invent paper content. If you don't have enough to say anything, use `BLOCKED`.

### 3. Classify

Compare the claim's specific wording (its strength, scope, and mechanism) against what you actually found. Use exactly one label:

- `SUPPORTED`: the source, as far as you can tell from what you read, directly and clearly supports the claim as stated — including its strength (don't mark `SUPPORTED` if the source hedges but the claim doesn't).
- `PARTIALLY_SUPPORTED`: the source supports part of the claim, or supports it under narrower conditions than the claim states.
- `WEAK_OR_INDIRECT`: the source is topically related but doesn't clearly establish the claim (e.g. it's suggestive, anecdotal, or a passing mention).
- `UNSUPPORTED`: the source, as far as you can tell, does not support the claim, or appears to contradict it.
- `REVIEW_REQUIRED`: you have partial information and a genuine read either way is plausible — don't force a call a human should make with the full text in hand.
- `BLOCKED`: you don't have enough material (no abstract, no notes, no web access, ambiguous claim wording) to say anything useful.

Default to `REVIEW_REQUIRED` or `BLOCKED` over guessing. A wrong `SUPPORTED` is worse than an honest `BLOCKED`.

### 4. Record reasoning, not just a label

For every pair, capture:

- The claim (verbatim, with location).
- The citation key(s).
- What source material was used (abstract / full text / metadata-only / prior notes) — per step 2.
- The classification.
- A one-to-three sentence reason referencing the actual source content, not a restatement of the claim.

### 5. Output

Propose a diff-style append to `.nora/citation/CLAIM_SUPPORT_AUDIT.md` following `templates/citation/CLAIM_SUPPORT_AUDIT.md`'s structure. Never overwrite prior entries in that file; append only.

```markdown
## Proposed Nora citation updates

### CLAIM_SUPPORT_AUDIT.md
...
```

If any pair came out `REVIEW_REQUIRED` or `BLOCKED` and the mechanical review queue is in use, also propose an append to `.nora/citation/CITATION_REVIEW_QUEUE.yaml` (type: `claim_support`) so it surfaces alongside the mechanical findings.
