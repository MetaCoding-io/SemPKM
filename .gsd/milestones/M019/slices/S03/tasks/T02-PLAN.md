---
estimated_steps: 5
estimated_files: 2
---

# T02: Write Playwright E2E test and add Todoist selectors

**Slice:** S03 — E2E Tests + User Guide
**Milestone:** M019

## Description

Write the Playwright E2E test for Todoist sync following the github-sync.spec.ts phase structure. Add `todoistSync` selector block to `e2e/helpers/selectors.ts`. The test proves the full lifecycle: install → connect → sync → verify → cleanup against the Docker test stack with the mock Todoist API from T01.

Known limitation: the test will likely hit the pre-existing subprocess 500 error at the app install phase (Phase 2). This is documented across M016-M018 and is not Todoist-specific. The test should be structurally complete regardless.

## Steps

1. **Add `todoistSync` selector block to `e2e/helpers/selectors.ts`** after the existing `githubSync` block:
   ```typescript
   todoistSync: {
     patInput: '#todoist-token',
     connectBtn: '.api-key-form button[type="submit"]',
     connectStatus: '.connection-status',
     tokenPreview: '.token-preview',
     projectCheckbox: '.project-checkbox input[type="checkbox"]',
     saveProjectsBtn: '.projects-form button[type="submit"]',
     syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
     saveConfigBtn: '.sync-config-form button[type="submit"]',
     syncNowBtn: '#sync-now-btn',
     syncStats: '.sync-stats',
     statValue: '.stat-value',
   },
   ```

2. **Create `e2e/tests/37-todoist-sync/todoist-sync.spec.ts`** following `e2e/tests/32-github-sync/github-sync.spec.ts` phase structure. Import auth fixtures, SEL, and wait helpers. Single test: `'full lifecycle: install → connect → sync → verify → cleanup'`. Set `test.setTimeout(240_000)`. Accept dialog events. Phases:

   - **Phase 0 — Cleanup**: Remove todoist-sync if installed from prior run. Navigate to `/admin/apps`, look for "Todoist Sync" card, if found → go to `/admin/apps/todoist-sync` → click uninstall → wait.
   
   - **Phase 1 — Install basic-pkm**: Navigate to `/admin/models`, check if basic-pkm is installed. If not, fill `/app/models/basic-pkm` in `#model-path`, submit, wait for it to appear. Use polling `expect.toPass()` pattern.
   
   - **Phase 2 — Install todoist-sync app**: Navigate to `/admin/apps`, fill `/app/apps/todoist-sync` in install input, submit, wait for the app to appear in the list. Document in comments that this phase may hit pre-existing subprocess 500 error.
   
   - **Phase 3 — Open app settings**: Navigate to the workspace `/browser/`, expand APPS section (click section header to add `.expanded` class — per KNOWLEDGE.md, sections start collapsed). Click on "Todoist Sync" in the apps list. Wait for the connect form to appear.
   
   - **Phase 4 — Connect PAT**: Fill `test-todoist-pat-token-abc123` into `SEL.todoistSync.patInput`, click connect button. Wait for connection status to appear showing "Connected". Verify token preview and projects count are visible.
   
   - **Phase 5 — Select projects**: Wait for project checkboxes to appear (loaded via htmx). Check the first project checkbox. Click save projects button. Wait for confirmation.
   
   - **Phase 6 — Configure sync**: Click bidirectional radio button. Click save config button. Wait for sync config to be saved.
   
   - **Phase 7 — Sync Now**: Click sync now button. Wait for sync stats to appear or update. Allow generous timeout (30s) for sync operation.
   
   - **Phase 8 — Verify tasks via SPARQL**: Use `ownerRequest` to POST to `/api/sparql` with a SELECT query checking for bpkm:Task objects with `externalProvider = "todoist"`. Verify at least one task was created. Check priority mapping: the task with Todoist priority 4 should have `bpkm:priority = "critical"`.
   
   - **Phase 9 — Admin detail check**: Navigate to `/admin/apps/todoist-sync`. Verify the app detail page loads with status information.
   
   - **Phase 10 — Cleanup**: Navigate to `/admin/apps/todoist-sync`, click uninstall button, wait for completion. Navigate to `/admin/apps` to verify todoist-sync is removed.

3. **Add comment block at top of test file** documenting:
   - Purpose: proves full Todoist sync vertical against mock API
   - Mock server dependency: mock-todoist Docker service on port 8080
   - Known limitation: may hit pre-existing subprocess 500 error at Phase 2
   - PAT token used: `test-todoist-pat-token-abc123` (must match mock server's accepted token)

4. **Verify test compiles**: `npx playwright test e2e/tests/37-todoist-sync/ --list`

5. **Verify selectors match templates**: Cross-check each selector against the actual template HTML IDs/classes from `apps/todoist-sync/frontend/templates/connect.html` and `connect_status.html`.

## Must-Haves

- [ ] `todoistSync` selectors in `e2e/helpers/selectors.ts` match actual template IDs/classes
- [ ] E2E test covers all phases: cleanup → install → connect → select projects → configure → sync → SPARQL verify → admin → cleanup
- [ ] SPARQL verification checks for `externalProvider = "todoist"` tasks and priority inversion (Todoist 4 → critical)
- [ ] Pre-existing subprocess issue documented in test comments
- [ ] Test uses the correct mock PAT token: `test-todoist-pat-token-abc123`
- [ ] APPS section expansion handled (click header to add `.expanded` class)

## Verification

- `npx playwright test e2e/tests/37-todoist-sync/ --list` — shows the test without TypeScript errors
- Selectors cross-checked against template HTML: `rg "todoist-token|api-key-form|connection-status|project-checkbox|sync-config-form|sync-now-btn|sync-stats" apps/todoist-sync/frontend/templates/`

## Inputs

- `e2e/tests/32-github-sync/github-sync.spec.ts` — Reference implementation for phase structure, dialog handling, SPARQL verification pattern
- `e2e/helpers/selectors.ts` — Existing githubSync block as pattern for todoistSync
- `e2e/fixtures/auth.ts` — Auth fixture for ownerPage/ownerRequest
- `apps/todoist-sync/frontend/templates/connect.html` — Template IDs: `#todoist-token`, `.api-key-form`
- `apps/todoist-sync/frontend/templates/connect_status.html` — Template classes: `.connection-status`, `.token-preview`, `.sync-config-form`, `#sync-now-btn`, `.sync-stats`
- `apps/todoist-sync/frontend/templates/projects.html` — Template classes: `.project-checkbox`, `.projects-form`
- T01 mock server accepts `test-todoist-pat-token-abc123` as valid PAT token
- KNOWLEDGE.md: "Workspace explorer sections start collapsed" — must click header to expand APPS section

## Observability Impact

- **E2E test phases:** Each phase (0–10) is commented with a clear header in the test file. Playwright trace/report shows exactly which phase failed.
- **SPARQL verification:** Phase 8 queries the triplestore for `externalProvider = "todoist"` tasks and priority mapping, producing observable pass/fail evidence that sync actually created data.
- **Selector cross-check:** `rg` command against templates verifies selectors match real DOM IDs/classes — catches stale selectors before runtime.
- **Failure visibility:** `npx playwright test --list` catches TypeScript compilation errors. Runtime failures show the phase number and specific assertion in Playwright HTML report.

## Expected Output

- `e2e/tests/37-todoist-sync/todoist-sync.spec.ts` — ~280-line E2E test with all 11 phases
- `e2e/helpers/selectors.ts` — `todoistSync` selector block added
