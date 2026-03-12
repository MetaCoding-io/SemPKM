# S06: Federation Bug Fix & Dual-Instance Testing

**Goal:** Fix the Sync Now auto-discovery bug, stand up a dual-instance Docker Compose for federation testing, and prove the invite → accept → sync flow works end-to-end between two real SemPKM instances.
**Demo:** Run `npx playwright test --project=federation` — the E2E test sets up two instances, creates a shared graph on A, simulates an invitation to B, B accepts, A copies an object in, B syncs and retrieves it.

## Must-Haves

- `discover_remote_instance_url()` filters members to HTTP(S) URLs only — `urn:` local IDs are skipped
- `syncSharedGraph()` in federation.js sends empty body (no `remote_instance_url: ''`)
- `docker-compose.federation-test.yml` stands up two complete SemPKM stacks (separate triplestores, DBs, ports) on a shared Docker network
- Federation E2E test scripts manage the dual-instance lifecycle (start, wait-for-healthy, stop)
- Playwright E2E test proves: setup both instances → publish WebIDs → create shared graph → simulate invitation → accept → copy object → sync → verify object appears on instance B

## Proof Level

- This slice proves: integration
- Real runtime required: yes (two Docker-based SemPKM instances)
- Human/UAT required: no (automated Playwright test)

## Verification

- `cd backend && .venv/bin/pytest tests/test_federation_discovery.py -v` — unit tests for `discover_remote_instance_url` filtering pass
- `docker compose -f docker-compose.federation-test.yml up -d --build && e2e/scripts/wait-for-federation.sh` — both instances start and report healthy
- `cd e2e && npx playwright test tests/18-federation/federation-sync.spec.ts --project=chromium` — E2E test passes

## Observability / Diagnostics

- Runtime signals: federation sync endpoint logs discovered remote URL and sync result counts; `discover_remote_instance_url` logs warning when no HTTP(S) members found
- Inspection surfaces: `docker compose -f docker-compose.federation-test.yml logs api-a` / `api-b` for per-instance logs; `/api/health` on both instances
- Failure visibility: sync endpoint returns structured `SyncResult` with `pulled`, `applied`, `errors` fields; HTTP 400 with descriptive detail on discovery failure
- Redaction constraints: none (test environment uses fixed non-secret keys)

## Integration Closure

- Upstream surfaces consumed: `backend/app/federation/service.py` (discover, sync, accept, copy), `backend/app/federation/router.py` (sync endpoint), `frontend/static/js/federation.js` (syncSharedGraph), `backend/app/webid/router.py` (username/publish endpoints), existing `docker-compose.test.yml` pattern, existing `e2e/fixtures/auth.ts` pattern
- New wiring introduced in this slice: `docker-compose.federation-test.yml` (dual-instance stack), `e2e/scripts/start-federation-env.sh` + `wait-for-federation.sh` (lifecycle scripts), Playwright federation project in `playwright.config.ts`, federation E2E test
- What remains before the milestone is truly usable end-to-end: S07 (Obsidian import) — independent of federation

## Tasks

- [x] **T01: Fix Sync Now auto-discovery bug and add unit tests** `est:45m`
  - Why: FED-11 — the Sync Now button fails because `discover_remote_instance_url()` doesn't filter out `urn:` local WebIDs, producing nonsense URLs. The frontend also sends `{ remote_instance_url: '' }` instead of omitting the field (minor but messy).
  - Files: `backend/app/federation/service.py`, `frontend/static/js/federation.js`, `backend/tests/test_federation_discovery.py`
  - Do: (1) In `discover_remote_instance_url()`, filter SPARQL results to only `http://` or `https://` WebIDs — skip `urn:` members. Add a warning log when no HTTP(S) members are found. (2) In `federation.js`, change `syncSharedGraph()` to send `{}` body instead of `{ remote_instance_url: '' }`. (3) Write unit tests for discovery: test with HTTP member present, test with only `urn:` members (should return None), test with mixed members.
  - Verify: `cd backend && .venv/bin/pytest tests/test_federation_discovery.py -v` passes
  - Done when: discovery correctly filters to HTTP(S) members, JS sends clean body, all unit tests pass

- [x] **T02: Create dual-instance docker-compose and lifecycle scripts** `est:1h`
  - Why: FED-12 — federation cannot be tested with a single instance. Two complete SemPKM stacks are needed on a shared network so they can reach each other's APIs for sync, WebID resolution, and patch export.
  - Files: `docker-compose.federation-test.yml`, `e2e/scripts/start-federation-env.sh`, `e2e/scripts/wait-for-federation.sh`, `e2e/scripts/stop-federation-env.sh`
  - Do: (1) Create `docker-compose.federation-test.yml` with two full stacks: `triplestore-a`/`api-a`/`frontend-a` on ports 3911/8911, `triplestore-b`/`api-b`/`frontend-b` on ports 3912/8912, shared `sempkm-federation` network. Each instance gets its own volumes, `BASE_NAMESPACE`, `APP_BASE_URL` (set to `http://frontend-a:80` / `http://frontend-b:80`), and `SECRET_KEY`. (2) Write `start-federation-env.sh` (teardown → build → up), `wait-for-federation.sh` (poll both `localhost:3911/api/health` and `localhost:3912/api/health`), `stop-federation-env.sh` (down -v). (3) Verify both stacks start and health endpoints respond.
  - Verify: `e2e/scripts/start-federation-env.sh && e2e/scripts/wait-for-federation.sh` succeeds; `curl -sf http://localhost:3911/api/health && curl -sf http://localhost:3912/api/health` return OK
  - Done when: two SemPKM instances run independently and are reachable from each other on the Docker network

- [x] **T03: Add Playwright federation project and E2E sync test** `est:1h30m`
  - Why: FED-13 — the full invite → accept → sync flow must be proven between two real instances. This is the integration test that validates federation actually works.
  - Files: `e2e/playwright.config.ts`, `e2e/tests/18-federation/federation-sync.spec.ts`, `e2e/helpers/api-client.ts`
  - Do: (1) Add a `federation` project to `playwright.config.ts` that matches `18-federation/*.spec.ts`, uses `http://localhost:3911` as base URL, and runs in single-worker sequential mode. (2) Extend `ApiClient` with federation helper methods: `setWebIDUsername(name)`, `publishWebID()`, `createSharedGraph(name, model)`, `getSharedGraphs()`, `copyObjectToSharedGraph(graphId, objectIri)`, `syncSharedGraph(graphId)`, `listSharedGraphObjects(graphId)`. (3) Write the E2E test that: sets up both instances (claim via setup tokens read from different compose services), publishes WebIDs on both, creates a shared graph on instance A, simulates the invitation receipt on B by directly inserting the Offer notification into B's triplestore via B's SPARQL endpoint (bypasses HTTP Signatures — documented as hybrid approach in research), accepts the invitation on B via API, creates and copies an object on A to the shared graph, triggers sync on B, and asserts the object appears in B's shared graph objects list. (4) Add `readFederationSetupToken(instance: 'a' | 'b')` helper to auth fixtures.
  - Verify: `cd e2e && npx playwright test tests/18-federation/federation-sync.spec.ts --project=chromium` passes end-to-end
  - Done when: Playwright test exercises the full federation flow between two live Docker instances and passes

## Files Likely Touched

- `backend/app/federation/service.py`
- `frontend/static/js/federation.js`
- `backend/tests/test_federation_discovery.py`
- `docker-compose.federation-test.yml`
- `e2e/scripts/start-federation-env.sh`
- `e2e/scripts/wait-for-federation.sh`
- `e2e/scripts/stop-federation-env.sh`
- `e2e/playwright.config.ts`
- `e2e/tests/18-federation/federation-sync.spec.ts`
- `e2e/helpers/api-client.ts`
- `e2e/fixtures/auth.ts`
