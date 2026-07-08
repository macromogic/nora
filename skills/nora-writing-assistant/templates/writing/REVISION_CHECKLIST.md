# Revision Checklist

Pre-submission pass, in order. Mechanical steps first (cheap, scriptable),
judgment steps after. Check items off per revision round; add project-specific
items at the bottom.

## Mechanical (CLI)

- [ ] `nora writing lint` — zero BLOCKED findings; every REVIEW_REQUIRED either fixed or consciously accepted
- [ ] `nora citation lint` — no undefined keys, duplicates resolved, SAFE_FIX hygiene applied (`nora citation fix --apply` after review)
- [ ] `nora citation keygen` — key convention violations either renamed (by hand, `.bib` + `.tex` together) or accepted

## Judgment (skill workflows)

- [ ] `/nora-writing-assistant overclaim-check` on abstract, intro, and conclusion
- [ ] `/nora-citation-auditor audit-claim-support` on the strongest claims
- [ ] Reading pass for flow (`paragraph-diagnosis` on anything that stumbles)

## Project-specific

(add your venue's checklist items here — page limits, anonymization, artifact links, ...)
