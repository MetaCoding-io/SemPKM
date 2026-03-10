# Phase 58: Federation - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

SemPKM instances can sync knowledge and exchange notifications with other instances using standard protocols. Users create shared named graphs that replicate between instances via RDF Patch. Notifications (invitations, recommendations, sync alerts, messages) flow through W3C Linked Data Notifications. Authentication uses HTTP Signatures (RFC 9421) against WebID public keys. Real-time collaborative editing (CRDTs) is explicitly deferred to a future phase.

</domain>

<decisions>
## Implementation Decisions

### Sync Model & Granularity
- **Shared named graphs** — both sides agree on a shared graph (named space) that replicates. Everything outside stays private. Like a shared folder with clear boundaries.
- **Separate named graphs per shared space** — each shared graph gets its own RDF4J named graph (`urn:sempkm:shared:{uuid}`). Private data stays in `urn:sempkm:current`. SPARQL queries use FROM clauses to union private + all shared graphs the user has access to.
- **Manual sync now, automatic polling later** — ship "Sync Now" button first. Design data model to support automatic polling but don't implement the background job. Future phase adds the scheduler.
- **Last-write-wins for conflicts** — whichever change has the later timestamp overwrites. Acceptable for rare conflicts in a personal-first PKM with manual sync. Overwritten edits preserved in event history (recoverable). Data model designed so a CRDT could replace LWW later.
- **Copy to shared graph** — user shares an object by copying its triples into a shared graph. Private original remains. Two independent copies — edits to the shared copy sync, edits to the private copy don't.
- **Both create-in and copy-to** — users can create new objects directly in a shared graph (graph selector in creation form) AND copy existing private objects into one.
- **Dangling references at boundaries** — when a shared object references a private object, the edge syncs but the target doesn't exist on the remote. Show as an unresolved link ("External: Alice's Instance"). No data leaks.
- **Same Mental Model required** — both instances must have the same model installed to share objects of that type. Invitation flow checks model compatibility. No model data syncs.
- **Leave = read-only snapshot** — when a user leaves a shared graph, sync stops but data remains as a frozen snapshot. Objects marked "no longer synced." User can delete manually.

### RDF Patch & Event Sync
- **Derive patches from event operations** — each event's `materialize_inserts` become A (Add) lines and `materialize_deletes` become D (Delete) lines in the RDF Patch format.
- **Timestamp-based ordering with UUID tiebreaker** — use existing `sempkm:timestamp` for "since" queries. Event UUID string comparison as tiebreaker for same-millisecond events. No new sequence field needed.
- **SyncSource tagging at event store level** — when applying remote patches, `EventStore.commit()` includes a `sempkm:syncSource` predicate (remote instance URL) in event metadata. Events with a syncSource are never exported back to that source. Prevents infinite loops.
- **Both pull and push authenticated** — pulling and pushing patches require HTTP Signature verification against the remote's WebID public key. Shared graphs are private — only registered remotes can access.

### Notifications & Inbox
- **Four notification types**: shared graph invitations, object recommendations, sync status alerts, free-form messages (markdown supported)
- **Sidebar panel** — "Inbox" panel in sidebar with badge count for unread. Shows notification list with per-type actions.
- **Send flow** — right-click object for "Send to remote..." (recommendations); Collaboration panel for invitations, messages, and shared graph management.
- **Stored in RDF** — LDN notifications stored as named graphs (`urn:sempkm:inbox:{uuid}`) in the triplestore. JSON-LD in, RDF stored. Consistent with project convention of keeping semantic data in RDF.
- **Notification states** — unread, read, acted, dismissed. Never deleted. Inbox shows unread+read; archive view for acted+dismissed.
- **Object recommendation actions** — show label, type, summary fetched from remote. User can Import (copy to private graph), Open Remote (link to source), or Dismiss.
- **Sync status alerts pushed via LDN** — when changes are committed to a shared graph, the instance sends an LDN notification to all remote members with patch count. Remote sees alert in inbox with "Sync Now" action.
- **LDN inbox discoverable via Link header** — `Link: </api/inbox>; rel="http://www.w3.org/ns/ldp#inbox"` on WebID profile response. Also as `ldp:inbox` triple in RDF profile. W3C LDN standard discovery.
- **All incoming notifications authenticated** — require HTTP Signature verification. Reject unsigned with 401.

### Remote Trust & Discovery
- **Invitation is introduction** — no separate "register remote" step. When a user accepts a shared graph invitation, the remote's WebID is stored as a known contact. Collaboration panel shows remotes derived from shared graphs.
- **First contact: WebID URL or WebFinger handle** — single input field accepts either a full WebID URL (`https://...`) or a `user@domain` handle. Auto-detects format. Each instance exposes `/.well-known/webfinger` endpoint for handle resolution.
- **Propose + accept for shared graphs** — Alice creates a shared graph and sends LDN invitation to Bob's WebID inbox URL. Bob sees invitation, accepts or declines. On accept, both instances create the named graph and start syncing.
- **RFC 9421 HTTP Message Signatures** — implement current IETF standard with Ed25519 (existing key type). Python library: `http-message-signatures`. No legacy cavage draft — SemPKM-to-SemPKM only.
- **WebID public key cache** — TTL cache (1 hour, 64 entries) for fetched WebID profiles and public keys. Force-refresh on signature verification failure (handles key rotation). Pattern matches existing LabelService TTLCache.

### Collaboration UI
- **Sidebar panel** — "Collaboration" panel showing shared graphs with sync status, remote contacts, and "New shared graph" button.
- **Nav tree shared section** — separate "SHARED" section below existing type groups. Each shared graph is a collapsible group showing its objects by type. Shared objects show a subtle share icon.
- **Minimal sync status** — last sync timestamp + count of local changes not yet pushed. Green dot (<24h), yellow (>24h), gray (never synced).
- **Toast notifications for sync results** — after "Sync Now" completes, brief toast showing pulled/pushed counts. Open tabs auto-refresh if their object changed. No disruptive modal.

### Claude's Discretion
- Exact RDF Patch serialization format (header, transaction markers)
- WebFinger JRD response structure
- HTTP Signature covered component selection
- Shared graph UUID generation and naming conventions
- Inbox notification RDF vocabulary (ActivityStreams types)
- Toast notification styling and duration
- Sync error handling and retry behavior
- Graph selector UI in object creation form

</decisions>

<specifics>
## Specific Ideas

- CRDT for RDF is the future (NextGraph, W3C CRDT for RDF CG) but no production Python library exists today. LWW conflict strategy designed to be replaceable by CRDT later.
- Shared named graphs model inspired by Matrix rooms — each shared graph is like a room that both instances participate in.
- Keeping all semantic data in RDF (not SQL) for federation data — notifications, sync state, shared graph metadata. SQL stays scoped to auth.
- WebFinger enables email-like handles (`bob@instance.com`) alongside full WebID URLs for a friendlier UX.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/webid/service.py`: Ed25519 key generation, encrypted storage, WebID profile RDF construction — federation signs requests with these keys
- `backend/app/webid/router.py`: Content-negotiated `/users/{username}` endpoint — add `ldp:inbox` Link header and RDF triple here
- `backend/app/indieauth/`: Complete OAuth2 provider — IndieAuth for browser auth, HTTP Signatures for server-to-server
- `backend/app/events/store.py`: `EventStore.commit()` with `Operation` dataclass — add `sempkm:syncSource` predicate and derive RDF Patch from `materialize_inserts`/`materialize_deletes`
- `backend/app/events/query.py`: Event query with timestamp filtering — extend for "events since T on graph G" sync export
- `backend/app/triplestore/client.py`: Transaction support (begin/commit/rollback) — use for atomic patch application
- `backend/app/rdf/namespaces.py`: Namespace registry — add LDP, AS (ActivityStreams) namespaces
- `LabelService._cache` (TTLCache pattern) — reuse for WebID public key caching

### Established Patterns
- Named graph isolation: events in `urn:sempkm:event:{uuid}`, current state in `urn:sempkm:current` — extend with `urn:sempkm:shared:{uuid}` and `urn:sempkm:inbox:{uuid}`
- SPARQL graph scoping via `scope_to_current_graph()` in `sparql/client.py` — extend to union shared graphs
- Sidebar panels with drag-reorder (`[data-panel-name]` + `[data-drop-zone]`) — add Inbox and Collaboration panels
- Context menu pattern from Phase 55 (multi-select, bulk actions) — extend with "Send to remote..."
- Link headers on WebID profile response — add `ldp:inbox` alongside existing `indieauth-metadata`

### Integration Points
- `sparql/client.py` `scope_to_current_graph()` — must add FROM clauses for shared graphs the user has access to
- `commands/router.py` — object creation needs graph target parameter
- `events/store.py` `EventStore.commit()` — materialization must target correct graph (private or shared)
- `webid/router.py` — add `ldp:inbox` Link header and WebFinger endpoint
- Nav tree template — add SHARED section with shared graph groups
- Workspace sidebar — add Inbox and Collaboration panels

</code_context>

<deferred>
## Deferred Ideas

- **CRDT-based real-time sync** — W3C CRDT for RDF CG standardizing, NextGraph in alpha. Replace LWW with CRDT when mature Python library exists. Data model designed to accommodate this.
- **Automatic sync polling** — background job checking remotes on interval. Data model supports it; implement scheduler in a future phase.
- **Fediverse interop** — legacy cavage HTTP Signatures + RSA for Mastodon/ActivityPub compatibility. Add if fediverse interop becomes a goal.
- **Detailed sync history/log** — expandable sync log per shared graph showing recent operations. Currently minimal status only.
- **Conflict review UI** — visual diff + resolution when CRDT isn't handling conflicts. Deferred since LWW is the current strategy.

</deferred>

---

*Phase: 58-federation*
*Context gathered: 2026-03-10*
