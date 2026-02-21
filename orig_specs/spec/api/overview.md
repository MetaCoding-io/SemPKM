# API Overview (v1)

Reads:
- SPARQL endpoint

Writes:
- Minimal command API that writes to the event log:
  - object.create
  - object.patch
  - body.set
  - edge.create
  - edge.patch
  - (optional) delete/tombstone commands
  - publish.trigger

SPARQL UPDATE is not a supported external write surface.