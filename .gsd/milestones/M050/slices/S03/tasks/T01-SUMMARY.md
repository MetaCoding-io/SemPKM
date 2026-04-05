---
id: T01
parent: S03
milestone: M050
key_files:
  - frontend/static/js/workspace.js
  - backend/app/templates/browser/my_views.html
  - e2e/helpers/dockview.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - Renamed internal var to resolvedType to avoid confusion with the selectedType parameter name
  - Placed selectedType after waitState in E2E helper to preserve backward compat with all 25 existing callers
duration: 
verification_result: passed
completed_at: 2026-04-05T21:56:51.784Z
blocker_discovered: false
---

# T01: Added selectedType parameter to openGenericViewTab with localStorage fallback, wired type_filter from saved views template, and updated E2E helpers and selectors

**Added selectedType parameter to openGenericViewTab with localStorage fallback, wired type_filter from saved views template, and updated E2E helpers and selectors**

## What Happened

Fixed the save/restore view flow so saved views can restore their type filter. openGenericViewTab() now accepts an optional 4th selectedType parameter with localStorage fallback. Updated my_views.html to pass pv.type_filter. Updated E2E dockview helper to forward selectedType. Updated selectors.ts: removed obsolete variantSelect, added typeFilterDropdown, savedViewsTree, savedViewEntry.

## Verification

Ran task verification command: confirmed selectedType in function signature, type_filter in my_views.html onclick, variantSelect absent from selectors.ts, and selectedType forwarded in E2E helper (5 hits in dockview.ts). Verified all 25 existing E2E callers pass ≤7 args — backward compatible.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'function openGenericViewTab' workspace.js | grep -q 'selectedType'` | 0 | ✅ pass | 100ms |
| 2 | `rg 'openGenericViewTab' my_views.html | grep -q 'type_filter'` | 0 | ✅ pass | 100ms |
| 3 | `rg 'variantSelect' selectors.ts | wc -l | grep -q '^0$'` | 0 | ✅ pass | 100ms |
| 4 | `grep -n 'selectedType' e2e/helpers/dockview.ts (5 hits)` | 0 | ✅ pass | 100ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/my_views.html`
- `e2e/helpers/dockview.ts`
- `e2e/helpers/selectors.ts`
