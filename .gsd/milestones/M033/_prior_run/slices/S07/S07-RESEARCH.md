# S07 Research: Deployment & Onboarding Overhaul

**Slice:** S07 — Deployment & Onboarding Overhaul
**Depth:** Targeted
**Date:** 2026-03-21

---

## Summary

S07 implements the three proposals from the approved design doc (`.gsd/design/DEPLOYMENT-AND-ONBOARDING-DESIGN.md`): (1) setup wizard deployment mode step with instance config persistence, (2) Caddy cloud compose profile for automatic HTTPS, and (3) optional local TLS via mkcert. The design is thorough and prescriptive — file-by-file, endpoint-by-endpoint. The main work is careful execution of a well-specified plan.

The codebase is well-prepared: the setup wizard (`setup.html` + `auth.js`) is a simple single-step form, `config.py` is a flat Pydantic Settings class, and the auth status/setup endpoints are clean and isolated. The Caddy pattern is proven from the demo instance (`Caddyfile`, `docker-compose.demo.yml`). No unfamiliar technology.

---

## Recommendation

Execute the design doc's 5 phases as 4 tasks:

1. **T01: Instance config model + backend endpoint** — `instance_config.py`, setup route, `config.py` integration, startup validation. This is the foundation everything else depends on.
2. **T02: Setup wizard UI** — `setup.html` multi-step, `auth.js` flow, CSS, `StatusResponse` extension. Depends on T01's endpoint.
3. **T03: Caddy cloud profile + infrastructure** — `Caddyfile.cloud`, `docker-compose.cloud.yml`, rename `Caddyfile` → `Caddyfile.demo`, `.env.cloud.example`, local-tls profile. Independent of T01/T02.
4. **T04: Documentation updates** — Production deployment chapter, installation chapter, new cloud deployment chapter, env var appendix, `.gitignore`, guide index sync. Depends on T01-T03 being done.

T01 and T03 are independent and could run in parallel. T02 depends on T01. T04 depends on all.

---

## Implementation Landscape

### Files to Create

| File | Purpose | Complexity |
|------|---------|------------|
| `backend/app/instance_config.py` | Pydantic model (`InstanceConfig`), `load_instance_config()`, `save_instance_config()`, `generate_instance_id()`. Reads/writes `data/.instance-config.json`. | Low — ~60 lines, standard file I/O with atomic write (`.tmp` + rename) |
| `backend/app/api/setup_routes.py` | `POST /api/setup/configure-instance` — accepts `{mode, domain?}`, validates, writes config, returns derived namespace. Guard: refuses if user data exists. | Medium — ~80 lines, needs triplestore check for existing data |
| `Caddyfile.cloud` | Cloud Caddy template with `{$SEMPKM_DOMAIN}`, static file serving, API reverse proxy. | Low — ~30 lines, follows proven demo Caddyfile pattern |
| `docker-compose.cloud.yml` | Compose override replacing nginx with Caddy for cloud deployments. | Low — ~30 lines, follows docker-compose.demo.yml pattern |
| `.env.cloud.example` | Example cloud environment variables | Low — ~10 lines |
| `Caddyfile.local-tls` | Local TLS Caddy config using mkcert certs | Low — ~20 lines |
| `docker-compose.local-tls.yml` | Local TLS compose override | Low — ~20 lines |

### Files to Modify

| File | Change | Risk |
|------|--------|------|
| `backend/app/config.py` | Load instance config at import time, priority chain: env var > instance config > Pydantic default. Add `instance_config_path` field. | **Medium** — `Settings` is imported everywhere. Must not break when `data/.instance-config.json` doesn't exist (the common case during development). |
| `backend/app/main.py` | (1) Import and register `setup_routes` router. (2) Add startup namespace validation warning. (3) Add `instance_configured` to setup mode detection. | Low — additive changes only |
| `backend/app/auth/router.py` | Add `instance_configured: bool` to `GET /api/auth/status` response. | Low — one field addition |
| `backend/app/auth/schemas.py` | Add `instance_configured: bool` to `StatusResponse`. | Low — one field |
| `frontend/static/setup.html` | Two-step wizard: deployment mode (radio group) → account creation. | Medium — full HTML rewrite of the form area |
| `frontend/static/js/auth.js` | `checkAuthStatus()` handles `instance_configured`. `handleSetupForm()` becomes multi-step: step 1 calls configure-instance, step 2 calls setup. | Medium — significant JS logic change |
| `frontend/static/css/style.css` | Step indicator styling, radio card styling for deployment mode. | Low — additive CSS |
| `Caddyfile` → `Caddyfile.demo` | Rename. | Trivial |
| `docker-compose.demo.yml` | Reference `Caddyfile.demo` instead of `Caddyfile`. | Trivial — but currently the demo compose doesn't reference the Caddyfile at all (it uses `nginx.demo.conf`). The existing `Caddyfile` runs on the host, not in Docker. Renaming is purely organizational. |
| `.gitignore` | Add `certs/` line | Trivial |
| `docs/guide/03-installation-and-setup.md` | Document new setup wizard flow | Low |
| `docs/guide/20-production-deployment.md` | Add Caddy cloud profile section | Low |
| `docs/guide/appendix-a-environment-variables.md` | Add `SEMPKM_DOMAIN`, document instance config file | Low |
| `docs/guide/README.md` + `docs/guide/index.html` + `backend/app/templates/guide.html` | Add new cloud deployment chapter link (Knowledge: 3 files must stay in sync) | Low |

### Existing Patterns to Follow

**Config priority chain (design doc §3):** env var > instance config > Pydantic default. The mechanism: `config.py` currently uses `SettingsConfigDict(env_file=".env")`. After loading Pydantic defaults, check if `data/.instance-config.json` exists and override `base_namespace` and `app_base_url` if the env vars aren't explicitly set. The tricky part: Pydantic's `env_file` loading makes it hard to distinguish "env var was set" from "default was used". Solution: check `os.environ.get("BASE_NAMESPACE")` directly — if None, the value came from Pydantic default or .env file, and instance config should win.

**Auth status flow:** `GET /api/auth/status` → `StatusResponse(setup_complete, setup_mode)` → frontend `checkAuthStatus()` redirects to `/setup.html` if `setup_mode=true`. Extending this with `instance_configured` field lets the frontend show step 1 or step 2 based on state.

**Setup mode detection (main.py:388-405):** After checking `is_setup_complete()`, sets `app.state.setup_mode` and logs the setup token. Instance configuration check should happen in the same block — if `data/.instance-config.json` doesn't exist and `BASE_NAMESPACE` is still `example.org`, set a flag.

**Caddy pattern (demo):** The existing `Caddyfile` is a host-level reverse proxy to Docker on port 3902. The *cloud* Caddyfile is different — it runs *inside* Docker, replacing nginx, and proxies directly to `api:8000`. The cloud compose override replaces the `frontend` service entirely.

**Docker compose override:** `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up`. The override file redefines the `frontend` service. Must include the same network (`sempkm`) and health check dependency on `api`.

### Critical Constraints

1. **Config loading must not break existing setups.** When `data/.instance-config.json` doesn't exist (every existing installation), behavior must be identical to current. The instance config is purely additive.

2. **`POST /api/setup/configure-instance` must be callable without authentication.** It runs before the owner account exists. But it must be guarded — only callable when `setup_mode` is true or no instance config exists. Otherwise anyone could change the namespace.

3. **Namespace change guard.** If the triplestore has data in `urn:sempkm:current`, the configure-instance endpoint must refuse to change the namespace. The design doc specifies this. Implementation: query `ASK { GRAPH <urn:sempkm:current> { ?s ?p ?o } }` — if true, return 409 Conflict.

4. **The demo compose doesn't use the Caddyfile in Docker.** The existing `Caddyfile` runs on the host machine (bare metal Caddy → Docker nginx). The demo compose uses `nginx.demo.conf`. Renaming `Caddyfile` to `Caddyfile.demo` is organizational — it doesn't affect the demo compose file's `volumes` section.

5. **Caddy static serving must replicate nginx location blocks.** The nginx.conf has specific locations for `/css/`, `/js/`, `/assets/`, SSE streams (with `proxy_buffering off`), WebDAV, and the catch-all. The Caddyfile.cloud must handle all these paths. SSE streams need `flush_interval -1` in Caddy (equivalent to `proxy_buffering off`).

6. **Three guide files must stay in sync** (Knowledge entry). `docs/guide/README.md`, `docs/guide/index.html`, and `backend/app/templates/guide.html` all need the new cloud deployment chapter entry.

### Verification Approach

- **T01 (backend):** Unit tests for `instance_config.py` (load/save/generate), integration test for `POST /api/setup/configure-instance` (all three modes, domain validation, namespace guard). Run `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v`.
- **T02 (frontend):** Manual verification via browser — navigate to `setup.html`, confirm two-step flow renders, confirm step 1 calls configure-instance, confirm step 2 calls setup. Since there's no Playwright test infrastructure for the setup flow, CSS/HTML review + API call verification is sufficient.
- **T03 (infrastructure):** `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config` — validates the merged compose. Verify `Caddyfile.cloud` syntax with `caddy validate --config Caddyfile.cloud` (if Caddy is available on host). Verify `.env.cloud.example` has all required vars.
- **T04 (docs):** Verify all three guide index files are in sync. Check that links resolve (`rg "21-cloud-deployment" docs/guide/`).

### Noteworthy Details

- **`os.environ` check for config priority.** Pydantic v2's `SettingsConfigDict(env_file=".env")` loads `.env` file values as if they were environment variables. After `Settings()` is constructed, there's no built-in way to know if a value came from an explicit env var, the .env file, or the Pydantic default. However, `os.environ.get("BASE_NAMESPACE")` returns the value only if it's in the actual process environment (Docker `environment:` section sets this). The `.env` file loaded by Pydantic does NOT set `os.environ`. So: if `os.environ.get("BASE_NAMESPACE")` is not None, the operator explicitly set it and instance config should not override.

  **Update:** Actually, Pydantic with `env_file=".env"` does NOT put `.env` values into `os.environ`. But Docker Compose's `env_file: .env` directive in `docker-compose.yml` DOES set them in the container's environment. The current `docker-compose.yml` uses `environment:` with `${BASE_NAMESPACE:-https://example.org/data/}` shell substitution, which means `BASE_NAMESPACE` will always be in `os.environ` inside the container. **The priority detection needs a different approach.**

  **Better approach:** Add a sentinel. If `data/.instance-config.json` exists, load it. Apply its values only when the current config value matches the Pydantic default (`https://example.org/data/`). If someone has explicitly set a non-default `BASE_NAMESPACE` in `.env` or `docker-compose.yml`, it won't match the default, and instance config won't override it. This is imperfect (what if someone intentionally set `BASE_NAMESPACE=https://example.org/data/`?) but covers the real-world case.

  **Simplest correct approach:** In `docker-compose.yml`, change `BASE_NAMESPACE: ${BASE_NAMESPACE:-https://example.org/data/}` to `BASE_NAMESPACE: ${BASE_NAMESPACE:-}`. When the env var is empty/unset, `config.py` uses the Pydantic default. Then the instance config check is: if `settings.base_namespace == "https://example.org/data/"` (still the default), instance config takes priority. This is a one-line change to `docker-compose.yml` but represents a semantic shift — the compose file no longer provides the default; Pydantic does.

- **Caddy SSE handling.** nginx has several SSE-specific location blocks (`/browser/llm/chat/stream`, `/api/lint/stream`). In Caddy, the equivalent is `flush_interval -1` on the reverse_proxy directive, which disables response buffering. This can be set globally or per-path. Since most routes are fine with buffering, use `handle_path` blocks for SSE endpoints with `flush_interval -1`.

- **Caddy WebDAV proxy.** The nginx config has a dedicated `/dav/` location with `Authorization` header forwarding and extended timeouts. Caddy's `reverse_proxy` forwards all headers by default including `Authorization`, so no special config is needed. Timeouts: Caddy's default read/write timeouts are generous enough for WebDAV PROPFIND.

- **Caddy merge_slashes.** The design doc correctly notes Caddy doesn't merge slashes by default — this was a known nginx issue that required `merge_slashes off`. No action needed.

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Config priority detection inside Docker | Use Pydantic default as sentinel: if `base_namespace` is still `https://example.org/data/`, instance config takes priority. Explicit non-default values in .env/compose always win. |
| Caddy SSE streaming | Use `flush_interval -1` on reverse_proxy for SSE paths |
| Scope of Caddyfile rename | `Caddyfile` → `Caddyfile.demo` is organizational only. The demo compose doesn't volume-mount it — it's used by host-level Caddy. |
| User guide sync | Three files: `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`. Knowledge entry confirms. |
