---
id: T05
parent: S01
milestone: M014
provides:
  - Admin API key management page at /admin/api-keys with create, list, and delete flows
  - Sidebar nav link and admin index card for API key management
key_files:
  - backend/app/templates/admin/api_tokens.html
  - backend/app/admin/router.py
  - backend/app/templates/admin/index.html
  - backend/app/templates/components/_sidebar.html
key_decisions:
  - Used request.app.state.auth_service instead of constructing AuthService(db) — AuthService requires async_sessionmaker, not a raw AsyncSession, so the plan's suggestion to follow the admin router's Depends(get_db_session) pattern wouldn't work
patterns_established:
  - Admin API key page follows webhooks.html template pattern exactly — card layout, form + htmx POST, sparql-results table, error-box/success-box partials, hx-confirm on delete
observability_surfaces:
  - logger.info on API token create/delete via admin UI (backend container logs)
  - /admin/api-keys page shows all active tokens with name + created date
  - One-time plaintext token display with copy button after creation
  - Deleted tokens immediately return 401 "Invalid or expired API token" on Bearer auth
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T05: Admin API key management page

**Added admin page at /admin/api-keys for creating, listing, and deleting API keys with one-time plaintext display, copy button, and confirmation-guarded delete — no shell access needed.**

## What Happened

Added three routes to the admin router (`GET /admin/api-keys`, `POST /admin/api-keys`, `DELETE /admin/api-keys/{token_id}`) that use `request.app.state.auth_service` to call `list_api_tokens`, `create_api_token`, and `revoke_api_token`. Created `api_tokens.html` template following the webhooks page pattern with a create form, token list table, one-time plaintext banner with Copy button and warning, and empty state.

Added "API Keys" card to admin index between Operations Log and Applications. Added "API Keys" sidebar nav link with `key-round` Lucide icon between Operations Log and SPARQL Console, inside the owner-only block.

Key deviation from plan: AuthService takes `async_sessionmaker` not `AsyncSession`, so I used `request.app.state.auth_service` (already initialized at startup) instead of constructing a new instance per request. This matches the auth router's `_get_auth_service(request)` pattern exactly.

## Verification

Full UI round-trip verified in browser:
1. Admin portal shows "API Keys" card with correct description and "Manage API Keys" button
2. Sidebar shows "API Keys" link with key-round icon in Admin section (owner-only)
3. API Keys page renders with create form and empty state message when no tokens exist
4. Created token "Extension Key" → plaintext displayed once with Copy button + "This key will only be shown once" warning
5. Token appeared in table with name and created timestamp
6. Copied token used successfully with Bearer auth (`GET /api/types` returned valid data)
7. Deleted token → confirmation dialog fired → token removed from table → success message shown
8. Same token then returned 401 `"Invalid or expired API token"` via Bearer auth
9. Empty state message correctly displayed after all tokens deleted

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose exec api python -c "import ast; ast.parse(open('/app/app/admin/router.py').read())"` | 0 | ✅ pass | 1s |
| 2 | LSP diagnostics on backend/app/admin/router.py | 0 | ✅ pass (no errors, only pre-existing hints) | <1s |
| 3 | browser_assert: admin index has API Keys card + link | 0 | ✅ pass (4/4 checks) | <1s |
| 4 | browser_assert: empty state text visible | 0 | ✅ pass (4/4 checks) | <1s |
| 5 | `curl -H "Authorization: Bearer <created-token>" /api/types` | 0 | ✅ pass (returned types JSON) | <1s |
| 6 | `curl -H "Authorization: Bearer <deleted-token>" /api/types` | 0 | ✅ pass (returned 401 "Invalid or expired API token") | <1s |
| 7 | `docker compose exec api python -m pytest tests/test_commands_bearer_auth.py tests/test_api_surface.py` | N/A | ⚠️ skipped — pytest-asyncio not installed in container venv (pre-existing) | — |

## Diagnostics

- **Admin page:** Navigate to `/admin/api-keys` as owner to see all active API keys
- **Container logs:** `docker compose logs api | grep "API token"` shows create/delete events
- **Token verification:** Create a token via admin UI → use as `Authorization: Bearer <token>` header against any dual-auth endpoint (e.g., `GET /api/types`)
- **Revocation check:** Delete a token via admin UI → same Bearer request returns 401

## Deviations

- Plan suggested constructing `AuthService(db)` from `Depends(get_db_session)` — this doesn't work because `AuthService.__init__` takes `async_sessionmaker`, not `AsyncSession`. Used `request.app.state.auth_service` instead (already initialized at app startup), matching the auth router's own pattern.
- Plan mentioned touching `frontend/static/css/style.css` — not needed; the existing `.admin-page`, `.card`, `.sparql-results`, `.success-box`, `.error-box` classes already provide correct styling.

## Known Issues

- Backend unit tests (`test_commands_bearer_auth.py`, `test_api_surface.py`) cannot run inside the Docker container because `pytest-asyncio` is not installed in the venv. This is a pre-existing issue, not caused by this task. The tests exist on the host filesystem but the `tests/` directory is not volume-mounted into the container.

## Files Created/Modified

- `backend/app/admin/router.py` — Added three API key routes (GET, POST, DELETE), _get_auth_service helper, AuthService import
- `backend/app/templates/admin/api_tokens.html` — New template with create form, one-time plaintext display, token list table, empty state
- `backend/app/templates/admin/index.html` — Added API Keys card to admin dashboard grid
- `backend/app/templates/components/_sidebar.html` — Added API Keys nav link with key-round icon in owner section
- `.gsd/milestones/M014/slices/S01/tasks/T05-PLAN.md` — Added Observability Impact section (pre-flight fix)
