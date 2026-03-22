"""API endpoints for mirroring federated SPARQL results.

POST /api/sparql/mirror — execute a federated query and mirror results
GET /api/sparql/mirror/endpoints — list allowed federation endpoints
POST /api/sparql/mirror/endpoints — add a federation endpoint (owner-only)
DELETE /api/sparql/mirror/endpoints/{encoded_url} — remove a federation endpoint (owner-only)
GET /api/sparql/mirror/stats — mirror statistics
DELETE /api/sparql/mirror — clear all mirrored data (owner-only)
"""

import logging
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.config import settings
from app.dependencies import get_triplestore_client
from app.sparql.federation_config import (
    add_endpoint,
    get_merged_endpoints,
    remove_endpoint,
)
from app.sparql.mirror import MirrorService
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sparql/mirror", tags=["sparql-mirror"])


class MirrorRequest(BaseModel):
    """Request body for mirror endpoint."""

    query: str
    endpoint_url: str


class AddEndpointRequest(BaseModel):
    """Request body for adding a federation endpoint."""

    url: str


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
    """Return the merged federation endpoint allowlist (env + admin)."""
    merged = get_merged_endpoints()
    return {
        "endpoints": merged,
        "allowlist_configured": len(merged) > 0,
    }


@router.post("/endpoints")
async def add_federation_endpoint(
    body: AddEndpointRequest,
    user: User = Depends(require_role("owner")),
):
    """Add a federation endpoint to the admin-managed allowlist.

    Validates URL format and persists to data/.federation-endpoints.json.
    Returns the updated merged list.
    """
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL: must start with http:// or https://",
        )

    merged = add_endpoint(url)
    logger.info(
        "Federation endpoint added via API: %s (user: %s)", url, user.email
    )
    return {
        "endpoints": merged,
        "allowlist_configured": len(merged) > 0,
    }


@router.delete("/endpoints/{encoded_url:path}")
async def remove_federation_endpoint(
    encoded_url: str,
    user: User = Depends(require_role("owner")),
):
    """Remove an admin-added federation endpoint.

    URL-decodes the path parameter. Refuses to remove env-var-sourced entries.
    Returns the updated merged list.
    """
    url = unquote(encoded_url).strip()

    try:
        merged = remove_endpoint(url)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    logger.info(
        "Federation endpoint removed via API: %s (user: %s)", url, user.email
    )
    return {
        "endpoints": merged,
        "allowlist_configured": len(merged) > 0,
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
