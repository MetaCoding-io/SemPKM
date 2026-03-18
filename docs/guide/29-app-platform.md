# Chapter 29: App Platform

The **App Platform** lets you extend SemPKM with installable applications. Apps can add new pages to the workspace, contribute panels and views, override object renderers, run scheduled background tasks, and interact with the knowledge graph through a sandboxed SDK. The platform manages app lifecycle (install, start, stop, uninstall) and enforces a permissions model that limits what each app can access.

This chapter covers two perspectives: **managing apps** from the admin portal, and **building apps** with the SDK.

## Managing Apps

Apps are managed from the **Admin > Applications** page. This page lists all installed apps with their current status, and provides controls for installing, starting, stopping, and removing apps.

### The Applications Page

Navigate to **Admin > Applications** to see the apps management interface. The page shows:

- An **Install App** form at the top for adding new apps
- A card for each installed app showing its name, version, status badge, description, uptime, PID, and restart count
- Action buttons on each card for start, stop, and restart

### Installing an App

To install an app:

1. Enter the **absolute path** to the app's directory in the install form (e.g., `/app/apps/my-app`).
2. Click **Install**.
3. The platform validates the directory contains a valid `manifest.yaml`, reads the manifest, registers the app, and starts it.

If validation fails (missing manifest, invalid fields), an error message appears at the top of the page.

### App Status and Monitoring

Each app card displays a color-coded status badge:

| Status | Badge | Meaning |
|--------|-------|---------|
| Running | Green | App process is alive and responding to health checks |
| Stopped | Gray | App is installed but not running |
| Error | Red | App crashed or failed to start — check the error message |
| Installing | Blue | App is being set up (brief transitional state) |

The app detail page (click the app name) shows additional monitoring data:

- **PID** — the OS process ID of the running app
- **Uptime** — how long the app has been running since last start
- **Restart count** — how many times the platform has restarted the app (includes crash recovery restarts)
- **Error message** — if the app is in error state, the last error is displayed
- **Logs** — recent log output from the app process

### Starting, Stopping, and Restarting

From the app detail page:

- **Start** — available when the app is stopped or in error state. Launches the app process and runs the `on_startup` lifecycle hook.
- **Stop** — available when the app is running. Sends a shutdown signal, runs the `on_shutdown` hook, and terminates the process.
- **Restart** — available when the app is running. Stops and immediately restarts the app. Useful after configuration changes.

The platform includes automatic **crash recovery**: if a running app's process exits unexpectedly, the platform detects this and restarts it with exponential backoff (1s → 2s → 4s, up to a maximum).

### Task Monitoring

Apps can declare scheduled background tasks in their manifest. The app detail page shows a **Task History** section with:

- **Task configuration** — each declared task with its ID, description, default interval, and retry policy. You can override the interval or pause individual tasks from this panel.
- **Recent runs table** — a history of task executions showing task ID, start time, status (success/error/running), duration in milliseconds, and any error message.

### Uninstalling an App

Click the red **Uninstall** button on the app detail page. A confirmation dialog appears warning that the app will be stopped and its data removed. Confirm to proceed.

Uninstalling stops the running process, calls the `on_uninstall` lifecycle hook (if the app defines one), and removes the app's registration from the platform.

### Permissions Display

The app detail page shows a **Permissions** section listing commands, network domains, SPARQL access, and background task status.

## Building Apps with the SDK

The SemPKM App SDK (`sempkm_app_sdk`) provides the framework for building apps. Apps are Python packages with a manifest file, an entry point that defines handlers, and optional frontend assets.

### App Directory Structure

A typical app directory looks like this:

```
my-app/
├── manifest.yaml           # App metadata, permissions, UI declarations
├── app.py                  # Python entry point with App instance
├── requirements.txt        # Python dependencies (optional)
└── frontend/
    ├── static/
    │   ├── styles.css      # App-specific CSS
    │   └── app.js          # App-specific JavaScript
    └── templates/
        ├── main.html       # Jinja2 templates for fragment routes
        └── right-pane.html
```

### The Manifest File (manifest.yaml)

The manifest declares your app's identity, permissions, tasks, and UI integration points. Here is a condensed example based on the test app (see `apps/test-app/manifest.yaml` for the full version):

```yaml
appId: "test-app"
name: "Test Application"
version: "1.0.0"
description: "Comprehensive test app exercising all SDK features"

permissions:
  commands: ["object.create"]
  sparql: { read: true }
  backgroundTasks: true
  network: []

backend:
  entrypoint: "app:test_app"

tasks:
  - id: "heartbeat"
    description: "Periodic heartbeat check"
    interval: "5m"
    retryPolicy: { maxRetries: 1, maxBackoff: "10s" }

frontend:
  staticDir: "frontend/static"
  css: ["styles.css"]
  js: ["app.js"]

ui:
  pages:
    - id: "main"
      path: "/main"
      label: "Test App"
      icon: "flask-conical"
      nav: "apps"
      fragment: "main"
  contributions:
    rightPane:
      - id: "test-info"
        label: "Test Info"
        icon: "info"
        fragment: "right-pane"
        targetTypes: ["*"]
        priority: 50
    views:
      - id: "test-view"
        label: "Test View"
        icon: "test-tubes"
        fragment: "test-view"
    commandPalette:
      - id: "test-command"
        label: "Test App Command"
        keywords: ["test", "demo"]
        actionType: "dialog"
        fragment: "command-dialog"
  objectRenderers:
    - type: "urn:sempkm:test:TestRenderedType"
      modes: { read: "read-renderer" }
```

Key manifest fields:

| Field | Description |
|-------|-------------|
| `appId` | Unique identifier for the app (used in IRI prefixes, API paths) |
| `name` / `version` | Display name and semantic version |
| `permissions` | What the app is allowed to access (see Permissions section) |
| `backend.entrypoint` | Python `module:attribute` path to the `App` instance |
| `tasks` | Scheduled background tasks with interval and retry config |
| `frontend` | Static asset directory and CSS/JS files to inject |
| `ui.pages` | Standalone pages registered in the workspace navigation |
| `ui.contributions` | Panels, views, and command palette entries |
| `ui.objectRenderers` | Custom renderers for specific RDF types |

### The App Class and Decorators

Create an `App` instance and register handlers using decorators:

```python
from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse

app = App("my-app")

@app.on_startup
def on_startup(ctx: AppContext):
    print(f"App started: {ctx.app_id}")

@app.on_shutdown
def on_shutdown(ctx: AppContext):
    print(f"App stopped: {ctx.app_id}")

@app.route("/_fragments/main")
async def main_page(request: Request):
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("main.html"))

@app.task("heartbeat")
def heartbeat(ctx: AppContext):
    return {"status": "alive"}
```

Available decorators:

| Decorator | Signature | When it runs |
|-----------|-----------|-------------|
| `@app.on_install` | `fn(ctx: AppContext)` | Once, when the app is first installed |
| `@app.on_startup` | `fn(ctx: AppContext)` | Each time the app process starts |
| `@app.on_shutdown` | `fn(ctx: AppContext)` | Each time the app process stops |
| `@app.on_uninstall` | `fn(ctx: AppContext)` | Once, when the app is removed |
| `@app.route(path)` | `async fn(request: Request)` | On each HTTP request to the path |
| `@app.task(task_id)` | `fn(ctx: AppContext)` | On schedule, per manifest interval |

### AppContext and SDK Clients

Every handler receives an `AppContext` instance that provides scoped access to platform services. The context is available as `ctx` in lifecycle/task handlers, and as `request.app.state.ctx` in route handlers.

**Properties:**

| Property | Client | Description |
|----------|--------|-------------|
| `ctx.commands` | `CommandClient` | Execute platform commands (e.g., `object.create`). Enforces the `permissions.commands` whitelist. |
| `ctx.graph` | `GraphClient` | Run SPARQL SELECT queries against the knowledge graph. Gated by `permissions.sparql.read`. |
| `ctx.state` | `StateClient` | Key-value storage scoped to the app's named graph. Persists across restarts. |
| `ctx.settings` | `SettingsClient` | App settings (delegates to state client). |
| `ctx.http` | `HttpClient` | Make external HTTP requests. Restricted to domains listed in `permissions.network`. |

**Template rendering:**

```python
html = ctx.render_template("my-template.html", title="Hello", items=data)
```

Templates are loaded from `{app_dir}/frontend/templates/` using Jinja2 with autoescape enabled.

### Fragment Routes and Templates

Apps serve HTML fragments that the platform loads via htmx. Each route returns an HTML snippet (not a full page) that gets injected into the workspace. The `fragment` field in manifest UI declarations maps to these route paths — e.g., a page with `fragment: "main"` loads `/_fragments/main` from the app.

```python
@app.route("/_fragments/right-pane")
async def right_pane(request: Request):
    iri = request.query_params.get("iri", "unknown")
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("right-pane.html", iri=iri))
```

> **Tip:** Fragment routes receive the current object IRI as a query parameter (`?iri=...`) when used in contributions like right-pane panels or object renderers.

### Task Handlers

Task handlers are decorated with `@app.task(task_id)` where `task_id` matches a manifest `tasks` entry. They receive `AppContext` directly and return a dict with status information. The platform records results in the task history. If the handler raises an exception, the run is marked as failed and the manifest retry policy applies.

### Frontend Integration Levels

Apps can integrate with the workspace UI at three levels, from simplest to most deeply embedded:

#### Level 1: Standalone Pages

Declare a page under `ui.pages`. It appears in the workspace navigation and loads your fragment route in a full workspace tab. This is the simplest integration — your app gets its own page.

#### Level 2: Workspace Contributions

Contributions add content to existing workspace areas:

- **`rightPane`** — a tab in the right sidebar panel, showing contextual info about the selected object (receives `?iri=...`).
- **`views`** — a custom view type in the explorer's view list.
- **`commandPalette`** — entries in the command palette (Ctrl+K) that open dialogs or trigger actions.

#### Level 3: Object Renderer Overrides

Your app replaces the default read and/or edit renderer for specific RDF types. When a user opens an object of that type, your fragment renders instead of the built-in editor. Renderer assignments can be managed from the app detail page in the admin portal.

### Permissions

The app sandbox enforces permissions declared in the manifest. An app cannot exceed its declared permissions at runtime.

| Permission | Manifest Field | What It Controls |
|------------|---------------|-----------------|
| **Commands** | `permissions.commands` | Whitelist of platform commands the app can invoke. Any command not listed is rejected. |
| **IRI Prefix** | (automatic) | All IRIs created by the app are scoped to `urn:sempkm:app:{appId}:`. The SDK enforces this prefix. |
| **SPARQL Read** | `permissions.sparql.read` | Whether the app can query the knowledge graph. Set to `true` to enable. |
| **Network** | `permissions.network` | List of allowed external domains. An empty list (`[]`) means no external network access. |
| **Background Tasks** | `permissions.backgroundTasks` | Whether the app can run scheduled tasks. |

> **Tip:** Start with minimal permissions and add more as needed. The admin portal's Permissions section on the app detail page shows exactly what each app can access.

## See Also

- The `apps/test-app/` directory in the SemPKM repository is a complete working example exercising all SDK features.

---

**Previous:** [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md) | **Next:** [Appendix A: Environment Variables](appendix-a-environment-variables.md)
