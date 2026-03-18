"""API surface routers: well-known discovery and external API endpoints.

The well_known_router serves ``GET /.well-known/sempkm`` — the first
endpoint external clients hit to discover instance capabilities.

The api_surface_router (prefix ``/api``) hosts types, shapes,
context-query, sparql, and commands endpoints.
"""

import logging
import re

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.config import settings

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
    icon_service = request.app.state.icon_service
    model_service = request.app.state.model_service

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
