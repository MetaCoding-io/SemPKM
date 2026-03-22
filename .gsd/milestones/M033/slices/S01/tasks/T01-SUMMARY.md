---
id: T01
parent: S01
milestone: M033
provides:
  - InstanceConfig Pydantic model with load/save/generate
  - POST /api/setup/configure-instance endpoint (local/domain/later modes)
  - Config priority chain (env var > instance config > default)
  - instance_configured field in GET /api/auth/status
  - Startup namespace validation warning
key_files:
  - backend/app/instance_config.py
  - backend/app/api/setup_routes.py
  - backend/app/config.py
  - backend/app/auth/schemas.py
  - backend/app/auth/router.py
  - backend/app/main.py
  - backend/tests/test_instance_config.py
key_decisions:
  - Atomic write via os.replace prevents partial config files
  - load/save use None default + runtime DEFAULT_CONFIG_PATH resolution for testability
  - Config priority chain applied at module load via _apply_instance_config_overrides()
  - ASK query against urn:sempkm:current for user-data guard (fail-open on triplestore error)
patterns_established:
  - Instance config path uses None default parameter with module-level DEFAULT_CONFIG_PATH fallback for clean monkeypatching in tests
observability_surfaces:
  - Structured log at startup: "base_namespace source: {env|instance_config|default} = {value}"
  - Warning log when base_namespace is example.org with no instance config
  - GET /api/auth/status → instance_configured: bool
  - data/.instance-config.json human-readable JSON on disk
  - 400/409 error responses with descriptive detail messages
duration: 25min
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Instance config module, setup endpoint, and config priority chain

**Created InstanceConfig model with atomic save/load, POST /api/setup/configure-instance endpoint with domain validation and user-data guard, config priority chain (env > instance config > default), instance_configured in auth status, and startup namespace warning — 32 tests passing.**

## What Happened

Built the backend foundation for the deployment configuration system per the design doc:

1. **`backend/app/instance_config.py`** — InstanceConfig Pydantic model with `Literal["local", "domain", "later"]` deployment_mode, generate_instance_id (UUID v4), load_instance_config (returns None on absent/malformed), save_instance_config (atomic write via .tmp + os.replace). Functions use `None` default parameter that resolves to module-level `DEFAULT_CONFIG_PATH` at runtime, enabling clean monkeypatching in tests.

2. **`backend/app/api/setup_routes.py`** — setup_router with `POST /api/setup/configure-instance`. Validates mode (Pydantic Literal), validates domain (RFC-952 regex, protocol prefix rejection), checks for user data via ASK SPARQL against urn:sempkm:current (409 if data exists, fail-open if triplestore unreachable). Preserves existing instance_id on reconfiguration. Computes base_namespace and app_base_url per mode per design doc spec.

3. **`backend/app/config.py`** — Added `_apply_instance_config_overrides()` called at module load after `settings = Settings()`. Checks `os.environ.get()` for each overridable field; only applies instance config when env var is absent. Logs which source won for base_namespace.

4. **`backend/app/auth/schemas.py`** — Added `instance_configured: bool` to StatusResponse.

5. **`backend/app/auth/router.py`** — auth_status checks `DEFAULT_CONFIG_PATH.is_file()` to set instance_configured. Demo mode returns `instance_configured=True`.

6. **`backend/app/main.py`** — Added startup warning when base_namespace is example.org with no instance config. Wired setup_router into the app.

7. **`backend/tests/test_instance_config.py`** — 32 tests covering model validation, UUID generation, save/load round-trip, missing/malformed file handling, atomic write, config priority chain, all three endpoint modes, domain validation (protocol prefix, empty, invalid hostname), 409 conflict, instance_id preservation, and StatusResponse field.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` — **32 passed**
- `cd backend && .venv/bin/python -c "from app.instance_config import InstanceConfig, load_instance_config, save_instance_config; print('imports ok')"` — **imports ok**
- `grep -q "instance_configured" backend/app/auth/schemas.py` — **PASS**
- `grep -q "configure-instance" backend/app/api/setup_routes.py` — **PASS**
- Existing test suites (test_demo_mode.py, test_api_surface.py) still pass: **76 passed**

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` | 0 | ✅ pass | 0.29s |
| 2 | `cd backend && .venv/bin/python -c "from app.instance_config import ..."` | 0 | ✅ pass | 4.0s |
| 3 | `grep -q "instance_configured" backend/app/auth/schemas.py` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "configure-instance" backend/app/api/setup_routes.py` | 0 | ✅ pass | <0.1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_demo_mode.py tests/test_api_surface.py -v` | 0 | ✅ pass | 1.49s |

## Diagnostics

- **Startup log:** Look for `base_namespace source: {env|instance_config|default} = ...` in API startup logs
- **Warning log:** Look for `BASE_NAMESPACE is set to the default 'https://example.org/data/'` when no instance config exists
- **API inspection:** `GET /api/auth/status` → `instance_configured` field indicates whether the wizard has been completed
- **File inspection:** `cat data/.instance-config.json` shows current deployment configuration
- **Error responses:** `POST /api/setup/configure-instance` returns 400 with descriptive detail on invalid mode/domain, 409 when user data exists

## Deviations

- Changed `load_instance_config` and `save_instance_config` to use `path: Path | None = None` instead of `path: Path = DEFAULT_CONFIG_PATH` default. The original design used a default parameter that captures the Path object at function definition time, making it impossible to monkeypatch `DEFAULT_CONFIG_PATH` in tests. The new pattern evaluates the module-level constant at call time.

## Known Issues

None.

## Files Created/Modified

- `backend/app/instance_config.py` — **new** — InstanceConfig model, generate_instance_id, load/save with atomic write
- `backend/app/api/setup_routes.py` — **new** — setup_router with POST /api/setup/configure-instance
- `backend/app/config.py` — **modified** — added _apply_instance_config_overrides() priority chain at module load
- `backend/app/auth/schemas.py` — **modified** — added instance_configured: bool to StatusResponse
- `backend/app/auth/router.py` — **modified** — auth_status returns instance_configured from config file check
- `backend/app/main.py` — **modified** — startup namespace warning, setup_router wiring
- `backend/tests/test_instance_config.py` — **new** — 32 comprehensive tests
