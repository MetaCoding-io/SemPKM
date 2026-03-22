---
estimated_steps: 7
estimated_files: 7
skills_used:
  - test
  - best-practices
---

# T01: Instance config module, setup endpoint, and config priority chain

**Slice:** S01 — Deployment & Onboarding Overhaul
**Milestone:** M033

## Description

Create the backend foundation for the deployment configuration system. This includes the InstanceConfig Pydantic model with load/save operations, a new `/api/setup/configure-instance` endpoint, integration of the config priority chain into the existing Settings class, extension of the auth status endpoint, and startup namespace validation. Comprehensive pytest unit tests cover the config priority chain and endpoint behavior.

The design reference is `.gsd/design/DEPLOYMENT-AND-ONBOARDING-DESIGN.md` sections 3 (Setup Wizard), 6 (BASE_NAMESPACE Strategy), and 8 (Implementation Plan Phase 1).

## Steps

1. **Create `backend/app/instance_config.py`:**
   - `InstanceConfig` Pydantic model: `instance_id: str`, `deployment_mode: str` (literal "local" | "domain" | "later"), `base_namespace: str`, `app_base_url: str`, `configured_at: str` (ISO datetime)
   - `generate_instance_id() -> str` — returns `str(uuid.uuid4())`
   - `load_instance_config(path: Path = Path("data/.instance-config.json")) -> InstanceConfig | None` — reads JSON, returns None if file absent or malformed
   - `save_instance_config(config: InstanceConfig, path: Path = ...) -> None` — atomic write (write `.tmp`, `os.replace` to target), creates parent dirs
   - Constants: `DEFAULT_CONFIG_PATH = Path("data/.instance-config.json")`

2. **Create `backend/app/api/setup_routes.py`:**
   - `setup_router = APIRouter(prefix="/api/setup", tags=["setup"])`
   - `POST /configure-instance` endpoint accepting `ConfigureInstanceRequest(mode: str, domain: str | None = None)`
   - Validation: mode must be "local" | "domain" | "later"; domain required when mode="domain"; domain validated (no protocol prefix, valid hostname regex)
   - Guard: if triplestore has user data in `urn:sempkm:current` graph, refuse with 409 Conflict
   - Logic: generate instance_id (or preserve existing), compute base_namespace and app_base_url per mode, write instance config, return `ConfigureInstanceResponse(base_namespace, app_base_url, instance_id)`
   - Local mode: `base_namespace = f"urn:sempkm:{instance_id}/"`, `app_base_url = "http://localhost:3000"`
   - Domain mode: `base_namespace = f"https://{domain}/data/"`, `app_base_url = f"https://{domain}"`
   - Later mode: `base_namespace = f"urn:sempkm:{instance_id}/"`, `app_base_url = ""`

3. **Modify `backend/app/config.py`:**
   - After `Settings` class definition, after `settings = Settings()`, attempt to load instance config
   - Apply priority chain: for `base_namespace` and `app_base_url`, if the field was NOT explicitly set via environment variable (check `os.environ.get()`), and instance config exists, override the settings field with the instance config value
   - Log which source won: `logger.info("base_namespace source: %s = %s", source, value)`
   - Import lazily to avoid circular imports if needed

4. **Extend `backend/app/auth/schemas.py` and `backend/app/auth/router.py`:**
   - Add `instance_configured: bool` to `StatusResponse`
   - In `auth_status()`: check if `data/.instance-config.json` exists, set `instance_configured` accordingly
   - In demo mode: return `instance_configured=True` (skip wizard)

5. **Add startup validation in `backend/app/main.py`:**
   - In lifespan, after SQL init, check if `settings.base_namespace == "https://example.org/data/"` and no instance config exists → `logger.warning("BASE_NAMESPACE is set to the default 'https://example.org/data/'. ...")`
   - Wire `setup_router` into the app: `from app.api.setup_routes import setup_router` then `app.include_router(setup_router)`

6. **Add `_is_html_route` exclusion:**
   - The new `/api/setup/` prefix already falls under `/api/` so no change needed to `_is_html_route()`. Verify this.

7. **Write `backend/tests/test_instance_config.py`:**
   - Test `InstanceConfig` model creation and serialization
   - Test `generate_instance_id()` returns valid UUID string
   - Test `save_instance_config()` + `load_instance_config()` round-trip
   - Test `load_instance_config()` returns None for missing file
   - Test `load_instance_config()` returns None for malformed JSON
   - Test atomic write behavior (file is complete or absent, no partial writes)
   - Test config priority chain: mock env vars and instance config, verify settings picks correct source
   - Test configure-instance endpoint: mock triplestore, verify local/domain/later modes produce correct config
   - Test configure-instance rejects invalid domain (protocol prefix, empty string)
   - Test configure-instance returns 409 when user data exists
   - Test StatusResponse includes `instance_configured`

## Must-Haves

- [ ] `InstanceConfig` Pydantic model with all fields from design doc
- [ ] Atomic write (write to .tmp, os.replace) prevents partial config files
- [ ] Config priority chain: env var > instance config > default
- [ ] `POST /api/setup/configure-instance` with mode validation, domain validation, data-exists guard
- [ ] `instance_configured: bool` in GET /api/auth/status
- [ ] Startup warning when base_namespace is example.org with no instance config
- [ ] Comprehensive pytest tests passing

## Verification

- `cd backend && python -m pytest tests/test_instance_config.py -v` — all tests pass
- `cd backend && python -c "from app.instance_config import InstanceConfig, load_instance_config, save_instance_config; print('imports ok')"` — module imports cleanly
- `grep -q "instance_configured" backend/app/auth/schemas.py` — field exists

## Observability Impact

- Signals added/changed: structured log at startup showing config source for base_namespace; warning when example.org default is active
- How a future agent inspects this: `GET /api/auth/status` → `instance_configured` field; read `data/.instance-config.json` directly
- Failure state exposed: 400 on invalid mode/domain, 409 when user data exists, warning log on dangerous default

## Inputs

- `backend/app/config.py` — existing Settings class to extend with instance config loading
- `backend/app/auth/router.py` — existing auth_status endpoint to extend
- `backend/app/auth/schemas.py` — existing StatusResponse to extend
- `backend/app/main.py` — existing lifespan to add startup validation and router wiring
- `backend/app/api/router.py` — existing API router module (sibling for new setup_routes)
- `.gsd/design/DEPLOYMENT-AND-ONBOARDING-DESIGN.md` — design reference for config model, endpoint, priority chain

## Expected Output

- `backend/app/instance_config.py` — new module with InstanceConfig model, load/save, generate_instance_id
- `backend/app/api/setup_routes.py` — new router with POST /api/setup/configure-instance
- `backend/app/config.py` — modified with instance config loading and priority chain
- `backend/app/auth/schemas.py` — modified StatusResponse with instance_configured field
- `backend/app/auth/router.py` — modified auth_status with instance_configured logic
- `backend/app/main.py` — modified with startup validation and setup_router wiring
- `backend/tests/test_instance_config.py` — new comprehensive test file
