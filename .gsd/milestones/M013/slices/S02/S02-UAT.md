# S02: Types and Shapes JSON Endpoints — UAT

**Milestone:** M013
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven unit tests + live-runtime curl verification)
- Why this mode is sufficient: Both endpoints return deterministic JSON from service-layer data. Unit tests verify schema, fields, and edge cases against mock data. Live-runtime curl confirms the endpoints work end-to-end through Docker Compose with real SHACL shapes.

## Preconditions

- Docker Compose stack running: `docker compose up -d` from repo root
- At least one Mental Model installed (basic-pkm is the starter model)
- A valid API token exists: check via `docker compose exec api python -m app.auth.cli list-tokens`
- If no token: `docker compose exec api python -m app.auth.cli create-token --name test`

## Smoke Test

```bash
curl -s -H "Authorization: Bearer <token>" http://localhost:3000/api/types | jq '.types | length'
```
Expected: A number > 0 (e.g., 6 for basic-pkm v2.0 with Task and Milestone). If 0, no models are installed.

## Test Cases

### 1. Types endpoint returns all installed types

1. `curl -s -H "Authorization: Bearer <token>" http://localhost:3000/api/types | jq '.'`
2. **Expected:** JSON object with `types` array. Each entry has `iri`, `label`, `icon`, `icon_color`, `model_id`, `model_name` fields.
3. Verify at least these types from basic-pkm: Note, Project, Person, Concept, Task, Milestone
4. Verify `model_id` is `"basic-pkm"` and `model_name` is `"Basic PKM"` for those types
5. Verify `icon` is a non-null string for at least Note (should be `"file-text"` or similar)

### 2. Types endpoint works with session cookie

1. Log in via browser at `http://localhost:3000`
2. Open browser DevTools → Network tab
3. Navigate to `http://localhost:3000/api/types` in a new tab
4. **Expected:** JSON response (not 401, not redirect) — session cookie authenticates the request

### 3. Types endpoint rejects unauthenticated requests

1. `curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/types`
2. **Expected:** HTTP 401
3. `curl -s http://localhost:3000/api/types | jq '.detail'`
4. **Expected:** `"Not authenticated"`

### 4. Shapes endpoint returns property shapes for known type

1. `curl -s -H "Authorization: Bearer <token>" http://localhost:3000/api/shapes/urn:sempkm:model:basic-pkm:Note | jq '.'`
2. **Expected:** JSON object with:
   - `shape_iri`: string containing "Note"
   - `target_class`: `"urn:sempkm:model:basic-pkm:Note"`
   - `label`: `"Note"` (or similar)
   - `properties`: non-empty array
   - Each property has `path`, `name`, `order` at minimum
3. Verify property `name` values include familiar fields (e.g., "Title", "Body", "Tags")
4. Verify constraint fields: `min_count` is int, `max_count` is int or null, `in_values` is array

### 5. Shapes endpoint returns groups with correct ordering

1. From the shapes response in test 4, check the `groups` array
2. **Expected:** Each group has `iri`, `label`, `order` fields
3. Groups are ordered by `order` value (ascending)

### 6. Shapes endpoint returns 404 for unknown type

1. `curl -s -H "Authorization: Bearer <token>" http://localhost:3000/api/shapes/urn:nonexistent:Type | jq '.'`
2. **Expected:** HTTP 404 with `{"detail": "No shape found for type: urn:nonexistent:Type"}`
3. `curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer <token>" http://localhost:3000/api/shapes/urn:nonexistent:Type`
4. **Expected:** `404`

### 7. Shapes endpoint rejects unauthenticated requests

1. `curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/shapes/urn:sempkm:model:basic-pkm:Note`
2. **Expected:** HTTP 401

### 8. CORS headers present on both endpoints

1. `curl -s -I -H "Authorization: Bearer <token>" http://localhost:3000/api/types | grep -i access-control`
2. **Expected:** `Access-Control-Allow-Origin: *` header present
3. `curl -s -I -H "Authorization: Bearer <token>" http://localhost:3000/api/shapes/urn:sempkm:model:basic-pkm:Note | grep -i access-control`
4. **Expected:** `Access-Control-Allow-Origin: *` header present

### 9. Shape property shapes match form editor fields

1. Open the SemPKM workspace in browser
2. Create or open a Note object → switch to Edit mode
3. Note the visible form fields (e.g., Title, Body, Tags, etc.)
4. Compare with `curl -s -H "Authorization: Bearer <token>" http://localhost:3000/api/shapes/urn:sempkm:model:basic-pkm:Note | jq '.properties[].name'`
5. **Expected:** The JSON property names match the form field labels in the editor

## Edge Cases

### Empty icon map (no model icons)

1. If a type has no icon declared in the model manifest, `icon` and `icon_color` should be `null` (not missing)
2. Verify with: `curl -s -H "Authorization: Bearer <token>" http://localhost:3000/api/types | jq '.types[] | select(.icon == null)'`
3. **Expected:** User-created types (if any) appear with null icons

### URL-encoded type IRI in shapes path

1. `curl -s -H "Authorization: Bearer <token>" "http://localhost:3000/api/shapes/urn%3Asempkm%3Amodel%3Abasic-pkm%3ANote" | jq '.target_class'`
2. **Expected:** Returns the same shape as the unencoded path — FastAPI `:path` converter handles decoding

### Multiple models installed

1. If CRM, Zettelkasten, or Research models are also installed:
2. `curl -s -H "Authorization: Bearer <token>" http://localhost:3000/api/types | jq '[.types[].model_id] | unique'`
3. **Expected:** Returns multiple model IDs (e.g., `["basic-pkm", "crm", "zettelkasten", "research"]`)

## Failure Signals

- HTTP 500 on `/api/types` → IconService or ModelService initialization failed (check Docker logs for traceback)
- HTTP 500 on `/api/shapes/{type_iri}` → ShapesService.get_form_for_type() threw an exception
- HTTP 302 redirect instead of 401 → `_is_html_route()` not excluding the endpoint path
- Empty `types` array when models are installed → ShapesService.get_types() not finding SHACL shapes graphs
- Properties array empty for a known type → ShapesService.get_form_for_type() returning a form with no properties
- `icon: null` for all types → IconService can't find model manifest files (check `/app/models` volume mount)

## Requirements Proved By This UAT

- API-02 — Types endpoint returns JSON with labels, icons, and model attribution for all installed types
- API-03 — Shapes endpoint returns structured JSON matching SHACL form editor fields, with 404 for unknown types
- API-05 (partial) — Both endpoints accept Bearer token and session cookie auth
- API-06 (partial) — CORS headers present on both endpoints

## Not Proven By This UAT

- API-04 — Context-query endpoint (S03 scope)
- API-08 — User guide documentation (S03 scope)
- Full E2E Playwright test coverage (S03 scope)
- Performance under load (not in scope for M013)

## Notes for Tester

- The `/api/types` endpoint creates `IconService` ad-hoc from `/app/models` — this only works inside Docker where the volume mount exists. Outside Docker, icons will all be `null`.
- `model_id` extraction relies on the `urn:sempkm:model:{id}:TypeName` convention. User-created types will have `model_id: null` and `model_name: null` — this is expected.
- The shapes endpoint uses `:path` converter so colons in the type IRI don't need URL-encoding in most HTTP clients (curl handles it natively).
