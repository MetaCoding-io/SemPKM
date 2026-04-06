---
id: S01
parent: M052
milestone: M052
provides:
  - Enriched kanban cards with priority/date/icon rendering
  - Column color accent pattern via status keyword matching
  - _detect_enrichment_fields() method on ViewSpecService for reuse by other views
requires:
  []
affects:
  - S04
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/tests/test_kanban.py
  - frontend/static/css/views.css
  - frontend/static/css/theme.css
  - backend/app/templates/browser/kanban_view.html
  - frontend/static/js/kanban.js
key_decisions:
  - D394: Kanban enrichment field detection via SHACL heuristic scanning — priority by sh:in path keyword, date by reusing _detect_date_fields()
  - D393: Column color mapping via generic keyword-based status-to-color heuristic, no manifest extension needed
patterns_established:
  - Kanban enrichment detection reuses existing SHACL introspection (_detect_date_fields) and scans form properties for priority — no new queries needed
  - Column color accents via JS keyword matching on data-status with CSS variable references — generalizable to other status-based views
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M052/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M052/slices/S01/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T02:02:43.412Z
blocker_discovered: false
---

# S01: Kanban Enrichment & Column Colors

**Kanban view now renders enriched cards with priority badges, due dates, and type icons, plus color-coded column borders based on status keywords.**

## What Happened

Two tasks delivered the full kanban enrichment feature end-to-end.

T01 added `_detect_enrichment_fields()` to ViewSpecService, which scans SHACL PropertyShapes for priority-like fields (sh:in with 'priority' in path, or fallback non-status sh:in) and date-like fields (reuses `_detect_date_fields()` start-field logic). `_build_kanban_select()` was extended with optional `priority_path` and `date_path` parameters that inject OPTIONAL SPARQL clauses. `execute_kanban_query()` now auto-detects enrichment, populates item dicts with `priority` and `due_date` keys (both nullable), and returns enrichment metadata. The router passes this metadata to the template context. 15 new unit tests cover all enrichment detection, SPARQL generation, and query execution paths.

T02 added the frontend rendering layer. Priority badges are small colored pills using `data-priority` attribute selectors with `color-mix()` theme primitives (critical→red, high→amber, medium→blue, low→green). Due dates render as muted text with a Lucide calendar icon. Type icons use the `data-lucide` + `createIcons()` pattern from the manifest icon registry. Column color accents are applied via `_applyColumnColors()` in kanban.js — keyword matching on the column's `data-status` value maps to CSS variable references (todo→blue, progress→amber, done→green, block→red, cancel→gray). A `--_color-gray-400` primitive was added to theme.css for the cancel/archive accent. All SVG elements have `flex-shrink: 0`. Zero standalone hex/rgba values — all colors use `color-mix(in srgb, var(--_color-*) N%, transparent)` with theme primitives.

Both tasks completed with zero regressions — all 33 kanban tests pass (18 existing + 15 new).

## Verification

All 33 kanban tests pass (18 existing + 15 new enrichment tests). CSS has 5 kanban-card-priority references, template has kanban-card-meta div, JS has _applyColumnColors function. Zero standalone hex values in views.css — all use color-mix with theme primitives. Lucide SVGs have flex-shrink: 0. --_color-gray-400 primitive present in theme.css for both light and dark modes.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 used data-lucide attribute + createIcons() for type icons instead of lucide.createElement() — the createElement API isn't reliably available on the CDN bundle and data-lucide is the established codebase pattern.

## Known Limitations

Column color keyword matching is English-only — status values in other languages won't get color accents (they fall back to transparent). Type icon rendering depends on window.SemPKM._sempkmIcons being populated — types without manifest icon entries show no icon.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/views/service.py` — Added _detect_enrichment_fields() method and _build_enrichment_metadata() helper; extended _build_kanban_select() with optional priority_path/date_path OPTIONAL clauses; updated execute_kanban_query() to auto-detect and return enrichment data
- `backend/app/views/router.py` — Pass enrichment metadata from execute_kanban_query() to kanban template context
- `backend/tests/test_kanban.py` — Added 15 new tests: TestDetectEnrichmentFields (5), TestBuildKanbanSelectEnrichment (4), TestExecuteKanbanQueryEnrichment (5)
- `frontend/static/css/views.css` — Added kanban-card-meta, kanban-card-priority (4 data-priority color variants), kanban-card-date, kanban-card-type-icon, kanban-date-icon CSS rules with color-mix theme primitives
- `frontend/static/css/theme.css` — Added --_color-gray-400 primitive in both light and dark mode blocks
- `backend/app/templates/browser/kanban_view.html` — Added conditional priority badge, due date line with calendar icon, and type icon placeholder inside kanban cards
- `frontend/static/js/kanban.js` — Added _applyColumnColors() with keyword-to-CSS-variable mapping and _applyTypeIcons() with manifest icon registry lookup; both called from initKanban()
