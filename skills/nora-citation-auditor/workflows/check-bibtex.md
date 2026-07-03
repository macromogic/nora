# Workflow: Check BibTeX

Use this workflow to mechanically audit one or more `.bib` files in isolation, without cross-referencing `.tex` usage.

## Goal

Detect structural and hygiene problems in the bibliography:

1. Duplicate BibTeX keys
2. Duplicate DOI fields
3. Missing important fields (title, author, year, venue/journal/booktitle as applicable to entry type)
4. Possible duplicate titles (conservative fuzzy match)
5. Possible arXiv/journal duplicate candidates (review-only)

## Procedure

### 1. Locate the bibliography

Follow `SKILL.md`'s file-discovery rules. If more than one `.bib` file is in scope, confirm with the user whether to treat them as one merged bibliography or audit separately.

### 2. Parse entries

For each `.bib` entry, record: entry type (`@article`, `@inproceedings`, ...), citation key, and available fields.

Do not rewrite or reformat entries — this is a read-only pass.

### 3. Duplicate keys

Flag any citation key that is defined more than once in the same (or merged) bibliography.

- Label: `AUTO_SAFE` — an exact duplicate key is unambiguous to detect, but which entry to keep is still a human decision.
- Report both full entries so the user can compare.

### 4. Duplicate DOIs

Normalize DOIs (case-insensitive, strip leading `https://doi.org/` or `doi:`) and flag any DOI that appears on more than one entry.

- Label: `AUTO_SAFE` for the detection; the merge/removal decision is `REVIEW_REQUIRED`.

### 5. Missing important fields

For each entry, check for the fields expected by its type:

- All types: `title`, `author`, `year`
- `@article`: `journal`
- `@inproceedings` / `@conference`: `booktitle`
- `@book`: `publisher`
- Other types: use judgment; note the check as best-effort in the report if the entry type is unusual.

- Label: `DO_NOT_APPLY` — flag only; do not guess or fill in a missing field.

### 6. Possible duplicate titles (conservative fuzzy match)

Compare normalized titles (lowercase, strip punctuation, collapse whitespace) pairwise. Flag a pair only if:

- Normalized titles are identical, or
- Similarity is very high (e.g. they differ only by a trailing subtitle, edition marker, or minor typo) — err toward under-flagging. Do not flag titles that merely share common words or topic.

- Label: `REVIEW_REQUIRED` for every match. Never merge automatically.

### 7. Possible arXiv/journal duplicate candidates

Flag pairs where one entry looks like an arXiv preprint (`eprint`/`archivePrefix: arXiv` field, or a key/title suggesting arXiv) and another entry has a very similar title and author set, suggesting the same work later published in a venue.

- Label: `REVIEW_REQUIRED` always. This check is inherently uncertain — never treat a match as confirmed.

### 8. Output

Summarize findings grouped by check (duplicate keys, duplicate DOIs, missing fields, duplicate titles, arXiv/journal candidates), each with HITL labels, per `SKILL.md`'s output requirements. Propose (do not write) an append to `.nora/citation/CITATION_REVIEW_QUEUE.yaml` for anything actionable.
