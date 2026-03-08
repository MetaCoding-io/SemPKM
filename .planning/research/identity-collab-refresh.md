# Identity & Collaboration Refresh: Implementation-Ready Details

**Created:** 2026-03-07
**Context:** Targeted refresh of decentralized-identity.md and collaboration-architecture.md research for v2.5 implementation. Focuses on library verification, WebID+IndieAuth integration patterns, cross-instance authentication, and IndieAuth provider implementation.

---

## 1. Library Verification

### indieweb-utils (v0.10.0, September 2025) -- USABLE WITH CAVEATS

**Status:** Actively maintained (501 commits, 8 releases). Latest release September 11, 2025. MIT license.

**IndieAuth support:** The library provides **both server-side and client-side** helpers:

Server-side functions:
- `generate_auth_token()` -- creates JWT-encoded authorization codes
- `redeem_code()` -- exchanges authorization codes for access tokens
- `validate_access_token()` -- verifies token validity, returns user info
- `is_user_authenticated()` -- Flask helper (would need adaptation for FastAPI)

Client-side functions:
- `discover_indieauth_endpoints()` -- locates metadata endpoints
- `handle_indieauth_callback()` -- processes callback responses
- `get_valid_relmeauth_links()` -- validates bidirectional rel=me links
- `get_profile()` -- fetches user profile via h-card

**Assessment:** The server-side functions provide useful scaffolding but are Flask-oriented. For SemPKM's FastAPI backend, use as reference/utility rather than direct integration. The discovery and validation functions are framework-agnostic and directly usable.

**Confidence:** HIGH (verified via PyPI and GitHub)

### PyLD (v2.0.4, February 2024) -- STABLE, USABLE

**Status:** Maintained by Digital Bazaar. Requires Python >= 3.6. Implements JSON-LD API including URDNA2015 canonicalization.

**Key capability for SemPKM:** `jsonld.normalize()` with `algorithm: 'URDNA2015'` produces deterministic N-Quads output for graph signing. This is the critical function for RDF graph integrity proofs.

**Confidence:** HIGH (verified via PyPI, well-established library)

### python-cryptography -- CURRENT, Ed25519 SUPPORTED

**Status:** Actively maintained (currently at v44.x). Ed25519 support is stable and well-documented.

**Ed25519 usage pattern:**
```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Key generation
private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Signing (deterministic -- same key+data = same signature)
signature = private_key.sign(b"message")

# Verification (raises InvalidSignature on failure)
public_key.verify(signature, b"message")

# Serialization for storage/DID documents
from cryptography.hazmat.primitives import serialization
public_bytes = public_key.public_bytes(
    serialization.Encoding.Raw,
    serialization.PublicFormat.Raw
)
```

**Confidence:** HIGH (official docs verified)

### http-message-signatures (v2.0.1, January 2026) -- NEW RECOMMENDATION

**Not in original research.** This is a Python implementation of RFC 9421 (HTTP Message Signatures), the IETF standard that supersedes the old draft used by Mastodon/fediverse.

- `pip install http-message-signatures` -- core signing/verification
- `pip install requests-http-signature` -- requests integration with body digest

**Why this matters:** RFC 9421 is the standardized version of what the fediverse uses for server-to-server authentication. SemPKM should implement RFC 9421 from the start rather than the legacy cavage-12 draft.

**Confidence:** HIGH (verified via PyPI, January 2026 release)

### PunyAuth -- DEAD, DO NOT USE

**Status:** Repository archived March 5, 2026. Only 10 commits. Never completed. The original research listed this as an option -- it is no longer viable.

### Alto -- STALE, USE AS REFERENCE ONLY

**Status:** Last significant activity October 2021. Flask-based. Use as architectural reference for how IndieAuth endpoints are structured, but do not depend on it.

### datasette-indieauth (v1.2.2, November 2022) -- CLIENT ONLY

Simon Willison's implementation is an IndieAuth **client** (consumer), not a provider. Useful as reference for the client-side flow, not for building SemPKM's authorization server.

---

## 2. WebID + IndieAuth Integration Pattern

### How They Connect

WebID and IndieAuth are **complementary but independent** systems. They do NOT automatically discover each other -- SemPKM must bridge them.

**WebID** answers: "Who is this person?" (an RDF profile document at an HTTP URI)
**IndieAuth** answers: "Can this person prove they control that URL?" (OAuth2-based authentication)

### The Bridge: Same URL, Two Representations

The key insight is that the **user's profile URL serves both purposes**:

```
https://sempkm.example.com/users/alice
```

1. **As WebID:** When requested with `Accept: text/turtle`, returns RDF profile document (FOAF properties, public keys, linked identities)
2. **As IndieAuth identity:** When requested with `Accept: text/html`, returns HTML page with `<link rel="indieauth-metadata" href="...">` discovery

This is content negotiation -- the same URL, different representations based on what the client asks for.

### Minimal WebID Profile Document

```turtle
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix cert: <http://www.w3.org/ns/auth/cert#> .
@prefix solid: <http://www.w3.org/ns/solid/terms#> .
@prefix dcterms: <http://purl.org/dc/terms/> .

<https://sempkm.example.com/users/alice>
    a foaf:PersonalProfileDocument ;
    foaf:primaryTopic <https://sempkm.example.com/users/alice#me> .

<https://sempkm.example.com/users/alice#me>
    a foaf:Person ;
    foaf:name "Alice" ;
    cert:key [
        a cert:Ed25519PublicKey ;
        cert:publicKeyBase64 "..." ;
    ] ;
    solid:oidcIssuer <https://sempkm.example.com/> .
```

### HTML Representation (for IndieAuth discovery)

```html
<html>
<head>
    <link rel="indieauth-metadata" href="https://sempkm.example.com/.well-known/oauth-authorization-server">
    <link rel="me" href="https://mastodon.social/@alice">
</head>
<body>
    <div class="h-card">
        <a class="p-name u-url" href="https://sempkm.example.com/users/alice">Alice</a>
    </div>
</body>
</html>
```

### How Solid Servers Do It

Solid uses `solid:oidcIssuer` in the WebID profile to point to the OIDC provider. The verification flow:

1. Client obtains an ID Token from the issuer
2. Client extracts the WebID URI from the token
3. Resource server fetches the WebID profile
4. Resource server checks that the issuer in the ID Token matches `solid:oidcIssuer` in the profile
5. If they match, the request is authenticated as that WebID

SemPKM should adopt this same pattern but with IndieAuth instead of full OIDC. The `solid:oidcIssuer` triple (or an equivalent custom predicate) in the WebID profile points to the SemPKM instance's IndieAuth metadata endpoint.

### Recommended FastAPI Routes

```python
# WebID profile with content negotiation
@app.get("/users/{username}")
async def user_profile(username: str, request: Request):
    accept = request.headers.get("accept", "text/html")
    if "text/turtle" in accept or "application/ld+json" in accept:
        return turtle_profile(username)  # RDF WebID document
    return html_profile(username)  # HTML with IndieAuth discovery links

# IndieAuth metadata (RFC 8414 style)
@app.get("/.well-known/oauth-authorization-server")
async def indieauth_metadata():
    return {
        "issuer": "https://sempkm.example.com/",
        "authorization_endpoint": "https://sempkm.example.com/auth/authorize",
        "token_endpoint": "https://sempkm.example.com/auth/token",
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["profile", "read", "write"],
    }
```

**Confidence:** MEDIUM (synthesized from Solid-OIDC spec, IndieAuth spec, and WebID spec -- no single implementation demonstrates this exact pattern)

---

## 3. Cross-Instance Authentication for RDF Collaboration

### The Problem

Instance A wants to push/pull named graphs to/from Instance B. Instance B needs to verify that the request is from a specific WebID (e.g., `https://a.example.com/users/alice#me`).

### Recommended Pattern: HTTP Message Signatures (RFC 9421)

This is the same mechanism the fediverse uses for server-to-server ActivityPub, but SemPKM should use the standardized RFC 9421 rather than the legacy draft.

**Flow:**

1. **Instance A signs the request** using the Ed25519 private key associated with the actor's WebID
2. **Instance B receives the request** and extracts the `keyId` from the Signature-Input header
3. **Instance B fetches the WebID profile** at the keyId URL (with caching)
4. **Instance B extracts the public key** from the profile's `cert:key` property
5. **Instance B verifies the signature** against the public key
6. **Instance B checks authorization** -- does this WebID have permission on the requested resource?

**Implementation with http-message-signatures:**

```python
from http_message_signatures import HTTPMessageSigner, HTTPMessageVerifier

# Signing outbound requests (Instance A)
signer = HTTPMessageSigner(
    signature_algorithm=Ed25519,
    key_resolver=LocalKeyResolver(actor_private_key),
    covered_component_ids=["@method", "@target-uri", "content-type", "content-digest"],
)
signer.sign(request, key_id=f"https://a.example.com/users/alice#key")

# Verifying inbound requests (Instance B)
verifier = HTTPMessageVerifier(
    signature_algorithm=Ed25519,
    key_resolver=WebIDKeyResolver(),  # Fetches WebID, extracts public key
)
verify_result = verifier.verify(request)
webid = verify_result.parameters["keyId"]  # The authenticated identity
```

### Why NOT Solid-OIDC / WebID-OIDC

Solid-OIDC requires a full OpenID Connect provider with ID Tokens, DPoP (Demonstration of Proof of Possession), and token introspection. This is a heavy implementation for server-to-server communication. HTTP Signatures are simpler and more appropriate for machine-to-machine trust.

**Use IndieAuth for:** Human users authenticating via browser (OAuth2 flow)
**Use HTTP Signatures for:** Instance-to-instance API calls (server-to-server)

### Fediverse State of the Art (Context)

The fediverse (Mastodon et al.) currently uses the legacy cavage-12 HTTP Signatures draft with RSA-SHA256. Migration to RFC 9421 is underway but slow -- as of January 2026, only Mastodon and WordPress have partial RFC 9421 support, and neither supports Ed25519 yet.

**Implication for SemPKM:** Since we are building a new system (not interoperating with existing fediverse), we should implement RFC 9421 with Ed25519 from the start. If fediverse interop becomes important later, adding RSA-SHA256 as a fallback is straightforward.

### Key Discovery via WebID

The `WebIDKeyResolver` mentioned above would:

1. HTTP GET the WebID URI with `Accept: text/turtle`
2. Parse the Turtle response
3. Find `cert:key` or `sec:publicKey` triples for the WebID subject
4. Match the `keyId` from the signature to a specific key in the profile
5. Extract the public key bytes
6. Cache the result (with TTL, e.g., 1 hour)

**Confidence:** MEDIUM-HIGH (RFC 9421 is standardized, Python library exists and is current, but the WebID+HTTP Signatures combination is not widely deployed outside Solid research)

---

## 4. IndieAuth Provider Implementation

### Required Endpoints

An IndieAuth authorization server needs exactly three endpoints:

| Endpoint | Purpose | SemPKM Route |
|----------|---------|--------------|
| **Metadata** | Server discovery (RFC 8414 adapted) | `/.well-known/oauth-authorization-server` |
| **Authorization** | User consent + auth code generation | `/auth/authorize` |
| **Token** | Exchange auth code for access token | `/auth/token` |

Optional but recommended:
- **Token Revocation** (`/auth/revoke`) -- invalidate tokens
- **Userinfo** (`/auth/userinfo`) -- return profile info for `profile` scope

### PKCE Flow (Mandatory)

PKCE is **REQUIRED** by the IndieAuth spec (not optional like in base OAuth2).

```
1. Client generates code_verifier (43-128 chars, [A-Za-z0-9-._~])
2. Client computes code_challenge = BASE64URL(SHA256(code_verifier))
3. Client redirects to authorization endpoint with:
   - response_type=code
   - client_id=https://client.example.com/
   - redirect_uri=https://client.example.com/callback
   - state=<random>
   - code_challenge=<challenge>
   - code_challenge_method=S256
   - scope=profile  (or "read write" etc.)
   - me=https://sempkm.example.com/users/alice

4. SemPKM shows consent screen to logged-in user
5. User approves -> SemPKM generates authorization code
6. Redirect to redirect_uri with code=<auth_code>&state=<state>

7. Client POSTs to token endpoint:
   - grant_type=authorization_code
   - code=<auth_code>
   - client_id=https://client.example.com/
   - redirect_uri=https://client.example.com/callback
   - code_verifier=<original_verifier>

8. Token endpoint verifies:
   - code is valid and not expired
   - client_id matches
   - redirect_uri matches
   - SHA256(code_verifier) == stored code_challenge
9. Returns access token + profile URL
```

### Token Format

The IndieAuth spec says tokens are **opaque to clients** -- no specific format required. Options:

**Option A: JWT (recommended for SemPKM)**
- Self-contained, verifiable without DB lookup
- Include `me` (WebID URL), `scope`, `exp`, `iss`
- Sign with instance's Ed25519 key
- `indieweb-utils` already uses JWT for auth codes

**Option B: Random opaque tokens with DB storage**
- Simpler but requires token table and lookups
- Better for revocation

**Recommendation:** JWT for access tokens (stateless verification on API routes), with a revocation list for invalidated tokens.

### Client Identification (No Registration)

A key IndieAuth difference from standard OAuth2: **clients are identified by URL, not pre-registered**. The authorization server:

1. Receives `client_id` as a URL (e.g., `https://other-sempkm.example.com/`)
2. Fetches that URL to verify it exists
3. Optionally parses `h-app` microformat for app name/icon
4. Shows the client info on the consent screen
5. Verifies `redirect_uri` is on the same domain as `client_id` (or explicitly listed)

This means any SemPKM instance can authenticate against any other without pre-registration -- critical for decentralized collaboration.

### Minimal Implementation Checklist

```
[x] GET /.well-known/oauth-authorization-server
    Returns JSON with issuer, authorization_endpoint, token_endpoint,
    code_challenge_methods_supported: ["S256"]

[x] GET /auth/authorize
    - Verify user is logged in (redirect to login if not)
    - Validate client_id (fetch URL, check redirect_uri)
    - Show consent screen with client info + requested scopes
    - On approve: generate auth code, store with PKCE challenge, redirect

[x] POST /auth/token
    - Validate grant_type=authorization_code
    - Verify code, client_id, redirect_uri, code_verifier
    - Return { "access_token": "...", "token_type": "Bearer",
               "me": "https://sempkm.example.com/users/alice",
               "scope": "profile read" }

[x] User profile URL returns HTML with:
    <link rel="indieauth-metadata"
          href="/.well-known/oauth-authorization-server">
```

### Reference Implementations Worth Studying

1. **indieweb-utils** (Python) -- server-side helper functions, JWT-based codes. Best Python reference despite Flask orientation.
2. **datasette-indieauth** (Python) -- clean client-side implementation by Simon Willison. Good for understanding the flow from the consumer side.
3. **WordPress IndieAuth plugin** (PHP) -- most battle-tested IndieAuth provider implementation. Study for edge cases and error handling.
4. **indieauth.com** (service) -- Aaron Parecki's reference implementation. Not open-source server-side, but the spec author's implementation.

**Confidence:** HIGH (IndieAuth spec is stable, well-documented, and the endpoints are straightforward OAuth2 with PKCE)

---

## 5. Corrections to Existing Research

### PunyAuth is Dead
The existing `decentralized-identity.md` lists PunyAuth as a viable option. It was **archived March 5, 2026**. Remove from consideration.

### indieweb-utils Has Server-Side IndieAuth Support
The existing research only mentions "helper functions for IndieAuth endpoints" -- it actually provides `generate_auth_token()`, `redeem_code()`, `validate_access_token()`, and more. These are substantial building blocks, not just helpers.

### HTTP Message Signatures Are Standardized
The existing research mentions "HTTP Signatures (draft-ietf-httpbis-message-signatures)" -- this is now **RFC 9421** (published February 2024). There is a good Python implementation (`http-message-signatures` v2.0.1). This should be the recommended mechanism for server-to-server authentication, not an afterthought.

### WebID-OIDC vs IndieAuth Clarification
The existing research treats these as separate concerns. For SemPKM, the cleaner model is:
- **IndieAuth** for human browser-based authentication (simpler than full OIDC)
- **HTTP Signatures** for server-to-server API authentication (no tokens needed)
- **WebID profile** as the identity document that both systems reference
- Do NOT implement full Solid-OIDC -- it is overengineered for our use case

---

## 6. Recommended Implementation Order for v2.5

### Step 1: WebID Profile Endpoint (1-2 days)
- Content-negotiated route at `/users/{username}`
- Turtle representation with FOAF properties from existing user data in triplestore
- HTML representation with `rel="indieauth-metadata"` and `rel="me"` links
- Fragment URI pattern: `https://domain/users/alice#me` for the person

### Step 2: IndieAuth Metadata + Authorization Endpoint (2-3 days)
- `/.well-known/oauth-authorization-server` metadata endpoint
- `/auth/authorize` with consent screen
- Auth code generation with PKCE challenge storage (can use existing DB or in-memory with TTL)

### Step 3: IndieAuth Token Endpoint (1 day)
- `/auth/token` endpoint
- JWT access token generation signed with instance key
- Token verification middleware for protected routes

### Step 4: Ed25519 Key Management (1 day)
- Generate Ed25519 keypair per user on account creation
- Store encrypted private key in database
- Expose public key in WebID profile document (`cert:key`)
- Expose public key at a fetchable URI for HTTP Signature verification

### Step 5: HTTP Signature Signing/Verification (2-3 days)
- Outbound request signing using `http-message-signatures`
- Inbound request verification with WebID-based key resolver
- Key caching with TTL
- This enables instance-to-instance authenticated API calls

### Total: ~7-10 days for complete identity foundation

---

## Sources

### Libraries (Verified)
- [indieweb-utils v0.10.0](https://pypi.org/project/indieweb-utils/) -- PyPI, September 2025
- [PyLD v2.0.4](https://pypi.org/project/PyLD/) -- PyPI, February 2024
- [http-message-signatures v2.0.1](https://pypi.org/project/http-message-signatures/) -- PyPI, January 2026
- [requests-http-signature](https://pypi.org/project/requests-http-signature/) -- PyPI, requests integration
- [PunyAuth](https://github.com/cleverdevil/punyauth) -- ARCHIVED March 2026
- [Alto](https://github.com/capjamesg/alto) -- Last active October 2021

### Specifications
- [IndieAuth Spec](https://indieauth.spec.indieweb.org/) -- Endpoint requirements, PKCE mandate
- [RFC 9421: HTTP Message Signatures](https://www.rfc-editor.org/rfc/rfc9421) -- Published February 2024
- [Solid WebID Profile](https://solid.github.io/webid-profile/) -- Profile document structure
- [WebID 1.0](https://w3c.github.io/WebID/spec/identity/index.html) -- Identity spec
- [ActivityPub HTTP Signatures](https://swicg.github.io/activitypub-http-signature/) -- Fediverse signing patterns

### Implementation References
- [indieweb-utils IndieAuth docs](https://indieweb-utils.readthedocs.io/en/latest/indieauth.html) -- Server-side function reference
- [Simon Willison: Implementing IndieAuth for Datasette](https://simonwillison.net/2020/Nov/18/indieauth/) -- Client-side implementation walkthrough
- [RFC 9421 HTTP Signatures in 2026 - SocialHub](https://socialhub.activitypub.rocks/t/rfc-9421-http-signatures-in-2026/8427) -- Fediverse adoption status
- [Solid-OIDC issuer discovery](https://github.com/solid/webid-oidc-spec) -- WebID-to-issuer verification flow

---

*Research conducted: 2026-03-07*
*Refreshes: decentralized-identity.md (2026-03-03), collaboration-architecture.md (2026-03-03)*
