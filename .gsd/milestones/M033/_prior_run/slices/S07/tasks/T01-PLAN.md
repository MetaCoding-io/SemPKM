---
estimated_steps: 7
estimated_files: 7
skills_used: []
---

# T01: Instance config model, configure-instance endpoint, and config priority chain

**Slice:** S07 — Deployment & Onboarding Overhaul
**Milestone:** M033

## Description

Create the foundational backend infrastructure for deployment mode configuration. This includes the `InstanceConfig` Pydantic model for reading/writing `data/.instance-config.json`, the `POST /api/setup/configure-instance` endpoint that accepts deployment mode and domain, the config priority chain that lets instance config override Pydantic defaults, startup namespace validation, and the `instance_configured` field on the auth status response. Comprehensive unit tests cover all paths.

## Steps

1. **Create `backend/app/instance_config.py`** with:
   - `InstanceConfig` Pydantic model: `instance_id: str`, `deployment_mode: str` (literal "local"|"domain"|"later"), `base_namespace: str`, `app_base_url: str`, `configured_at: str` (ISO 8601)
   - `load_instance_config(path: str | Path = "data/.instance-config.json") -> InstanceConfig | None` — reads and parses, returns None if file doesn't exist or is invalid
   - `save_instance_config(config: InstanceConfig, path: str | Path = "data/.instance-config.json")` — atomic write (write to `.tmp`, `os.replace`)
   - `generate_instance_id() -> str` — `str(uuid.uuid4())`

2. **Create `backend/app/api/setup_routes.py`** with:
   - Router with prefix `/api/setup`, tags `["setup"]`
   - `POST /configure-instance` endpoint accepting `{"mode": "local"|"domain"|"later", "domain": str | None}`
   - Mode `"local"`: generate instance ID, set `base_namespace=urn:sempkm:{uuid}/`, `app_base_url=http://localhost:3000`
   - Mode `"domain"`: validate domain (no protocol prefix, valid hostname regex), set `base_namespace=https://{domain}/data/`, `app_base_url=https://{domain}`
   - Mode `"later"`: generate instance ID, set `base_namespace=urn:sempkm:{uuid}/`, `app_base_url=""`
   - **Guard**: query triplestore `ASK { GRAPH <urn:sempkm:current> { ?s ?p ?o } }` — if true, return 409 Conflict ("Cannot change namespace after data has been created")
   - **Auth guard**: only callable when `setup_mode` is true OR no instance config exists. Return 403 otherwise.
   - Save config via `save_instance_config()`, return the config as JSON response
   - **Important**: this endpoint runs before an owner account exists — no auth dependency. But guard against post-setup calls.

3. **Modify `backend/app/config.py`** — after `settings = Settings()`, load instance config. If the file exists AND `settings.base_namespace` equals the Pydantic default `"https://example.org/data/"`, override `settings.base_namespace` with the instance config value. Same for `app_base_url` if it's empty. Add a module-level log message noting which config source won. Don't break imports — the `settings` object is used everywhere.

4. **Add startup namespace validation in `backend/app/main.py`** — in the lifespan startup block, after setup mode detection: if `settings.base_namespace == "https://example.org/data/"` and `load_instance_config()` returns None, log a WARNING about IRI collisions. Also set `app.state.instance_configured` based on whether instance config file exists.

5. **Update `backend/app/auth/schemas.py`** — add `instance_configured: bool` field to `StatusResponse` with default `False`.

6. **Update `backend/app/auth/router.py`** — in `auth_status()`, read `instance_configured` from `request.app.state` (defaulting to `True` in demo mode) and include it in the response.

7. **Register the setup router in `backend/app/main.py`** — import `setup_router` from `app.api.setup_routes` and call `app.include_router(setup_router)`. Place it near the other API routers.

8. **Write `backend/tests/test_instance_config.py`** covering:
   - `generate_instance_id()` returns valid UUID string
   - `save_instance_config()` + `load_instance_config()` round-trip
   - `load_instance_config()` returns None for missing file
   - `load_instance_config()` returns None for invalid JSON
   - `POST /api/setup/configure-instance` with mode=local — correct namespace format
   - `POST /api/setup/configure-instance` with mode=domain — correct namespace format
   - `POST /api/setup/configure-instance` with mode=domain, missing domain — 422
   - `POST /api/setup/configure-instance` with mode=domain, invalid domain — 422
   - `POST /api/setup/configure-instance` with mode=later — UUID namespace
   - Namespace guard: returns 409 when triplestore has data (mock the triplestore check)
   - Auth guard: returns 403 when setup_mode is false and instance config exists
   - `GET /api/auth/status` includes `instance_configured` field

## Must-Haves

- [ ] `InstanceConfig` model validates all fields
- [ ] Atomic file write prevents corruption on crash
- [ ] Configure-instance endpoint refuses namespace change when user data exists (409)
- [ ] Configure-instance endpoint callable without auth during setup mode
- [ ] Config priority: env var > instance config > Pydantic default
- [ ] `instance_configured` field in auth status response
- [ ] Unit tests pass for all modes and edge cases

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` — all tests pass
- `rg "instance_configured" backend/app/auth/schemas.py backend/app/auth/router.py` — field exists in both
- `rg "setup_router\|setup_routes" backend/app/main.py` — router is registered

## Observability Impact

- Signals added/changed: startup WARNING log when `base_namespace` is `example.org` without instance config; INFO log when instance config overrides Pydantic default
- How a future agent inspects this: check `data/.instance-config.json` file content; `GET /api/auth/status` response includes `instance_configured`
- Failure state exposed: 409 Conflict response with message when namespace change is attempted after data creation

## Inputs

- `backend/app/config.py` — existing Settings class to extend with config priority chain
- `backend/app/main.py` — lifespan startup block where namespace validation and router registration go
- `backend/app/auth/router.py` — auth_status endpoint to extend with `instance_configured`
- `backend/app/auth/schemas.py` — StatusResponse model to extend
- `backend/app/api/router.py` — existing API router pattern reference

## Expected Output

- `backend/app/instance_config.py` — new InstanceConfig model with load/save/generate
- `backend/app/api/setup_routes.py` — new configure-instance endpoint
- `backend/app/config.py` — modified with instance config loading
- `backend/app/main.py` — modified with startup validation, router registration, instance_configured state
- `backend/app/auth/schemas.py` — modified with instance_configured field
- `backend/app/auth/router.py` — modified with instance_configured in status response
- `backend/tests/test_instance_config.py` — comprehensive test suite
