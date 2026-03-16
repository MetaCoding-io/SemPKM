"""SPARQL result embed sub-router.

Provides GET /browser/sparql-result/{query_id} for rendering saved
SPARQL query results as standalone HTML tables, primarily for iframe
embedding in the spatial canvas.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.config import settings
from app.dependencies import (
    get_label_service,
    get_prefix_registry,
    get_query_service,
    get_triplestore_client,
)
from app.services.icons import IconService
from app.services.labels import LabelService
from app.services.prefixes import PrefixRegistry
from app.sparql.query_service import QueryService
from app.sparql.router import _execute_sparql, _enrich_sparql_results, _get_icon_service
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

sparql_result_router = APIRouter(tags=["sparql-result"])


@sparql_result_router.get("/sparql-result/{query_id}")
async def sparql_result_embed(
    request: Request,
    query_id: str,
    embed: int = Query(default=1),
    user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
    label_service: LabelService = Depends(get_label_service),
    prefix_registry: PrefixRegistry = Depends(get_prefix_registry),
    icon_service: IconService = Depends(_get_icon_service),
):
    """Render saved SPARQL query results as an HTML table.

    Fetches the saved query by ID, executes it against the triplestore,
    enriches results with labels, and renders as a standalone HTML page
    suitable for iframe embedding.

    Returns 404 if the query ID is not found, 500 if execution fails.
    """
    templates = request.app.state.templates

    # Validate UUID
    try:
        qid = uuid.UUID(query_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid query ID")

    # Fetch saved query (no user_id filter — allow any authenticated user to view)
    saved_query = await query_service.get_query(qid)
    if not saved_query:
        raise HTTPException(status_code=404, detail="Saved query not found")

    # Execute the query
    try:
        raw_results = await _execute_sparql(saved_query.query_text, client)
        if raw_results is None:
            raise HTTPException(status_code=500, detail="Empty query result")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(
            "SPARQL execution failed for query %s: %s",
            query_id, str(e), exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"SPARQL execution failed: {str(e)}",
        )

    # Enrich results with label/type metadata
    try:
        enriched = await _enrich_sparql_results(
            raw_results, label_service, icon_service,
            prefix_registry, client, settings.base_namespace,
        )
    except Exception:
        logger.warning("Failed to enrich SPARQL results", exc_info=True)
        enriched = raw_results

    # Extract column names and rows from SPARQL JSON results
    variables = enriched.get("head", {}).get("vars", [])
    bindings = enriched.get("results", {}).get("bindings", [])
    enrichment = enriched.get("_enrichment", {})

    context = {
        "request": request,
        "query_name": saved_query.name,
        "query_description": getattr(saved_query, "description", "") or "",
        "variables": variables,
        "bindings": bindings,
        "enrichment": enrichment,
        "total_rows": len(bindings),
    }

    response = templates.TemplateResponse(
        request, "browser/sparql_result_embed.html", context
    )
    response.headers["X-Embed-Mode"] = "1"
    return response
