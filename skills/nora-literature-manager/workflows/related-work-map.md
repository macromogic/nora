# Workflow: Related Work Map

Use this workflow to assess role coverage and keep the generated related-work view current.

## Goal

A clear picture of how tracked papers cover the project's related-work roles, where the gaps are, and an up-to-date `RELATED_WORK_MAP.md` — generated, never hand-curated.

## Procedure

### 1. Read the coverage report

Run `nora literature coverage`: role × status counts, unassigned papers, and gap roles. This report — not the raw papers.yaml — is the working input.

### 2. Interpret

- **Unassigned papers**: triage debt — assign roles via the `triage` workflow (`mark --role`).
- **Gap roles**: judge which gaps actually matter for this project (a tool paper may never need a `threat_model` entry; a security paper without one is a real hole). Say which gaps you'd fill and why; filling them is a `search` follow-up — or `nora literature expand --seed <id>` from the strongest paper in a neighboring role (check `CITATION_GRAPH_SUMMARY.md` for papers reached from multiple seeds; those are strong mechanical signals).
- **Role imbalances**: e.g. many `background`, zero `competing_system` before a paper submission is a warning sign worth surfacing.

### 3. Regenerate the view

Run `nora literature render` to refresh `RELATED_WORK_MAP.md` (and `READING_QUEUE.md`). The view is grouped by role with status tags; it is read-only output — any correction goes through `mark`, then render again.

### 4. Output

End with the coverage report, your gap assessment (which gaps matter, which don't, and why), and confirmation that `render` was run.
