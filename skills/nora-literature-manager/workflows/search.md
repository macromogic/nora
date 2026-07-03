# Workflow: Search

Use this workflow to find candidate papers for the project.

## Goal

Produce a set of `candidate` entries in `READING_QUEUE.md`, each with a recorded reason it might be relevant, plus a log entry in `LITERATURE_LOG.md` describing what was searched and why.

## Procedure

### 1. Establish what you're searching for

Ask the user, or use conversation/project context, for:

- The topic, method, claim, or comparison the search is for.
- Anything already known to be relevant (a seed paper, a keyword set, a venue).

If `.nora/CONTEXT_BRIEF.md` or `.nora/PROJECT_STATE.yaml` exist, use them to ground relevance — don't search blind if the project's actual goal is available.

### 2. Check what tools are available

- **If web/search tools are available in this session**: use them. Search by topic/keywords, and by following citation trails from known-relevant papers if useful. Prefer precise queries over broad ones — this workflow is about finding specific candidates, not doing a full survey.
- **If no web/search tools are available**: say so explicitly, and ask the user to supply candidates directly — titles, DOIs, arXiv IDs, BibTeX entries, PDFs, or pasted abstracts/notes. This workflow still organizes those the same way a tool-driven search would.

Either way, do not fabricate search results. If a tool call returns nothing useful, say so rather than inventing plausible-sounding papers.

### 3. Record each candidate

For each candidate paper, capture:

- Title, authors, year, venue (as available).
- DOI/arXiv ID/URL if available.
- **Why it might matter to this project** — this is required, not optional. "Came up in search" is not a reason; "proposes the baseline method we compare against" is.
- Status: `candidate`.

### 4. Output

Append new candidates to `READING_QUEUE.md` (additive — don't touch existing entries). Append a log entry to `LITERATURE_LOG.md` recording the search query/approach and what was found. Per `SKILL.md`, this is low-stakes and purely additive, so write directly and then summarize what was added.
