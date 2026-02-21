"""Handler for the edge.patch command.

Updates annotation properties on an existing edge resource. Does NOT allow
modifying source, target, or predicate (those are immutable per design).
"""

from rdflib import URIRef, Variable

from app.commands.schemas import EdgePatchParams
from app.commands.handlers.object_create import _resolve_predicate, _to_rdf_value
from app.events.store import Operation


async def handle_edge_patch(
    params: EdgePatchParams, base_namespace: str
) -> Operation:
    """Handle edge.patch: update annotation properties on an edge resource.

    Only updates annotation properties; source/target/predicate are immutable.
    Same pattern as object.patch: delete old values, insert new values.

    Args:
        params: Validated EdgePatchParams with edge IRI and properties dict.
        base_namespace: Configurable base namespace (unused for patches
            but included for handler interface consistency).

    Returns:
        Operation with data_triples, materialize_inserts, and materialize_deletes.
    """
    subject = URIRef(params.iri)

    data_triples: list[tuple] = []
    materialize_inserts: list[tuple] = []
    materialize_deletes: list[tuple] = []

    for idx, (predicate_str, value) in enumerate(params.properties.items()):
        predicate = _resolve_predicate(predicate_str)
        rdf_value = _to_rdf_value(value)

        # Event graph records what was set
        data_triples.append((subject, predicate, rdf_value))

        # Materialization: delete old, insert new
        materialize_deletes.append(
            (subject, predicate, Variable(f"old_{idx}"))
        )
        materialize_inserts.append((subject, predicate, rdf_value))

    return Operation(
        operation_type="edge.patch",
        affected_iris=[params.iri],
        description=f"Patched edge: {params.iri}",
        data_triples=data_triples,
        materialize_inserts=materialize_inserts,
        materialize_deletes=materialize_deletes,
    )
