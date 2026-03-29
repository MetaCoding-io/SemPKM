# S04 Research — Ontology Viewer: Locator Scoping for Dockview Panels

## Summary

The "resolved to 2 elements" strict mode errors are caused by a **duplicate HTML block** in `ontology_page.html`, not by dockview multi-panel rendering. The template contains two `<div class="ontology-tab-content">` sections (lines 83-114 and lines 116-131) that declare the same panes with identical `id` and `data-testid` attributes. This causes every Playwright locator targeting `[data-testid="tbox-tree"]`, `[data-testid="rbox-legend"]`, or `[data-testid="tbox-node"]` to resolve to 2+ elements, triggering strict mode failures.

Additionally, the ABox tab **button** (`[data-testid="ontology-tab-abox"]`) is completely missing from the template's tab bar, so the ABox E2E test cannot even find the tab to click.

## Recommendation

Remove the second (stale) `ontology-tab-content` block entirely. Merge the missing ABox pane into the first (canonical) block. Add the missing ABox tab button. Fix the unclosed `</div>` on the first RBox pane. No E2E test changes needed — the selectors are correct, the template is wrong.

## Implementation Landscape

### Root Cause: Duplicate `ontology-tab-content` blocks in template

**File:** `backend/app/templates/browser/ontology/ontology_page.html`

**Block 1 (lines 83-114) — newer, canonical version:**
- Full TBox with split tree/detail layout, filter bar, htmx event triggers for `classCreated`, `classDeleted`, `classEdited`
- RBox with htmx event triggers for `propertyCreated`, `propertyDeleted`, `propertyEdited`
- **Missing:** ABox pane
- **Bug:** RBox `<div>` is unclosed — the `</div>` at line 114 closes `ontology-tab-content` instead

**Block 2 (lines 116-131) — older, stale version:**
- Simple TBox (no split layout, no filter bar, no `classEdited` trigger)
- ABox pane with placeholder text
- Simple RBox with placeholder text
- This block should be **removed entirely**

### Duplicated elements causing Playwright strict mode failures

| data-testid | Count | Used by test | Effect |
|---|---|---|---|
| `tbox-tree` | 2 | ontology-viewer.spec.ts, class-creation.spec.ts | `locator()` resolves to 2, strict fail |
| `rbox-legend` | 2 | ontology-viewer.spec.ts | `locator()` resolves to 2, strict fail |
| `tbox-node` | doubled | Both specs (nodes loaded into both tbox-tree divs via htmx) | Every node locator resolves to 2× expected |
| `abox-browser` | 1 | ontology-viewer.spec.ts ABox test | Not duplicated but test can't reach it (no tab button) |

### Missing ABox tab button

The tab bar (lines 11-38) has buttons for TBox and RBox but **no ABox button**. The E2E test at `e2e/tests/22-ontology/ontology-viewer.spec.ts:89` clicks `SEL.ontology.tabAbox` which is `[data-testid="ontology-tab-abox"]` — this element does not exist. The ABox backend route (`GET /ontology/abox`) and templates (`abox_browser.html`, `abox_instances.html`) all exist and work fine.

### Unclosed RBox div

In Block 1, the RBox pane opens at line 110:
```html
<div id="ontology-rbox" class="ontology-pane" data-testid="rbox-legend"
     hx-get="/browser/ontology/rbox"
     hx-trigger="propertyCreated from:body, propertyDeleted from:body, propertyEdited from:body"
     hx-swap="innerHTML">
</div>  ← This closes ontology-tab-content, not the rbox pane
```

The `</div>` at line 114 is at 2-space indent level, meaning it closes the parent `ontology-tab-content` rather than the rbox pane. The fix is to add a proper `</div>` to close the rbox pane before the `ontology-tab-content` close.

## Files to Change

### Template fix (single file)
- **`backend/app/templates/browser/ontology/ontology_page.html`** — The only file that needs modification:
  1. Add ABox tab button to the tab bar (between TBox and RBox buttons, before "Create Class")
  2. Add ABox pane to the first `ontology-tab-content` block (between TBox and RBox)
  3. Fix the unclosed RBox `</div>` in the first block
  4. Remove the entire second `ontology-tab-content` block (lines 116-131)

### No E2E test changes needed
- `e2e/tests/22-ontology/ontology-viewer.spec.ts` — All selectors are correct. They reference `SEL.ontology.*` which map to the right `data-testid` values.
- `e2e/tests/23-class-creation/class-creation.spec.ts` — All selectors are correct.
- `e2e/helpers/selectors.ts` — No changes needed.

### ABox tab button specification

The new button must:
- Have `data-testid="ontology-tab-abox"` (matches `SEL.ontology.tabAbox`)
- Call `switchOntologyTab(this, 'abox')` on click
- Lazy-load ABox content via `hx-get="/browser/ontology/abox"` with `hx-target="#ontology-abox"` and `hx-trigger="click once"` (same pattern as the existing RBox button)
- Display label: `ABox` with hint `<span class="ontology-tab-hint">Instances</span>`

### ABox pane specification

The new pane must:
- Have `id="ontology-abox"` and `data-testid="abox-browser"`
- CSS class `ontology-pane` (hidden by default, shown by `switchOntologyTab`)
- Initial content: `<div class="ontology-loading">Click the ABox tab to load instance data.</div>`

## Verification

```bash
# 1. No duplicate data-testids in ontology_page.html
grep -c 'data-testid="tbox-tree"' backend/app/templates/browser/ontology/ontology_page.html
# Expected: 1

grep -c 'data-testid="rbox-legend"' backend/app/templates/browser/ontology/ontology_page.html
# Expected: 1

grep -c 'data-testid="abox-browser"' backend/app/templates/browser/ontology/ontology_page.html
# Expected: 1

grep -c 'data-testid="ontology-tab-abox"' backend/app/templates/browser/ontology/ontology_page.html
# Expected: 1

# 2. No duplicate IDs
grep -c 'id="ontology-tbox"' backend/app/templates/browser/ontology/ontology_page.html
# Expected: 1

grep -c 'id="ontology-rbox"' backend/app/templates/browser/ontology/ontology_page.html
# Expected: 1

# 3. E2E tests pass
cd e2e && npx playwright test tests/22-ontology/ tests/23-class-creation/ --reporter=list
```

## Task Decomposition Guidance

This is a **single-task fix**. All changes are in one template file. The work is:
1. Add ABox tab button in the tab bar
2. Fix Block 1: close the RBox div properly, add ABox pane between TBox and RBox
3. Remove Block 2 entirely (lines 116-131 of the current file)
4. Run verification greps + E2E tests

No CSS changes needed (ABox styles already exist in `workspace.css`). No backend changes needed (routes exist). No JS changes needed (`switchOntologyTab` already handles arbitrary tab IDs). No E2E test changes needed (selectors are correct).
