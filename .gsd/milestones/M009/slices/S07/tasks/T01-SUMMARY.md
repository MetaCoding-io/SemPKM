---
id: T01
parent: S07
milestone: M009
provides:
  - apps/test-app/ with comprehensive manifest exercising all SDK UI contribution types
  - SDK app with 5 fragment routes, 1 task handler, 2 lifecycle hooks
  - 5 HTML templates with unique IDs for E2E assertion targeting
  - Docker test stack volume mounts for apps and SDK
key_files:
  - apps/test-app/manifest.yaml
  - apps/test-app/app.py
  - docker-compose.test.yml
key_decisions:
  - Task handler uses single-arg `(ctx)` signature matching actual SDK dispatch, not the two-arg `(ctx, body)` from the plan
patterns_established:
  - Test app templates use `id="test-app-*"` convention for reliable E2E selector targeting
observability_surfaces:
  - Test app logs startup/shutdown/heartbeat at INFO via standard Python logger
  - console.log('Test app loaded') in app.js for frontend load verification
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Create test app and update Docker test infrastructure

**Created apps/test-app/ with comprehensive manifest, SDK handlers for all integration points, 5 fragment templates, and updated docker-compose.test.yml with apps/SDK volume mounts.**

## What Happened

Created the complete test application fixture at `apps/test-app/` that exercises every SDK integration point built across S01–S06. The manifest declares all UI contribution types: pages, rightPane, views, commandPalette, objectRenderers, and tasks. The app.py registers 5 fragment route handlers, 1 scheduled task handler, and 2 lifecycle hooks (startup/shutdown) using the SDK's decorator API.

Each HTML template contains a unique `id` attribute (`test-app-main`, `test-app-right-pane`, `test-app-view`, `test-app-command-dialog`, `test-app-renderer`) so E2E tests can reliably assert the correct content loaded.

Updated `docker-compose.test.yml` with three new volume mounts: `./apps:/app/apps:ro` and `./backend/sdk:/app/backend/sdk:ro` on the api service (so the container can see app source and SDK), plus `sempkm_test_data:/app/data:ro` on the frontend service (for nginx to serve app-static files from the shared data volume).

## Verification

- Manifest validates against `AppManifestSchema` via `parse_app_manifest()` — all fields parse correctly (1 page, 1 task, 1 rightPane, 1 view, 1 command, 1 renderer)
- `docker compose -f docker-compose.test.yml config --quiet` exits 0 (valid compose syntax)
- 5 template files confirmed in `apps/test-app/frontend/templates/`
- `app.py` syntax validated via `ast.parse()`
- Zero conflict markers in `apps/`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `parse_app_manifest('/home/james/Code/SemPKM/apps/test-app/manifest.yaml')` | 0 | ✅ pass | <1s |
| 2 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | <1s |
| 3 | `ls apps/test-app/frontend/templates/ \| wc -l` → 5 | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/test-app/app.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `grep -c "test-app" apps/test-app/manifest.yaml` → 1 | 0 | ✅ pass | <1s |
| 6 | `docker compose -f docker-compose.test.yml config --services` → 3 services | 0 | ✅ pass | <1s |
| 7 | `grep -rn "^<<<<<<< " apps/` → 0 results | 1 (no match) | ✅ pass | <1s |

### Slice-level checks (partial — T01 is task 1 of 3):

| # | Slice Check | Status | Notes |
|---|------------|--------|-------|
| 1 | Manifest validates | ✅ pass | parse_app_manifest succeeds |
| 2 | docker-compose.test.yml config valid | ✅ pass | Shows 3 services |
| 3 | E2E Playwright specs | ⏳ pending | T03 deliverable |
| 4 | Existing test suite passes | ⏳ pending | Deferred to T03 |
| 5 | Zero conflict markers | ✅ pass | Clean |

## Diagnostics

- Manifest validation: `cd backend && python -c "from app.apps.manifest import parse_app_manifest; parse_app_manifest('/path/to/apps/test-app/manifest.yaml')"`
- App syntax: `python3 -c "import ast; ast.parse(open('apps/test-app/app.py').read())"`
- Docker config: `docker compose -f docker-compose.test.yml config`

## Deviations

- Task handler signature changed from `(ctx: AppContext, body: dict)` to `(ctx: AppContext)` — the SDK's `run_task` endpoint dispatches with `handler(ctx)` (single arg), so the plan's two-arg signature would cause a TypeError at runtime.

## Known Issues

None.

## Files Created/Modified

- `apps/test-app/manifest.yaml` — Comprehensive manifest with all UI contribution types
- `apps/test-app/app.py` — SDK app with 5 route handlers, 1 task, 2 lifecycle hooks
- `apps/test-app/requirements.txt` — Empty (SDK injected by platform)
- `apps/test-app/frontend/templates/main.html` — Main page fragment
- `apps/test-app/frontend/templates/right-pane.html` — Right pane fragment
- `apps/test-app/frontend/templates/command-dialog.html` — Command dialog fragment
- `apps/test-app/frontend/templates/read-renderer.html` — Object renderer fragment
- `apps/test-app/frontend/templates/test-view.html` — View tab fragment
- `apps/test-app/frontend/static/styles.css` — Minimal CSS for each container
- `apps/test-app/frontend/static/app.js` — Console log for load verification
- `docker-compose.test.yml` — Added 3 volume mounts (2 on api, 1 on frontend)
