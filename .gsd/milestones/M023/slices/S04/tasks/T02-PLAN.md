---
estimated_steps: 5
estimated_files: 3
---

# T02: Wire Docker integration, add selectors, and write Playwright E2E test

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M023

## Description

Connect the mock Jira API server to the Docker test stack, add Jira-specific CSS selectors to the shared helpers file, and write the Playwright E2E test that exercises the full Jira sync lifecycle. The E2E test follows the exact 12-phase pattern established by `github-sync.spec.ts` but adapted for Jira's 3-field connect form, project selection, and Jira-specific SPARQL verification queries.

## Steps

1. **Add `mock-jira` service to `docker-compose.test.yml`:**
   - Add immediately after the `mock-github` service block (around line 90). Use the identical pattern:
     ```yaml
     mock-jira:
       image: python:3.12-slim
       volumes:
         - ./e2e/mock-jira-api:/app:ro
       working_dir: /app
       command: ["python", "server.py"]
       healthcheck:
         test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
         interval: 3s
         timeout: 3s
         retries: 5
       networks:
         - sempkm-test
     ```
   - Add `JIRA_API_URL: http://mock-jira:8080` to the `api` service `environment` section (after `GITHUB_API_URL`)
   - Add `mock-jira: condition: service_healthy` to the `api` service `depends_on` section (after `mock-github`)

2. **Add `jiraSync` selector block to `e2e/helpers/selectors.ts`:**
   - Add after the `linearSync` block (around line 200), before the closing `} as const;`:
     ```typescript
     // Jira Sync E2E
     jiraSync: {
       emailInput: '#jira-email',
       tokenInput: '#jira-token',
       siteUrlInput: '#jira-site-url',
       connectBtn: '.credentials-form button[type="submit"]',
       connectStatus: '.connection-status',
       siteUrl: '.site-url',
       projectCheckbox: '.project-checkbox-item input[type="checkbox"]',
       saveProjectsBtn: '.projects-section button[type="submit"]',
       syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
       saveConfigBtn: '.sync-config-form button[type="submit"]',
       syncNowBtn: '#sync-now-btn',
       syncStats: '.sync-stats',
       statValue: '.stat-value',
     },
     ```

3. **Create `e2e/tests/41-jira-sync/jira-sync.spec.ts`** following `e2e/tests/32-github-sync/github-sync.spec.ts` as the reference. Write the full test with these phases:

   **Phase 0 — Cleanup:** Navigate to `/admin/apps`. If "Jira Sync" card exists, go to `/admin/apps/jira-sync`, click uninstall, wait, return to apps list.

   **Phase 1 — Prerequisite:** Navigate to `/admin/models`. If basic-pkm not installed, install from `/app/models/basic-pkm`. Poll until it appears.

   **Phase 2 — Install jira-sync:** Navigate to `/admin/apps`. Fill install input with `/app/apps/jira-sync`. Click submit. Poll until "Jira Sync" card shows "Running" status. Wait 5s for subprocess startup.

   **Phase 3 — Open app in workspace:** Navigate to `/browser/`. Wait for workspace. Find `#section-apps`, expand if collapsed (check `.expanded` class — KNOWLEDGE.md says sections start collapsed). Click "Jira Sync" tree leaf. Wait for `#connect-content` to appear (with retry loop like github test).

   **Phase 4 — Connect:** Fill `SEL.jiraSync.emailInput` with `test@example.com`. Fill `SEL.jiraSync.tokenInput` with `fake-jira-token-12345`. Fill `SEL.jiraSync.siteUrlInput` with `testcompany.atlassian.net`. Click `SEL.jiraSync.connectBtn`. Wait for `.connection-status` to show "Connected". **This is the key difference from GitHub** — 3 fields instead of 1.

   **Phase 5 — Select project:** Wait for project checkboxes. Check the first project checkbox. Click save projects button. Wait for htmx swap. Verify still connected.

   **Phase 6 — Configure sync:** Check bidirectional radio. Click save config. Wait for htmx swap. Verify still connected.

   **Phase 7 — Sync Now:** Click sync now button. Wait 5s + network idle. Verify sync stats visible. Check "Last Pull" section for success status. Verify created count ≥ 2.

   **Phase 8 — Verify tasks via SPARQL:** POST to `/api/sparql` with `SELECT (COUNT(?s) AS ?count) WHERE { ?s a <urn:sempkm:model:basic-pkm:Task> . }`. Expect count ≥ 2 (PROJ-1 + PROJ-2 become Tasks; PROJ-3 Epic becomes Milestone).

   **Phase 9 — Verify Epic→Milestone via SPARQL:** POST to `/api/sparql` with ASK query:
   ```sparql
   ASK WHERE {
     ?m a <urn:sempkm:model:basic-pkm:Milestone> .
     ?m <urn:sempkm:model:basic-pkm:externalProvider> "jira" .
   }
   ```
   Expect `boolean: true`.

   **Phase 9b — Verify dependsOn edge via SPARQL:** POST to `/api/sparql` with ASK query:
   ```sparql
   ASK WHERE {
     ?blocked <urn:sempkm:model:basic-pkm:dependsOn> ?blocker .
     ?blocked <urn:sempkm:model:basic-pkm:externalProvider> "jira" .
   }
   ```
   Expect `boolean: true`.

   **Phase 10 — Admin verification:** Navigate to `/admin/apps`. Verify "Jira Sync" card shows "Running".

   **Phase 11 — Cleanup:** Navigate to `/admin/apps/jira-sync`. Click uninstall. Verify card no longer appears.

4. **Use correct imports and fixtures:**
   ```typescript
   import { test, expect, BASE_URL } from '../../fixtures/auth';
   import { SEL } from '../../helpers/selectors';
   import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';
   ```
   - Accept dialogs: `ownerPage.on('dialog', (dialog) => dialog.accept());`
   - Set timeout: `test.setTimeout(240_000);`
   - Use `ownerPage` and `ownerRequest` from the auth fixture

5. **Verify all file changes are consistent:**
   - Grep for `jiraSync` in selectors.ts → should exist
   - Grep for `mock-jira` in docker-compose.test.yml → should appear in service definition, env var, and depends_on
   - E2E test file should have all phase comments

## Must-Haves

- [ ] `docker-compose.test.yml` has `mock-jira` service with correct image, volume mount, healthcheck, and network
- [ ] `JIRA_API_URL: http://mock-jira:8080` in api environment
- [ ] `mock-jira: condition: service_healthy` in api depends_on
- [ ] `jiraSync` selector block in `selectors.ts` with all 13 selectors matching the template HTML element IDs/classes
- [ ] E2E test has all 12 phases: cleanup, prerequisite, install, open workspace, connect (3 fields), select projects, configure sync, sync now, verify tasks, verify milestone, verify dependsOn, admin, cleanup
- [ ] E2E test uses correct SPARQL queries for verification (Task count, Milestone ASK, dependsOn ASK)
- [ ] Test timeout set to 240s
- [ ] Dialog auto-accept configured

## Verification

- `grep -c "jiraSync" e2e/helpers/selectors.ts` returns 1
- `grep -c "mock-jira" docker-compose.test.yml` returns at least 3 (service name, env var reference, depends_on)
- `grep -c "JIRA_API_URL" docker-compose.test.yml` returns 1
- `grep -c "Phase" e2e/tests/41-jira-sync/jira-sync.spec.ts` returns at least 10

## Inputs

- `e2e/mock-jira-api/server.py` — from T01, the mock server that Docker will run
- `e2e/mock-github-api/server.py` — reference for Docker service pattern in docker-compose.test.yml
- `e2e/tests/32-github-sync/github-sync.spec.ts` — reference E2E test to clone (298 lines, 12 phases)
- `e2e/helpers/selectors.ts` — existing selectors file to extend with `jiraSync` block
- `docker-compose.test.yml` — existing Docker test stack to extend
- `apps/jira-sync/frontend/templates/connect.html` — form IDs: `#jira-email`, `#jira-token`, `#jira-site-url`, class `.credentials-form`
- `apps/jira-sync/frontend/templates/connect_status.html` — selectors: `.connection-status`, `.project-checkbox-item`, `.projects-section`, `.sync-config-form`, `#sync-now-btn`, `.sync-stats`
- KNOWLEDGE.md: workspace APPS section starts collapsed (needs `.expanded` class toggle), htmx URLs already use proxy prefix

## Observability Impact

- **Docker healthcheck:** `mock-jira` service uses `urllib.request.urlopen('http://localhost:8080/health')` healthcheck — visible via `docker compose ps mock-jira` (healthy/unhealthy state). API container depends_on this healthcheck, so startup failures block the entire test stack.
- **Container logs:** All mock-jira HTTP requests logged to stderr with `[mock-jira]` prefix — inspect via `docker compose -f docker-compose.test.yml logs mock-jira`.
- **E2E test phases:** Each phase is labeled with a comment block (`Phase 0 — Cleanup`, etc). Playwright's test runner reports which phase failed with line numbers.
- **SPARQL verification:** Phases 8/9/9b use SPARQL queries to verify RDF graph state after sync. Failed assertions show the actual count/boolean vs expected, making it clear whether the sync engine or the mock is at fault.
- **Selector mismatches:** If template IDs change, `jiraSync` selectors in `selectors.ts` will cause Playwright `toBeVisible` timeouts with the exact CSS selector that failed.
- **Failure signals:** A failing E2E test produces Playwright trace files and screenshots in `e2e/test-results/`. The phase comment tells you which lifecycle step broke.

## Expected Output

- `docker-compose.test.yml` — modified with mock-jira service, JIRA_API_URL env var, depends_on entry
- `e2e/helpers/selectors.ts` — modified with jiraSync selector block
- `e2e/tests/41-jira-sync/jira-sync.spec.ts` — new Playwright E2E test (~300 lines, 12 phases)
