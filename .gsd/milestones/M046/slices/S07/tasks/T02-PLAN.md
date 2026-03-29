---
estimated_steps: 11
estimated_files: 4
skills_used: []
---

# T02: Bump .object-tab timeouts and replace waitForIdle with element-specific waits

Fix 4 test files covering Categories 3 (waitForIdle timeout) and 4 (object-tab loading timeout). These are repetitive mechanical edits — bumping `timeout: 10000` to `timeout: 20000` and replacing `waitForIdle` calls with element-specific waits.

## Steps

1. **object-view-redesign.spec.ts** — Bulk find-replace all `{ timeout: 10000 }` to `{ timeout: 20000 }` for `.object-tab`, `.object-face-edit.face-visible`, and `.object-face-read:not(.face-hidden)` waitForSelector calls. There are 13 instances.

2. **bug-fixes.spec.ts** — Change all 5 `.object-tab` waitForSelector calls from `{ timeout: 10000 }` to `{ timeout: 20000 }`.

3. **admin-model-detail.spec.ts** — Replace `waitForIdle(ownerPage)` calls that precede ontology diagram or relationship tab assertions with element-specific waits. For the ontology diagram section, replace `waitForIdle` with `await ownerPage.waitForSelector('.ontology-diagram, [data-testid="ontology-section"], .mermaid', { timeout: 20000 });` or whichever element indicates the diagram loaded. For other sections, replace with appropriate content-specific waits. Read the file first to identify which `waitForIdle` calls are the problematic ones (the ones near Relationships tab or ontology diagram).

4. **create-edge.spec.ts** — Replace the `waitForIdle` call after object loading with `await ownerPage.waitForSelector('.relations-section, #relations-content', { timeout: 20000 });` — wait for the relations panel content rather than all htmx to complete.

## Must-Haves

- [ ] object-view-redesign: all 13 timeout:10000 bumped to 20000
- [ ] bug-fixes: all 5 .object-tab timeouts bumped to 20000
- [ ] admin-model-detail: waitForIdle replaced with element-specific waits for diagram/relationship tests
- [ ] create-edge: waitForIdle replaced with relations panel content wait

## Inputs

- ``e2e/tests/01-objects/object-view-redesign.spec.ts` — current timeout:10000 values across 13 waitForSelector calls`
- ``e2e/tests/12-bug-fixes/bug-fixes.spec.ts` — current 5 .object-tab timeout:10000 waits`
- ``e2e/tests/05-admin/admin-model-detail.spec.ts` — current waitForIdle calls near diagram/relationship assertions`
- ``e2e/tests/01-objects/create-edge.spec.ts` — current waitForIdle call after object load`

## Expected Output

- ``e2e/tests/01-objects/object-view-redesign.spec.ts` — all timeouts bumped to 20000`
- ``e2e/tests/12-bug-fixes/bug-fixes.spec.ts` — all .object-tab timeouts bumped to 20000`
- ``e2e/tests/05-admin/admin-model-detail.spec.ts` — waitForIdle replaced with element-specific waits`
- ``e2e/tests/01-objects/create-edge.spec.ts` — waitForIdle replaced with relations content wait`

## Verification

cd e2e && npx playwright test tests/01-objects/object-view-redesign.spec.ts tests/12-bug-fixes/bug-fixes.spec.ts tests/05-admin/admin-model-detail.spec.ts tests/01-objects/create-edge.spec.ts --project=chromium --retries=1 --reporter=line 2>&1 | tail -30
