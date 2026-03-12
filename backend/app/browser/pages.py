"""Pages sub-router — docs, guide viewer, lint dashboard, and canvas."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_lint_service, get_shapes_service
from app.lint.service import LintService
from app.services.shapes import ShapesService

pages_router = APIRouter(tags=["pages"])


@pages_router.get("/docs")
async def docs_page(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Docs & Tutorials hub page rendered as a workspace tab fragment."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "browser/docs_page.html", {
        "user": user,
    })


@pages_router.get("/docs/guide/{filename:path}")
async def docs_guide_viewer(
    filename: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render a single guide markdown file as a workspace tab fragment."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "browser/docs_viewer.html", {
        "user": user,
        "filename": filename,
    })


@pages_router.get("/lint-dashboard")
async def lint_dashboard(
    request: Request,
    page: int = 1,
    severity: str | None = None,
    object_type: str | None = None,
    search: str | None = None,
    sort: str = "severity",
    user: User = Depends(get_current_user),
    lint_service: LintService = Depends(get_lint_service),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Render the global lint dashboard as an htmx partial for the bottom panel."""
    results = await lint_service.get_results(
        page=page, per_page=50, severity=severity,
        object_type=object_type, search=search, sort=sort,
    )
    status = await lint_service.get_status()
    types = await shapes_service.get_types()

    templates = request.app.state.templates
    return templates.TemplateResponse(request, "browser/lint_dashboard.html", {
        "results": results,
        "status": status,
        "types": types,
        "current_severity": severity or "",
        "current_type": object_type or "",
        "current_search": search or "",
        "current_sort": sort,
        "current_page": page,
    })


@pages_router.get("/canvas")
async def canvas_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Render the Spatial Canvas workspace tab (M0 prototype)."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "browser/canvas_page.html", {
        "request": request,
        "user": user,
    })
