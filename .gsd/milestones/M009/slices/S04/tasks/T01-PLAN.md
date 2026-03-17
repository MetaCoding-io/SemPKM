---
estimated_steps: 7
estimated_files: 5
---

# T01: Browser sub-router, templates, and workspace wiring

**Slice:** S04 — Frontend Level 1 — Standalone Pages & Sidebar
**Milestone:** M009

## Description

Create the browser sub-router for app pages (`backend/app/browser/apps.py`) with two endpoints, two Jinja2 templates, register the router in the browser coordinator, and add the APPS sidebar section to workspace.html. This is the full server-side layer for standalone app pages.

## Steps

1. Create `backend/app/browser/apps.py` with an `apps_router = APIRouter()` containing two endpoints:

   **`GET /apps/explorer`** — the sidebar section body:
   - Get `app_registry` from `request.app.state.app_registry` and `app_manager` from `request.app.state.app_manager`
   - For each app_id in `app_registry.list_apps()`, call `await app_manager.get_status(app_id)` — keep only apps where `status["status"] == "running"`
   - For each running app, get the manifest via `app_registry.get_manifest(app_id)` and collect pages from `manifest.ui.pages` where `page.nav == "apps"`
   - Build a list of dicts: `{"app_id": app_id, "app_name": manifest.name, "page": page}` for each qualifying page
   - Return `templates.TemplateResponse("browser/apps_explorer.html", {"request": request, "app_pages": app_pages})`

   **`GET /apps/{app_id}/page/{page_id}`** — the dockview tab content wrapper:
   - Get the manifest from `request.app.state.app_registry.get_manifest(app_id)` — if None, raise `HTTPException(404, detail=f"App {app_id} not found")`
   - Find the page in `manifest.ui.pages` where `page.id == page_id` — if not found, raise `HTTPException(404, detail=f"Page {page_id} not found in app {app_id}")`
   - Build `fragment_url = f"/app/{app_id}/_fragments/{page.fragment}"`
   - Build CSS list: `[f"/app-static/{app_id}/{css}" for css in manifest.frontend.css]`
   - Build JS list: `[f"/app-static/{app_id}/{js}" for js in manifest.frontend.js]`
   - Return `templates.TemplateResponse("browser/app_page.html", {"request": request, "app_id": app_id, "page": page, "fragment_url": fragment_url, "css_urls": css_urls, "js_urls": js_urls})`

   Use `Jinja2Blocks` for the templates instance (same as other browser sub-modules). Add `import logging` and a logger `logger = logging.getLogger(__name__)`.

2. Create `backend/app/templates/browser/apps_explorer.html`:
   ```html
   {# APPS explorer section body — lists pages from running apps.
      Rendered by GET /browser/apps/explorer.
      Context: app_pages — list of {app_id, app_name, page} dicts #}

   {% if app_pages %}
     {% for entry in app_pages %}
     <div class="tree-leaf"
          onclick="openAppPageTab('{{ entry.app_id }}', '{{ entry.page.id }}', '{{ entry.page.label | e }}')">
       <i data-lucide="{{ entry.page.icon }}" class="tree-icon"></i>
       <span class="tree-label" title="{{ entry.app_name | e }} — {{ entry.page.label | e }}">{{ entry.page.label }}</span>
     </div>
     {% endfor %}
   {% else %}
     <div class="tree-empty">No apps installed</div>
   {% endif %}
   ```

3. Create `backend/app/templates/browser/app_page.html`:
   ```html
   {# App page dockview tab content.
      Loads app fragment via htmx from the proxy chain.
      Context: app_id, page, fragment_url, css_urls, js_urls #}

   {% for css in css_urls %}
   <link rel="stylesheet" href="{{ css }}">
   {% endfor %}

   <div class="app-page-content"
        hx-get="{{ fragment_url }}"
        hx-trigger="load"
        hx-swap="innerHTML">
     <div class="tree-empty">Loading {{ page.label | e }}...</div>
   </div>

   {% for js in js_urls %}
   <script src="{{ js }}"></script>
   {% endfor %}
   ```

4. Register `apps_router` in `backend/app/browser/router.py`. Import: `from .apps import apps_router`. Include it **before** `objects_router` — put it after `sparql_result_router` and before `objects_router` in both the import list and the include calls. This is critical: objects_router has a `{iri:path}` catch-all that would consume `/apps/` URLs (D052, D058, D136 pattern).

5. Add the APPS explorer section to `backend/app/templates/browser/workspace.html`. Insert it between the WORKFLOWS section's closing `</div>` and the `{% include "browser/partials/shared_nav_section.html" %}` line. Follow the DASHBOARDS/WORKFLOWS pattern:
   ```html
   <div class="explorer-section" id="section-apps" data-panel-name="apps">
       <div class="explorer-section-header" draggable="true"
            onclick="this.parentElement.classList.toggle('expanded')">
           <i data-lucide="grip-vertical" class="panel-grip"></i>
           <i data-lucide="chevron-right" class="explorer-section-chevron"></i>
           <span class="explorer-section-title">APPS</span>
       </div>
       <div class="explorer-section-body" id="apps-tree"
            hx-get="/browser/apps/explorer"
            hx-trigger="load, appsRefreshed from:body"
            hx-swap="innerHTML">
           <div class="tree-empty">Loading apps...</div>
       </div>
   </div>
   ```

6. Verify syntax of all created/modified Python files with `python3 -c "import ast; ast.parse(open(f).read())"`.

7. Verify router include order: `grep -n "include_router" backend/app/browser/router.py` — `apps_router` must appear before `objects_router`.

## Must-Haves

- [ ] `GET /apps/explorer` returns HTML listing pages from running apps with `nav == "apps"`
- [ ] `GET /apps/{app_id}/page/{page_id}` returns page wrapper with correct proxy fragment URL and CSS/JS includes
- [ ] 404 responses for unknown app or page with descriptive detail message
- [ ] `apps_router` registered before `objects_router` in `browser/router.py`
- [ ] APPS section in workspace.html with htmx lazy-load on `load, appsRefreshed from:body`

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/browser/apps.py').read())"` — no SyntaxError
- `grep -c "apps_router" backend/app/browser/router.py` → 2 (import + include)
- `grep -c "APPS" backend/app/templates/browser/workspace.html` → at least 1
- `grep -n "include_router" backend/app/browser/router.py` shows apps_router before objects_router

## Observability Impact

- **Logger:** `app.browser.apps` logs WARNING on unknown app_id or page_id lookups (page miss)
- **Inspection:** `GET /browser/apps/explorer` returns HTML list of app pages visible in sidebar — can be fetched directly to verify running app state
- **Failure:** 404 responses with descriptive `detail` messages for unknown app or page — visible in browser network tab and server logs
- **htmx event:** `appsRefreshed` custom event on `<body>` triggers sidebar refresh — allows downstream code to signal app state changes

## Inputs

- `backend/app/browser/router.py` — existing browser router coordinator, sub-router include pattern
- `backend/app/templates/browser/dashboard_explorer.html` — template pattern for explorer section body
- `backend/app/templates/browser/workspace.html` — sidebar section pattern (DASHBOARDS, WORKFLOWS)
- `backend/app/apps/manifest.py` — `AppManifestSchema` with `ui.pages` (list of `AppPage`: id, path, label, icon, nav, fragment) and `frontend` (css, js lists)
- `backend/app/apps/registry.py` — `AppRegistry` with `list_apps()`, `get_manifest(app_id)`
- `backend/app/apps/manager.py` — `AppManager` with `get_status(app_id)` returning dict with `status` key

## Expected Output

- `backend/app/browser/apps.py` — new browser sub-router with 2 endpoints
- `backend/app/templates/browser/apps_explorer.html` — new explorer section template
- `backend/app/templates/browser/app_page.html` — new dockview tab content template
- `backend/app/browser/router.py` — modified: import + include apps_router before objects_router
- `backend/app/templates/browser/workspace.html` — modified: APPS section added between WORKFLOWS and shared_nav_section
