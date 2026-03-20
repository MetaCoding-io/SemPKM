---
estimated_steps: 4
estimated_files: 2
---

# T02: Playwright E2E spec + selectors

**Slice:** S04 — E2E tests + user guide
**Milestone:** M024

## Description

Create the Playwright E2E test for Monday.com Sync and add the `mondaySync` selector block to the shared selectors file. The test follows the Jira E2E spec (12-phase structure) with two extra phases for column mapping and label mapping configuration — the novel Monday.com feature.

The test exercises the full lifecycle against the Docker test stack with the mock-monday server: install basic-pkm model → install monday-sync app → open workspace → connect via API token → select board → configure columns → configure labels → set sync direction → sync now → verify tasks via SPARQL → verify admin page → cleanup uninstall.

**Key differences from Jira E2E:**
- Monday.com uses a single API token (not email + token + site URL)
- Token input selector is `#monday-token` (not `#jira-email` / `#jira-token` / `#jira-site-url`)
- Extra column mapping configuration phase after board selection
- Extra label mapping configuration phase after column mapping
- Board checkboxes use `.board-checkbox-item` (not `.project-checkbox-item`)

## Steps

1. **Add `mondaySync` selector block to `e2e/helpers/selectors.ts`** — add after the `jiraSync` block at the bottom of the `SEL` object:
   ```typescript
   // Monday.com Sync E2E
   mondaySync: {
     tokenInput: '#monday-token',
     connectBtn: '.credentials-form button[type="submit"]',
     connectStatus: '.connection-status',
     displayName: '.display-name',
     boardCheckbox: '.board-checkbox-item input[type="checkbox"]',
     saveBoardsBtn: '.boards-section button[type="submit"]',
     configureColumnsBtn: '.board-mapping-row a',
     saveColumnMappingBtn: '.column-mapping-form button[type="submit"]',
     configureLabelsBtn: '.board-mapping-row a.btn-configure-labels',
     saveLabelMappingBtn: '.label-mapping-form button[type="submit"]',
     syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
     saveConfigBtn: '.sync-config-form button[type="submit"]',
     syncNowBtn: '#sync-now-btn',
     syncStats: '.sync-stats',
   },
   ```

2. **Create `e2e/tests/42-monday-sync/monday-sync.spec.ts`** — follow Jira's spec structure exactly but adapt for Monday.com. The spec must have these imports:
   ```typescript
   import { test, expect, BASE_URL } from '../../fixtures/auth';
   import { SEL } from '../../helpers/selectors';
   import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';
   ```

3. **Implement all test phases** inside a single `test.describe('Monday.com Sync', () => { test('full lifecycle...', async ({ ownerPage, ownerRequest }) => { ... }) })` block. Each phase mirrors the Jira pattern:

   **Phase 0 — Cleanup**: Remove monday-sync if installed from prior run.
   - Navigate to `${BASE_URL}/admin/apps`
   - If a card with "Monday.com Sync" exists, go to admin detail and click uninstall
   - Accept dialogs via `ownerPage.on('dialog', ...)` 
   - Set generous timeout: `test.setTimeout(240_000)`

   **Phase 1 — Prerequisite: install basic-pkm model** (same as Jira):
   - Navigate to `${BASE_URL}/admin/models`
   - If basic-pkm not in model table, fill `/app/models/basic-pkm` in `#model-path` and submit
   - Poll with `.toPass()` until model appears

   **Phase 2 — Install monday-sync app**:
   - Navigate to `${BASE_URL}/admin/apps`
   - Fill `/app/apps/monday-sync` in `SEL.apps.installInput`, click submit
   - Poll until app card shows "Running" status (120s timeout with retry intervals)
   - Wait 5s for app subprocess to fully start

   **Phase 3 — Open app settings in workspace**:
   - Navigate to `${BASE_URL}/browser/`
   - Wait for workspace, wait for idle
   - Find `#section-apps`, expand if not expanded (click header)
   - Click tree-leaf with text "Monday.com Sync"
   - Wait for `#connect-content` to be visible (with retry loop like Jira)

   **Phase 4 — Connect via API token**:
   - Fill `SEL.mondaySync.tokenInput` with `'fake-monday-token-12345'`
   - Click `SEL.mondaySync.connectBtn`
   - Wait for `SEL.mondaySync.connectStatus` to be visible and contain "Connected"

   **Phase 5 — Select board**:
   - First board checkbox should be visible
   - Check it
   - Click `SEL.mondaySync.saveBoardsBtn`
   - Wait for htmx swap, verify still connected

   **Phase 6 — Configure columns**:
   - Find a "Configure Columns" link/button in the board mapping row
   - Click it (this loads the column mapping fragment via htmx)
   - Wait for the column mapping form to appear
   - The form has `<select>` dropdowns for each bpkm property. Look for dropdowns and if visible, try to save
   - Click the save button for column mapping
   - Wait for htmx swap back to connect_status

   **Phase 7 — Configure labels**:
   - Find a "Configure Labels" link/button
   - Click it (loads the label mapping fragment via htmx)
   - Wait for the label mapping form to appear
   - Look for dropdowns mapping Monday.com labels to bpkm values, save if present
   - Click the save button for label mapping
   - Wait for htmx swap back to connect_status

   **Phase 8 — Configure sync direction**:
   - Set bidirectional radio: `SEL.mondaySync.syncDirectionBidirectional`
   - Click `SEL.mondaySync.saveConfigBtn`
   - Wait for htmx swap, verify still connected

   **Phase 9 — Sync Now**:
   - Click `SEL.mondaySync.syncNowBtn`
   - Wait 5s for sync to complete
   - Verify `SEL.mondaySync.syncStats` is visible
   - Find "Last Pull" stat group, verify status contains "success" or "ok"
   - Check "Created" count is ≥ 2

   **Phase 10 — Verify tasks via SPARQL**:
   - POST to `${BASE_URL}/api/sparql` with SPARQL COUNT query for `bpkm:Task` objects
   - Parse bindings, verify task count ≥ 2

   **Phase 11 — Admin detail page**:
   - Navigate to `${BASE_URL}/admin/apps`
   - Verify monday-sync card shows "Running" status

   **Phase 12 — Cleanup: uninstall**:
   - Navigate to `${BASE_URL}/admin/apps/monday-sync`
   - Click uninstall button in form `form[action="/admin/apps/monday-sync/uninstall"]`
   - Verify app no longer appears in apps list

4. **Verify TypeScript compiles** — run `npx tsc --noEmit e2e/tests/42-monday-sync/monday-sync.spec.ts` or at minimum check the file has valid syntax.

## Must-Haves

- [ ] `mondaySync` selector block added to `e2e/helpers/selectors.ts`
- [ ] E2E spec has all 12+ phases: cleanup → install basic-pkm → install monday-sync → workspace open → connect → board select → configure columns → configure labels → sync direction → sync now → SPARQL verify → admin verify → cleanup
- [ ] Single API token connection (not 3-field like Jira)
- [ ] Column mapping configuration phase navigates to configure_columns.html fragment and saves
- [ ] Label mapping configuration phase navigates to configure_labels.html fragment and saves
- [ ] SPARQL verification confirms ≥ 2 Task objects created
- [ ] Cleanup uninstalls the app at the end
- [ ] Test accepts confirm dialogs for uninstall operations
- [ ] 240s generous timeout for Docker operations

## Verification

- File `e2e/tests/42-monday-sync/monday-sync.spec.ts` exists with all phases
- `node -e "require('typescript').createSourceFile('test.ts', require('fs').readFileSync('e2e/tests/42-monday-sync/monday-sync.spec.ts','utf8'), 99)"` — parses without error (or similar syntax check)
- `grep -c 'mondaySync' e2e/helpers/selectors.ts` — at least 1 match
- Full E2E: `npx playwright test e2e/tests/42-monday-sync/monday-sync.spec.ts` (requires Docker stack)

## Inputs

- `e2e/tests/41-jira-sync/jira-sync.spec.ts` — Reference E2E spec to clone structure from (318 lines, 12 phases)
- `e2e/helpers/selectors.ts` — Existing selectors file to extend (add mondaySync block)
- `e2e/mock-monday-api/server.py` (from T01) — The mock server this test runs against
- `apps/monday-sync/frontend/templates/connect.html` — Token input is `#monday-token`
- `apps/monday-sync/frontend/templates/connect_status.html` — Board checkboxes `.board-checkbox-item`, configure buttons in `.board-mapping-row`, sync controls
- `apps/monday-sync/frontend/templates/configure_columns.html` — Column mapping form selectors
- `apps/monday-sync/frontend/templates/configure_labels.html` — Label mapping form selectors
- KNOWLEDGE.md: Workspace APPS section starts collapsed, needs `.expanded` class
- KNOWLEDGE.md: E2E tests Docker stack addresses containers by compose project name

## Observability Impact

- **Phase comments in spec:** Each of the 13 phases has a comment block (`// Phase N — ...`) making Playwright failure reports instantly diagnosable — the test name + line number tells you exactly which lifecycle step failed
- **SPARQL verification phase:** Phase 10 POST to `/api/sparql` confirms RDF objects were actually created in the triplestore, not just that the UI reported "success" — catches silent sync failures
- **Playwright test report:** On failure, Playwright captures screenshots + trace showing the exact UI state at the failing assertion — available in `test-results/` directory
- **Selector compilation:** If any `SEL.mondaySync.*` selector is wrong, the test fails immediately with a clear "element not found" error pointing to the exact selector

## Expected Output

- `e2e/tests/42-monday-sync/monday-sync.spec.ts` — ~350 lines, full lifecycle E2E test
- `e2e/helpers/selectors.ts` — Extended with `mondaySync` selector block
