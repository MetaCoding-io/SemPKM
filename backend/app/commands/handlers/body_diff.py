"""Handler for the body.diff command.

Stores an incremental body diff alongside the full new body content.
The diff text is stored via sempkm:bodyDiff for event log rendering,
while the full body is stored via the body predicate for materialization.
Materialization is identical to body.set — delete old body, insert new.
"""

from rdflib import URIRef, Literal, Variable
from rdflib.namespace import XSD

from app.commands.schemas import BodyDiffParams
from app.events.store import Operation
from app.rdf.namespaces import SEMPKM


async def handle_body_diff(
    params: BodyDiffParams, base_namespace: str
) -> Operation:
    """Handle body.diff: store an incremental diff and replace the body.

    Stores two data triples in the event graph:
    1. (subject, sempkm:bodyDiff, diff_text) — the unified diff
    2. (subject, predicate, body) — the full new body

    Materialization mirrors body.set: delete old body, insert new body.

    Args:
        params: Validated BodyDiffParams with iri, body, diff_text.
        base_namespace: Configurable base namespace (unused for body.diff
            but included for handler interface consistency).

    Returns:
        Operation with data_triples (diff + new body), materialize_inserts,
        and materialize_deletes (old body pattern).
    """
    subject = URIRef(params.iri)
    predicate = URIRef(params.predicate) if params.predicate else SEMPKM.body
    canonical = SEMPKM.body
    body_literal = Literal(params.body, datatype=XSD.string)
    diff_literal = Literal(params.diff_text, datatype=XSD.string)

    # Event graph records both the diff and the new full body
    data_triples = [
        (subject, SEMPKM.bodyDiff, diff_literal),
        (subject, predicate, body_literal),
    ]

    # Materialization: delete old body under target predicate, insert new
    materialize_deletes = [(subject, predicate, Variable("old_body"))]
    materialize_inserts = [(subject, predicate, body_literal)]

    # If saving to a model-specific predicate, also clean up any leftover
    # canonical urn:sempkm:body value to avoid duplication
    if predicate != canonical:
        materialize_deletes.append(
            (subject, canonical, Variable("old_canonical_body"))
        )

    return Operation(
        operation_type="body.diff",
        affected_iris=[params.iri],
        description=f"Diff body on: {params.iri}",
        data_triples=data_triples,
        materialize_inserts=materialize_inserts,
        materialize_deletes=materialize_deletes,
    )
