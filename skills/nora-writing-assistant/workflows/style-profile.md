# Workflow: Style Profile

Use this workflow to establish or update the project's writing style, and its phrase bank of reusable cautious phrasing.

## Goal

A `WRITING_STYLE.md` that accurately reflects the project's target venue, tone, and terminology preferences, and a `PHRASE_BANK.md` of phrasing worth reusing — kept current as the project's writing evolves.

## Procedure

### 1. Check for standalone mode

If `.nora/` does not exist, ask the user whether they want a standalone style profile anyway (some writing workspaces have a style without a full Nora project) or whether this workflow isn't needed right now. Standalone style profiles still write to `.nora/writing/` (creating just that subdirectory).

### 2. Gather style information

Ask the user, or infer from existing manuscript text if supplied:

- Target venue (conference/journal, or "not yet decided").
- Desired tone (e.g. formal, first-person plural vs. passive, British vs. American spelling).
- Project-specific terminology: preferred terms, terms to avoid, consistent naming for methods/systems/datasets introduced by the project.
- Any existing style preferences already stated earlier in the conversation or found in prior manuscript text.

Do not invent house style out of nothing — if the user has no preference on something, note it as unset rather than picking one for them, unless they ask you to propose a default.

### 3. Update the phrase bank

Collect or propose reusable phrasing for common needs: cautious hedging ("suggests", "is consistent with"), transitions, and standard response/framing language (e.g. how this project typically introduces limitations or related work). Pull from `overclaim-check` findings or `polish` sessions earlier in this conversation if they surfaced good examples.

### 4. Log recurring issues

If this run was prompted by a recurring problem (e.g. "we keep overclaiming in the intro"), add a dated entry to `STYLE_NOTES.md` describing the issue and the decision made about it — this is append-only, not a replacement of prior notes.

### 5. Output

```markdown
## Proposed Nora writing updates

### WRITING_STYLE.md
...

### PHRASE_BANK.md
...

### STYLE_NOTES.md (if a recurring issue was logged)
...
```

Apply only on user confirmation.
