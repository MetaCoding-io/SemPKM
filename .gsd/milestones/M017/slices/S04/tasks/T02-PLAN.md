---
estimated_steps: 7
estimated_files: 2
---

# T02: Playwright E2E test for GitHub sync lifecycle

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M017

## Description

Write a Playwright E2E test covering the full GitHub sync lifecycle: install → configure → sync → verify tasks and PR edges → verify diagnostic surface → cleanup. This is the primary runtime validation for requirements GH-01 through GH-07, proving the entire stack works end-to-end against the mock GitHub API server (from T01) running in Docker.

Follow `e2e/tests/31-linear-sync/linear-sync.spec.ts` as the reference pattern — same test structure, import pattern, phase organization, and timeout strategy. Adapt selectors for github-sync's template IDs/classes.

**Skill note:** Load the `test` skill if available for test framework conventions.

## Steps

1. **Add `githubSync` selector block to `e2e/helpers/selectors.ts`** — Insert before the closing `} as const;`. Based on the actual template selectors from `apps/github-sync/frontend/templates/`:
   ```typescript
   githubSync: {
     patInput: '#github-pat',
     connectBtn: '.api-key-form button[type="submit"]',
     connectStatus: '.connection-status',
     username: '.username',
     repoCheckbox: '.repo-checkbox-item input[type="checkbox"]',
     saveReposBtn: '.repos-section button[type="submit"]',
     syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
     saveConfigBtn: '.sync-config-form button[type="submit"]',
     syncNowBtn: '#sync-now-btn',
     syncStats: '.sync-stats',
     statValue: '.stat-value',
   },
   ```

2. **Create `e2e/tests/32-github-sync/github-sync.spec.ts`** — Import `test, expect, BASE_URL` from auth fixture, `SEL` from selectors, wait helpers. Wrap in `test.describe('GitHub Sync', ...)` with a single serial test.

3. **Phase 0 — Cleanup** — Navigate to `/admin/apps`, check for existing github-sync card. If found, navigate to `/admin/apps/github-sync`, click uninstall button, wait for completion. Navigate back to apps list.

4. **Phase 1 — Prerequisite (basic-pkm)** — Navigate to `/admin/models`. If basic-pkm card not visible, install from `/app/models/basic-pkm`. Wait for model card to appear.

5. **Phase 2 — Install github-sync** — Navigate to `/admin/apps`. Enter `/app/apps/github-sync` in the app install input. Submit. Poll for the app card to show "Running" status (retry with page reloads, up to 60s).

6. **Phases 3-7 — Connect and configure** in the workspace:
   - Phase 3: Navigate to `/browser/`. Click APPS section header to expand (collapsed by default per KNOWLEDGE.md). Wait for github-sync entry to appear. Click it.
   - Phase 4: Wait for PAT input (`SEL.githubSync.patInput`). Fill `ghp_testtoken123456789`. Click connect button. Wait for `.connection-status` with "Connected" text and `.username` with "test-user".
   - Phase 5: Wait for repo checkboxes. Check the first checkbox (`test-owner/test-repo`). Click Save Repos.
   - Phase 6: Click bidirectional radio. Click Save Config.
   - Phase 7: Click Sync Now button. Wait for sync stats section to appear and show pull result. Assert that the pull status is "success" or "ok" and created count ≥ 2.

7. **Phases 8-11 — Verify and cleanup**:
   - Phase 8: Use `ownerRequest` to execute SPARQL query `SELECT (COUNT(?s) AS ?count) WHERE { ?s a <urn:bpkm:Task> }` via POST to `${BASE_URL}/api/sparql`. Parse count, assert ≥ 3 (2 issues + 1 PR).
   - Phase 9: SPARQL query for PR-to-issue edge: `ASK WHERE { ?pr <urn:bpkm:dependsOn> ?issue . ?pr <urn:bpkm:externalProvider> "github-pr" }`. Assert true.
   - Phase 10: Navigate to `/admin/apps`. Verify github-sync card shows "Running".
   - Phase 11: Navigate to `/admin/apps/github-sync`. Click uninstall. Wait for completion.

**Important constraints from KNOWLEDGE.md:**
- Explorer APPS section starts collapsed — must click the section header with `onclick="this.parentElement.classList.toggle('expanded')"` to expand before clicking the leaf.
- All htmx URLs in templates use `/app/github-sync/` proxy prefix — the test interacts via the workspace proxy, not direct app routes.
- SPARQL API scopes to current state graph only — queries bpkm:Task objects in the current graph.
- Use `test.setTimeout(240_000)` for generous timeout covering Docker operations.
- Accept dialog events for hx-confirm on uninstall/disconnect: `ownerPage.on('dialog', (dialog) => dialog.accept())`.

## Must-Haves

- [ ] `githubSync` selector block added to `e2e/helpers/selectors.ts`
- [ ] E2E test covers all 12 phases (cleanup → prerequisite → install → workspace open → connect → repos → config → sync now → SPARQL verify tasks → SPARQL verify PR edge → admin detail → cleanup)
- [ ] SPARQL verification confirms ≥3 bpkm:Task objects (2 issues + 1 PR)
- [ ] SPARQL verification confirms bpkm:dependsOn edge from PR task to issue task
- [ ] Test verifies sync stats diagnostic surface shows pull result status and created count
- [ ] Test handles APPS section collapsed state (clicks header to expand)
- [ ] Test uses 240s timeout for full lifecycle

## Verification

- `npx playwright test e2e/tests/32-github-sync/github-sync.spec.ts` passes against the Docker test stack (port 3901 with mock-github service running)
- All 12 phases complete without timeout
- SPARQL assertions confirm task creation and PR edge linking

## Observability Impact

- Signals added/changed: E2E test exercises and asserts on sync stats UI panel — proving the diagnostic surface is rendered and readable by both humans and automated tests
- How a future agent inspects this: Check `.stat-value` elements in sync stats section for pull result status, created count, and error count
- Failure state exposed: Phase-level test structure means Playwright error messages indicate which phase failed, with screenshot on failure

## Inputs

- `e2e/tests/31-linear-sync/linear-sync.spec.ts` — Reference test to clone (250 lines, 12-phase structure)
- `e2e/helpers/selectors.ts` — Selector registry to extend with `githubSync` block
- `e2e/fixtures/auth.ts` — Auth fixture providing `ownerPage` and `ownerRequest`
- `e2e/helpers/wait-for.ts` — `waitForIdle` and `waitForWorkspace` helpers
- `apps/github-sync/frontend/templates/connect.html` — Template with `#github-pat`, `.api-key-form` selectors
- `apps/github-sync/frontend/templates/connect_status.html` — Template with `.connection-status`, `.repo-checkbox-item`, `.sync-config-form`, `#sync-now-btn`, `.sync-stats`, `.stat-value` selectors
- T01 output: mock-github-api server running in Docker providing canned responses
- KNOWLEDGE.md: APPS section starts collapsed, SPARQL API scopes to current graph only

## Expected Output

- `e2e/tests/32-github-sync/github-sync.spec.ts` — Complete E2E test file (~250-300 lines) with 12 phases
- `e2e/helpers/selectors.ts` — Updated with `githubSync` selector block
