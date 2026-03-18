---
verdict: pass
remediation_round: 0
---

# Milestone Validation: M013 — API Surface for External Clients

## Success Criteria Checklist

- [x] **Well-known endpoint with dual auth** — `GET /.well-known/sempkm` returns JSON with version ("2.6.0"), endpoint URLs, auth methods, and capabilities. Bearer token and session cookie auth both work. S01 delivers 25 unit tests + Docker curl verification. `_is_html_route()` fix (D163) ensures 401 returns JSON, not 302.
- [x] **Types endpoint** — `GET /api/types` returns every type from installed models with labels, Lucide icon names, icon colors, model_id, and model_name. S02 delivers 8 unit tests. IconService created ad-hoc per codebase pattern (D164).
- [x] **Shapes endpoint** — `GET /api/shapes/{type_iri}` returns structured JSON with property shapes matching the SHACL form editor fields (paths, names, constraints, groups, helptext, ordering). S02 delivers 11 unit tests including constraint round-trip. Key risk (serialization fidelity) retired via `dataclasses.asdict()` → Pydantic (D160).
- [x] **Context-query endpoint** — `POST /api/context-query` with `{"url": "..."}` returns objects whose properties contain that URL. With `{"keywords": "..."}` returns FTS-matched objects. Results deduplicated (URL matches take precedence). S03 delivers 13 endpoint tests + 5 SPARQL escape tests. Note: relevance scores not surfaced in v1 (D162 — by design for v1, edge traversal and scoring deferred).
- [x] **CORS headers** — All four endpoints return `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Headers: Authorization, Content-Type, Accept`, `Access-Control-Allow-Methods: GET, POST, OPTIONS`. OPTIONS preflight returns 204. nginx `always` flag ensures headers on error responses. Docker curl verified.
- [x] **nginx Authorization forwarding** — `/api/` proxy block has `proxy_set_header Authorization $http_authorization` matching the `/dav/` pattern. Docker curl confirms Bearer tokens reach FastAPI.
- [x] **Unit tests** — 63 tests in `test_api_surface.py` covering success paths, error cases (unknown type → 404, no matches → empty, invalid body → 400), and auth variations (cookie, bearer, unauthenticated → 401, invalid bearer → 401). Exceeds plan's "all four endpoints" requirement.
- [x] **User guide** — `docs/guide/31-api-surface.md` documents all four endpoints with curl examples, JSON response examples, field descriptions, auth methods, CORS guidance, and error responses. README TOC updated. 3 glossary entries (API Surface, Context Query, Instance Discovery) added.

## Milestone Definition of Done Checklist

- [x] All three slice deliverables complete and individually verified
- [x] Dual-auth dependency wired and exercised by all four endpoints
- [x] nginx config forwards Authorization headers and adds CORS headers on `/api/` routes
- [x] All endpoints return well-structured JSON matching documented schemas (Pydantic response models → OpenAPI)
- [x] Unit tests cover success paths, error paths, and both auth modes (63 tests)
- [x] curl verification against live Docker stack confirms success criteria (S01 verified; S03 E2E tests exercise full stack)
- [x] User guide chapter documents all four endpoints with request/response examples
- [x] E2E Playwright test exercises well-known, types, shapes, and context-query endpoints through real stack (7 tests)

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | Dual-auth dependency, CORS, nginx fix, well-known endpoint | `get_current_user_or_api` dependency (cookie-first, Bearer fallback), `_extract_bearer_token` helper, nginx `/api/` + `/.well-known/sempkm` blocks with Authorization forwarding + CORS, `GET /.well-known/sempkm` with InstanceInfo model, 25 unit tests, `_is_html_route` fix, `api_surface_router` wired empty | **pass** |
| S02 | Types and Shapes JSON endpoints | `GET /api/types` with TypeInfo/TypesResponse models merging ShapesService+IconService+ModelService, `GET /api/shapes/{type_iri:path}` with PropertyShapeInfo/PropertyGroupInfo/ShapeResponse models via dataclasses.asdict(), 19 unit tests, IconService runtime fix (D164) | **pass** |
| S03 | Context-query, E2E tests, user guide | `POST /api/context-query` with URL + keyword matching + dedup + type/label enrichment, 18 unit tests (13 endpoint + 5 SPARQL escape), 7 E2E Playwright tests, Chapter 31 user guide, 3 glossary entries | **pass** |

## Cross-Slice Integration

**S01 → S02 boundary:** S01 produces `get_current_user_or_api`, CORS headers, nginx config, and `api_surface_router` wired in `main.py`. S02 consumes all of these — adds endpoints to the same router, uses the same auth dependency. ✅ Aligned.

**S02 → S03 boundary:** S02 produces types and shapes endpoints + Pydantic response models. S03's context-query endpoint enriches results with type labels and uses the same auth dependency. ✅ Aligned.

**S01,S02 → S03 boundary:** S03 consumes auth dependency (S01), CORS (S01), and type metadata patterns (S02) for result enrichment. E2E tests exercise all four endpoints through the full Docker stack. ✅ Aligned.

No boundary mismatches detected.

## Requirement Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| API-01 (well-known discovery) | validated | 10 unit tests + Docker curl. InstanceInfo schema verified. |
| API-02 (types endpoint) | validated | 8 unit tests. TypeInfo fields (iri, label, icon, icon_color, model_id, model_name) verified. |
| API-03 (shapes endpoint) | validated | 11 unit tests. Constraint round-trip, groups, helptext verified. Shape serialization risk retired. |
| API-04 (context-query) | validated | 13 endpoint tests + 5 SPARQL escape tests + 2 E2E tests. URL match, keyword match, dedup, graceful degradation verified. |
| API-05 (dual-auth) | validated | 15 unit tests. Cookie-first, Bearer fallback, invalid credentials → 401 with distinct messages. |
| API-06 (CORS headers) | validated | Docker curl. `Access-Control-Allow-Origin: *`, OPTIONS → 204, `always` flag on nginx. |
| API-07 (nginx Auth forwarding) | validated | Docker curl + `nginx -t`. `proxy_set_header Authorization $http_authorization` on `/api/`. |
| API-08 (user guide docs) | validated | Chapter 31 with 4 endpoint sections, curl examples, auth, CORS, errors. README TOC + 3 glossary entries. |

All 8 M013 requirements validated. No unaddressed requirements. The roadmap's orphan risk assessment ("all Active requirements not in this milestone's scope belong to M009/M010") is confirmed correct.

## Decisions Recorded

| ID | Decision | Choice |
|----|----------|--------|
| D159 | Dual-auth approach | Cookie-first, Bearer fallback; existing get_current_user unchanged |
| D160 | Shape serialization strategy | dataclasses.asdict() → Pydantic models |
| D161 | CORS policy | Wildcard `Access-Control-Allow-Origin: *` via nginx |
| D162 | Context-query scope | Literal matches only for v1 (no edge traversal) |
| D163 | JSON API paths outside /api/ | Extended `_is_html_route()` exclusion list |
| D164 | IconService access in endpoints | Ad-hoc instantiation matching codebase pattern |

## Known Limitations (accepted, not blocking)

1. **Context-query v1 — no relevance scores:** FTS keyword matches return matches but the endpoint doesn't surface ranking. By design per D162.
2. **Context-query v1 — no edge traversal:** Only searches literal values, not objects linked to matching objects. By design per D162.
3. **Authenticated success path not Docker-curl-verified:** The full authenticated success path (valid Bearer → 200) was tested via httpx AsyncClient unit tests, not Docker curl (would require creating a real API token in the DB). Unauthenticated and invalid-bearer paths are Docker-verified.
4. **IconService depends on /app/models directory:** In development without Docker, icon data returns None for all types. Not a crash but icons silently disappear.
5. **Model ID extraction depends on IRI naming convention:** User-created types with non-standard IRIs get `model_id: null`.

## Test Summary

- **Unit tests:** 63 in `test_api_surface.py` (25 S01 + 19 S02 + 18 S03 + 1 additional)
- **E2E tests:** 7 in `api-surface.spec.ts` covering all four endpoints
- **Backend regression:** 990+ tests passing at S02 completion, zero regressions reported
- **All slice verifications:** passed

## Verdict Rationale

All 8 success criteria met. All 3 slices delivered their claimed outputs with evidence. All 8 requirements validated. Cross-slice boundaries aligned correctly — the S01 auth+CORS foundation was consumed cleanly by S02 and S03. The milestone's key risks (dual-auth wiring, shape serialization fidelity, nginx header blocking) were all retired in the planned slices. 63 unit tests + 7 E2E tests provide strong contract and integration coverage. User guide Chapter 31 documents the full API surface. No gaps requiring remediation.

## Remediation Plan

None required — verdict is **pass**.
