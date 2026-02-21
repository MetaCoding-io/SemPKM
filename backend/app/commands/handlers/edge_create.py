"""Handler for the edge.create command.

Creates a first-class edge resource with its own IRI (per user decision).
Edges have source, target, predicate, and optional annotation properties.
"""

from rdflib import URIRef
from rdflib.namespace import RDF

from app.commands.schemas import EdgeCreateParams
from app.commands.handlers.object_create import _resolve_predicate, _to_rdf_value
from app.events.store import Operation
from app.rdf.iri import mint_edge_iri
from app.rdf.namespaces import SEMPKM


async def handle_edge_create(
    params: EdgeCreateParams, base_namespace: str
) -> Operation:
    """Handle edge.create: mint edge IRI and build relationship triples.

    Creates triples for:
    - rdf:type sempkm:Edge
    - sempkm:source -> source IRI
    - sempkm:target -> target IRI
    - sempkm:predicate -> predicate IRI
    - Any annotation properties on the edge resource

    Args:
        params: Validated EdgeCreateParams with source, target, predicate,
            and optional properties.
        base_namespace: Configurable base namespace for edge IRI minting.

    Returns:
        Operation with data_triples and materialize_inserts for the edge resource.
    """
    edge_iri = mint_edge_iri(base_namespace)
    edge = URIRef(edge_iri)
    source = URIRef(params.source)
    target = URIRef(params.target)
    predicate_iri = _resolve_predicate(params.predicate)

    triples: list[tuple] = []

    # Edge type
    triples.append((edge, RDF.type, SEMPKM.Edge))

    # Structural properties (immutable after creation)
    triples.append((edge, SEMPKM.source, source))
    triples.append((edge, SEMPKM.target, target))
    triples.append((edge, SEMPKM.predicate, predicate_iri))

    # Optional annotation properties
    for predicate_str, value in params.properties.items():
        prop_predicate = _resolve_predicate(predicate_str)
        rdf_value = _to_rdf_value(value)
        triples.append((edge, prop_predicate, rdf_value))

    return Operation(
        operation_type="edge.create",
        affected_iris=[edge_iri, params.source, params.target],
        description=f"Created edge: {params.source} -> {params.target}",
        data_triples=triples,
        materialize_inserts=triples,
        materialize_deletes=[],
    )
