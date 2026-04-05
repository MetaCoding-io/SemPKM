---
id: M050
title: "View System Rework"
status: complete
completed_at: 2026-04-05T22:37:29.741Z
key_decisions:
  - D389: Remove View Variants dropdown entirely — confusing UX with no data model impact. Model-declared ViewSpecs remain accessible through explorer sidebar.
  - D390: Reuse existing SHACL introspection methods for renderer-filtered type lists — no new SPARQL queries needed, just shape-based filtering via _detect_status_field, _detect_date_fields, _detect_geo_fields.
key_files:
  - backend/app/views/service.py — get_compatible_types() method
  - backend/app/views/router.py — /browser/views/compatible-types endpoint
  - backend/app/templates/browser/type_filter_dropdown.html — new select dropdown partial
  - backend/app/templates/browser/view_toolbar.html — View Variants removed
  - frontend/static/css/views.css — FC6 dark mode custom properties, pill CSS removed
  - backend/app/templates/browser/timeline_view.html — popup dismiss handlers
  - frontend/static/js/workspace.js — openGenericViewTab selectedType parameter
  - backend/app/templates/browser/my_views.html — type_filter wiring for saved views
  - e2e/tests/02-views/save-restore-view.spec.ts — save/restore/delete E2E test
  - backend/tests/test_compatible_types.py — 10 unit tests for renderer filtering
lessons_learned:
  - FullCalendar 6 uses CSS custom properties (--fc-button-text-color etc.) not direct CSS properties for button styling. Dark mode overrides must set the custom properties, not the direct properties — the custom-property rule wins the specificity battle.
  - Frappe Gantt 1.2.2 exposes gantt.hide_popup() for programmatic popup dismiss — useful when adding click-outside/Escape handlers. Document-level listeners must be cleaned up via registerCleanup for dockview panel lifecycle.
  - Existing SHACL introspection methods (_detect_status_field, _detect_date_fields, _detect_geo_fields) compose well for renderer compatibility filtering — no new SPARQL was needed, just iteration over cached shape data.
---

# M050: View System Rework

**Replaced the 37-pill type bar with renderer-filtered smart dropdowns, removed the confusing View Variants concept, fixed calendar dark mode and timeline popover UX, and repaired the save/restore view flow with E2E coverage.**

## What Happened

M050 targeted five view system UX problems that accumulated across M031–M034: an unwieldy 37-pill type filter bar, a confusing View Variants dropdown, invisible calendar nav icons in dark mode, undismissible timeline Gantt popups, and broken type filter restoration in saved views.

S01 (Smart Type Dropdown) was the high-risk foundation slice. It added `get_compatible_types(renderer, exclude_iris)` to ViewSpecService, reusing existing SHACL introspection methods (`_detect_status_field`, `_detect_date_fields`, `_detect_geo_fields`) to filter types by renderer compatibility — kanban only shows types with status fields, calendar/timeline only types with date fields, map only types with geo fields, and generic renderers show all types. A new JSON endpoint `GET /browser/views/compatible-types` was added for potential frontend lazy-loading. All 11 view templates (7 core + 4 specialized) were converted from the pill bar to a `<select>` dropdown via a new `type_filter_dropdown.html` partial. The onchange handler preserves scope_query and persists selection to localStorage. The View Variants dropdown was removed per D389. 10 unit tests cover all renderer filter paths.

S02 (Toolbar Cleanup + View Polish) delivered two targeted CSS/JS fixes. Calendar dark mode was fixed by adding 8 FullCalendar 6 custom properties (`--fc-button-text-color`, etc.) to the dark theme block, which FC6 reads natively — the previous direct-property overrides lost the specificity battle. Timeline popup dismiss was added via document-level click-outside and Escape handlers calling `gantt.hide_popup()`, with proper dockview cleanup registration.

S03 (Save/Restore Flow + E2E Tests) fixed the type filter restoration bug. `openGenericViewTab()` gained an optional `selectedType` parameter with localStorage fallback. The `my_views.html` sidebar template was updated to pass `pv.type_filter` when opening a saved view. An E2E test proves the full save→restore→delete round-trip with type filter preservation, passing on both Chromium and Firefox.

## Success Criteria Results

### Success Criteria Results

- **Open Kanban View → type dropdown shows only types with status fields. Open Table View → shows all types. No more 37-pill bar.**
  ✅ MET — `get_compatible_types('kanban')` filters via `_detect_status_field()`, returning only types with SHACL `sh:in` enum properties. `get_compatible_types('table')` returns all types. All 11 view templates use `type_filter_dropdown.html` instead of `type_filter_pills.html`. Verified: `grep -r 'type_filter_pills' ... | wc -l` → 0 references to old pills.

- **View toolbar is clean — no View Variants dropdown. Calendar dark mode shows visible nav buttons. Timeline popover dismisses on Escape/click-outside.**
  ✅ MET — `grep -c 'view-variant-select' view_toolbar.html` → 0. Calendar dark mode uses 8 FC6 custom properties (`--fc-button-text-color` etc.) verified present in views.css. Timeline has `hide_popup()` calls (2) and Escape handler with `registerCleanup` verified in timeline_view.html.

- **Save a view with type filter and scope query → find it in Saved Views sidebar → click to open → same type filter and scope are restored. E2E tests pass.**
  ✅ MET — `openGenericViewTab()` accepts `selectedType` parameter (9 references in workspace.js). `my_views.html` passes `type_filter` to the open handler (2 references). E2E test at `e2e/tests/02-views/save-restore-view.spec.ts` passes on Chromium and Firefox (16.7s total).

## Definition of Done Results

### Definition of Done Results

- ✅ All 3 slices complete: S01 ✅, S02 ✅, S03 ✅
- ✅ All 3 slice summaries exist: S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md
- ✅ All 6 task summaries exist: S01/T01, S01/T02, S02/T01, S02/T02, S03/T01, S03/T02
- ✅ Code changes verified in 6 commits with 20+ non-.gsd/ source files
- ✅ Zero unexpected file deletions across all M050 commits
- ✅ Unit tests: 10/10 passed for compatible types (test_compatible_types.py)
- ✅ E2E tests: save-restore-view.spec.ts passes on Chromium + Firefox
- ✅ Cross-slice integration: S03 consumes S01's type dropdown and S02's toolbar cleanup correctly

## Requirement Outcomes

No requirements changed status during M050. The milestone was a UX polish/fix effort addressing accumulated view system issues — no new requirements were created or validated.

## Deviations

S01/T02 updated all 11 view templates instead of the planned 7 — the 4 specialized views (OKR, BMC, quadrant, decision-matrix) also included the pills template. S03/T02 used direct API calls for save/delete instead of dialog UI interaction for E2E reliability.

## Follow-ups

Update my_views.html onclick handlers to use SemPKM.openGenericViewTab() prefix (part of the broader M044 namespace migration cleanup noted in D374).
