# M007: Generic Views, VFS Completion & Polish

**Gathered:** 2026-03-15
**Status:** Ready for execution

## Why This Milestone

Every active requirement in REQUIREMENTS.md feeds into this milestone. M006 left two design docs (VIEWS-RETHINK.md, VFS-V2-DESIGN.md) partially implemented — the planner cherry-picked easy subsets without flagging what was dropped. This milestone completes them and fixes the UI/docs gaps found during M006 review.

Three workstreams:

1. **Generic Views (VIEW-01–05)** — The Views Rethink design doc calls for 3 generic views (Table/Cards/Graph) with SHACL-driven dynamic columns and type filter pills. M006/S02 only regrouped the existing per-type tree — the actual design was never built.

2. **VFS v2 Completion (VFS-07–12)** — The VFS v2 design doc has 8 items. M006/S02 did item 1 (saved query scope). Items 2-7 (type filter, query IRI alignment, preview fix, path contract docs, composable chains, filename templates) are still unbuilt. Item 8 (write support) is explicitly deferred.

3. **Polish & Docs (UIPOL-01, DOCS-04)** — 7 UI consistency fixes found during review + missing user guide for M006 dashboard/workflow features.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open a "Table View" from the explorer and see all objects across all types
- Click type filter pills to narrow by type, with columns changing to match the type's SHACL shape
- See model-declared view variants in the carousel when a type is selected
- Navigate a clean explorer tree with 3 generic entries + Saved Views (no 31+ per-type folders)
- Create VFS mounts filtered to specific types without writing SPARQL
- Use composable strategy chains for multi-level folder hierarchies (by-tag → by-date)
- Customize filenames with templates ({date}-{title}.md)
- See consistent Lucide chevrons and always-visible action buttons in the explorer
- Read user guide documentation for dashboards and workflows

## Design Documents

- `.gsd/design/VIEWS-RETHINK.md` — Generic views, SHACL columns, type pills, explorer consolidation
- `.gsd/design/VFS-V2-DESIGN.md` — Type filter, query IRI alignment, preview, composable chains, filename templates
- `.gsd/design/GENERIC-VIEWS-VFS-V2-SLICE-PLAN.md` — Detailed slice plan for S01+S02 (written during M006 review)

## Scope

### In Scope
- All 13 active requirements: VIEW-01–05, VFS-07–12, DOCS-04, UIPOL-01

### Out of Scope
- VIEW-06 (custom column selection UI) — deferred
- VIEW-07 (faceted search) — deferred
- VFS-13 (write support) — deferred, separate milestone
