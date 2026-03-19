# S04: E2E Tests + User Guide — UAT

**Milestone:** M016
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for E2E test)
- Why this mode is sufficient: The E2E test exercises the full integration against the Docker test stack with mock Linear API. The docs are verified by content inspection and link validation.

## Preconditions

1. Docker test stack running: `cd /home/james/Code/SemPKM && docker compose -f docker-compose.test.yml up -d`
2. Wait for all services healthy: `docker compose -f docker-compose.test.yml ps` shows api, triplestore, frontend, mock-linear all healthy
3. Mock Linear API responding: `docker compose -f docker-compose.test.yml logs mock-linear 2>&1 | grep "Mock Linear API"` shows startup message
4. Playwright installed: `npx playwright install chromium` (if not already)

## Smoke Test

Run the mock server selftest to confirm canned responses are valid:
```
python3 e2e/mock-linear-api/server.py --selftest
```
Expected: All 6 response types pass (viewer, organization, teams, issues, states, issueUpdate).

## Test Cases

### 1. E2E test full run

1. Start the Docker test stack: `docker compose -f docker-compose.test.yml up -d`
2. Wait for services: `docker compose -f docker-compose.test.yml ps` — all 4 services healthy
3. Run: `npx playwright test e2e/tests/31-linear-sync/linear-sync.spec.ts`
4. **Expected:** All 11 phases pass:
   - Cleanup (uninstall any existing linear-sync/basic-pkm)
   - Install basic-pkm model
   - Install linear-sync app
   - Open workspace settings
   - Connect via API key
   - Select team
   - Configure sync settings
   - Trigger Sync Now
   - Verify tasks created via SPARQL (3 tasks from mock data)
   - Check admin detail page
   - Cleanup

### 2. Mock server diagnostic logging

1. With Docker test stack running, run the E2E test (test case 1)
2. After test completes, run: `docker compose -f docker-compose.test.yml logs mock-linear 2>&1 | grep "Matched query type"`
3. **Expected:** Log lines showing matched query types (viewer, organization, teams, states, issues, issueUpdate)

### 3. Chapter 34 content completeness

1. Open `docs/guide/34-linear-sync.md`
2. Verify 12 `##`-level sections exist: What Linear Sync Does, Prerequisites, Installation, Connecting Your Linear Account, Selecting a Team, Sync Configuration, Manual Sync, Understanding Sync Stats, Field Mapping, Push Sync and Bidirectional Mode, Admin Monitoring, Troubleshooting
3. Verify field mapping table has entries for: title, description, status, priority, assignee, labels, dueDate, completedDate, effort, estimate, url, externalUuid
4. Verify status sub-table has 5 mappings (Triage→todo, Backlog→todo, Todo→todo, In Progress→in-progress, Done→done)
5. Verify priority sub-table has 5 mappings (0→none, 1→critical, 2→high, 3→medium, 4→low)
6. **Expected:** All sections present, all mapping tables complete and accurate

### 4. Navigation chain integrity

1. Run: `grep "Chapter 34" docs/guide/33-context-overlay.md`
2. **Expected:** Nav footer line: `**Next:** [Chapter 34: Linear Sync](34-linear-sync.md)`
3. Run: `grep "Appendix A" docs/guide/34-linear-sync.md`
4. **Expected:** Nav footer line pointing to Appendix A
5. Run: `grep "34-linear-sync" docs/guide/README.md`
6. **Expected:** TOC entry for Chapter 34

### 5. Glossary entries

1. Run: `grep -A2 "Linear Sync\|Pull Sync\|Push Sync\|Bidirectional Sync" docs/guide/appendix-d-glossary.md`
2. **Expected:** 4 glossary entries, each with a description and cross-reference to Chapter 34
3. Verify alphabetical ordering: Bidirectional Sync < Linear Sync < Pull Sync < Push Sync

### 6. htmx proxy prefix fix

1. Run: `grep "hx-post\|hx-get\|hx-trigger" apps/linear-sync/frontend/templates/connect.html apps/linear-sync/frontend/templates/connect_status.html`
2. **Expected:** All htmx URLs start with `/app/linear-sync/` — no bare `/_fragments/` paths
3. **Expected:** Zero occurrences of `hx-post="/_fragments/` or `hx-get="/_fragments/`

### 7. Env var configurability

1. Run: `grep "LINEAR_API_URL\|LINEAR_GRAPHQL_URL\|LINEAR_TOKEN_URL" apps/linear-sync/services/linear_client.py apps/linear-sync/services/auth.py`
2. **Expected:** `os.environ.get()` calls with production URLs as defaults in both files

## Edge Cases

### Mock server receives unknown query

1. With Docker stack running, send a POST to mock-linear with an unrecognized query body:
   ```
   docker compose -f docker-compose.test.yml exec -T mock-linear curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8080/graphql -d '{"query": "{ unknownField }"}'
   ```
2. **Expected:** HTTP 404 (no matching canned response)

### Selftest without Docker

1. Run: `python3 e2e/mock-linear-api/server.py --selftest`
2. **Expected:** Exits 0 with all 6 response types validated — no Docker dependency

### Docker config validity

1. Run: `docker compose -f docker-compose.test.yml --env-file /dev/null config > /dev/null`
2. **Expected:** Exits 0 — compose file is valid YAML with all service definitions

## Failure Signals

- E2E test fails at "connect via API key" phase → htmx proxy routing bug recurred or mock server not responding
- E2E test fails at "verify tasks" phase → sync engine not creating tasks, or SPARQL query not finding them in current graph
- Mock server logs show no "Matched query type" lines → mock server not receiving requests (Docker networking issue)
- `python3 e2e/mock-linear-api/server.py --selftest` fails → canned response JSON is malformed
- `grep "34-linear-sync" docs/guide/README.md` returns empty → TOC not updated
- Any `/_fragments/` path found in htmx attributes → proxy prefix fix was reverted or incomplete

## Requirements Proved By This UAT

- This UAT proves the integration-level verification for the full M016 milestone (all SYNC requirements exercised end-to-end)
- E2E test exercises: auth flow (SYNC-01), pull sync with field mapping (SYNC-02), settings UI (SYNC-04), admin sync history (SYNC-05)
- Chapter 34 documents: all sync configuration and field mapping for user reference

## Not Proven By This UAT

- Push sync at E2E level — the mock server accepts issueUpdate mutations but the E2E test doesn't verify the push direction was triggered. Push sync is covered by 150 unit tests.
- OAuth flow — E2E test uses API key auth. OAuth requires a real Linear workspace or a more complex mock.
- Person matching (SYNC-06) — mock data includes assignee fields but the E2E test doesn't verify Person objects are created.
- Real Linear API behavior — mock server returns canned responses; actual API pagination, rate limiting, and error recovery are not exercised.

## Notes for Tester

- The Docker test stack takes ~30 seconds to become fully healthy (triplestore initialization is the bottleneck).
- If the E2E test fails at "install linear-sync," check that the `apps/linear-sync/` directory is mounted into the api container via docker-compose.test.yml.
- The mock-linear service logs are the best diagnostic for API interaction issues — check them first.
- The 3 mock issues have IDs `MOCK-1`, `MOCK-2`, `MOCK-3` — these appear in SPARQL verification queries.
- Chapter 34's field mapping tables were verified against the actual `field_mapper.py` source code, not the milestone plan.
