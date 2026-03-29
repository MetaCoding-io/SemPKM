---
estimated_steps: 16
estimated_files: 1
skills_used: []
---

# T01: Fix duplicate ontology-tab-content block, add missing ABox tab and pane

The ontology_page.html template contains two `<div class="ontology-tab-content">` blocks with duplicate element IDs and data-testid attributes. This causes Playwright strict mode failures ('resolved to 2 elements') in both ontology-viewer.spec.ts and class-creation.spec.ts. The ABox tab button is also missing from the tab bar.

All changes are in one file: `backend/app/templates/browser/ontology/ontology_page.html`.

## Steps

1. Read the current template file to confirm the duplicate blocks (lines ~83-131).
2. In the tab bar (the `.ontology-tabs` div), add an ABox tab button between the RBox button and the 'Create Class' button. The button must:
   - Have `data-tab="abox"` and `data-testid="ontology-tab-abox"`
   - Call `switchOntologyTab(this, 'abox')` on click
   - Lazy-load via `hx-get="/browser/ontology/abox"` `hx-target="#ontology-abox"` `hx-swap="innerHTML"` `hx-trigger="click once"`
   - Display: `ABox <span class="ontology-tab-hint">Instances</span>`
3. In the FIRST `ontology-tab-content` block, fix the RBox pane's unclosed `</div>` — add a closing `</div>` for the rbox pane before the closing `</div>` of the `ontology-tab-content`.
4. Add an ABox pane div between the RBox pane and the closing `</div>` of the first `ontology-tab-content` block. The pane must:
   - Have `id="ontology-abox"`, `class="ontology-pane"`, `data-testid="abox-browser"`
   - Contain: `<div class="ontology-loading">Click the ABox tab to load instance data.</div>`
5. Remove the ENTIRE second `ontology-tab-content` block (the stale duplicate with simpler TBox, ABox placeholder, and simpler RBox).
6. Run verification greps to confirm no duplicate IDs or data-testids.
7. Run E2E tests: `cd e2e && npx playwright test tests/22-ontology/ tests/23-class-creation/ --reporter=list`

## Inputs

- ``backend/app/templates/browser/ontology/ontology_page.html` — current template with duplicate blocks`
- ``e2e/helpers/selectors.ts` — SEL.ontology selectors (read-only reference for data-testid values)`

## Expected Output

- ``backend/app/templates/browser/ontology/ontology_page.html` — fixed template with single ontology-tab-content block, ABox tab button, ABox pane, and proper RBox div closure`

## Verification

bash -c 'echo "=== Duplicate check ==="; for attr in tbox-tree rbox-legend abox-browser ontology-tab-abox; do count=$(grep -c "data-testid=\"$attr\"" backend/app/templates/browser/ontology/ontology_page.html); echo "$attr: $count (expected 1)"; if [ "$count" -ne 1 ]; then echo "FAIL: $attr has $count occurrences"; exit 1; fi; done; for id in ontology-tbox ontology-rbox ontology-abox; do count=$(grep -c "id=\"$id\"" backend/app/templates/browser/ontology/ontology_page.html); echo "$id: $count (expected 1)"; if [ "$count" -ne 1 ]; then echo "FAIL: $id has $count occurrences"; exit 1; fi; done; echo "All duplicate checks passed"'
