---
id: M013
provides:
  - GET /.well-known/sempkm discovery endpoint with version, endpoints, auth methods, and capabilities
  - GET /api/types endpoint returning all installed model types with labels, Lucide icons, icon colors, and model attribution
  - GET /api/shapes/{type_iri} endpoint returning SHACL property shapes as structured JSON (properties, groups, constraints, helptext, ordering)
  - POST /api/context-query endpoint with URL matching (SPARQL FILTER) + keyword/title matching (FTS/LuceneSail), deduplication, and type/label enrichment
  - get_current_user_or_api dual-auth FastAPI dependency (session cookie + Bearer API token)
  - _extract_bearer_token helper for case-insensitive Bearer scheme parsing
  - nginx Authorization header forwarding and CORS headers on /api/ and /.well-known/ routes
  - Pydantic response models (InstanceInfo, TypeInfo, TypesResponse, PropertyShapeInfo, PropertyGroupInfo, ShapeResponse, ContextQueryRequest, ContextResult, ContextQueryResponse) providing OpenAPI documentation
  - _extract_model_id helper parsing model_id from type IRI convention
  - _sparql_escape_str helper for SPARQL injection prevention in URL matching
  - backend/app/api/ module directory with well_known_router and api_surface_router
  - User guide Chapter 31 documenting the full API surface
  - 3 glossary entries (API Surface, Context Query, Instance Discovery)
key_decisions:
  - D159 — Cookie auth tried first, Bearer as fallback; existing get_current_user unchanged
  - D160 — Shape serialization via dataclasses.asdict() to Pydantic models (no ShapesService refactor)
  - D161 — CORS Access-Control-Allow-Origin: * on /api/ and /.well-known/ via nginx
  - D162 — Context-query v1 searches literal values only (no edge traversal)
  - D163 — _is_html_route() extended to exclude /.well-known/ paths so 401 returns JSON
  - D164 — IconService created ad-hoc in endpoint handler matching codebase pattern
patterns_established:
  - Dual-auth dependency pattern (get_current_user_or_api) for external-client API endpoints
  - Authorization forwarding pattern consistent across /api/, /dav/, and /.well-known/ nginx blocks
  - CORS header block pattern (Origin/Headers/Methods with `always` flag) for reuse on future proxy blocks
  - Shape serialization via dataclass → asdict() → Pydantic model via **kwargs unpacking
  - Context-query deduplication via dict[iri, match_type] with first-match-wins precedence
  - Graceful degradation: each query stage catches exceptions independently and logs at WARNING
  - API-only E2E tests using ownerRequest fixture for authenticated HTTP calls without browser navigation
  - Chain tests (shapes test fetches real type IRI from types endpoint) to avoid hardcoded seed-data dependencies
  - _is_html_route exclusion pattern for JSON API paths outside /api/
observability_surfaces:
  - DEBUG log "dual-auth resolved via session cookie" or "dual-auth resolved via Bearer token"
  - HTTP 401 detail field distinguishes failure mode — "Not authenticated" vs "Invalid or expired API token" vs "Invalid or expired session"
  - GET /api/types response serves as runtime inventory of all loaded models and types
  - GET /api/shapes/{type_iri} returns full SHACL property shapes for runtime inspection
  - POST /api/context-query response includes match_type per result and total count
  - Empty body on context-query → 400 with "At least one of url, title, or keywords is required"
  - 404 with structured detail "No shape found for type: <iri>" on unknown types
  - curl -v -X OPTIONS /api/ shows CORS headers and 204 — absence means nginx config error
requirement_outcomes:
  - id: API-01
    from_status: active
    to_status: validated
    proof: 10 unit tests verify schema, content-type, auth enforcement, and field types. E2E test confirms through Docker stack. Docker curl confirms 401 JSON for unauthenticated requests.
  - id: API-02
    from_status: active
    to_status: validated
    proof: 8 unit tests verify types JSON array with icons, model attribution, auth, and empty state. E2E test confirms real types returned through Docker stack.
  - id: API-03
    from_status: active
    to_status: validated
    proof: 11 unit tests verify shapes JSON with constraints, groups, helptext, target_class, 404, and auth. E2E test chains from real type IRI through Docker stack.
  - id: API-04
    from_status: active
    to_status: validated
    proof: 13 context-query unit tests + 5 SPARQL escape tests + 2 E2E tests verify URL match, keyword match, deduplication, type enrichment, graceful degradation, and auth enforcement.
  - id: API-05
    from_status: active
    to_status: validated
    proof: 8 bearer extraction tests + 7 dual-auth integration tests verify both cookie and bearer paths with distinct 401 detail messages.
  - id: API-06
    from_status: active
    to_status: validated
    proof: nginx.conf has Access-Control-Allow-Origin:* with always flag on /api/ and /.well-known/. OPTIONS preflight returns 204. Docker curl verified.
  - id: API-07
    from_status: active
    to_status: validated
    proof: nginx.conf has proxy_set_header Authorization $http_authorization on /api/ block matching /dav/ pattern. nginx -t validates config syntax.
  - id: API-08
    from_status: active
    to_status: validated
    proof: docs/guide/31-api-surface.md documents all four endpoints with curl examples, JSON responses, auth methods, CORS config, and error responses. README TOC updated. 3 glossary entries added.
duration: 153m
verification_result: passed
completed_at: 2026-03-17
---

# M013: API Surface for External Clients

**Shipped four JSON API endpoints for external clients — instance discovery, type inventory, SHACL shape serialization, and context-query — with dual-auth (cookie + Bearer token), CORS headers, 62 unit tests, 7 E2E Playwright tests, and full user guide documentation**

## What Happened

Three slices delivered a complete JSON API layer enabling browser extensions, mobile apps, and third-party integrations to interact with SemPKM programmatically.

**S01 — Auth + CORS + Discovery (53m):** Built the foundational auth and proxy infrastructure. Created `get_current_user_or_api` in `backend/app/auth/dependencies.py` — a FastAPI dependency that tries session cookie first, falls back to Bearer token via `AuthService.verify_api_token()`, and returns distinct 401 messages for each failure mode. Updated `frontend/nginx.conf` to forward Authorization headers and add CORS headers (`Access-Control-Allow-Origin: *`) on both `/api/` and `/.well-known/sempkm` routes, with OPTIONS preflight returning 204. Shipped `GET /.well-known/sempkm` as the first endpoint — an instance discovery document with version, endpoint URLs, auth methods, and capabilities. Discovered and fixed that `_is_html_route()` in `main.py` was converting 401s to 302 login redirects for `/.well-known/` paths (D163). Created the `backend/app/api/` module with `well_known_router` and empty `api_surface_router` wired into `main.py`. 25 unit tests covered all auth paths and the discovery endpoint.

**S02 — Types + Shapes (45m):** Added two data endpoints to `api_surface_router`. `GET /api/types` merges data from three services — ShapesService (type IRIs + labels), IconService (Lucide icon names + colors), and ModelService (model name lookup) — returning a `TypesResponse` with `TypeInfo` Pydantic models. `GET /api/shapes/{type_iri:path}` calls `ShapesService.get_form_for_type()` and converts the `NodeShapeForm` dataclass to structured JSON via `dataclasses.asdict()` → Pydantic models, retiring the key risk of shape serialization fidelity. Returns 404 for unknown types. Fixed a runtime 500 where `IconService` was expected on `app.state` but the codebase creates it ad-hoc everywhere (D164). 19 tests added covering both endpoints.

**S03 — Context-Query + E2E + Docs (55m):** Completed the API surface with `POST /api/context-query`, which accepts `{url, title, keywords}` and runs two matching strategies: URL matching via SPARQL `FILTER(STR(?val) = "...")` and keyword/title matching via `SearchService.search()` (LuceneSail FTS). Results are deduplicated (URL matches take precedence), then enriched with labels and types. Each enrichment stage catches exceptions independently — the endpoint degrades gracefully rather than returning 500. Created 7 Playwright E2E tests exercising all four endpoints through the full Docker Compose stack. Wrote Chapter 31 of the user guide with request/response examples, authentication guidance, CORS documentation, and error handling. Added 3 glossary entries. 18 context-query tests (13 endpoint + 5 SPARQL escape helper) brought the total to 62.

## Cross-Slice Verification

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | `curl /.well-known/sempkm` returns JSON with version, endpoints, capabilities | ✅ | 10 unit tests + E2E test `GET /.well-known/sempkm returns discovery document` |
| 2 | `curl /api/types` returns all types with labels, icons, model attribution | ✅ | 8 unit tests + E2E test `GET /api/types returns array with iri and label` |
| 3 | `curl /api/shapes/{type_iri}` returns SHACL property shapes matching form editor fields | ✅ | 11 unit tests (constraints, groups, helptext, ordering) + E2E chain test from real type IRI |
| 4 | `POST /api/context-query` with URL/keywords returns matching objects | ✅ | 13 unit tests + E2E tests for keyword match and validation |
| 5 | All endpoints return CORS headers (`Access-Control-Allow-Origin: *`) | ✅ | nginx.conf lines 44-47, 66-68, 86-88 with `always` flag |
| 6 | nginx forwards Authorization headers on `/api/` | ✅ | nginx.conf line 62: `proxy_set_header Authorization $http_authorization` |
| 7 | All endpoints have unit tests (success, error, auth) | ✅ | 62 tests in `test_api_surface.py` — all passing |
| 8 | User guide documents the API surface | ✅ | `docs/guide/31-api-surface.md` + README TOC + 3 glossary entries |

**Definition of done checklist:**
- ✅ All three slices complete with individual summaries
- ✅ Dual-auth dependency wired and exercised by all four endpoints
- ✅ nginx config forwards Authorization headers and adds CORS headers on `/api/` routes
- ✅ All endpoints return well-structured JSON matching documented schemas
- ✅ 62 unit tests cover success paths, error paths, and both auth modes
- ✅ 7 E2E Playwright tests exercise endpoints through real Docker stack
- ✅ User guide Chapter 31 documents all four endpoints with request/response examples
- ✅ E2E tests exercise well-known and types endpoints (plus shapes, context-query, and auth gate)

## Requirement Changes

- API-01: active → validated — 10 unit tests + E2E test verify well-known JSON schema, auth, and field types
- API-02: active → validated — 8 unit tests + E2E test verify types JSON with icons and model attribution
- API-03: active → validated — 11 unit tests + E2E chain test verify shapes JSON with constraints, groups, helptext
- API-04: active → validated — 13 endpoint tests + 5 SPARQL escape tests + 2 E2E tests verify context-query
- API-05: active → validated — 15 unit tests verify dual-auth dependency with both cookie and bearer paths
- API-06: active → validated — nginx.conf CORS headers verified on /api/ and /.well-known/ with OPTIONS 204
- API-07: active → validated — nginx.conf Authorization forwarding verified matching /dav/ pattern
- API-08: active → validated — Chapter 31 user guide with curl examples, auth docs, CORS docs, 3 glossary entries

## Forward Intelligence

### What the next milestone should know
- The API surface (`/.well-known/sempkm`, `/api/types`, `/api/shapes/{type_iri}`, `/api/context-query`) is the integration contract for the browser extension (M014/M015). All four endpoints require authentication (cookie or Bearer token) and return JSON with CORS headers via nginx.
- `get_current_user_or_api` is the standard dependency for all external-client API endpoints. Import from `app.auth.dependencies`. Cookie auth is tried first, then Bearer token.
- The `api_surface_router` (prefix `/api`) is already wired into `main.py`. New endpoints just need `@api_surface_router.get(...)` or `.post(...)` decorators.
- Docker stack port mapping is `3901:80` in the test environment, not `3000:80` as some docs suggest. Use `localhost:3901` for curl verification.
- The InstanceInfo discovery document lists endpoints that don't exist yet (`/api/sparql`, `/api/commands`). These are placeholders for future milestones.
- Pydantic response models provide OpenAPI docs at `/docs` — useful for extension developers and the user guide.

### What's fragile
- `_is_html_route()` in `main.py` — any new JSON API prefix outside `/api/` must be added to the exclusion list or 401s will become 302 redirects. Currently excludes `/api/` and `/.well-known/`.
- CORS headers are in nginx, not FastAPI middleware — if FastAPI also adds CORSMiddleware, headers may duplicate or conflict.
- IconService ad-hoc creation from `/app/models` path — if the models directory structure changes, icon lookup breaks silently (returns None).
- `_extract_model_id` regex depends on `urn:sempkm:model:{id}:` IRI convention. User-created types have different IRI patterns and return `model_id: null`.
- Context-query SPARQL URL matching uses `_sparql_escape_str()` for injection prevention. While tested (5 tests), extremely long URLs or unusual Unicode could cause SPARQL engine issues.
- FTS keyword matching depends on `search_service` on `app.state` — if SearchService initialization fails at startup, the keyword path silently degrades.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` — 62 tests in ~1.4s. Single source of truth for all endpoint correctness.
- `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium` — 7 E2E tests proving full stack (nginx → FastAPI → triplestore) works with real auth.
- `curl -v -X OPTIONS http://localhost:3901/api/types -H "Origin: chrome-extension://abc" -H "Access-Control-Request-Method: GET"` — verifies CORS pipeline through nginx.
- `docker exec sempkm-frontend-1 nginx -t` — validates nginx config syntax.

### What assumptions changed
- **Assumed:** `/.well-known/` paths would naturally return JSON errors on 401. **Actual:** `_is_html_route()` converted 401s to 302 login redirects. Required a code fix (D163).
- **Assumed:** IconService would be on `app.state`. **Actual:** The codebase creates it ad-hoc everywhere. Fixed by following the established pattern (D164).
- **Assumed:** Shape serialization might have edge cases with nested dataclasses. **Actual:** `dataclasses.asdict()` + Pydantic handles all fields cleanly including None, empty lists, and nested groups (D160 risk retired).
- **Assumed:** Tests would be concentrated in final tasks. **Actual:** Tests were distributed across implementation tasks for immediate verification, with final tasks doing gap-fill.

## Files Created/Modified

- `backend/app/auth/dependencies.py` — added `_extract_bearer_token` helper and `get_current_user_or_api` dual-auth dependency
- `backend/app/api/__init__.py` — new module init
- `backend/app/api/router.py` — well_known_router, api_surface_router, all four endpoints, 9 Pydantic models, helper functions
- `backend/app/main.py` — import and register both routers; fix _is_html_route to exclude /.well-known/ paths
- `backend/app/config.py` — update app_version default from "0.1.0" to "2.6.0"
- `frontend/nginx.conf` — Authorization forwarding + CORS headers on /api/; new /.well-known/sempkm proxy block; OPTIONS preflight handling
- `backend/tests/test_api_surface.py` — 62 tests covering dual-auth, well-known, types, shapes, context-query, and SPARQL escape
- `e2e/tests/30-api-surface/api-surface.spec.ts` — 7 E2E tests for all M013 API endpoints
- `docs/guide/31-api-surface.md` — Chapter 31 documenting the full API surface
- `docs/guide/README.md` — Added Chapter 31 to table of contents
- `docs/guide/30-personas.md` — Updated navigation footer to link to Chapter 31
- `docs/guide/appendix-d-glossary.md` — Added API Surface, Context Query, Instance Discovery entries
