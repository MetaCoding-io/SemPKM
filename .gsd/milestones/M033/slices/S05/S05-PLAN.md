# S05: Federated SPARQL Console

**Goal:** SPARQL console provides endpoint URL autocomplete inside SERVICE clauses, a pre-execution info banner showing endpoint allowlist status, and an admin page for managing the federation endpoint allowlist.
**Demo:** Type `SERVICE <` in the SPARQL console → autocomplete suggests allowlisted endpoints. Edit a query with SERVICE clauses → info banner appears below editor showing endpoint status. Open Admin → Federation → add/remove endpoints, see changes reflected in the console.

## Must-Haves

- Endpoint URL autocomplete triggers when cursor is inside `SERVICE <...>` in the CodeMirror editor
- Autocomplete suggestions come from the cached mirror allowlist (fetched at console init, not just post-execution)
- Pre-execution info banner detects SERVICE endpoints via debounced editor change listener and shows per-endpoint allowlist status
- `data/.federation-endpoints.json` persists admin-added endpoints, merged with env var entries at load time
- POST/DELETE API endpoints for adding/removing federation endpoints (owner-only)
- GET `/api/sparql/mirror/endpoints` returns merged list (env var ∪ persisted) with source annotation
- Admin federation page follows existing admin card/page patterns
- Admin index page has a Federation card linking to the new page

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_federation_config.py -v` — unit tests for federation config load/save/merge
- `cd backend && .venv/bin/python -m pytest tests/test_federation_endpoints_api.py -v` — API tests for POST/DELETE/GET endpoints
- Manual browser: open SPARQL console, type `SERVICE <`, confirm autocomplete dropdown; add endpoint in admin, verify it appears in console

## Tasks

- [x] **T01: Federation endpoint persistence and admin API** `est:45m`
  - Why: The allowlist is currently env-var only. Need file-based persistence so admins can add/remove endpoints at runtime, plus API routes for CRUD, plus the admin page.
  - Files: `backend/app/sparql/federation_config.py`, `backend/app/sparql/mirror_router.py`, `backend/app/templates/admin/federation.html`, `backend/app/templates/admin/index.html`, `backend/app/admin/router.py`
  - Do: Create `federation_config.py` following `instance_config.py` pattern (Pydantic model, load/save with atomic write, merge with env var). Add POST/DELETE routes to `mirror_router.py` with `require_role("owner")`. Update GET `/endpoints` to return merged list with source field. Create admin federation template following `webhooks.html` layout. Add Federation card to admin index. Add route in admin router.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_federation_config.py tests/test_federation_endpoints_api.py -v`
  - Done when: Admin can add/remove endpoints via the API; GET returns merged env+file list; admin page renders with add form and remove buttons

- [ ] **T02: SERVICE endpoint autocomplete and info banner** `est:30m`
  - Why: The console has SERVICE detection and mirror button post-execution, but no pre-execution feedback or typing assistance. Need autocomplete for endpoint URLs and a live info banner.
  - Files: `frontend/static/js/sparql-console.js`, `frontend/static/css/workspace.css`
  - Do: Add `fetchMirrorAllowlist()` call in `initSparqlConsole()`. Extend `sparqlCompletions()` with SERVICE URI detection branch — when cursor is after `SERVICE <` or `SERVICE SILENT <`, filter allowlist cache entries matching the partial URL and return completions with type `'url'` and detail `'⛓'`. Add debounced `EditorView.updateListener` that runs `detectServiceEndpoints()` on content changes and renders an info bar below the editor showing endpoint URLs with allowlist status indicators. Add CSS for `.sparql-service-info` banner.
  - Verify: Manual browser — type `SERVICE <` in console, see autocomplete; type a full SERVICE query, see info banner appear below editor
  - Done when: Autocomplete suggests allowlisted endpoints when typing inside SERVICE URIs; info banner shows per-endpoint status within ~500ms of typing

- [ ] **T03: Unit and API tests for federation features** `est:30m`
  - Why: Verify the persistence layer and API contract with automated tests that run in CI.
  - Files: `backend/tests/test_federation_config.py`, `backend/tests/test_federation_endpoints_api.py`
  - Do: Write unit tests for `federation_config.py` — load/save round-trip, merge with env var, duplicate handling, empty file, malformed file. Write API tests for POST/DELETE/GET endpoints — add endpoint, verify it appears in GET, delete it, verify it's gone; test owner-only access control; test env var entries are non-removable.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_federation_config.py tests/test_federation_endpoints_api.py -v`
  - Done when: All tests pass; coverage includes happy path, edge cases (empty/duplicate/malformed), and access control

## Files Likely Touched

- `backend/app/sparql/federation_config.py` (new)
- `backend/app/sparql/mirror_router.py`
- `backend/app/sparql/mirror.py`
- `backend/app/templates/admin/federation.html` (new)
- `backend/app/templates/admin/index.html`
- `backend/app/admin/router.py`
- `frontend/static/js/sparql-console.js`
- `frontend/static/css/workspace.css`
- `backend/tests/test_federation_config.py` (new)
- `backend/tests/test_federation_endpoints_api.py` (new)

## Observability / Diagnostics

- **Log signals:** `federation_config.py` logs at INFO for add/remove/save operations, WARNING for load failures. `mirror_router.py` logs at INFO for API add/remove with user email. `admin/router.py` logs at INFO/WARNING for admin add/remove.
- **Inspection surface:** `GET /api/sparql/mirror/endpoints` returns the full merged endpoint list with source annotation (`"env"` or `"admin"`) and `removable` flag — this is the primary diagnostic endpoint for endpoint configuration state.
- **Failure visibility:** Malformed `data/.federation-endpoints.json` gracefully degrades to empty list (logged at WARNING). Invalid URL format returns 400 with descriptive detail. Env-var removal attempt returns 409 with explanation.
- **Persisted state:** `data/.federation-endpoints.json` is the durable artifact — readable as plain JSON for manual inspection or recovery.
