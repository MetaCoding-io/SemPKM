"""View router for data browsing views (table, cards, graph).

Provides endpoints for listing available view specs per type, rendering
table views with sortable columns, pagination, and text filtering,
and graph views with Cytoscape.js visualization.
Views render as htmx partials into the #editor-area of the workspace.

Uses ViewSpecService for loading view specs and executing SPARQL queries,
and LabelService for resolving column header and row labels.
"""

import logging
from urllib.parse import unquote, quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_label_service, get_view_spec_service
from app.services.labels import LabelService
from app.views.service import ViewSpec, ViewSpecService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser/views", tags=["views"])

def _group_specs_by_type(specs: list[ViewSpec], labels: dict[str, str]) -> list[dict]:
    grouped: dict[str, list[ViewSpec]] = {}
    for spec in specs:
        type_iri = spec.target_class or ""
        if type_iri not in grouped:
            grouped[type_iri] = []
        grouped[type_iri].append(spec)

    groups: list[dict] = []
    for type_iri, spec_list in grouped.items():
        label = labels.get(type_iri, type_iri or "Unknown Type")
        spec_list.sort(key=lambda s: s.label)
        groups.append({
            "type_iri": type_iri,
            "type_label": label,
            "specs": spec_list,
        })

    groups.sort(key=lambda g: g["type_label"])
    return groups


@router.get("/available")
async def available_views(
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
):
    """Return all available view specs as JSON for the command palette."""
    specs = await view_spec_service.get_all_view_specs()
    payload = [
        {
            "spec_iri": spec.spec_iri,
            "label": spec.label,
            "renderer_type": spec.renderer_type,
            "target_class": spec.target_class,
        }
        for spec in specs
    ]
    return JSONResponse(content=payload)


@router.get("/explorer")
async def views_explorer(
    request: Request,
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    label_service: LabelService = Depends(get_label_service),
):
    """Render the views explorer tree grouped by model, then by type.

    Each model becomes a folder. Within each folder, types are listed as
    entries (one entry per target_class, default renderer = table).
    The carousel tab bar handles switching between table/card/graph renderers.
    A "Saved Views" folder at the bottom contains promoted query views.
    """
    templates = request.app.state.templates
    specs = await view_spec_service.get_all_view_specs()

    # Collect all IRIs needing labels (types + models)
    type_iris = {spec.target_class for spec in specs if spec.target_class}
    model_ids = {spec.source_model for spec in specs if spec.source_model}
    all_iris = list(type_iris | model_ids)
    labels = await label_service.resolve_batch(all_iris) if all_iris else {}

    # Group specs by model, then by target_class within each model
    # Each type appears once — the carousel handles renderer switching
    model_groups: dict[str, dict[str, list[ViewSpec]]] = {}
    for spec in specs:
        model_key = spec.source_model or "_other"
        if model_key not in model_groups:
            model_groups[model_key] = {}
        type_key = spec.target_class or "_untyped"
        if type_key not in model_groups[model_key]:
            model_groups[model_key][type_key] = []
        model_groups[model_key][type_key].append(spec)

    # Build structured groups for the template
    groups = []
    for model_key, types in sorted(model_groups.items(), key=lambda x: labels.get(x[0], x[0])):
        model_label = labels.get(model_key, model_key.replace("-", " ").title()) if model_key != "_other" else "Other Views"
        type_entries = []
        for type_key, type_specs in sorted(types.items(), key=lambda x: labels.get(x[0], x[0])):
            type_label = labels.get(type_key, type_key) if type_key != "_untyped" else "Untyped"
            # Find default spec (prefer table, then first available)
            default_spec = next((s for s in type_specs if s.renderer_type == "table"), type_specs[0])
            type_entries.append({
                "type_iri": type_key,
                "type_label": type_label,
                "specs": type_specs,
                "default_spec": default_spec,
                "renderer_types": sorted({s.renderer_type for s in type_specs}),
            })
        groups.append({
            "model_id": model_key,
            "model_label": model_label,
            "types": type_entries,
        })

    context = {
        "request": request,
        "groups": groups,
    }
    return templates.TemplateResponse(
        request, "browser/views_explorer.html", context
    )


@router.get("/menu")
async def views_menu(
    request: Request,
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    label_service: LabelService = Depends(get_label_service),
):
    """Render a full view menu listing all views across types."""
    templates = request.app.state.templates
    specs = await view_spec_service.get_all_view_specs()

    type_iris = {spec.target_class for spec in specs if spec.target_class}
    labels = await label_service.resolve_batch(list(type_iris)) if type_iris else {}
    groups = _group_specs_by_type(specs, labels) if specs else []

    context = {
        "request": request,
        "groups": groups,
    }
    return templates.TemplateResponse(
        request, "browser/views_menu.html", context
    )


@router.get("/list/{type_iri:path}")
async def view_list(
    request: Request,
    type_iri: str,
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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

    spec = await view_spec_service.get_view_spec_by_iri(
        decoded_iri, user_id=user.id,
    )
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

    # For user views: skip type switcher and use "Custom View" label
    if spec.source_model == "user":
        all_specs: list[ViewSpec] = []
        type_label = "Custom View"
        labels: dict[str, str] = {}
    else:
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
        "source_model": spec.source_model,
    }

    return templates.TemplateResponse(
        request, "browser/table_view.html", context
    )


@router.get("/card/{spec_iri:path}")
async def cards_view(
    request: Request,
    spec_iri: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    filter: str = Query(default=""),
    group_by: str = Query(default=""),
    user: User = Depends(get_current_user),
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

    spec = await view_spec_service.get_view_spec_by_iri(
        decoded_iri, user_id=user.id,
    )
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

    # For user views: skip type switcher and use "Custom View" label
    if spec.source_model == "user":
        all_specs: list[ViewSpec] = []
        type_label = "Custom View"
    else:
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
        "view_type": "card",
        "source_model": spec.source_model,
    }

    return templates.TemplateResponse(
        request, "browser/cards_view.html", context
    )


@router.get("/graph/{spec_iri:path}/data")
async def graph_data(
    request: Request,
    spec_iri: str,
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
):
    """Return graph data as JSON for Cytoscape.js visualization.

    Returns {nodes, edges, type_colors} as application/json.
    This endpoint is fetched by graph.js after the container is rendered
    (per Research Pitfall 2: container must be visible before Cytoscape init).
    """
    decoded_iri = unquote(spec_iri)

    spec = await view_spec_service.get_view_spec_by_iri(
        decoded_iri, user_id=user.id,
    )
    if not spec:
        return JSONResponse(
            content={"nodes": [], "edges": [], "type_colors": {}},
            status_code=404,
        )

    result = await view_spec_service.execute_graph_query(spec)
    return JSONResponse(content=result)


@router.get("/graph/expand/{node_iri:path}")
async def graph_expand(
    request: Request,
    node_iri: str,
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
):
    """Return neighbor nodes and edges for expansion in the graph.

    Called by Cytoscape double-click handler to expand a node's neighbors.
    Returns {nodes, edges, type_colors} as application/json.
    """
    decoded_iri = unquote(node_iri)
    result = await view_spec_service.expand_neighbors(decoded_iri)
    return JSONResponse(content=result)


@router.get("/graph/{spec_iri:path}")
async def graph_view(
    request: Request,
    spec_iri: str,
    filter: str = Query(default=""),
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    label_service: LabelService = Depends(get_label_service),
):
    """Render the graph view container with Cytoscape.js initialization.

    The graph data is NOT included in the HTML -- it is loaded via a
    separate JSON endpoint (/data) after the DOM is ready, per Research
    Pitfall 2 (container must be visible before Cytoscape init).
    """
    templates = request.app.state.templates
    decoded_iri = unquote(spec_iri)

    spec = await view_spec_service.get_view_spec_by_iri(
        decoded_iri, user_id=user.id,
    )
    if not spec:
        return HTMLResponse(
            content='<div class="editor-empty"><p>View spec not found.</p></div>',
            status_code=404,
        )

    # For user views: skip type switcher and use "Custom View" label
    if spec.source_model == "user":
        all_specs: list[ViewSpec] = []
        type_label = "Custom View"
    else:
        # Get all view specs for this type (for view type switcher)
        all_specs = await view_spec_service.get_view_specs_for_type(spec.target_class)

        # Resolve type label
        type_labels = await label_service.resolve_batch([spec.target_class])
        type_label = type_labels.get(spec.target_class, spec.target_class)

    # Build available layouts: 3 built-in + model-contributed
    built_in_layouts = [
        {"name": "fcose", "label": "Force-Directed"},
        {"name": "dagre", "label": "Hierarchical"},
        {"name": "concentric", "label": "Radial"},
    ]
    model_layouts = await view_spec_service.get_model_layouts()

    available_layouts = built_in_layouts + model_layouts

    # Build encoded spec IRI for data endpoint URL
    encoded_spec_iri = quote(decoded_iri, safe="")

    # Pre-fetch type colors for initial styling (will be updated when data loads)
    type_colors = {}

    context = {
        "request": request,
        "spec": spec,
        "spec_iri": decoded_iri,
        "spec_iri_encoded": encoded_spec_iri,
        "all_specs": all_specs,
        "type_label": type_label,
        "type_iri": spec.target_class,
        "available_layouts": available_layouts,
        "type_colors": type_colors,
        "sort_col": "",
        "sort_dir": "asc",
        "current_filter": filter,
    }

    return templates.TemplateResponse(
        request, "browser/graph_view.html", context
    )
