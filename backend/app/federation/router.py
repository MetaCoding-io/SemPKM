"""Federation API endpoints for RDF Patch export and shared graph sync.

Provides endpoints for remote instances to pull patches from shared graphs,
filtered by timestamp and syncSource to prevent infinite sync loops.
"""

import logging

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_triplestore_client
from app.events.store import Operation
from app.federation.patch import serialize_patch
from app.federation.schemas import PatchExportResponse
from app.rdf.namespaces import SEMPKM, XSD
from app.triplestore.client import TriplestoreClient
from rdflib import URIRef, Literal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/federation", tags=["federation"])


@router.get("/patches/{graph_id}", response_model=PatchExportResponse)
async def export_patches(
    graph_id: str,
    since: str = Query(..., description="ISO timestamp to fetch events after"),
    requester: str = Query(
        default="",
        description="Requester instance URL for syncSource filtering (loop prevention)",
    ),
    current_user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
) -> PatchExportResponse:
    """Export RDF Patch for events targeting a shared graph since a timestamp.

    Queries event named graphs that:
    1. Have sempkm:graphTarget matching the shared graph IRI
    2. Have timestamp > since
    3. Do NOT have sempkm:syncSource matching the requester (loop prevention)

    Returns the combined patch text, event count, and metadata.
    """
    graph_iri = f"urn:sempkm:shared:{graph_id}"

    # Build SPARQL to find matching events and their data triples.
    # We query event graphs that target the shared graph and extract
    # all non-metadata triples as inserts for the patch.
    requester_filter = ""
    if requester:
        requester_filter = (
            f'FILTER NOT EXISTS {{ ?event <{SEMPKM.syncSource}> <{requester}> }}'
        )

    sparql = f"""
    SELECT ?event ?timestamp ?s ?p ?o
    WHERE {{
      GRAPH ?event {{
        ?event a <{SEMPKM.Event}> ;
               <{SEMPKM.timestamp}> ?timestamp ;
               <{SEMPKM.graphTarget}> <{graph_iri}> .
        FILTER(?timestamp > "{since}"^^<{XSD.dateTime}>)
        {requester_filter}
        ?s ?p ?o .
        FILTER(?s != ?event)
      }}
    }}
    ORDER BY ?timestamp ?event
    """

    results = await client.query(sparql)
    bindings = results.get("results", {}).get("bindings", [])

    # Group data triples by event
    events_data: dict[str, list[tuple]] = {}
    for row in bindings:
        event_uri = row["event"]["value"]
        s = _binding_to_term(row["s"])
        p = _binding_to_term(row["p"])
        o = _binding_to_term(row["o"])
        if event_uri not in events_data:
            events_data[event_uri] = []
        events_data[event_uri].append((s, p, o))

    # Create Operations from grouped event data (all triples treated as inserts
    # since the event graph stores the "new state" triples)
    operations: list[Operation] = []
    for event_uri, triples in events_data.items():
        op = Operation(
            operation_type="federation.export",
            affected_iris=[event_uri],
            description=f"Exported from event {event_uri}",
            data_triples=[],
            materialize_inserts=triples,
            materialize_deletes=[],
        )
        operations.append(op)

    # Serialize to RDF Patch format
    if operations:
        patch_text = serialize_patch(operations, graph_iri)
    else:
        patch_text = ""

    return PatchExportResponse(
        patch_text=patch_text,
        event_count=len(events_data),
        since=since,
        graph_iri=graph_iri,
    )


def _binding_to_term(binding: dict) -> URIRef | Literal:
    """Convert a SPARQL JSON result binding to an rdflib term."""
    term_type = binding["type"]
    value = binding["value"]

    if term_type == "uri":
        return URIRef(value)
    elif term_type == "literal":
        datatype = binding.get("datatype")
        lang = binding.get("xml:lang")
        if lang:
            return Literal(value, lang=lang)
        elif datatype:
            return Literal(value, datatype=URIRef(datatype))
        else:
            return Literal(value)
    elif term_type == "bnode":
        return URIRef(f"urn:skolem:{value}")
    else:
        return URIRef(value)
