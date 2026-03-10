# Phase 58: Federation - Research

**Researched:** 2026-03-10
**Domain:** RDF federation (sync, notifications, HTTP signatures, WebFinger)
**Confidence:** MEDIUM

## Summary

Phase 58 adds federation capabilities to SemPKM: shared named graphs that sync between instances via RDF Patch, notifications via W3C Linked Data Notifications (LDN), server-to-server authentication via RFC 9421 HTTP Message Signatures with Ed25519 keys, and discovery via WebFinger. The scope is substantial -- it touches the event store, SPARQL scoping, triplestore client, command API, WebID subsystem, and workspace UI (sidebar panels, nav tree sections, bottom panel).

The architecture builds on strong existing foundations: Ed25519 keys already exist in WebID profiles, the event store's `Operation` dataclass with `materialize_inserts`/`materialize_deletes` maps directly to RDF Patch A/D lines, and the triplestore client already supports transactions. The main complexity lies in (1) wiring `syncSource` tagging into EventStore to prevent infinite sync loops, (2) extending SPARQL graph scoping to union shared graphs, and (3) implementing HTTP Signature signing/verification using the `http-message-signatures` library.

No production Python libraries exist for RDF Patch, LDN, or WebFinger -- these are simple enough protocols that hand-implementing them is the correct approach. The `http-message-signatures` library (v2.0.1, Jan 2026) handles RFC 9421 with Ed25519 support. The main risk is the breadth of the phase -- 10 requirements spanning backend APIs, RDF operations, HTTP security, and multiple UI components.

**Primary recommendation:** Structure implementation in waves: (1) RDF Patch serialization + export API, (2) sync import + loop prevention, (3) LDN inbox + HTTP Signatures, (4) collaboration UI + shared graph management, (5) notification UI + send flow.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Shared named graphs** -- separate named graphs per shared space (`urn:sempkm:shared:{uuid}`). Private data stays in `urn:sempkm:current`. SPARQL queries use FROM clauses to union private + shared graphs.
- **Manual sync now, automatic polling later** -- ship "Sync Now" button. Data model supports polling but don't implement the scheduler.
- **Last-write-wins for conflicts** -- whichever change has the later timestamp overwrites. Overwritten edits preserved in event history.
- **Copy to shared graph** -- user shares an object by copying triples into a shared graph. Private original remains.
- **Both create-in and copy-to** -- users can create objects directly in a shared graph AND copy existing private objects into one.
- **Dangling references at boundaries** -- shared object references to private objects show as unresolved links.
- **Same Mental Model required** -- both instances must have the same model installed. Invitation flow checks compatibility.
- **Leave = read-only snapshot** -- when user leaves, sync stops but data remains frozen.
- **Derive patches from event operations** -- `materialize_inserts` become A lines, `materialize_deletes` become D lines.
- **Timestamp-based ordering with UUID tiebreaker** -- use existing `sempkm:timestamp`. No new sequence field.
- **SyncSource tagging** -- `EventStore.commit()` includes `sempkm:syncSource` predicate for remote-originated events. Events with syncSource never exported back to that source.
- **Both pull and push authenticated** via HTTP Signatures against WebID public keys.
- **Four notification types**: shared graph invitations, object recommendations, sync status alerts, free-form messages (markdown).
- **Sidebar "Inbox" panel** with badge count for unread. Sidebar "Collaboration" panel for shared graph management.
- **LDN notifications stored in RDF** as named graphs (`urn:sempkm:inbox:{uuid}`).
- **Notification states**: unread, read, acted, dismissed. Never deleted.
- **LDN inbox discoverable via Link header** on WebID profile response.
- **All incoming notifications authenticated** via HTTP Signature verification.
- **Invitation is introduction** -- no separate "register remote" step. WebID stored on accepting a shared graph invitation.
- **First contact via WebID URL or WebFinger handle** (`user@domain`).
- **Propose + accept for shared graphs** -- Alice sends LDN invitation, Bob accepts/declines.
- **RFC 9421 HTTP Message Signatures** with Ed25519. Python library: `http-message-signatures`.
- **WebID public key cache** -- TTL cache (1 hour, 64 entries). Force-refresh on verification failure.
- **Nav tree "SHARED" section** below existing type groups. Each shared graph is a collapsible group.
- **Minimal sync status** -- last sync timestamp + pending count. Green/yellow/gray dot.
- **Toast notifications for sync results** -- brief toast showing pulled/pushed counts.

### Claude's Discretion
- Exact RDF Patch serialization format (header, transaction markers)
- WebFinger JRD response structure
- HTTP Signature covered component selection
- Shared graph UUID generation and naming conventions
- Inbox notification RDF vocabulary (ActivityStreams types)
- Toast notification styling and duration
- Sync error handling and retry behavior
- Graph selector UI in object creation form

### Deferred Ideas (OUT OF SCOPE)
- CRDT-based real-time sync
- Automatic sync polling (background scheduler)
- Fediverse interop (legacy cavage HTTP Signatures + RSA)
- Detailed sync history/log
- Conflict review UI
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FED-01 | Events can be serialized as RDF Patch format (A/D operations) | RDF Patch spec defines A/D line format; derive from Operation.materialize_inserts/deletes |
| FED-02 | API endpoint exports event patches since a given sequence number | Extend EventQueryService with graph-scoped timestamp filtering |
| FED-03 | User can register a remote SemPKM instance for sync | Invitation-as-introduction pattern; WebFinger discovery; store WebID in RDF |
| FED-04 | Named graph sync pulls patches from remote instance and applies via EventStore | HTTP client with Signature auth fetches patches; apply via EventStore.commit() with graph targeting |
| FED-05 | Sync prevents infinite loops via syncSource tagging | Add sempkm:syncSource predicate in EventStore.commit(); filter on export |
| FED-06 | Server exposes LDN inbox endpoint discoverable via Link header | Add ldp:inbox Link header to WebID profile; implement POST /api/inbox receiver |
| FED-07 | User can send notification to remote instance's LDN inbox | HTTP POST with JSON-LD payload, signed with HTTP Signatures |
| FED-08 | User can view and act on received LDN notifications in workspace | Inbox sidebar panel with htmx; notification list with per-type actions |
| FED-09 | Incoming federation requests authenticated via HTTP Signatures | http-message-signatures library with Ed25519; FastAPI dependency for verification |
| FED-10 | Collaboration UI shows registered remotes, sync status, incoming changes | Collaboration sidebar panel; nav tree SHARED section; sync status indicators |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `http-message-signatures` | 2.0.1 | RFC 9421 HTTP Message Signatures (sign & verify) | Only maintained Python implementation of RFC 9421; supports Ed25519 |
| `httpx` | >=0.28 | HTTP client for federation requests (already in stack) | Already used by TriplestoreClient; supports async, custom auth |
| `rdflib` | >=7.5.0 | RDF serialization for patches & notifications (already in stack) | Already used throughout; handles N-Triples serialization |
| `cachetools` | >=7.0 | TTLCache for WebID public key caching (already in stack) | Already used by LabelService; proven TTL cache pattern |
| `cryptography` | >=43.0 | Ed25519 key operations (already in stack) | Already used by WebID service for key generation/encryption |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `http-sfv` | (dependency of http-message-signatures) | Structured Field Values parsing | Automatically used by http-message-signatures |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom RDF Patch serializer | Apache Jena's RDF Patch library | Jena is Java-only; Python has no RDF Patch library; protocol is simple enough to implement directly |
| Custom LDN receiver | pyldn | pyldn is unmaintained (last update 2020); LDN receiver is a simple POST endpoint |
| Custom WebFinger | python-webfinger (client) | python-webfinger is client-only; we need server endpoint; WebFinger server is trivial |

**Installation:**
```bash
pip install http-message-signatures
```

No other new dependencies needed -- everything else is already in the stack.

## Architecture Patterns

### New Module Structure
```
backend/app/
├── federation/              # New module
│   ├── __init__.py
│   ├── router.py            # API endpoints: /api/federation/*, /api/inbox
│   ├── service.py           # FederationService: sync orchestration
│   ├── patch.py             # RDF Patch serialization/deserialization
│   ├── signatures.py        # HTTP Signature sign/verify wrappers
│   ├── webfinger.py         # WebFinger endpoint + discovery client
│   ├── inbox.py             # LDN inbox receiver + notification storage
│   └── schemas.py           # Pydantic models for federation APIs
├── rdf/
│   └── namespaces.py        # Add LDP, AS namespaces (existing file)
├── events/
│   └── store.py             # Extend commit() for graph targeting + syncSource (existing file)
└── sparql/
    └── client.py            # Extend scope_to_current_graph() for shared graphs (existing file)
```

### Pattern 1: RDF Patch Serialization
**What:** Convert Operation materialize_inserts/deletes to RDF Patch A/D lines
**When to use:** Exporting events for federation sync

```python
# RDF Patch format: one line per operation
# H id <urn:uuid:...>           # Header: patch ID
# TX                            # Transaction start
# A <s> <p> <o> <g> .          # Add quad
# D <s> <p> <o> <g> .          # Delete quad
# TC .                          # Transaction commit

def serialize_patch(operations: list[Operation], graph_iri: str) -> str:
    """Serialize Operations to RDF Patch text format."""
    lines = []
    lines.append(f"H id <urn:uuid:{uuid4()}>")
    lines.append("TX .")
    for op in operations:
        for s, p, o in op.materialize_deletes:
            lines.append(f"D {_ntriples(s)} {_ntriples(p)} {_ntriples(o)} <{graph_iri}> .")
        for s, p, o in op.materialize_inserts:
            lines.append(f"A {_ntriples(s)} {_ntriples(p)} {_ntriples(o)} <{graph_iri}> .")
    lines.append("TC .")
    return "\n".join(lines)
```

### Pattern 2: HTTP Signature Authentication (Outbound)
**What:** Sign outgoing federation requests with the instance's Ed25519 private key
**When to use:** All server-to-server federation HTTP calls

```python
from http_message_signatures import HTTPMessageSigner, HTTPSignatureKeyResolver, algorithms

class SemPKMKeyResolver(HTTPSignatureKeyResolver):
    def __init__(self, private_key_pem: str, public_key_pem: str):
        self._private_key = load_pem_private_key(private_key_pem.encode(), password=None)
        self._public_key = load_pem_public_key(public_key_pem.encode())

    def resolve_private_key(self, key_id: str):
        return self._private_key

    def resolve_public_key(self, key_id: str):
        return self._public_key

signer = HTTPMessageSigner(
    signature_algorithm=algorithms.ED25519,
    key_resolver=resolver,
)
# Covered components per RFC 9421:
signer.sign(request, key_id=webid_uri,
    covered_component_ids=("@method", "@authority", "@target-uri", "content-type", "content-digest"))
```

### Pattern 3: HTTP Signature Verification (Inbound)
**What:** Verify incoming federation requests by fetching remote WebID public key
**When to use:** FastAPI dependency for federation endpoints

```python
from http_message_signatures import HTTPMessageVerifier, algorithms

class RemoteKeyResolver(HTTPSignatureKeyResolver):
    def __init__(self, key_cache: TTLCache):
        self._cache = key_cache

    def resolve_public_key(self, key_id: str) -> Ed25519PublicKey:
        # key_id is the remote WebID URI
        # Fetch WebID profile, extract sec:publicKeyPem
        # Cache with TTL; force-refresh on VerifyError
        ...

verifier = HTTPMessageVerifier(
    signature_algorithm=algorithms.ED25519,
    key_resolver=RemoteKeyResolver(cache),
)
verify_results = verifier.verify(request)
```

### Pattern 4: SyncSource Loop Prevention
**What:** Tag events from federation with source identity; exclude from re-export
**When to use:** When applying remote patches and when exporting patches

```python
# In EventStore.commit() -- add optional sync_source parameter:
async def commit(self, operations, performed_by=None, performed_by_role=None,
                 target_graph=None, sync_source=None):
    # ...
    if sync_source:
        event_triples.append(
            (event_iri, SEMPKM.syncSource, URIRef(sync_source))
        )
    # target_graph overrides CURRENT_GRAPH_IRI for materialization
    graph = URIRef(target_graph) if target_graph else CURRENT_GRAPH_IRI
    # ...

# In export query -- filter out events with matching syncSource:
FILTER NOT EXISTS { ?event sempkm:syncSource <{remote_instance_url}> }
```

### Pattern 5: LDN Inbox Receiver
**What:** POST endpoint accepting JSON-LD notifications per W3C LDN spec
**When to use:** Receiving notifications from remote instances

```python
@router.post("/api/inbox", status_code=202)
async def receive_notification(request: Request, ...):
    # 1. Verify HTTP Signature (dependency)
    # 2. Parse JSON-LD body
    # 3. Store as named graph urn:sempkm:inbox:{uuid}
    # 4. Return 202 Accepted with Location header
    body = await request.json()
    notification_graph = URIRef(f"urn:sempkm:inbox:{uuid4()}")
    # Parse JSON-LD and store triples in notification_graph
    ...
    return Response(status_code=202, headers={"Location": str(notification_graph)})
```

### Pattern 6: Shared Graph SPARQL Scoping
**What:** Extend `scope_to_current_graph()` to union shared graphs
**When to use:** All read queries in the browser/workspace

```python
def scope_to_current_graph(query, all_graphs=False, include_inferred=True,
                           shared_graphs=None):
    # ... existing logic ...
    from_clause = f"FROM <{CURRENT_GRAPH}>\n"
    if include_inferred:
        from_clause += f"FROM <{INFERRED_GRAPH}>\n"
    if shared_graphs:
        for sg in shared_graphs:
            from_clause += f"FROM <{sg}>\n"
    # ...
```

### Anti-Patterns to Avoid
- **Direct SPARQL UPDATE for sync** -- ALL writes must go through EventStore.commit() even for federation patches, to preserve event sourcing invariant
- **Storing federation state in SQL** -- keep sync metadata (shared graphs, remote contacts, notification state) in RDF for consistency with project convention
- **Polling in the main thread** -- even though automatic polling is deferred, design the sync service as async-compatible from the start
- **Trusting unsigned requests** -- every federation endpoint must verify HTTP Signatures; reject 401 on failure

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP Message Signatures | Custom signing/verification | `http-message-signatures` 2.0.1 | RFC 9421 is complex (covered components, structured headers, canonicalization); library handles edge cases |
| Ed25519 key operations | Custom key management | `cryptography` library (already in stack) | Already used by WebID service; proven key generation/serialization |
| TTL caching | Custom expiry logic | `cachetools.TTLCache` (already in stack) | Already used by LabelService; battle-tested TTL semantics |
| JSON-LD parsing | Custom RDF deserialization | `rdflib` with JSON-LD plugin (already in stack) | Already used throughout; handles @context expansion |

**Key insight:** RDF Patch, LDN, and WebFinger are simple protocols that SHOULD be hand-implemented (they're just HTTP + simple formats). HTTP Message Signatures is the only complex enough protocol to warrant a library.

## Common Pitfalls

### Pitfall 1: Infinite Sync Loops
**What goes wrong:** Instance A pushes patch to B, B stores it as an event, B pushes it back to A, infinite loop
**Why it happens:** Without sync source tagging, there's no way to distinguish local events from remote-originated events
**How to avoid:** Add `sempkm:syncSource` predicate to events created from federation patches. Filter these events out when exporting patches to the same source.
**Warning signs:** Event count growing rapidly after sync; same triples appearing in multiple events

### Pitfall 2: SPARQL Graph Scoping Regression
**What goes wrong:** Adding shared graph FROM clauses breaks existing queries or leaks data between users
**Why it happens:** `scope_to_current_graph()` is called in many places; adding shared graph awareness changes query behavior globally
**How to avoid:** Pass shared graph list as a parameter, not a global setting. Each user request must determine which shared graphs the user has access to. Default to no shared graphs when the parameter is absent (backward compatible).
**Warning signs:** Queries returning unexpected results; objects appearing that shouldn't be visible

### Pitfall 3: EventStore Graph Targeting
**What goes wrong:** Shared graph operations materialize into `urn:sempkm:current` instead of the shared graph
**Why it happens:** EventStore.commit() is hardcoded to CURRENT_GRAPH_IRI for materialization
**How to avoid:** Add optional `target_graph` parameter to `commit()` that overrides the materialization target. Default to CURRENT_GRAPH_IRI for backward compatibility.
**Warning signs:** Shared objects not appearing in shared graph queries; private graph growing with shared data

### Pitfall 4: HTTP Signature Request Body Handling
**What goes wrong:** Signature verification fails because the request body was consumed before signature check
**Why it happens:** FastAPI reads the request body stream only once; verification needs the body for content-digest
**How to avoid:** Read the body early, store it, and pass it to both the signature verifier and the JSON parser. Use `await request.body()` which caches the result.
**Warning signs:** 401 errors on valid signed requests; intermittent verification failures

### Pitfall 5: Content Negotiation on WebID Profile
**What goes wrong:** Federation requests fail because WebID profile returns HTML instead of RDF
**Why it happens:** The existing public_profile endpoint returns HTML by default; federation clients need Turtle or JSON-LD
**How to avoid:** Federation client must send `Accept: text/turtle` or `Accept: application/ld+json` headers when fetching WebID profiles. The existing content negotiation already handles this correctly.
**Warning signs:** Key resolution failures; "Profile not found" errors

### Pitfall 6: Notification State Never Deleted
**What goes wrong:** Inbox named graphs accumulate forever, triplestore grows unboundedly
**Why it happens:** Decision says "never deleted" for notification states
**How to avoid:** Design with eventual archival in mind. State transitions (unread -> read -> acted/dismissed) should be efficient SPARQL updates. Consider a future "purge dismissed after N days" option but don't implement now.
**Warning signs:** Triplestore query performance degrading over months

### Pitfall 7: Cross-Instance Blank Node Identity
**What goes wrong:** Blank nodes from one instance don't match blank nodes on another; patches fail or create duplicates
**Why it happens:** Blank node identifiers are instance-local by RDF semantics; RDF Patch requires "system identifiers"
**How to avoid:** SemPKM uses URIRef for all resources (IRI minting via `mint_object_iri`). Blank nodes should not appear in shared graph data. If they do appear (edge annotations use BNodes), skolemize them before export.
**Warning signs:** Duplicate edge annotations after sync; "dangling blank node" errors

## Code Examples

### RDF Patch Export from Events
```python
# Derive from existing EventStore patterns
# Source: events/store.py Operation dataclass

from app.events.store import _serialize_rdf_term

def events_to_patch(events: list[dict], graph_iri: str) -> str:
    """Convert event data to RDF Patch format.

    Each event's materialize_inserts become A lines,
    materialize_deletes become D lines.
    """
    lines = [f"H id <urn:uuid:{uuid4()}>", "TX ."]
    for event in events:
        for triple in event.get("deletes", []):
            s, p, o = triple
            lines.append(f"D {_nt(s)} {_nt(p)} {_nt(o)} <{graph_iri}> .")
        for triple in event.get("inserts", []):
            s, p, o = triple
            lines.append(f"A {_nt(s)} {_nt(p)} {_nt(o)} <{graph_iri}> .")
    lines.append("TC .")
    return "\n".join(lines) + "\n"
```

### WebFinger Endpoint
```python
# Source: RFC 7033 specification

@router.get("/.well-known/webfinger")
async def webfinger(
    resource: str = Query(...),
    rel: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db_session),
    request: Request = ...,
):
    """WebFinger discovery endpoint per RFC 7033."""
    # Parse acct: URI -> username@domain
    if resource.startswith("acct:"):
        user_host = resource[5:]
        username = user_host.split("@")[0]
    elif resource.startswith("http"):
        # Extract username from WebID URL
        username = resource.rsplit("/", 1)[-1].split("#")[0]
    else:
        raise HTTPException(400, "Unsupported resource URI scheme")

    user = await db.execute(select(User).where(User.username == username))
    user = user.scalar_one_or_none()
    if not user or not user.webid_published:
        raise HTTPException(404, "Resource not found")

    base_url = get_base_url(request)
    webid_uri = build_webid_uri(username, base_url)
    profile_url = build_profile_url(username, base_url)

    jrd = {
        "subject": resource,
        "aliases": [webid_uri, profile_url],
        "links": [
            {
                "rel": "self",
                "type": "text/turtle",
                "href": profile_url,
            },
            {
                "rel": "http://www.w3.org/ns/ldp#inbox",
                "href": f"{base_url}/api/inbox",
            },
        ],
    }

    # Filter by rel if specified
    if rel:
        jrd["links"] = [l for l in jrd["links"] if l["rel"] in rel]

    return JSONResponse(content=jrd, media_type="application/jrd+json")
```

### LDN Notification JSON-LD (ActivityStreams 2.0)
```python
# Source: W3C Activity Vocabulary

# Shared graph invitation
invitation = {
    "@context": "https://www.w3.org/ns/activitystreams",
    "type": "Offer",
    "actor": sender_webid,
    "object": {
        "type": "Collection",
        "id": shared_graph_iri,
        "name": shared_graph_name,
        "sempkm:requiredModel": model_id,
    },
    "target": recipient_webid,
    "summary": f"{sender_name} invites you to join shared graph '{shared_graph_name}'",
}

# Object recommendation
recommendation = {
    "@context": "https://www.w3.org/ns/activitystreams",
    "type": "Announce",
    "actor": sender_webid,
    "object": {
        "type": "Object",
        "id": object_iri,
        "name": object_label,
        "sempkm:objectType": type_iri,
    },
    "target": recipient_webid,
    "summary": f"{sender_name} recommends: {object_label}",
}

# Sync status alert
sync_alert = {
    "@context": "https://www.w3.org/ns/activitystreams",
    "type": "Update",
    "actor": sender_webid,
    "object": {
        "type": "Collection",
        "id": shared_graph_iri,
        "name": shared_graph_name,
    },
    "summary": f"{patch_count} new changes in '{shared_graph_name}'",
    "sempkm:patchCount": patch_count,
}

# Free-form message
message = {
    "@context": "https://www.w3.org/ns/activitystreams",
    "type": "Note",
    "actor": sender_webid,
    "content": markdown_content,
    "mediaType": "text/markdown",
    "target": recipient_webid,
}
```

### Named Graph Conventions
```python
# Shared graph: urn:sempkm:shared:{uuid}
# Inbox notification: urn:sempkm:inbox:{uuid}
# Private state: urn:sempkm:current (existing)
# Events: urn:sempkm:event:{uuid} (existing)

import uuid

def mint_shared_graph_iri() -> str:
    return f"urn:sempkm:shared:{uuid.uuid4()}"

def mint_inbox_graph_iri() -> str:
    return f"urn:sempkm:inbox:{uuid.uuid4()}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTTP Signatures (cavage draft) | RFC 9421 HTTP Message Signatures | Feb 2024 (RFC published) | Use `http-message-signatures` 2.0.x, not older cavage-based libs |
| W3C Linked Data Patch Format | RDF Patch (Apache Jena ecosystem) | 2023+ | LD Patch is for SPARQL-like operations; RDF Patch is simpler A/D for replication |
| RSA keys for signing | Ed25519 keys | Ongoing migration | Project already uses Ed25519; aligns with modern practice |
| ActivityPub for federation | LDN for notifications | N/A (design choice) | LDN is simpler, sufficient for PKM-to-PKM; AP is for social media |

**Deprecated/outdated:**
- **cavage HTTP Signatures draft**: Superseded by RFC 9421. The `http-message-signatures` library implements the current standard.
- **LD Patch (W3C)**: Different specification from RDF Patch. LD Patch uses SPARQL-like syntax; RDF Patch uses simple A/D lines. SemPKM uses RDF Patch.

## Open Questions

1. **http-message-signatures with httpx**
   - What we know: The library works with `requests.Request` objects
   - What's unclear: Whether it works natively with httpx requests or needs an adapter
   - Recommendation: Build a thin adapter that converts httpx Request to the format expected by the library, or sign headers manually and set them on the httpx request

2. **Shared graph access control per user**
   - What we know: Each shared graph is a named graph; users accept invitations
   - What's unclear: How to determine which shared graphs a user can access for SPARQL scoping (stored in RDF vs SQL)
   - Recommendation: Store shared graph membership as RDF triples in a metadata graph (`urn:sempkm:federation`). Query at request time and pass to `scope_to_current_graph()`.

3. **Event re-derivation for patch export**
   - What we know: Events store data_triples in named graphs. materialize_inserts/deletes are not stored separately -- they are used at commit time and discarded.
   - What's unclear: How to reconstruct A/D lines from stored event data for export
   - Recommendation: Add `sempkm:graphTarget` predicate to event metadata when the event targets a shared graph. For export, query data triples from the event graph and treat them all as inserts (the event graph contains the "new state" triples). For deletes, compare with previous event state or store delete triples explicitly in event metadata.

4. **Multi-user shared graph permissions**
   - What we know: SemPKM has owner/member roles
   - What's unclear: Whether both owner and member can participate in shared graphs
   - Recommendation: Allow both roles to participate. The invitation acceptance stores the user's WebID. Scope shared graph visibility per user.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright ^1.50.0 (E2E) + pytest (backend, declared but unused) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd e2e && npx playwright test --project=chromium --grep "federation"` |
| Full suite command | `cd e2e && npx playwright test --project=chromium` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FED-01 | Events serialize as RDF Patch | unit | `cd backend && python -m pytest tests/test_patch.py -x` | No -- Wave 0 |
| FED-02 | Export patches since timestamp | integration | `cd e2e && npx playwright test tests/18-federation/export-patches.spec.ts` | No -- Wave 0 |
| FED-03 | Register remote instance | E2E | `cd e2e && npx playwright test tests/18-federation/register-remote.spec.ts` | No -- Wave 0 |
| FED-04 | Pull + apply sync patches | integration | `cd backend && python -m pytest tests/test_sync.py -x` | No -- Wave 0 |
| FED-05 | Sync loop prevention | unit | `cd backend && python -m pytest tests/test_sync_source.py -x` | No -- Wave 0 |
| FED-06 | LDN inbox endpoint | integration | `cd e2e && npx playwright test tests/18-federation/ldn-inbox.spec.ts` | No -- Wave 0 |
| FED-07 | Send notification to remote | E2E | `cd e2e && npx playwright test tests/18-federation/send-notification.spec.ts` | No -- Wave 0 |
| FED-08 | View/act on notifications | E2E | `cd e2e && npx playwright test tests/18-federation/inbox-ui.spec.ts` | No -- Wave 0 |
| FED-09 | HTTP Signature authentication | unit | `cd backend && python -m pytest tests/test_signatures.py -x` | No -- Wave 0 |
| FED-10 | Collaboration UI | E2E | `cd e2e && npx playwright test tests/18-federation/collaboration-ui.spec.ts` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Run relevant unit tests for changed module
- **Per wave merge:** Full E2E suite
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_patch.py` -- covers FED-01 (RDF Patch serialization/deserialization)
- [ ] `backend/tests/test_signatures.py` -- covers FED-09 (HTTP Signature sign/verify)
- [ ] `backend/tests/test_sync_source.py` -- covers FED-05 (loop prevention)
- [ ] `backend/tests/conftest.py` -- shared test fixtures (mock triplestore, test keys)
- [ ] `e2e/tests/18-federation/` -- directory for federation E2E tests
- [ ] Framework install: `pip install pytest pytest-asyncio` (already declared as dev deps)

**Note:** Federation testing is inherently hard to E2E test with a single Docker stack. Most tests will need either (a) a second Docker stack instance, or (b) mock federation endpoints within the test. Backend unit/integration tests are critical for FED-01, FED-05, FED-09 where behavior can be tested without a real remote.

## Sources

### Primary (HIGH confidence)
- [RDF Patch specification](https://afs.github.io/rdf-patch/) -- A/D line format, header conventions, MIME type
- [RFC 9421 HTTP Message Signatures](https://www.rfc-editor.org/rfc/rfc9421) -- Current IETF standard for HTTP signing
- [W3C Linked Data Notifications](https://www.w3.org/TR/ldn/) -- Inbox discovery, sender/receiver protocol, JSON-LD payloads
- [RFC 7033 WebFinger](https://www.rfc-editor.org/rfc/rfc7033.html) -- .well-known/webfinger endpoint, JRD response format
- [W3C Activity Vocabulary](https://www.w3.org/TR/activitystreams-vocabulary/) -- Activity types (Offer, Accept, Announce, etc.)
- [http-message-signatures PyPI](https://pypi.org/project/http-message-signatures/) -- v2.0.1, Python >=3.10, RFC 9421 implementation with Ed25519

### Secondary (MEDIUM confidence)
- [pyauth/http-message-signatures GitHub](https://github.com/pyauth/http-message-signatures) -- API usage patterns, key resolver pattern
- [Mastodon RFC 9421 adoption PR](https://github.com/mastodon/mastodon/pull/34814) -- Confirms RFC 9421 is production-ready
- Existing SemPKM codebase (events/store.py, webid/service.py, sparql/client.py) -- Integration points verified by code reading

### Tertiary (LOW confidence)
- http-message-signatures httpx compatibility -- not verified; may need adapter (flagged in Open Questions)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- single new dependency (http-message-signatures) is well-maintained and RFC-aligned
- Architecture: MEDIUM -- patterns follow existing codebase conventions but federation is inherently complex; integration points need careful implementation
- Pitfalls: MEDIUM -- based on RDF federation experience and codebase analysis; some edge cases may surface during implementation

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (30 days -- http-message-signatures API stable post-2.0)
