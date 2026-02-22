"""View router for data browsing views (table, cards, graph).

Provides endpoints for listing available view specs per type, rendering
table views with sortable columns, pagination, and text filtering.
Views render as htmx partials into the #editor-area of the workspace.

Uses ViewSpecService for loading view specs and executing SPARQL queries,
and LabelService for resolving column header and row labels.
"""

import logging
from urllib.parse import unquote, quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.dependencies import get_label_service, get_view_spec_service
from app.services.labels import LabelService
from app.views.service import ViewSpecService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser/views", tags=["views"])


@router.get("/list/{type_iri:path}")
async def view_list(
    request: Request,
    type_iri: str,
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    label_service: LabelService = Depends(get_label_service),
):
    """List available view specs for a given type.

    Returns an HTML partial listing all view specs from ViewSpecService
    grouped by renderer type. Each entry links to its view endpoint
    via htmx for rendering into the editor area.
    """
    templates = request.app.state.templates
    decoded_iri = unquote(type_iri)

    specs = await view_spec_service.get_view_specs_for_type(decoded_iri)

    # Resolve type label
    type_labels = await label_service.resolve_batch([decoded_iri])
    type_label = type_labels.get(decoded_iri, decoded_iri)

    # Group specs by renderer type
    grouped: dict[str, list] = {}
    for spec in specs:
        rtype = spec.renderer_type
        if rtype not in grouped:
            grouped[rtype] = []
        grouped[rtype].append(spec)

    context = {
        "request": request,
        "type_iri": decoded_iri,
        "type_label": type_label,
        "grouped_specs": grouped,
        "specs": specs,
    }

    return templates.TemplateResponse(
        request, "browser/view_menu.html", context
    )


@router.get("/table/{spec_iri:path}")
async def table_view(
    request: Request,
    spec_iri: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: str = Query(default=""),
    dir: str = Query(default="asc"),
    filter: str = Query(default=""),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    label_service: LabelService = Depends(get_label_service),
):
    """Render a table view for a given view spec IRI.

    Calls ViewSpecService.execute_table_query() with pagination, sorting,
    and filtering parameters, then renders table_view.html as an htmx
    partial for the editor area.

    Column header labels are resolved via LabelService from the spec's
    column variable names mapped to property IRIs. Each row's ?s value
    links to open the object in a tab via openTab().
    """
    templates = request.app.state.templates
    decoded_iri = unquote(spec_iri)

    spec = await view_spec_service.get_view_spec_by_iri(decoded_iri)
    if not spec:
        return HTMLResponse(
            content='<div class="editor-empty"><p>View spec not found.</p></div>',
            status_code=404,
        )

    # Use spec's sort default if no sort specified
    effective_sort = sort if sort else spec.sort_default

    result = await view_spec_service.execute_table_query(
        spec=spec,
        page=page,
        page_size=page_size,
        sort_col=effective_sort,
        sort_dir=dir,
        filter_text=filter,
    )

    # Resolve column header labels from property IRIs in the view spec
    # Column names from spec are SPARQL variable names (title, status, etc.)
    # We need human-readable column headers
    column_labels: dict[str, str] = {}
    for col in result["columns"]:
        # Capitalize and clean up variable names as headers
        column_labels[col] = col.replace("_", " ").title()

    # Resolve labels for all object IRIs in rows (for clickable first column)
    obj_iris = [row["s"] for row in result["rows"] if row.get("s")]
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

    # Get all view specs for this type (for view type switcher)
    all_specs = await view_spec_service.get_view_specs_for_type(spec.target_class)

    # Resolve type label
    type_labels = await label_service.resolve_batch([spec.target_class])
    type_label = type_labels.get(spec.target_class, spec.target_class)

    # Build encoded spec IRI for URLs
    encoded_spec_iri = quote(decoded_iri, safe="")

    context = {
        "request": request,
        "spec": spec,
        "spec_iri_encoded": encoded_spec_iri,
        "rows": result["rows"],
        "columns": result["columns"],
        "column_labels": column_labels,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
        "sort_col": effective_sort,
        "sort_dir": dir,
        "current_filter": filter,
        "labels": labels,
        "all_specs": all_specs,
        "type_label": type_label,
        "type_iri": spec.target_class,
        "view_type": "table",
    }

    return templates.TemplateResponse(
        request, "browser/table_view.html", context
    )


@router.get("/cards/{spec_iri:path}")
async def cards_view(
    request: Request,
    spec_iri: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    filter: str = Query(default=""),
    group_by: str = Query(default=""),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    label_service: LabelService = Depends(get_label_service),
):
    """Render a cards view for a given view spec IRI.

    Calls ViewSpecService.execute_cards_query() with pagination, filtering,
    and optional grouping parameters, then renders cards_view.html as an
    htmx partial for the editor area.

    Cards show title and body snippet on the front, with all properties
    and relationships on the back via CSS 3D flip animation.
    """
    templates = request.app.state.templates
    decoded_iri = unquote(spec_iri)

    spec = await view_spec_service.get_view_spec_by_iri(decoded_iri)
    if not spec:
        return HTMLResponse(
            content='<div class="editor-empty"><p>View spec not found.</p></div>',
            status_code=404,
        )

    # Normalize empty group_by to None
    effective_group_by = group_by if group_by else None

    result = await view_spec_service.execute_cards_query(
        spec=spec,
        page=page,
        page_size=page_size,
        filter_text=filter,
        group_by=effective_group_by,
    )

    # Get all view specs for this type (for view type switcher)
    all_specs = await view_spec_service.get_view_specs_for_type(spec.target_class)

    # Resolve type label
    type_labels = await label_service.resolve_batch([spec.target_class])
    type_label = type_labels.get(spec.target_class, spec.target_class)

    # Build encoded spec IRI for URLs
    encoded_spec_iri = quote(decoded_iri, safe="")

    context = {
        "request": request,
        "spec": spec,
        "spec_iri_encoded": encoded_spec_iri,
        "cards": result["cards"],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
        "groups": result["groups"],
        "group_by": effective_group_by or "",
        "columns": result["columns"],
        "current_filter": filter,
        "sort_col": "",
        "sort_dir": "asc",
        "all_specs": all_specs,
        "type_label": type_label,
        "type_iri": spec.target_class,
        "view_type": "cards",
    }

    return templates.TemplateResponse(
        request, "browser/cards_view.html", context
    )
