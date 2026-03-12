# T02: 58-federation 02

**Slice:** S58 — **Milestone:** M001

## Description

HTTP Signature authentication, WebFinger discovery, and LDN inbox receiver.

Purpose: Establish the security and notification foundations for federation. All server-to-server requests must be signed and verified using RFC 9421 HTTP Message Signatures with Ed25519 keys (already in WebID profiles). The LDN inbox endpoint receives notifications from remote instances. WebFinger enables email-like handle discovery (user@domain -> WebID URL).

Output: `signatures.py` (sign/verify wrappers using http-message-signatures library), `webfinger.py` (server + client), `inbox.py` (POST /api/inbox receiver storing in RDF), WebID profile Link header for inbox discovery, WebFinger router registered in main.py.

## Must-Haves

- [ ] "Incoming federation requests are authenticated by verifying HTTP Signatures against the sender's WebID public key"
- [ ] "Server exposes an LDN inbox endpoint at /api/inbox that accepts JSON-LD notifications"
- [ ] "LDN inbox is discoverable via Link header on WebID profile responses"
- [ ] "WebFinger endpoint resolves user@domain handles to WebID URLs"
- [ ] "WebID public keys are cached with 1-hour TTL and force-refreshed on verification failure"

## Files

- `backend/app/federation/signatures.py`
- `backend/app/federation/webfinger.py`
- `backend/app/federation/inbox.py`
- `backend/app/webid/router.py`
- `backend/app/main.py`
- `backend/pyproject.toml`
