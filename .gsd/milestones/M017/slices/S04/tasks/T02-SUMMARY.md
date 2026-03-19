---
id: T02
parent: S04
milestone: M017
provides:
  - Playwright E2E test skeleton for GitHub sync lifecycle (12 phases)
  - githubSync selector block in e2e/helpers/selectors.ts
  - Fix for browser/apps.py app_registry → app_manager.registry bug
  - Fix for workspace-layout.js missing app-page/app-view URL routing
key_files:
  - e2e/tests/32-github-sync/github-sync.spec.ts
  - e2e/helpers/selectors.ts
  - backend/app/browser/apps.py
  - frontend/static/js/workspace-layout.js
key_decisions:
  - Use full URN IRI (urn:sempkm:model:basic-pkm:Task) in SPARQL queries instead of fabricated prefix
patterns_established:
  - Retry-loop pattern for app fragment loading in E2E tests (app subprocess may not be ready when status shows "Running")
observability_surfaces:
  - Phase-level test structure for Playwright failure localization
duration: ~45min
verification_result: partial
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Playwright E2E test for GitHub sync lifecycle

**Created github-sync E2E test with 12 phases and fixed two platform bugs blocking app page rendering; test runs through Phase 2 (install) but subprocess start issue prevents fragment loading — needs investigation of app data dir/venv state**

## What Happened

1. **Added `githubSync` selector block** to `e2e/helpers/selectors.ts` — 11 selectors matching connect.html and connect_status.html template IDs/classes.

2. **Created `e2e/tests/32-github-sync/github-sync.spec.ts`** — Full 12-phase test (cleanup → prerequisite → install → workspace → connect → repos → config → sync → SPARQL count → SPARQL edge → admin verify → cleanup). Follows linear-sync.spec.ts pattern. 240s timeout.

3. **Fixed pre-existing bug in `backend/app/browser/apps.py`** — All 6 occurrences of `request.app.state.app_registry` changed to `request.app.state.app_manager.registry`. The `app_registry` attribute was never set on app.state; only `app_manager` was. This caused 500 errors on `/browser/apps/explorer`, making the APPS sidebar show "Loading apps..." forever.

4. **Fixed pre-existing bug in `frontend/static/js/workspace-layout.js`** — Added `app-page` and `app-view` URL routing in the special-panel init function. Without these, clicking an app leaf generated `/browser/app-page` (404) instead of `/browser/apps/{appId}/page/{pageId}`.

5. **Fixed `.env` syntax error** — The `LINEAR_API_KEY` line had parentheses in the variable name which broke `docker compose`.

6. **Test runs through Phase 2** successfully: cleanup, model install, app install all pass. Phase 3 (workspace app page) now correctly routes to the right URL and loads the page wrapper. However, the app subprocess fragment request (`/app/github-sync/_fragments/connect`) returns 500 because the UDS socket at `/tmp/sempkm-app-github-sync.sock` doesn't exist.

## Resume Notes for Next Agent

The blocking issue is that the github-sync app subprocess is not starting even though the DB row shows `status='running'`. Investigation trail:

- `docker compose -f docker-compose.test.yml exec -T api ls /tmp/sempkm-app-*` shows no sockets
- The install API call returns success and the admin page shows "Running" badge
- The `auto_start` method in `backend/app/apps/manager.py` should restart apps on container restart
- Need to check: `docker compose -f docker-compose.test.yml exec -T api ls /app/data/apps/github-sync/` — does the venv exist? Does it have sempkm_app_sdk installed?
- Need to check: `docker compose -f docker-compose.test.yml logs api 2>&1 | grep -i "github-sync\|spawn\|venv\|pip\|install.*app"` for subprocess start errors
- The test-app E2E (test 30) presumably worked at some point — compare how that test handles the same flow
- The `apps` volume mount is at `./apps:/app/apps:ro` (read-only) but the venv is at `/app/data/apps/{id}/venv/` in the data volume

Once the subprocess issue is resolved, the remaining test phases (4-11) should work as written — all selectors verified against templates.

## Verification

Partial — test compiles clean (tsc --noEmit passes), Phases 0-2 execute correctly, Phase 3 routing works but fragment loading fails due to app subprocess not starting.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx tsc --noEmit --project tsconfig.json` (e2e dir) | 0 | ✅ pass | 2s |
| 2 | `npx playwright test tests/32-github-sync/github-sync.spec.ts --project=chromium` | 1 | ❌ fail (Phase 3 fragment 500) | ~90s |

## Diagnostics

- **App subprocess socket:** `docker compose -f docker-compose.test.yml exec -T api ls /tmp/sempkm-app-github-sync.sock`
- **App data dir:** `docker compose -f docker-compose.test.yml exec -T api ls -la /app/data/apps/github-sync/`
- **API logs for app errors:** `docker compose -f docker-compose.test.yml logs api 2>&1 | grep -i "github-sync\|spawn\|start.*app"`
- **Mock github health:** `docker compose -f docker-compose.test.yml logs mock-github`

## Deviations

- Fixed `#model_path` → `#model-path` and `.card` → `#model-table tr` for model install detection (admin template uses table, not cards)
- Fixed two pre-existing platform bugs (browser/apps.py registry access, workspace-layout.js app-page routing) that blocked all app page rendering in the workspace
- Fixed `.env` file syntax error

## Known Issues

1. **App subprocess not starting** — The github-sync app shows "Running" in admin but the UDS socket doesn't exist. Root cause needs investigation (venv creation, sempkm_app_sdk availability, subprocess spawn errors).
2. **Scheduler datetime bug** — `backend/app/apps/scheduler.py:257` has `TypeError: can't subtract offset-naive and offset-aware datetimes` (known from KNOWLEDGE.md K-entry, fix was applied to `get_status()` but not to `_evaluate_task()`).
3. **CSS 404** — `/app-static/github-sync/styles.css` returns 404 — static file serving for apps may need investigation.

## Files Created/Modified

- `e2e/tests/32-github-sync/github-sync.spec.ts` — Full 12-phase E2E test (~200 lines)
- `e2e/helpers/selectors.ts` — Added `githubSync` selector block (11 selectors)
- `backend/app/browser/apps.py` — Fixed app_registry → app_manager.registry (6 occurrences)
- `frontend/static/js/workspace-layout.js` — Added app-page and app-view URL routing in special-panel init
- `.env` — Fixed LINEAR_API_KEY syntax (parentheses in var name)
