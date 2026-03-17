---
id: T03
parent: S05
milestone: M011
provides:
  - User guide Chapter 29 documenting all 4 M011 mental models
  - Updated TOC, navigation chain, and glossary entries
key_files:
  - docs/guide/29-mental-model-catalog.md
  - docs/guide/README.md
  - docs/guide/28-dashboards-and-workflows.md
  - docs/guide/appendix-d-glossary.md
key_decisions: []
patterns_established:
  - Chapter format: model overview, type field tables, relationships diagram, saved queries table, validation rules table, installation instructions, recommended dashboard config
observability_surfaces:
  - none (documentation-only task)
duration: 25m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Write user guide Chapter 29 (Mental Model Catalog) and update navigation

**Wrote 608-line Chapter 29 documenting all 4 M011 models with field references, relationships, saved queries, validation rules, installation steps, and recommended dashboards; updated TOC, nav chain, and 15 glossary entries.**

## What Happened

Created `docs/guide/29-mental-model-catalog.md` with four sections covering Basic PKM v2.0, Personal CRM, Zettelkasten+, and Research Workflow. Each section includes:

- Type descriptions with field reference tables (type, required, description) built from actual SHACL shapes
- Relationship diagrams in ASCII format showing inter-type connections
- Saved query tables listing all view names from the model's views.jsonld
- Validation rules tables with severity and exact messages from rules.ttl
- Installation instructions (paths for `Admin > Mental Models > Install`)
- Recommended dashboard configurations (per D150 — dashboards can't be bundled)
- A comparison table at the end summarizing type counts, focus, and key concepts

Updated three supporting files:
1. `docs/guide/README.md` — added Ch. 29 entry in Part VIII after entry 28
2. `docs/guide/28-dashboards-and-workflows.md` — changed "Next:" link from Appendix A to Ch. 29
3. `docs/guide/appendix-d-glossary.md` — added 15 alphabetically-sorted glossary entries for new model types, each with a cross-reference to Ch. 29

Also fixed the T03-PLAN.md observability gap per pre-flight instructions.

## Verification

All must-have checks pass:

- `test -f docs/guide/29-mental-model-catalog.md` → PASS (608 lines)
- `grep "29-mental-model-catalog" docs/guide/README.md` → PASS (listed in TOC)
- `grep "29-mental-model-catalog" docs/guide/28-dashboards-and-workflows.md` → PASS (Ch. 28 Next link updated)
- `grep "appendix-a" docs/guide/29-mental-model-catalog.md` → PASS (Ch. 29 links to Appendix A)
- `grep -c "Chapter 29" docs/guide/appendix-d-glossary.md` → 15 (exceeds minimum of 5)
- 4 model sections confirmed via `grep -c "^## [0-9]"` → 4

Slice-level verification for T03 items:
- Ch. 29 file exists: PASS
- Listed in TOC: PASS
- `tail -1 docs/guide/28-dashboards-and-workflows.md` contains `29-mental-model-catalog`: PASS

## Diagnostics

- Navigation chain integrity: `grep "29-mental-model-catalog" docs/guide/28-dashboards-and-workflows.md docs/guide/README.md`
- Cross-reference accuracy: field tables can be validated against `models/*/shapes/*.jsonld`
- Saved query names: can be validated against `models/*/views/*.jsonld` via `grep '"rdfs:label"'`
- Validation messages: can be validated against `models/*/rules/*.ttl` via `grep 'sh:message'`

## Deviations

- Plan listed Milestone status values as `planned/in-progress/completed/cancelled`; actual shapes use `planned/active/completed/cancelled`. Used the actual values from shapes.
- Plan listed Claim confidence values as `established/likely/possible/speculative/contested`; actual shapes use `established/supported/contested/speculative/refuted`. Used the actual values from shapes.
- Added a "Model Comparison" summary table at the end of Ch. 29 (not in plan) for quick cross-model reference.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/29-mental-model-catalog.md` — New Chapter 29 (608 lines) documenting all 4 M011 models
- `docs/guide/README.md` — Added Ch. 29 entry in Part VIII TOC
- `docs/guide/28-dashboards-and-workflows.md` — Updated "Next:" footer link to Ch. 29
- `docs/guide/appendix-d-glossary.md` — Added 15 glossary entries for new model types
- `.gsd/milestones/M011/slices/S05/tasks/T03-PLAN.md` — Added Observability Impact section
