---
estimated_steps: 6
estimated_files: 6
---

# T01: App manifest, skeleton, and settings page shell

**Slice:** S01 — OAuth + App Skeleton + Linear Client
**Milestone:** M016

## Description

Creates the installable Linear Sync app foundation: manifest, Python entrypoint, HTML templates, CSS, and requirements file. This follows the exact patterns established by `apps/test-app/` — same manifest schema, same SDK integration points, same directory layout. After this task, the app can be installed via the admin portal and its settings page loads (showing an empty connect form).

## Steps

1. Create `apps/linear-sync/manifest.yaml` following `apps/test-app/manifest.yaml` structure:
   - `appId: "linear-sync"`, `name: "Linear Sync"`, `version: "0.1.0"`
   - `permissions.commands`: `["object.create", "object.patch", "body.set", "body.diff", "edge.create"]`
   - `permissions.sparql.read: true`
   - `permissions.backgroundTasks: true`
   - `permissions.network`: `["api.linear.app", "linear.app"]` (api.linear.app for GraphQL, linear.app for OAuth)
   - `backend.entrypoint: "app:linear_sync_app"`
   - `tasks`: one entry `poll-tasks` with interval `15m` and retry policy
   - `frontend.staticDir: "frontend/static"`, `css: ["styles.css"]`
   - `ui.pages`: one entry with `id: "settings"`, `path: "/settings"`, `label: "Linear Sync"`, `icon: "git-pull-request"`, `nav: "apps"`, `fragment: "connect"`

2. Create `apps/linear-sync/app.py`:
   - Import `App`, `AppContext` from `sempkm_app_sdk`
   - Create `linear_sync_app = App("linear-sync")`
   - Register `/_fragments/connect` GET route — placeholder returning "Connect to Linear" HTML
   - Register `/_fragments/connect/api-key` POST route — placeholder returning 501
   - Register `/_fragments/oauth-callback` GET route — placeholder returning 501
   - Register `/_fragments/connect/disconnect` POST route — placeholder returning 501
   - Register startup/shutdown lifecycle hooks with logging
   - The variable name `linear_sync_app` must match the manifest `backend.entrypoint` value `app:linear_sync_app`

3. Create `apps/linear-sync/requirements.txt` with comment `# SDK is injected by the platform — httpx available via SDK. No additional dependencies.`

4. Create `apps/linear-sync/services/__init__.py` (empty)

5. Create `apps/linear-sync/frontend/templates/connect.html`:
   - Two-section layout: "API Key" section with input field + "Connect" button (htmx POST to `/_fragments/connect/api-key`), and "OAuth" section with "Connect with Linear" link
   - Use htmx `hx-post`, `hx-target`, `hx-swap` attributes for the API key form
   - Include `id="connect-content"` wrapper div for htmx target swapping
   - Minimal but functional HTML — styling comes from styles.css

6. Create `apps/linear-sync/frontend/templates/connect_status.html`:
   - Shows: connected badge (green), auth method (API Key / OAuth), workspace name
   - Team list section (placeholder `{{ teams }}` loop)
   - Disconnect button with htmx POST to `/_fragments/connect/disconnect`

7. Create `apps/linear-sync/frontend/static/styles.css`:
   - Scope all rules under `.linear-sync-settings` to avoid conflicts
   - Connection status badge (green/red)
   - Form styling for API key input
   - Team list table styling
   - Follow the app CSS scoping pattern from the test-app

## Must-Haves

- [ ] `manifest.yaml` is valid YAML and includes all permission types needed by S02/S03 (object.create, object.patch, body.set, body.diff, edge.create)
- [ ] `app.py` exports `linear_sync_app` matching `backend.entrypoint: "app:linear_sync_app"`
- [ ] Connect fragment route registered at `/_fragments/connect`
- [ ] Templates render valid HTML (no unclosed tags, no Jinja syntax errors)
- [ ] `requirements.txt` exists (even if empty/comment-only)
- [ ] Directory structure matches: `apps/linear-sync/{manifest.yaml,app.py,requirements.txt,services/__init__.py,frontend/{templates/,static/}}`

## Verification

- `python3 -c "import yaml; yaml.safe_load(open('apps/linear-sync/manifest.yaml')); print('manifest OK')"` — valid YAML
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read()); print('app.py OK')"` — valid Python
- `python3 -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('apps/linear-sync/frontend/templates')); [env.get_template(t) for t in ['connect.html', 'connect_status.html']]; print('templates OK')"` — templates parse
- All 6 files/dirs exist in the expected locations

## Inputs

- `apps/test-app/manifest.yaml` — reference manifest structure
- `apps/test-app/app.py` — reference app.py pattern (App class, route decorator, lifecycle hooks)
- `backend/sdk/sempkm_app_sdk/app.py` — App class API (route, task, on_startup, on_shutdown decorators)
- `backend/sdk/sempkm_app_sdk/context.py` — AppContext with `render_template()` method for Jinja rendering

## Expected Output

- `apps/linear-sync/manifest.yaml` — complete app manifest
- `apps/linear-sync/app.py` — app skeleton with placeholder routes
- `apps/linear-sync/requirements.txt` — dependency declaration
- `apps/linear-sync/services/__init__.py` — empty package init
- `apps/linear-sync/frontend/templates/connect.html` — disconnected state UI
- `apps/linear-sync/frontend/templates/connect_status.html` — connected state UI
- `apps/linear-sync/frontend/static/styles.css` — scoped CSS
