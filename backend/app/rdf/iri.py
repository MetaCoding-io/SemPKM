"""IRI minting functions for SemPKM objects, edges, and events.

Follows the user-decided IRI patterns:
- Objects: {namespace}/{Type}/{slug-or-uuid}
- Edges: {namespace}/Edge/{uuid}
- Events: urn:sempkm:event:{uuid}
"""

import uuid
from urllib.parse import quote

from rdflib import URIRef


def mint_object_iri(
    base_namespace: str,
    type_name: str,
    slug: str | None = None,
) -> str:
    """Mint an IRI for a new object.

    Pattern: {namespace}/{Type}/{slug-or-uuid}
    Example: https://example.org/data/Person/alice

    Args:
        base_namespace: The configurable base namespace (e.g., https://example.org/data/).
        type_name: The type local name (e.g., "Person"). Used as-is.
        slug: Optional human-readable slug. Falls back to UUID if not provided.

    Returns:
        The minted IRI string.
    """
    identifier = slug if slug else str(uuid.uuid4())
    safe_id = quote(identifier, safe="")
    return f"{base_namespace.rstrip('/')}/{type_name}/{safe_id}"


def mint_edge_iri(base_namespace: str) -> str:
    """Mint an IRI for a new edge resource.

    Edges always get UUIDs (no human-readable slugs) per user decision.
    Pattern: {namespace}/Edge/{uuid}

    Args:
        base_namespace: The configurable base namespace.

    Returns:
        The minted IRI string.
    """
    return f"{base_namespace.rstrip('/')}/Edge/{uuid.uuid4()}"


def mint_event_iri() -> URIRef:
    """Mint an IRI for a new event graph.

    Uses URN scheme per research recommendation.
    Pattern: urn:sempkm:event:{uuid}

    Returns:
        A URIRef for the event graph.
    """
    return URIRef(f"urn:sempkm:event:{uuid.uuid4()}")
