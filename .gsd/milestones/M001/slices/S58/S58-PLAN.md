# S58: Federation

**Goal:** RDF Patch serialization, EventStore extensions for federation, and patch export API.
**Demo:** RDF Patch serialization, EventStore extensions for federation, and patch export API.

## Must-Haves


## Tasks

- [x] **T01: 58-federation 01** `est:5min`
  - RDF Patch serialization, EventStore extensions for federation, and patch export API.

Purpose: Establish the data foundation for federation sync. Events must be convertible to RDF Patch format (A/D lines), the EventStore must support targeting shared named graphs and tagging remote-originated events with syncSource to prevent infinite sync loops, and an API endpoint must allow remote instances to pull patches since a given timestamp.

Output: `backend/app/federation/` module with patch.py, schemas.py, router.py; extended EventStore with target_graph and sync_source parameters; LDP and AS namespaces added.
- [x] **T02: 58-federation 02** `est:7min`
  - HTTP Signature authentication, WebFinger discovery, and LDN inbox receiver.

Purpose: Establish the security and notification foundations for federation. All server-to-server requests must be signed and verified using RFC 9421 HTTP Message Signatures with Ed25519 keys (already in WebID profiles). The LDN inbox endpoint receives notifications from remote instances. WebFinger enables email-like handle discovery (user@domain -> WebID URL).

Output: `signatures.py` (sign/verify wrappers using http-message-signatures library), `webfinger.py` (server + client), `inbox.py` (POST /api/inbox receiver storing in RDF), WebID profile Link header for inbox discovery, WebFinger router registered in main.py.
- [x] **T03: 58-federation 03** `est:15min`
  - Shared graph management, sync pull/apply, notification sending, SPARQL graph scoping, and outbound sync alerts.

Purpose: Wire together the foundation from Plans 01-02 into working federation flows. Users can create shared graphs, invite remote users, pull and apply patches from remote instances (with syncSource loop prevention), copy objects into shared graphs, send notifications, see shared graph data in SPARQL queries, and trigger outbound sync-alert notifications when local changes are committed to shared graphs.

Output: `service.py` (FederationService orchestrating all federation logic), extended router with shared graph CRUD and sync endpoints, extended SPARQL scoping for shared graphs wired into query endpoints, outbound LDN alerts on local writes to shared graphs.
- [x] **T04: 58-federation 04** `est:6min`
  - Inbox notification UI, collaboration panel, and nav tree shared section.

Purpose: Give users a workspace interface for federation features -- viewing and acting on notifications, managing shared graphs and remote contacts, seeing shared data in the nav tree, and triggering manual sync. This completes the user-facing federation experience.

Output: Inbox sidebar panel (notification list with per-type actions), Collaboration sidebar panel (shared graphs, contacts, sync controls), SHARED nav tree section (shared graph objects by type), federation.js/css for interactions.

## Files Likely Touched

- `backend/app/federation/__init__.py`
- `backend/app/federation/patch.py`
- `backend/app/federation/schemas.py`
- `backend/app/federation/router.py`
- `backend/app/events/store.py`
- `backend/app/rdf/namespaces.py`
- `backend/app/main.py`
- `backend/app/federation/signatures.py`
- `backend/app/federation/webfinger.py`
- `backend/app/federation/inbox.py`
- `backend/app/webid/router.py`
- `backend/app/main.py`
- `backend/pyproject.toml`
- `backend/app/federation/service.py`
- `backend/app/federation/router.py`
- `backend/app/federation/schemas.py`
- `backend/app/sparql/client.py`
- `backend/app/sparql/router.py`
- `backend/app/commands/router.py`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/partials/inbox_panel.html`
- `backend/app/templates/browser/partials/collaboration_panel.html`
- `backend/app/templates/browser/partials/shared_nav_section.html`
- `frontend/static/js/federation.js`
- `frontend/static/css/federation.css`
- `backend/app/federation/router.py`
- `backend/app/browser/router.py`
