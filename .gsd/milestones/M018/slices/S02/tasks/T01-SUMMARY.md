---
id: T01
parent: S02
milestone: M018
provides:
  - proxy query-param forwarding for OAuth callbacks and all app HTTP
  - correct SDK network permission parsing for list-type manifests
  - SDK pythonpath available for backend tests
key_files:
  - backend/app/apps/proxy.py
  - backend/sdk/sempkm_app_sdk/context.py
  - backend/tests/test_app_proxy_query_params.py
  - backend/tests/test_sdk_network_permissions.py
key_decisions:
  - Added "sdk" to pytest pythonpath rather than restructuring the SDK as a backend dependency
patterns_established:
  - Regression test pattern for proxy URL construction using CaptureClient
observability_surfaces:
  - PermissionError message includes allowed_domains list for domain enforcement debugging
duration: 15min
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Fix app proxy query-param forwarding and HttpClient domain enforcement

**Fixed two platform bugs: proxy now forwards query strings to app subprocesses, and SDK correctly parses list-type network permissions from manifests.**

## What Happened

Two one-line fixes plus 12 regression tests:

1. **Proxy query params** (`proxy.py` line 63): Added conditional `?{query}` append to `target_url` when `request.url.query` is non-empty. Previously, an OAuth callback like `?code=xxx&state=yyy` was silently dropped.

2. **SDK network permissions** (`context.py` line 136): Changed `else []` to `else network` so list-type manifest values like `["api.google.com"]` are passed through to `HttpClient.allowed_domains` instead of being discarded.

3. **Test infrastructure**: Added `sdk` to `pythonpath` in `pyproject.toml` so SDK imports work in tests. Fixed pre-existing `test_github_sync_engine.py` stub that poisoned `sys.modules` — it now tries the real SDK import first, falling back to stubs only when unavailable.

## Verification

- 5 proxy regression tests pass (query forwarding, no-query, single param, POST, encoded chars)
- 7 SDK network permission tests pass (list, dict, missing, empty, wildcard, end-to-end domain check)
- Full suite: 1463 tests pass, 0 failures

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_app_proxy_query_params.py -v` | 0 | ✅ pass | 0.21s |
| 2 | `cd backend && python -m pytest tests/test_sdk_network_permissions.py -v` | 0 | ✅ pass | 0.24s |
| 3 | `cd backend && python -m pytest tests/ -x -q` | 0 | ✅ pass | 8.37s |

## Diagnostics

- **Proxy forwarding**: Inspect via app subprocess request logging — query params now arrive. Existing `logger.warning` on connection failures covers error paths.
- **Network permissions**: `ctx.http._allowed_domains` shows parsed domains. `PermissionError` messages include the allowed list for debugging.

## Deviations

- Fixed pre-existing `test_bulk_eventstore` failure caused by `test_github_sync_engine` stubbing `sempkm_app_sdk` as a non-package module. The fix tries real import before falling back to stubs.
- Added `sdk` to pytest `pythonpath` in `pyproject.toml` — needed for SDK import in tests without the stub workaround.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/proxy.py` — append query string to target_url when present
- `backend/sdk/sempkm_app_sdk/context.py` — pass list-type network permissions through to HttpClient
- `backend/tests/test_app_proxy_query_params.py` — new: 5 regression tests for proxy query forwarding
- `backend/tests/test_sdk_network_permissions.py` — new: 7 regression tests for SDK network permission parsing
- `backend/pyproject.toml` — added `sdk` to pytest pythonpath
- `backend/tests/test_github_sync_engine.py` — fixed SDK stub to try real import first
