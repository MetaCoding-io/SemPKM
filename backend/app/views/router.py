"""View router for data browsing views (table, cards, graph).

Provides endpoints for listing available view specs per type, rendering
table views with sortable columns, pagination, and text filtering,
and graph views with Cytoscape.js visualization.
Views render as htmx partials into the #editor-area of the workspace.

Uses ViewSpecService for loading view specs and executing SPARQL queries,
and LabelService for resolving column header and row labels.
"""

import logging
import uuid
from urllib.parse import unquote, quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_label_service, get_query_service, get_shapes_service, get_view_spec_service
from app.services.labels import LabelService
from app.services.shapes import ShapesService
from app.sparql.query_service import QueryService
from app.browser._helpers import get_hidden_types
from app.views.service import ViewSpec, ViewSpecService, extract_scope_where_body, inject_values_binding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser/views", tags=["views"])


def _embed_response(templates, request, fragment_template: str, context: dict):
    """Render a fragment template inside embed_wrapper.html for embed mode.

    Renders the fragment to an HTML string, then wraps it in the minimal
    base_embed.html layout via embed_wrapper.html.
    """
    fragment_html = templates.env.get_template(fragment_template).render(context)
    wrapper_context = {"request": request, "content": fragment_html}
    response = templates.TemplateResponse(
        request, "browser/embed_wrapper.html", wrapper_context
    )
    response.headers["X-Embed-Mode"] = "1"
    return response

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


class SaveViewRequest(BaseModel):
    name: str
    renderer_type: str
    type_filter: str = ""
    scope_query_id: str = ""


@router.post("/save")
async def save_view(
    body: SaveViewRequest,
    user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
):
    """Save the current generic view configuration as a promoted view.

    Creates a PromotedView without requiring an existing saved query.
    """
    try:
        result = await query_service.save_promoted_view(
            user_id=user.id,
            display_label=body.name,
            renderer_type=body.renderer_type,
            type_filter=body.type_filter,
            scope_query_id=body.scope_query_id,
        )
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)

    return JSONResponse(content={
        "id": result.id,
        "label": result.display_label,
        "renderer": result.renderer_type,
    })


@router.delete("/saved/{view_id}")
async def delete_saved_view(
    view_id: str,
    user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
):
    """Delete a saved promoted view by its view ID."""
    try:
        view_uuid = uuid.UUID(view_id)
    except ValueError:
        return JSONResponse(content={"error": "Invalid view ID"}, status_code=400)

    await query_service.delete_promoted_view(view_uuid, user.id)
    return JSONResponse(content={"ok": True})@router.get("/explorer")
async def views_explorer(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Render the views explorer tree with flat generic entries + Saved Views folder.

    The template is static — Spatial Canvas, Ontology Viewer, Table/Cards/Graph
    generic views, and a Saved Views folder that lazy-loads via htmx from
    /browser/my-views.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "browser/views_explorer.html", {"request": request}
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


_VALID_RENDERERS = {"table", "card", "graph"}


@router.get("/generic/{renderer}")
async def generic_view(
    request: Request,
    renderer: str,
    type: str = Query(default=""),
    scope_query: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: str = Query(default=""),
    dir: str = Query(default="asc"),
    filter: str = Query(default=""),
    group_by: str = Query(default=""),
    embed: int = Query(default=0),
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    label_service: LabelService = Depends(get_label_service),
    shapes_service: ShapesService = Depends(get_shapes_service),
    query_service: QueryService = Depends(get_query_service),
):
    """Render a generic view using SHACL-driven dynamic queries.

    Builds SPARQL dynamically from SHACL metadata (via build_dynamic_query),
    creating a transient ViewSpec for execution. Supports table, card, and
    graph renderers. When ``type`` is specified, columns are derived from
    SHACL properties for that type.

    Args:
        renderer: One of 'table', 'card', 'graph'.
        type: Optional RDF type IRI to filter and derive columns from.
    """
    if renderer not in _VALID_RENDERERS:
        logger.info("generic_view: invalid renderer '%s'", renderer)
        return HTMLResponse(
            content='<div class="editor-empty"><p>Invalid renderer type. Use table, card, or graph.</p></div>',
            status_code=404,
        )

    templates = request.app.state.templates
    type_iri = type if type else None

    # Resolve scope_query to a WHERE body filter if set
    scope_filter_text: str | None = None
    if scope_query:
        try:
            query_uuid = uuid.UUID(scope_query)
            saved = await query_service.get_query(query_uuid, user.id)
            if saved:
                scope_filter_text = extract_scope_where_body(saved.query_text)
                if not scope_filter_text:
                    logger.warning("generic_view: scope_query=%s WHERE body extraction failed", scope_query)
            else:
                logger.warning("generic_view: scope_query=%s not found — rendering unfiltered", scope_query)
        except (ValueError, Exception):
            logger.warning("generic_view: invalid scope_query=%s — rendering unfiltered", scope_query, exc_info=True)

    # Fetch saved queries for the scope dropdown
    user_saved_queries = await query_service.list_user_queries(user.id)
    model_saved_queries = await query_service.list_model_queries()

    # Build dynamic query from SHACL metadata
    sparql_query, columns = await view_spec_service.build_dynamic_query(
        type_iri, renderer, scope_filter=scope_filter_text,
    )

    # Create transient ViewSpec
    spec = ViewSpec(
        spec_iri=f"urn:sempkm:view:generic-{renderer}",
        label=f"All Objects" if not type_iri else f"Objects",
        target_class=type_iri or "",
        renderer_type=renderer,
        sparql_query=sparql_query,
        columns=columns if columns else view_spec_service._DEFAULT_COLUMNS.copy(),
        source_model="system",
    )

    # Build pagination base URL for this generic view
    pagination_base_url = f"/browser/views/generic/{renderer}"

    # pag_extra carries the type param (and other non-standard params) via & separator
    pag_extra = ""
    if type_iri:
        pag_extra = f"&type={quote(type_iri, safe='')}"
    if scope_query:
        pag_extra += f"&scope_query={quote(scope_query, safe='')}"

    # Resolve type label if type is specified
    type_label = "All Objects"
    if type_iri:
        type_labels = await label_service.resolve_batch([type_iri])
        type_label = type_labels.get(type_iri, type_iri)

    encoded_spec_iri = quote(spec.spec_iri, safe="")

    # Fetch available types for type filter pills
    types_list = await shapes_service.get_types(exclude_iris=get_hidden_types())

    # Get model-declared view specs for the active type (for variant dropdown)
    model_view_specs = await view_spec_service.get_view_specs_for_type(type_iri) if type_iri else []

    logger.info("generic_view: renderer=%s type=%s scope_query=%s", renderer, type_iri or "(all)", scope_query or "(none)")

    if renderer == "table":
        effective_sort = sort if sort else ""
        result = await view_spec_service.execute_table_query(
            spec=spec,
            page=page,
            page_size=page_size,
            sort_col=effective_sort,
            sort_dir=dir,
            filter_text=filter,
        )

        # Resolve labels for row IRIs
        obj_iris = [row["s"] for row in result["rows"] if row.get("s")]
        labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

        # Column headers
        column_labels: dict[str, str] = {}
        for col in result["columns"]:
            column_labels[col] = col.replace("_", " ").title()

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
            "model_view_specs": model_view_specs,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "view_type": "table",
            "source_model": "system",
            "dashboard_mode": 0,
            "is_generic": True,
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "selected_type": type_iri or "",
            "types": types_list,
            "renderer": renderer,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
        }
        if embed:
            return _embed_response(templates, request, "browser/table_view.html", context)
        return templates.TemplateResponse(request, "browser/table_view.html", context)

    elif renderer == "card":
        effective_group_by = group_by if group_by else None

        result = await view_spec_service.execute_cards_query(
            spec=spec,
            page=page,
            page_size=page_size if page_size != 25 else 12,
            filter_text=filter,
            group_by=effective_group_by,
        )

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
            "model_view_specs": model_view_specs,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "view_type": "card",
            "source_model": "system",
            "dashboard_mode": 0,
            "is_generic": True,
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "selected_type": type_iri or "",
            "types": types_list,
            "renderer": renderer,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
        }
        if embed:
            return _embed_response(templates, request, "browser/cards_view.html", context)
        return templates.TemplateResponse(request, "browser/cards_view.html", context)

    else:  # graph
        # For graph: execute and render graph container
        result = await view_spec_service.execute_graph_query(spec)

        # Build the data URL for the generic graph endpoint
        graph_data_url = f"/browser/views/generic/graph/data"
        graph_data_params = []
        if type_iri:
            graph_data_params.append(f"type={quote(type_iri, safe='')}")
        if scope_query:
            graph_data_params.append(f"scope_query={quote(scope_query, safe='')}")
        if graph_data_params:
            graph_data_url += "?" + "&".join(graph_data_params)

        context = {
            "request": request,
            "spec": spec,
            "spec_iri": spec.spec_iri,
            "spec_iri_encoded": encoded_spec_iri,
            "model_view_specs": model_view_specs,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "available_layouts": [
                {"name": "fcose", "label": "Force-Directed"},
                {"name": "dagre", "label": "Hierarchical"},
                {"name": "concentric", "label": "Radial"},
            ],
            "type_colors": result.get("type_colors", {}),
            "sort_col": "",
            "sort_dir": "asc",
            "current_filter": filter,
            "is_generic": True,
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "selected_type": type_iri or "",
            "graph_data_url": graph_data_url,
            "types": types_list,
            "renderer": renderer,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
        }
        if embed:
            return _embed_response(templates, request, "browser/graph_view.html", context)
        return templates.TemplateResponse(request, "browser/graph_view.html", context)


@router.get("/generic/{renderer}/data")
async def generic_graph_data(
    request: Request,
    renderer: str,
    type: str = Query(default=""),
    scope_query: str = Query(default=""),
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    query_service: QueryService = Depends(get_query_service),
):
    """Return graph data as JSON for the generic graph view.

    Builds a dynamic CONSTRUCT query and executes it.
    Accepts optional scope_query to filter results by saved query.
    """
    if renderer != "graph":
        return JSONResponse(content={"nodes": [], "edges": [], "type_colors": {}}, status_code=404)

    type_iri = type if type else None

    # Resolve scope filter if scope_query is set
    scope_filter_text: str | None = None
    if scope_query:
        try:
            query_uuid = uuid.UUID(scope_query)
            saved = await query_service.get_query(query_uuid, user.id)
            if saved:
                scope_filter_text = extract_scope_where_body(saved.query_text)
        except (ValueError, Exception):
            logger.warning("generic_graph_data: invalid scope_query=%s", scope_query, exc_info=True)

    sparql_query, _ = await view_spec_service.build_dynamic_query(
        type_iri, "graph", scope_filter=scope_filter_text,
    )

    spec = ViewSpec(
        spec_iri="urn:sempkm:view:generic-graph",
        label="Graph View",
        target_class=type_iri or "",
        renderer_type="graph",
        sparql_query=sparql_query,
        source_model="system",
    )

    result = await view_spec_service.execute_graph_query(spec)
    return JSONResponse(content=result)


@router.get("/type-pills")
async def type_pills(
    request: Request,
    renderer: str = Query(default="table"),
    selected_type: str = Query(default=""),
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Return available types as a list for type filter pills.

    Returns JSON list of types with their IRIs and labels, plus active
    state and href for each pill.
    """
    types = await shapes_service.get_types(exclude_iris=get_hidden_types())

    pills = []
    for t in types:
        iri = t["iri"]
        pills.append({
            "iri": iri,
            "label": t["label"],
            "active": iri == selected_type,
            "href": f"/browser/views/generic/{renderer}?type={quote(iri, safe='')}",
        })

    return JSONResponse(content={"types": pills, "renderer": renderer, "selected_type": selected_type})


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
    context_iri: str = Query(default=""),
    context_var: str = Query(default=""),
    dashboard_mode: int = Query(default=0),
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

    # Inject VALUES binding for dashboard cross-view context
    effective_query_spec = spec
    if context_iri and context_var:
        modified_query = inject_values_binding(spec.sparql_query, context_var, context_iri)
        if modified_query != spec.sparql_query:
            # Create a copy with the modified query
            effective_query_spec = ViewSpec(
                spec_iri=spec.spec_iri,
                label=spec.label,
                target_class=spec.target_class,
                renderer_type=spec.renderer_type,
                sparql_query=modified_query,
                columns=spec.columns,
                sort_default=spec.sort_default,
                card_title=spec.card_title,
                card_subtitle=spec.card_subtitle,
                source_model=spec.source_model,
            )

    result = await view_spec_service.execute_table_query(
        spec=effective_query_spec,
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
        type_label = "Custom View"
        labels: dict[str, str] = {}
    else:
        # Resolve labels for all object IRIs in rows (for clickable first column)
        obj_iris = [row["s"] for row in result["rows"] if row.get("s")]
        labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

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
        "model_view_specs": [],
        "type_label": type_label,
        "type_iri": spec.target_class,
        "view_type": "table",
        "source_model": spec.source_model,
        "dashboard_mode": dashboard_mode,
        "pagination_base_url": f"/browser/views/table/{encoded_spec_iri}",
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
    context_iri: str = Query(default=""),
    context_var: str = Query(default=""),
    dashboard_mode: int = Query(default=0),
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

    # Inject VALUES binding for dashboard cross-view context
    effective_query_spec = spec
    if context_iri and context_var:
        modified_query = inject_values_binding(spec.sparql_query, context_var, context_iri)
        if modified_query != spec.sparql_query:
            effective_query_spec = ViewSpec(
                spec_iri=spec.spec_iri,
                label=spec.label,
                target_class=spec.target_class,
                renderer_type=spec.renderer_type,
                sparql_query=modified_query,
                columns=spec.columns,
                sort_default=spec.sort_default,
                card_title=spec.card_title,
                card_subtitle=spec.card_subtitle,
                source_model=spec.source_model,
            )

    result = await view_spec_service.execute_cards_query(
        spec=effective_query_spec,
        page=page,
        page_size=page_size,
        filter_text=filter,
        group_by=effective_group_by,
    )

    # For user views: skip type switcher and use "Custom View" label
    if spec.source_model == "user":
        type_label = "Custom View"
    else:
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
        "model_view_specs": [],
        "type_label": type_label,
        "type_iri": spec.target_class,
        "view_type": "card",
        "source_model": spec.source_model,
        "dashboard_mode": dashboard_mode,
        "pagination_base_url": f"/browser/views/card/{encoded_spec_iri}",
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
        type_label = "Custom View"
    else:
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
        "model_view_specs": [],
        "type_label": type_label,
        "type_iri": spec.target_class,
        "available_layouts": available_layouts,
        "type_colors": type_colors,
        "sort_col": "",
        "sort_dir": "asc",
        "current_filter": filter,
        "pagination_base_url": f"/browser/views/graph/{encoded_spec_iri}",
    }

    return templates.TemplateResponse(
        request, "browser/graph_view.html", context
    )
