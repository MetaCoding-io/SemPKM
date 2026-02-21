"""SemPKM namespace definitions and common prefix mappings.

Provides rdflib Namespace objects for the SemPKM system namespace,
user data namespace, and standard RDF vocabularies. Also defines
the current state graph IRI and a COMMON_PREFIXES dict for SPARQL
prefix injection.
"""

from rdflib import Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS, SKOS

from app.config import settings

# SemPKM system namespace for events, state graph, metadata
SEMPKM = Namespace("urn:sempkm:")

# User data namespace, dynamically constructed from settings
DATA = Namespace(settings.base_namespace)

# Standard vocabularies (re-exported for convenience)
__all__ = [
    "SEMPKM",
    "DATA",
    "RDF",
    "RDFS",
    "XSD",
    "DCTERMS",
    "SKOS",
    "SCHEMA",
    "CURRENT_GRAPH_IRI",
    "COMMON_PREFIXES",
]

# Schema.org namespace
SCHEMA = Namespace("https://schema.org/")

# The current state graph identifier
CURRENT_GRAPH_IRI = URIRef("urn:sempkm:current")

# Common prefix mappings for SPARQL injection and JSON-LD contexts
COMMON_PREFIXES: dict[str, str] = {
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "xsd": str(XSD),
    "sempkm": str(SEMPKM),
    "schema": str(SCHEMA),
    "dcterms": str(DCTERMS),
    "skos": str(SKOS),
}
