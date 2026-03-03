# Decentralized Identity Research

**Created:** 2026-03-03
**Context:** Research into how SemPKM (self-hosted, RDF triplestore-backed PKM) could serve as an identity provider and integrate with decentralized identity systems. Evaluated DIDs, Verifiable Credentials, WebID, IndieAuth, and specific DID methods.

---

## Executive Summary

SemPKM has a natural advantage: DID Documents and Verifiable Credentials are JSON-LD (which is RDF), so they'd live natively in the triplestore. The recommended approach is tiered: start with WebID profiles + IndieAuth (days of work, immediate interoperability), then add did:web + RDF graph signing (cryptographic provenance), then Verifiable Credentials (knowledge attestation). Key management should be server-managed — users should never handle cryptographic keys directly.

---

## 1. W3C Decentralized Identifiers (DIDs)

### Specification Status

- [DID 1.0](https://www.w3.org/press-releases/2022/did-rec/) became a W3C Recommendation on July 19, 2022 (despite formal objections from Google, Apple, Mozilla)
- [DID 1.1](https://www.w3.org/TR/did-1.1/) is currently a Candidate Recommendation (incremental update)
- A new [DID Methods Working Group](https://w3c.github.io/did-methods-wg-charter/2025/did-methods-wg.html) chartered to standardize at least three methods: one ephemeral, one web-based, one fully decentralized

### DID Methods Relevant to Self-Hosted Apps

**[did:key](https://w3c-ccg.github.io/did-key-spec/)** — Simplest method: public key IS the identifier. Zero infrastructure, purely generative. No key rotation or deactivation. Best for ephemeral interactions, testing, short-lived sessions.

**[did:web](https://w3c-ccg.github.io/did-method-web/)** — Maps DIDs to HTTPS. `did:web:example.com:users:alice` resolves to `https://example.com/users/alice/did.json`. No blockchain, just serve JSON. Supports key rotation (update the doc) but no cryptographic audit trail. Inherits DNS/TLS vulnerabilities.

**[did:plc](https://web.plc.directory/spec/v0.1/did-plc)** — Bluesky's method. Self-authenticating operation log with 72-hour recovery window. DID is hash of genesis operation. Currently relies on single directory server (plc.directory). Production-proven at 25M+ Bluesky users.

**[did:dht](https://did-dht.com/)** — Uses BitTorrent's Mainline DHT for resolution. Ed25519 identity key. Fully decentralized, relatively new.

**[did:webvh](https://identity.foundation/didwebvh/v0.3/)** (formerly did:tdw) — "Trust DID Web with Verifiable History." Enhances did:web with `did.jsonl` cryptographic chain, self-certifying identifier (SCID), pre-rotation, optional witnesses. Fixes did:web's trust gaps while keeping ease of deployment. **Python implementation exists (~1500 LOC).**

### DID Documents

JSON-LD documents containing verification methods (public keys), authentication methods, assertion methods, service endpoints, and controller info. Use `@context` of `https://www.w3.org/ns/did/v1` — **natively RDF**, processable as triples. Directly fits SemPKM's triplestore.

### Libraries

- **DIDKit** (Spruce): Rust core with Python bindings (`pip install didkit`). Supports did:key, did:web, VC issuance/verification. **Python bindings archived July 2025** — team recommends [`ssi`](https://github.com/spruceid/ssi) Rust library directly.
- **[PyLD](https://github.com/digitalbazaar/pyld)**: Python JSON-LD processor, essential for URDNA2015 canonicalization
- **python-cryptography**: Ed25519, secp256k1, P-256 key operations
- **[Veramo](https://veramo.io/)** (JS): Full DID/VC framework in TypeScript
- **[Universal Resolver](https://github.com/decentralized-identity/universal-resolver)**: Single interface to resolve any DID method

### Controversy

[W3C overruled formal objections](https://www.theregister.com/2022/07/01/w3c_overrules_objections/) from Google, Apple, Mozilla. Key criticisms: 180+ non-interoperable methods ("namespace land rush"), some rely on blockchains, no privacy requirements. Valid at ecosystem level but less relevant when choosing a specific, well-understood method like did:web.

---

## 2. W3C Verifiable Credentials (VCs)

### Specification Status

[Verifiable Credentials 2.0](https://www.w3.org/press-releases/2025/verifiable-credentials-2-0/) became a W3C Recommendation on May 15, 2025. Seven specs including [VC Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/), Data Integrity 1.0, Bitstring Status List, JOSE/COSE securing, EdDSA/ECDSA cryptosuites.

### Issuer-Holder-Verifier Model

1. **Issuer** creates credential asserting claims about subject, signs with DID assertion key
2. **Holder** stores credential
3. **Holder** presents to **Verifier**
4. **Verifier** checks signature validity, issuer trust, revocation status, claims

VCs are JSON-LD with `@context` including `https://www.w3.org/ns/credentials/v2` — natively RDF.

### Credentials a PKM Tool Could Issue

| Credential Type | Description | Value |
|---|---|---|
| **Authorship Attestation** | "User X authored graph Y on date Z" | Provenance for shared knowledge |
| **Knowledge Contribution** | "User X contributed N triples to domain Y" | Reputation/portfolio |
| **Membership Credential** | "User X is a member of instance at domain.com" | Cross-instance auth |
| **Data Integrity Certificate** | "Named graph X has hash Y, signed by instance Z" | Tamper-evident sharing |
| **Peer Review** | "User X reviewed/endorsed graph Y" | Trust chains |

### Python Libraries

- **DIDKit** (archived but functional): `didkit.issue_credential()`, `didkit.verify_credential()`
- **PyLD + cryptography**: Manual VC construction via [URDNA2015 canonicalization workflow](https://grotto-networking.com/blog/posts/jsonldProofs.html)
- **ACA-Py** (Hyperledger Aries): Full VC lifecycle agent, but heavyweight

---

## 3. WebID

### How It Works

A [WebID](https://w3c.github.io/WebID/spec/identity/index.html) is an HTTP(S) URI denoting an agent. Dereferencing returns an RDF document (Turtle/JSON-LD) describing the agent with FOAF/schema.org properties.

Example: `https://sempkm.example.com/users/alice#me` — fragment `#me` refers to person, document URL returns RDF profile.

### Authentication Mechanisms

- **WebID-TLS** (deprecated): Client-side TLS certs. Browser support degraded.
- **WebID-OIDC** (v0.1.0, 2022): Layer on OpenID Connect with Proof of Possession tokens.
- **[Solid-OIDC](https://solid.github.io/solid-oidc/)**: Current Solid auth spec. Still in draft.

### SemPKM as WebID Provider

SemPKM already stores user data as RDF. Serving [WebID Profile Documents](https://solid.github.io/webid-profile/) at user URLs with content negotiation is ~1 day of work. Include FOAF properties, public keys, `solid:oidcIssuer`. Compatible with Solid ecosystem and any Linked Data consumer.

---

## 4. did:web for SemPKM — Detailed

### Resolution

`did:web:sempkm.example.com:users:alice` → `https://sempkm.example.com/users/alice/did.json`

Two FastAPI routes:
```python
@app.get("/.well-known/did.json")       # Instance DID
@app.get("/users/{username}/did.json")   # Per-user DIDs
```

### Pros
- Zero additional infrastructure
- Globally resolvable DIDs mapping to existing URL structure
- W3C DID Methods WG actively standardizing
- Path-based DIDs for per-user identities

### Cons
- DNS dependency: identity security = DNS + TLS security
- No cryptographic audit trail (update document = no history)
- Server operator can change any user's DID Document
- Privacy: DNS providers and server logs track resolution

### Upgrade Path: did:webvh
Start with did:web (minimal effort), upgrade to [did:webvh](https://identity.foundation/didwebvh/v0.3/) when spec stabilizes. did:webvh adds cryptographic version chain, pre-rotation, witnesses, and portability across domains. Python implementation exists.

---

## 5. AT Protocol / did:plc

### How did:plc Works

Operation log with genesis → updates → recovery. DID is SHA-256 hash of genesis operation. 72-hour recovery window via higher-authority rotation keys. Currently relies on plc.directory (centralization risk, being addressed via Swiss association governance).

### Could SemPKM Participate?

Theoretically possible, practically challenging:
- AT Protocol data model (signed record repos) fundamentally different from RDF triplestores
- Custom [Lexicons](https://docs.bsky.app/docs/advanced-guides/custom-schemas) could represent knowledge, but bridging is enormous effort
- [2025 roadmap](https://docs.bsky.app/blog/2025-protocol-roadmap-spring): 41M+ users, PDS web interface, shared/group-private data planned

### did:plc vs did:web

| Aspect | did:plc | did:web |
|---|---|---|
| Key rotation | Full with audit trail | Replace doc, no audit |
| Recovery | 72-hour window | None |
| Infrastructure | Requires plc.directory | Just HTTPS |
| Self-hosted | Not really | Yes, fully |
| Portability | Full (survives domain changes) | None (domain-bound) |
| Maturity | Production (25M+ users) | Wide adoption |

**Verdict:** did:web more appropriate for self-hosted app. AT Protocol integration not worth the effort.

---

## 6. IndieAuth / IndieWeb Identity

### How [IndieAuth](https://indieauth.spec.indieweb.org/) Works

OAuth2-based identity where URLs are identifiers:
1. User enters their URL (e.g., `https://sempkm.example.com/users/alice`)
2. Client discovers `rel=indieauth-metadata` link
3. OAuth2 authorization flow with mandatory PKCE
4. Profile URL is the verified identity

No client registration needed. Both users and apps identified by URLs.

### [RelMeAuth](https://indieweb.org/RelMeAuth)

Bidirectional link verification: your site links to Mastodon with `rel="me"`, Mastodon links back. Used for Mastodon verified checkmarks.

### IndieAuth vs DIDs

| Aspect | IndieAuth | DIDs (did:web) |
|---|---|---|
| Identifier | URL (your domain) | DID string |
| Complexity | OAuth2 (well-understood) | New protocol |
| Key management | None for users | Server-managed keys |
| Cryptographic proof | No (relies on HTTPS) | Yes (Ed25519 signatures) |
| Graph signing | Not possible | Yes — main value-add |
| Maturity | Production, many implementations | Evolving |

### Python Libraries

- [indieweb-utils](https://indieweb-utils.readthedocs.io/en/latest/indieauth.html): Helper functions for IndieAuth endpoints
- [Alto](https://github.com/capjamesg/alto): Flask-based IndieAuth authorization + token endpoint
- [Punyauth](https://github.com/cleverdevil/punyauth): Pure Python IndieAuth endpoint

**Verdict:** Highest value-to-complexity ratio for authentication. Build alongside DIDs — IndieAuth for auth, DIDs for signing.

---

## 7. RDF Graph Signing

[RDF Dataset Canonicalization](https://www.w3.org/news/2024/rdf-dataset-canonicalization-is-a-w3c-recommendation/) (URDNA2015) became a W3C Recommendation in 2024. This enables:

1. Canonicalize named graph using URDNA2015 (N-Quads output)
2. SHA-256 hash the canonical form
3. Sign with user's Ed25519 key (from DID)
4. Store proof as RDF alongside the graph

```python
from pyld import jsonld
canonical = jsonld.normalize(graph_as_jsonld, {
    'algorithm': 'URDNA2015',
    'format': 'application/n-quads'
})
# Hash and sign with user's key
```

Directly applicable to SemPKM's named graph architecture — knowledge contributions get cryptographically signed provenance.

---

## 8. Integration with Collaboration Architecture

The identity work layers onto the [collaboration architecture](collaboration-architecture.md):

| Collab Layer | Identity Integration |
|---|---|
| Layer 1: RDF Patch Sync | Sign patches with user DID keys → verifiable change attribution |
| Layer 2: LDN Notifications | Notifications identify sender by DID, receiver verifies |
| Layer 3: Federated Identity | **This IS the identity layer** — WebID + did:web + IndieAuth |
| Layer 4: CRDT Real-Time | DID Auth for session establishment between instances |

---

## Recommended Phased Approach

### Phase 1: Foundation (WebID + IndieAuth)
- Serve WebID profiles at user URLs (Turtle via content negotiation)
- Implement IndieAuth provider (authorization + token endpoints)
- Add `rel="me"` for fediverse verification
- **Effort:** ~1 week | **Value:** Immediate interoperability with IndieWeb + Solid ecosystem

### Phase 2: DID Layer (did:web)
- Generate Ed25519 key pairs per user (server-managed)
- Serve DID Documents at did:web resolution paths
- Sign named graphs with URDNA2015 + user keys
- Store proofs as RDF in triplestore
- **Effort:** ~2-3 weeks | **Value:** Cryptographic provenance for knowledge sharing

### Phase 3: Verifiable Credentials
- Issue authorship/contribution VCs using DID keys
- VC verification endpoint
- Cross-instance knowledge sharing with signed provenance
- **Effort:** ~2-3 weeks | **Value:** Portable, verifiable knowledge attestations

### Phase 4: Enhanced Trust (did:webvh)
- Migrate did:web → did:webvh for verifiable history
- Pre-rotation for key compromise recovery
- **Effort:** ~4-6 weeks | **Value:** Tamper-evident identity history

### What NOT to Build
- Full Solid Pod provider (different problem, no SPARQL)
- AT Protocol integration (incompatible data models)
- Blockchain-based DIDs (unnecessary complexity)
- Custom DID method (use existing methods)
- Full SSI wallet (overkill for PKM)

### Key Management Strategy

Users should **never** manage cryptographic keys directly. Approach:
- Server generates Ed25519 key pairs per user, stores encrypted
- Users authenticate via normal password/2FA
- Progressive disclosure: power users can optionally provide own keys later
- [Key management is the biggest practical barrier](https://deepthix.com/en/blog/atproto-gestion-cles-decentralisation-1771755536559/) to decentralized identity adoption

---

## Sources

### W3C Specifications
- [DID 1.0 W3C Recommendation](https://www.w3.org/press-releases/2022/did-rec/)
- [DID 1.1 Candidate Recommendation](https://www.w3.org/TR/did-1.1/)
- [VC 2.0 W3C Recommendation](https://www.w3.org/press-releases/2025/verifiable-credentials-2-0/)
- [VC Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/)
- [RDF Dataset Canonicalization](https://www.w3.org/news/2024/rdf-dataset-canonicalization-is-a-w3c-recommendation/)
- [DID Methods WG Charter](https://w3c.github.io/did-methods-wg-charter/2025/did-methods-wg.html)

### DID Methods
- [did:web](https://w3c-ccg.github.io/did-method-web/) | [did:key](https://w3c-ccg.github.io/did-key-spec/) | [did:plc](https://web.plc.directory/spec/v0.1/did-plc) | [did:dht](https://did-dht.com/) | [did:webvh](https://identity.foundation/didwebvh/v0.3/)

### WebID and Solid
- [WebID 1.0](https://w3c.github.io/WebID/spec/identity/index.html) | [WebID Profile](https://solid.github.io/webid-profile/) | [Solid-OIDC](https://solid.github.io/solid-oidc/)

### IndieAuth and IndieWeb
- [IndieAuth spec](https://indieauth.spec.indieweb.org/) | [RelMeAuth](https://indieweb.org/RelMeAuth) | [IndieAuth wiki](https://indieweb.org/IndieAuth)

### AT Protocol
- [2025 Protocol Roadmap](https://docs.bsky.app/blog/2025-protocol-roadmap-spring) | [Custom Schemas](https://docs.bsky.app/docs/advanced-guides/custom-schemas) | [AT Protocol DID spec](https://atproto.com/specs/did)

### Libraries
- [PyLD](https://github.com/digitalbazaar/pyld) | [Universal Resolver](https://github.com/decentralized-identity/universal-resolver) | [indieweb-utils](https://indieweb-utils.readthedocs.io/en/latest/indieauth.html) | [Punyauth](https://github.com/cleverdevil/punyauth) | [Alto](https://github.com/capjamesg/alto)

### Analysis
- [W3C overrules DID objections](https://www.theregister.com/2022/07/01/w3c_overrules_objections/) | [AT Protocol key management](https://deepthix.com/en/blog/atproto-gestion-cles-decentralisation-1771755536559/) | [Fediverse DID integration](https://github.com/WebOfTrustInfo/rwot9-prague/blob/master/topics-and-advance-readings/fediverse-did-integration.md) | [VC verification tutorial](https://grotto-networking.com/blog/posts/jsonldProofs.html)

---

*Research conducted: 2026-03-03*
