"""Event metadata RDF vocabulary constants.

Defines the RDF predicates used in event named graphs for metadata
(type, timestamp, operation, affected IRIs, description) and the
state graph type marker.
"""

from rdflib import URIRef

from app.rdf.namespaces import SEMPKM

# Event type (rdf:type value for events)
EVENT_TYPE = SEMPKM.Event

# Event metadata predicates
EVENT_TIMESTAMP = SEMPKM.timestamp
EVENT_OPERATION = SEMPKM.operationType
EVENT_AFFECTED = SEMPKM.affectedIRI
EVENT_DESCRIPTION = SEMPKM.description

# User provenance predicates
EVENT_PERFORMED_BY = SEMPKM.performedBy
EVENT_PERFORMED_BY_ROLE = SEMPKM.performedByRole

# System actor IRI for system-initiated operations
SYSTEM_ACTOR_IRI = URIRef("urn:sempkm:system")

# State graph type marker (for sentinel triple)
STATE_GRAPH_TYPE = SEMPKM.StateGraph
