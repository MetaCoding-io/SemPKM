"""Event metadata RDF vocabulary constants.

Defines the RDF predicates used in event named graphs for metadata
(type, timestamp, operation, affected IRIs, description) and the
state graph type marker.
"""

from app.rdf.namespaces import SEMPKM

# Event type (rdf:type value for events)
EVENT_TYPE = SEMPKM.Event

# Event metadata predicates
EVENT_TIMESTAMP = SEMPKM.timestamp
EVENT_OPERATION = SEMPKM.operationType
EVENT_AFFECTED = SEMPKM.affectedIRI
EVENT_DESCRIPTION = SEMPKM.description

# User provenance predicate
EVENT_PERFORMED_BY = SEMPKM.performedBy

# State graph type marker (for sentinel triple)
STATE_GRAPH_TYPE = SEMPKM.StateGraph
