"""API surface routers: well-known discovery and external API endpoints.

The well_known_router serves ``GET /.well-known/sempkm`` — the first
endpoint external clients hit to discover instance capabilities.

The api_surface_router (prefix ``/api``) will host types, shapes,
context-query, sparql, and commands endpoints added in S02+.
"""

import logging

from fastapi import APIRouter, Depends
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
# Response model
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
