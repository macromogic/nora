# Workflow: Polish

Use this workflow to improve the wording, clarity, and flow of a passage without changing its technical content or claim strength (unless the user asks, or a change is explicitly called out).

## Goal

A revised passage that reads better while saying exactly the same thing — same claims, same strength, same citations attached to the same claims.

## Procedure

### 1. Establish scope

Identify the exact passage to polish (a sentence, paragraph, or a few paragraphs the user pasted or pointed to). If given a whole file with no scope specified, ask which part to focus on — do not polish an entire manuscript in one pass.

### 2. Load context, if relevant

- Project-aware mode: check `.nora/writing/WRITING_STYLE.md` for venue/tone/terminology preferences and `PHRASE_BANK.md` for preferred cautious phrasing to reuse.
- Standalone mode: state that no Nora project context was detected, and use default academic writing conventions.

### 3. Revise

- Improve clarity, flow, word choice, and sentence structure.
- Do not change what is claimed or how strongly it's claimed — see Writing rule 6 in `SKILL.md` if a strength change genuinely seems warranted; if so, call it out separately rather than folding it silently into a "polish."
- Keep every citation (`\cite{...}` or equivalent) attached to the same claim it was attached to before.
- Do not invent detail to make a sentence sound more complete — if the original is vague, either preserve the vagueness or flag it as something the user may want to clarify (don't resolve it yourself).

### 4. Output

Show the original and the revised passage together (diff-style if the passage is more than a sentence or two). Explain any non-trivial wording choices if they might be non-obvious. Do not write the change into the actual file unless the user confirms.
