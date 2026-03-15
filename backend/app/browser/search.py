"""Search sub-router — reference search and tag suggestions."""

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sparql_escape(value: str) -> str:
    """Escape special characters for SPARQL string literals."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def build_tag_suggestions_sparql(q: str) -> str:
    """Build a SPARQL query to find tag values matching *q*.

    Queries both ``bpkm:tags`` and ``schema:keywords`` via UNION, groups by
    tag value to get a frequency count, and applies a case-insensitive
    CONTAINS filter when *q* is non-empty.

    Returns at most 30 results ordered by frequency DESC then alphabetically.
    """
    filter_clause = ""
    if q:
        escaped_q = _sparql_escape(q)
        filter_clause = (
            f'  FILTER(CONTAINS(LCASE(?tagValue), LCASE("{escaped_q}")))\n'
        )

    sparql = f"""SELECT ?tagValue (COUNT(DISTINCT ?s) AS ?count)
FROM <urn:sempkm:current>
WHERE {{
  {{
    ?s <urn:sempkm:model:basic-pkm:tags> ?tagValue .
  }}
  UNION
  {{
    ?s <https://schema.org/keywords> ?tagValue .
  }}
{filter_clause}}}
GROUP BY ?tagValue
ORDER BY DESC(?count) ?tagValue
LIMIT 30"""
    return sparql


def parse_tag_bindings(bindings: list[dict]) -> list[dict]:
    """Convert SPARQL bindings into ``[{"value": str, "count": int}]``."""
    results = []
    for b in bindings:
        tag_val = b.get("tagValue", {}).get("value", "")
        count = int(b.get("count", {}).get("value", "0"))
        if tag_val:
            results.append({"value": tag_val, "count": count})
    return results


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


# ---------------------------------------------------------------------------
# Tag suggestions endpoint
# ---------------------------------------------------------------------------


@search_router.get("/tag-suggestions")
async def tag_suggestions(
    request: Request,
    q: str = "",
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Return HTML partial with matching tag values for autocomplete.

    Queries both ``bpkm:tags`` and ``schema:keywords`` via UNION.
    When *q* is non-empty, applies case-insensitive CONTAINS filtering.
    Results are ordered by frequency DESC then alphabetically, capped at 30.
    """
    templates = request.app.state.templates

    sparql = build_tag_suggestions_sparql(q)

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Tag suggestions query failed for q='%s'", q, exc_info=True)
        bindings = []

    results = parse_tag_bindings(bindings)

    logger.debug("Tag suggestions for q='%s': %d results", q, len(results))

    return templates.TemplateResponse(
        request,
        "browser/tag_suggestions.html",
        {"request": request, "results": results},
    )
