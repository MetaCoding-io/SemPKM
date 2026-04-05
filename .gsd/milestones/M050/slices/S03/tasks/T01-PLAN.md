---
estimated_steps: 25
estimated_files: 4
skills_used: []
---

# T01: Fix type filter pass-through in openGenericViewTab and my_views.html

## Description

The save/restore flow stores `type_filter` correctly in RDF but never restores it because `openGenericViewTab()` only reads from localStorage, and `my_views.html` doesn't pass the stored value. This task fixes both bugs and updates the E2E infrastructure.

## Steps

1. **Read** `frontend/static/js/workspace.js` around the `openGenericViewTab` function (line ~3765). Add `selectedType` as a 4th parameter with fallback:
   - Change signature from `function openGenericViewTab(renderer, scopeQuery, scopeLabel)` to `function openGenericViewTab(renderer, scopeQuery, scopeLabel, selectedType)`
   - Change the selectedType assignment from `var selectedType = localStorage.getItem('sempkm_generic_type_' + renderer) || '';` to `var selectedType = selectedType || localStorage.getItem('sempkm_generic_type_' + renderer) || '';`
   - **Important:** The new param must shadow the `var` declaration. Rename the `var` to avoid confusion: use `var resolvedType = selectedType || localStorage.getItem(...)` and pass `resolvedType` to the dockview params.

2. **Read** `backend/app/templates/browser/my_views.html`. Update the non-query onclick handler:
   - Change from: `onclick="openGenericViewTab('{{ pv.renderer_type }}', '{{ pv.scope_query_id | default('') }}', '{{ pv.display_label | replace("'", "\\'") }}')"`
   - Change to: `onclick="openGenericViewTab('{{ pv.renderer_type }}', '{{ pv.scope_query_id | default('') }}', '{{ pv.display_label | replace("'", "\\'") }}', '{{ pv.type_filter | default('') }}')"`

3. **Read** `e2e/helpers/dockview.ts`. Add `selectedType` parameter to the `openGenericViewTab` helper:
   - Add `selectedType?: string` parameter after `scopeLabel`
   - Update the `page.evaluate` call to pass `selectedType` and forward it to `window.SemPKM.openGenericViewTab(renderer, scopeQuery || '', scopeLabel || '', selectedType || '')`

4. **Read** `e2e/helpers/selectors.ts`. In the `views:` block:
   - Remove `variantSelect: '.view-variant-select'` (View Variants was removed in S02)
   - Add `typeFilterDropdown: '.type-filter-select'`
   - Add `savedViewsTree: '#saved-views-tree'`
   - Add `savedViewEntry: '.view-leaf[data-view-id]'`

5. **Verify** all changes with grep checks.

## Must-Haves

- [ ] `openGenericViewTab()` accepts optional 4th `selectedType` parameter with localStorage fallback
- [ ] All existing callers (which pass 3 args) continue working — the 4th param is optional
- [ ] `my_views.html` passes `pv.type_filter` to `openGenericViewTab()`
- [ ] E2E `openGenericViewTab` helper forwards `selectedType`
- [ ] `variantSelect` removed from selectors.ts

## Inputs

- ``frontend/static/js/workspace.js` — contains openGenericViewTab() function at line ~3765`
- ``backend/app/templates/browser/my_views.html` — saved views sidebar template with onclick handlers`
- ``e2e/helpers/dockview.ts` — E2E helper wrapping openGenericViewTab()`
- ``e2e/helpers/selectors.ts` — centralized CSS selectors for E2E tests`

## Expected Output

- ``frontend/static/js/workspace.js` — openGenericViewTab() with 4-param signature`
- ``backend/app/templates/browser/my_views.html` — onclick passes pv.type_filter as 4th arg`
- ``e2e/helpers/dockview.ts` — helper forwards selectedType parameter`
- ``e2e/helpers/selectors.ts` — variantSelect removed, typeFilterDropdown/savedViewsTree/savedViewEntry added`

## Verification

rg 'function openGenericViewTab' frontend/static/js/workspace.js | grep -q 'selectedType' && rg 'openGenericViewTab' backend/app/templates/browser/my_views.html | grep -q 'type_filter' && rg 'variantSelect' e2e/helpers/selectors.ts | wc -l | grep -q '^0$' && echo 'T01 PASS'
