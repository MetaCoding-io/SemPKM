---
id: T01
parent: S01
milestone: M024
provides:
  - Monday.com Sync app scaffold with manifest, auth module, connect/disconnect routes, templates, scoped CSS
  - 31 passing auth tests covering store/get/clear/verify/status credential lifecycle
key_files:
  - apps/monday-sync/manifest.yaml
  - apps/monday-sync/services/auth.py
  - apps/monday-sync/app.py
  - apps/monday-sync/frontend/templates/connect.html
  - apps/monday-sync/frontend/templates/connect_status.html
  - apps/monday-sync/frontend/static/styles.css
  - backend/tests/test_monday_auth.py
key_decisions:
  - Monday.com auth uses single API token stored as `monday_api_token` state key (simpler than Jira's email+token+site_url triple)
  - Auth header format is bare `Authorization: <api_key>` — no Basic/Bearer prefix
patterns_established:
  - Single-token auth pattern: store_credentials(state, token), get_credentials(state) -> dict|None, clear_credentials(state), verify_connection(state, client), get_connection_status(state, client)
  - Board selection UI uses checkbox list with `board_ids` form field (analogous to Jira's project_keys)
observability_surfaces:
  - monday_sync.auth logger (INFO on store/clear/verify, WARNING on verify failures)
  - monday_sync logger (INFO on app lifecycle, route actions; WARNING/ERROR on failures)
  - get_connection_status() returns structured dict with connected/display_name/email/token_preview/error
duration: 18m
verification_result: passed
completed_at: 2026-03-19T23:33:00-04:00
blocker_discovered: false
---

# T01: App scaffold, auth module, connect UI, and auth tests

**Created complete Monday.com Sync app scaffold with auth credential lifecycle, connect/disconnect routes, board selection UI templates, scoped CSS, and 31 passing auth tests.**

## What Happened

Built the full `apps/monday-sync/` directory structure following the Jira Sync pattern. The auth module is simplified from Jira's three-credential model (email+token+site_url) to a single API token — Monday.com's auth only needs `Authorization: <api_key>`. All six auth functions (store, get, clear, verify, get_connection_status, _mask_token) follow the established pattern. The app.py has connect/disconnect/board-save/sync-config routes plus poll-tasks and push-changes task handler stubs. Templates use `/app/monday-sync/` htmx URL prefix per KNOWLEDGE.md. CSS scoped under `.monday-sync-settings` mirrors the Jira pattern with board-specific class names.

## Verification

- 31 auth tests pass covering store/get/clear credentials, mask_token edge cases (short/long/boundary tokens), verify_connection success/failure/network-error, connection status connected/disconnected/empty-token/error states, and round-trip integration tests
- All Python files pass `ast.parse()` syntax check
- All 9 expected files exist in `apps/monday-sync/`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py -v` | 0 | ✅ pass (31 tests) | 0.06s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` | 0 | ✅ pass | <0.1s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/auth.py').read())"` | 0 | ✅ pass | <0.1s |
| 4 | All 9 files existence check | 0 | ✅ pass | <0.1s |

### Slice-level verification (partial — T01 only)

| # | Command | Exit Code | Verdict | Notes |
|---|---------|-----------|---------|-------|
| 1 | `pytest tests/test_monday_auth.py -v` | 0 | ✅ 31 passed | Exceeds 20+ requirement |
| 2 | `pytest tests/test_monday_client.py -v` | — | ⬜ not yet created | T02 |
| 3 | `pytest tests/test_monday_field_mapper.py -v` | — | ⬜ not yet created | T03 |
| 4 | `pytest tests/test_monday_person_matcher.py -v` | — | ⬜ not yet created | T04 |

## Diagnostics

- **Auth state inspection:** `get_connection_status(state_client, monday_client)` returns dict with `connected`, `display_name`, `email`, `token_preview`, `error` — drives the template rendering
- **Token redaction:** `_mask_token()` masks to `first4+****+last4` (or `first4+****` for tokens ≤8 chars) — never exposes raw token
- **Loggers:** `monday_sync.auth` at INFO/WARNING; `monday_sync` at INFO/WARNING/ERROR
- **Test runner:** `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py -v` — must run from backend/ directory with its venv

## Deviations

None — all planned files and functions implemented as specified.

## Known Issues

None.

## Files Created/Modified

- `apps/monday-sync/manifest.yaml` — App manifest with appId, permissions, tasks, UI page, network domain
- `apps/monday-sync/requirements.txt` — Empty dependencies file (SDK provides core deps)
- `apps/monday-sync/services/__init__.py` — Empty package init
- `apps/monday-sync/services/auth.py` — Auth helpers: store/get/clear/verify/status + _mask_token
- `apps/monday-sync/app.py` — Route handlers (connect/disconnect/boards/sync-config/sync-now) and task stubs
- `apps/monday-sync/frontend/templates/connect.html` — API token input form with htmx POST
- `apps/monday-sync/frontend/templates/connect_status.html` — Connected state with board selection, sync config, stats, disconnect
- `apps/monday-sync/frontend/static/styles.css` — Scoped CSS under .monday-sync-settings
- `backend/tests/test_monday_auth.py` — 31 auth tests using importlib loading pattern
- `.gsd/milestones/M024/slices/S01/tasks/T01-PLAN.md` — Added Observability Impact section
