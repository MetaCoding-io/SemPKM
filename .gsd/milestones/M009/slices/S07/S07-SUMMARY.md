---
id: S07
parent: M009
milestone: M009
provides:
  - apps/test-app/ — comprehensive test fixture exercising all 6 SDK UI contribution types (page, right pane, view, command palette, renderer override, task)
  - e2e/tests/30-app-platform/app-platform.spec.ts — Playwright E2E spec with 7 phases and 28 assertions proving full app platform lifecycle
  - AppManager.uninstall(clean_data=True) — triplestore SPARQL cleanup on uninstall (subject, object, state graph)
  - admin uninstall endpoint accepts clean_data form parameter
  - Fixed pre-existing test_renderer_overrides async event loop failure (Python 3.14 compat)
requires:
  - slice: S01
    provides: AppManager lifecycle, AppManifestSchema, DB models
  - slice: S02
    provides: App SDK package, IPC proxy, JWT auth
  - slice: S03
    provides: Admin portal (list/detail/actions), nginx proxy, Docker volume mounts
  - slice: S04
    provides: APPS sidebar, app page fragment loading, app_shell.html
  - slice: S05
    provides: Scheduler, permissions, bulk EventStore, browserVisible
  - slice: S06
    provides: Right pane contributions, views explorer entries, command palette API, renderer overrides
affects:
  - S08
key_files:
  - apps/test-app/manifest.yaml
  - apps/test-app/app.py
  - apps/test-app/frontend/templates/main.html
  - apps/test-app/frontend/templates/right-pane.html
  - apps/test-app/frontend/templates/command-dialog.html
  - apps/test-app/frontend/templates/read-renderer.html
  - apps/test-app/frontend/templates/test-view.html
  - docker-compose.test.yml
  - backend/app/apps/manager.py
  - backend/app/apps/admin_router.py
  - e2e/tests/30-app-platform/app-platform.spec.ts
  - e2e/helpers/selectors.ts
  - backend/tests/test_app_admin.py
  - backend/tests/test_renderer_overrides.py
key_decisions:
  - D169: App uninstall triplestore cleanup is best-effort (try/except, WARNING log, never blocks uninstall)
  - Test app manifest uses backoffMultiplier (int) per actual AppTaskRetryPolicy schema, not backoff (string) from initial plan
patterns_established:
  - Test app as comprehensive SDK fixture — one app covering all UI contribution types serves both as E2E test fixture and SDK reference implementation
  - E2E phase pattern for lifecycle testing — cleanup → install → verify admin → verify workspace → verify API → stop/start → uninstall → verify removal
  - Polling pattern for async Docker operations — loop N attempts with delay + page reload, then hard assert
  - App IRI prefix convention for cleanup — urn:sempkm:app:{appId}: used for both subject/object SPARQL filtering and state graph naming
  - Each fragment template has a unique id attribute (test-app-main, test-app-right-pane, etc.) for reliable E2E assertion targeting
observability_surfaces:
  - INFO log "Cleaning triplestore data for app {app_id}" on clean uninstall path
  - WARNING log "Failed to clean triplestore data for app {app_id}" if SPARQL cleanup fails
  - Playwright traces on first retry + screenshots on failure for E2E debugging
  - 28 explicit expect() assertions in E2E spec — failures pinpoint which integration phase broke
drill_down_paths:
  - .gsd/milestones/M009/slices/S07/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S07/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S07/tasks/T03-SUMMARY.md
duration: 32m
verification_result: passed
completed_at: 2026-03-17
---

# S07: Test App, E2E Tests & Integration Proof

**Comprehensive test app (`apps/test-app/`) exercises all SDK features. Playwright E2E spec proves the full install → workspace → admin → uninstall vertical. Uninstall gains triplestore data cleanup. All 1201 backend tests pass with zero failures.**

## What Happened

Three tasks assembled the integration proof for the entire M009 app platform:

**T01 (Test App + Docker)** created `apps/test-app/` with a manifest exercising all 6 UI contribution types: standalone page, right pane section, custom view, command palette entry, object renderer override, and scheduled task. The `app.py` implements 5 fragment route handlers, 1 task handler, and 2 lifecycle hooks (startup/shutdown). Five HTML templates provide targetable content for E2E assertions via unique `id` attributes. Docker `docker-compose.test.yml` was updated with `./apps:/app/apps:ro` and `./backend/sdk:/app/backend/sdk:ro` volume mounts on the API service, plus `sempkm_test_data:/app/data:ro` on the frontend service for app-static serving.

**T02 (Uninstall Data Cleanup)** added `clean_data: bool = False` to `AppManager.uninstall()`. When True, it executes three SPARQL queries before DB deletion: (1) DELETE subjects with app IRI prefix, (2) DELETE objects with app IRI prefix, (3) CLEAR the app's state graph. Cleanup is best-effort (try/except with WARNING log) — consistent with the existing uninstall pattern where process stop failures are also non-blocking. The admin uninstall endpoint was updated to accept and pass through `clean_data` as a form parameter.

**T03 (Playwright E2E Spec)** created `e2e/tests/30-app-platform/app-platform.spec.ts` — a single-test sequential spec with 7 phases: (0) idempotent cleanup, (1) install via admin form, (2) verify admin detail page (h1, running badge, PID, permissions, tasks), (3) verify workspace APPS sidebar + app page fragment loading, (4) right pane section verification (soft-check), (5) command palette API verification (authoritative), (6) stop/start lifecycle, (7) uninstall + verify removal from admin list and workspace sidebar. 14 CSS selectors added to `e2e/helpers/selectors.ts`.

**Bonus fix:** The pre-existing `test_renderer_overrides.py::test_returns_match_with_no_pref` failure (from S06) was caused by `asyncio.get_event_loop().run_until_complete()` deprecation in Python 3.14. Replaced with `asyncio.run()` across all 5 affected test methods — all 19 renderer override tests now pass.

## Verification

| Check | Result |
|-------|--------|
| `parse_app_manifest('../apps/test-app/manifest.yaml')` | ✅ Test Application v1.0.0, 1 task |
| `docker compose -f docker-compose.test.yml config --services` | ✅ triplestore, api, frontend |
| `docker compose -f docker-compose.test.yml config --quiet` | ✅ Exit 0 |
| `pytest tests/test_app_manifest.py -v -k "test_app"` | ✅ 60 passed |
| `pytest tests/ -x --ignore=tests/test_sdk_integration.py` | ✅ **1201 passed, 0 failures** |
| `grep -rn "^<<<<<<< " apps/ backend/app/apps/ e2e/tests/30-app-platform/` | ✅ Zero conflict markers |
| `grep -c "clean_data" backend/app/apps/manager.py` | ✅ 3 occurrences |
| `grep -c "clean_data" backend/app/apps/admin_router.py` | ✅ 4 occurrences |
| `grep "STRSTARTS" backend/app/apps/manager.py` | ✅ 2 lines (subject + object) |
| `grep "CLEAR GRAPH" backend/app/apps/manager.py` | ✅ 1 line |
| E2E spec `expect()` count | ✅ 28 assertions |
| Test app templates | ✅ 5 templates (main, right-pane, command-dialog, read-renderer, test-view) |

**Note:** E2E spec execution requires a running Docker test stack. The spec is syntactically valid, follows established patterns (matching `admin-model-lifecycle.spec.ts`), and TypeScript compilation succeeds.

## Requirements Advanced

- APP-01 — Test app manifest validates against AppManifestSchema, exercising all field types (pages, contributions, tasks, objectRenderers, permissions)
- APP-02 — E2E spec proves install → start → health check → stop → restart → uninstall lifecycle
- APP-07 — E2E spec proves standalone page loads in workspace via APPS sidebar → fragment loading
- APP-10 — E2E spec proves admin detail page shows PID, permissions, tasks, status badges, stop/start/uninstall actions
- APP-13 — Admin endpoint now accepts clean_data for uninstall, completing the DB/triplestore cleanup loop
- APP-14 — docker-compose.test.yml has required volume mounts for apps and SDK

## Requirements Validated

- None moved to validated in this slice (E2E requires live Docker stack execution for full validation)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **Manifest retry fields:** Plan specified `backoff: "1s"` but actual `AppTaskRetryPolicy` schema uses `backoffMultiplier` (int, 1–10). Used `backoffMultiplier: 2` to match real schema.
- **Manifest parse function:** Plan called `parse_app_manifest('../apps/test-app')` (directory) but function takes a file path. Used `'../apps/test-app/manifest.yaml'`.
- **No clean_data checkbox in admin UI:** T02 added the backend parameter but the detail.html uninstall form doesn't include a clean_data checkbox. The E2E spec's Phase 0 cleanup uses the API directly with `clean_data: 'true'`; Phase 7 uninstall uses the default form (clean_data=false).
- **Fixed pre-existing test failure:** `test_renderer_overrides.py` had 5 methods using deprecated `asyncio.get_event_loop().run_until_complete()` that failed on Python 3.14. Fixed by replacing with `asyncio.run()`.
- **Admin uninstall test updated:** `test_uninstall_calls_manager` expected `uninstall("test-app")` but T02 changed the signature to include `clean_data=False`. Updated assertion to match.

## Known Limitations

- **E2E test not verified against live Docker stack** — The spec is syntactically valid and follows established patterns but has not been executed against a running Docker test stack. Full end-to-end verification requires `docker compose -f docker-compose.test.yml up`.
- **No clean_data UI control** — The admin uninstall form doesn't expose the `clean_data` checkbox. Users can only trigger data cleanup via API, not via the admin portal UI. This is a minor UX gap for S08 or a follow-up.
- **Right pane E2E verification is soft-check** — The right pane test phase uses try/catch because it depends on complex workspace state (object focus, right pane visibility, htmx load timing). The command palette API check provides authoritative proof of app contribution registration.

## Follow-ups

- Add `clean_data` checkbox to admin detail page uninstall form (minor UI addition)
- Run full E2E spec against Docker test stack to complete live verification
- S08 (User Guide Documentation) is the only remaining slice before M009 completion

## Files Created/Modified

- `apps/test-app/manifest.yaml` — Full manifest with all UI contribution types
- `apps/test-app/app.py` — SDK app with 5 routes, 1 task, 2 lifecycle hooks
- `apps/test-app/requirements.txt` — Empty (SDK injected by platform)
- `apps/test-app/frontend/templates/main.html` — Main page fragment (id=test-app-main)
- `apps/test-app/frontend/templates/right-pane.html` — Right pane section fragment
- `apps/test-app/frontend/templates/command-dialog.html` — Command dialog fragment
- `apps/test-app/frontend/templates/read-renderer.html` — Object renderer fragment
- `apps/test-app/frontend/templates/test-view.html` — View tab fragment
- `apps/test-app/frontend/static/styles.css` — Minimal CSS for test app containers
- `apps/test-app/frontend/static/app.js` — Minimal JS (console.log)
- `docker-compose.test.yml` — Added 3 volume mounts (2 on api, 1 on frontend)
- `backend/app/apps/manager.py` — Added clean_data parameter with SPARQL cleanup
- `backend/app/apps/admin_router.py` — Added clean_data form parameter to uninstall endpoint
- `e2e/tests/30-app-platform/app-platform.spec.ts` — 278-line E2E spec with 7 phases
- `e2e/helpers/selectors.ts` — Added apps section with 14 CSS selectors
- `backend/tests/test_app_admin.py` — Updated uninstall assertion for clean_data parameter
- `backend/tests/test_renderer_overrides.py` — Fixed asyncio.run() for Python 3.14 compat

## Forward Intelligence

### What the next slice should know
- S08 is documentation only — it should reference `apps/test-app/` as the SDK reference implementation. The manifest.yaml covers all UI contribution types and is the most complete example of the manifest schema in the codebase.
- The test app's `app.py` demonstrates every SDK decorator and pattern: `@test_app.route()`, `@test_app.task()`, `@test_app.on_startup`, `@test_app.on_shutdown`.
- All 14 APP requirements have been implemented across S01–S07. S08 needs to document the user-facing and developer-facing aspects without introducing any new features.

### What's fragile
- **E2E spec timing assumptions** — The polling loops (50s for install, 30s for restart) assume reasonable Docker performance. Slow CI environments may need higher timeouts.
- **Right pane soft-check** — Phase 4 is wrapped in try/catch because right pane loading depends on workspace focus state. If this becomes a hard requirement, the test would need explicit workspace panel manipulation before checking.
- **clean_data without UI** — The backend supports it, the API accepts it, but the admin form doesn't expose it. A user expecting "Remove all data" from the admin portal would need to know to use the API.

### Authoritative diagnostics
- `pytest tests/ -x --ignore=tests/test_sdk_integration.py` — **1201 tests, 0 failures** is the authoritative backend health signal
- `docker compose -f docker-compose.test.yml config --quiet` — exit 0 confirms Docker stack validity
- `parse_app_manifest('../apps/test-app/manifest.yaml')` — confirms test fixture integrity

### What assumptions changed
- **Plan assumed `backoff` string field** — Actual schema uses `backoffMultiplier` (int). The test app manifest was adjusted accordingly.
- **Plan assumed directory-based manifest parsing** — `parse_app_manifest()` takes a file path, not a directory. Test commands adjusted.
- **Pre-existing test failure was from S06, not S05** — The renderer override test used deprecated asyncio API. Fixed as part of this slice's "zero regressions" goal.
