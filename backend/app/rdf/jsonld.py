"""JSON-LD serialization utilities for SemPKM.

Provides the SemPKM JSON-LD context and helper functions for
converting rdflib Graphs to compacted JSON-LD output. The context
is served locally (never references external URLs) per research
Pitfall 4.
"""

import json

from rdflib import Graph, URIRef, Literal, BNode


# SemPKM JSON-LD context with prefix mappings
SEMPKM_CONTEXT: dict = {
    "@context": {
        "sempkm": "urn:sempkm:",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "schema": "https://schema.org/",
        "dcterms": "http://purl.org/dc/terms/",
        "skos": "http://www.w3.org/2004/02/skos/core#",
    }
}


def graph_to_jsonld(graph: Graph) -> dict:
    """Serialize an rdflib Graph to compacted JSON-LD with SemPKM context.

    Args:
        graph: The rdflib Graph to serialize.

    Returns:
        A dict containing the JSON-LD representation with @context.
    """
    jsonld_str = graph.serialize(
        format="json-ld",
        context=SEMPKM_CONTEXT["@context"],
    )
    return json.loads(jsonld_str)


def triples_to_jsonld(
    subject_iri: str,
    triples: list[tuple],
) -> dict:
    """Build a small graph from triples and serialize to JSON-LD.

    Convenience function for API responses. Creates a temporary graph,
    adds the provided triples, and serializes with the SemPKM context.

    Args:
        subject_iri: The primary subject IRI (used for documentation, not filtering).
        triples: List of (subject, predicate, object) tuples using rdflib terms.

    Returns:
        A dict containing the JSON-LD representation with @context.
    """
    g = Graph()
    for s, p, o in triples:
        g.add((s, p, o))
    return graph_to_jsonld(g)
