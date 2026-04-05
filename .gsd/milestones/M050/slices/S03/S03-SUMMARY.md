---
id: S03
parent: M050
milestone: M050
provides:
  - openGenericViewTab selectedType parameter for saved view type restoration
  - E2E selectors for saved views sidebar (savedViewsTree, savedViewEntry, typeFilterDropdown)
  - E2E test proving save/restore/delete round-trip
requires:
  - slice: S01
    provides: Smart type dropdown (.type-filter-select) in view toolbars
  - slice: S02
    provides: View Variants removal (variantSelect selector obsolete)
affects:
  []
key_files:
  - frontend/static/js/workspace.js
  - backend/app/templates/browser/my_views.html
  - e2e/helpers/dockview.ts
  - e2e/helpers/selectors.ts
  - e2e/tests/02-views/save-restore-view.spec.ts
key_decisions:
  - Renamed internal var to resolvedType to avoid confusion with the selectedType parameter name
  - Placed selectedType after waitState in E2E helper to preserve backward compat with all 25 existing callers
  - Used direct API calls for save/delete in E2E tests instead of dialog-based UI interaction for reliability
patterns_established:
  - openGenericViewTab accepts optional selectedType with localStorage fallback — future view types that need additional restore params follow the same pattern
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M050/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M050/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T22:33:00.084Z
blocker_discovered: false
---

# S03: Save/Restore Flow + E2E Tests

**Fixed saved view type filter restoration by wiring selectedType through openGenericViewTab and the sidebar template, proved with E2E tests covering save→restore→delete round-trip.**

## What Happened

The save/restore view flow had a two-part bug: (1) openGenericViewTab() never accepted an explicit type filter — it only read from localStorage, and (2) the my_views.html sidebar template never passed the stored type_filter value when opening a saved view.

T01 fixed the plumbing. openGenericViewTab() gained an optional 4th selectedType parameter with localStorage fallback (renamed internal var to resolvedType to avoid shadowing). The my_views.html template was updated to pass pv.type_filter as the 4th argument. The E2E dockview helper was updated to forward selectedType (placed after waitState for backward compat with all 25 existing callers). Selectors.ts was cleaned up: removed the obsolete variantSelect (View Variants removed in S02), added typeFilterDropdown, savedViewsTree, and savedViewEntry.

T02 created e2e/tests/02-views/save-restore-view.spec.ts with a comprehensive test: opens a table view, selects a type filter, saves via API, expands the Saved Views sidebar, verifies the entry has correct data-type-filter attribute, restores via openGenericViewTab with the type filter, verifies the toolbar dropdown shows the same type, then deletes and confirms removal. Passes on both Chromium and Firefox (16.7s).

## Verification

All 5 slice-level checks pass:
1. selectedType parameter present in openGenericViewTab signature ✅
2. type_filter wired in my_views.html onclick handler ✅
3. variantSelect removed from selectors.ts ✅
4. E2E test file exists at e2e/tests/02-views/save-restore-view.spec.ts ✅
5. selectedType forwarded in E2E dockview helper (5 references) ✅

E2E tests: 2 passed (Chromium + Firefox), 0 failed, 16.7s total.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 used direct API calls for save/delete instead of dialog-based UI interaction (more reliable in E2E context). T02 used localStorage fallback to ensure type filter propagates through dockview panel params. Both are pragmatic reliability choices, not functional deviations.

## Known Limitations

The my_views.html template uses bare openGenericViewTab() instead of SemPKM.openGenericViewTab() — a pre-existing issue from the M044 namespace migration (D374). The type filter restoration works because the bare global still exists as a shim, but should be updated in a future cleanup pass.

## Follow-ups

Update my_views.html onclick handlers to use SemPKM.openGenericViewTab() prefix (part of the broader M044 namespace migration cleanup noted in D374).

## Files Created/Modified

- `frontend/static/js/workspace.js` — Added optional selectedType parameter to openGenericViewTab with localStorage fallback
- `backend/app/templates/browser/my_views.html` — Wired pv.type_filter as 4th arg to openGenericViewTab in sidebar onclick
- `e2e/helpers/dockview.ts` — Added selectedType parameter forwarding to openGenericViewTab helper
- `e2e/helpers/selectors.ts` — Removed variantSelect, added typeFilterDropdown/savedViewsTree/savedViewEntry
- `e2e/tests/02-views/save-restore-view.spec.ts` — New E2E test for save/restore/delete view flow with type filter preservation
