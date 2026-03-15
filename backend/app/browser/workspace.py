"""Workspace sub-router — layout, navigation tree, icons, and views."""

import logging
<<<<<<< HEAD
import re
from typing import Callable
=======
>>>>>>> gsd/M002/S04
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
<<<<<<< HEAD

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.dependencies import (
    get_label_service,
    get_query_service,
    get_shapes_service,
    get_triplestore_client,
    get_view_spec_service,
)
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
    SAVED_QUERY_ID,
    SPARQL_SCOPE,
    VISIBILITY,
    MountDefinition,
)
from app.vfs.strategies import (
    _LABEL_COALESCE,
    _LABEL_OPTIONALS,
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
=======
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_db_session
from app.dependencies import (
    get_label_service,
    get_shapes_service,
    get_view_spec_service,
)
from app.services.icons import IconService
from app.services.labels import LabelService
from app.services.shapes import ShapesService
>>>>>>> gsd/M002/S04
from app.views.service import ViewSpecService

from ._helpers import _is_htmx_request, _validate_iri, get_icon_service

<<<<<<< HEAD
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

=======
>>>>>>> gsd/M002/S04
logger = logging.getLogger(__name__)

workspace_router = APIRouter(tags=["workspace"])


<<<<<<< HEAD
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
    types = await shapes_service.get_types()
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

    sparql = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?obj ?type WHERE {
      GRAPH <urn:sempkm:current> {
        ?obj a ?type .
        FILTER NOT EXISTS { ?obj dcterms:isPartOf ?parent . }
      }
    }
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

    sparql = """
    SELECT ?tagValue (COUNT(DISTINCT ?iri) AS ?count)
    FROM <urn:sempkm:current>
    WHERE {
      { ?iri <urn:sempkm:model:basic-pkm:tags> ?tagValue }
      UNION
      { ?iri <https://schema.org/keywords> ?tagValue }
    }
    GROUP BY ?tagValue
    ORDER BY ?tagValue
    """

    bindings = await _execute_sparql_select(client, sparql)

    folders = [
        {
            "value": b["tagValue"]["value"],
            "label": b["tagValue"]["value"],
            "count": int(b["count"]["value"]),
        }
        for b in bindings
    ]

    logger.debug("By-tag explorer: %d tag folders", len(folders))

    return templates.TemplateResponse(
        request,
        "browser/tag_tree.html",
        {"request": request, "folders": folders},
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
               ?scope ?savedQueryId ?createdBy ?visibility ?createdAt
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
          OPTIONAL {{ <{mount_iri}> <{SAVED_QUERY_ID}> ?savedQueryId }}
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
        saved_query_id=b.get("savedQueryId", {}).get("value"),
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

    scope_filter = build_scope_filter(mount)
    strategy = mount.strategy

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


=======
>>>>>>> gsd/M002/S04
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
    types = await shapes_service.get_types()
    type_icons = icon_svc.get_icon_map(context="tree")
    from app.config import settings

    context = {
        "request": request,
        "types": types,
        "type_icons": type_icons,
        "active_page": "browser",
        "user": user,
        "base_namespace": settings.base_namespace,
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
<<<<<<< HEAD
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
=======
    """
    templates = request.app.state.templates
    types = await shapes_service.get_types()
    type_icons = icon_svc.get_icon_map(context="tree")

    return templates.TemplateResponse(
        request,
        "browser/nav_tree.html",
        {"request": request, "types": types, "type_icons": type_icons},
>>>>>>> gsd/M002/S04
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
      GRAPH <urn:sempkm:current> {{
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


<<<<<<< HEAD
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
      GRAPH <urn:sempkm:current> {{
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
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return objects that have a specific tag value (across bpkm:tags and schema:keywords).

    Used by htmx lazy-loading in the by-tag explorer tree.
    """
    if not tag:
        raise HTTPException(status_code=400, detail="Missing required parameter: tag")

    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    escaped_tag = _sparql_escape(tag)
    sparql = f"""
    SELECT ?iri ?label ?typeIri
    FROM <urn:sempkm:current>
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
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return folder contents for VFS mount lazy expansion.

    Dispatches to the correct strategy query builder based on the
    mount's strategy. For ``by-date``, supports two-level expansion
    (year → months, year+month → objects).
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    if not _UUID_RE.match(mount_id):
        raise HTTPException(status_code=400, detail="Invalid mount_id format")

    mount = await _get_mount_definition(client, mount_id)
    if mount is None:
        raise HTTPException(status_code=400, detail=f"Unknown mount: {mount_id}")

    logger.debug(
        "Mount children requested: mount_id=%s, folder=%s, strategy=%s",
        mount_id, folder, mount.strategy,
    )

    scope_filter = build_scope_filter(mount)
    strategy = mount.strategy

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


=======
>>>>>>> gsd/M002/S04
@workspace_router.get("/my-views")
async def my_views(
    request: Request,
    user: User = Depends(get_current_user),
<<<<<<< HEAD
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
    query_service: QueryService = Depends(get_query_service),
=======
    db: AsyncSession = Depends(get_db_session),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
>>>>>>> gsd/M002/S04
):
    """Return promoted view entries for the 'My Views' nav tree section.

    Renders browser/my_views.html with the user's promoted ViewSpecs
    including query_id for the demote action.
    """
    templates = request.app.state.templates

<<<<<<< HEAD
    specs = await view_spec_service.get_user_promoted_view_specs(user.id)
=======
    specs = await view_spec_service.get_user_promoted_view_specs(user.id, db)
>>>>>>> gsd/M002/S04

    if not specs:
        return HTMLResponse(
            content='<div class="tree-empty">No promoted views yet</div>'
        )

<<<<<<< HEAD
    # Build spec_iri -> query_id map from promoted view data
    promoted = await query_service.list_promoted_views(user.id)
    query_id_map = {
        f"urn:sempkm:user-view:{pv.id}": pv.query_id for pv in promoted
=======
    # Also fetch query_ids for demote buttons by querying PromotedQueryView
    from sqlalchemy import select as sa_select

    from app.sparql.models import PromotedQueryView

    pv_result = await db.execute(
        sa_select(PromotedQueryView)
        .where(PromotedQueryView.user_id == user.id)
    )
    pv_rows = pv_result.scalars().all()
    # Map spec_iri -> query_id for the template
    query_id_map = {
        f"urn:sempkm:user-view:{pv.id}": str(pv.query_id) for pv in pv_rows
>>>>>>> gsd/M002/S04
    }

    context = {
        "request": request,
        "specs": specs,
        "query_id_map": query_id_map,
    }
    return templates.TemplateResponse(
        request, "browser/my_views.html", context
    )
<<<<<<< HEAD


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

    graph_iri = "urn:sempkm:current"
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
                    <{subject}> <{tags_predicate}> "{_sparql_escape(old_value)}" .
                }}
            }}
            """
            await client.update(delete_sparql)
            migrated_count += 1
            continue

        # Build delete + insert in one update
        insert_triples = "\n".join(
            f'        <{subject}> <{tags_predicate}> "{_sparql_escape(tag)}" .'
            for tag in new_tags
        )
        update_sparql = f"""
        DELETE DATA {{
            GRAPH <{graph_iri}> {{
                <{subject}> <{tags_predicate}> "{_sparql_escape(old_value)}" .
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


def _sparql_escape(value: str) -> str:
    """Escape special characters for SPARQL string literals."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


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
=======
>>>>>>> gsd/M002/S04
