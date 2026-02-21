"""Handler for the object.patch command.

Updates specified properties on an existing object. Generates delete patterns
for old values and insert triples for new values, applied to the current state
graph during materialization.
"""

from rdflib import URIRef, Variable

from app.commands.schemas import ObjectPatchParams
from app.commands.handlers.object_create import _resolve_predicate, _to_rdf_value
from app.events.store import Operation


async def handle_object_patch(
    params: ObjectPatchParams, base_namespace: str
) -> Operation:
    """Handle object.patch: build delete/insert patterns for property updates.

    For each property, creates:
    - A delete pattern (subject, predicate, Variable("old_N")) to remove old values
    - An insert triple (subject, predicate, new_value) to set the new value

    The event graph records the new values (what was set).

    Args:
        params: Validated ObjectPatchParams with iri and properties dict.
        base_namespace: Configurable base namespace (unused for patches but
            included for handler interface consistency).

    Returns:
        Operation with data_triples (new values), materialize_inserts,
        and materialize_deletes (variable patterns).
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

        # Materialization: delete old value, insert new
        materialize_deletes.append(
            (subject, predicate, Variable(f"old_{idx}"))
        )
        materialize_inserts.append((subject, predicate, rdf_value))

    return Operation(
        operation_type="object.patch",
        affected_iris=[params.iri],
        description=f"Patched object: {params.iri}",
        data_triples=data_triples,
        materialize_inserts=materialize_inserts,
        materialize_deletes=materialize_deletes,
    )
