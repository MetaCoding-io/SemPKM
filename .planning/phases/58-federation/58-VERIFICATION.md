---
phase: 58-federation
verified: 2026-03-12T04:30:00Z
status: gaps_found
score: 9/10 must-haves verified
re_verification: false
gaps:
  - truth: "Sync Now button triggers sync and shows toast with pulled/pushed counts"
    status: failed
    reason: "federation.js sends remote_instance_url as empty string ('') but the sync endpoint raises HTTP 400 when remote_instance_url is empty or missing. The UI button will always fail with a 400 error when clicked."
    artifacts:
      - path: "frontend/static/js/federation.js"
        issue: "Line 85: body: JSON.stringify({ remote_instance_url: '' }) — empty string guaranteed to 400"
      - path: "backend/app/federation/router.py"
        issue: "Lines 231-234: raises HTTPException(400) when remote_url is falsy (empty string is falsy)"
    missing:
      - "Either the sync endpoint must discover remote_instance_url from shared graph member metadata when not supplied, OR the UI must prompt for or retrieve the remote URL before calling sync. Per CONTEXT.md decision: 'no separate register remote step — remotes derived from shared graphs.' So the endpoint should auto-discover from FEDERATION_GRAPH members."
human_verification:
  - test: "Sync status dot colors in Collaboration panel"
    expected: "Green dot (<24h since sync), yellow dot (>24h), gray dot (never synced)"
    why_human: "Cannot verify CSS color rendering or correct date arithmetic at runtime without live data"
  - test: "Inbox badge count updates on notification receipt"
    expected: "Badge number increments and becomes visible when unread notifications exist"
    why_human: "Requires sending an actual LDN notification to verify badge polling triggers correctly"
  - test: "Shared object click opens workspace tab"
    expected: "Clicking a shared object in the SHARED nav section calls openTab(iri, label)"
    why_human: "openTab() wiring relies on workspace.js being loaded; needs browser verification"
  - test: "HTTP Signature verification rejects unsigned requests to /api/inbox POST"
    expected: "Returns 401 for unsigned POST requests to the inbox"
    why_human: "Requires actual HTTP request testing against the running server"
---

# Phase 58: Federation Verification Report

**Phase Goal:** SemPKM instances can sync knowledge and exchange notifications with other instances using standard protocols
**Verified:** 2026-03-12T04:30:00Z
**Status:** gaps_found — 1 gap blocking Sync Now UI flow
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Event operations can be serialized as RDF Patch text with A (Add) and D (Delete) lines | VERIFIED | `backend/app/federation/patch.py` — `serialize_patch()` and `deserialize_patch()` fully implemented with H/TX/A/D/TC format, quad graph component, BNode skolemization |
| 2 | API endpoint returns patches for a shared graph since a given timestamp | VERIFIED | `GET /api/federation/patches/{graph_id}?since=` in router.py — SPARQL queries event graphs by `sempkm:graphTarget` and timestamp filter, returns `PatchExportResponse` |
| 3 | Events created with a syncSource are excluded from patch export to that same source | VERIFIED | router.py line 403: `FILTER NOT EXISTS {{ ?event <{SEMPKM.syncSource}> <{requester}> }}` wired to `requester` query param |
| 4 | Sync pulls patches from remote instance and applies via EventStore with syncSource tagging | VERIFIED | `service.py` `sync_shared_graph()` calls `deserialize_patch()` then `EventStore.commit([op], target_graph=graph_iri, sync_source=remote_instance_url)` |
| 5 | Incoming federation requests are authenticated by verifying HTTP Signatures against the sender's WebID public key | VERIFIED | `signatures.py` — `VerifyHTTPSignature` dependency on POST /api/inbox; `RemoteKeyResolver` fetches WebID Turtle profile, extracts `sec:publicKeyPem`, TTLCache(64, 3600) with force-refresh |
| 6 | Server exposes an LDN inbox endpoint at /api/inbox that accepts JSON-LD notifications | VERIFIED | `inbox.py` — POST /api/inbox validates type (Offer/Announce/Update/Note), actor matches sender WebID, stores as `urn:sempkm:inbox:{uuid}` named graph |
| 7 | LDN inbox is discoverable via Link header on WebID profile responses | VERIFIED | `webid/router.py` line 227: `Link: </api/inbox>; rel="http://www.w3.org/ns/ldp#inbox"` added to public profile; also as `ldp:inbox` RDF triple |
| 8 | WebFinger endpoint resolves user@domain handles to WebID URLs | VERIFIED | `webfinger.py` — GET `/.well-known/webfinger` parses `acct:` and `http(s):` URIs, returns JRD with self/inbox links; `discover_webid()` client function implemented |
| 9 | User can see inbox notifications in sidebar panel, collaboration panel shows shared graphs with sync status | VERIFIED | All templates exist and are wired in workspace.html; htmx loads from `/api/federation/inbox-partial` and `/api/federation/collab-partial` with per-type action buttons and sync-dot CSS |
| 10 | Sync Now button triggers sync and shows toast with pulled/pushed counts | FAILED | `federation.js` line 85 sends `remote_instance_url: ''`; endpoint raises HTTP 400 for empty/missing `remote_instance_url` — Sync Now always fails in UI |

**Score:** 9/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/federation/__init__.py` | Federation module init | VERIFIED | Exists |
| `backend/app/federation/patch.py` | RDF Patch serialization/deserialization | VERIFIED | 184 lines; `serialize_patch`, `deserialize_patch`, `_nt` all implemented substantively |
| `backend/app/federation/schemas.py` | Pydantic models for federation API | VERIFIED | All 8 models: `PatchExportResponse`, `SharedGraphInfo`, `SharedGraphCreate`, `SharedGraphResponse`, `InvitationSend`, `SyncResult`, `NotificationSend`, `ContactInfo` |
| `backend/app/federation/router.py` | Federation API endpoints (13 endpoints) | VERIFIED | 732 lines; all CRUD, sync, invite, notify, contacts, patch-export, and 3 htmx partial endpoints present |
| `backend/app/federation/service.py` | FederationService orchestration | VERIFIED | 840+ lines; `create_shared_graph`, `sync_shared_graph`, `copy_to_shared_graph`, `send_invitation`, `accept_invitation`, `notify_remote_members_of_change`, `get_user_shared_graphs` |
| `backend/app/federation/signatures.py` | HTTP Signature sign/verify | VERIFIED | `sign_request`, `verify_request`, `fetch_webid_public_key`, `VerifyHTTPSignature` all implemented with TTLCache(64, 3600) |
| `backend/app/federation/webfinger.py` | WebFinger server + client | VERIFIED | `webfinger_router` with `/.well-known/webfinger`, `discover_webid()` client |
| `backend/app/federation/inbox.py` | LDN inbox receiver | VERIFIED | POST/GET/PATCH endpoints with signature verification, RDF storage, state management |
| `backend/app/events/store.py` | Extended with `target_graph` and `sync_source` | VERIFIED | Lines 79-80: params present; lines 165-174: syncSource and graphTarget triples added |
| `backend/app/rdf/namespaces.py` | LDP and AS namespace definitions | VERIFIED | LDP, AS defined; "ldp" and "as" in COMMON_PREFIXES; in `__all__` |
| `backend/app/sparql/client.py` | `scope_to_current_graph` with `shared_graphs` | VERIFIED | Line 51: `shared_graphs: list[str] | None = None` parameter; lines 96-97: FROM clauses added |
| `backend/app/sparql/router.py` | SPARQL wired to pass shared graphs | VERIFIED | `_resolve_user_shared_graphs` helper; wired in `sparql_get` and `sparql_post` |
| `backend/app/commands/router.py` | `target_graph` parameter for object creation | VERIFIED | Lines 114-173: target_graph extracted, passed to EventStore, outbound alerts fired |
| `backend/app/templates/browser/partials/inbox_panel.html` | Inbox panel wrapper | VERIFIED | 18 lines; htmx hx-get/hx-trigger/hx-swap wired to `/api/federation/inbox-partial` |
| `backend/app/templates/browser/partials/inbox_list.html` | Notification list with actions | VERIFIED | 65 lines; per-type icons and action buttons (Accept/Decline, Sync Now, Mark Read, Dismiss) |
| `backend/app/templates/browser/partials/collaboration_panel.html` | Collaboration panel wrapper | VERIFIED | 17 lines; htmx loaded |
| `backend/app/templates/browser/partials/collab_content.html` | Shared graphs + contacts | VERIFIED | 94 lines; sync-dot, Sync Now button, Invite button, inline forms, contacts section |
| `backend/app/templates/browser/partials/shared_nav_section.html` | SHARED nav section wrapper | VERIFIED | 18 lines; htmx outerHTML swap from `/api/federation/shared-nav` |
| `backend/app/templates/browser/partials/shared_nav_content.html` | Shared graph objects by type | VERIFIED | 41 lines; `onclick="openTab()"` on shared objects |
| `frontend/static/js/federation.js` | Federation UI JS | VERIFIED | 335 lines (min: 80); IIFE with sync, toast, badge polling, form handlers, notification actions |
| `frontend/static/css/federation.css` | Federation styles | VERIFIED | 503 lines (min: 50); inbox-badge, sync-dot variants, federation-toast with animation, notification-item, shared-graph-card |
| `backend/app/webid/router.py` | WebID profile with ldp:inbox Link header | VERIFIED | Line 227: Link header added; lines 240, 258: `ldp:inbox` RDF triple added |
| `backend/app/main.py` | All three routers registered | VERIFIED | Lines 61-63: imports; lines 454-456: `federation_router`, `webfinger_router`, `inbox_router` all mounted |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `federation/patch.py` | `events/store.py` | `_nt()` for N-Triples serialization | VERIFIED | `patch.py` imports `Operation` from `events.store`; `_nt()` is independent (by design — different format from `_serialize_rdf_term`) |
| `federation/router.py` | `federation/patch.py` | `serialize_patch` call in export endpoint | VERIFIED | Line 24: `from app.federation.patch import serialize_patch`; line 451: `patch_text = serialize_patch(operations, graph_iri)` |
| `federation/service.py` | `events/store.py` | `EventStore.commit(target_graph=, sync_source=)` | VERIFIED | Line 280: `await self._event_store.commit([op], ..., target_graph=shared_graph_iri)` and line 650: `sync_source=remote_instance_url` |
| `federation/service.py` | `federation/patch.py` | `deserialize_patch` for applying remote patches | VERIFIED | Line 21: import; line 625: `quads = deserialize_patch(patch_text)` |
| `federation/service.py` | `federation/signatures.py` | `sign_request` for outbound federation HTTP calls | VERIFIED | Line 27: `from app.federation.signatures import sign_request`; line 598: used in sync flow |
| `federation/inbox.py` | `federation/signatures.py` | `VerifyHTTPSignature` dependency on inbox endpoint | VERIFIED | Line 18 import; line 33: `sender_webid: str = Depends(VerifyHTTPSignature())` |
| `webid/router.py` | Link header | `ldp:inbox` discovery on public profile endpoint | VERIFIED | Line 227: `Link: </api/inbox>; rel="http://www.w3.org/ns/ldp#inbox"` |
| `main.py` | `federation/webfinger.py` | `webfinger_router` public router registration | VERIFIED | Line 62: `from app.federation.webfinger import webfinger_router`; line 455: `app.include_router(webfinger_router)` |
| `sparql/router.py` | `sparql/client.py` | `scope_to_current_graph(shared_graphs=)` in `_execute_sparql` | VERIFIED | Line 157: `processed, all_graphs=all_graphs, shared_graphs=shared_graphs` |
| `sparql/router.py` | `federation/service.py` | `FederationService.get_user_shared_graphs()` for SPARQL scoping | VERIFIED | Lines 125, 335, 408: `_resolve_user_shared_graphs()` calls `service.get_user_shared_graphs(webid_uri)` |
| `federation.js` | `/api/federation/shared-graphs/{id}/sync` | `fetch POST` for Sync Now button | PARTIAL | Line 82: fetch to correct URL; line 85: `remote_instance_url: ''` guaranteed 400 response |
| `federation.js` | `/api/inbox` | `fetch GET` for inbox badge count | VERIFIED | Line 42: `fetch('/api/inbox?state=unread')` with response handling |
| `inbox_panel.html` | `/api/federation/inbox-partial` | htmx hx-get for notification list | VERIFIED | Line 13: `hx-get="/api/federation/inbox-partial"` with `hx-trigger="load, every 60s"` |
| `workspace.html` | federation partials | include for sidebar panels | VERIFIED | Lines 74, 165, 166: all three partials included; CSS (line 11) and JS (line 13) loaded |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| FED-01 | 58-01 | Events can be serialized as RDF Patch format (A/D operations) | SATISFIED | `patch.py` `serialize_patch()` produces H/TX/A/D/TC format with quad graph component |
| FED-02 | 58-01 | API endpoint exports event patches since a given sequence number | SATISFIED | Implemented as timestamp-based (CONTEXT.md decision: "Timestamp-based ordering... No new sequence field needed"). GET `/api/federation/patches/{graph_id}?since={iso}` |
| FED-03 | 58-03 | User can register a remote SemPKM instance for sync | SATISFIED | Invitation-accept flow creates shared graph locally and stores sender as contact. "Invitation is introduction" per CONTEXT.md — no separate register step |
| FED-04 | 58-03 | Named graph sync pulls patches from remote instance and applies via EventStore | SATISFIED | `FederationService.sync_shared_graph()` fetches patches, deserializes, applies via `EventStore.commit(target_graph=, sync_source=)` |
| FED-05 | 58-01 | Sync prevents infinite loops via syncSource tagging | SATISFIED | `EventStore.commit(sync_source=)` adds `sempkm:syncSource` triple; export endpoint `FILTER NOT EXISTS { ?event sempkm:syncSource <requester> }` |
| FED-06 | 58-02 | Server exposes LDN inbox endpoint discoverable via Link header on WebID profiles | SATISFIED | POST/GET/PATCH `/api/inbox` in inbox.py; `ldp:inbox` Link header in webid/router.py |
| FED-07 | 58-03 | User can send a notification to a remote instance's LDN inbox | SATISFIED | POST `/api/federation/notifications/send` -> `FederationService.send_notification()` -> WebFinger discovery -> signed POST |
| FED-08 | 58-04 | User can view and act on received LDN notifications in the workspace | SATISFIED | `inbox_panel.html` + `inbox_list.html` with Accept/Decline/Sync/Dismiss actions; htmx-loaded in workspace |
| FED-09 | 58-02 | Incoming federation requests are authenticated via HTTP Signatures against WebID public keys | SATISFIED | `VerifyHTTPSignature` FastAPI dependency on POST /api/inbox; Ed25519 verification via `http-message-signatures` library; TTLCache(64, 3600) with force-refresh |
| FED-10 | 58-04 | Collaboration UI shows registered remote instances, sync status, and incoming changes | SATISFIED | Collaboration panel shows shared graphs with sync-dot color coding (green/yellow/gray), contacts list, sync/invite actions; SHARED nav tree section |

**Note:** REQUIREMENTS.md still shows FED-01, FED-02, FED-05 as `[ ] Pending`. This is a stale checkbox state — the implementations were verified in the codebase above. The summaries for 58-01 document `requirements-completed: [FED-01, FED-02, FED-05]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/static/js/federation.js` | 85 | `remote_instance_url: ''` hard-coded empty string | Blocker | Sync Now UI button always fails with HTTP 400; the sync endpoint requires a non-empty remote URL |

No placeholder comments, stub implementations, or empty return values found in any federation files.

### Human Verification Required

#### 1. Sync Status Dot Colors

**Test:** Open the workspace, create a shared graph, observe the sync dot color
**Expected:** Gray dot for a freshly created graph (never synced); green after a successful sync completed within 24h; yellow if sync is stale
**Why human:** Color rendering and CSS variable resolution need visual confirmation; runtime date arithmetic cannot be verified statically

#### 2. Inbox Badge Count Updates

**Test:** With the workspace open, have a second instance POST a signed notification to `/api/inbox`; observe the badge on the INBOX panel header
**Expected:** Badge appears with count 1, polling refreshes it every 60 seconds
**Why human:** Requires live notification delivery and UI interaction to verify badge polling cycle

#### 3. Shared Object Click Opens Workspace Tab

**Test:** Add an object to a shared graph, reload the workspace, click the object in the SHARED nav section
**Expected:** The object opens in a workspace editor tab (via `openTab(iri, label)`)
**Why human:** Depends on `openTab()` from `workspace.js` being present in the page; needs browser execution

#### 4. HTTP Signature Rejection of Unsigned Inbox Requests

**Test:** POST to `/api/inbox` without Signature/Signature-Input headers
**Expected:** Returns 401 Unauthorized with detail "Missing or invalid HTTP Signature"
**Why human:** Requires actual HTTP request to the running server to verify the VerifyHTTPSignature dependency rejects unsigned calls

### Gaps Summary

One gap blocks the phase's "Sync Now" user experience:

**Sync Now button always returns 400 error.** The `syncSharedGraph()` function in `federation.js` (line 85) hard-codes `remote_instance_url: ''`. The sync endpoint in `router.py` raises `HTTPException(400, "remote_instance_url required in request body")` when this field is empty (empty string is falsy in Python). The user will always see an error toast when clicking "Sync Now."

The CONTEXT.md design states "no separate register remote step — remotes derived from shared graphs." This implies the endpoint should auto-discover `remote_instance_url` from the shared graph's member WebIDs in the `urn:sempkm:federation` graph, rather than requiring it as a request body field. Either:
- The endpoint should look up remote member URLs from federation metadata when `remote_instance_url` is not supplied, OR
- The UI must provide a way for the user to enter the remote URL before syncing

The core federation infrastructure (RDF Patch, EventStore extensions, HTTP Signatures, WebFinger, LDN inbox, SPARQL scoping, invitation flow, all UI panels) is substantively implemented and correctly wired. This is the only functional gap.

---

_Verified: 2026-03-12T04:30:00Z_
_Verifier: Claude (gsd-verifier)_
