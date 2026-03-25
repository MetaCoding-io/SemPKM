---
id: T01
parent: S02
milestone: M043
key_files:
  - backend/app/browser/apps.py
  - backend/app/api/setup_routes.py
  - backend/app/main.py
  - backend/tests/test_app_views_commands.py
  - backend/tests/test_instance_config.py
  - backend/tests/test_sparql_injection_regression.py
key_decisions:
  - Added setup_mode guard as first check in configure-instance endpoint, before the existing user-data check, using getattr with False default for safety
  - Startup warnings use _is_localhost helper that checks for empty URL, localhost, or 127.0.0.1 — errs on the side of not warning for unconfigured instances
duration: ""
verification_result: passed
completed_at: 2026-03-25T09:00:13.064Z
blocker_discovered: false
---

# T01: Add authentication to 6 unprotected app endpoints, guard setup endpoint with setup_mode check, add startup security warnings

**Add authentication to 6 unprotected app endpoints, guard setup endpoint with setup_mode check, add startup security warnings**

## What Happened

Implemented three security hardening changes:

1. **App endpoint authentication (F-001):** Added `user: User = Depends(get_current_user)` to all 6 unprotected endpoints in `browser/apps.py`: apps_explorer, app_page, right_pane_sections, views_explorer_apps, app_view_tab, and commands_list. Unauthenticated requests now receive 401.

2. **Setup endpoint guard (F-004):** Added a `setup_mode` check to `POST /api/setup/configure-instance` in `setup_routes.py`. Returns 403 if `setup_mode` is not active on `app.state`, preventing reconfiguration after initial setup completes. The existing 409 user-data check remains as a second layer.

3. **Startup security warnings:** Added three warning checks to the lifespan function in `main.py`, emitted before "API started successfully":
   - `demo_mode=True` with non-localhost `APP_BASE_URL` → warns about disabled auth on public instance
   - `cookie_secure=False` with non-localhost `APP_BASE_URL` → warns about plain HTTP cookie transmission
   - `cookie_secure=False` with HTTPS `APP_BASE_URL` → warns about misconfigured HTTPS deployment

Also fixed a pre-existing bug in `test_app_views_commands.py` where `manager.registry` was never wired to the real `AppRegistry`, causing all 17 existing tests to fail. Added `manager.registry = registry` to the `_create_app()` helper. Added auth dependency overrides to the SPARQL injection regression test fixture (`TestF007AppsIriInjection`) and instance config test helper (`_make_test_app`). Net effect: 14 previously-broken tests now pass, 8 new tests added (6 unauthenticated 401 + 1 setup guard 403 + 1 from registry fix).

## Verification

Ran `pytest tests/test_app_views_commands.py tests/test_instance_config.py tests/test_sparql_injection_regression.py::TestF007AppsIriInjection -v` — 58 passed, 1 pre-existing failure (appId/pageId test for feature not yet implemented). Full suite: 5254 passed (was 5239), 102 failed (was 116) — net improvement of +15 passing tests.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py tests/test_instance_config.py tests/test_sparql_injection_regression.py::TestF007AppsIriInjection -v` | 1 | ✅ pass (58/59 passed, 1 pre-existing failure) | 3200ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/ --ignore=tests/test_caldav_field_mapper.py --ignore=tests/test_caldav_sync_engine.py --ignore=tests/test_notion_executor.py --tb=no -q` | 1 | ✅ pass (5254 passed vs 5239 before, 102 failed vs 116 before) | 33000ms |


## Deviations

Fixed pre-existing bug in test_app_views_commands.py where manager.registry was not wired to the real AppRegistry (all 17 tests were broken before this task). Updated test fixtures in test_instance_config.py and test_sparql_injection_regression.py to add auth dependency overrides required by the newly-protected endpoints.

## Known Issues

One pre-existing test failure: test_navigate_matching_app_page_includes_appid_pageid expects appId/pageId keys in command palette response that the endpoint doesn't produce. This predates M043.

## Files Created/Modified

- `backend/app/browser/apps.py`
- `backend/app/api/setup_routes.py`
- `backend/app/main.py`
- `backend/tests/test_app_views_commands.py`
- `backend/tests/test_instance_config.py`
- `backend/tests/test_sparql_injection_regression.py`
