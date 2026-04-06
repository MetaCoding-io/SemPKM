"""API surface routers: well-known discovery and external API endpoints.

The well_known_router serves ``GET /.well-known/sempkm`` — the first
endpoint external clients hit to discover instance capabilities.

The api_surface_router (prefix ``/api``) hosts types, shapes,
context-query, sparql, and commands endpoints.
"""

import logging
import re

from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.config import settings
from app.services.icons import IconService
from app.services.search import SearchService
from app.sparql.builder import sparql_escape_string
from app.rdf.namespaces import CURRENT_GRAPH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Version constant — used in the discovery document.
# Reads from settings.app_version so it can be overridden via env var.
# ---------------------------------------------------------------------------

APP_VERSION = settings.app_version

# ---------------------------------------------------------------------------
# IRI convention parser for model attribution
# ---------------------------------------------------------------------------

_MODEL_IRI_PATTERN = re.compile(r"^urn:sempkm:model:([^:]+):")


def _extract_model_id(type_iri: str) -> str | None:
    """Extract model_id from a type IRI following the convention.

    Convention: ``urn:sempkm:model:{model_id}:TypeName``
    Returns None for IRIs that don't match this pattern.
    """
    m = _MODEL_IRI_PATTERN.match(type_iri)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class InstanceInfo(BaseModel):
    """Discovery document returned by ``GET /.well-known/sempkm``.

    External clients use this to learn what endpoints are available,
    which auth methods the instance accepts, and what capabilities
    are enabled.
    """

    version: str
    endpoints: dict[str, str]
    auth: dict[str, bool | str]
    capabilities: list[str]


class TypeInfo(BaseModel):
    """A single type available in the instance."""

    iri: str
    label: str
    icon: str | None = None
    icon_color: str | None = None
    model_id: str | None = None
    model_name: str | None = None


class TypesResponse(BaseModel):
    """Response for GET /api/types."""

    types: list[TypeInfo]


class PropertyShapeInfo(BaseModel):
    """A single SHACL property shape (form field) serialized to JSON."""

    path: str
    name: str
    datatype: str | None = None
    target_class: str | None = None
    order: float = 0.0
    group: str | None = None
    min_count: int = 0
    max_count: int | None = None
    in_values: list[str] = []
    default_value: str | None = None
    description: str | None = None
    helptext: str | None = None


class PropertyGroupInfo(BaseModel):
    """A SHACL property group (form section) serialized to JSON."""

    iri: str
    label: str
    order: float = 0.0


class ShapeResponse(BaseModel):
    """Response for GET /api/shapes/{type_iri}."""

    shape_iri: str
    target_class: str
    label: str
    groups: list[PropertyGroupInfo] = []
    properties: list[PropertyShapeInfo] = []
    helptext: str | None = None


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

well_known_router = APIRouter(tags=["api-discovery"])

api_surface_router = APIRouter(prefix="/api", tags=["api-surface"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@well_known_router.get(
    "/.well-known/sempkm",
    response_model=InstanceInfo,
    summary="Instance discovery",
    description=(
        "Returns a JSON document describing this SemPKM instance: "
        "its version, available API endpoints, supported auth methods, "
        "and enabled capabilities. Requires authentication."
    ),
)
async def get_well_known(
    user: User = Depends(get_current_user_or_api),
) -> InstanceInfo:
    """Return the instance discovery document.

    This is the first endpoint external clients (browser extensions,
    CLI tools, federation peers) should call to learn how to interact
    with this instance.
    """
    logger.debug("well-known requested by user=%s", user.email)
    return InstanceInfo(
        version=APP_VERSION,
        endpoints={
            "types": "/api/types",
            "shapes": "/api/shapes/{type_iri}",
            "context_query": "/api/context-query",
            "sparql": "/api/sparql",
            "commands": "/api/commands",
        },
        auth={
            "session": True,
            "api_key": True,
            "indieauth": "/auth/authorize",
        },
        capabilities=[
            "types",
            "shapes",
            "context-query",
            "sparql",
            "commands",
        ],
    )


# ---------------------------------------------------------------------------
# GET /api/types — list all available types from installed models
# ---------------------------------------------------------------------------


@api_surface_router.get(
    "/types",
    response_model=TypesResponse,
    summary="List available types",
    description=(
        "Returns all types from installed Mental Models with labels, "
        "Lucide icon names, icon colors, and model attribution."
    ),
)
async def get_types(
    request: Request,
    user: User = Depends(get_current_user_or_api),
) -> TypesResponse:
    """Return all available types from installed models.

    Combines data from ShapesService (type IRIs + labels),
    IconService (Lucide icon names + colors), and ModelService
    (model name lookup by model_id extracted from type IRI).
    """
    shapes_service = request.app.state.shapes_service
    model_service = request.app.state.model_service

    # Create IconService ad-hoc (matches codebase pattern — not on app.state)
    from app.config import settings as _settings
    _models_dir = str(Path("/app/models"))
    icon_service = IconService(models_dir=_models_dir, extra_dirs=[_settings.marketplace_models_dir])
    user_icons = getattr(request.app.state, "user_type_icons", None)
    if user_icons:
        icon_service.set_user_type_icons(user_icons)

    # Get type list from SHACL shapes
    raw_types = await shapes_service.get_types()

    # Get icon map for tree context (includes Lucide icon name + color)
    icon_map = icon_service.get_icon_map("tree")

    # Build model name lookup from installed models
    model_name_map: dict[str, str] = {}
    try:
        installed = await model_service.list_models()
        model_name_map = {m.model_id: m.name for m in installed}
    except Exception:
        logger.warning("Failed to load model names for /api/types", exc_info=True)

    # Merge into TypeInfo list
    type_infos: list[TypeInfo] = []
    for t in raw_types:
        iri = t["iri"]
        label = t["label"]
        icon_entry = icon_map.get(iri)
        model_id = _extract_model_id(iri)

        type_infos.append(
            TypeInfo(
                iri=iri,
                label=label,
                icon=icon_entry["icon"] if icon_entry else None,
                icon_color=icon_entry["color"] if icon_entry else None,
                model_id=model_id,
                model_name=model_name_map.get(model_id) if model_id else None,
            )
        )

    logger.debug("GET /api/types returning %d types for user=%s", len(type_infos), user.email)
    return TypesResponse(types=type_infos)


# ---------------------------------------------------------------------------
# GET /api/shapes/{type_iri} — property shapes for a specific type
# ---------------------------------------------------------------------------


@api_surface_router.get(
    "/shapes/{type_iri:path}",
    response_model=ShapeResponse,
    summary="Get property shapes for a type",
    description=(
        "Returns SHACL property shapes for a given type IRI as structured "
        "JSON. Includes property constraints (min/max count, allowed values), "
        "property groups, and helptext — everything needed to render a "
        "dynamic form for the type."
    ),
)
async def get_shapes(
    type_iri: str,
    request: Request,
    user: User = Depends(get_current_user_or_api),
) -> ShapeResponse:
    """Return SHACL property shapes for a specific type.

    Calls ShapesService.get_form_for_type() which returns a NodeShapeForm
    dataclass. The dataclass fields map 1:1 to the Pydantic response model.
    Returns 404 if no shape is found for the given type IRI.
    """
    shapes_service = request.app.state.shapes_service
    form = await shapes_service.get_form_for_type(type_iri)

    if form is None:
        logger.debug("No shape found for type_iri=%s, user=%s", type_iri, user.email)
        raise HTTPException(
            status_code=404,
            detail=f"No shape found for type: {type_iri}",
        )

    # Convert dataclass → Pydantic via asdict (fields match 1:1)
    groups = [PropertyGroupInfo(**asdict(g)) for g in form.groups]
    properties = [PropertyShapeInfo(**asdict(p)) for p in form.properties]

    logger.debug(
        "GET /api/shapes/%s returning %d properties, %d groups for user=%s",
        type_iri, len(properties), len(groups), user.email,
    )
    return ShapeResponse(
        shape_iri=form.shape_iri,
        target_class=form.target_class,
        label=form.label,
        groups=groups,
        properties=properties,
        helptext=form.helptext,
    )


# ---------------------------------------------------------------------------
# Context-query models
# ---------------------------------------------------------------------------


class ContextQueryRequest(BaseModel):
    """Request body for POST /api/context-query.

    At least one of url, title, or keywords must be provided.
    """

    url: str | None = None
    title: str | None = None
    keywords: str | None = None


class ContextResult(BaseModel):
    """A single result from the context query."""

    iri: str
    label: str
    type_iri: str | None = None
    type_label: str | None = None
    match_type: str
    snippet: str | None = None


class ContextQueryResponse(BaseModel):
    """Response for POST /api/context-query."""

    results: list[ContextResult]
    total: int


# ---------------------------------------------------------------------------
# POST /api/context-query — find related objects by URL/title/keywords
# ---------------------------------------------------------------------------


@api_surface_router.post(
    "/context-query",
    response_model=ContextQueryResponse,
    summary="Find related objects by page context",
    description=(
        "Accepts page metadata (URL, title, keywords) and returns "
        "related objects from the knowledge graph. Combines exact URL "
        "matching via SPARQL with keyword matching via LuceneSail FTS. "
        "Results are deduplicated and enriched with labels and types."
    ),
)
async def context_query(
    body: ContextQueryRequest,
    request: Request,
    user: User = Depends(get_current_user_or_api),
) -> ContextQueryResponse:
    """Find objects related to the given page context.

    URL matching: SPARQL query finds any object that has a property
    whose string value exactly matches the given URL.

    Keyword matching: combines title + keywords into a search string
    and runs FTS via SearchService (LuceneSail).

    Results are merged, deduplicated by IRI, and enriched with labels
    (via LabelService) and types (via SPARQL rdf:type query).
    """
    # --- Validation: at least one field required ---
    if not body.url and not body.title and not body.keywords:
        raise HTTPException(
            status_code=400,
            detail="At least one of url, title, or keywords is required",
        )

    triplestore = request.app.state.triplestore_client
    label_service = request.app.state.label_service
    search_service: SearchService = request.app.state.search_service

    # Collect results keyed by IRI → match_type (first match wins)
    matched: dict[str, str] = {}  # iri → match_type
    snippets: dict[str, str] = {}  # iri → snippet (from FTS)

    # --- URL matching via SPARQL ---
    if body.url:
        escaped_url = sparql_escape_string(body.url)
        url_sparql = (
            f"SELECT DISTINCT ?s WHERE {{ "
            f"GRAPH <{CURRENT_GRAPH}> {{ "
            f'?s ?p ?val . FILTER(STR(?val) = "{escaped_url}") '
            f"}} }} LIMIT 20"
        )
        try:
            url_result = await triplestore.query(url_sparql)
            bindings = url_result.get("results", {}).get("bindings", [])
            for row in bindings:
                iri = row.get("s", {}).get("value", "")
                if iri and iri not in matched:
                    matched[iri] = "url"
        except Exception:
            logger.warning(
                "Context-query URL matching failed for url=%s",
                body.url,
                exc_info=True,
            )

    # --- Keyword matching via SearchService (FTS / LuceneSail) ---
    search_text_parts: list[str] = []
    if body.title:
        search_text_parts.append(body.title)
    if body.keywords:
        search_text_parts.append(body.keywords)
    search_text = " ".join(search_text_parts).strip()

    if search_text:
        try:
            fts_results = await search_service.search(search_text, limit=20)
            for sr in fts_results:
                if sr.iri not in matched:
                    match_type = "title" if body.title and not body.keywords else "keyword"
                    matched[sr.iri] = match_type
                if sr.snippet and sr.iri not in snippets:
                    snippets[sr.iri] = sr.snippet
        except Exception:
            logger.warning(
                "Context-query keyword matching failed for text=%r",
                search_text,
                exc_info=True,
            )

    # --- Empty results fast-path ---
    if not matched:
        logger.debug(
            "POST /api/context-query: 0 results for user=%s (url=%s, title=%s, keywords=%s)",
            user.email, body.url, body.title, body.keywords,
        )
        return ContextQueryResponse(results=[], total=0)

    all_iris = list(matched.keys())

    # --- Resolve labels ---
    labels: dict[str, str] = {}
    try:
        labels = await label_service.resolve_batch(all_iris)
    except Exception:
        logger.warning("Context-query label resolution failed", exc_info=True)

    # --- Resolve types via SPARQL ---
    type_map: dict[str, str] = {}  # iri → type_iri
    values_clause = " ".join(f"(<{iri}>)" for iri in all_iris)
    type_sparql = (
        f"SELECT ?s ?type WHERE {{ "
        f"GRAPH <{CURRENT_GRAPH}> {{ "
        f"VALUES (?s) {{ {values_clause} }} "
        "?s a ?type "
        f"}} }}"
    )
    try:
        type_result = await triplestore.query(type_sparql)
        for row in type_result.get("results", {}).get("bindings", []):
            iri = row.get("s", {}).get("value", "")
            type_iri = row.get("type", {}).get("value", "")
            if iri and type_iri and iri not in type_map:
                type_map[iri] = type_iri
    except Exception:
        logger.warning("Context-query type resolution failed", exc_info=True)

    # --- Resolve type labels ---
    type_labels: dict[str, str] = {}
    unique_type_iris = list(set(type_map.values()))
    if unique_type_iris:
        try:
            type_labels = await label_service.resolve_batch(unique_type_iris)
        except Exception:
            logger.warning("Context-query type label resolution failed", exc_info=True)

    # --- Build response ---
    results: list[ContextResult] = []
    for iri, match_type in matched.items():
        type_iri = type_map.get(iri)
        results.append(
            ContextResult(
                iri=iri,
                label=labels.get(iri, iri),
                type_iri=type_iri,
                type_label=type_labels.get(type_iri, None) if type_iri else None,
                match_type=match_type,
                snippet=snippets.get(iri),
            )
        )

    logger.debug(
        "POST /api/context-query: %d results for user=%s (url=%s, title=%s, keywords=%s)",
        len(results), user.email, body.url, body.title, body.keywords,
    )
    return ContextQueryResponse(results=results, total=len(results))
