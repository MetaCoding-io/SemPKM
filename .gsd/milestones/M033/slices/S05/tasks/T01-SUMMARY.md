---
id: T01
parent: S05
milestone: M033
provides:
  - Federation endpoint file-based persistence (load/save/merge)
  - POST/DELETE/GET API routes for federation endpoint CRUD
  - Admin federation page with add/remove UI
  - Admin index Federation card
  - validate_endpoint() checks merged list (env + admin)
key_files:
  - backend/app/sparql/federation_config.py
  - backend/app/sparql/mirror_router.py
  - backend/app/sparql/mirror.py
  - backend/app/templates/admin/federation.html
  - backend/app/templates/admin/index.html
  - backend/app/admin/router.py
  - backend/tests/test_federation_config.py
  - backend/tests/test_federation_endpoints_api.py
key_decisions:
  - Used unittest.mock.patch to mock Pydantic Settings in tests (frozen model prevents monkeypatch.setattr)
  - Admin htmx DELETE uses query param ?url= instead of path param to avoid double-encoding issues
patterns_established:
  - _patch_env_endpoints() helper for mocking frozen Pydantic Settings.get_allowed_endpoints() in tests
observability_surfaces:
  - GET /api/sparql/mirror/endpoints returns merged list with source and removable annotations
  - federation_config.py logs INFO on add/remove/save, WARNING on load failures
  - data/.federation-endpoints.json is the durable persisted state file
duration: 35m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Federation endpoint persistence and admin API

**Created federation_config.py persistence layer, POST/DELETE/GET API routes, and admin federation management page with endpoint CRUD**

## What Happened

Built the complete federation endpoint persistence layer following the `instance_config.py` atomic-write pattern:

1. **`federation_config.py`** — Pydantic model `FederationEndpoints` with `endpoints: list[str]` and `updated_at: str`. Functions: `load_federation_endpoints()` (never raises, returns empty on failure), `save_federation_endpoints()` (atomic via temp file + `os.replace()`), `get_merged_endpoints()` (merges env var entries with persisted, env wins on dedup), `add_endpoint()`, `remove_endpoint()` (raises ValueError for env entries or missing entries).

2. **Updated `mirror_router.py`** — Added `POST /api/sparql/mirror/endpoints` (owner-only, validates http/https URL format), `DELETE /api/sparql/mirror/endpoints/{encoded_url}` (owner-only, refuses env entries with 409). Updated `GET /api/sparql/mirror/endpoints` to return merged list with `{url, source, removable}` shape.

3. **Updated `mirror.py`** — `validate_endpoint()` now checks the merged endpoint list (env + admin) instead of only the env var.

4. **Created `admin/federation.html`** — Extends base.html, shows add form with URL input and htmx POST, endpoint list table with source badges and remove buttons. Follows webhooks.html layout pattern.

5. **Updated admin portal** — Added Federation card to `admin/index.html`. Added GET/POST/DELETE routes to `admin/router.py` for the federation management page.

6. **Tests** — 18 unit tests in `test_federation_config.py` (load, save, round-trip, merge, add, remove, edge cases) and 6 API tests in `test_federation_endpoints_api.py` (GET, POST, DELETE, URL validation, env protection).

## Verification

Both test suites pass: 24/24 tests green.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_federation_config.py -v` | 0 | ✅ pass | 0.6s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_federation_endpoints_api.py -v` | 0 | ✅ pass | 0.6s |

## Diagnostics

- **Merged endpoint list:** `GET /api/sparql/mirror/endpoints` returns `{"endpoints": [...], "allowlist_configured": bool}` with each entry having `url`, `source` ("env"/"admin"), and `removable` fields.
- **Persisted state:** Inspect `data/.federation-endpoints.json` directly — it's plain JSON with `endpoints` array and `updated_at` timestamp.
- **Log signals:** `federation_config` logger emits INFO on successful add/remove/save, WARNING on load failures. `mirror_router` and `admin.router` log endpoint changes with user email.

## Deviations

- Admin DELETE route uses query parameter `?url=` instead of URL-encoded path parameter to avoid double-encoding issues with htmx `hx-delete` and URL-in-URL encoding.
- Tests use `unittest.mock.patch` with a mock settings object instead of `monkeypatch.setattr` because Pydantic Settings (v2) is a frozen model that rejects attribute assignment on methods.

## Known Issues

None.

## Files Created/Modified

- `backend/app/sparql/federation_config.py` — new federation endpoint persistence module (load/save/merge/add/remove)
- `backend/app/sparql/mirror_router.py` — added POST/DELETE routes, updated GET to use merged endpoints
- `backend/app/sparql/mirror.py` — updated validate_endpoint() to check merged list
- `backend/app/templates/admin/federation.html` — new admin federation endpoint management page
- `backend/app/templates/admin/index.html` — added Federation card to admin index
- `backend/app/admin/router.py` — added federation GET/POST/DELETE admin routes
- `backend/tests/test_federation_config.py` — 18 unit tests for persistence layer
- `backend/tests/test_federation_endpoints_api.py` — 6 API tests for endpoint routes
- `.gsd/milestones/M033/slices/S05/S05-PLAN.md` — added Observability section
