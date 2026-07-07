# Workflow: Triage

Use this workflow to judge `candidate` papers: what each is for (roles), why it matters (note), and whether it's worth queueing to read.

## Goal

Every triaged candidate carries roles + a relevance note, and is either queued (`queued`), left as `candidate` (not enough information), or proposed for rejection through the decision gate.

## Procedure

### 1. Gather candidates

`nora literature queue` shows what's already queued; list candidates from `nora literature coverage` counts and the conversation. If the user named specific papers, scope to those.

### 2. Judge relevance

For each candidate, using whatever is actually available (title, abstract, venue, prior notes — never invented content):

- Does it relate to the project's current goal (per `.nora/CONTEXT_BRIEF.md` / `PROJECT_STATE.yaml` if present)?
- What is it *for*: assign roles from the fixed list (see SKILL.md), e.g. a baseline is `competing_system`, a method source is `methodology`.

### 3. Apply judgments via the CLI

- Roles + note (agent-safe, no gate): `nora literature mark <id> --role R1 --role R2 --note "..."`
- Worth reading now (free transition): `nora literature mark <id> queued`
- Not relevant (**gated**): do not mark `rejected` directly. Append one proposal to `.nora/decisions/decisions.yaml` (`status: pending`) listing the papers and the rejection reasons; after the user approves, run `nora literature mark <id> rejected --decision <id>` per paper.
- Genuinely can't tell: leave as `candidate` and say so — don't force a call.

### 4. Output

End with: marks applied (CLI output), the pending rejection proposal if one was filed (and that it awaits the user), and `nora literature coverage` if role assignments changed the picture.
