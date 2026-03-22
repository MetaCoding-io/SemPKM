---
estimated_steps: 5
estimated_files: 6
skills_used: []
---

# T01: Federation endpoint persistence and admin API

**Slice:** S05 — Federated SPARQL Console
**Milestone:** M033

## Description

Create the file-based federation endpoint persistence layer and admin management UI. Currently the federation allowlist is read-only from `settings.federation_allowed_endpoints` (comma-separated env var). This task adds runtime CRUD: a JSON file at `data/.federation-endpoints.json` stores admin-added endpoints, merged with env var entries at load time. New API routes allow adding/removing endpoints. An admin page provides the management UI.

## Steps

1. **Create `backend/app/sparql/federation_config.py`** following the `instance_config.py` pattern:
   - Pydantic model `FederationEndpoints` with `endpoints: list[str]` and `updated_at: str` (ISO 8601)
   - `DEFAULT_FEDERATION_PATH = Path("data/.federation-endpoints.json")`
   - `load_federation_endpoints(path=None) -> FederationEndpoints` — returns model with empty list if file absent/invalid, never raises
   - `save_federation_endpoints(config, path=None)` — atomic write via temp file + `os.replace()`
   - `get_merged_endpoints() -> list[dict]` — merges env var entries (from `settings.get_allowed_endpoints()`) with persisted entries, returns list of `{"url": str, "source": "env"|"admin", "removable": bool}`. Env var entries are `removable: False`. Deduplicates by URL (env wins).

2. **Update `backend/app/sparql/mirror_router.py`** — add two new routes and update the existing GET:
   - `POST /api/sparql/mirror/endpoints` — accepts `{"url": str}`, validates URL format (must start with `http://` or `https://`), adds to persisted file, returns updated merged list. Uses `require_role("owner")`.
   - `DELETE /api/sparql/mirror/endpoints/{encoded_url}` — URL-decodes the path param, removes from persisted file (refuses to remove env-var-sourced entries), returns updated list. Uses `require_role("owner")`.
   - Update existing `GET /api/sparql/mirror/endpoints` to call `get_merged_endpoints()` instead of `settings.get_allowed_endpoints()`. Response shape changes to `{"endpoints": [{"url": str, "source": str, "removable": bool}], "allowlist_configured": bool}`.

3. **Update `backend/app/sparql/mirror.py`** — change `validate_endpoint()` to check merged endpoints:
   - Import `get_merged_endpoints` from `federation_config`
   - `validate_endpoint()` checks if the URL is in the merged list (either env or admin source)

4. **Create `backend/app/templates/admin/federation.html`** following `webhooks.html` layout:
   - Extends `base.html`
   - Title "Federation Endpoints"
   - Lead text explaining the allowlist purpose
   - Add form: text input for endpoint URL + submit button, uses htmx `hx-post="/admin/federation/add"` targeting the endpoint list
   - Endpoint list: each entry shows URL, source badge ("env" or "admin"), and a remove button for admin-sourced entries
   - Remove buttons use htmx `hx-delete` targeting the list container
   - Lucide icons in buttons must use CSS sizing with `flex-shrink: 0` per CLAUDE.md rules

5. **Wire into admin portal:**
   - Add `GET /admin/federation` route in `backend/app/admin/router.py` — renders the federation template with current endpoint list from `get_merged_endpoints()`. Owner-only. Follow the pattern of `webhooks()` route.
   - Add `POST /admin/federation/add` and `DELETE /admin/federation/remove` htmx routes in admin router that call the API and return updated HTML partial.
   - Add a "Federation" card to `backend/app/templates/admin/index.html` following the existing card pattern (h2, p description, a.btn-primary with htmx).

## Must-Haves

- [ ] `federation_config.py` handles load/save/merge with atomic writes
- [ ] POST and DELETE API routes enforce owner-only access
- [ ] GET endpoint returns merged list with source annotation
- [ ] Env var entries cannot be removed via the API (returns 400/409)
- [ ] Admin page renders endpoint list with add/remove UI
- [ ] Admin index has Federation card
- [ ] `validate_endpoint()` checks merged list, not just env var

## Verification

- Manually test: `curl -X POST /api/sparql/mirror/endpoints -d '{"url":"https://dbpedia.org/sparql"}' -H 'Content-Type: application/json'` returns updated list
- `curl GET /api/sparql/mirror/endpoints` returns merged env+admin entries with source field
- Admin page renders at `/admin/federation`
- Tests in T03 will provide automated coverage

## Inputs

- `backend/app/instance_config.py` — reference pattern for file persistence (atomic write, Pydantic model)
- `backend/app/sparql/mirror_router.py` — existing mirror routes to extend
- `backend/app/sparql/mirror.py` — `validate_endpoint()` to update
- `backend/app/config.py` — `get_allowed_endpoints()` env var source
- `backend/app/templates/admin/webhooks.html` — template layout pattern
- `backend/app/templates/admin/index.html` — admin card pattern
- `backend/app/admin/router.py` — admin route registration pattern

## Expected Output

- `backend/app/sparql/federation_config.py` — new federation config persistence module
- `backend/app/sparql/mirror_router.py` — updated with POST/DELETE routes and merged GET
- `backend/app/sparql/mirror.py` — updated validate_endpoint()
- `backend/app/templates/admin/federation.html` — new admin federation page
- `backend/app/templates/admin/index.html` — updated with Federation card
- `backend/app/admin/router.py` — updated with federation route
