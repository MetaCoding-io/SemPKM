"""Pages sub-router — docs, guide viewer, lint dashboard, and canvas."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_label_service, get_lint_filter_service, get_lint_service, get_shapes_service
from app.lint.filter_service import LintFilterService
from app.lint.service import LintService, _local_name
from app.services.labels import LabelService
from app.services.shapes import ShapesService

from ._helpers import get_hidden_types

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
    filter_service: LintFilterService = Depends(get_lint_filter_service),
):
    """Render the global lint dashboard as an htmx partial for the bottom panel."""
    suppressed_rules, dismissed_pairs = await filter_service.get_user_filters(user.id)
    results = await lint_service.get_results(
        page=page, per_page=50, severity=severity,
        object_type=object_type, search=search, sort=sort,
        detail=True,
        suppressed_rules=suppressed_rules or None,
        dismissed_pairs=dismissed_pairs or None,
    )
    status = await lint_service.get_status()
    types = await shapes_service.get_types(exclude_iris=get_hidden_types())
    active_presets = await filter_service.list_presets(user.id)

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
        "suppressed_count": len(suppressed_rules),
        "active_presets": active_presets,
    })


@pages_router.get("/lint-settings")
async def lint_settings(
    request: Request,
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
    label_service: LabelService = Depends(get_label_service),
):
    """Render the lint filter management section as an htmx partial."""
    suppressions = await filter_service.list_suppressions(user.id)
    dismissals = await filter_service.list_dismissals(user.id)
    presets = await filter_service.list_presets(user.id)

    # Collect all IRIs that need labels
    iris_to_resolve: list[str] = []
    for s in suppressions:
        iris_to_resolve.append(s.rule_source_iri)
    for d in dismissals:
        iris_to_resolve.append(d.rule_source_iri)
        iris_to_resolve.append(d.object_iri)

    # Batch-resolve labels
    labels: dict[str, str] = {}
    if iris_to_resolve:
        labels = await label_service.resolve_batch(iris_to_resolve)

    # Attach resolved labels to data objects for template use
    enriched_suppressions = []
    for s in suppressions:
        enriched_suppressions.append({
            "id": s.id,
            "rule_source_iri": s.rule_source_iri,
            "rule_label": _local_name(s.rule_source_iri),
            "created_at": s.created_at,
        })

    enriched_dismissals = []
    for d in dismissals:
        enriched_dismissals.append({
            "id": d.id,
            "object_iri": d.object_iri,
            "object_label": labels.get(d.object_iri, _local_name(d.object_iri)),
            "rule_source_iri": d.rule_source_iri,
            "rule_label": _local_name(d.rule_source_iri),
            "created_at": d.created_at,
        })

    templates = request.app.state.templates
    return templates.TemplateResponse(request, "browser/lint_settings.html", {
        "suppressions": enriched_suppressions,
        "dismissals": enriched_dismissals,
        "presets": presets,
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
