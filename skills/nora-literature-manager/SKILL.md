---
name: nora-literature-manager
description: Track, triage, and organize research literature around the structured papers.yaml backend — ingesting candidates, assigning roles, maintaining a decision-gated reading lifecycle, and keeping per-paper notes. Use this skill when collecting related work, deciding what to read next, taking notes on a paper, or mapping how papers relate to the project. Works with or without web search tools, and with or without a Nora project.
---

# Nora Literature Manager

## Purpose

Help track, triage, and organize research literature. Since 0.4.0 the module is backed by a structured state file: `.nora/literature/papers.yaml` is the single source of truth, written only by `nora literature` CLI commands. This skill supplies the judgment (what a paper is for, whether it's worth reading, why it matters); the CLI does the bookkeeping (ids, dedup, status machine, generated views).

Division of labor, in one line each:

- **CLI** (`nora literature ...`): ingest, dedup, status transitions (with the decision gate enforced mechanically), coverage report, rendered markdown views.
- **This skill**: relevance judgment, role assignment, reading rationale, per-paper notes under `PAPER_NOTES/`.

This skill currently supports five workflows:

- `search`: collect candidate papers (via web/search tools if available, or from user-supplied material) and ingest them
- `triage`: judge candidates, assign roles and relevance notes, queue what's worth reading
- `reading-queue`: view and advance the reading queue through the status machine
- `paper-note`: create or update a per-paper note under `PAPER_NOTES/`
- `related-work-map`: check role coverage and regenerate the related-work view

## Scope

This skill does not:

- Duplicate the CLI's metadata search. `nora literature search` queries arXiv/OpenAlex/Semantic Scholar/Crossref/DBLP with caching and dedup — prefer it over hand-driving web tools for finding papers; session web tools are a supplement. Citation-graph expansion (`expand`) is a future CLI feature.
- Judge whether a citation supports a specific claim — that's `nora-citation-auditor`'s `audit-claim-support`.
- Write BibTeX entries or modify `.bib`/`.tex` files. `proposed_cite` means "we propose citing this"; the actual `.bib` entry is the user's (or citation-auditor-assisted) step.
- Edit `papers.yaml` by hand — ever. All mutations go through `nora literature` commands. If a command is missing for something, say so and propose it; don't work around the CLI.

## Precondition: Nora state is optional

Run `nora root` first to resolve the workspace. This skill does not require a full `.nora/` project:

- If `.nora/` exists, read `.nora/PROJECT_STATE.yaml` / `.nora/CONTEXT_BRIEF.md` so triage judgments are grounded in what the project is actually about.
- If `.nora/` does not exist, run in **standalone literature mode**: state this explicitly, and let `nora literature init` create just `.nora/literature/`.

Before any workflow, check that `.nora/literature/papers.yaml` exists (`nora literature doctor`). If the module isn't initialized, ask the user before running `nora literature init`. If doctor reports a pre-0.4 layout (markdown files, no papers.yaml), tell the user the module was redesigned and let *them* decide when to move the old files aside — don't delete or migrate anything on your own.

## Argument routing

- If `$ARGUMENTS` is `help` → print this skill's usage: the supported workflows (`search`, `triage`, `reading-queue`, `paper-note`, `related-work-map`) and their invocation form (e.g. `/nora-literature-manager triage`). Do not run any workflow.
- If `$ARGUMENTS` starts with `search` → follow `workflows/search.md`.
- If `$ARGUMENTS` starts with `triage` → follow `workflows/triage.md`.
- If `$ARGUMENTS` starts with `reading-queue` → follow `workflows/reading-queue.md`.
- If `$ARGUMENTS` starts with `paper-note` → follow `workflows/paper-note.md`.
- If `$ARGUMENTS` starts with `related-work-map` → follow `workflows/related-work-map.md`.
- Otherwise (empty, or any unrecognized argument) → do not guess a workflow. Run `nora literature queue` and `nora literature coverage` if the module is initialized, summarize the state, and ask what the user wants to do. If `$ARGUMENTS` has text, treat it as the user's actual request evaluated against that context.

## The status machine and the decision gate

```text
candidate -> queued -> reading -> read -> proposed_cite -> cited
        \______________________________________________-> rejected
```

- Free transitions (`candidate`/`queued`/`reading`, any direction): the agent may run `nora literature mark` directly — queueing is bookkeeping, not a research decision.
- Gated transitions (anything to `read`, `proposed_cite`, `cited`, or `rejected`): append a proposal to `.nora/decisions/decisions.yaml` (`status: pending`), wait for the user to approve, then run `mark <id> <status> --decision <id>`. The CLI refuses gated promotions without an approved decision — do not attempt to bypass this by editing papers.yaml, and treat a refusal as "ask the user", not as an obstacle.
- `cited` additionally means the paper is actually cited in the manuscript's `.tex`/`.bib` — verify (or say you haven't) before proposing it.

## Roles

Assign one or more roles per paper during triage (`mark <id> --role ...`):

`direct_related`, `background`, `platform_spec`, `threat_model`, `methodology`, `evaluation_tool`, `dataset_benchmark`, `defense_mitigation`, `competing_system`, `survey`, `other`

Roles answer "what is this paper *for*, in this project" — `nora literature coverage` reports the role × status matrix and gaps, which is what `related-work-map` reasons over.

## Core principles

1. Record *why* a paper matters (`mark --note`), not just its title. "Came up in search" is not a reason.
2. Never invent paper content. No abstract, no notes → say so; don't guess from the title.
3. All literature state changes go through `nora literature` commands. Generated views (`READING_QUEUE.md`, `RELATED_WORK_MAP.md`) are read-only output — regenerate with `render`, never edit.
4. The decision gate is the user's control point. Batch related proposals into one decisions.yaml entry where sensible (e.g. one triage session), but never promote past the gate yourself.
5. Ingest is additive and low-stakes (new candidates only, built-in dedup) — run it directly and summarize. Everything that changes an existing paper's meaning (roles, notes, status) follows the gate rules above.

## Project-local output

```text
.nora/literature/
  papers.yaml           # single source of truth — CLI-owned, never hand-edited
  READING_QUEUE.md      # generated view ('nora literature render')
  RELATED_WORK_MAP.md   # generated view ('nora literature render')
  PAPER_NOTES/          # one note per paper, named <id>.md (agent/human-written)
```

## Output requirements

For `search` and `triage`, end with the CLI's own summary lines (added/skipped, marks applied) plus any pending decision proposals awaiting the user.

For `reading-queue`, end with `nora literature queue` output and what changed.

For `paper-note`, end with the note's file path and a short summary of its contents.

For `related-work-map`, end with the `coverage` report, the gaps you'd prioritize filling, and a note that `render` was run (if it was).

If no update is needed, explicitly say so.
