"""SemPKM namespace definitions and common prefix mappings.

Provides rdflib Namespace objects for the SemPKM system namespace,
user data namespace, and standard RDF vocabularies. Also defines
the current state graph IRI and a COMMON_PREFIXES dict for SPARQL
prefix injection.
"""

from rdflib import Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD, DCTERMS, SKOS

from app.config import settings

# SemPKM system namespace for events, state graph, metadata
SEMPKM = Namespace("urn:sempkm:")

# User data namespace, dynamically constructed from settings
DATA = Namespace(settings.base_namespace)

# Additional vocabularies not in rdflib.namespace
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
PROV = Namespace("http://www.w3.org/ns/prov#")
LDP = Namespace("http://www.w3.org/ns/ldp#")
AS = Namespace("https://www.w3.org/ns/activitystreams#")
GIST = Namespace("https://w3id.org/semanticarts/ns/ontology/gist/")

# Standard vocabularies (re-exported for convenience)
__all__ = [
    "SEMPKM",
    "DATA",
    "RDF",
    "RDFS",
    "OWL",
    "XSD",
    "SH",
    "DCTERMS",
    "SKOS",
    "SCHEMA",
    "FOAF",
    "PROV",
    "LDP",
    "AS",
    "GIST",
    "CURRENT_GRAPH_IRI",
    "INFERRED_GRAPH_IRI",
    "MIRRORED_GRAPH_IRI",
    "CURRENT_GRAPH",
    "INFERRED_GRAPH",
    "MIRRORED_GRAPH",
    "MODELS_GRAPH",
    "QUERIES_GRAPH",
    "VALIDATIONS_GRAPH",
    "USER_TYPES_GRAPH",
    "GIST_GRAPH",
    "FEDERATION_GRAPH",
    "WEBHOOKS_GRAPH",
    "MOUNTS_GRAPH",
    "TASK_TEMPLATES_GRAPH",
    "OPS_LOG_GRAPH",
    "COMMON_PREFIXES",
]

# Schema.org namespace
SCHEMA = Namespace("https://schema.org/")

# The current state graph identifier
CURRENT_GRAPH_IRI = URIRef("urn:sempkm:current")

# The inferred triples graph identifier (OWL 2 RL inference results)
INFERRED_GRAPH_IRI = URIRef("urn:sempkm:inferred")

# The mirrored triples graph identifier (federated SPARQL results cached locally)
MIRRORED_GRAPH_IRI = URIRef("urn:sempkm:mirrored")

# ── Named graph identifiers (string form for SPARQL interpolation) ──────────
# Canonical source for all urn:sempkm:* graph names.
# Import from here — never define a local copy.

CURRENT_GRAPH = "urn:sempkm:current"
INFERRED_GRAPH = "urn:sempkm:inferred"
MIRRORED_GRAPH = "urn:sempkm:mirrored"
MODELS_GRAPH = "urn:sempkm:models"
QUERIES_GRAPH = "urn:sempkm:queries"
VALIDATIONS_GRAPH = "urn:sempkm:validations"
USER_TYPES_GRAPH = "urn:sempkm:user-types"
GIST_GRAPH = "urn:sempkm:ontology:gist"
FEDERATION_GRAPH = "urn:sempkm:federation"
WEBHOOKS_GRAPH = "urn:sempkm:webhooks"
MOUNTS_GRAPH = "urn:sempkm:mounts"
TASK_TEMPLATES_GRAPH = "urn:sempkm:task-templates"
OPS_LOG_GRAPH = "urn:sempkm:ops-log"

# Common prefix mappings for SPARQL injection and JSON-LD contexts
COMMON_PREFIXES: dict[str, str] = {
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "owl": str(OWL),
    "xsd": str(XSD),
    "sh": str(SH),
    "sempkm": str(SEMPKM),
    "schema": str(SCHEMA),
    "dcterms": str(DCTERMS),
    "skos": str(SKOS),
    "foaf": str(FOAF),
    "prov": str(PROV),
    "ldp": str(LDP),
    "as": str(AS),
    "gist": str(GIST),
}
