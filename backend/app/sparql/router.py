"""SPARQL read endpoint for querying the current state graph.

Supports GET and POST (both form-encoded and JSON body) per the SPARQL
Protocol standard. Automatically injects common prefixes and scopes
queries to the current state graph to prevent event graph data leakage.
"""

import logging

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse, Response

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_triplestore_client
from app.sparql.client import inject_prefixes, scope_to_current_graph
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


async def _execute_sparql(
    query: str,
    client: TriplestoreClient,
    all_graphs: bool = False,
) -> Response:
    """Process a SPARQL query: inject prefixes, scope to current graph, execute.

    Args:
        query: Raw SPARQL query string from the user.
        client: Triplestore client for query execution.
        all_graphs: If True, skip current graph scoping (admin/debug).

    Returns:
        Response with SPARQL results JSON or error.
    """
    if not query or not query.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Empty query"},
        )

    try:
        # Apply prefix injection then graph scoping
        processed = inject_prefixes(query)
        processed = scope_to_current_graph(processed, all_graphs=all_graphs)

        logger.debug("Executing SPARQL: %s", processed[:200])

        result = await client.query(processed)

        return JSONResponse(
            content=result,
            media_type="application/sparql-results+json",
        )

    except Exception as e:
        error_msg = str(e)
        logger.warning("SPARQL query failed: %s", error_msg)

        # Distinguish between bad queries (4xx) and triplestore errors (5xx)
        if "400" in error_msg or "MalformedQuery" in error_msg:
            return JSONResponse(
                status_code=400,
                content={"error": f"Malformed SPARQL query: {error_msg}"},
            )

        return JSONResponse(
            status_code=502,
            content={"error": f"Triplestore error: {error_msg}"},
        )


@router.get("/sparql")
async def sparql_get(
    query: str = Query(..., description="SPARQL query string"),
    all_graphs: bool = Query(False, description="Skip current graph scoping"),
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
) -> Response:
    """Execute a SPARQL query via GET (query as URL parameter).

    Standard SPARQL Protocol GET endpoint. Queries are automatically
    scoped to the current state graph unless all_graphs=true.
    """
    return await _execute_sparql(query, client, all_graphs=all_graphs)


@router.post("/sparql")
async def sparql_post(
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
) -> Response:
    """Execute a SPARQL query via POST.

    Accepts two content types:
    - application/x-www-form-urlencoded: Standard SPARQL Protocol (query=...)
    - application/json: Convenience format ({"query": "...", "all_graphs": false})

    Queries are automatically scoped to the current state graph unless
    all_graphs is set to true.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            query = body.get("query", "")
            all_graphs = body.get("all_graphs", False)
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid JSON body"},
            )
    else:
        # Default: form-encoded (application/x-www-form-urlencoded)
        form = await request.form()
        query = form.get("query", "")
        all_graphs = form.get("all_graphs", "false").lower() == "true"

    return await _execute_sparql(query, client, all_graphs=all_graphs)
