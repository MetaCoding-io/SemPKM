# S03: Admin Portal & Docker/nginx Integration — UAT

**Milestone:** M009
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for config verification, live-runtime for admin UI)
- Why this mode is sufficient: nginx config and docker-compose changes are verifiable via grep/inspection. Admin endpoints are tested via 33 unit tests. Full Docker runtime exercise is S07 scope — this UAT covers what's verifiable now plus a Docker smoke test.

## Preconditions

- Docker stack running from this worktree (`docker compose up -d` from the M009 worktree)
- At least one user with `owner` role exists (setup wizard completed)
- Logged in as owner in browser at `http://localhost:3000`

## Smoke Test

Navigate to `http://localhost:3000/admin/apps` while logged in as owner. Page should load showing "Applications" heading with either a list of installed apps or an empty state message.

## Test Cases

### 1. Admin list page loads with empty state

1. Navigate to `/admin/apps`
2. Verify page title or heading shows "Applications"
3. **Expected:** Empty state message displayed (e.g. "No apps installed"), install form visible with app_path input and "Install" button

### 2. Sidebar nav entry visible for owner

1. Click the hamburger/sidebar to expand admin navigation
2. Look for "Applications" entry in the Admin section
3. **Expected:** "Applications" link visible with puzzle icon, positioned after "Operations Log"
4. Click "Applications" — page loads via htmx without full page reload

### 3. Sidebar nav hidden for non-owner

1. Log in as a `member` role user
2. Expand sidebar navigation
3. **Expected:** "Applications" link is NOT visible in the sidebar

### 4. Admin index card present

1. Navigate to `/admin/` (admin home)
2. Scroll through dashboard cards
3. **Expected:** "Applications" card visible with description text and link to `/admin/apps`

### 5. Install app via admin form

1. Place a valid test app in `./apps/test-app/` with a `manifest.yaml`
2. Navigate to `/admin/apps`
3. Enter `test-app` in the install form's app_path field
4. Click "Install"
5. **Expected:** Redirect back to `/admin/apps` with success flash message. App appears in list with status badge.

### 6. App list shows status details

1. After installing an app (test 5), view `/admin/apps`
2. Check the app card/row
3. **Expected:** Status badge (running/stopped/installing), version string, uptime display, PID number visible

### 7. App detail page loads

1. Click on an installed app name in the list
2. **Expected:** Detail page at `/admin/apps/{app_id}` loads with:
   - Header showing app name, version, status badge
   - Stats bar with PID, uptime, restart count
   - Permissions table (from manifest)
   - Log viewer section (ring buffer output or "No logs available")
   - Start/Stop/Restart/Uninstall action buttons
   - Placeholder sections for "Task History" and "Renderer Assignments"

### 8. Start/Stop/Restart actions

1. On the detail page for a stopped app, click "Start"
2. **Expected:** Redirect back to detail page with updated status showing "running"
3. Click "Stop"
4. **Expected:** Status changes to "stopped"
5. Click "Restart"
6. **Expected:** Status shows "running" again

### 9. Uninstall action

1. On the detail page, click "Uninstall"
2. **Expected:** Redirect to `/admin/apps` list. App no longer appears in the list. Success flash message shown.

### 10. Detail page 404 for unknown app

1. Navigate to `/admin/apps/nonexistent-app-id`
2. **Expected:** HTTP 404 response

### 11. htmx partial rendering

1. Navigate to `/admin/apps` via sidebar link (htmx request)
2. Open browser DevTools Network tab
3. **Expected:** Response contains only the content block (no full `<html>` wrapper), because the request includes `HX-Request: true` header

### 12. Install error handling

1. Enter an invalid path (e.g. `nonexistent-path`) in the install form
2. Click "Install"
3. **Expected:** Redirect back to `/admin/apps` with error flash message indicating the app could not be installed

## Edge Cases

### Unknown app_id on lifecycle actions

1. POST to `/admin/apps/nonexistent/start` (via curl or modified form action)
2. **Expected:** HTTP 404 or error redirect — does not crash

### Non-owner tries lifecycle action

1. Log in as `member` role
2. POST to `/admin/apps/{app_id}/start`
3. **Expected:** HTTP 403 forbidden

### Unauthenticated access

1. In an incognito/private window, navigate to `/admin/apps`
2. **Expected:** Redirect to login page (302)

## Config Verification (artifact-driven — no runtime needed)

### nginx location for app-static

1. Run: `grep -A4 "location /app-static/" frontend/nginx.conf`
2. **Expected:** `alias /app/data/apps-static/;` with trailing slashes on both location and alias. Cache headers present (`Cache-Control`, `Expires`).

### nginx location for app proxy

1. Run: `grep -A6 "location /app/" frontend/nginx.conf`
2. **Expected:** `proxy_pass http://api:8000/app/;` with standard proxy headers. Located before catch-all `location /`.

### nginx location ordering

1. Run: `grep -n "location " frontend/nginx.conf | tail -5`
2. **Expected:** `/app-static/` and `/app/` appear on earlier line numbers than catch-all `/`

### docker-compose apps volume

1. Run: `grep "apps:/app/apps" docker-compose.yml`
2. **Expected:** `./apps:/app/apps:ro` mount on api service

### docker-compose shared data volume on frontend

1. Run: `grep "sempkm_data" docker-compose.yml`
2. **Expected:** Two matches — one on api service (existing), one on frontend service (new, `:ro`)

### Static asset copy method exists

1. Run: `grep "_copy_static_assets" backend/app/apps/manager.py`
2. **Expected:** At least 2 matches — method definition and call from install()

### Router ordering in main.py

1. Run: `grep -n "app_admin_router\|app_proxy_router" backend/app/main.py`
2. **Expected:** `app_admin_router` line number is lower than `app_proxy_router` line number

## Failure Signals

- `/admin/apps` returns 404 or 502 → router not included in main.py or included after proxy catch-all
- Sidebar missing "Applications" → template edit not applied or user is not owner role
- Admin page shows no app data → AppManager not wired to app.state
- `/app-static/{appId}/file.css` returns 404 in Docker → nginx alias misconfigured or sempkm_data volume not mounted on frontend
- Install form submits but nothing happens → POST endpoint not working, check logs for errors

## Requirements Proved By This UAT

- APP-10 (partial) — Admin list + detail pages with lifecycle actions. Full validation when task history (S05) and renderer assignments (S06) are added.
- APP-14 — Docker/nginx integration: volume mounts, proxy locations, static asset serving config verified.

## Not Proven By This UAT

- Static assets actually served by nginx in running Docker stack (requires S07 with real app installed)
- Task history display on detail page (S05)
- Renderer assignments display on detail page (S06)
- Memory usage stat on list page (not implemented)
- Full E2E install → use → admin → uninstall flow (S07)

## Notes for Tester

- The "Config Verification" section can be run without Docker — just grep commands on the source files.
- The live UI tests require Docker stack running with an owner user session.
- The detail page has placeholder sections marked "Coming in S05" and "Coming in S06" — these are intentional, not bugs.
- Flash messages are passed via query params — check the URL bar after install/uninstall for `?success=...` or `?error=...`.
- The test app used in tests 5-9 must have a valid `manifest.yaml` — use the one from S01/S02 test fixtures if available.
