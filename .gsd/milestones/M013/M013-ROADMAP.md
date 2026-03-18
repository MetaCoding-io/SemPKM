# M013: API Surface for External Clients

**Vision:** Expose a clean JSON API layer for external clients (browser extension, mobile apps, third-party integrations) to discover instance capabilities, query available types with their SHACL shapes, and find related objects by context.

## Success Criteria

- `curl -H "Authorization: Bearer <token>" http://localhost:3000/.well-known/sempkm` returns JSON with version string, endpoint URLs, and capability list — and the same works with a session cookie
- `curl http://localhost:3000/api/types` returns every type from all installed Mental Models with labels, Lucide icon names, and source model attribution
- `curl http://localhost:3000/api/shapes/urn:sempkm:model:basic-pkm:Note` returns structured JSON with property shapes matching the fields in the existing SHACL form editor (same paths, names, constraints, groups, helptext, ordering)
- `POST /api/context-query` with `{"url": "https://example.com"}` returns objects whose properties contain that URL, and with `{"keywords": "project"}` returns FTS-matched objects with relevance scores
- All four endpoints return proper CORS headers (`Access-Control-Allow-Origin: *`) so browser extensions can call them directly
- nginx forwards `Authorization` headers on the `/api/` proxy block so Bearer tokens reach FastAPI
- All four endpoints have unit tests exercising success paths, error cases (unknown type, no matches), and auth variations
- User guide documents the API surface for extension/integration developers

## Key Risks / Unknowns

- **Dual-auth dependency wiring** — `get_current_user` only checks session cookies. `AuthService.verify_api_token()` exists but has no FastAPI dependency. Building a combined dependency that accepts either session cookie OR Bearer token is the prerequisite for all four endpoints. If this wiring is wrong, no endpoint works for external clients.
- **nginx Authorization header blocking** — The `/api/` proxy block doesn't forward `Authorization` headers (only `/dav/` does). Without this one-line fix, Bearer tokens never reach FastAPI.
- **Shape JSON serialization fidelity** — PropertyShape/PropertyGroup/NodeShapeForm are plain dataclasses. `dataclasses.asdict()` should work cleanly, but edge cases (None fields, empty lists, nested groups) need verification against what the form generator actually uses.

## Proof Strategy

- **Dual-auth + nginx** → retire in S01 by shipping `/.well-known/sempkm` with both Bearer token and session cookie auth working end-to-end through Docker Compose. This proves the entire auth + proxy pipeline before any data endpoint depends on it.
- **Shape serialization** → retire in S02 by comparing JSON output of `/api/shapes/{type_iri}` against the form fields the SHACL form generator actually renders for the same type.

## Verification Classes

- Contract verification: pytest unit tests for all endpoints (auth dependency, response schemas, edge cases), run via `python -m pytest tests/test_api_surface.py -v`
- Integration verification: curl commands against running Docker Compose stack exercising real triplestore data, real auth tokens, real SHACL shapes
- Operational verification: nginx CORS headers and Authorization forwarding verified via browser DevTools network tab and curl `-v` output
- UAT / human verification: none — all criteria are machine-verifiable

## Milestone Definition of Done

This milestone is complete only when all are true:

- All three slice deliverables are complete and individually verified
- Dual-auth dependency is wired and exercised by all four endpoints
- nginx config forwards Authorization headers and adds CORS headers on `/api/` routes
- All endpoints return well-structured JSON matching documented schemas
- Unit tests cover success paths, error paths, and both auth modes
- curl verification against live Docker stack confirms all five success criteria
- User guide chapter documents all four endpoints with request/response examples
- E2E Playwright test exercises at least the well-known and types endpoints through the real stack

## Requirement Coverage

- Covers: API-01 (well-known discovery), API-02 (types endpoint), API-03 (shapes endpoint), API-04 (context-query endpoint) — all new requirements created by this milestone
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — all Active requirements not in this milestone's scope (APP-01–14, RSS-01–08) belong to M009/M010

## Slices

- [x] **S01: Dual-Auth, CORS, nginx fix, and Well-Known Endpoint** `risk:high` `depends:[]`
  > After this: `curl -H "Authorization: Bearer <token>" localhost:3000/.well-known/sempkm` returns JSON discovery document through Docker Compose, proving Bearer auth works end-to-end through nginx → FastAPI. Session cookie auth works on the same endpoint.
- [ ] **S02: Types and Shapes JSON Endpoints** `risk:medium` `depends:[S01]`
  > After this: `curl localhost:3000/api/types` returns all installed model types with labels/icons/models, and `curl localhost:3000/api/shapes/<type_iri>` returns SHACL property shapes as structured JSON matching the form editor's fields.
- [ ] **S03: Context-Query, E2E Tests, and User Guide** `risk:low` `depends:[S01,S02]`
  > After this: `POST /api/context-query` finds related objects by URL and keywords. Playwright E2E tests exercise all four endpoints. User guide documents the full API surface.

## Boundary Map

### S01 → S02

Produces:
- `get_current_user_or_api` FastAPI dependency that resolves a `User` from either session cookie or Bearer token — all S02/S03 endpoints depend on this
- nginx `/api/` block forwarding `Authorization` header and returning CORS headers
- `/.well-known/sempkm` endpoint as proof that the auth + proxy pipeline works
- `backend/app/api/` module directory with router wired into `main.py`

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `GET /api/types` returning structured type metadata (IRI, label, icon, model name)
- `GET /api/shapes/{type_iri}` returning SHACL property shapes as JSON
- Pydantic response models for types and shapes that S03's context-query can reuse for result enrichment

Consumes:
- `get_current_user_or_api` dependency from S01
- CORS + nginx config from S01

### S01,S02 → S03

Produces:
- `POST /api/context-query` endpoint with URL matching and FTS keyword search
- E2E Playwright test exercising all four endpoints
- User guide chapter documenting the API surface

Consumes:
- Auth dependency, CORS headers, nginx config from S01
- Type/shape response models from S02 (for enriching context-query results with type labels)
