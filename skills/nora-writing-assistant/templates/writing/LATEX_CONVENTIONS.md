# LaTeX Conventions

Project-specific LaTeX conventions. `nora writing lint` mechanically checks the
starred items; the rest are conventions for humans and agents to follow when
writing. Edit freely — this file is yours, not generated.

## References *

- Use `\cref{...}` (cleveref) for all Figure/Table/Section/Equation references —
  never hand-written `Figure~\ref{...}` and never hard-coded numbers ("Figure 3").

## Quotes and punctuation *

- Double quotes in prose: `` ``like this'' `` — never straight `"..."`
  (code contexts — `verbatim`, `\verb`, `\lstinline`, `\texttt` — are exempt).
- ASCII punctuation only in prose; em-dash is `---`, ellipsis is `\dots`.
- Hyphenation: `-` inside compound words, `--` for ranges (pages, years),
  `---` for sentence-level dashes.

## Placeholders and draft markup *

- No `\work[...]`-style placeholder commands, ever. They are agent-misuse
  artifacts: remove them, do not define them as real macros.
- No leftover `TODO` / `FIXME` / `XXX` / `??` in submitted text.
- Draft commands (`\hl`, `\sout`, `\marginpar`, underlining) are for drafts only.

## Emphasis *

- Bold/italics sparingly — if everything is emphasized, nothing is.

## Packages and macros

- Introducing a new LaTeX package or macro requires explicit user approval
  (see `AGENTS.md`); agents never add one on their own.
- Add project-specific term/notation conventions below as they are decided:

(none yet)
