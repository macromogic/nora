---
name: nora-literature-manager
description: Search, triage, track, and organize research literature for a project — reading queues, per-paper notes, and a related-work map, distinguishing candidate papers from ones actually read or cited. Use this skill when finding related work, deciding what to read next, taking notes on a paper, or organizing how papers relate to each other and to your project's claims. Works with or without web search tools, and with or without a Nora project.
---

# Nora Literature Manager

## Purpose

Help search, triage, track, and organize research literature for a project. This skill focuses on literature *workflow management* — reading queues, triage rationale, per-paper notes, and a related-work map — not on being a full literature-search API client.

This skill currently supports five workflows:

- `search`: find candidate papers (using web/search tools if available, or by organizing manually supplied papers if not)
- `triage`: review candidates and decide whether they're worth reading, with a recorded rationale
- `reading-queue`: view and update the reading queue (status, priority, "why it matters")
- `paper-note`: create or update a per-paper note
- `related-work-map`: organize papers by topic, method, claim, or comparison axis

## Scope

This skill does not:

- Implement a full literature-search API client. If web/search tools are available in the session, use them; if not, work from whatever the user supplies (titles, DOIs, BibTeX entries, PDFs, pasted abstracts, notes).
- Judge whether a citation supports a specific claim — that's `nora-citation-auditor`'s `audit-claim-support` workflow. This skill tracks *what to read and why*; the claim-support audit happens once something is actually being cited.
- Write BibTeX entries or modify `.bib`/`.tex` files. If a paper should be added to the bibliography, say so and suggest the user (or `nora-citation-auditor`) do it — don't do it here.
- Write to Zotero or assume any external reference manager integration.

## Precondition: Nora state is optional

Unlike `nora-project-manager`, this skill does not require `.nora/` to exist.

- If `.nora/` exists, treat this as a Nora-enabled project: read `.nora/PROJECT_STATE.yaml` / `.nora/CONTEXT_BRIEF.md` for context on what the project is actually about (so triage relevance judgments are grounded), and write output under `.nora/literature/`.
- If `.nora/` does not exist, run in **standalone literature mode**: state this explicitly to the user, still write output under `.nora/literature/` (creating just that subdirectory), and don't require any other project artifacts.

Before running any workflow, check whether `.nora/literature/` exists.

- If it does not exist, ask the user whether you should run `nora literature init` to create the skeleton first. Do not create `.nora/literature/*` files yourself outside that skeleton until the user answers.
- If the user agrees, run `nora literature init`, then continue with the requested workflow.

## Argument routing

- If `$ARGUMENTS` is `help` → print this skill's usage: the supported workflows (`search`, `triage`, `reading-queue`, `paper-note`, `related-work-map`) and their invocation form (e.g. `/nora-literature-manager triage`). Do not run any workflow.
- If `$ARGUMENTS` starts with `search` → follow `workflows/search.md`.
- If `$ARGUMENTS` starts with `triage` → follow `workflows/triage.md`.
- If `$ARGUMENTS` starts with `reading-queue` → follow `workflows/reading-queue.md`.
- If `$ARGUMENTS` starts with `paper-note` → follow `workflows/paper-note.md`.
- If `$ARGUMENTS` starts with `related-work-map` → follow `workflows/related-work-map.md`.
- Otherwise (empty, or any unrecognized argument) → do not guess a workflow. Summarize the current reading queue (counts by status) if `.nora/literature/` exists, or say that no literature state was found, and ask what the user wants to do. If `$ARGUMENTS` has text, treat it as the user's actual request evaluated against that context.

## Core principles

1. Record *why* a paper matters, not just its title — every entry in the reading queue and every paper note needs a relevance note, not a bare citation.
2. Keep candidates and confirmed reads/citations clearly distinct (see Paper statuses below) — never silently promote a `candidate` to `read` or `cited` without that actually having happened.
3. Do not invent paper content. If you don't have an abstract or text, say so; don't guess what a paper says from its title alone.
4. Do not write to `.bib`/`.tex` or claim a paper is cited until it actually is — that's a fact about the manuscript, not about this skill's queue.
5. Prefer proposed updates over silent mutation, matching the rest of Nora — but for low-stakes, purely additive log/queue entries (e.g. appending a new candidate found during `search`), it's reasonable to write directly and then summarize what was added, since nothing existing is being overwritten. Reserve explicit propose-then-confirm for anything that changes an existing entry's status or content.

## Paper statuses

Use exactly these statuses, in this rough lifecycle order (not every paper passes through every stage):

- `candidate`: surfaced by `search`, not yet triaged
- `screened`: looked at during `triage`, judged plausibly relevant, not yet queued to read
- `to-read`: queued, not started
- `reading`: in progress
- `read`: finished reading, note may or may not exist yet
- `cited`: actually cited in the project's `.tex`/`.bib` (verify before assigning this — don't assume)
- `rejected`: triaged out; record why in `LITERATURE_LOG.md`
- `replaced`: superseded by a better/newer source; record what replaced it

## Project-local output

```text
.nora/literature/
  LITERATURE_LOG.md
  READING_QUEUE.md
  RELATED_WORK_MAP.md
  PAPER_NOTES/
```

- `LITERATURE_LOG.md` — records search/triage activity and inclusion/exclusion rationale.
- `READING_QUEUE.md` — tracks papers by status, with a relevance note per entry.
- `RELATED_WORK_MAP.md` — organizes papers by topic, method, claim, or comparison axis.
- `PAPER_NOTES/` — one file per paper that's been read or is being actively evaluated in depth; see `workflows/paper-note.md`.

## Output requirements

For `search` and `triage`, end with a summary of what was added or changed in `READING_QUEUE.md` and `LITERATURE_LOG.md`.

For `reading-queue`, end with the current queue state (grouped by status) and, if anything changed, what changed.

For `paper-note`, end with the note's file path and a short summary of its contents.

For `related-work-map`, end with a proposed diff-style update to `RELATED_WORK_MAP.md`:

```markdown
## Proposed Nora literature updates

### RELATED_WORK_MAP.md
...
```

If no update is needed, explicitly say so.
