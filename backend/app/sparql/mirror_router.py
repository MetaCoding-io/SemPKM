"""API endpoints for mirroring federated SPARQL results.

POST /api/sparql/mirror — execute a federated query and mirror results
GET /api/sparql/mirror/endpoints — list allowed federation endpoints
GET /api/sparql/mirror/stats — mirror statistics
DELETE /api/sparql/mirror — clear all mirrored data (owner-only)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.config import settings
from app.dependencies import get_triplestore_client
from app.sparql.mirror import MirrorService
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sparql/mirror", tags=["sparql-mirror"])


class MirrorRequest(BaseModel):
    """Request body for mirror endpoint."""

    query: str
    endpoint_url: str


@router.post("")
async def mirror_results(
    body: MirrorRequest,
    user: User = Depends(require_role("owner")),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Execute a federated SPARQL query and mirror results locally.

    Validates the endpoint against the configured allowlist, executes the
    query via the triplestore (which handles SERVICE clause federation),
    then stores the results in urn:sempkm:mirrored with provenance.
    """
    service = MirrorService(client)

    # Validate endpoint against allowlist
    if not service.validate_endpoint(body.endpoint_url):
        logger.warning(
            "Mirror: blocked endpoint %s (user: %s)",
            body.endpoint_url,
            user.email,
        )
        raise HTTPException(
            status_code=403,
            detail=f"Endpoint not in allowlist: {body.endpoint_url}",
        )

    # Execute the query — RDF4J handles SERVICE clause federation natively
    try:
        result = await client.query(body.query)
    except Exception as e:
        logger.error("Mirror: query execution failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to execute federated query: {str(e)}",
        )

    bindings = result.get("results", {}).get("bindings", [])
    vars_list = result.get("head", {}).get("vars", [])

    if not bindings:
        return {
            "mirrored_count": 0,
            "provenance_graph": None,
            "message": "Query returned no results to mirror",
        }

    # Mirror the results
    try:
        mirror_result = await service.mirror_results(
            bindings=bindings,
            vars=vars_list,
            endpoint_url=body.endpoint_url,
        )
    except Exception as e:
        logger.error("Mirror: storage failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store mirrored triples: {str(e)}",
        )

    return {
        "mirrored_count": mirror_result.triple_count,
        "provenance_graph": mirror_result.provenance_graph,
    }


@router.get("/endpoints")
async def list_endpoints(
    user: User = Depends(get_current_user),
):
    """Return the configured federation endpoint allowlist."""
    endpoints = settings.get_allowed_endpoints()
    return {
        "endpoints": endpoints,
        "allowlist_configured": len(endpoints) > 0,
    }


@router.get("/stats")
async def mirror_stats(
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Return statistics about mirrored data."""
    service = MirrorService(client)
    stats = await service.get_mirror_stats()
    return stats


@router.delete("")
async def clear_mirrored(
    user: User = Depends(require_role("owner")),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Clear all mirrored triples and provenance graphs. Owner-only."""
    service = MirrorService(client)
    count = await service.clear_mirrored()
    return {
        "cleared_count": count,
        "message": f"Cleared {count} mirrored triples and all provenance graphs",
    }
