---
estimated_steps: 5
estimated_files: 7
skills_used: []
---

# T02: Federation endpoint allowlist — API and settings UI

**Slice:** S01 — Federated SPARQL & Mirrored Triples
**Milestone:** M033

## Description

Federation SERVICE queries against arbitrary SPARQL endpoints are a security risk (data exfiltration, SSRF). An admin-managed allowlist gates which endpoints users can query. The allowlist is stored in the existing `InstanceConfig` key-value table (key: `federation.allowed_endpoints`, value: JSON array of `{url, label}` objects).

This task creates:
1. `FederationAllowlist` service class for CRUD operations
2. API router with GET/POST/DELETE endpoints (owner-only)
3. Settings UI partial for managing endpoints
4. Enforcement hook in SPARQL execution that rejects non-allowlisted SERVICE endpoints

The settings page (`settings_page.html`) already has a category sidebar pattern with partials — the Federation section follows this exactly.

## Steps

1. **Create `backend/app/federation/allowlist.py`:** Define `FederationAllowlist` class with an `AsyncSession` dependency. Methods: `get_endpoints() -> list[dict]` (reads `federation.allowed_endpoints` from InstanceConfig, returns `[{url, label}]`), `add_endpoint(url: str, label: str)` (validates URL format, appends to list, writes back), `remove_endpoint(url: str)` (removes matching entry), `is_allowed(url: str) -> bool` (checks if URL is in the list). Include Wikidata (`https://query.wikidata.org/sparql`) and DBpedia (`https://dbpedia.org/sparql`) as default entries if key doesn't exist yet.

2. **Create `backend/app/federation/allowlist_router.py`:** API router with prefix `/api/federation`. Routes: `GET /endpoints` (returns allowlist, any authenticated user), `POST /endpoints` (adds endpoint, owner-only, body: `{url, label}`), `DELETE /endpoints` (removes endpoint, owner-only, body: `{url}`). Use `Depends(get_current_user)` and role checking.

3. **Create `backend/app/templates/browser/_federation_settings.html`:** Partial template following the pattern of `_llm_settings.html` / `_webid_settings.html`. Shows: list of allowed endpoints with URL and label, delete button per row, "Add endpoint" form with URL and label inputs, submit button. Uses htmx: `hx-post="/api/federation/endpoints"` with `hx-swap="outerHTML"` on the endpoint list for live updates. Include a help text explaining that Wikidata and DBpedia are pre-configured defaults.

4. **Wire into settings page:** Add a "Federation" category button to `settings_page.html` sidebar (after "Authorized Apps"). Add the category panel div that includes `_federation_settings.html` via htmx `hx-get="/browser/settings/federation"` with `hx-trigger="intersect once"`. Add the settings route in `backend/app/browser/settings.py`.

5. **Enforce allowlist in SPARQL execution:** In `backend/app/sparql/router.py` `_execute_sparql()` (or a new helper), before executing: parse SERVICE endpoint URLs from the query using regex on the stripped-strings version, check each against the allowlist. If any endpoint is not allowed, return 403 with message listing the rejected endpoint. Owner role bypasses the check (consistent with all_graphs bypass). Write unit tests for allowlist CRUD and enforcement.

## Must-Haves

- [ ] `FederationAllowlist` class with get/add/remove/is_allowed methods
- [ ] API endpoints: GET/POST/DELETE at `/api/federation/endpoints`
- [ ] Owner-only write access; any authenticated user can read the list
- [ ] Settings UI partial with endpoint list, add form, delete buttons
- [ ] "Federation" category appears in settings sidebar
- [ ] Wikidata and DBpedia are default entries
- [ ] SERVICE endpoints validated against allowlist before query execution
- [ ] Owner bypasses allowlist check
- [ ] Unit tests for allowlist CRUD

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_federation_allowlist.py -v` — all pass
- Verify settings page renders Federation category with endpoint management UI

## Inputs

- `backend/app/auth/models.py` — InstanceConfig model (key-value store)
- `backend/app/browser/settings.py` — existing settings page routes
- `backend/app/templates/browser/settings_page.html` — settings page template with category sidebar
- `backend/app/templates/browser/_llm_settings.html` — reference partial pattern
- `backend/app/sparql/router.py` — _execute_sparql() function where enforcement goes
- `backend/app/sparql/client.py` — scope_to_current_graph() with SERVICE pass-through (from T01)

## Expected Output

- `backend/app/federation/allowlist.py` — FederationAllowlist service class
- `backend/app/federation/allowlist_router.py` — API router for endpoint CRUD
- `backend/app/templates/browser/_federation_settings.html` — settings UI partial
- `backend/app/templates/browser/settings_page.html` — Federation category added to sidebar
- `backend/app/browser/settings.py` — federation settings route added
- `backend/app/sparql/router.py` — allowlist enforcement in query execution
- `backend/tests/test_federation_allowlist.py` — unit tests for allowlist CRUD and enforcement

## Observability Impact

- **New inspection surface:** `GET /api/federation/endpoints` returns the current allowlist as JSON — any authenticated user can call it to verify the endpoint configuration.
- **Structured logging:** `FederationAllowlist.add_endpoint()` and `remove_endpoint()` log at INFO level with the endpoint URL and label, providing an audit trail for allowlist changes.
- **Failure visibility:** When a non-allowlisted SERVICE endpoint is used, the SPARQL execution returns HTTP 403 with `detail: "Federation endpoint not in allowlist: <url>"` — the rejected URL is explicitly named in the error message.
- **Future agent inspection:** Run `curl -s localhost:8000/api/federation/endpoints` (with auth) to see the current allowlist. Check `InstanceConfig` table for key `federation.allowed_endpoints` to verify persistence.
