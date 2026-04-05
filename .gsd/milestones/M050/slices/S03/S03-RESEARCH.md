# S03 Research: Save/Restore Flow + E2E Tests

**Date:** 2026-04-05
**Status:** Complete
**Depth:** Targeted — known technology, clear bug path, established E2E patterns

## Summary

The save/restore flow is 80% built and working. The save path (toolbar → backend → RDF) works correctly end-to-end. The restore path has two JS bugs: (1) `openGenericViewTab()` doesn't accept a `selectedType` parameter — it always reads from localStorage, so saved views can't pass their stored type filter, and (2) `my_views.html` onclick handlers don't pass the stored `data-type-filter` value. Both are surgical JS fixes. E2E tests need a new spec file — no existing tests cover save/restore, and the `openGenericViewTab` E2E helper also needs the `selectedType` parameter added.

## Bug Analysis

### Bug 1: `openGenericViewTab()` ignores saved type filter

**File:** `frontend/static/js/workspace.js` (line 3765)

Current signature: `function openGenericViewTab(renderer, scopeQuery, scopeLabel)`

The function reads `selectedType` from localStorage only (line 3808):
```javascript
var selectedType = localStorage.getItem('sempkm_generic_type_' + renderer) || '';
```

Then passes it to dockview panel params (line 3815):
```javascript
params: {
    specialType: 'generic-view',
    renderer: renderer,
    selectedType: selectedType,  // from localStorage, never from caller
    scopeQuery: scopeQuery || '',
}
```

`workspace-layout.js` (line 246) correctly reads `params.params.selectedType` and builds the URL query string. So the fix is: add `selectedType` as a 4th parameter to `openGenericViewTab()`, falling back to localStorage when not provided.

**Fix:** Change signature to `function openGenericViewTab(renderer, scopeQuery, scopeLabel, selectedType)` and use `selectedType || localStorage.getItem(...)` for the value.

### Bug 2: `my_views.html` onclick doesn't pass type_filter

**File:** `backend/app/templates/browser/my_views.html`

The template stores `data-type-filter="{{ pv.type_filter }}"` on each entry, but the onclick handler for non-query views is:
```javascript
onclick="openGenericViewTab('{{ pv.renderer_type }}', '{{ pv.scope_query_id }}', '{{ pv.display_label }}')"
```

Missing the 4th arg. After Bug 1 fix, this becomes:
```javascript
onclick="openGenericViewTab('{{ pv.renderer_type }}', '{{ pv.scope_query_id }}', '{{ pv.display_label }}', '{{ pv.type_filter }}')"
```

### Bug 3: `openViewTab` (query-based views) also ignores type_filter

The `openViewTab(viewId, viewLabel, viewType)` function used for query-based promoted views doesn't pass type_filter either. The `my_views.html` template has `data-type-filter` on these entries too. This is a secondary fix — the same pattern applies.

## Save Flow Verification (confirmed working)

1. `view_toolbar.html` inline `saveCurrentView()` → reads `toolbar.dataset.typeFilter` ✅
2. Sends `POST /browser/views/save` with `{name, renderer_type, type_filter, scope_query_id}` ✅
3. `SaveViewRequest` model accepts all fields ✅
4. `query_service.save_promoted_view()` stores `type_filter` in RDF via `PRED_TYPE_FILTER` triple ✅
5. `list_promoted_views()` returns `type_filter` via OPTIONAL SPARQL binding ✅
6. `my_views.html` renders `data-type-filter="{{ pv.type_filter }}"` ✅

## Save Button UX

The save button is a `bookmark-plus` icon with `title="Save View"` tooltip — no text label. The research doc flagged this as undiscoverable, but adding a visible label is a minor UX improvement, not a bug. The save prompt uses `window.prompt()` for the view name — functional but basic.

**Minimum fix:** Add "Save" text label next to the icon, or a descriptive tooltip. Not essential for the flow to work.

## Files to Modify

### JS Changes
| File | Change | Lines |
|------|--------|-------|
| `frontend/static/js/workspace.js` | Add `selectedType` param to `openGenericViewTab()` | ~3765-3815 |
| `e2e/helpers/dockview.ts` | Add `selectedType` param to `openGenericViewTab()` helper | ~185-200 |

### Template Changes
| File | Change | Lines |
|------|--------|-------|
| `backend/app/templates/browser/my_views.html` | Pass `pv.type_filter` as 4th arg in onclick handlers | ~12-15 |

### E2E Selector Update
| File | Change |
|------|--------|
| `e2e/helpers/selectors.ts` | Remove stale `variantSelect` selector, add `typeFilterDropdown` and `savedViewsTree` selectors |

### New E2E Test File
| File | Purpose |
|------|---------|
| `e2e/tests/02-views/save-restore-view.spec.ts` | Full save/restore flow: save with type+scope → find in sidebar → open → verify restored filters |

## E2E Test Infrastructure

### Existing Patterns
- Auth fixture: `import { test, expect, BASE_URL } from '../../fixtures/auth'` — provides `ownerPage` and `ownerSessionToken`
- Workspace wait: `waitForWorkspace(ownerPage)` from `e2e/helpers/wait-for.ts`
- View tab opening: `openGenericViewTab(page, renderer, waitSelector)` from `e2e/helpers/dockview.ts`
- Selectors: `SEL.views.saveViewBtn` (`.save-view-btn`), `SEL.views.scopeSelect` (`.view-scope-select`)
- No existing save/restore E2E tests — clean slate

### Test Plan

1. **Save a view configuration**: Open a generic view → select a type from dropdown → click save → enter name → verify toast
2. **Find saved view in sidebar**: Expand SAVED VIEWS section → assert the new view appears with correct label
3. **Restore a saved view**: Click the saved view entry → verify the opened tab has the correct renderer, type filter, and scope query
4. **Delete a saved view**: Click unpin button → confirm → verify view removed from sidebar

### Key Selectors Needed
- Type filter dropdown: `.type-filter-select` (from `type_filter_dropdown.html`)
- Save button: `.save-view-btn` (already in SEL.views)
- Saved views tree: `#saved-views-tree`
- Saved view entry: `.view-leaf[data-view-id]`
- Unpin button: `.sparql-demote-btn`

### Prompt Dialog Handling
`saveCurrentView()` uses `window.prompt()` for the name input. Playwright handles this via `page.on('dialog')` listener. Must register the listener BEFORE clicking the save button.

## Natural Task Boundaries

### T01: Fix save/restore JS flow
- Add `selectedType` param to `openGenericViewTab()` in workspace.js
- Update `my_views.html` onclick handlers to pass `pv.type_filter`
- Update the `openGenericViewTab()` E2E helper in dockview.ts
- Update `e2e/helpers/selectors.ts` — remove stale `variantSelect`, add new selectors
- Verification: Manual grep checks confirming the parameter flows through

### T02: E2E test for save/restore flow
- Create `e2e/tests/02-views/save-restore-view.spec.ts`
- Test save with type filter → find in sidebar → restore → verify type filter preserved
- Test delete saved view
- Verification: `npx playwright test e2e/tests/02-views/save-restore-view.spec.ts` passes

## Risk Assessment

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|------------|
| 1 | Changing `openGenericViewTab` signature breaks existing callers | Medium | Low | The new param is optional with fallback to localStorage — all existing callers pass undefined which triggers the fallback |
| 2 | `window.prompt()` dialog handling in Playwright | Low | Low | Well-documented pattern — `page.on('dialog', d => d.accept('name'))` |
| 3 | Saved views sidebar lazy-load timing in E2E | Medium | Medium | Use `page.waitForSelector('#saved-views-tree .view-leaf')` after expanding the section |
| 4 | Type dropdown options not loaded when E2E test selects a type | Medium | Medium | Wait for `.type-filter-select option[value]` before interacting |

## Constraints

- `openGenericViewTab()` is used by 8+ E2E test files and the explorer sidebar — the signature change must be backward compatible (4th param optional)
- The `openGenericViewTab` E2E helper is used in 6 test files — its signature change must also be backward compatible
- The saved views sidebar uses `hx-trigger="intersect once"` for lazy loading — E2E tests must scroll/expand the section to trigger the load
- `saveCurrentView()` uses `window.prompt()` not a custom modal — Playwright handles this natively but the test must register the dialog listener first
