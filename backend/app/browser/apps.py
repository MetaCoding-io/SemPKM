"""Apps browser sub-router — explorer sidebar, dockview page wrapper,
dynamic right-pane sections, app view tabs, catalog browsing, and command
palette API.

Provides:
- ``GET /apps/explorer`` — HTML list of navigable pages from running apps
- ``GET /apps/{app_id}/page/{page_id}`` — dockview tab content with htmx
  fragment loading and app CSS/JS includes
- ``GET /apps/right-pane-sections`` — merged platform + app right-pane HTML
- ``GET /apps/views/explorer`` — HTML fragment of app view entries for Views sidebar
- ``GET /apps/{app_id}/view/{view_id}`` — dockview tab content for app views
- ``GET /apps/catalog`` — workspace catalog grid (all apps, installed + available)
- ``GET /apps/catalog/{app_id}`` — workspace catalog detail page
- ``GET /api/apps/commands`` — JSON array of command palette entries from running apps
"""

import logging
from urllib.parse import quote

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.apps.manifest import AppManifestSchema, parse_app_manifest
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.sparql.builder import safe_iri

logger = logging.getLogger(__name__)

apps_router = APIRouter(tags=["apps"])


@apps_router.get("/apps/explorer", response_class=HTMLResponse)
async def apps_explorer(request: Request):
    """Return the APPS sidebar section body.

    Lists pages from running apps that declare ``nav: "apps"`` in their
    manifest ``ui.pages`` entries.  Consumed by the APPS explorer section
    in workspace.html via htmx lazy-load.
    """
    app_registry = request.app.state.app_manager.registry
    app_manager = request.app.state.app_manager
    templates = request.app.state.templates

    app_pages: list[dict] = []

    for app_id in app_registry.list_apps():
        # Only include running apps
        try:
            status = await app_manager.get_status(app_id)
        except (ValueError, Exception):
            # App not in DB or status lookup failed — skip silently
            continue

        if status.get("status") != "running":
            continue

        manifest = app_registry.get_manifest(app_id)
        if manifest is None:
            continue

        for page in manifest.ui.pages:
            if page.nav == "apps":
                app_pages.append({
                    "app_id": app_id,
                    "app_name": manifest.name,
                    "page": page,
                })

    return templates.TemplateResponse(
        request,
        "browser/apps_explorer.html",
        {"request": request, "app_pages": app_pages},
    )


@apps_router.get("/apps/{app_id}/page/{page_id}", response_class=HTMLResponse)
async def app_page(request: Request, app_id: str, page_id: str):
    """Render the dockview tab content wrapper for an app page.

    Loads the app's fragment via htmx through the proxy chain
    (``/app/{app_id}/_fragments/{fragment}``), and includes the app's
    CSS and JS assets from the static asset path.
    """
    app_registry = request.app.state.app_manager.registry
    templates = request.app.state.templates

    manifest = app_registry.get_manifest(app_id)
    if manifest is None:
        logger.warning("App page request for unknown app: %s", app_id)
        raise HTTPException(404, detail=f"App {app_id} not found")

    # Find the matching page in the manifest
    target_page = None
    for page in manifest.ui.pages:
        if page.id == page_id:
            target_page = page
            break

    if target_page is None:
        logger.warning(
            "App page request for unknown page: %s in app %s", page_id, app_id
        )
        raise HTTPException(
            404, detail=f"Page {page_id} not found in app {app_id}"
        )

    fragment_url = f"/app/{app_id}/_fragments/{target_page.fragment}"
    css_urls = [f"/app-static/{app_id}/{css}" for css in manifest.frontend.css]
    js_urls = [f"/app-static/{app_id}/{js}" for js in manifest.frontend.js]

    return templates.TemplateResponse(
        request,
        "browser/app_page.html",
        {
            "request": request,
            "app_id": app_id,
            "page": target_page,
            "fragment_url": fragment_url,
            "css_urls": css_urls,
            "js_urls": js_urls,
        },
    )


@apps_router.get("/apps/right-pane-sections", response_class=HTMLResponse)
async def right_pane_sections(
    request: Request,
    iri: str = Query(..., description="Object IRI to load right pane for"),
):
    """Return merged platform + app right-pane sections HTML.

    Queries the object's ``rdf:type`` from the triplestore, then
    collects app contributions matching those types.  Platform sections
    (relations, lint, comments) are always included.
    """
    app_registry = request.app.state.app_manager.registry
    templates = request.app.state.templates

    encoded_iri = quote(iri, safe="")

    # Validate IRI before SPARQL interpolation
    try:
        safe = safe_iri(iri)
    except ValueError:
        logger.warning("right_pane_sections: rejected invalid IRI: %s", iri)
        return HTMLResponse(content="<p>Invalid IRI</p>", status_code=400)

    # --- Resolve object types from triplestore ---
    type_iris: list[str] = []
    try:
        ts_client = request.app.state.triplestore_client
        sparql = f"SELECT ?type WHERE {{ {safe} a ?type }}"
        result = await ts_client.query(sparql)
        type_iris = [
            row["type"]["value"]
            for row in result.get("results", {}).get("bindings", [])
            if "type" in row
        ]
    except Exception:
        logger.warning(
            "Failed to query types for <%s> — falling back to platform-only sections",
            iri,
        )

    # --- Collect app contributions ---
    app_sections: list[dict] = []
    try:
        app_sections = app_registry.get_right_pane_contributions(type_iris)
    except Exception:
        logger.warning(
            "Failed to collect app contributions for <%s>",
            iri,
        )

    logger.debug(
        "Right pane for <%s>: %d type(s), %d app section(s)",
        iri,
        len(type_iris),
        len(app_sections),
    )

    return templates.TemplateResponse(
        request,
        "browser/right_pane_sections.html",
        {
            "request": request,
            "iri": iri,
            "encoded_iri": encoded_iri,
            "app_sections": app_sections,
        },
    )


# ── Views explorer app contributions ─────────────────────────────────────


@apps_router.get("/apps/views/explorer", response_class=HTMLResponse)
async def views_explorer_apps(request: Request):
    """Return HTML fragment of app view entries for the Views sidebar.

    Queries the registry for running apps that declare ``ui.contributions.views``
    entries. Each view becomes a clickable tree-leaf that opens an app view tab.
    """
    app_registry = request.app.state.app_manager.registry
    app_manager = request.app.state.app_manager
    templates = request.app.state.templates

    app_views: list[dict] = []

    for app_id in app_registry.list_apps():
        try:
            status = await app_manager.get_status(app_id)
        except (ValueError, Exception):
            continue

        if status.get("status") != "running":
            continue

        manifest = app_registry.get_manifest(app_id)
        if manifest is None:
            continue

        for view in manifest.ui.contributions.views:
            app_views.append({
                "app_id": app_id,
                "app_name": manifest.name,
                "view": view,
            })

    logger.debug(
        "Views explorer: %d app view(s) from running apps", len(app_views)
    )

    return templates.TemplateResponse(
        request,
        "browser/app_views_explorer.html",
        {"request": request, "app_views": app_views},
    )


# ── App view tab content ─────────────────────────────────────────────────


@apps_router.get("/apps/{app_id}/view/{view_id}", response_class=HTMLResponse)
async def app_view_tab(request: Request, app_id: str, view_id: str):
    """Render the dockview tab content wrapper for an app view.

    Loads the app's view fragment via htmx through the proxy chain,
    and includes the app's CSS and JS assets.
    """
    app_registry = request.app.state.app_manager.registry
    templates = request.app.state.templates

    manifest = app_registry.get_manifest(app_id)
    if manifest is None:
        logger.warning("App view request for unknown app: %s", app_id)
        raise HTTPException(404, detail=f"App {app_id} not found")

    target_view = None
    for view in manifest.ui.contributions.views:
        if view.id == view_id:
            target_view = view
            break

    if target_view is None:
        logger.warning(
            "App view request for unknown view: %s in app %s", view_id, app_id
        )
        raise HTTPException(
            404, detail=f"View {view_id} not found in app {app_id}"
        )

    fragment_url = f"/app/{app_id}/_fragments/{target_view.fragment}"
    css_urls = [f"/app-static/{app_id}/{css}" for css in manifest.frontend.css]
    js_urls = [f"/app-static/{app_id}/{js}" for js in manifest.frontend.js]

    return templates.TemplateResponse(
        request,
        "browser/app_view_tab.html",
        {
            "request": request,
            "app_id": app_id,
            "view": target_view,
            "fragment_url": fragment_url,
            "css_urls": css_urls,
            "js_urls": js_urls,
        },
    )


# ── Workspace catalog ─────────────────────────────────────────────────────


def _format_uptime(seconds: float | None) -> str:
    """Format uptime_seconds into a human-readable string."""
    if seconds is None:
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


@apps_router.get("/apps/catalog", response_class=HTMLResponse)
async def catalog_list(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Render workspace catalog grid of all apps — installed + available on disk.

    Open to all authenticated users (no role restriction).
    """
    app_manager = request.app.state.app_manager
    templates = request.app.state.templates
    installed_ids = set(app_manager.registry.list_apps())

    apps: list[dict] = []

    # Installed apps
    for app_id in sorted(installed_ids):
        manifest = app_manager.registry.get_manifest(app_id)
        if manifest is None:
            continue
        try:
            status = await app_manager.get_status(app_id)
            app_status = status.get("status", "unknown")
            uptime = _format_uptime(status.get("uptime_seconds"))
        except (ValueError, Exception):
            app_status = "unknown"
            uptime = "—"

        apps.append({
            "app_id": app_id,
            "name": manifest.name,
            "description": manifest.description,
            "version": manifest.version,
            "category": manifest.category,
            "features": manifest.features,
            "status": app_status,
            "uptime": uptime,
            "author": manifest.author,
            "installed": True,
        })

    # Available (not-installed) apps on disk
    apps_dir = app_manager._apps_dir
    if apps_dir.is_dir():
        for child in sorted(apps_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest_path = child / "manifest.yaml"
            if not manifest_path.exists():
                continue
            candidate_id = child.name
            if candidate_id in installed_ids:
                continue
            try:
                with open(manifest_path) as f:
                    raw = yaml.safe_load(f)
                apps.append({
                    "app_id": candidate_id,
                    "name": raw.get("name", candidate_id),
                    "description": raw.get("description", ""),
                    "version": raw.get("version", "0.0.0"),
                    "category": raw.get("category", ""),
                    "features": raw.get("features", []),
                    "status": "not_installed",
                    "uptime": "—",
                    "author": raw.get("author"),
                    "installed": False,
                    "path": str(child),
                })
            except Exception as exc:
                logger.warning(
                    "Failed to parse manifest for %s: %s", candidate_id, exc
                )

    return templates.TemplateResponse(
        request,
        "browser/catalog_list.html",
        {"request": request, "apps": apps, "user": user},
    )


@apps_router.get("/apps/catalog/{app_id}", response_class=HTMLResponse)
async def catalog_detail(
    request: Request,
    app_id: str,
    user: User = Depends(get_current_user),
):
    """Render workspace catalog detail page for a single app.

    Open to all authenticated users. Install/uninstall actions are
    conditionally rendered for owner role only in the template.
    """
    app_manager = request.app.state.app_manager
    templates = request.app.state.templates
    installed_ids = set(app_manager.registry.list_apps())

    manifest = None
    app_status = "not_installed"
    uptime = "—"
    app_path = ""

    if app_id in installed_ids:
        manifest = app_manager.registry.get_manifest(app_id)
        if manifest is None:
            logger.warning("Catalog detail: manifest missing for installed app %s", app_id)
            raise HTTPException(404, detail=f"App '{app_id}' not found")
        try:
            status = await app_manager.get_status(app_id)
            app_status = status.get("status", "unknown")
            uptime = _format_uptime(status.get("uptime_seconds"))
        except (ValueError, Exception):
            app_status = "unknown"
    else:
        # Try loading from disk
        apps_dir = app_manager._apps_dir
        manifest_path = apps_dir / app_id / "manifest.yaml"
        if not manifest_path.exists():
            logger.warning("Catalog detail: unknown app_id %s", app_id)
            raise HTTPException(404, detail=f"App '{app_id}' not found")
        try:
            manifest = parse_app_manifest(str(manifest_path))
        except Exception as exc:
            logger.warning("Catalog detail: manifest parse error for %s: %s", app_id, exc)
            raise HTTPException(404, detail=f"Failed to load manifest for '{app_id}'")
        app_path = str(apps_dir / app_id)

    return templates.TemplateResponse(
        request,
        "browser/catalog_detail.html",
        {
            "request": request,
            "app_id": app_id,
            "manifest": manifest,
            "status": app_status,
            "uptime": uptime,
            "user": user,
            "installed": app_id in installed_ids,
            "app_path": app_path,
        },
    )


# ── Command palette API ──────────────────────────────────────────────────

# Separate router prefix for JSON API endpoints
app_commands_router = APIRouter(prefix="/api", tags=["apps"])


@app_commands_router.get("/apps/commands")
async def commands_list(request: Request):
    """Return JSON array of command palette entries from running apps.

    Each entry provides ``id``, ``title``, ``section``, ``actionType``, and
    ``actionUrl`` for the frontend to inject into ninja-keys.
    """
    app_registry = request.app.state.app_manager.registry
    app_manager = request.app.state.app_manager

    commands: list[dict] = []

    for app_id in app_registry.list_apps():
        try:
            status = await app_manager.get_status(app_id)
        except (ValueError, Exception):
            continue

        if status.get("status") != "running":
            continue

        manifest = app_registry.get_manifest(app_id)
        if manifest is None:
            continue

        for cmd in manifest.ui.contributions.commandPalette:
            action_url = ""
            if cmd.actionType == "dialog" and cmd.fragment:
                action_url = f"/app/{app_id}/_fragments/{cmd.fragment}"
            elif cmd.actionType == "post" and cmd.endpoint:
                action_url = f"/app/{app_id}/{cmd.endpoint.lstrip('/')}"
            elif cmd.actionType == "navigate" and cmd.path:
                action_url = cmd.path

            commands.append({
                "id": f"appcmd:{app_id}:{cmd.id}",
                "title": cmd.label,
                "keywords": cmd.keywords,
                "section": manifest.name,
                "actionType": cmd.actionType,
                "actionUrl": action_url,
            })

    logger.debug(
        "Command palette: %d app command(s) from running apps", len(commands)
    )

    return commands
