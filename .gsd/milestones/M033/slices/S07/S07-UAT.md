# S07 UAT: Deployment & Onboarding Overhaul

## Preconditions
- SemPKM Docker stack is not running (or can be restarted for clean-state tests)
- Access to a terminal with docker compose available
- Working directory is the SemPKM project root

---

## Test 1: Instance Config Model Persistence

**Goal:** Verify instance config can be saved, loaded, and survives corruption

1. Run: `cd backend && .venv/bin/python -c "from app.instance_config import *; cfg = InstanceConfig(instance_id=generate_instance_id(), deployment_mode='local', base_namespace='urn:sempkm:test/', app_base_url='http://localhost:3901'); save_instance_config(cfg, '/tmp/test-ic.json'); loaded = load_instance_config('/tmp/test-ic.json'); print(f'Mode: {loaded.deployment_mode}, NS: {loaded.base_namespace}')"`
   - **Expected:** `Mode: local, NS: urn:sempkm:test/`
2. Run: `echo "not json" > /tmp/test-ic-bad.json && cd backend && .venv/bin/python -c "from app.instance_config import load_instance_config; print(load_instance_config('/tmp/test-ic-bad.json'))"`
   - **Expected:** `None` (corrupt file handled gracefully)
3. Run: `cd backend && .venv/bin/python -c "from app.instance_config import load_instance_config; print(load_instance_config('/tmp/nonexistent.json'))"`
   - **Expected:** `None` (missing file handled gracefully)

---

## Test 2: Configure-Instance Endpoint — All Three Modes

**Goal:** Verify each deployment mode produces correct namespace and app_base_url

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_mode_local -v`
   - **Expected:** PASSED — local mode sets `urn:sempkm:{uuid}/` namespace and `http://localhost:3901` app_base_url
2. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_mode_domain -v`
   - **Expected:** PASSED — domain mode sets `https://{domain}/data/` namespace and `https://{domain}` app_base_url
3. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_mode_later -v`
   - **Expected:** PASSED — later mode sets `urn:sempkm:{uuid}/` namespace with empty app_base_url

---

## Test 3: Namespace Guard (One-Way Door)

**Goal:** Verify the endpoint refuses namespace changes after data exists

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_namespace_guard_409_when_data_exists -v`
   - **Expected:** PASSED — returns HTTP 409 with `"Cannot change namespace after data has been created"`
2. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_auth_guard_403_when_not_setup_mode_and_config_exists -v`
   - **Expected:** PASSED — returns HTTP 403 with `"Instance already configured"`

---

## Test 4: Domain Validation

**Goal:** Verify invalid domain inputs are rejected with clear errors

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_mode_domain_missing_domain -v`
   - **Expected:** PASSED — missing domain field rejected
2. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_mode_domain_invalid_domain -v`
   - **Expected:** PASSED — domain with `http://` prefix rejected
3. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_mode_domain_invalid_hostname -v`
   - **Expected:** PASSED — invalid hostname (e.g., `not a domain`) rejected

---

## Test 5: Config Priority Chain

**Goal:** Verify env var > instance config > default precedence

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigPriorityChain::test_instance_config_overrides_default_namespace -v`
   - **Expected:** PASSED — instance config wins over Pydantic default
2. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigPriorityChain::test_env_var_takes_priority_over_instance_config -v`
   - **Expected:** PASSED — explicit env var wins over instance config

---

## Test 6: Auth Status Includes instance_configured

**Goal:** Verify the status endpoint reports configuration state

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestAuthStatusInstanceConfigured -v`
   - **Expected:** All 3 tests PASSED — `instance_configured` is false when no config, true when config exists, true in demo mode

---

## Test 7: Setup Wizard Two-Step UI

**Goal:** Verify setup.html contains the two-step wizard structure

1. Run: `grep -c "step-1\|setup-step-1" frontend/static/setup.html`
   - **Expected:** ≥1 (step 1 container exists)
2. Run: `grep -c "step-2\|setup-step-2" frontend/static/setup.html`
   - **Expected:** ≥1 (step 2 container exists)
3. Run: `grep -c "deployment-mode\|radio-card" frontend/static/setup.html`
   - **Expected:** ≥1 (deployment mode radio cards exist)
4. Run: `grep -q "configure-instance" frontend/static/js/auth.js && echo OK`
   - **Expected:** `OK` (auth.js calls the configure-instance endpoint)
5. Run: `grep -q "instance_configured" frontend/static/js/auth.js && echo OK`
   - **Expected:** `OK` (auth.js checks instance_configured in status response)
6. Run: `grep -q "handleDeploymentStep\|_showSetupStep" frontend/static/js/auth.js && echo OK`
   - **Expected:** `OK` (wizard step management functions exist)

---

## Test 8: Caddy Cloud Profile Validates

**Goal:** Verify docker-compose.cloud.yml merges cleanly with base compose

1. Run: `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet`
   - **Expected:** Exit 0, no output (valid merged compose)
2. Run: `grep -c "SEMPKM_DOMAIN" Caddyfile.cloud`
   - **Expected:** ≥1 (domain template variable used)
3. Run: `grep -c "flush_interval" Caddyfile.cloud`
   - **Expected:** ≥1 (SSE streaming configured)
4. Run: `grep -c "reverse_proxy" Caddyfile.cloud`
   - **Expected:** ≥1 (API proxy configured)

---

## Test 9: Local TLS Profile Validates

**Goal:** Verify docker-compose.local-tls.yml merges cleanly

1. Run: `docker compose -f docker-compose.yml -f docker-compose.local-tls.yml config --quiet`
   - **Expected:** Exit 0, no output
2. Run: `grep -c "mkcert\|local.pem\|local-key.pem\|certs" Caddyfile.local-tls`
   - **Expected:** ≥1 (mkcert cert paths referenced)

---

## Test 10: Infrastructure Files Complete

**Goal:** Verify all expected files exist

1. Run: `test -f Caddyfile.cloud && test -f docker-compose.cloud.yml && test -f .env.cloud.example && echo OK`
   - **Expected:** `OK`
2. Run: `test -f Caddyfile.local-tls && test -f docker-compose.local-tls.yml && echo OK`
   - **Expected:** `OK`
3. Run: `test -f Caddyfile.demo && echo OK`
   - **Expected:** `OK` (renamed from original Caddyfile)
4. Run: `test ! -f Caddyfile && echo OK`
   - **Expected:** `OK` (original Caddyfile no longer exists — renamed to Caddyfile.demo)
5. Run: `grep -q "certs/" .gitignore && echo OK`
   - **Expected:** `OK`

---

## Test 11: Documentation & Guide Index Sync

**Goal:** Verify cloud deployment docs exist and all three guide indexes are in sync

1. Run: `test -f docs/guide/39-cloud-deployment.md && echo OK`
   - **Expected:** `OK`
2. Run: `grep -c "cloud-deployment\|39-cloud-deployment\|Cloud Deployment" docs/guide/README.md`
   - **Expected:** ≥1
3. Run: `grep -c "cloud-deployment\|39-cloud-deployment\|Cloud Deployment" docs/guide/index.html`
   - **Expected:** ≥1
4. Run: `grep -c "cloud-deployment\|39-cloud-deployment\|Cloud Deployment" backend/app/templates/guide.html`
   - **Expected:** ≥1
5. Run: `grep -q "SEMPKM_DOMAIN" docs/guide/appendix-a-environment-variables.md && echo OK`
   - **Expected:** `OK`
6. Run: `grep -q "Deployment Mode\|deployment mode" docs/guide/03-installation-and-setup.md && echo OK`
   - **Expected:** `OK` (setup wizard flow documented)

---

## Edge Cases

### EC-1: Domain with protocol prefix
- POST `/api/setup/configure-instance` with `{"mode": "domain", "domain": "https://example.com"}` should return 422 with protocol prefix error
- Covered by: `test_mode_domain_invalid_domain`

### EC-2: Configure after data exists
- POST `/api/setup/configure-instance` when triplestore has objects should return 409
- Covered by: `test_namespace_guard_409_when_data_exists`

### EC-3: Reconfigure after first config (outside setup mode)
- POST `/api/setup/configure-instance` when config already exists and not in setup mode should return 403
- Covered by: `test_auth_guard_403_when_not_setup_mode_and_config_exists`

### EC-4: Corrupt instance config file
- `load_instance_config()` with malformed JSON returns None, not crash
- Covered by: `test_load_invalid_json_returns_none` and `test_load_invalid_schema_returns_none`
