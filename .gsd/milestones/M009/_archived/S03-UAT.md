# S03: Admin Portal & Docker/nginx Integration — UAT

**Milestone:** M009
**Written:** 2026-03-16

## UAT Type

- UAT mode: mixed (artifact-driven for config files + live-runtime for admin pages)
- Why this mode is sufficient: nginx config and docker-compose are artifact-verifiable. Admin page behavior requires a running Docker stack.

## Preconditions

- Docker stack running via `docker compose up -d` (api, frontend, triplestore containers healthy)
- At least one app installed via `AppManager.install()` (can use test-app from S07, or manually place a minimal app in `./apps/` and hit the install endpoint)
- Logged in as an owner-role user

## Smoke Test

Navigate to `/admin/apps` — page loads with the "Applications" heading and either an empty state or a list of installed apps with status badges.

## Test Cases

### 1. Admin sidebar shows Applications link (owner only)

1. Log in as an owner-role user
2. Navigate to any admin page (e.g. `/admin`)
3. Look at the left sidebar under the Admin group
4. **Expected:** "Applications" link visible with a puzzle icon, after "Operations Log"

### 2. Admin sidebar hides Applications for non-owners

1. Log in as a member-role user
2. Navigate to any page with the sidebar visible
3. **Expected:** No "Applications" link in the sidebar (entire Admin group hidden or Applications absent)

### 3. Admin index page shows Applications card

1. Navigate to `/admin`
2. Look at the dashboard cards grid
3. **Expected:** "Applications" card visible with description text and link to `/admin/apps`

### 4. App list page loads with installed apps

1. Ensure at least one app is installed (status: running or stopped)
2. Navigate to `/admin/apps`
3. **Expected:** Page shows app cards with:
   - App name and version pill
   - Status badge (green "running", gray "stopped", red "error", yellow "installing")
   - Uptime duration (for running apps)
   - PID (for running apps)
   - Quick-action buttons (Start/Stop/Restart/Uninstall)

### 5. App list page with no apps installed

1. Ensure no apps are installed (clean state)
2. Navigate to `/admin/apps`
3. **Expected:** Page shows install form and empty/no-apps message

### 6. htmx partial rendering for sidebar navigation

1. Navigate to `/admin/apps` via a full page load
2. Click a different admin link in the sidebar (e.g. "Operations Log")
3. Click "Applications" in the sidebar again
4. **Expected:** Only the content area updates (no full page reload). Page URL stays correct. The sidebar link highlights correctly.

### 7. App detail page shows full information

1. Navigate to `/admin/apps`
2. Click on an installed app name/card
3. **Expected:** Detail page at `/admin/apps/{app_id}` shows:
   - Back link to app list
   - Status stats bar (status, PID, uptime, restart count)
   - Permissions table (from app manifest)
   - Log viewer section (recent log output from ring buffer)
   - Action buttons appropriate to current status
   - Placeholder sections for "Task History" and "Renderer Assignments"

### 8. Start/Stop/Restart lifecycle actions

1. Navigate to detail page for a stopped app
2. Click "Start" button
3. **Expected:** App transitions to "running" status, page updates with PID and uptime
4. Click "Stop" button
5. **Expected:** App transitions to "stopped" status, PID clears
6. Click "Start" again, then "Restart"
7. **Expected:** App restarts (brief transition, new PID)

### 9. Uninstall action

1. Navigate to detail page for an installed app
2. Click "Uninstall" button
3. **Expected:** App is removed. Redirects to list page. App no longer appears in list.

### 10. Install flow

1. Place a valid app directory in `./apps/` (with manifest.json)
2. Navigate to `/admin/apps`
3. Use the install form/endpoint to install the app
4. **Expected:** App appears in the list with "installing" → "running" status transition

### 11. nginx serves app static assets

1. Install an app that has `frontend/static/` directory with a CSS or JS file
2. Request `GET /app-static/{app_id}/style.css` (or whatever file exists)
3. **Expected:** File served with correct content type and `Cache-Control: public, max-age=3600` header

### 12. nginx proxies /app/{appId}/ to API

1. With a running app that has routes
2. Request `GET /app/{app_id}/_health`
3. **Expected:** Request reaches the app's health endpoint through nginx → FastAPI → AppProxy → UDS chain. Response returns 200.

## Edge Cases

### Unknown app_id returns 404

1. Navigate to `/admin/apps/nonexistent-app-id`
2. **Expected:** HTTP 404 response (not a proxy error, not a 500)

### Install with invalid manifest

1. Place a directory in `./apps/` with an invalid `manifest.json` (e.g. missing required fields)
2. Attempt to install via POST `/admin/apps/install`
3. **Expected:** Error message displayed inline on the list page. No app entry created in DB.

### Install non-existent app directory

1. POST `/admin/apps/install` with an `app_dir` that doesn't exist
2. **Expected:** Error response, not a 500 traceback

### Route ordering verification

1. With `app_admin_router` and `app_proxy_router` both active
2. Request `GET /admin/apps`
3. **Expected:** Returns admin HTML page, NOT a proxy response from an app

## Failure Signals

- `/admin/apps` returns proxy response or 404 → router ordering is wrong (app_proxy_router shadows admin routes)
- `/admin/apps` returns 403 → role check failing, user not owner
- Static assets at `/app-static/` return 404 → nginx alias path wrong or sempkm_data volume not mounted on frontend
- App lifecycle actions return 500 → AppManager not on app.state or method signatures changed
- Sidebar missing "Applications" → template change not applied or user role check failing
- Detail page shows no logs → ring buffer empty or get_logs() returning wrong format

## Requirements Proved By This UAT

- APP-10 (partial) — Admin list and detail pages with status, permissions, logs, lifecycle actions. Task history and renderer assignments are placeholder.
- APP-14 (partial) — nginx locations, docker-compose mounts, static asset serving. Full Docker stack validation.

## Not Proven By This UAT

- APP-10 memory usage display (deferred to S07 when process monitoring is live)
- APP-10 task history section (S05 fills the placeholder)
- APP-10 renderer assignments section (S06 fills the placeholder)
- APP-14 runtime verification of `pip`/`venv` capability in api container (assumed from Dockerfile)
- Full end-to-end install → use → admin → uninstall flow (S07 E2E scope)

## Notes for Tester

- The Docker stack must be running for most tests. Config-file checks (nginx.conf, docker-compose.yml) can be done via grep without Docker.
- The install flow requires a valid app directory under `./apps/`. If no test app exists yet (S07 creates it), create a minimal one with just `manifest.json` containing required fields (id, name, version, description, author, permissions).
- The "Task History" and "Renderer Assignments" sections on the detail page intentionally show placeholder content — this is not a bug, it's deferred to S05 and S06.
- Lifecycle action buttons are conditional: "Start" only shown when stopped, "Stop"/"Restart" only when running. Check the button visibility matches the app's actual status.
