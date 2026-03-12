# T01: 58-federation 01

**Slice:** S58 — **Milestone:** M001

## Description

RDF Patch serialization, EventStore extensions for federation, and patch export API.

Purpose: Establish the data foundation for federation sync. Events must be convertible to RDF Patch format (A/D lines), the EventStore must support targeting shared named graphs and tagging remote-originated events with syncSource to prevent infinite sync loops, and an API endpoint must allow remote instances to pull patches since a given timestamp.

Output: `backend/app/federation/` module with patch.py, schemas.py, router.py; extended EventStore with target_graph and sync_source parameters; LDP and AS namespaces added.

## Must-Haves

- [ ] "Event operations can be serialized as RDF Patch text with A (Add) and D (Delete) lines"
- [ ] "API endpoint returns patches for a shared graph since a given timestamp"
- [ ] "Events created with a syncSource are excluded from patch export to that same source"
- [ ] "Objects copied to a shared graph appear in that graph rather than the private graph"

## Files

- `backend/app/federation/__init__.py`
- `backend/app/federation/patch.py`
- `backend/app/federation/schemas.py`
- `backend/app/federation/router.py`
- `backend/app/events/store.py`
- `backend/app/rdf/namespaces.py`
- `backend/app/main.py`
