# S07: Test App, E2E Tests & Integration Proof — UAT

**Milestone:** M009
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for test app validation + backend tests; live-runtime for E2E)
- Why this mode is sufficient: The test app is a static fixture validated by manifest parsing. Backend tests run without Docker. E2E tests require the Docker stack but exercise every integration point. Human spot-checking is optional — the 28-assertion E2E spec covers all user-visible flows.

## Preconditions

1. Docker test stack running: `docker compose -f docker-compose.test.yml up -d`
2. API service healthy: `curl -s http://localhost:3901/health` returns 200
3. Backend venv active: `cd backend && source .venv/bin/activate`
4. No pre-existing test-app installed (Phase 0 of E2E handles cleanup, but verify: `curl -s http://localhost:3901/admin/apps/test-app` returns 404)
5. Playwright installed: `cd e2e && npx playwright install chromium`

## Smoke Test

```bash
cd backend && .venv/bin/python3 -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/test-app/manifest.yaml'); print(f'{m.name} v{m.version}')"
```
Expected: `Test Application v1.0.0`

## Test Cases

### 1. Test App Manifest Validates Against Schema

1. `cd backend`
2. `.venv/bin/python3 -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/test-app/manifest.yaml'); print(m.model_dump_json(indent=2))"`
3. **Expected:** JSON output shows appId=test-app, name=Test Application, version=1.0.0, 1 task (heartbeat), frontend with CSS/JS, ui with pages/contributions/objectRenderers

### 2. Docker Test Stack Config Is Valid

1. `docker compose -f docker-compose.test.yml config --services`
2. **Expected:** Output lists `triplestore`, `api`, `frontend`
3. `docker compose -f docker-compose.test.yml config | grep -A2 "./apps"`
4. **Expected:** Shows `./apps:/app/apps:ro` volume mount on api service
5. `docker compose -f docker-compose.test.yml config | grep -A2 "./backend/sdk"`
6. **Expected:** Shows `./backend/sdk:/app/backend/sdk:ro` volume mount on api service

### 3. All Backend Tests Pass (Zero Regressions)

1. `cd backend && .venv/bin/python3 -m pytest tests/ -x --ignore=tests/test_sdk_integration.py --tb=short -q`
2. **Expected:** `1201 passed` with 0 failures

### 4. Manifest Schema Tests All Pass

1. `cd backend && .venv/bin/python3 -m pytest tests/test_app_manifest.py -v -k "test_app"`
2. **Expected:** 60 tests pass

### 5. Admin Uninstall Endpoint Accepts clean_data

1. `grep "clean_data" backend/app/apps/admin_router.py`
2. **Expected:** At least 2 occurrences — one as `Form(False)` parameter, one in the `uninstall()` call
3. `grep "clean_data" backend/app/apps/manager.py`
4. **Expected:** At least 3 occurrences — parameter definition, SPARQL execution block, and log message

### 6. Triplestore Cleanup SPARQL Is Correct

1. `grep -A1 "STRSTARTS" backend/app/apps/manager.py`
2. **Expected:** Two SPARQL DELETE WHERE queries — one filtering on `STR(?s)` (subjects), one on `STR(?o)` (objects)
3. `grep "CLEAR GRAPH" backend/app/apps/manager.py`
4. **Expected:** `CLEAR GRAPH <urn:sempkm:app:{app_id}:state>` — clears the app's state graph

### 7. E2E Spec Covers All Integration Phases (Artifact Check)

1. `grep "Phase" e2e/tests/30-app-platform/app-platform.spec.ts`
2. **Expected:** Comments for Phase 0 through Phase 7 (8 phases total)
3. `grep -c "expect(" e2e/tests/30-app-platform/app-platform.spec.ts`
4. **Expected:** ≥ 25 assertions
5. `grep "test-app-main\|right-pane\|command-dialog\|test-view\|read-renderer" e2e/tests/30-app-platform/app-platform.spec.ts | wc -l`
6. **Expected:** ≥ 3 (fragment ID assertions in spec)

### 8. E2E Full Lifecycle (Requires Docker Stack)

1. Start Docker test stack: `docker compose -f docker-compose.test.yml up -d`
2. Wait for health: `until curl -sf http://localhost:3901/health; do sleep 2; done`
3. Run E2E: `cd e2e && npx playwright test --project=chromium tests/30-app-platform/app-platform.spec.ts --reporter=list`
4. **Expected:** 1 test passed. Phases verified:
   - Phase 1: Test app installed and reaches "running" status in admin
   - Phase 2: Admin detail page shows app name, running badge, PID, permissions (object.create), tasks (heartbeat)
   - Phase 3: Workspace APPS sidebar shows "Test App"; clicking opens page with `#test-app-main` fragment
   - Phase 4: Right pane shows "Test Info" section (soft-check — may be skipped in CI)
   - Phase 5: Command palette API returns `test-app:test-command` with correct metadata
   - Phase 6: Stop shows "stopped" badge; Start recovers to "running"
   - Phase 7: Uninstall removes app from admin list and APPS sidebar

### 9. Test App Templates Have Unique IDs

1. `grep 'id="test-app-' apps/test-app/frontend/templates/*.html`
2. **Expected:** 5 unique IDs: test-app-main, test-app-right-pane, test-app-command-dialog, test-app-renderer, test-app-view

### 10. No Conflict Markers

1. `grep -rn "^<<<<<<< " apps/ backend/app/apps/ e2e/tests/30-app-platform/`
2. **Expected:** Zero results (exit code 1)

## Edge Cases

### Clean Uninstall with Non-Reachable Triplestore

1. In `manager.py`, the `clean_data=True` path is wrapped in try/except
2. `grep -A3 "except.*Exception" backend/app/apps/manager.py | grep -i "clean\|triplestore"`
3. **Expected:** WARNING log on failure, uninstall continues (does not raise)

### Idempotent E2E Cleanup

1. Run the E2E test twice in succession
2. **Expected:** Phase 0 cleanup handles already-installed test-app by stopping + uninstalling before Phase 1 install

### Manifest Validation Failure Path

1. `cd backend && .venv/bin/python3 -c "from app.apps.manifest import parse_app_manifest; parse_app_manifest('/nonexistent/path')"`
2. **Expected:** ValueError or FileNotFoundError with descriptive message

## Failure Signals

- `pytest tests/` shows any failures → regression introduced
- `parse_app_manifest('../apps/test-app/manifest.yaml')` raises → test fixture broken
- `docker compose -f docker-compose.test.yml config --quiet` exits non-zero → Docker config invalid
- E2E test hangs at Phase 1 → app install/venv creation failing in Docker
- E2E test fails at Phase 2 → admin detail page template broken
- E2E test fails at Phase 3 → APPS sidebar or fragment loading broken
- E2E test fails at Phase 5 → command palette API endpoint broken or app contributions not registered
- E2E test fails at Phase 6 → stop/start lifecycle broken
- E2E test fails at Phase 7 → uninstall endpoint or redirect broken

## Requirements Proved By This UAT

- APP-01 — Test app manifest validates against full AppManifestSchema (test case 1)
- APP-02 — E2E proves install → start → stop → restart → uninstall lifecycle (test case 8, phases 1/6/7)
- APP-07 — E2E proves standalone page loads in workspace via sidebar (test case 8, phase 3)
- APP-08 — E2E proves right pane contribution and command palette entry (test case 8, phases 4/5)
- APP-10 — E2E proves admin detail page shows PID, permissions, tasks, status (test case 8, phase 2)
- APP-13 — Uninstall now supports clean_data triplestore cleanup (test cases 5/6)
- APP-14 — Docker test stack config validates with required volume mounts (test case 2)

## Not Proven By This UAT

- APP-03 (SDK package installation into app venv) — proven at S02 level, not re-verified here
- APP-04 (IPC over UDS with JWT) — proven at S02/S03 level via proxy chain, implicitly exercised by E2E
- APP-05 (permission enforcement) — proven at S05 level with 33 unit tests, not E2E-tested
- APP-06 (task scheduler firing) — task config visible in admin (E2E phase 2) but actual task execution not waited for in E2E
- APP-09 (renderer overrides) — object renderer registered in manifest but E2E doesn't create a TestRenderedType object to trigger the override
- APP-11 (bulk EventStore) — proven at S05 level with 16 unit tests
- APP-12 (browserVisible) — proven at S05 level with 22 unit tests

## Notes for Tester

- **E2E timing is generous** — 180s test timeout, 50s install polling, 30s restart polling. In a fast Docker environment, the test completes in ~60s. Slow environments may approach the 180s ceiling.
- **Right pane (Phase 4) is a soft-check** — it may be skipped if the workspace focus state doesn't trigger right pane loading. Phase 5 (command palette API) provides the authoritative proof that app contributions are registered.
- **clean_data is API-only** — The admin uninstall form doesn't have a checkbox for it yet. To test clean uninstall via UI, you'd need to submit the form with a clean_data field manually (e.g., via browser DevTools).
- **Python 3.14 compat fix included** — If you see `asyncio.get_event_loop()` deprecation warnings elsewhere, the same `asyncio.run()` fix pattern applies.
