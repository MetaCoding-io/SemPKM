# T03: 58-federation 03

**Slice:** S58 — **Milestone:** M001

## Description

Shared graph management, sync pull/apply, notification sending, SPARQL graph scoping, and outbound sync alerts.

Purpose: Wire together the foundation from Plans 01-02 into working federation flows. Users can create shared graphs, invite remote users, pull and apply patches from remote instances (with syncSource loop prevention), copy objects into shared graphs, send notifications, see shared graph data in SPARQL queries, and trigger outbound sync-alert notifications when local changes are committed to shared graphs.

Output: `service.py` (FederationService orchestrating all federation logic), extended router with shared graph CRUD and sync endpoints, extended SPARQL scoping for shared graphs wired into query endpoints, outbound LDN alerts on local writes to shared graphs.

## Must-Haves

- [ ] "User can create a shared graph and send an invitation to a remote user's LDN inbox"
- [ ] "Accepting an invitation stores the remote's WebID as a known contact and creates the shared graph locally"
- [ ] "Sync pulls patches from remote instance, applies via EventStore with syncSource tagging"
- [ ] "Events with syncSource are not re-exported back to the originating instance"
- [ ] "User can copy an existing object's triples into a shared graph"
- [ ] "User can send a notification (object recommendation, message) to a remote instance"
- [ ] "SPARQL queries include FROM clauses for shared graphs the user has access to"
- [ ] "Local writes to a shared graph send LDN sync-alert notifications to all remote members"

## Files

- `backend/app/federation/service.py`
- `backend/app/federation/router.py`
- `backend/app/federation/schemas.py`
- `backend/app/sparql/client.py`
- `backend/app/sparql/router.py`
- `backend/app/commands/router.py`
