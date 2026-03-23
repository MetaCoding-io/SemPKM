"""Admin portal routes for app platform management.

Serves Jinja2 templates with htmx partial rendering for the
/admin/apps list and detail pages.  All endpoints require the
``owner`` role.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.apps.models import AppRendererPref, AppTaskConfig, AppTaskRun
from app.apps.scheduler import parse_interval_seconds
from app.auth.dependencies import require_role
from app.auth.models import User

logger = logging.getLogger(__name__)

app_admin_router = APIRouter(tags=["app-management"])


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"


def _templates_response(
    request: Request,
    template: str,
    context: dict,
    block_name: str | None = None,
):
    """Render a template with optional block-level rendering."""
    templates = request.app.state.templates
    if block_name:
        return templates.TemplateResponse(request, template, context, block_name=block_name)
    return templates.TemplateResponse(request, template, context)


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


# ──────────────────────────────────────────────
# List page
# ──────────────────────────────────────────────


@app_admin_router.get("/admin/apps")
async def admin_apps_list(
    request: Request,
    user: User = Depends(require_role("owner")),
):
    """Render the app list page with status badges for each installed app."""
    app_manager = request.app.state.app_manager
    app_ids = app_manager.registry.list_apps()

    apps = []
    for app_id in app_ids:
        try:
            status = await app_manager.get_status(app_id)
        except ValueError:
            status = {"app_id": app_id, "status": "not_found"}
        manifest = app_manager.registry.get_manifest(app_id)
        apps.append({
            "app_id": app_id,
            "status": status.get("status", "unknown"),
            "pid": status.get("pid"),
            "uptime": _format_uptime(status.get("uptime_seconds")),
            "restart_count": status.get("restart_count", 0),
            "error_message": status.get("error_message"),
            "version": status.get("version", manifest.version if manifest else "?"),
            "name": manifest.name if manifest else app_id,
            "description": manifest.description if manifest else "",
            "category": manifest.category if manifest else "",
        })

    # Discover available (not yet installed) apps on disk
    available_apps = []
    installed_ids = set(app_ids)
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
            # Parse minimal manifest info for display
            try:
                import yaml
                with open(manifest_path) as f:
                    raw = yaml.safe_load(f)
                available_apps.append({
                    "app_id": candidate_id,
                    "name": raw.get("name", candidate_id),
                    "description": raw.get("description", ""),
                    "version": raw.get("version", "0.0.0"),
                    "path": str(child),
                })
            except Exception as exc:
                logger.warning("Failed to parse manifest for %s: %s", candidate_id, exc)
                available_apps.append({
                    "app_id": candidate_id,
                    "name": candidate_id,
                    "description": f"(manifest parse error: {exc})",
                    "version": "?",
                    "path": str(child),
                })

    context = {
        "request": request,
        "apps": apps,
        "available_apps": available_apps,
        "user": user,
        "active_page": "admin",
    }

    # Check for flash messages via query params
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    if success:
        context["success"] = success
    if error:
        context["error"] = error

    if _is_htmx_request(request):
        return _templates_response(
            request, "admin/apps/list.html", context, block_name="content"
        )
    return _templates_response(request, "admin/apps/list.html", context)


# ──────────────────────────────────────────────
# Detail page
# ──────────────────────────────────────────────


@app_admin_router.get("/admin/apps/{app_id}")
async def admin_app_detail(
    request: Request,
    app_id: str,
    user: User = Depends(require_role("owner")),
):
    """Render the detail page for a single app with status, logs, and actions."""
    app_manager = request.app.state.app_manager
    manifest = app_manager.registry.get_manifest(app_id)

    try:
        status = await app_manager.get_status(app_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"App '{app_id}' not found")

    logs = app_manager.get_logs(app_id)

    # Load task runs and configs for the task history section
    task_runs: list[AppTaskRun] = []
    task_configs: dict[str, AppTaskConfig] = {}
    session_factory = request.app.state.async_session_factory
    async with session_factory() as session:
        runs_result = await session.execute(
            select(AppTaskRun)
            .where(AppTaskRun.app_id == app_id)
            .order_by(AppTaskRun.started_at.desc())
            .limit(20)
        )
        task_runs = list(runs_result.scalars().all())

        if manifest and manifest.tasks:
            for task in manifest.tasks:
                config = await session.get(AppTaskConfig, (app_id, task.id))
                if config:
                    task_configs[task.id] = config

    # Collect renderer assignment status for each declared renderer
    renderer_assignments: list[dict] = []
    has_renderers = False
    if manifest and manifest.ui.objectRenderers:
        has_renderers = True
        async with session_factory() as session:
            for renderer in manifest.ui.objectRenderers:
                for mode_name, fragment in [("read", renderer.modes.read), ("edit", renderer.modes.edit)]:
                    if not fragment:
                        continue
                    pref = await session.get(AppRendererPref, (renderer.type, mode_name))
                    if pref and pref.app_id == app_id:
                        rend_status = "active"
                        active_app_id = None
                    elif pref:
                        rend_status = "overridden"
                        active_app_id = pref.app_id
                    else:
                        rend_status = "default"
                        active_app_id = None
                    renderer_assignments.append({
                        "type_iri": renderer.type,
                        "type_label": renderer.type.rsplit("/", 1)[-1].rsplit("#", 1)[-1],
                        "mode": mode_name,
                        "status": rend_status,
                        "active_app_id": active_app_id,
                    })

    context = {
        "request": request,
        "app_id": app_id,
        "status": status,
        "manifest": manifest,
        "logs": logs,
        "uptime": _format_uptime(status.get("uptime_seconds")),
        "user": user,
        "active_page": "admin",
        "task_runs": task_runs,
        "task_configs": task_configs,
        "renderer_assignments": renderer_assignments,
        "has_renderers": has_renderers,
    }

    if _is_htmx_request(request):
        return _templates_response(
            request, "admin/apps/detail.html", context, block_name="content"
        )
    return _templates_response(request, "admin/apps/detail.html", context)


# ──────────────────────────────────────────────
# Install
# ──────────────────────────────────────────────


@app_admin_router.post("/admin/apps/install")
async def admin_apps_install(
    request: Request,
    user: User = Depends(require_role("owner")),
    app_path: str = Form(...),
):
    """Install an app from a filesystem path and redirect to list."""
    app_manager = request.app.state.app_manager
    try:
        result = await app_manager.install(Path(app_path))
        logger.info(
            "App installed: %s (by user %s)", result.get("app_id", app_path), user.email
        )
        return RedirectResponse(
            url=f"/admin/apps?success=App+installed+successfully",
            status_code=303,
        )
    except (ValueError, RuntimeError) as exc:
        logger.warning("App install failed for path '%s': %s", app_path, exc)
        return RedirectResponse(
            url=f"/admin/apps?error={exc}",
            status_code=303,
        )


# ──────────────────────────────────────────────
# Lifecycle actions
# ──────────────────────────────────────────────


@app_admin_router.post("/admin/apps/{app_id}/start")
async def admin_app_start(
    request: Request,
    app_id: str,
    user: User = Depends(require_role("owner")),
):
    """Start an app subprocess."""
    app_manager = request.app.state.app_manager
    await app_manager.start(app_id)
    logger.info("App started: %s (by user %s)", app_id, user.email)

    if _is_htmx_request(request):
        return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)
    return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)


@app_admin_router.post("/admin/apps/{app_id}/stop")
async def admin_app_stop(
    request: Request,
    app_id: str,
    user: User = Depends(require_role("owner")),
):
    """Stop an app subprocess."""
    app_manager = request.app.state.app_manager
    await app_manager.stop(app_id)
    logger.info("App stopped: %s (by user %s)", app_id, user.email)

    if _is_htmx_request(request):
        return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)
    return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)


@app_admin_router.post("/admin/apps/{app_id}/restart")
async def admin_app_restart(
    request: Request,
    app_id: str,
    user: User = Depends(require_role("owner")),
):
    """Restart an app subprocess."""
    app_manager = request.app.state.app_manager
    await app_manager.restart(app_id)
    logger.info("App restarted: %s (by user %s)", app_id, user.email)

    if _is_htmx_request(request):
        return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)
    return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)


@app_admin_router.post("/admin/apps/{app_id}/uninstall")
async def admin_app_uninstall(
    request: Request,
    app_id: str,
    user: User = Depends(require_role("owner")),
    clean_data: bool = Form(False),
):
    """Uninstall an app and redirect to list."""
    app_manager = request.app.state.app_manager
    await app_manager.uninstall(app_id, clean_data=clean_data)
    logger.info(
        "App uninstalled: %s (by user %s, clean_data=%s)",
        app_id,
        user.email,
        clean_data,
    )

    return RedirectResponse(
        url="/admin/apps?success=App+uninstalled+successfully",
        status_code=303,
    )


# ──────────────────────────────────────────────
# Task history & config
# ──────────────────────────────────────────────


@app_admin_router.get("/admin/apps/{app_id}/tasks")
async def admin_app_tasks(
    request: Request,
    app_id: str,
    user: User = Depends(require_role("owner")),
):
    """Return recent task runs for an app as JSON."""
    session_factory = request.app.state.async_session_factory
    async with session_factory() as session:
        result = await session.execute(
            select(AppTaskRun)
            .where(AppTaskRun.app_id == app_id)
            .order_by(AppTaskRun.started_at.desc())
            .limit(50)
        )
        runs = result.scalars().all()

    return JSONResponse([
        {
            "id": run.id,
            "task_id": run.task_id,
            "run_id": run.run_id,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "status": run.status,
            "duration_ms": run.duration_ms,
            "error_message": run.error_message,
        }
        for run in runs
    ])


@app_admin_router.post("/admin/apps/{app_id}/tasks/{task_id}/config")
async def admin_app_task_config(
    request: Request,
    app_id: str,
    task_id: str,
    user: User = Depends(require_role("owner")),
    interval: str | None = Form(None),
    paused: bool = Form(False),
):
    """Update task scheduling config (interval override, pause toggle)."""
    # Validate interval if provided
    if interval:
        interval = interval.strip()
        if interval:
            try:
                parse_interval_seconds(interval)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        else:
            interval = None

    session_factory = request.app.state.async_session_factory
    async with session_factory() as session:
        config = await session.get(AppTaskConfig, (app_id, task_id))
        if config is None:
            config = AppTaskConfig(
                app_id=app_id,
                task_id=task_id,
                interval_override=interval,
                paused=paused,
            )
            session.add(config)
        else:
            config.interval_override = interval
            config.paused = paused
        await session.commit()

    logger.info(
        "Task config updated: %s/%s (interval=%s, paused=%s, by %s)",
        app_id, task_id, interval, paused, user.email,
    )

    if _is_htmx_request(request):
        return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)
    return JSONResponse({"status": "ok", "app_id": app_id, "task_id": task_id})


# ──────────────────────────────────────────────
# Renderer preference management
# ──────────────────────────────────────────────


@app_admin_router.post("/admin/apps/{app_id}/renderers/set")
async def admin_app_renderer_set(
    request: Request,
    app_id: str,
    user: User = Depends(require_role("owner")),
    type_iri: str = Form(...),
    mode: str = Form("read"),
):
    """Set this app as the preferred renderer for (type_iri, mode).

    Upserts an ``AppRendererPref`` row.  If a row already exists for the
    (type_iri, mode) pair, the ``app_id`` is overwritten.
    """
    app_manager = request.app.state.app_manager
    manifest = app_manager.registry.get_manifest(app_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"App '{app_id}' not found")

    session_factory = request.app.state.async_session_factory
    async with session_factory() as session:
        pref = await session.get(AppRendererPref, (type_iri, mode))
        if pref is None:
            pref = AppRendererPref(type_iri=type_iri, mode=mode, app_id=app_id)
            session.add(pref)
        else:
            pref.app_id = app_id
        await session.commit()

    logger.info(
        "Renderer pref set: type=%s mode=%s app=%s (by %s)",
        type_iri, mode, app_id, user.email,
    )

    return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)


@app_admin_router.post("/admin/apps/{app_id}/renderers/clear")
async def admin_app_renderer_clear(
    request: Request,
    app_id: str,
    user: User = Depends(require_role("owner")),
    type_iri: str = Form(...),
    mode: str = Form("read"),
):
    """Clear the renderer preference for (type_iri, mode).

    Idempotent — returns success even when no row exists.
    """
    session_factory = request.app.state.async_session_factory
    async with session_factory() as session:
        pref = await session.get(AppRendererPref, (type_iri, mode))
        if pref is not None:
            await session.delete(pref)
            await session.commit()
            logger.info(
                "Renderer pref cleared: type=%s mode=%s (was app=%s, by %s)",
                type_iri, mode, pref.app_id, user.email,
            )
        else:
            logger.debug(
                "Renderer pref clear (no-op): type=%s mode=%s (by %s)",
                type_iri, mode, user.email,
            )

    return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)
