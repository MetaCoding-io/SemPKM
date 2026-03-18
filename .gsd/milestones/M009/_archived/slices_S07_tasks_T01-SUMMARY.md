---
id: T01
parent: S07
milestone: M009
provides:
  - apps/test-app/ — comprehensive test fixture exercising all SDK features
  - docker-compose.test.yml volume mounts for apps and SDK
key_files:
  - apps/test-app/manifest.yaml
  - apps/test-app/app.py
  - docker-compose.test.yml
key_decisions:
  - Used backoffMultiplier (int) instead of backoff (string) per actual AppTaskRetryPolicy schema — plan's retry fields were adjusted to match
patterns_established:
  - Test app manifest covers all UI contribution types (pages, rightPane, views, commandPalette, objectRenderers, tasks) as a reference fixture
  - Each template uses a unique id attribute (test-app-main, test-app-right-pane, etc.) for E2E assertion targeting
observability_surfaces:
  - parse_app_manifest() validates the test app at import time — schema violations raise ValueError with field-level detail
  - Test app logs startup/shutdown/heartbeat via Python logging at INFO level
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Create test app and update Docker test infrastructure

**Created `apps/test-app/` with all SDK integration points and updated `docker-compose.test.yml` with required volume mounts.**

## What Happened

Created the comprehensive test application at `apps/test-app/` with:
- `manifest.yaml` exercising all UI contribution types: 1 page, 1 right pane section, 1 view, 1 command palette entry, 1 object renderer, 1 scheduled task
- `app.py` with 5 fragment route handlers, 1 task handler, 2 lifecycle hooks (startup/shutdown)
- 5 HTML templates with unique `id` attributes for E2E assertion targeting
- Minimal static assets (CSS + JS)
- Empty `requirements.txt` (SDK injected by platform)

Updated `docker-compose.test.yml` with 3 volume mounts:
- `./apps:/app/apps:ro` on api service (app source)
- `./backend/sdk:/app/backend/sdk:ro` on api service (SDK package)
- `sempkm_test_data:/app/data:ro` on frontend service (app-static serving)

## Verification

| Check | Result |
|-------|--------|
| `parse_app_manifest('../apps/test-app/manifest.yaml')` | ✅ OK: Test Application v1.0.0, 1 pages, 1 tasks |
| `docker compose -f docker-compose.test.yml config --quiet` | ✅ Exit 0 |
| `ls apps/test-app/frontend/templates/ \| wc -l` | ✅ 5 |
| `grep -c "test-app" apps/test-app/manifest.yaml` | ✅ 1 |
| `python3 -c "import ast; ast.parse(open('apps/test-app/app.py').read())"` | ✅ Syntax OK |
| `docker compose -f docker-compose.test.yml config --services` | ✅ triplestore, api, frontend |
| `pytest tests/test_app_manifest.py -v -k "test_app"` | ✅ 60 passed |
| `pytest tests/ -x --ignore=tests/test_sdk_integration.py` | ⚠️ 861 passed, 1 pre-existing failure (test_renderer_overrides — from S05, unrelated) |
| `grep -rn "^<<<<<<< " apps/` | ✅ Zero conflict markers |

## Diagnostics

- **Manifest validation:** `cd backend && .venv/bin/python3 -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/test-app/manifest.yaml'); print(m.model_dump_json(indent=2))"`
- **Docker config inspection:** `docker compose -f docker-compose.test.yml config` — full expanded config with all volumes
- **Template listing:** `ls -la apps/test-app/frontend/templates/`
- **Pre-existing failure:** `tests/test_renderer_overrides.py::test_returns_match_with_no_pref` — unrelated to this task, from S05

## Deviations

- Plan specified `retryPolicy: { backoff: "1s", maxBackoff: "10s" }` but actual schema uses `backoffMultiplier` (int, 1–10) not `backoff` (string). Used `backoffMultiplier: 2` and `maxBackoff: "10s"` to match the real `AppTaskRetryPolicy` model.
- Plan called `parse_app_manifest('../apps/test-app')` (directory) but the function takes a file path. Used `'../apps/test-app/manifest.yaml'` instead.

## Known Issues

- Pre-existing test failure in `test_renderer_overrides.py::test_returns_match_with_no_pref` (from S05, not caused by this task)

## Files Created/Modified

- `apps/test-app/manifest.yaml` — Full manifest with all UI contribution types
- `apps/test-app/app.py` — SDK app with 5 routes, 1 task, 2 lifecycle hooks
- `apps/test-app/requirements.txt` — Empty (SDK injected by platform)
- `apps/test-app/frontend/templates/main.html` — Main page fragment (id=test-app-main)
- `apps/test-app/frontend/templates/right-pane.html` — Right pane fragment (id=test-app-right-pane)
- `apps/test-app/frontend/templates/command-dialog.html` — Command dialog fragment (id=test-app-command-dialog)
- `apps/test-app/frontend/templates/read-renderer.html` — Renderer fragment (id=test-app-renderer)
- `apps/test-app/frontend/templates/test-view.html` — View fragment (id=test-app-view)
- `apps/test-app/frontend/static/styles.css` — Minimal CSS for test app containers
- `apps/test-app/frontend/static/app.js` — Minimal JS (console.log)
- `docker-compose.test.yml` — Added 3 volume mounts (2 on api, 1 on frontend)
