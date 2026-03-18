---
estimated_steps: 6
estimated_files: 4
---

# T05: Admin API key management page

**Slice:** S01 — Backend auth fix + extension scaffold with working capture
**Milestone:** M014

## Description

Users need a way to generate API keys through the admin UI so they can configure the browser extension without shell access. The auth router already has full CRUD endpoints for API tokens (`POST /api/auth/tokens`, `GET /api/auth/tokens`, `DELETE /api/auth/tokens/{id}`) with proper schemas (`CreateTokenRequest`, `CreateTokenResponse`, `TokenListItem`). This task adds an admin page that exposes these endpoints through htmx forms, following the existing webhooks page pattern.

The page needs: a create form (name input), a list table showing existing tokens (name, created date), per-token delete buttons, and — critically — a one-time display of the plaintext token after creation with a copy button and warning that it won't be shown again.

## Steps

1. **Add the admin route** in `backend/app/admin/router.py`:
   - `GET /admin/api-keys` renders `admin/api_tokens.html` with token list
   - The route must call the existing `GET /api/auth/tokens` logic internally — specifically, import `AuthService` and call `auth_service.list_api_tokens(user.id)` to get the token list. Do NOT make an HTTP call to `/api/auth/tokens` from the backend.
   - Use `require_role("owner")` dependency (cookie auth, consistent with all other admin routes)
   - Follow the `templates_response()` pattern with htmx block rendering

2. **Add create and delete handler routes** in the same router:
   - `POST /admin/api-keys` — reads `name` from form, calls `auth_service.create_api_token(user_id=user.id, name=name)`, returns updated token list partial WITH the plaintext token displayed once in a success banner
   - `DELETE /admin/api-keys/{token_id}` — calls `auth_service.revoke_api_token(user.id, token_id)`, returns updated token list partial
   - Both return the `token_list` block for htmx swap
   - To get the AuthService instance, follow the pattern in `backend/app/auth/router.py`: `auth_service = AuthService(db)` where `db` comes from `Depends(get_db_session)`. Look at how `_get_auth_service` works in the auth router — it gets the db session from `request.app.state` or the dependency.

3. **Create the template** `backend/app/templates/admin/api_tokens.html`:
   - Extends `base.html`, block title "SemPKM - API Keys"
   - Header: "API Keys" with lead text about browser extension and external client authentication
   - Create form card: name text input + "Create Key" button (htmx POST to `/admin/api-keys`, target `#token-list`, swap outerHTML)
   - Token list block (`{% block token_list %}`): 
     - If `new_token` is defined, show a highlighted success banner with the plaintext token in a `<code>` element, a "Copy" button using `navigator.clipboard.writeText()`, and a ⚠️ warning: "This key will only be shown once. Copy it now."
     - Table with columns: Name, Created, Actions (delete button)
     - Delete button: htmx DELETE to `/admin/api-keys/{id}`, target `#token-list`, swap outerHTML, with `hx-confirm="Delete this API key? Any extension or client using it will stop working."`
     - Empty state: "No API keys yet. Create one to authenticate the browser extension."
   - Follow the webhooks.html template structure (card layout, `.sparql-results` table class, `.error-box`/`.success-box` patterns)
   - The copy button should use an inline `onclick` handler — but wait, this is a Jinja template served by the backend, not a Chrome extension, so inline handlers are fine (no CSP restriction)

4. **Add sidebar nav link** in `backend/app/templates/components/_sidebar.html`:
   - Add an "API Keys" link in the Admin section, between "Operations Log" and the SPARQL Console link
   - Use `data-lucide="key-round"` icon (Lucide icon for API keys)
   - htmx navigation pattern: `hx-get="/admin/api-keys" hx-target="#app-content" hx-swap="innerHTML" hx-push-url="true"`
   - Only shown to owner role (inside the existing `{% if user.role == 'owner' %}` block)

5. **Add card to admin index** in `backend/app/templates/admin/index.html`:
   - Add an "API Keys" card in the dashboard-cards grid, between the Operations Log card and Applications card
   - Description: "Create and manage API keys for the browser extension and external API clients."
   - Button: "Manage API Keys" linking to `/admin/api-keys`

6. **Add AuthService dependency** — The admin router needs access to AuthService. Look at how the auth router gets it:
   - In `backend/app/auth/router.py`, `_get_auth_service(request)` creates `AuthService(db)` from `request.state.db`
   - The admin router should use the same pattern. Import `AuthService` from `app.auth.service`, get `db` from `Depends(get_db_session)`, and construct `AuthService(db)` in each handler
   - Verify the AuthService constructor signature: `AuthService.__init__(self, db: AsyncSession)`

## Must-Haves

- [ ] `GET /admin/api-keys` renders token list page with create form
- [ ] `POST /admin/api-keys` creates token and shows plaintext ONCE with copy button
- [ ] `DELETE /admin/api-keys/{token_id}` revokes token with confirmation dialog
- [ ] Sidebar nav link under Admin section with key icon
- [ ] Admin index card for API Keys
- [ ] Empty state message when no tokens exist
- [ ] Warning text that the token won't be shown again

## Verification

- Navigate to admin portal → "API Keys" card visible → click → page renders with create form and empty state message
- Enter name "Extension Key" → click Create → plaintext token displayed with copy button and warning → token appears in table
- Click Copy → paste into text editor → token string matches
- Click Delete on the token → confirmation dialog → confirm → token removed from table
- Sidebar Admin section shows "API Keys" link with key icon
- `cd backend && python -m pytest tests/test_commands_bearer_auth.py tests/test_api_surface.py -v` — no regressions
- Create a token via admin UI → copy it → use it in extension options page "Test Connection" → green checkmark
- Delete that token → extension returns 401

## Inputs

- `backend/app/auth/router.py` — Reference for AuthService usage pattern (`_get_auth_service`, `create_api_token`, `list_api_tokens`, `revoke_api_token`)
- `backend/app/auth/schemas.py` — `CreateTokenRequest`, `CreateTokenResponse`, `TokenListItem` schemas showing field names
- `backend/app/auth/service.py` — `AuthService` class with `create_api_token(user_id, name)`, `list_api_tokens(user_id)`, `revoke_api_token(user_id, token_id)` methods
- `backend/app/admin/router.py` — Existing admin router patterns (webhooks, models, ops-log) for route structure, template rendering, and htmx partial support
- `backend/app/templates/admin/webhooks.html` — Reference template for card layout, form structure, table layout, error/success boxes, htmx patterns
- `backend/app/templates/admin/index.html` — Admin landing page card grid to add the API Keys card
- `backend/app/templates/components/_sidebar.html` — Sidebar nav structure for adding API Keys link
- T01-T04 summaries confirm the extension options page and popup are ready to use API keys created through this page

## Expected Output

- `backend/app/templates/admin/api_tokens.html` — New admin template for API key management (create form, token list table, one-time plaintext display, delete buttons)
- `backend/app/admin/router.py` — Three new routes: `GET /admin/api-keys`, `POST /admin/api-keys`, `DELETE /admin/api-keys/{token_id}`
- `backend/app/templates/admin/index.html` — API Keys card added to admin dashboard
- `backend/app/templates/components/_sidebar.html` — "API Keys" nav link added to Admin section

## Observability Impact

- **New log messages:** `logger.info("API token '%s' created via admin UI for user %s", name, user.id)` on create; `logger.info("API token %s revoked via admin UI for user %s", token_id, user.id)` on delete — these fire in the API container logs alongside the existing auth-layer debug logs.
- **Inspection surface:** Navigate to `/admin/api-keys` as an owner to see all active API keys (name + created date). The one-time plaintext token display is visible only immediately after creation.
- **Failure visibility:** Token creation errors render as `.error-box` in the htmx response. Delete of non-existent tokens shows "API key not found." in an error box. Non-owner users get 403 from `require_role("owner")`.
- **Downstream signal:** Tokens created through this page are immediately usable in extension options "Test Connection" flow. Deleted tokens cause 401 `"Invalid or expired API token"` on subsequent Bearer auth attempts.
