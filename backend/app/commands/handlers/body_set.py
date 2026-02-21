"""Handler for the body.set command.

Sets an object's Markdown body content using the sempkm:body predicate.
Replaces any existing body with the new content.
"""

from rdflib import URIRef, Literal, Variable
from rdflib.namespace import XSD

from app.commands.schemas import BodySetParams
from app.events.store import Operation
from app.rdf.namespaces import SEMPKM


async def handle_body_set(
    params: BodySetParams, base_namespace: str
) -> Operation:
    """Handle body.set: replace the Markdown body of an object.

    Uses sempkm:body as the predicate. Deletes any existing body value
    and inserts the new one.

    Args:
        params: Validated BodySetParams with iri and body content.
        base_namespace: Configurable base namespace (unused for body.set
            but included for handler interface consistency).

    Returns:
        Operation with data_triples (new body), materialize_inserts,
        and materialize_deletes (old body pattern).
    """
    subject = URIRef(params.iri)
    predicate = SEMPKM.body
    body_literal = Literal(params.body, datatype=XSD.string)

    # Event graph records the new body
    data_triples = [(subject, predicate, body_literal)]

    # Materialization: delete old body, insert new
    materialize_deletes = [(subject, predicate, Variable("old_body"))]
    materialize_inserts = [(subject, predicate, body_literal)]

    return Operation(
        operation_type="body.set",
        affected_iris=[params.iri],
        description=f"Set body on: {params.iri}",
        data_triples=data_triples,
        materialize_inserts=materialize_inserts,
        materialize_deletes=materialize_deletes,
    )
