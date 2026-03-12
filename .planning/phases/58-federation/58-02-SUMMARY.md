---
phase: 58-federation
plan: 02
subsystem: api
tags: [http-signatures, rfc-9421, webfinger, ldn, inbox, federation, ed25519]

# Dependency graph
requires:
  - phase: 58-federation
    provides: Federation module structure, LDP and AS namespaces, EventStore sync extensions
provides:
  - HTTP Signature signing and verification (RFC 9421 with Ed25519)
  - WebFinger server endpoint and client discovery
  - LDN inbox receiver storing notifications as RDF named graphs
  - VerifyHTTPSignature FastAPI dependency for federation auth
  - WebID profile ldp:inbox discovery (Link header + RDF triple)
affects: [58-03, 58-04]

# Tech tracking
tech-stack:
  added: [http-message-signatures]
  patterns: [RFC 9421 HTTP Message Signatures, WebID public key caching with force-refresh, LDN inbox as RDF named graphs]

key-files:
  created:
    - backend/app/federation/signatures.py
    - backend/app/federation/webfinger.py
    - backend/app/federation/inbox.py
  modified:
    - backend/pyproject.toml
    - backend/app/webid/router.py
    - backend/app/main.py

key-decisions:
  - "Used requests.PreparedRequest as adapter for http-message-signatures library (expects requests objects, not httpx)"
  - "Key ID in HTTP Signatures is the sender's WebID URI, enabling direct key lookup"
  - "Notification JSON-LD stored as SPARQL INSERT DATA triples rather than rdflib JSON-LD parsing for reliability"

patterns-established:
  - "HTTP Signature auth: VerifyHTTPSignature() dependency on federation endpoints"
  - "WebID key cache: TTLCache(64, 3600) with force-refresh retry on verification failure"
  - "LDN inbox: notifications stored as urn:sempkm:inbox:{uuid} named graphs with state management"

requirements-completed: [FED-09, FED-06]

# Metrics
duration: 7min
completed: 2026-03-11
---

# Phase 58 Plan 02: HTTP Signatures, WebFinger, and LDN Inbox Summary

**RFC 9421 HTTP Signature auth with Ed25519, WebFinger handle discovery, and LDN inbox receiver storing notifications as RDF named graphs**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-11T01:25:44Z
- **Completed:** 2026-03-11T01:32:51Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- HTTP Signature signing/verification with Ed25519 keys via http-message-signatures library
- WebFinger endpoint at /.well-known/webfinger resolves published WebID profiles with JRD responses
- LDN inbox at POST /api/inbox receives signed JSON-LD notifications, stores as RDF named graphs
- Notification state management (unread/read/acted/dismissed) via GET and PATCH endpoints
- WebID profile responses include ldp:inbox Link header and RDF triple for inbox discovery

## Task Commits

Each task was committed atomically:

1. **Task 1: HTTP Signatures (sign/verify) and dependency installation** - `0f891ad` (feat)
2. **Task 2: WebFinger endpoint, LDN inbox receiver, WebID Link header, and router registration** - `ce91b81` (feat)

## Files Created/Modified
- `backend/app/federation/signatures.py` - HTTP Signature sign/verify wrappers, VerifyHTTPSignature dependency, WebID key cache
- `backend/app/federation/webfinger.py` - WebFinger server endpoint (/.well-known/webfinger) and discover_webid() client
- `backend/app/federation/inbox.py` - LDN inbox POST receiver, GET listing, PATCH state update
- `backend/pyproject.toml` - Added http-message-signatures>=2.0.1 dependency
- `backend/app/webid/router.py` - Added ldp:inbox Link header and RDF triple to public profile
- `backend/app/main.py` - Registered webfinger_router and inbox_router

## Decisions Made
- Used requests.PreparedRequest as adapter for http-message-signatures library since it expects requests objects, not httpx. sign_request() builds a requests.Request internally.
- Key ID in HTTP Signatures is the sender's WebID URI, enabling direct key lookup from the WebID profile's sec:publicKeyPem.
- Notification JSON-LD fields stored as SPARQL INSERT DATA triples rather than using rdflib JSON-LD parsing, for simplicity and reliability (no JSON-LD plugin dependency).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HTTP Signature auth ready for protecting all federation endpoints (Plans 03-04)
- WebFinger discovery enables remote instance lookup for shared graph invitations
- LDN inbox ready to receive shared graph invitations, recommendations, sync alerts
- VerifyHTTPSignature dependency available for any federation endpoint requiring auth

## Self-Check: PASSED

- All 6 files verified present on disk
- Both task commits (0f891ad, ce91b81) verified in git log

---
*Phase: 58-federation*
*Completed: 2026-03-11*
