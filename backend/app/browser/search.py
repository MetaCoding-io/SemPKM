"""Search sub-router — reference search for sh:class fields."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_label_service, get_triplestore_client
from app.services.labels import LabelService
from app.triplestore.client import TriplestoreClient

from ._helpers import _validate_iri

logger = logging.getLogger(__name__)

search_router = APIRouter(tags=["search"])


@search_router.get("/search")
async def search_references(
    request: Request,
    type: str = "",
    q: str = "",
    field_id: str = "",
    index: str | None = None,
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Search for instances of a type for sh:class reference fields.

    Queries the current state graph for objects matching the given rdf:type
    and filtering by label regex. Returns HTML suggestion items for the
    search-as-you-type dropdown.
    """
    templates = request.app.state.templates

    if not type:
        return HTMLResponse(content="", status_code=200)

    if not _validate_iri(type):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    # Build SPARQL query to find instances of the type
    sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?obj WHERE {{
      GRAPH <urn:sempkm:current> {{
        ?obj rdf:type <{type}> .
      }}
    }}
    LIMIT 20
    """

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Reference search failed for type %s", type, exc_info=True)
        bindings = []

    obj_iris = [b["obj"]["value"] for b in bindings]
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

    # Filter by query string if provided
    results = []
    query_lower = q.lower() if q else ""
    for iri in obj_iris:
        label = labels.get(iri, iri)
        if not query_lower or query_lower in label.lower() or query_lower in iri.lower():
            results.append({"iri": iri, "label": label})

    # Resolve type label for the "Create new..." option
    type_labels = await label_service.resolve_batch([type])
    type_label = type_labels.get(type, type.rsplit("/", 1)[-1] if "/" in type else type)

    context = {
        "request": request,
        "results": results,
        "type_iri": type,
        "type_label": type_label,
        "field_id": field_id,
        "index": int(index) if index is not None and index.isdigit() else None,
    }

    return templates.TemplateResponse(
        request, "browser/search_suggestions.html", context
    )
