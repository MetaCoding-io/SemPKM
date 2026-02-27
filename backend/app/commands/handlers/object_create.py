"""Handler for the object.create command.

Creates a new RDF object with a minted IRI, type triple, and property triples.
Returns an Operation for EventStore.commit().
"""

from typing import Any

from rdflib import URIRef, Literal
from rdflib.namespace import RDF

from app.commands.schemas import ObjectCreateParams
from app.events.store import Operation
from app.rdf.iri import mint_object_iri
from app.rdf.namespaces import COMMON_PREFIXES, DATA


def _resolve_predicate(predicate: str) -> URIRef:
    """Resolve a compact IRI (e.g., 'rdfs:label') or full IRI to a URIRef.

    Checks COMMON_PREFIXES for known prefix mappings. If the predicate
    contains '://' it is treated as a full IRI. Otherwise, if it contains
    a ':', it is split on the first ':' and expanded using known prefixes.
    Falls back to using the predicate as a local name under the data namespace.
    """
    # Already a full IRI
    if "://" in predicate or predicate.startswith("urn:"):
        return URIRef(predicate)

    # Compact IRI with known prefix
    if ":" in predicate:
        prefix, local = predicate.split(":", 1)
        namespace = COMMON_PREFIXES.get(prefix)
        if namespace:
            return URIRef(f"{namespace}{local}")
        # Unknown prefix: treat as full IRI attempt
        return URIRef(predicate)

    # Bare local name: use data namespace
    return URIRef(f"{DATA}{predicate}")


def _to_rdf_value(value: Any) -> URIRef | Literal:
    """Convert a Python value to an appropriate rdflib term.

    - Strings starting with 'http://', 'https://', or 'urn:' become URIRefs
    - Other strings become Literals
    - Numbers become typed Literals
    - Booleans become typed Literals
    """
    if isinstance(value, str):
        if value.startswith(("http://", "https://", "urn:")):
            return URIRef(value)
        # Detect ISO 8601 datetime strings → typed xsd:dateTime literal
        if len(value) >= 19 and value[4:5] == "-" and value[7:8] == "-" and "T" in value:
            from rdflib.namespace import XSD
            return Literal(value, datatype=XSD.dateTime)
        return Literal(value)
    elif isinstance(value, bool):
        return Literal(value)
    elif isinstance(value, int):
        return Literal(value)
    elif isinstance(value, float):
        return Literal(value)
    else:
        return Literal(str(value))


async def handle_object_create(
    params: ObjectCreateParams, base_namespace: str
) -> Operation:
    """Handle object.create: mint IRI, build type and property triples.

    Args:
        params: Validated ObjectCreateParams with type, optional slug, and properties.
        base_namespace: Configurable base namespace for IRI minting.

    Returns:
        Operation with data_triples and materialize_inserts for the new object.
    """
    object_iri = mint_object_iri(base_namespace, params.type, params.slug)
    subject = URIRef(object_iri)

    # Type IRI: base_namespace + type name
    type_iri = URIRef(f"{base_namespace.rstrip('/')}/{params.type}")

    triples: list[tuple] = []

    # rdf:type triple
    triples.append((subject, RDF.type, type_iri))

    # Property triples
    for predicate_str, value in params.properties.items():
        predicate = _resolve_predicate(predicate_str)
        rdf_value = _to_rdf_value(value)
        triples.append((subject, predicate, rdf_value))

    return Operation(
        operation_type="object.create",
        affected_iris=[object_iri],
        description=f"Created {params.type}: {params.slug or 'new'}",
        data_triples=triples,
        materialize_inserts=triples,
        materialize_deletes=[],
    )
