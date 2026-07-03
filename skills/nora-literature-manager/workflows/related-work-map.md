# Workflow: Related Work Map

Use this workflow to organize tracked papers by topic, method, claim, or comparison axis.

## Goal

Keep `RELATED_WORK_MAP.md` a useful map of how the papers in `READING_QUEUE.md`/`PAPER_NOTES/` relate to each other and to the project — not just a re-listing of the reading queue.

## Procedure

### 1. Determine the organizing axis

Ask the user, unless it's already clear from context, which axis to organize by (one map can use more than one axis in different sections):

- **Topic**: papers grouped by subject area.
- **Method**: papers grouped by technique/approach.
- **Claim**: papers grouped by which of the project's claims they relate to or support.
- **Comparison**: papers grouped by what they're a baseline/alternative/contrast to in this project.

### 2. Gather source material

Pull from `READING_QUEUE.md` (for what's tracked) and `PAPER_NOTES/` (for papers with enough depth to place meaningfully — a bare `candidate` with no note is usually too thin to map yet; note it as unplaced rather than forcing a category).

### 3. Update the map

- Preserve existing categories and placements the user hasn't asked to change.
- Add new papers to existing categories where they fit, or propose a new category if none fits.
- For each entry, keep it to a one-line reason for its placement (not a repeat of the full paper note) — link to the paper note for detail.
- Flag papers that don't clearly fit any existing category instead of forcing a placement.

### 4. Output

This changes an existing, curated document, so propose the diff rather than writing silently:

```markdown
## Proposed Nora literature updates

### RELATED_WORK_MAP.md
...
```

Apply only on user confirmation.
