---
estimated_steps: 7
estimated_files: 3
---

# T02: Wire Docker compose, add selectors, write Playwright E2E spec

**Slice:** S04 — E2E tests + mock server + user guide
**Milestone:** M022

## Description

Wire the mock Asana server into the Docker test stack, add E2E selectors for the Asana Sync UI, and write the Playwright E2E test that exercises the complete lifecycle: install → connect → configure field mapping → sync → verify → cleanup. This is the integration-level proof for the entire M022 milestone.

The novel phase compared to prior sync app E2E tests is **Phase 4 (field mapping configuration)** — after project selection, the test clicks "Discover Fields", waits for htmx swap, then configures section-based status mapping and priority mapping before saving. The research recommends section-based status mapping for the E2E test because it's simpler to verify (static table rendering, no JS-driven dynamic rendering).

**Reference:** `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` (304 lines) — closest pattern (non-OAuth PAT/credentials auth).

## Steps

1. **Read reference files** for patterns:
   - `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` — E2E spec structure (phases 0-6, selectors, SPARQL verification)
   - `e2e/helpers/selectors.ts` — existing selector blocks (caldavCalendarSync is the closest pattern)
   - `docker-compose.test.yml` — existing mock service definitions

2. **Update `docker-compose.test.yml`**:
   - Add env vars to the `api` service's `environment` block:
     ```
     ASANA_API_URL: http://mock-asana:8080/api/1.0
     ASANA_TOKEN_URL: http://mock-asana:8080/-/oauth_token
     ```
   - Add `mock-asana` to the `api` service's `depends_on` block with `condition: service_healthy`
   - Add the `mock-asana` service definition (identical pattern to mock-caldav):
     ```yaml
     mock-asana:
       image: python:3.12-slim
       volumes:
         - ./e2e/mock-asana-api:/app:ro
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

3. **Add `asanaSync` selector block to `e2e/helpers/selectors.ts`** — insert before the closing `} as const;`:
   ```typescript
   asanaSync: {
     patInput: '#asana-pat',
     connectBtn: '.api-key-form button[type="submit"]',
     connectStatus: '.connection-status',
     projectCheckbox: '.project-checkbox-item input[type="checkbox"]',
     saveProjectsBtn: '.projects-section button[type="submit"]',
     discoverFieldsBtn: '.discover-section button[type="submit"]',
     statusSourceSection: 'input[name="status_source"][value="section"]',
     saveMappingBtn: '.field-mapping-form button[type="submit"]',
     syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
     saveConfigBtn: '.sync-config-form button[type="submit"]',
     syncNowBtn: '#sync-now-btn',
     syncStats: '.sync-stats',
     statValue: '.stat-value',
   },
   ```

4. **Create `e2e/tests/40-asana-sync/` directory and write `asana-sync.spec.ts`** (~350-400 lines). Follow the CalDAV spec structure:

   **Phase 0 — Cleanup:** Navigate to `/admin/apps`, check if asana-sync exists, uninstall if so.

   **Phase 1 — Install basic-pkm model:** Navigate to `/admin/models`, install `/app/models/basic-pkm` if not already present. Wait for it to appear.

   **Phase 2 — Install asana-sync app:** Navigate to `/admin/apps`, fill install input with `/app/apps/asana-sync`, submit. Poll until app card shows "Running" status (120s timeout with retries). Wait 5s for subprocess socket.

   **Phase 3 — PAT connect:** Navigate to `/admin/apps/asana-sync`. Wait for connect form to render. Fill `SEL.asanaSync.patInput` with `"test-asana-pat-token-abc123"`. Click `SEL.asanaSync.connectBtn`. Wait for `SEL.asanaSync.connectStatus` to show "Connected". Verify email "test@example.com" appears.

   **Phase 4 — Configure field mapping:** This is the novel phase:
   - Check all project checkboxes (`SEL.asanaSync.projectCheckbox`) and click `SEL.asanaSync.saveProjectsBtn`. Wait for page to settle.
   - Click `SEL.asanaSync.discoverFieldsBtn`. Wait for network idle (htmx swap delivers discovered fields).
   - Select section-based status mapping: click `SEL.asanaSync.statusSourceSection` radio. The section mapping table should be visible.
   - Click `SEL.asanaSync.saveMappingBtn`. Wait for save confirmation.

   **Phase 5 — Sync and verify:**
   - Click `SEL.asanaSync.syncNowBtn`. Wait for sync to complete (wait for stat values to appear).
   - Verify sync stats show created count > 0.
   - Run SPARQL verification via `ownerRequest`: `POST /api/sparql` with query:
     ```sparql
     PREFIX bpkm: <https://test.example.org/data/def/basic-pkm/>
     PREFIX dcterms: <http://purl.org/dc/terms/>
     SELECT ?label WHERE {
       ?s a bpkm:Task ;
          dcterms:title ?label .
       FILTER(CONTAINS(STR(?label), "Review"))
     }
     ```
   - Assert at least 1 result (proves tasks were synced from mock).

   **Phase 6 — Admin detail + cleanup:**
   - Navigate to `/admin/apps/asana-sync`. Verify detail page loads.
   - Uninstall the app. Wait for redirect to apps list.

   **Important constraints from KNOWLEDGE.md:**
   - Workspace explorer sections start collapsed — expand APPS section before asserting
   - PAT token: `test-asana-pat-token-abc123` (must match mock server VALID_TOKEN)
   - All htmx URLs route through app proxy at `/app/asana-sync/`
   - Accept dialog handler for hx-confirm on disconnect/uninstall
   - 240s test timeout for Docker operations

5. **Verify docker-compose syntax:** `docker compose -f docker-compose.test.yml config --quiet`

6. **Verify E2E spec structure:** Confirm all 7 phases present (0-6), correct selector references, SPARQL verification query.

7. **Verify selectors:** `grep -c "asanaSync" e2e/helpers/selectors.ts` ≥ 1.

## Must-Haves

- [ ] docker-compose.test.yml has mock-asana service with healthcheck and env vars on api service
- [ ] selectors.ts has asanaSync block with PAT input, connect button, project checkbox, discover fields, status source, save mapping, sync now, sync stats selectors
- [ ] E2E spec has Phase 0 (cleanup), Phase 1 (model install), Phase 2 (app install + Running), Phase 3 (PAT connect), Phase 4 (field mapping), Phase 5 (sync + SPARQL verify), Phase 6 (cleanup)
- [ ] SPARQL verification query proves tasks were synced from mock data

## Verification

- `docker compose -f docker-compose.test.yml config --quiet` — no errors
- `grep -c "asanaSync" e2e/helpers/selectors.ts` — returns ≥ 1
- E2E spec file exists at `e2e/tests/40-asana-sync/asana-sync.spec.ts` with all 7 phases
- Spec uses `test-asana-pat-token-abc123` matching mock server VALID_TOKEN
- Spec imports from `../../fixtures/auth` and `../../helpers/selectors`

## Inputs

- `e2e/mock-asana-api/server.py` (from T01) — VALID_TOKEN value, canned task names for SPARQL verification
- `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` — reference E2E pattern
- `e2e/helpers/selectors.ts` — existing selectors to extend
- `docker-compose.test.yml` — existing compose file to extend
- `apps/asana-sync/frontend/templates/connect.html` — PAT form selectors (`#asana-pat`, `.api-key-form`)
- `apps/asana-sync/frontend/templates/connect_status.html` — field mapping selectors (`.projects-section`, `.discover-section`, `.field-mapping-form`, `#sync-now-btn`, `.sync-stats`)

## Expected Output

- `docker-compose.test.yml` — updated with mock-asana service + env vars
- `e2e/helpers/selectors.ts` — updated with asanaSync selector block
- `e2e/tests/40-asana-sync/asana-sync.spec.ts` — ~350-400 line Playwright E2E spec with 7 phases

## Observability Impact

- **Docker healthcheck:** `mock-asana` service has a healthcheck probing `GET /health` — Docker reports `healthy/unhealthy` in `docker compose ps`, and the `api` service won't start until `mock-asana` is healthy.
- **E2E test phases:** Each phase is labeled with a `// Phase N` comment and produces Playwright-level pass/fail. Phase 5b SPARQL verification confirms data presence in the triplestore.
- **Mock request logging:** Every request to mock-asana is logged to stderr as `[mock-asana] METHOD /path → STATUS`, visible in `docker compose logs mock-asana`.
- **Failure visibility:** Auth errors return `401 {"errors": [{"message": "Not Authorized"}]}`. SPARQL verification failures report the actual labels found vs. expected. Selector timeouts report which element was not found.
