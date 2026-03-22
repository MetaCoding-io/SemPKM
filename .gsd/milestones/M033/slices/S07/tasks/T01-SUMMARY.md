---
id: T01
parent: S07
milestone: M033
provides:
  - InstanceConfig Pydantic model with load/save/generate
  - POST /api/setup/configure-instance endpoint with mode validation, namespace guard, auth guard
  - Config priority chain (env var > instance config > Pydantic default)
  - Startup namespace validation warning
  - instance_configured field in GET /api/auth/status
key_files:
  - backend/app/instance_config.py
  - backend/app/api/setup_routes.py
  - backend/app/config.py
  - backend/app/main.py
  - backend/app/auth/schemas.py
  - backend/app/auth/router.py
  - backend/tests/test_instance_config.py
key_decisions:
  - Auth guard allows configure-instance when setup_mode=True OR no config file exists (not just setup_mode)
  - Config override checks os.environ directly for BASE_NAMESPACE/APP_BASE_URL presence rather than comparing to default, ensuring env vars always win
patterns_established:
  - httpx.AsyncClient + ASGITransport for endpoint testing with mock app state (first use in this codebase)
  - Atomic config file write via tmp + os.replace pattern
observability_surfaces:
  - data/.instance-config.json file presence and content
  - GET /api/auth/status instance_configured field
  - Startup WARNING log when base_namespace is example.org with no instance config
  - Startup INFO log when instance config overrides Pydantic default
  - 409 Conflict response when namespace change attempted after data creation
duration: 30m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Instance config model, configure-instance endpoint, and config priority chain

**Added InstanceConfig model with atomic persistence, configure-instance endpoint with deployment mode validation and namespace guard, config priority chain, and instance_configured in auth status**

## What Happened

Created `backend/app/instance_config.py` with the `InstanceConfig` Pydantic model (Literal-constrained deployment_mode), `generate_instance_id()`, `load_instance_config()` (returns None for missing/corrupt files), and `save_instance_config()` (atomic write via tmp + os.replace).

Created `backend/app/api/setup_routes.py` with `POST /api/setup/configure-instance`. The endpoint supports three modes: `local` (URN namespace, localhost URL), `domain` (HTTPS namespace from validated hostname), and `later` (URN namespace, empty URL). Two guards protect it: an auth guard (403 when not in setup_mode and config already exists) and a namespace guard (409 when triplestore has data in urn:sempkm:current).

Modified `backend/app/config.py` to apply instance config overrides after `settings = Settings()`. The override checks `os.environ` directly for `BASE_NAMESPACE` and `APP_BASE_URL` — only applies instance config values when no explicit env var is set and the setting is still at its Pydantic default. This preserves the priority chain: env var > instance config > default.

Added startup namespace validation in `main.py` lifespan: logs a WARNING when `base_namespace` is still `example.org` and no instance config exists. Also sets `app.state.instance_configured` for the auth status endpoint.

Extended `StatusResponse` with `instance_configured: bool = False` and updated `auth_status()` to populate it from app state (defaulting to `True` in demo mode).

Registered `setup_router` in `main.py` alongside the other API routers.

## Verification

- All 26 unit tests pass covering model validation, UUID generation, save/load round-trip, missing/invalid file handling, all three deployment modes, domain validation (protocol prefix rejection, invalid hostname), namespace guard (409), auth guard (403), mode-without-config bypass, invalid mode rejection, auth status with instance_configured in all states
- `rg "instance_configured"` confirms field in both schemas.py and router.py
- `rg "setup_router|setup_routes"` confirms router registration in main.py

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` | 0 | ✅ pass | 0.55s |
| 2 | `rg "instance_configured" backend/app/auth/schemas.py backend/app/auth/router.py` | 0 | ✅ pass | <0.1s |
| 3 | `rg "setup_router\|setup_routes" backend/app/main.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Config file**: check `data/.instance-config.json` for current deployment mode and namespace
- **Auth status**: `GET /api/auth/status` returns `instance_configured: true/false`
- **Startup logs**: look for `base_namespace overridden by instance config` (INFO) or `base_namespace is still 'https://example.org/data/'` (WARNING)
- **Failure path**: `POST /api/setup/configure-instance` returns 409 with detail `"Cannot change namespace after data has been created"` when triplestore has data; 403 with `"Instance already configured"` when called post-setup

## Deviations

None.

## Known Issues

- The `HTTP_422_UNPROCESSABLE_ENTITY` constant used in setup_routes.py produces a FastAPI deprecation warning suggesting `HTTP_422_UNPROCESSABLE_CONTENT` — cosmetic only, no functional impact.

## Files Created/Modified

- `backend/app/instance_config.py` — new: InstanceConfig model, load/save/generate functions
- `backend/app/api/setup_routes.py` — new: POST /api/setup/configure-instance endpoint with guards
- `backend/app/config.py` — modified: instance config override logic after Settings() instantiation
- `backend/app/main.py` — modified: startup namespace validation, instance_configured state, setup_router registration
- `backend/app/auth/schemas.py` — modified: added instance_configured field to StatusResponse
- `backend/app/auth/router.py` — modified: populate instance_configured in auth_status()
- `backend/tests/test_instance_config.py` — new: 26 tests covering model, persistence, endpoint, guards, config priority
- `.gsd/milestones/M033/slices/S07/S07-PLAN.md` — added failure-path verification step per pre-flight check
