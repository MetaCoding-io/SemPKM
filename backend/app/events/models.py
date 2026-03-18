"""Event metadata RDF vocabulary constants.

Defines the RDF predicates used in event named graphs for metadata
(type, timestamp, operation, affected IRIs, description) and the
state graph type marker.

PROV-O Alignment (M006/S01):
- sempkm:timestamp     → prov:startedAtTime
- sempkm:performedBy   → prov:wasAssociatedWith
- sempkm:description   → rdfs:label
- sempkm:Event declared rdfs:subClassOf prov:Activity (D104)

Custom predicates kept (no PROV-O equivalents):
- sempkm:operationType, sempkm:affectedIRI, sempkm:performedByRole
"""

from rdflib import URIRef
from rdflib.namespace import RDFS

from app.rdf.namespaces import PROV, SEMPKM

# Event type (rdf:type value for events)
# Note: sempkm:Event rdfs:subClassOf prov:Activity (D104)
EVENT_TYPE = SEMPKM.Event

# Event metadata predicates (PROV-O aligned)
EVENT_TIMESTAMP = PROV.startedAtTime       # was SEMPKM.timestamp
EVENT_OPERATION = SEMPKM.operationType     # no PROV-O equivalent
EVENT_AFFECTED = SEMPKM.affectedIRI        # no PROV-O equivalent
EVENT_DESCRIPTION = RDFS.label             # was SEMPKM.description

# User provenance predicates
EVENT_PERFORMED_BY = PROV.wasAssociatedWith      # was SEMPKM.performedBy
EVENT_PERFORMED_BY_ROLE = SEMPKM.performedByRole  # no PROV-O equivalent (D090)

# System actor IRI for system-initiated operations
SYSTEM_ACTOR_IRI = URIRef("urn:sempkm:system")

# State graph type marker (for sentinel triple)
STATE_GRAPH_TYPE = SEMPKM.StateGraph

# Bulk event metadata (M009/S05/T03)
BULK_EVENT_TYPE = SEMPKM.BulkEvent
EVENT_SUMMARY = SEMPKM.summary
EVENT_SOURCE = SEMPKM.source
EVENT_OPERATION_COUNT = SEMPKM.operationCount
EVENT_AFFECTED_COUNT = SEMPKM.affectedCount
