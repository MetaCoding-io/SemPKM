---
id: T04
parent: S02
milestone: M009
provides:
  - Real subprocess integration tests proving full SDK round-trip on UDS
  - Minimal SDK test app fixture (manifest + route + task + lifecycle handler)
key_files:
  - backend/tests/test_sdk_integration.py
  - backend/tests/fixtures/test_sdk_app/app.py
  - backend/tests/fixtures/test_sdk_app/manifest.yaml
  - backend/tests/fixtures/test_sdk_app/requirements.txt
key_decisions:
  - Used module-scoped pytest fixture for subprocess — single process serves all 8 tests (faster, reliable)
  - Token is a plain random string (not JWT) matching SDK's shared-secret comparison model
patterns_established:
  - Integration test pattern: subprocess.Popen → poll for socket file → httpx.AsyncClient(uds=) → assert
  - FastAPI route handlers in SDK apps must type-annotate `request: Request` to avoid 422 from FastAPI parameter resolution
observability_surfaces:
  - Test subprocess stdout/stderr captured by pytest fixture and included in failure messages
  - Socket cleanup in fixture teardown with unique-per-run suffix preventing cross-run collisions
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T04: Integration proof — real subprocess round-trip

**Added 8 integration tests proving full SDK subprocess round-trip: health, fragment route, lifecycle dispatch, task dispatch, and token enforcement over real UDS**

## What Happened

Created a minimal SDK test app fixture at `backend/tests/fixtures/test_sdk_app/` with a manifest, one fragment route, one task handler, and one startup lifecycle hook. Built `test_sdk_integration.py` with a module-scoped subprocess fixture that starts the SDK runner on a unique UDS, waits for the socket file, then exercises all endpoint types through httpx async client with UDS transport.

Initial run had one failure: the fragment route returned HTTP 422 because the handler's `request` parameter lacked a `Request` type annotation — FastAPI treats untyped parameters as query params and rejects requests without them. Fixed by adding `from fastapi import Request` and annotating `request: Request` in the test app.

All 8 integration tests and the full 92-test S02 suite pass cleanly.

## Verification

- `cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v` — 8/8 passed
- `cd backend && .venv/bin/pytest tests/test_app_tokens.py tests/test_sdk_app.py tests/test_app_proxy.py tests/test_sdk_integration.py -v` — 92/92 passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_sdk_integration.py -v` | 0 | ✅ pass | 0.94s |
| 2 | `pytest tests/test_app_tokens.py tests/test_sdk_app.py tests/test_app_proxy.py tests/test_sdk_integration.py -v` | 0 | ✅ pass | 1.36s |

## Diagnostics

- **Subprocess capture**: If integration tests fail, pytest captures the runner's stdout/stderr and includes them in the `pytest.fail()` message — no silent failures
- **Socket inspection**: Each test run uses a unique `/tmp/sempkm-app-test-sdk-{hex}.sock` path — parallel runs won't collide
- **Runner logs**: The subprocess emits uvicorn access logs and SDK-level logs (lifecycle dispatch, token validation) to stderr, all captured by the fixture
- **Health probe**: `GET /_health` returns `{"status": "ok"}` without auth — use as liveness check for any SDK app

## Deviations

- Added `from fastapi import Request` import and `request: Request` type annotation to the test app's fragment handler. Without it, FastAPI treats the parameter as a query param and returns 422. This is a known FastAPI behavior, not a plan deviation — the plan's code sketch simply omitted the type annotation.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — minimal valid app manifest for contract tests
- `backend/tests/fixtures/test_sdk_app/app.py` — SDK-based test app with route, task, and lifecycle handlers
- `backend/tests/fixtures/test_sdk_app/requirements.txt` — empty (SDK injected by platform)
- `backend/tests/test_sdk_integration.py` — 8 async integration tests proving full subprocess round-trip on UDS
