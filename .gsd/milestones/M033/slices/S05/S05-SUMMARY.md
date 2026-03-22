---
id: S05
parent: M033
milestone: M033
provides:
  - Federation endpoint file-based persistence (load/save/merge with env var)
  - POST/DELETE/GET API routes for federation endpoint CRUD (owner-only)
  - Admin federation management page with add/remove UI
  - SERVICE URI autocomplete in SPARQL console editor
  - Debounced info banner showing per-endpoint allowlist status
  - Allowlist cache warm-up at console init
  - 65 tests (18 config, 13 API, 6 mirror service, plus existing)
requires: []
affects: []
key_files:
  - backend/app/sparql/federation_config.py
  - backend/app/sparql/mirror_router.py
  - backend/app/sparql/mirror.py
  - backend/app/templates/admin/federation.html
  - backend/app/templates/admin/index.html
  - frontend/static/js/sparql-console.js
  - frontend/static/css/workspace.css
  - backend/tests/test_federation_config.py
  - backend/tests/test_federation_endpoints_api.py
  - backend/tests/test_mirror_service.py
key_decisions: []
patterns_established:
  - "Federation config: file persistence (data/.federation-endpoints.json) merged with env var entries at load time"
  - "Source annotation on endpoints: 'env' vs 'admin' — env entries are not removable"
  - "SERVICE URI autocomplete: detect cursor inside SERVICE <...>, filter allowlist by partial URL"
  - "Debounced editor change listener for pre-execution info banner"
observability_surfaces:
  - "GET /api/sparql/mirror/endpoints returns merged list with source field"
  - "Admin federation page shows env vs admin source labels"
  - "Console info banner shows per-endpoint ✓/⚠ status indicators"
  - "POST/DELETE return 403 for non-owner users"
drill_down_paths:
  - .gsd/milestones/M033/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M033/slices/S05/tasks/T02-SUMMARY.md
  - .gsd/milestones/M033/slices/S05/tasks/T03-SUMMARY.md
duration: 75m
verification_result: passed
completed_at: 2026-03-22
---

# S05: Federated SPARQL Console

**Added federation endpoint persistence with admin CRUD, SERVICE URI autocomplete, and pre-execution info banner — 65 tests passing**

## What Happened

T01 built the backend: `federation_config.py` with Pydantic model, atomic file persistence, and merge with env var entries. POST/DELETE routes on `mirror_router.py` (owner-only). Updated GET `/endpoints` to return merged list with source annotation. Admin federation page following existing card/page patterns. Federation card on admin index.

T02 built the frontend: allowlist cache warm-up at console init (was previously only post-execution). SERVICE URI autocomplete in CodeMirror — detects cursor inside `SERVICE <...>` and filters allowlist by partial URL. Debounced editor change listener rendering an info banner below the editor showing per-endpoint allowlist status (✓ allowed / ⚠ not in allowlist). Updated `isEndpointAllowed()` to handle the new object format from T01.

T03 expanded the test suite to 65 tests: 18 config persistence tests, 13 API integration tests (rewritten for source annotation format), 6 fixed mirror service tests (adapted for T01's validate_endpoint refactor).

## Verification

All 65 tests pass. Manual verification: typing `SERVICE <` in console shows autocomplete, info banner appears with endpoint status, admin page CRUD works, env var entries show as non-removable.

## Deviations

- T03 required fixing 6 existing mirror service tests broken by T01's validate_endpoint refactor — this was expected integration work.

## Known Limitations

- Autocomplete only triggers inside `SERVICE <...>` pattern — not for `SERVICE SILENT <...>` (could be extended).

## Follow-ups

None.

## Files Created/Modified

- `backend/app/sparql/federation_config.py` — Federation endpoint persistence model
- `backend/app/sparql/mirror_router.py` — POST/DELETE/GET API routes
- `backend/app/sparql/mirror.py` — validate_endpoint updated for merged list
- `backend/app/templates/admin/federation.html` — Admin federation management page
- `backend/app/templates/admin/index.html` — Federation card added
- `backend/app/admin/router.py` — Federation page route
- `frontend/static/js/sparql-console.js` — SERVICE autocomplete, info banner, allowlist cache
- `frontend/static/css/workspace.css` — .sparql-service-info banner styles
- `backend/tests/test_federation_config.py` — 18 config tests
- `backend/tests/test_federation_endpoints_api.py` — 13 API tests
- `backend/tests/test_mirror_service.py` — 6 fixed mirror tests

## Forward Intelligence

### What the next slice should know
- Federation endpoints are persisted at `data/.federation-endpoints.json` and merged with `SPARQL_MIRROR_ENDPOINTS` env var at load time.
- The GET endpoint returns `{url, source, removable}` objects, not plain strings.

### What's fragile
- The `isEndpointAllowed()` function was updated to handle both string and object formats — if the API response shape changes again, the console autocomplete and info banner will break.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_federation_config.py tests/test_federation_endpoints_api.py -v` for backend tests.
- `GET /api/sparql/mirror/endpoints` shows the current merged allowlist with sources.

### What assumptions changed
- None.
