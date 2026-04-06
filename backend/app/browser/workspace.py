"""Workspace sub-router — layout, navigation tree, icons, and views."""

import logging
import re
import uuid
from typing import Callable
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.dependencies import (
    get_label_service,
    get_query_service,
    get_shapes_service,
    get_triplestore_client,
)
from app.sparql.builder import sparql_escape_string
from app.sparql.query_service import QueryService
from app.triplestore.client import TriplestoreClient
from app.services.icons import IconService
from app.services.labels import LabelService
from app.services.shapes import ShapesService
from app.vfs.mount_service import (
    CREATED_AT,
    CREATED_BY,
    DATE_PROPERTY,
    DIRECTORY_STRATEGY,
    GRAPH_MOUNTS,
    GROUP_BY_PROPERTY,
    MOUNT_NAME,
    MOUNT_PATH,
    NS_MOUNT,
    NS_SEMPKM,
    SCOPE_QUERY,
    SPARQL_SCOPE,
    VISIBILITY,
    MountDefinition,
)
from app.browser.explorer_config import (
    ExplorerConfig,
    build_explorer_query,
    build_group_folders_query,
)
from app.browser.tag_tree import build_tag_tree
from app.vfs.strategies import (
    _LABEL_COALESCE,
    _LABEL_OPTIONALS,
    build_chain_narrowing_filter,
    build_scope_filter,
    query_date_month_folders,
    query_date_year_folders,
    query_flat_objects,
    query_has_uncategorized,
    query_objects_by_date,
    query_objects_by_property,
    query_objects_by_tag,
    query_objects_by_type,
    query_property_folders,
    query_tag_folders,
    query_type_folders,
    query_uncategorized_objects,
)
from app.rdf.namespaces import CURRENT_GRAPH

from ._helpers import _is_htmx_request, _validate_iri, get_hidden_types, get_icon_service

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

logger = logging.getLogger(__name__)

workspace_router = APIRouter(tags=["workspace"])


# ---------------------------------------------------------------------------
# Saved query resolution for VFS scope filtering
# ---------------------------------------------------------------------------

async def _resolve_scope_query_text(client, scope_query: str | None) -> str | None:
    """Resolve a scope_query IRI to its SPARQL query text.

    scope_query is expected to be a full IRI like urn:sempkm:query:{uuid}.
    Returns None if no scope_query or query not found.
    """
    if not scope_query:
        return None

    # Build the query IRI — scope_query is already a full IRI
    query_iri = scope_query

    sparql = f"""
    SELECT ?text WHERE {{
      GRAPH <urn:sempkm:queries> {{
        <{query_iri}> <urn:sempkm:vocab:queryText> ?text .
      }}
    }}
    """
    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0]["text"]["value"]
    except Exception:
        logger.warning("Failed to resolve saved query %s", scope_query, exc_info=True)
    return None


# ---------------------------------------------------------------------------
# Explorer mode handlers
# ---------------------------------------------------------------------------

async def _handle_by_type(
    request: Request,
    shapes_service: ShapesService,
    icon_svc: IconService,
    **_kwargs,
) -> HTMLResponse:
    """Render the nav tree grouped by RDF type (default explorer mode)."""
    templates = request.app.state.templates
    types = await shapes_service.get_types(exclude_iris=get_hidden_types())
    type_icons = icon_svc.get_icon_map(context="tree")

    return templates.TemplateResponse(
        request,
        "browser/nav_tree.html",
        {"request": request, "types": types, "type_icons": type_icons},
    )


async def _handle_hierarchy(
    request: Request,
    label_service: LabelService,
    icon_svc: IconService,
    **_kwargs,
) -> HTMLResponse:
    """Render hierarchy tree with root objects (no dcterms:isPartOf parent)."""
    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    sparql = f"""
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?obj ?type WHERE {{
      GRAPH <{CURRENT_GRAPH}> {{
        ?obj a ?type .
        FILTER NOT EXISTS {{ ?obj dcterms:isPartOf ?parent . }}
      }}
    }}
    """

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Failed to query hierarchy roots", exc_info=True)
        bindings = []

    # De-duplicate: pick first type per object
    obj_types: dict[str, str] = {}
    for b in bindings:
        iri = b["obj"]["value"]
        if iri not in obj_types:
            obj_types[iri] = b["type"]["value"]

    logger.debug("Hierarchy roots query returned %d objects", len(obj_types))

    # Resolve labels and icons
    obj_iris = list(obj_types.keys())
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

    objects = [
        {
            "iri": iri,
            "label": labels.get(iri, iri),
            "type_iri": type_iri,
            "icon": icon_svc.get_type_icon(type_iri, context="tree"),
        }
        for iri, type_iri in obj_types.items()
    ]

    return templates.TemplateResponse(
        request,
        "browser/hierarchy_tree.html",
        {"request": request, "objects": objects},
    )


async def _handle_by_tag(
    request: Request,
    label_service: LabelService,
    icon_svc: IconService,
    **_kwargs,
) -> HTMLResponse:
    """Render the explorer tree grouped by tag values across bpkm:tags and schema:keywords."""
    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    sparql = f"""
    SELECT ?tagValue (COUNT(DISTINCT ?iri) AS ?count)
    FROM <{CURRENT_GRAPH}>
    WHERE {{
      {{ ?iri <urn:sempkm:model:basic-pkm:tags> ?tagValue }}
      UNION
      {{ ?iri <https://schema.org/keywords> ?tagValue }}
    }}
    GROUP BY ?tagValue
    ORDER BY ?tagValue
    """

    bindings = await _execute_sparql_select(client, sparql)

    tag_values = [
        {
            "value": b["tagValue"]["value"],
            "count": int(b["count"]["value"]),
        }
        for b in bindings
    ]

    nodes = build_tag_tree(tag_values)

    logger.debug("By-tag explorer: %d root nodes", len(nodes))

    return templates.TemplateResponse(
        request,
        "browser/tag_tree.html",
        {"request": request, "nodes": nodes},
    )


EXPLORER_MODES: dict[str, Callable] = {
    "by-type": _handle_by_type,
    "hierarchy": _handle_hierarchy,
    "by-tag": _handle_by_tag,
}


# ---------------------------------------------------------------------------
# VFS mount explorer helpers
# ---------------------------------------------------------------------------

_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


async def _get_mount_definition(
    client, mount_id: str
) -> MountDefinition | None:
    """Fetch a MountDefinition by ID via async SPARQL query.

    Reuses the SPARQL pattern from ``mount_router._get_mount_by_id_async``
    but accepts any async triplestore client directly.
    """
    mount_iri = f"{NS_MOUNT}{mount_id}"
    result = await client.query(
        f"""
        SELECT ?name ?path ?strategy ?groupByProp ?dateProp
               ?scope ?scopeQuery ?createdBy ?visibility ?createdAt
        FROM <{GRAPH_MOUNTS}>
        WHERE {{
          <{mount_iri}> a <{NS_SEMPKM}MountSpec> ;
                        <{MOUNT_NAME}> ?name ;
                        <{MOUNT_PATH}> ?path ;
                        <{DIRECTORY_STRATEGY}> ?strategy ;
                        <{CREATED_BY}> ?createdBy ;
                        <{VISIBILITY}> ?visibility .
          OPTIONAL {{ <{mount_iri}> <{GROUP_BY_PROPERTY}> ?groupByProp }}
          OPTIONAL {{ <{mount_iri}> <{DATE_PROPERTY}> ?dateProp }}
          OPTIONAL {{ <{mount_iri}> <{SPARQL_SCOPE}> ?scope }}
          OPTIONAL {{ <{mount_iri}> <{SCOPE_QUERY}> ?scopeQuery }}
          OPTIONAL {{ <{mount_iri}> <{CREATED_AT}> ?createdAt }}
        }}
        LIMIT 1
        """
    )
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return None

    b = bindings[0]
    return MountDefinition(
        id=mount_id,
        name=b["name"]["value"],
        path=b["path"]["value"],
        strategy=b["strategy"]["value"],
        group_by_property=b.get("groupByProp", {}).get("value"),
        date_property=b.get("dateProp", {}).get("value"),
        sparql_scope=b.get("scope", {}).get("value", "all"),
        scope_query=b.get("scopeQuery", {}).get("value"),
        created_by=b["createdBy"]["value"],
        visibility=b["visibility"]["value"],
        created_at=b.get("createdAt", {}).get("value", ""),
    )


async def _execute_sparql_select(client, sparql: str) -> list[dict]:
    """Run a SPARQL SELECT and return the bindings list, or [] on failure."""
    try:
        result = await client.query(sparql)
        return result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("SPARQL query failed", exc_info=True)
        return []


async def _execute_sparql_ask(client, sparql: str) -> bool:
    """Run a SPARQL ASK and return the boolean result."""
    try:
        result = await client.query(sparql)
        return result.get("boolean", False)
    except Exception:
        logger.warning("SPARQL ASK query failed", exc_info=True)
        return False


async def _get_strategy_folders(
    client,
    strategy: str,
    mount,
    scope_filter: str,
) -> list[dict]:
    """Query folder-level data for a single strategy in the explorer.

    Returns list of dicts with 'value' and 'label' keys suitable for
    mount_tree_folders.html template context.
    """
    from app.vfs.mount_service import MountDefinition

    if strategy == "by-type":
        sparql = query_type_folders(scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        return [
            {"value": b["typeIri"]["value"], "label": b["typeLabel"]["value"]}
            for b in bindings
        ]

    elif strategy == "by-tag":
        if not mount.group_by_property:
            return []
        sparql = query_tag_folders(mount.group_by_property, scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        folders = [
            {"value": b["tagValue"]["value"], "label": b["tagValue"]["value"]}
            for b in bindings
        ]
        ask_sparql = query_has_uncategorized(mount.group_by_property, scope_filter)
        if await _execute_sparql_ask(client, ask_sparql):
            folders.append({"value": "_uncategorized", "label": "Uncategorized"})
        return folders

    elif strategy == "by-date":
        if not mount.date_property:
            return []
        sparql = query_date_year_folders(mount.date_property, scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        return [
            {"value": b["year"]["value"], "label": b["year"]["value"]}
            for b in bindings
        ]

    elif strategy == "by-property":
        if not mount.group_by_property:
            return []
        sparql = query_property_folders(mount.group_by_property, scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        folders = [
            {"value": b["groupValue"]["value"], "label": b["groupLabel"]["value"]}
            for b in bindings
        ]
        ask_sparql = query_has_uncategorized(mount.group_by_property, scope_filter)
        if await _execute_sparql_ask(client, ask_sparql):
            folders.append({"value": "_uncategorized", "label": "Uncategorized"})
        return folders

    return []


def _bindings_to_objects(
    bindings: list[dict],
    labels: dict[str, str],
    icon_svc: IconService,
) -> list[dict]:
    """Convert SPARQL bindings to object dicts for mount tree templates."""
    objects = []
    seen = set()
    for b in bindings:
        iri = b["iri"]["value"]
        if iri in seen:
            continue
        seen.add(iri)
        label = b.get("label", {}).get("value") or labels.get(iri, iri)
        type_iri = b.get("typeIri", {}).get("value", "")
        objects.append({
            "iri": iri,
            "label": label,
            "icon": icon_svc.get_type_icon(type_iri, context="tree") if type_iri else {
                "icon": "circle", "color": "var(--color-text-faint)", "size": 14,
            },
        })
    return objects


async def _handle_mount(
    request: Request,
    mount_id: str,
    label_service: LabelService,
    icon_svc: IconService,
    **_kwargs,
) -> HTMLResponse:
    """Render the explorer tree for a VFS mount by dispatching to its strategy."""
    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    mount = await _get_mount_definition(client, mount_id)
    if mount is None:
        raise HTTPException(status_code=400, detail=f"Unknown mount: {mount_id}")

    logger.debug(
        "Mount explorer tree requested: mount_id=%s, strategy=%s",
        mount_id, mount.strategy,
    )

    scope_filter = build_scope_filter(mount, await _resolve_scope_query_text(client, mount.scope_query))
    strategy = mount.strategy

    # ── Chain mount: show first strategy level folders ──
    if mount.is_chain:
        chain = mount.strategy_chain
        logger.debug("Chain mount initial render: chain=%s", chain)
        first_strategy = chain[0]
        folders = await _get_strategy_folders(client, first_strategy, mount, scope_filter)
        return templates.TemplateResponse(
            request,
            "browser/mount_tree.html",
            {
                "request": request,
                "folders": folders,
                "mount_id": mount_id,
                "mount_name": mount.name,
            },
        )

    # ── flat: render objects directly ──
    if strategy == "flat":
        sparql = query_flat_objects(scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        obj_iris = [b["iri"]["value"] for b in bindings]
        labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}
        objects = _bindings_to_objects(bindings, labels, icon_svc)
        return templates.TemplateResponse(
            request,
            "browser/mount_tree_objects.html",
            {"request": request, "objects": objects},
        )

    # ── by-type: type folders ──
    if strategy == "by-type":
        sparql = query_type_folders(scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        folders = [
            {"value": b["typeIri"]["value"], "label": b["typeLabel"]["value"]}
            for b in bindings
        ]
        return templates.TemplateResponse(
            request,
            "browser/mount_tree.html",
            {
                "request": request,
                "folders": folders,
                "mount_id": mount_id,
                "mount_name": mount.name,
            },
        )

    # ── by-date: year folders ──
    if strategy == "by-date":
        if not mount.date_property:
            return templates.TemplateResponse(
                request,
                "browser/mount_tree.html",
                {
                    "request": request,
                    "folders": [],
                    "mount_id": mount_id,
                    "mount_name": mount.name,
                    "empty_message": "No date property configured for this mount.",
                },
            )
        sparql = query_date_year_folders(mount.date_property, scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        folders = [
            {"value": b["year"]["value"], "label": b["year"]["value"]}
            for b in bindings
        ]
        return templates.TemplateResponse(
            request,
            "browser/mount_tree.html",
            {
                "request": request,
                "folders": folders,
                "mount_id": mount_id,
                "mount_name": mount.name,
            },
        )

    # ── by-tag: tag value folders ──
    if strategy == "by-tag":
        if not mount.group_by_property:
            return templates.TemplateResponse(
                request,
                "browser/mount_tree.html",
                {
                    "request": request,
                    "folders": [],
                    "mount_id": mount_id,
                    "mount_name": mount.name,
                    "empty_message": "No tag property configured for this mount.",
                },
            )
        sparql = query_tag_folders(mount.group_by_property, scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        folders = [
            {"value": b["tagValue"]["value"], "label": b["tagValue"]["value"]}
            for b in bindings
        ]
        # Check for uncategorized
        ask_sparql = query_has_uncategorized(mount.group_by_property, scope_filter)
        if await _execute_sparql_ask(client, ask_sparql):
            folders.append({"value": "_uncategorized", "label": "Uncategorized"})
        return templates.TemplateResponse(
            request,
            "browser/mount_tree.html",
            {
                "request": request,
                "folders": folders,
                "mount_id": mount_id,
                "mount_name": mount.name,
            },
        )

    # ── by-property: property value folders ──
    if strategy == "by-property":
        if not mount.group_by_property:
            return templates.TemplateResponse(
                request,
                "browser/mount_tree.html",
                {
                    "request": request,
                    "folders": [],
                    "mount_id": mount_id,
                    "mount_name": mount.name,
                    "empty_message": "No grouping property configured for this mount.",
                },
            )
        sparql = query_property_folders(mount.group_by_property, scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        folders = [
            {"value": b["groupValue"]["value"], "label": b["groupLabel"]["value"]}
            for b in bindings
        ]
        # Check for uncategorized
        ask_sparql = query_has_uncategorized(mount.group_by_property, scope_filter)
        if await _execute_sparql_ask(client, ask_sparql):
            folders.append({"value": "_uncategorized", "label": "Uncategorized"})
        return templates.TemplateResponse(
            request,
            "browser/mount_tree.html",
            {
                "request": request,
                "folders": folders,
                "mount_id": mount_id,
                "mount_name": mount.name,
            },
        )

    # Unknown strategy — shouldn't happen but handle gracefully
    raise HTTPException(
        status_code=400,
        detail=f"Unknown strategy '{strategy}' on mount {mount_id}",
    )


@workspace_router.get("/icons")
async def icons_data(
    request: Request,
    user: User = Depends(get_current_user),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return icon map for all contexts as JSON for client-side caching."""
    return JSONResponse(content={
        "tree": icon_svc.get_icon_map("tree"),
        "tab": icon_svc.get_icon_map("tab"),
        "graph": icon_svc.get_icon_map("graph"),
    })


@workspace_router.get("/")
async def workspace(
    request: Request,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Render the IDE-style workspace with three-column layout.

    Queries available object types from ShapesService for the navigation
    tree. Full page for direct navigation, content block only for htmx.
    """
    templates = request.app.state.templates
    types = await shapes_service.get_types(exclude_iris=get_hidden_types())
    type_icons = icon_svc.get_icon_map(context="tree")
    from app.config import settings

    context = {
        "request": request,
        "types": types,
        "type_icons": type_icons,
        "active_page": "browser",
        "user": user,
        "base_namespace": settings.base_namespace,
        "demo_mode": settings.demo_mode,
    }

    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "browser/workspace.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "browser/workspace.html", context)


@workspace_router.get("/nav-tree")
async def nav_tree(
    request: Request,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return the nav tree partial (type nodes only, collapsed).

    Used by refreshNavTree() in workspace.js to reload the OBJECTS section.
    Delegates to the by-type handler for consistency.
    """
    return await _handle_by_type(request, shapes_service, icon_svc)


@workspace_router.get("/explorer/tree")
async def explorer_tree(
    request: Request,
    mode: str = "by-type",
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    icon_svc: IconService = Depends(get_icon_service),
    label_service: LabelService = Depends(get_label_service),
):
    """Return explorer tree content for the requested mode.

    Dispatches to the appropriate handler from EXPLORER_MODES.
    Handles ``mount:<uuid>`` prefix to route to VFS mount handler.
    Returns 400 for unknown modes.
    """
    # ── Mount prefix dispatch ──
    if mode.startswith("mount:"):
        mount_id = mode[6:]  # strip "mount:" prefix
        if not _UUID_RE.match(mount_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid mount_id format",
            )
        return await _handle_mount(
            request=request,
            mount_id=mount_id,
            label_service=label_service,
            icon_svc=icon_svc,
        )

    handler = EXPLORER_MODES.get(mode)
    if handler is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown explorer mode: {mode}",
        )

    logger.debug("Explorer tree requested: mode=%s", mode)
    return await handler(
        request=request,
        shapes_service=shapes_service,
        icon_svc=icon_svc,
        label_service=label_service,
    )


@workspace_router.get("/tree/{type_iri:path}")
async def tree_children(
    request: Request,
    type_iri: str,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Load objects of a given type for the navigation tree.

    Queries the current graph for instances of the specified type,
    resolves labels via LabelService, and returns tree leaf nodes
    as an htmx partial.
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client
    decoded_iri = unquote(type_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?obj WHERE {{
      GRAPH <{CURRENT_GRAPH}> {{
        ?obj rdf:type <{decoded_iri}> .
      }}
    }}
    """

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Failed to query objects for type %s", decoded_iri, exc_info=True)
        bindings = []

    obj_iris = [b["obj"]["value"] for b in bindings]
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

    objects = [
        {"iri": iri, "label": labels.get(iri, iri)}
        for iri in obj_iris
    ]

    type_icon = icon_svc.get_type_icon(decoded_iri, context="tree")

    # Resolve type label for nav tree tooltip (phase 19-02)
    type_labels = await label_service.resolve_batch([decoded_iri])
    type_label = type_labels.get(decoded_iri, "")

    context = {"request": request, "objects": objects, "type_icon": type_icon, "type_label": type_label}
    return templates.TemplateResponse(
        request, "browser/tree_children.html", context
    )


@workspace_router.get("/explorer/config-options")
async def explorer_config_options(
    request: Request,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Return available filter/group/sort options for the explorer config builder.

    Returns JSON with:
      - types: available object types (label + IRI)
      - groupable_properties: per-type properties suitable for grouping
      - sort_options: built-in + type-specific sortable properties
    """
    hidden = get_hidden_types()
    types = await shapes_service.get_types(exclude_iris=hidden)
    node_shapes = await shapes_service.get_node_shapes()

    # Build per-type property lists for grouping and sorting
    groupable: dict[str, list[dict]] = {}
    sortable: dict[str, list[dict]] = {}

    for shape in node_shapes:
        if shape.target_class in hidden:
            continue
        type_iri = shape.target_class
        g_props: list[dict] = []
        s_props: list[dict] = []

        for prop in shape.properties:
            prop_entry = {"iri": prop.path, "label": prop.name}
            # Enum-like properties (sh:in) are preferred group candidates
            if prop.in_values:
                prop_entry["preferred_group"] = True
            g_props.append(prop_entry)
            s_props.append(prop_entry)

        groupable[type_iri] = g_props
        sortable[type_iri] = s_props

    return JSONResponse({
        "types": types,
        "group_by_builtins": [
            {"value": "type", "label": "Type"},
            {"value": "tag", "label": "Tag"},
        ],
        "sort_by_builtins": [
            {"value": "label", "label": "Label"},
            {"value": "created", "label": "Date Created"},
        ],
        "groupable_properties": groupable,
        "sortable_properties": sortable,
    })


@workspace_router.get("/explorer/config-tree")
async def explorer_config_tree(
    request: Request,
    type_filter: str | None = None,
    group_by: str | None = None,
    sort_by: str = "label",
    sort_order: str = "asc",
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return a config-driven explorer tree as an htmx partial.

    Accepts filter/group/sort params and returns either grouped folder
    nodes (when group_by is set) or a flat sorted object list.
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    config = ExplorerConfig(
        type_filter=type_filter,
        group_by=group_by,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Build config_params for forwarding to children endpoint
    params_parts: list[str] = []
    if type_filter:
        params_parts.append(f"type_filter={type_filter}")
    if group_by:
        params_parts.append(f"group_by={group_by}")
    if sort_by:
        params_parts.append(f"sort_by={sort_by}")
    if sort_order:
        params_parts.append(f"sort_order={sort_order}")
    config_params = "&".join(params_parts)

    # ── Grouped mode ──
    folders_sparql = build_group_folders_query(config)
    if folders_sparql is not None:
        bindings = await _execute_sparql_select(client, folders_sparql)
        folders = [
            {
                "value": b["groupValue"]["value"],
                "label": b.get("groupLabel", {}).get("value")
                    or b["groupValue"]["value"],
                "count": int(b.get("count", {}).get("value", 0)),
            }
            for b in bindings
        ]
        return templates.TemplateResponse(
            request,
            "browser/explorer_config_tree.html",
            {"request": request, "folders": folders, "config_params": config_params},
        )

    # ── Flat mode ──
    sparql = build_explorer_query(config)
    bindings = await _execute_sparql_select(client, sparql)
    objects = _bindings_to_objects(bindings, {}, icon_svc)
    return templates.TemplateResponse(
        request,
        "browser/explorer_config_tree.html",
        {"request": request, "objects": objects, "config_params": config_params},
    )


@workspace_router.get("/explorer/config-children")
async def explorer_config_children(
    request: Request,
    group_value: str,
    type_filter: str | None = None,
    group_by: str | None = None,
    sort_by: str = "label",
    sort_order: str = "asc",
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return sorted object leaf nodes within a specific group folder.

    Runs the full explorer query filtered to the given group_value, then
    returns matching objects as htmx partial content.
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    config = ExplorerConfig(
        type_filter=type_filter,
        group_by=group_by,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    sparql = build_explorer_query(config)
    bindings = await _execute_sparql_select(client, sparql)

    # Filter bindings to those matching the requested group_value
    filtered = []
    for b in bindings:
        gv = b.get("groupValue", {}).get("value")
        if gv == group_value:
            filtered.append(b)

    objects = _bindings_to_objects(filtered, {}, icon_svc)
    return templates.TemplateResponse(
        request,
        "browser/explorer_config_children.html",
        {"request": request, "objects": objects},
    )


@workspace_router.get("/explorer/children")
async def explorer_children(
    request: Request,
    parent: str,
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return child objects of a parent IRI for hierarchy expansion.

    Queries objects that have dcterms:isPartOf pointing to the parent.
    Used by htmx lazy-loading in the hierarchy tree.
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    if not _validate_iri(parent):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    sparql = f"""
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?obj ?type WHERE {{
      GRAPH <{CURRENT_GRAPH}> {{
        ?obj dcterms:isPartOf <{parent}> .
        ?obj a ?type .
      }}
    }}
    """

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning(
            "Failed to query hierarchy children for %s", parent, exc_info=True
        )
        bindings = []

    # De-duplicate: pick first type per object
    obj_types: dict[str, str] = {}
    for b in bindings:
        iri = b["obj"]["value"]
        if iri not in obj_types:
            obj_types[iri] = b["type"]["value"]

    logger.debug(
        "Hierarchy children query for %s returned %d objects", parent, len(obj_types)
    )

    # Resolve labels and icons
    obj_iris = list(obj_types.keys())
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

    objects = [
        {
            "iri": iri,
            "label": labels.get(iri, iri),
            "type_iri": type_iri,
            "icon": icon_svc.get_type_icon(type_iri, context="tree"),
        }
        for iri, type_iri in obj_types.items()
    ]

    return templates.TemplateResponse(
        request,
        "browser/hierarchy_children.html",
        {"request": request, "objects": objects},
    )


@workspace_router.get("/explorer/tag-children")
async def tag_children(
    request: Request,
    tag: str | None = None,
    prefix: str | None = None,
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return sub-folders or objects for a tag tree node.

    Two modes:
    - ``prefix``: expand a folder — queries all descendant tags, builds
      sub-tree nodes, returns a mix of sub-folders and leaf tags.
      If the prefix itself has directly-tagged objects (direct_count > 0),
      those objects are also fetched and included.
    - ``tag``: expand a leaf tag — queries objects with that exact tag value.

    Used by htmx lazy-loading in the by-tag explorer tree.
    """
    if not tag and not prefix:
        raise HTTPException(
            status_code=400,
            detail="Missing required parameter: tag or prefix",
        )

    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    # ── Prefix mode: sub-folder expansion ──
    if prefix is not None:
        escaped_prefix = sparql_escape_string(prefix)

        # Query all tags that start with "prefix/" (descendants)
        # PLUS the exact prefix value (for direct_count objects)
        sparql = f"""
        SELECT ?tagValue (COUNT(DISTINCT ?iri) AS ?count)
        FROM <{CURRENT_GRAPH}>
        WHERE {{
          {{
            ?iri <urn:sempkm:model:basic-pkm:tags> ?tagValue .
          }}
          UNION
          {{
            ?iri <https://schema.org/keywords> ?tagValue .
          }}
          FILTER(
            STRSTARTS(?tagValue, "{escaped_prefix}/")
            || ?tagValue = "{escaped_prefix}"
          )
        }}
        GROUP BY ?tagValue
        ORDER BY ?tagValue
        """

        bindings = await _execute_sparql_select(client, sparql)
        tag_values = [
            {
                "value": b["tagValue"]["value"],
                "count": int(b["count"]["value"]),
            }
            for b in bindings
        ]

        nodes = build_tag_tree(tag_values, prefix=prefix)

        # Check if the prefix itself has directly-tagged objects
        # (the parent node's direct_count). We need to find the direct
        # count for the exact prefix value in the query results.
        direct_objects: list[dict] = []
        prefix_has_direct = any(
            tv["value"] == prefix for tv in tag_values
        )

        if prefix_has_direct:
            # Fetch actual objects tagged with exactly this prefix value
            escaped_tag = sparql_escape_string(prefix)
            obj_sparql = f"""
            SELECT ?iri ?label ?typeIri
            FROM <{CURRENT_GRAPH}>
            WHERE {{
              {{
                ?iri <urn:sempkm:model:basic-pkm:tags> "{escaped_tag}" .
              }}
              UNION
              {{
                ?iri <https://schema.org/keywords> "{escaped_tag}" .
              }}
              ?iri a ?typeIri .
              {_LABEL_OPTIONALS}
              BIND({_LABEL_COALESCE} AS ?label)
              FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
            }}
            ORDER BY ?label
            """
            obj_bindings = await _execute_sparql_select(client, obj_sparql)
            obj_iris = [b["iri"]["value"] for b in obj_bindings]
            labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}
            direct_objects = _bindings_to_objects(obj_bindings, labels, icon_svc)

        logger.debug(
            "Tag children for prefix '%s': %d sub-nodes, %d direct objects",
            prefix, len(nodes), len(direct_objects),
        )

        return templates.TemplateResponse(
            request,
            "browser/tag_tree_folder.html",
            {
                "request": request,
                "nodes": nodes,
                "direct_objects": direct_objects,
            },
        )

    # ── Tag mode: exact-match object expansion (existing behavior) ──
    escaped_tag = sparql_escape_string(tag)
    sparql = f"""
    SELECT ?iri ?label ?typeIri
    FROM <{CURRENT_GRAPH}>
    WHERE {{
      {{
        ?iri <urn:sempkm:model:basic-pkm:tags> "{escaped_tag}" .
      }}
      UNION
      {{
        ?iri <https://schema.org/keywords> "{escaped_tag}" .
      }}
      ?iri a ?typeIri .
      {_LABEL_OPTIONALS}
      BIND({_LABEL_COALESCE} AS ?label)
      FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
    }}
    ORDER BY ?label
    """

    bindings = await _execute_sparql_select(client, sparql)
    obj_iris = [b["iri"]["value"] for b in bindings]
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}
    objects = _bindings_to_objects(bindings, labels, icon_svc)

    logger.debug("Tag children for '%s': %d objects", tag, len(objects))

    return templates.TemplateResponse(
        request,
        "browser/tag_tree_objects.html",
        {"request": request, "objects": objects},
    )


@workspace_router.get("/explorer/mount-children")
async def mount_children(
    request: Request,
    mount_id: str,
    folder: str,
    subfolder: str | None = None,
    depth: int = 0,
    parent_values: str | None = None,
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return folder contents for VFS mount lazy expansion.

    Dispatches to the correct strategy query builder based on the
    mount's strategy. For ``by-date``, supports two-level expansion
    (year → months, year+month → objects).

    For chain strategies, uses ``depth`` and ``parent_values`` params
    to navigate multi-level folder hierarchies. ``parent_values`` is
    a pipe-delimited string of folder values from parent chain levels.
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    if not _UUID_RE.match(mount_id):
        raise HTTPException(status_code=400, detail="Invalid mount_id format")

    mount = await _get_mount_definition(client, mount_id)
    if mount is None:
        raise HTTPException(status_code=400, detail=f"Unknown mount: {mount_id}")

    logger.debug(
        "Mount children requested: mount_id=%s, folder=%s, strategy=%s, depth=%d",
        mount_id, folder, mount.strategy, depth,
    )

    scope_filter = build_scope_filter(mount, await _resolve_scope_query_text(client, mount.scope_query))
    strategy = mount.strategy

    # ── Chain dispatch ────────────────────────────────────────────────
    if mount.is_chain:
        chain = mount.strategy_chain
        logger.debug(
            "Chain dispatch in mount_children: depth=%d, parent_values=%s, chain=%s",
            depth, parent_values, chain,
        )

        # Build cumulative narrowing from all parent chain levels
        narrowing_parts: list[str] = []
        if parent_values:
            pv_list = parent_values.split("|")
            for i, pv in enumerate(pv_list):
                if i < len(chain):
                    narrowing = build_chain_narrowing_filter(
                        chain[i], pv, mount
                    )
                    if narrowing:
                        narrowing_parts.append(narrowing)
                        logger.debug("Chain narrowing at depth %d: %s", i, pv)

        # Combine base scope + narrowing
        combined_scope = scope_filter
        for part in narrowing_parts:
            combined_scope = f"{combined_scope}\n  {part}" if combined_scope else part

        # Current chain level strategy (from the folder we're expanding)
        # Add the current folder's narrowing
        current_narrowing = build_chain_narrowing_filter(
            chain[depth], folder, mount
        )
        if current_narrowing:
            combined_scope = f"{combined_scope}\n  {current_narrowing}" if combined_scope else current_narrowing

        next_depth = depth + 1

        if next_depth >= len(chain):
            # Terminal level → return objects
            sparql = query_flat_objects(combined_scope)
            bindings = await _execute_sparql_select(client, sparql)
            obj_iris = [b["iri"]["value"] for b in bindings]
            labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}
            objects = _bindings_to_objects(bindings, labels, icon_svc)
            return templates.TemplateResponse(
                request,
                "browser/mount_tree_objects.html",
                {"request": request, "objects": objects},
            )
        else:
            # Non-terminal → return sub-folders for next chain level
            next_strategy = chain[next_depth]
            folders_list = await _get_strategy_folders(
                client, next_strategy, mount, combined_scope
            )
            # Build parent_values for next level
            new_parent_values = f"{parent_values}|{folder}" if parent_values else folder
            return templates.TemplateResponse(
                request,
                "browser/mount_tree_folders.html",
                {
                    "request": request,
                    "folders": folders_list,
                    "mount_id": mount_id,
                    "parent_folder": folder,
                    "chain_depth": next_depth,
                    "chain_parent_values": new_parent_values,
                },
            )

    # ── Non-chain strategies (existing behavior) ──────────────────────

    # ── flat: no folders, should not be called ──
    if strategy == "flat":
        return HTMLResponse("")

    # ── by-type: folder value is the type IRI → list objects of that type ──
    if strategy == "by-type":
        sparql = query_objects_by_type(folder, scope_filter)
        bindings = await _execute_sparql_select(client, sparql)
        obj_iris = [b["iri"]["value"] for b in bindings]
        labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}
        objects = _bindings_to_objects(bindings, labels, icon_svc)
        return templates.TemplateResponse(
            request,
            "browser/mount_tree_objects.html",
            {"request": request, "objects": objects},
        )

    # ── by-date: year → month folders, or year+month → objects ──
    if strategy == "by-date":
        if not mount.date_property:
            return HTMLResponse("")

        if subfolder is None:
            # Expand year → show month sub-folders
            sparql = query_date_month_folders(
                mount.date_property, folder, scope_filter
            )
            bindings = await _execute_sparql_select(client, sparql)
            folders_list = [
                {
                    "value": b["month"]["value"],
                    "label": _MONTH_NAMES[int(b["monthNum"]["value"])]
                    if 1 <= int(b["monthNum"]["value"]) <= 12
                    else b["month"]["value"],
                }
                for b in bindings
            ]
            return templates.TemplateResponse(
                request,
                "browser/mount_tree_folders.html",
                {
                    "request": request,
                    "folders": folders_list,
                    "mount_id": mount_id,
                    "parent_folder": folder,
                },
            )
        else:
            # Expand year+month → show objects
            sparql = query_objects_by_date(
                mount.date_property, folder, int(subfolder), scope_filter
            )
            bindings = await _execute_sparql_select(client, sparql)
            obj_iris = [b["iri"]["value"] for b in bindings]
            labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}
            objects = _bindings_to_objects(bindings, labels, icon_svc)
            return templates.TemplateResponse(
                request,
                "browser/mount_tree_objects.html",
                {"request": request, "objects": objects},
            )

    # ── by-tag: folder value is the tag → list objects with that tag ──
    if strategy == "by-tag":
        if not mount.group_by_property:
            return HTMLResponse("")

        if folder == "_uncategorized":
            sparql = query_uncategorized_objects(
                mount.group_by_property, scope_filter
            )
        else:
            sparql = query_objects_by_tag(
                mount.group_by_property, folder, scope_filter
            )
        bindings = await _execute_sparql_select(client, sparql)
        obj_iris = [b["iri"]["value"] for b in bindings]
        labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}
        objects = _bindings_to_objects(bindings, labels, icon_svc)
        return templates.TemplateResponse(
            request,
            "browser/mount_tree_objects.html",
            {"request": request, "objects": objects},
        )

    # ── by-property: folder value is the property value → list objects ──
    if strategy == "by-property":
        if not mount.group_by_property:
            return HTMLResponse("")

        if folder == "_uncategorized":
            sparql = query_uncategorized_objects(
                mount.group_by_property, scope_filter
            )
        else:
            # Determine if folder value is an IRI
            is_iri = folder.startswith("http://") or folder.startswith("https://") or folder.startswith("urn:")
            sparql = query_objects_by_property(
                mount.group_by_property, folder, is_iri, scope_filter
            )
        bindings = await _execute_sparql_select(client, sparql)
        obj_iris = [b["iri"]["value"] for b in bindings]
        labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}
        objects = _bindings_to_objects(bindings, labels, icon_svc)
        return templates.TemplateResponse(
            request,
            "browser/mount_tree_objects.html",
            {"request": request, "objects": objects},
        )

    return HTMLResponse("")


@workspace_router.get("/my-views")
async def my_views(
    request: Request,
    user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
):
    """Return promoted view entries for the 'My Views' nav tree section.

    Renders browser/my_views.html with the user's promoted views including
    type_filter, scope_query_id, and query_id for display and actions.
    """
    templates = request.app.state.templates

    promoted = await query_service.list_promoted_views(user.id)

    if not promoted:
        return HTMLResponse(
            content='<div class="tree-empty">No promoted views yet</div>'
        )

    context = {
        "request": request,
        "promoted_views": promoted,
    }
    return templates.TemplateResponse(
        request, "browser/my_views.html", context
    )


@workspace_router.post("/admin/migrate-tags")
async def migrate_tags(
    request: Request,
    user: User = Depends(require_role("owner")),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """One-time migration: split comma-separated bpkm:tags into individual triples.

    Finds all bpkm:tags literals containing a comma in the current graph,
    deletes them, and inserts individual trimmed tag triples. Idempotent:
    re-running when no comma-separated values exist is a no-op.

    Requires owner role.
    """
    from app.commands.handlers.object_patch import split_tag_values

    graph_iri = CURRENT_GRAPH
    tags_predicate = "urn:sempkm:model:basic-pkm:tags"

    # Query for all comma-containing tag values
    query = f"""
    SELECT ?s ?val WHERE {{
        GRAPH <{graph_iri}> {{
            ?s <{tags_predicate}> ?val .
        }}
        FILTER(CONTAINS(STR(?val), ","))
    }}
    """

    try:
        result = await client.query(query)
    except Exception:
        logger.exception("Tag migration: failed to query comma-separated tags")
        raise HTTPException(status_code=500, detail="Failed to query tags")

    bindings = result.get("results", {}).get("bindings", [])

    if not bindings:
        logger.info("Tag migration: no comma-separated tags found — nothing to do")
        return JSONResponse({"migrated": 0, "detail": "No comma-separated tags found"})

    migrated_count = 0

    for binding in bindings:
        subject = binding["s"]["value"]
        old_value = binding["val"]["value"]
        new_tags = split_tag_values(old_value)

        if not new_tags:
            # Edge case: value was only commas/whitespace — just delete
            delete_sparql = f"""
            DELETE DATA {{
                GRAPH <{graph_iri}> {{
                    <{subject}> <{tags_predicate}> "{sparql_escape_string(old_value)}" .
                }}
            }}
            """
            await client.update(delete_sparql)
            migrated_count += 1
            continue

        # Build delete + insert in one update
        insert_triples = "\n".join(
            f'        <{subject}> <{tags_predicate}> "{sparql_escape_string(tag)}" .'
            for tag in new_tags
        )
        update_sparql = f"""
        DELETE DATA {{
            GRAPH <{graph_iri}> {{
                <{subject}> <{tags_predicate}> "{sparql_escape_string(old_value)}" .
            }}
        }} ;
        INSERT DATA {{
            GRAPH <{graph_iri}> {{
{insert_triples}
            }}
        }}
        """
        try:
            await client.update(update_sparql)
            migrated_count += 1
            logger.debug(
                "Tag migration: split %s -> %s for %s",
                old_value, new_tags, subject,
            )
        except Exception:
            logger.exception(
                "Tag migration: failed to update tags for %s", subject
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to migrate tags for {subject}",
            )

    logger.info("Tag migration: migrated %d comma-separated tag values", migrated_count)
    return JSONResponse({"migrated": migrated_count})


@workspace_router.post("/admin/migrate-queries")
async def migrate_queries(
    request: Request,
    user: User = Depends(require_role("owner")),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """One-time migration: copy saved queries, shares, promotions, and history
    from SQL tables to the RDF triplestore.

    Idempotent: skips queries whose IRI already exists. Requires owner role.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.session import async_session_factory
    from app.sparql.migrate_queries import migrate_queries_to_rdf

    async with async_session_factory() as db:
        try:
            counts = await migrate_queries_to_rdf(db, client)
            return JSONResponse(counts)
        except Exception:
            logger.exception("Query migration failed")
            raise HTTPException(status_code=500, detail="Query migration failed")


# ---------------------------------------------------------------------------
# Explorer config CRUD API
# ---------------------------------------------------------------------------

def _get_explorer_config_service(request: Request):
    """Get explorer config service from app state."""
    from app.browser.explorer_config_service import ExplorerConfigService
    return request.app.state.explorer_config_service


@workspace_router.get("/api/explorer/configs")
async def list_explorer_configs(
    request: Request,
    user: User = Depends(get_current_user),
):
    """List all explorer configs for the current user plus presets."""
    service = _get_explorer_config_service(request)
    configs = await service.list_for_user(user.id)
    return JSONResponse(content=[
        {
            "id": c.id,
            "name": c.name,
            "config": c.config,
            "is_preset": c.is_preset,
        }
        for c in configs
    ])


@workspace_router.post("/api/explorer/configs")
async def create_explorer_config(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Create a new explorer configuration."""
    service = _get_explorer_config_service(request)
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    config = body.get("config") or body.get("config_json")
    if isinstance(config, str):
        import json as _json
        try:
            config = _json.loads(config)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid config JSON")

    result = await service.create(
        user_id=user.id,
        name=name,
        config=config or {},
    )
    return JSONResponse(
        content={"id": result.id, "name": result.name, "config": result.config},
        status_code=201,
    )


@workspace_router.patch("/api/explorer/configs/{config_id}")
async def update_explorer_config(
    request: Request,
    config_id: str,
    user: User = Depends(get_current_user),
):
    """Update an explorer configuration (name or config)."""
    service = _get_explorer_config_service(request)

    try:
        cid = uuid.UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid config ID")

    body = await request.json()
    updates = {}
    if "name" in body:
        updates["name"] = body["name"]
    if "config" in body:
        updates["config"] = body["config"]
    if "config_json" in body:
        import json as _json
        try:
            updates["config"] = _json.loads(body["config_json"]) if isinstance(body["config_json"], str) else body["config_json"]
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid config JSON")

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    result = await service.update(cid, user.id, **updates)
    if not result:
        raise HTTPException(status_code=404, detail="Config not found")

    return JSONResponse(content={"id": result.id, "name": result.name, "config": result.config})


@workspace_router.delete("/api/explorer/configs/{config_id}")
async def delete_explorer_config(
    request: Request,
    config_id: str,
    user: User = Depends(get_current_user),
):
    """Delete a user explorer configuration. Presets cannot be deleted."""
    service = _get_explorer_config_service(request)

    try:
        cid = uuid.UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid config ID")

    deleted = await service.delete(cid, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found or is a preset")

    return JSONResponse(content={"deleted": True})
