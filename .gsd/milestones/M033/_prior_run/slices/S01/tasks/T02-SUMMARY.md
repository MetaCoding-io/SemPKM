---
id: T02
parent: S01
milestone: M033
provides:
  - FederationAllowlist service class with CRUD methods
  - API router at /api/federation/endpoints (GET/POST/DELETE)
  - Federation settings UI partial in settings page
  - Allowlist enforcement in SPARQL query execution
  - extract_service_endpoints() utility for SERVICE URI parsing
key_files:
  - backend/app/federation/allowlist.py
  - backend/app/federation/allowlist_router.py
  - backend/app/templates/browser/_federation_settings.html
  - backend/app/templates/browser/settings_page.html
  - backend/app/sparql/router.py
  - backend/tests/test_federation_allowlist.py
  - frontend/static/css/federation.css
key_decisions:
  - Placed allowlist module in existing backend/app/federation/ package alongside ActivityPub federation code (conceptually related; avoids new top-level package)
  - Used InstanceConfig key-value store rather than a separate table for allowlist persistence (consistent with LLM config pattern)
  - extract_service_endpoints() uses regex on raw query text rather than the stripped-strings version — SERVICE URIs inside string literals would be false positives but this is an acceptable tradeoff since users don't typically embed SERVICE clauses in strings
patterns_established:
  - FederationAllowlist CRUD pattern backed by InstanceConfig JSON serialization — reusable for any future key-value config with structured data
  - _enforce_federation_allowlist() async check pattern in SPARQL handlers, called after role check and before execution
observability_surfaces:
  - GET /api/federation/endpoints — returns current allowlist as JSON for any authenticated user
  - INFO-level structured logging on add/remove endpoint operations
  - HTTP 403 with explicit endpoint URL in detail message when non-allowlisted SERVICE is rejected
duration: 25m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Federation endpoint allowlist — API and settings UI

**Added FederationAllowlist service, API router, settings UI, and SPARQL execution enforcement — non-allowlisted SERVICE endpoints are rejected with 403, owners bypass, Wikidata and DBpedia are default entries.**

## What Happened

1. Created `backend/app/federation/allowlist.py` with `FederationAllowlist` class backed by InstanceConfig (key: `federation.allowed_endpoints`, JSON array of `{url, label}` objects). Methods: `get_endpoints()` (seeds Wikidata + DBpedia defaults on first read), `add_endpoint()` (validates URL format, rejects duplicates), `remove_endpoint()`, `is_allowed()`. Also provides `extract_service_endpoints()` utility using regex to parse SERVICE clause endpoint URLs from SPARQL queries.

2. Created `backend/app/federation/allowlist_router.py` with three endpoints at `/api/federation`: GET `/endpoints` (any authenticated user), POST `/endpoints` (owner-only, adds endpoint), DELETE `/endpoints` (owner-only, removes endpoint). Uses Pydantic request models for validation.

3. Created `backend/app/templates/browser/_federation_settings.html` — settings partial showing the endpoint list as a table with URL and label columns, delete buttons (owner-only), and an add form with URL + label inputs. Uses vanilla JS fetch to interact with the API, re-renders the table on mutations, and initialises Lucide icons on dynamic content.

4. Added "Federation" category button with globe icon to `settings_page.html` sidebar (after Authorized Apps). Added the category panel div that includes the partial via Jinja2 `{% include %}`.

5. Wired `_enforce_federation_allowlist()` into both `sparql_get` and `sparql_post` in `router.py` — added `db: AsyncSession = Depends(get_db_session)` to both handlers, calls enforcement after empty-query check and before execution. Owners bypass the check entirely. Non-allowlisted endpoints produce HTTP 403 with the specific rejected URL in the error message.

6. Registered `federation_allowlist_router` in `main.py` right after the existing `federation_router`.

7. Added CSS for the allowlist table, add form, delete button, error messages, and loading state to `frontend/static/css/federation.css`.

8. Wrote 22 unit tests across 3 test classes: `TestFederationAllowlistCRUD` (12 tests), `TestExtractServiceEndpoints` (6 tests), `TestAllowlistEnforcement` (4 tests).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_federation_allowlist.py -v` — all 22 tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` — all 35 existing tests still pass (no regressions)
- Combined slice run: `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_federation_allowlist.py -v` — all 57 pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_federation_allowlist.py -v` | 0 | ✅ pass | 0.38s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py -v` | 0 | ✅ pass | 0.20s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_federation_allowlist.py -v` | 0 | ✅ pass | 0.57s |

## Diagnostics

- **Inspect allowlist:** `GET /api/federation/endpoints` (any authenticated user) returns `{"endpoints": [{"url": "...", "label": "..."}]}`.
- **Check InstanceConfig directly:** Query `SELECT * FROM instance_config WHERE key = 'federation.allowed_endpoints'` for the raw JSON value.
- **Verify enforcement:** Execute a SPARQL query with `SERVICE <https://unlisted.org/sparql> { ... }` as a non-owner user — should get HTTP 403 with `"Federation endpoint not in allowlist: https://unlisted.org/sparql"`.
- **Audit trail:** INFO-level log entries on add/remove operations include the endpoint URL and label.

## Deviations

- Task plan mentioned adding a settings route in `backend/app/browser/settings.py`, but the existing pattern uses `{% include %}` for server-side rendering of partials (not lazy htmx loading). Followed the established pattern — no new route needed in settings.py.
- The DELETE endpoint uses request body `{url}` rather than path parameter `{endpoint_url}` as initially suggested in the plan. This avoids URL-encoding issues with endpoint URLs containing slashes.

## Known Issues

- `test_mirror_service.py` does not exist yet — it's created in T03. The slice-level verification command `pytest tests/test_mirror_service.py` will fail until T03 is complete (expected).

## Files Created/Modified

- `backend/app/federation/allowlist.py` — FederationAllowlist service class with CRUD and extract_service_endpoints() utility
- `backend/app/federation/allowlist_router.py` — API router for GET/POST/DELETE at /api/federation/endpoints
- `backend/app/templates/browser/_federation_settings.html` — settings UI partial with endpoint table and add form
- `backend/app/templates/browser/settings_page.html` — added Federation category button and panel
- `backend/app/sparql/router.py` — added _enforce_federation_allowlist() and wired into sparql_get/sparql_post
- `backend/app/main.py` — registered federation_allowlist_router
- `frontend/static/css/federation.css` — added allowlist table/form/button styles
- `backend/tests/test_federation_allowlist.py` — 22 unit tests for allowlist CRUD, regex extraction, and enforcement
