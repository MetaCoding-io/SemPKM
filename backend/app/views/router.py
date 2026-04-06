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
from app.dependencies import get_triplestore_client, get_validation_queue, get_webhook_service
from app.services.labels import LabelService
from app.services.shapes import ShapesService
from app.sparql.query_service import QueryService
from app.browser._helpers import get_hidden_types
from app.sparql.builder import safe_iri
from app.views.service import ViewSpec, ViewSpecService, extract_scope_where_body, inject_values_binding
from app.triplestore.client import TriplestoreClient
from app.validation.queue import AsyncValidationQueue
from app.services.webhooks import WebhookService
from app.rdf.namespaces import CURRENT_GRAPH

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


@router.get("/compatible-types")
async def compatible_types(
    renderer: str = Query(default="table"),
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
):
    """Return types compatible with a given renderer as JSON.

    For renderers that require specific SHACL constraints (kanban needs
    status field, calendar/timeline need date fields, map needs geo pair),
    only matching types are returned. All other renderers return all types.
    """
    types = await view_spec_service.get_compatible_types(
        renderer=renderer,
        exclude_iris=get_hidden_types(),
    )
    return JSONResponse(content={"types": types})


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
    return JSONResponse(content={"ok": True})


@router.get("/saved-queries/explorer")
async def saved_queries_explorer(
    request: Request,
    user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
):
    """Render saved queries list for the explorer sidebar.

    Returns an HTML partial with all user and model queries as clickable,
    draggable tree-leaf entries for the QUERIES explorer section.
    """
    templates = request.app.state.templates
    try:
        queries = await query_service.list_all_queries(user.id)
    except Exception:
        logger.exception("saved_queries_explorer: failed to load queries")
        queries = []
    model_queries = [q for q in queries if q.source == "model"]
    user_queries = [q for q in queries if q.source != "model"]
    return templates.TemplateResponse(
        request,
        "browser/saved_queries_explorer.html",
        {
            "request": request,
            "queries": queries,
            "model_queries": model_queries,
            "user_queries": user_queries,
        },
    )


@router.get("/explorer")
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


_VALID_RENDERERS = {"table", "card", "graph", "kanban", "calendar", "map", "timeline", "quadrant", "bmc", "okr", "decision-matrix"}


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

    # Validate type IRI early to reject injection payloads with 400
    if type_iri:
        try:
            safe_iri(type_iri)
        except ValueError:
            logger.warning("generic_view: rejected invalid type IRI: %s", type_iri)
            return HTMLResponse(
                content='<div class="editor-empty"><p>Invalid type IRI</p></div>',
                status_code=400,
            )

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

    # Fetch types compatible with this renderer (filtered by SHACL constraints)
    types_list = await view_spec_service.get_compatible_types(
        renderer=renderer,
        exclude_iris=get_hidden_types(),
    )

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

    elif renderer == "graph":
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
                {"name": "isometric", "label": "Isometric 2.5D"},
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

    elif renderer == "calendar":
        if not type_iri:
            # No type selected → use merged mode (Events + Tasks combined)
            logger.info("generic_view: renderer=calendar no type → merged mode")

            calendar_data_url = "/browser/views/generic/calendar/data?merged=true"
            if scope_query:
                calendar_data_url += f"&scope_query={quote(scope_query, safe='')}"

            context = {
                "request": request,
                "date_fields": {"merged": True},  # truthy so template renders calendar
                "calendar_data_url": calendar_data_url,
                "type_label": type_label,
                "type_iri": "",
                "selected_type": "",
                "types": types_list,
                "model_view_specs": model_view_specs,
                "scope_query": scope_query,
                "user_saved_queries": user_saved_queries,
                "model_saved_queries": model_saved_queries,
                "is_generic": True,
                "renderer": "calendar",
                "pagination_base_url": pagination_base_url,
                "pag_extra": pag_extra,
                "spec": spec,
            }
            if embed:
                return _embed_response(templates, request, "browser/calendar_view.html", context)
            return templates.TemplateResponse(request, "browser/calendar_view.html", context)

        start_field, end_field = await view_spec_service._detect_date_fields(type_iri)

        if start_field is None:
            logger.warning("generic_view: renderer=calendar type=%s has no date properties", type_iri)
            return templates.TemplateResponse(
                request,
                "browser/calendar_view.html",
                {
                    "request": request,
                    "error_message": "This type has no date properties for Calendar display",
                    "events": [],
                    "date_fields": None,
                    "type_label": type_label,
                    "type_iri": spec.target_class,
                    "selected_type": type_iri or "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "calendar",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        logger.info(
            "generic_view: renderer=calendar type=%s scope_query=%s start=%s end=%s",
            type_iri, scope_query or "(none)", start_field.path,
            end_field.path if end_field else "(none)",
        )

        # Build the data URL for the calendar JSON endpoint
        calendar_data_url = f"/browser/views/generic/calendar/data"
        calendar_data_params = []
        if type_iri:
            calendar_data_params.append(f"type={quote(type_iri, safe='')}")
        if scope_query:
            calendar_data_params.append(f"scope_query={quote(scope_query, safe='')}")
        if calendar_data_params:
            calendar_data_url += "?" + "&".join(calendar_data_params)

        context = {
            "request": request,
            "date_fields": {
                "start": {"path": start_field.path, "name": start_field.name},
                "end": {"path": end_field.path, "name": end_field.name} if end_field else None,
            },
            "calendar_data_url": calendar_data_url,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "selected_type": type_iri or "",
            "types": types_list,
            "model_view_specs": model_view_specs,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
            "is_generic": True,
            "renderer": "calendar",
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "spec": spec,
        }
        if embed:
            return _embed_response(templates, request, "browser/calendar_view.html", context)
        return templates.TemplateResponse(request, "browser/calendar_view.html", context)

    elif renderer == "map":
        if not type_iri:
            logger.info("generic_view: renderer=map but no type selected")
            return templates.TemplateResponse(
                request,
                "browser/map_view.html",
                {
                    "request": request,
                    "error_message": "Select a type to use Map View",
                    "markers": [],
                    "geo_fields": None,
                    "type_label": type_label,
                    "type_iri": "",
                    "selected_type": "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "map",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        lat_field, lng_field = await view_spec_service._detect_geo_fields(type_iri)

        if lat_field is None:
            logger.warning("generic_view: renderer=map type=%s has no geo properties", type_iri)
            return templates.TemplateResponse(
                request,
                "browser/map_view.html",
                {
                    "request": request,
                    "error_message": "This type has no geographic coordinate properties for Map display",
                    "markers": [],
                    "geo_fields": None,
                    "type_label": type_label,
                    "type_iri": spec.target_class,
                    "selected_type": type_iri or "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "map",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        logger.info(
            "generic_view: renderer=map type=%s scope_query=%s lat=%s lng=%s",
            type_iri, scope_query or "(none)", lat_field.path, lng_field.path,
        )

        # Build the data URL for the map JSON endpoint
        map_data_url = "/browser/views/generic/map/data"
        map_data_params = []
        if type_iri:
            map_data_params.append(f"type={quote(type_iri, safe='')}")
        if scope_query:
            map_data_params.append(f"scope_query={quote(scope_query, safe='')}")
        if map_data_params:
            map_data_url += "?" + "&".join(map_data_params)

        context = {
            "request": request,
            "geo_fields": {
                "lat": {"path": lat_field.path, "name": lat_field.name},
                "lng": {"path": lng_field.path, "name": lng_field.name},
            },
            "map_data_url": map_data_url,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "selected_type": type_iri or "",
            "types": types_list,
            "model_view_specs": model_view_specs,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
            "is_generic": True,
            "renderer": "map",
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "spec": spec,
        }
        if embed:
            return _embed_response(templates, request, "browser/map_view.html", context)
        return templates.TemplateResponse(request, "browser/map_view.html", context)

    elif renderer == "timeline":
        if not type_iri:
            logger.info("generic_view: renderer=timeline but no type selected")
            return templates.TemplateResponse(
                request,
                "browser/timeline_view.html",
                {
                    "request": request,
                    "error_message": "Select a type to use Timeline View",
                    "tasks": [],
                    "date_fields": None,
                    "type_label": type_label,
                    "type_iri": "",
                    "selected_type": "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "timeline",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        start_field, end_field = await view_spec_service._detect_date_fields(type_iri)

        if start_field is None:
            logger.warning("generic_view: renderer=timeline type=%s has no date properties", type_iri)
            return templates.TemplateResponse(
                request,
                "browser/timeline_view.html",
                {
                    "request": request,
                    "error_message": "This type has no date properties for Timeline display",
                    "tasks": [],
                    "date_fields": None,
                    "type_label": type_label,
                    "type_iri": spec.target_class,
                    "selected_type": type_iri or "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "timeline",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        logger.info(
            "generic_view: renderer=timeline type=%s scope_query=%s start=%s end=%s",
            type_iri, scope_query or "(none)", start_field.path,
            end_field.path if end_field else "(none)",
        )

        # Build the data URL for the timeline JSON endpoint
        timeline_data_url = "/browser/views/generic/timeline/data"
        timeline_data_params = []
        if type_iri:
            timeline_data_params.append(f"type={quote(type_iri, safe='')}")
        if scope_query:
            timeline_data_params.append(f"scope_query={quote(scope_query, safe='')}")
        if timeline_data_params:
            timeline_data_url += "?" + "&".join(timeline_data_params)

        context = {
            "request": request,
            "date_fields": {
                "start": {"path": start_field.path, "name": start_field.name},
                "end": {"path": end_field.path, "name": end_field.name} if end_field else None,
            },
            "timeline_data_url": timeline_data_url,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "selected_type": type_iri or "",
            "types": types_list,
            "model_view_specs": model_view_specs,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
            "is_generic": True,
            "renderer": "timeline",
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "spec": spec,
        }
        if embed:
            return _embed_response(templates, request, "browser/timeline_view.html", context)
        return templates.TemplateResponse(request, "browser/timeline_view.html", context)

    elif renderer == "quadrant":
        if not type_iri:
            logger.info("generic_view: renderer=quadrant but no type selected")
            return templates.TemplateResponse(
                request,
                "browser/quadrant_view.html",
                {
                    "request": request,
                    "error_message": "Select a type to use Quadrant View",
                    "quadrants": [],
                    "axes": None,
                    "type_label": type_label,
                    "type_iri": "",
                    "selected_type": "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "quadrant",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        x_axis, y_axis, x_values, y_values = await view_spec_service._detect_quadrant_axes(type_iri)

        if x_axis is None:
            logger.warning("generic_view: renderer=quadrant type=%s has no quadrant-axis properties", type_iri)
            return templates.TemplateResponse(
                request,
                "browser/quadrant_view.html",
                {
                    "request": request,
                    "error_message": "This type has no properties with two-value constraints (sh:in) suitable for quadrant axes",
                    "quadrants": [],
                    "axes": None,
                    "type_label": type_label,
                    "type_iri": spec.target_class,
                    "selected_type": type_iri or "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "quadrant",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        logger.info(
            "generic_view: renderer=quadrant type=%s scope_query=%s x=%s y=%s",
            type_iri, scope_query or "(none)", x_axis.path, y_axis.path,
        )

        quadrant_result = await view_spec_service.execute_quadrant_query(
            type_iri, x_axis, y_axis, x_values, y_values,
            scope_filter=scope_filter_text,
        )

        # Build the data URL for the quadrant JSON endpoint
        quadrant_data_url = "/browser/views/generic/quadrant/data"
        quadrant_data_params = []
        if type_iri:
            quadrant_data_params.append(f"type={quote(type_iri, safe='')}")
        if scope_query:
            quadrant_data_params.append(f"scope_query={quote(scope_query, safe='')}")
        if quadrant_data_params:
            quadrant_data_url += "?" + "&".join(quadrant_data_params)

        context = {
            "request": request,
            "quadrants": quadrant_result["quadrants"],
            "axes": quadrant_result["axes"],
            "total": quadrant_result["total"],
            "quadrant_data_url": quadrant_data_url,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "selected_type": type_iri or "",
            "types": types_list,
            "model_view_specs": model_view_specs,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
            "is_generic": True,
            "renderer": "quadrant",
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "spec": spec,
        }
        if embed:
            return _embed_response(templates, request, "browser/quadrant_view.html", context)
        return templates.TemplateResponse(request, "browser/quadrant_view.html", context)

    elif renderer == "bmc":
        if not type_iri:
            logger.info("generic_view: renderer=bmc but no type selected")
            return templates.TemplateResponse(
                request,
                "browser/bmc_view.html",
                {
                    "request": request,
                    "error_message": "Select a type to use Canvas View",
                    "sections": [],
                    "section_types": {},
                    "type_label": type_label,
                    "type_iri": "",
                    "selected_type": "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "bmc",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        section_prop, canvas_prop = await view_spec_service._detect_bmc_sections(type_iri)

        if section_prop is None:
            logger.warning("generic_view: renderer=bmc type=%s has no BMC section type property", type_iri)
            return templates.TemplateResponse(
                request,
                "browser/bmc_view.html",
                {
                    "request": request,
                    "error_message": "This type has no BMC section type property (needs a property with exactly 9 sh:in values)",
                    "sections": [],
                    "section_types": {},
                    "type_label": type_label,
                    "type_iri": spec.target_class,
                    "selected_type": type_iri or "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "bmc",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        logger.info(
            "generic_view: renderer=bmc type=%s scope_query=%s section_prop=%s",
            type_iri, scope_query or "(none)", section_prop.path,
        )

        bmc_result = await view_spec_service.execute_bmc_query(
            type_iri, section_prop, canvas_prop,
            scope_filter=scope_filter_text,
        )

        # Build data URL for the BMC JSON endpoint
        bmc_data_url = "/browser/views/generic/bmc/data"
        bmc_data_params = []
        if type_iri:
            bmc_data_params.append(f"type={quote(type_iri, safe='')}")
        if scope_query:
            bmc_data_params.append(f"scope_query={quote(scope_query, safe='')}")
        if bmc_data_params:
            bmc_data_url += "?" + "&".join(bmc_data_params)

        context = {
            "request": request,
            "sections": bmc_result["sections"],
            "section_types": bmc_result["section_types"],
            "total": bmc_result["total"],
            "bmc_data_url": bmc_data_url,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "selected_type": type_iri or "",
            "types": types_list,
            "model_view_specs": model_view_specs,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
            "is_generic": True,
            "renderer": "bmc",
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "spec": spec,
        }
        if embed:
            return _embed_response(templates, request, "browser/bmc_view.html", context)
        return templates.TemplateResponse(request, "browser/bmc_view.html", context)

    elif renderer == "okr":
        if not type_iri:
            logger.info("generic_view: renderer=okr but no type selected")
            return templates.TemplateResponse(
                request,
                "browser/okr_view.html",
                {
                    "request": request,
                    "error_message": "Select a type to use OKR View",
                    "objectives": [],
                    "ungrouped": [],
                    "type_label": type_label,
                    "type_iri": "",
                    "selected_type": "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "okr",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        current_prop, target_prop, unit_prop, objective_prop = await view_spec_service._detect_okr_structure(type_iri)

        if current_prop is None:
            logger.warning("generic_view: renderer=okr type=%s has no OKR progress properties", type_iri)
            return templates.TemplateResponse(
                request,
                "browser/okr_view.html",
                {
                    "request": request,
                    "error_message": "This type has no decimal currentValue/targetValue properties suitable for OKR progress tracking",
                    "objectives": [],
                    "ungrouped": [],
                    "type_label": type_label,
                    "type_iri": spec.target_class,
                    "selected_type": type_iri or "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "okr",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        logger.info(
            "generic_view: renderer=okr type=%s scope_query=%s current=%s target=%s",
            type_iri, scope_query or "(none)", current_prop.path, target_prop.path,
        )

        okr_result = await view_spec_service.execute_okr_query(
            type_iri, current_prop, target_prop, unit_prop, objective_prop,
            scope_filter=scope_filter_text,
        )

        # Build data URL for the OKR JSON endpoint
        okr_data_url = "/browser/views/generic/okr/data"
        okr_data_params = []
        if type_iri:
            okr_data_params.append(f"type={quote(type_iri, safe='')}")
        if scope_query:
            okr_data_params.append(f"scope_query={quote(scope_query, safe='')}")
        if okr_data_params:
            okr_data_url += "?" + "&".join(okr_data_params)

        context = {
            "request": request,
            "objectives": okr_result["objectives"],
            "ungrouped": okr_result["ungrouped"],
            "total": okr_result["total"],
            "okr_data_url": okr_data_url,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "selected_type": type_iri or "",
            "types": types_list,
            "model_view_specs": model_view_specs,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
            "is_generic": True,
            "renderer": "okr",
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "spec": spec,
        }
        if embed:
            return _embed_response(templates, request, "browser/okr_view.html", context)
        return templates.TemplateResponse(request, "browser/okr_view.html", context)

    elif renderer == "decision-matrix":
        if not type_iri:
            logger.info("generic_view: renderer=decision-matrix but no type selected")
            return templates.TemplateResponse(
                request,
                "browser/decision_matrix_view.html",
                {
                    "request": request,
                    "error_message": "Select a type to use Decision Matrix View",
                    "alternatives": [],
                    "criteria": [],
                    "type_label": type_label,
                    "type_iri": "",
                    "selected_type": "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "decision-matrix",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        value_prop, alt_prop, crit_prop, _ = await view_spec_service._detect_decision_matrix_structure(type_iri)

        if value_prop is None:
            logger.warning("generic_view: renderer=decision-matrix type=%s has no scoring properties", type_iri)
            return templates.TemplateResponse(
                request,
                "browser/decision_matrix_view.html",
                {
                    "request": request,
                    "error_message": "This type has no value/alternative/criterion properties suitable for Decision Matrix scoring",
                    "alternatives": [],
                    "criteria": [],
                    "type_label": type_label,
                    "type_iri": spec.target_class,
                    "selected_type": type_iri or "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "decision-matrix",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        logger.info(
            "generic_view: renderer=decision-matrix type=%s scope_query=%s value=%s",
            type_iri, scope_query or "(none)", value_prop.path,
        )

        dm_result = await view_spec_service.execute_decision_matrix_query(
            type_iri, value_prop, alt_prop, crit_prop,
            scope_filter=scope_filter_text,
        )

        # Build data URL for the Decision Matrix JSON endpoint
        dm_data_url = "/browser/views/generic/decision-matrix/data"
        dm_data_params = []
        if type_iri:
            dm_data_params.append(f"type={quote(type_iri, safe='')}")
        if scope_query:
            dm_data_params.append(f"scope_query={quote(scope_query, safe='')}")
        if dm_data_params:
            dm_data_url += "?" + "&".join(dm_data_params)

        context = {
            "request": request,
            "alternatives": dm_result["alternatives"],
            "criteria": dm_result["criteria"],
            "total_scores": dm_result["total_scores"],
            "dm_data_url": dm_data_url,
            "type_label": type_label,
            "type_iri": spec.target_class,
            "selected_type": type_iri or "",
            "types": types_list,
            "model_view_specs": model_view_specs,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
            "is_generic": True,
            "renderer": "decision-matrix",
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "spec": spec,
        }
        if embed:
            return _embed_response(templates, request, "browser/decision_matrix_view.html", context)
        return templates.TemplateResponse(request, "browser/decision_matrix_view.html", context)

    else:  # kanban
        if not type_iri:
            logger.info("generic_view: renderer=kanban but no type selected")
            return templates.TemplateResponse(
                request,
                "browser/kanban_view.html",
                {
                    "request": request,
                    "error_message": "Select a type to use Kanban View",
                    "columns": [],
                    "status_field": None,
                    "type_label": type_label,
                    "type_iri": "",
                    "selected_type": "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "kanban",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        status_field, status_values = await view_spec_service._detect_status_field(type_iri)

        if status_field is None:
            logger.warning("generic_view: renderer=kanban type=%s has no status-like property", type_iri)
            return templates.TemplateResponse(
                request,
                "browser/kanban_view.html",
                {
                    "request": request,
                    "error_message": "This type has no status-like properties for Kanban grouping",
                    "columns": [],
                    "status_field": None,
                    "type_label": type_label,
                    "type_iri": spec.target_class,
                    "selected_type": type_iri or "",
                    "types": types_list,
                    "model_view_specs": model_view_specs,
                    "scope_query": scope_query,
                    "user_saved_queries": user_saved_queries,
                    "model_saved_queries": model_saved_queries,
                    "is_generic": True,
                    "renderer": "kanban",
                    "pagination_base_url": pagination_base_url,
                    "pag_extra": pag_extra,
                    "spec": spec,
                },
            )

        logger.info(
            "generic_view: renderer=kanban type=%s scope_query=%s",
            type_iri, scope_query or "(none)",
        )

        kanban_result = await view_spec_service.execute_kanban_query(
            type_iri, status_field, status_values, scope_filter=scope_filter_text,
        )

        context = {
            "request": request,
            "columns": kanban_result["columns"],
            "status_field": kanban_result["status_field"],
            "enrichment": kanban_result.get("enrichment"),
            "type_label": type_label,
            "type_iri": spec.target_class,
            "selected_type": type_iri or "",
            "types": types_list,
            "model_view_specs": model_view_specs,
            "scope_query": scope_query,
            "user_saved_queries": user_saved_queries,
            "model_saved_queries": model_saved_queries,
            "is_generic": True,
            "renderer": "kanban",
            "pagination_base_url": pagination_base_url,
            "pag_extra": pag_extra,
            "spec": spec,
        }
        if embed:
            return _embed_response(templates, request, "browser/kanban_view.html", context)
        return templates.TemplateResponse(request, "browser/kanban_view.html", context)


@router.get("/generic/{renderer}/data")
async def generic_view_data(
    request: Request,
    renderer: str,
    type: str = Query(default=""),
    scope_query: str = Query(default=""),
    merged: str = Query(default=""),
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    query_service: QueryService = Depends(get_query_service),
):
    """Return data as JSON for the generic graph, calendar, or map view.

    For graph: builds a dynamic CONSTRUCT query and executes it.
    For calendar: detects date fields and returns FullCalendar events.
      When ``merged=true``, queries both Event and Task types and merges.
    For map: detects geo fields and returns marker data with coordinates.
    Accepts optional scope_query to filter results by saved query.
    """
    if renderer not in ("graph", "calendar", "map", "timeline", "quadrant", "bmc", "okr", "decision-matrix"):
        return JSONResponse(content={"error": "Invalid renderer for data endpoint"}, status_code=404)

    type_iri = type if type else None

    # Validate type IRI early to reject injection payloads with 400
    if type_iri:
        try:
            safe_iri(type_iri)
        except ValueError:
            logger.warning("generic_view_data: rejected invalid type IRI: %s", type_iri)
            return JSONResponse(content={"error": "Invalid type IRI"}, status_code=400)

    # Resolve scope filter if scope_query is set
    scope_filter_text: str | None = None
    if scope_query:
        try:
            query_uuid = uuid.UUID(scope_query)
            saved = await query_service.get_query(query_uuid, user.id)
            if saved:
                scope_filter_text = extract_scope_where_body(saved.query_text)
        except (ValueError, Exception):
            logger.warning("generic_view_data: invalid scope_query=%s", scope_query, exc_info=True)

    if renderer == "calendar":
        # Merged mode: combine events from all known calendar types
        if merged == "true":
            result = await view_spec_service.execute_merged_calendar_query(
                scope_filter=scope_filter_text,
            )
            return JSONResponse(content=result)

        # Single-type mode
        if not type_iri:
            return JSONResponse(content={"events": [], "date_fields": None})
        start_field, end_field = await view_spec_service._detect_date_fields(type_iri)
        if start_field is None:
            return JSONResponse(content={"events": [], "date_fields": None})
        result = await view_spec_service.execute_calendar_query(
            type_iri, start_field, end_field, scope_filter=scope_filter_text,
        )
        return JSONResponse(content=result)

    if renderer == "map":
        if not type_iri:
            return JSONResponse(content={"markers": [], "geo_fields": None})
        lat_field, lng_field = await view_spec_service._detect_geo_fields(type_iri)
        if lat_field is None:
            return JSONResponse(content={"markers": [], "geo_fields": None})
        result = await view_spec_service.execute_map_query(
            type_iri, lat_field, lng_field, scope_filter=scope_filter_text,
        )
        return JSONResponse(content=result)

    if renderer == "timeline":
        if not type_iri:
            return JSONResponse(content={"tasks": [], "dependency_count": 0})
        start_field, end_field = await view_spec_service._detect_date_fields(type_iri)
        if start_field is None:
            return JSONResponse(content={"tasks": [], "dependency_count": 0})
        result = await view_spec_service.execute_timeline_query(
            type_iri, start_field, end_field, scope_filter=scope_filter_text,
        )
        return JSONResponse(content=result)

    if renderer == "quadrant":
        if not type_iri:
            return JSONResponse(content={"quadrants": [], "axes": None, "total": 0})
        x_axis, y_axis, x_values, y_values = await view_spec_service._detect_quadrant_axes(type_iri)
        if x_axis is None:
            return JSONResponse(content={"quadrants": [], "axes": None, "total": 0})
        result = await view_spec_service.execute_quadrant_query(
            type_iri, x_axis, y_axis, x_values, y_values,
            scope_filter=scope_filter_text,
        )
        return JSONResponse(content=result)

    if renderer == "bmc":
        if not type_iri:
            return JSONResponse(content={"sections": [], "section_types": {}, "total": 0})
        section_prop, canvas_prop = await view_spec_service._detect_bmc_sections(type_iri)
        if section_prop is None:
            return JSONResponse(content={"sections": [], "section_types": {}, "total": 0})
        result = await view_spec_service.execute_bmc_query(
            type_iri, section_prop, canvas_prop,
            scope_filter=scope_filter_text,
        )
        return JSONResponse(content=result)

    if renderer == "okr":
        if not type_iri:
            return JSONResponse(content={"objectives": [], "ungrouped": [], "total": 0})
        current_prop, target_prop, unit_prop, objective_prop = await view_spec_service._detect_okr_structure(type_iri)
        if current_prop is None:
            return JSONResponse(content={"objectives": [], "ungrouped": [], "total": 0})
        result = await view_spec_service.execute_okr_query(
            type_iri, current_prop, target_prop, unit_prop, objective_prop,
            scope_filter=scope_filter_text,
        )
        return JSONResponse(content=result)

    if renderer == "decision-matrix":
        if not type_iri:
            return JSONResponse(content={"alternatives": [], "criteria": [], "total_scores": 0})
        value_prop, alt_prop, crit_prop, _ = await view_spec_service._detect_decision_matrix_structure(type_iri)
        if value_prop is None:
            return JSONResponse(content={"alternatives": [], "criteria": [], "total_scores": 0})
        result = await view_spec_service.execute_decision_matrix_query(
            type_iri, value_prop, alt_prop, crit_prop,
            scope_filter=scope_filter_text,
        )
        return JSONResponse(content=result)

    # graph renderer
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


# ── Calendar PATCH endpoint ────────────────────────────────────

# Predicate mapping by type: which predicates hold start/end dates
_CALENDAR_DATE_PREDICATES: dict[str, dict[str, str]] = {
    "urn:sempkm:model:basic-pkm:Event": {
        "start": "https://schema.org/startDate",
        "end": "https://schema.org/endDate",
    },
    "urn:sempkm:model:basic-pkm:Task": {
        "start": "urn:sempkm:model:basic-pkm:scheduledStart",
        "end": "urn:sempkm:model:basic-pkm:scheduledEnd",
    },
}


class CalendarPatchRequest(BaseModel):
    """Request body for calendar drag/resize persistence."""
    iri: str
    start: str | None = None
    end: str | None = None


@router.post("/calendar/patch")
async def calendar_patch(
    body: CalendarPatchRequest,
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """Persist calendar drag/resize results via object.patch command.

    Accepts ``{iri, start?, end?}`` and determines the correct predicates
    based on the object's RDF type (Event → schema:startDate/endDate,
    Task → bpkm:scheduledStart/scheduledEnd).
    """
    try:
        safe_body_iri = safe_iri(body.iri)
    except ValueError:
        return JSONResponse(
            content={"error": "Invalid IRI"},
            status_code=400,
        )

    if body.start is None and body.end is None:
        return JSONResponse(
            content={"error": "At least one of start or end must be provided"},
            status_code=400,
        )

    # Detect the object's type to determine the right predicates
    type_query = f"""SELECT ?type WHERE {{
  GRAPH <{CURRENT_GRAPH}> {{
    {safe_body_iri} a ?type .
  }}
}}"""
    try:
        type_result = await client.query(type_query)
        type_bindings = type_result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("calendar_patch: type query failed for %s", body.iri, exc_info=True)
        return JSONResponse(
            content={"error": "Failed to determine object type"},
            status_code=500,
        )

    # Find the first matching type in our predicate map
    predicates: dict[str, str] | None = None
    for tb in type_bindings:
        t = tb.get("type", {}).get("value", "")
        if t in _CALENDAR_DATE_PREDICATES:
            predicates = _CALENDAR_DATE_PREDICATES[t]
            break

    if predicates is None:
        return JSONResponse(
            content={"error": "Object type not supported for calendar updates"},
            status_code=400,
        )

    # Build properties dict for object.patch
    properties: dict[str, str] = {}
    if body.start is not None:
        properties[predicates["start"]] = body.start
    if body.end is not None:
        properties[predicates["end"]] = body.end

    # Dispatch object.patch via the command system
    from app.commands.dispatcher import dispatch
    from app.commands.schemas import ObjectPatchCommand, ObjectPatchParams
    from app.config import settings
    from app.events.store import EventStore
    from rdflib import URIRef

    cmd = ObjectPatchCommand(
        command="object.patch",
        params=ObjectPatchParams(iri=body.iri, properties=properties),
    )

    try:
        operation = await dispatch(cmd, settings.base_namespace)
        event_store = EventStore(client)
        user_iri = URIRef(f"urn:sempkm:user:{user.id}")
        event_result = await event_store.commit(
            [operation],
            performed_by=user_iri,
            performed_by_role=user.role,
        )

        # Trigger async validation
        await validation_queue.enqueue(
            event_iri=str(event_result.event_iri),
            timestamp=event_result.timestamp,
        )

        # Dispatch webhooks
        try:
            await webhook_service.dispatch("object.changed", {
                "event_iri": str(event_result.event_iri),
                "command": "object.patch",
                "timestamp": event_result.timestamp,
            })
        except Exception:
            logger.warning("calendar_patch: webhook dispatch failed", exc_info=True)

        logger.info(
            "calendar_patch: patched %s start=%s end=%s event=%s",
            body.iri, body.start, body.end, event_result.event_iri,
        )

        return JSONResponse(content={"ok": True, "event_iri": str(event_result.event_iri)})

    except Exception as e:
        logger.exception("calendar_patch: command dispatch failed for %s", body.iri)
        return JSONResponse(
            content={"error": f"Patch failed: {str(e)}"},
            status_code=500,
        )


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
        {"name": "isometric", "label": "Isometric 2.5D"},
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
