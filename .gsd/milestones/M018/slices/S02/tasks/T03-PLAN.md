---
estimated_steps: 7
estimated_files: 5
---

# T03: Build app routes, templates, and connect flow

**Slice:** S02 — Google OAuth 2.0 + Calendar List
**Milestone:** M018

## Description

Wires the auth module and gcal client (from T02) into HTTP route handlers and user-facing Jinja2 templates. Implements the complete OAuth connect flow: user enters Google Cloud Console credentials → clicks "Connect with Google" → redirected to Google consent screen → callback exchanges code for tokens → calendar list displayed with selection checkboxes → user saves selection → disconnect clears state.

Follows the `apps/linear-sync/app.py` pattern closely. All htmx URLs must use the `/app/google-calendar/` prefix (per KNOWLEDGE.md "App template htmx URLs must use proxy prefix").

## Steps

1. **Create `apps/google-calendar/app.py`** with route handlers modeled on `apps/linear-sync/app.py`:
   - Import the App class, auth helpers, and GCalClient from services
   - `google_calendar_app = App("google-calendar")`
   - `_make_client(ctx)` → creates GCalClient from ctx.http and ctx.state plus client_id/client_secret from state
   - `/_fragments/connect` (GET) → if connected, render connect_status.html with calendar list; if disconnected, render connect.html. On connection error, fall back to connect.html with error message.
   - `/_fragments/connect/credentials` (POST) → save client_id and client_secret from form to state. Re-render connect.html with success message.
   - `/_fragments/connect/google` (POST) → generate random state param (uuid4), store in state as `oauth_state`, build authorize URL with `redirect_uri=http://localhost:3000/app/google-calendar/_fragments/oauth-callback`, return redirect response.
   - `/_fragments/oauth-callback` (GET) → read `code` and `state` from query params, verify state matches stored `oauth_state`, exchange code for tokens via `exchange_code()`, store tokens via `store_auth_tokens()`, fetch calendar list to get user's email (primary calendar summary), redirect to `/_fragments/connect` (or return connect_status).
   - `/_fragments/connect/disconnect` (POST) → call `clear_auth_state()`, re-render connect.html.
   - `/_fragments/settings/calendars` (POST) → read selected calendar IDs from form, store as JSON in state key `selected_calendars`, re-render connect_status.html.
   - Skeleton task handlers for S03/S04: `@google_calendar_app.task("poll-events")` and `@google_calendar_app.task("push-changes")` that return `{"status": "ok", "message": "Not yet implemented"}`.
   - **CRITICAL**: The callback route reads `code` and `state` from `request.query_params` — this depends on the T01 proxy fix being in place.

2. **Create `apps/google-calendar/frontend/templates/connect.html`**:
   - `<div id="connect-content" class="gcal-sync-settings">` wrapper
   - Error alert block (conditional on `error` variable)
   - Success alert block (conditional on `success` variable)
   - Section "Google Cloud Credentials": form with `client_id` and `client_secret` inputs, `hx-post="/app/google-calendar/_fragments/connect/credentials"`, `hx-target="#connect-content"`, `hx-swap="innerHTML"`
   - Instructions paragraph: "Create an OAuth 2.0 Client ID in Google Cloud Console → APIs & Services → Credentials. Set authorized redirect URI to `http://localhost:3000/app/google-calendar/_fragments/oauth-callback`."
   - Section "Connect": "Connect with Google" button as `hx-post="/app/google-calendar/_fragments/connect/google"`. Only enabled when client_id/client_secret are saved (passed as template variables `has_credentials`).
   - All htmx URLs prefixed with `/app/google-calendar/`

3. **Create `apps/google-calendar/frontend/templates/connect_status.html`**:
   - Connection status badge (● Connected) with Google email
   - Calendar list section: loop over `calendars`, each as checkbox `<input type="checkbox" name="calendar_ids" value="{{ cal.id }}" {% if cal.id in selected_calendars %}checked{% endif %}>` with calendar summary and primary badge
   - Save calendars form: `hx-post="/app/google-calendar/_fragments/settings/calendars"`, `hx-target="#connect-content"`
   - Disconnect section: button with `hx-post="/app/google-calendar/_fragments/connect/disconnect"`, `hx-confirm` dialog
   - All htmx URLs prefixed with `/app/google-calendar/`

4. **Create `apps/google-calendar/frontend/static/styles.css`**:
   - Adapt from `apps/linear-sync/frontend/static/styles.css`
   - Style the credential form, calendar checkbox list, connection badge, alerts
   - Use CSS variables from the workspace theme where available

5. **Create `apps/google-calendar/frontend/templates/` directory** (ensure the `frontend/templates/` and `frontend/static/` paths exist).

6. **Verify template syntax**: ensure all Jinja2 `{{ }}` and `{% %}` blocks are valid, no unclosed tags.

7. **Run full test suite** to confirm nothing is broken: `cd backend && python -m pytest tests/ -x -q`.

## Must-Haves

- [ ] `app.py` handles the full OAuth flow: credentials save → authorize redirect → callback → token exchange → calendar list display
- [ ] OAuth state parameter generated, stored, and verified on callback (CSRF protection)
- [ ] `connect.html` has credential inputs and "Connect with Google" button
- [ ] `connect_status.html` shows Google email, calendar checkboxes, save, disconnect
- [ ] All htmx URLs use `/app/google-calendar/` prefix
- [ ] Redirect URI is `http://localhost:3000/app/google-calendar/_fragments/oauth-callback`
- [ ] Selected calendars persisted as JSON via StateClient
- [ ] Skeleton task handlers for `poll-events` and `push-changes` exist

## Verification

- `cd backend && python -m pytest tests/ -x -q` — full suite passes, no regressions
- Template files have valid Jinja2 syntax (no unclosed blocks)
- `app.py` exports `google_calendar_app` matching the manifest entrypoint `app:google_calendar_app`

## Inputs

- T02 completed: `apps/google-calendar/services/auth.py` and `services/gcal_client.py` exist with all helper functions
- `apps/linear-sync/app.py` — reference route handler pattern (~397 lines)
- `apps/linear-sync/frontend/templates/connect.html` — reference connect form template
- `apps/linear-sync/frontend/templates/connect_status.html` — reference status template
- `apps/linear-sync/frontend/static/styles.css` — reference CSS
- KNOWLEDGE.md "App template htmx URLs must use proxy prefix" — all htmx URLs must be prefixed with `/app/google-calendar/`
- S02-RESEARCH.md: callback URL `http://localhost:3000/app/google-calendar/_fragments/oauth-callback`, Google authorize params, CSRF state pattern

## Expected Output

- `apps/google-calendar/app.py` — route handlers (~300 lines)
- `apps/google-calendar/frontend/templates/connect.html` — credential + OAuth connect form
- `apps/google-calendar/frontend/templates/connect_status.html` — status + calendar list + disconnect
- `apps/google-calendar/frontend/static/styles.css` — app styling
