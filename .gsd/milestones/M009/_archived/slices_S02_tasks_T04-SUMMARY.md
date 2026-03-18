---
id: T04
parent: S02
milestone: M009
provides:
  - Real subprocess integration tests proving full SDK round-trip on UDS
  - Minimal SDK test app fixture for contract tests
key_files:
  - backend/tests/test_sdk_integration.py
  - backend/tests/fixtures/test_sdk_app/app.py
  - backend/tests/fixtures/test_sdk_app/manifest.yaml
key_decisions:
  - Used sync httpx.Client for UDS transport in tests — simpler than async, subprocess is already sync
  - Module-scoped subprocess fixture — one process serves all 7 tests, cuts test time to ~1.5s
patterns_established:
  - SDK integration test pattern: subprocess.Popen with SDK runner → wait for socket → httpx UDS client → exercise endpoints → terminate on teardown
  - Socket path uniqueness: /tmp/sempkm-app-test-sdk-{random8}.sock prevents parallel test collisions
observability_surfaces:
  - Test fixture captures stdout/stderr from subprocess and includes them in pytest.fail() on early exit or timeout
  - Subprocess emits uvicorn access logs + SDK lifecycle dispatch logs to stderr
duration: 15m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T04: Integration proof — real subprocess round-trip

**Built integration tests proving the full S02 contract: real SDK subprocess on UDS serving health, fragments, lifecycle, and tasks — 7 tests, 77 total S02 tests passing.**

## What Happened

Created a minimal SDK test app fixture at `backend/tests/fixtures/test_sdk_app/` with a manifest, an `app.py` that registers one route (`/_fragments/main`), one task (`test-task`), and one startup hook. The app uses real `sempkm_app_sdk` imports.

Built `test_sdk_integration.py` with a module-scoped subprocess fixture that starts the SDK runner via `python -m sempkm_app_sdk.runner`, waits for the UDS socket to appear, and yields a sync httpx client connected over UDS. Seven tests cover: health 200, health no-token, fragment HTML, lifecycle dispatch with token, lifecycle 403 without token, task dispatch with token, task 403 without token.

Used sync httpx instead of async — the UDS transport is straightforward HTTP, and the subprocess management is already synchronous. Module scope on the fixture means one subprocess serves all tests, keeping the run fast (~1.5s).

## Verification

- `cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v` — 7/7 passed
- `cd backend && .venv/bin/pytest tests/test_app_tokens.py tests/test_sdk_app.py tests/test_app_proxy.py tests/test_sdk_integration.py -v` — 77/77 passed (full S02 suite)

All four S02 verification checks pass:
- ✅ JWT generation/validation unit tests (17 tests)
- ✅ SDK App class unit tests (30 tests)
- ✅ Proxy/router unit tests (23 tests)
- ✅ Integration contract tests (7 tests)

## Diagnostics

- If subprocess fails to start: fixture captures stdout/stderr and includes in pytest failure message
- Socket path: `/tmp/sempkm-app-test-sdk-{random}.sock` — unique per run, cleaned up in teardown
- Subprocess logs: uvicorn access logs + SDK lifecycle dispatch logs available on stderr

## Deviations

- Used sync `httpx.Client` instead of `httpx.AsyncClient` — plan mentioned async but sync is simpler and sufficient since the fixture is already synchronous
- Token generated via `generate_app_token()` using platform secret (JWT), but SDK validates by shared-secret string comparison — both sides get the same opaque string, which is the correct contract

## Known Issues

- PyJWT warns about HMAC key length < 32 bytes in test environment (the test secret is shorter than recommended). Not a test issue — the warning comes from the dev-mode secret key.

## Files Created/Modified

- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — minimal valid app manifest for test fixture
- `backend/tests/fixtures/test_sdk_app/app.py` — SDK test app with route, task, and startup hook
- `backend/tests/fixtures/test_sdk_app/requirements.txt` — empty (SDK injected by platform)
- `backend/tests/test_sdk_integration.py` — 7 contract tests proving full SDK round-trip on UDS
- `.gsd/milestones/M009/slices/S02/tasks/T04-PLAN.md` — added Observability Impact section
- `.gsd/milestones/M009/slices/S02/S02-PLAN.md` — marked T04 done
