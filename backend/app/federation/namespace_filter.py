"""Namespace filtering for incoming federation triples.

Rejects triples that reference system-managed namespaces to prevent
remote instances from injecting ontology definitions, SHACL shapes,
or internal metadata into the local graph.
"""

import logging

from rdflib import URIRef

logger = logging.getLogger(__name__)

# Namespaces that are system-managed and must not arrive via federation.
# urn:sempkm:shared: is explicitly allowed — it's the federation graph itself.
_BLOCKED_IRI_PREFIXES = (
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/ns/shacl#",
)

_BLOCKED_SEMPKM_PREFIX = "urn:sempkm:"
_ALLOWED_SEMPKM_PREFIX = "urn:sempkm:shared:"

# rdf:type predicate — used for the OWL/SHACL class check
_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

# OWL and SHACL class IRIs that must not be instantiated via federation
_BLOCKED_TYPE_OBJECTS = frozenset({
    "http://www.w3.org/2002/07/owl#Class",
    "http://www.w3.org/2002/07/owl#ObjectProperty",
    "http://www.w3.org/2002/07/owl#DatatypeProperty",
    "http://www.w3.org/2002/07/owl#AnnotationProperty",
    "http://www.w3.org/2002/07/owl#Ontology",
    "http://www.w3.org/2002/07/owl#Restriction",
    "http://www.w3.org/ns/shacl#NodeShape",
    "http://www.w3.org/ns/shacl#PropertyShape",
    "http://www.w3.org/ns/shacl#Shape",
})


def _is_blocked_iri(iri_str: str) -> bool:
    """Check if an IRI belongs to a blocked namespace.

    Returns True if the IRI is in a blocked system namespace.
    urn:sempkm:shared:* is explicitly allowed.
    """
    if iri_str.startswith(_ALLOWED_SEMPKM_PREFIX):
        return False
    if iri_str.startswith(_BLOCKED_SEMPKM_PREFIX):
        return True
    for prefix in _BLOCKED_IRI_PREFIXES:
        if iri_str.startswith(prefix):
            return True
    return False


def filter_federation_triples(
    triples: list[tuple],
) -> tuple[list[tuple], list[tuple]]:
    """Split incoming federation triples into allowed and rejected sets.

    Rejection rules:
    1. Any triple where s, p, or o is an IRI in a blocked namespace
       (urn:sempkm:* except urn:sempkm:shared:*, owl:#, sh:#)
    2. Any rdf:type triple where the object is an OWL or SHACL class
       (prevents ontology/shape injection)

    Args:
        triples: List of (subject, predicate, object) tuples with rdflib terms.

    Returns:
        Tuple of (allowed, rejected) triple lists.
    """
    allowed: list[tuple] = []
    rejected: list[tuple] = []

    for triple in triples:
        s, p, o = triple
        s_str = str(s)
        p_str = str(p)
        o_str = str(o)

        # Rule 1: block any triple touching a blocked namespace
        if _is_blocked_iri(s_str) or _is_blocked_iri(p_str) or _is_blocked_iri(o_str):
            rejected.append(triple)
            continue

        # Rule 2: block rdf:type assertions for OWL/SHACL classes
        if p_str == _RDF_TYPE and o_str in _BLOCKED_TYPE_OBJECTS:
            rejected.append(triple)
            continue

        allowed.append(triple)

    return allowed, rejected
