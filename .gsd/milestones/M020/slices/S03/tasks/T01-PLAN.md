---
estimated_steps: 6
estimated_files: 1
---

# T01: Write route-handler unit tests for Outlook app.py

**Slice:** S03 — Push Sync + Settings UI
**Milestone:** M020

## Description

Add ~15 route-handler unit tests to the existing `test_outlook_sync_engine.py` file, following the M017 GitHub Sync test pattern. These tests verify the app.py wiring layer: template context assembly (`_render_connect_status`), sync dispatch (`sync_now` with bidirectional vs pull-only), push-changes task handler, and sync-config persistence. All production code already exists — this is test-only work.

The key difference from the GitHub Sync pattern: Outlook app uses `ctx.state` for ALL config (sync_direction, poll_interval, selected_calendars) whereas GitHub Sync uses a separate `ctx.settings`. The `_RenderableAppContext` here extends `MockAppContext` and adds `render_template()` support plus a `settings` attribute backed by a second `MockStateClient` — but for Outlook, everything goes through `ctx.state`.

The `_render_connect_status` function calls `get_connection_status(ctx.state)` and `OutlookClient.get_calendar_list()`. The mock needs to handle both: connected state via state keys (`auth_method`, `microsoft_email`, `access_token`) and calendar list via monkey-patching `OutlookClient` or `_make_client_with_creds`.

## Steps

1. **Add `_load_app_module()` function** at the bottom of `test_outlook_sync_engine.py` (before the new test classes). This function:
   - Stubs `sempkm_app_sdk` if not in sys.modules (with a passthrough `App` class that preserves decorated functions via `.route()`, `.task()`, `.on_startup`, `.on_shutdown` decorators)
   - Stubs `starlette.requests` (with `Request` class), `starlette.responses` (with `HTMLResponse` and `RedirectResponse` classes)
   - Wires existing loaded modules: `sys.modules["services.sync_engine"] = _sync_engine`, `sys.modules["services.outlook_client"] = _outlook_client`, `sys.modules["services.auth"] = _auth`
   - Loads `apps/outlook-calendar/app.py` via `importlib.util.spec_from_file_location`
   - Returns the loaded module
   - Call it once at module level: `_app_module = _load_app_module()`

2. **Add mock scaffolding classes:**
   - `_RenderableAppContext(MockAppContext)` — extends existing `MockAppContext`, adds `self._rendered: list[tuple[str, dict]] = []` and `def render_template(self, template_name, **kwargs)` that appends to `_rendered` and returns `f"<rendered:{template_name}>"`
   - `_MockRequest` — minimal Starlette Request mock with `app.state.ctx` pointing to the context, `_form_data` dict, and `async def form()` returning `_MockFormData`
   - `_MockFormData(dict)` — with `.getlist(key)` method
   - `_make_connected_state()` helper — returns `{"auth_method": "oauth", "microsoft_email": "test@outlook.com", "access_token": "eyJ0test", "client_id": "test-client-id", "client_secret": "test-secret"}`
   - Monkey-patch for `_render_connect_status`: since it calls `_make_client_with_creds(ctx)` which constructs an `OutlookClient` and calls `get_calendar_list()`, patch `_app_module._make_client_with_creds` to return a mock client with an async `get_calendar_list` that returns `[{"id": "cal1", "name": "Calendar", "isDefaultCalendar": True, "canEdit": True}]`

3. **Write `TestRenderConnectStatus` class** (~5 tests):
   - `test_passes_sync_direction_to_template` — state has `sync_direction: "bidirectional"`, verify template kwargs
   - `test_passes_poll_interval_to_template` — state has `poll_interval: "30m"`, verify template kwargs
   - `test_passes_last_push_result_to_template` — state has `last_push_result` JSON, verify parsed dict in kwargs
   - `test_defaults_when_no_settings` — no sync_direction/poll_interval in state, verify defaults (pull-only, 15m, None)
   - `test_passes_existing_pull_result` — state has `last_pull_result` JSON, verify parsed dict in kwargs

4. **Write `TestSyncNowBidirectional` class** (~3 tests):
   - `test_push_called_when_bidirectional` — mock pull_sync and push_sync on `_sync_engine`, verify both called and push result stored
   - `test_last_sync_at_updated_after_both` — verify `last_sync_at` state key set after sync_now
   - `test_push_error_isolated` — push_sync raises, verify last_sync_at still set and last_push_result has status="error"

5. **Write `TestSyncNowPullOnly` class** (~2 tests) + `TestPushChangesHandler` (~2 tests) + `TestSyncConfigRoute` (~3 tests):
   - `TestSyncNowPullOnly`:
     - `test_push_not_called_when_pull_only` — sync_direction="pull-only", push_sync not called
     - `test_push_not_called_when_no_direction_set` — no sync_direction in state, push_sync not called
   - `TestPushChangesHandler`:
     - `test_calls_push_sync` — verify push_changes task calls push_sync and returns result
     - `test_error_returns_error_dict` — push_sync raises, verify error dict returned with status="error"
   - `TestSyncConfigRoute`:
     - `test_saves_sync_direction` — form has sync_direction and poll_interval, verify state updated
     - `test_defaults_on_missing_form_data` — empty form, verify defaults saved
     - `test_returns_html_response` — verify connect_status.html rendered after save

6. **Run full test suite and verify:**
   - `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -v --tb=short` — ~75 tests pass
   - `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` — ~192 tests pass

## Must-Haves

- [ ] `_load_app_module()` successfully loads `apps/outlook-calendar/app.py` with stubbed SDK/starlette
- [ ] `_RenderableAppContext` extends existing `MockAppContext` with `render_template` support
- [ ] `TestRenderConnectStatus` — 5 tests covering sync_direction, poll_interval, last_push_result, defaults, last_pull_result
- [ ] `TestSyncNowBidirectional` — 3 tests covering push dispatch, last_sync_at, error isolation
- [ ] `TestSyncNowPullOnly` — 2 tests covering pull-only and default behavior
- [ ] `TestPushChangesHandler` — 2 tests covering success and error paths
- [ ] `TestSyncConfigRoute` — 3 tests covering save, defaults, and re-render
- [ ] All ~75 tests in test_outlook_sync_engine.py pass
- [ ] Full Outlook suite (~192 tests across 3 files) passes

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -v --tb=short` — ~75 tests pass (60 existing + 15 new)
- `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` — ~192 tests pass
- Verify `test_push_error_isolated` proves diagnostic surface (last_push_result stores error detail)

## Inputs

- `backend/tests/test_outlook_sync_engine.py` — existing 60 tests with MockAppContext, MockStateClient, MockGraphClient, MockOutlookClient, MockExternalHttpClient scaffolding. Append new code at the bottom.
- `backend/tests/test_github_sync_engine.py` — reference implementation. Lines 1855–2260 contain `_MockRequest`, `_MockFormData`, `_load_app_module()`, `_RenderableAppContext`, and 5 test classes (15 tests total). Clone this pattern, adapting for Outlook.
- `apps/outlook-calendar/app.py` — production route handlers. Key functions: `_render_connect_status(ctx)` (reads state for sync config, calls `get_connection_status` and `OutlookClient.get_calendar_list()`), `sync_now(request)` (pull + optional push), `save_sync_config(request)` (form→state), `push_changes(ctx)` (task handler).

### Key adaptation notes from GitHub → Outlook:

1. **State vs Settings:** Outlook uses `ctx.state` for everything. GitHub uses `ctx.settings` for `selected_repos`, `sync_direction`, `poll_interval`. In Outlook, `sync_direction` and `poll_interval` are in `ctx.state`.

2. **Connected state:** Outlook needs `auth_method`, `microsoft_email`, `access_token`, `client_id`, `client_secret` in state (not `github_pat`).

3. **`_render_connect_status` calls OutlookClient:** The function calls `_make_client_with_creds(ctx)` which constructs an `OutlookClient` and then calls `client.get_calendar_list()`. You need to monkey-patch `_app_module._make_client_with_creds` to return a mock that has an async `get_calendar_list()`.

4. **Module wiring for `_load_app_module`:** Must register `services.sync_engine`, `services.outlook_client`, `services.auth` in sys.modules, plus stub `starlette.responses.RedirectResponse` (Outlook app.py imports it).

5. **sync_now reads from state, not settings:** The `sync_now` function reads `sync_direction` from `ctx.state.get("sync_direction")`, not from `ctx.settings`.

6. **No `settings` attribute needed on context:** `_RenderableAppContext` only needs `state` (inherited from `MockAppContext`) plus `render_template`. No `MockSettingsClient` needed.

## Observability Impact

- **Signals tested:** `last_push_result`, `last_pull_result`, `last_sync_at` state keys — these are the production diagnostic surface for sync health
- **Inspection:** Future agents can verify route-handler behavior by running `pytest tests/test_outlook_sync_engine.py -k "TestRenderConnect or TestSyncNow or TestPushChanges or TestSyncConfig" -v`
- **Failure visibility:** `test_push_error_isolated` and `test_error_returns_error_dict` prove that push failures produce parseable error dicts with `status="error"` and message detail — the same structure that production monitoring reads

## Expected Output

- `backend/tests/test_outlook_sync_engine.py` — expanded from ~1720 lines to ~1950 lines with 5 new test classes (15 tests) appended at the bottom, plus `_load_app_module`, `_RenderableAppContext`, `_MockRequest`, `_MockFormData`, `_make_connected_state` (renamed to avoid collision: use `_make_connected_state_for_routes` or similar), and monkey-patch helper
