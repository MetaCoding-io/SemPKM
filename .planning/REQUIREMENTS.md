# Requirements: SemPKM v2.5

**Defined:** 2026-03-07
**Core Value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## v2.5 Requirements

Requirements for v2.5 Polish, Import & Identity. Each maps to roadmap phases.

### UI Cleanup

- [ ] **UICL-01**: VFS browser markdown preview text renders at correct size (not zoomed in)
- [ ] **UICL-02**: VFS browser content does not show unwanted underline styling
- [ ] **UICL-03**: General UI polish pass — audit-driven tweaks (specifics added during discuss-phase)

### Obsidian Import

- [ ] **OBSI-01**: User can upload/point to an Obsidian vault directory for scanning
- [ ] **OBSI-02**: Scan results show file count, detected types, frontmatter keys, link targets, and tags
- [ ] **OBSI-03**: User can interactively map Obsidian note categories to Mental Model types
- [ ] **OBSI-04**: User can map frontmatter keys to RDF properties for each type
- [ ] **OBSI-05**: User can preview mapped objects before committing import
- [ ] **OBSI-06**: Batch import creates objects with bodies, properties, and edges via Command API
- [ ] **OBSI-07**: Wiki-links and tags are resolved to edges between imported objects

### WebID

- [ ] **WBID-01**: Each user has a WebID URI (e.g. `https://instance/users/alice#me`)
- [ ] **WBID-02**: Dereferencing the WebID URI returns an RDF profile document (FOAF/schema.org properties)
- [ ] **WBID-03**: Content negotiation serves Turtle, JSON-LD, or HTML based on Accept header
- [ ] **WBID-04**: Profile page includes `rel="me"` links for fediverse verification
- [ ] **WBID-05**: Server generates Ed25519 key pair per user, stores encrypted
- [ ] **WBID-06**: Public key is published in the WebID profile document

### IndieAuth

- [ ] **IAUTH-01**: Server exposes `rel="indieauth-metadata"` link for client discovery
- [ ] **IAUTH-02**: Authorization endpoint handles OAuth2 authorization code flow with mandatory PKCE
- [ ] **IAUTH-03**: Token endpoint issues access tokens after code exchange
- [ ] **IAUTH-04**: Token endpoint supports token verification (introspection)
- [ ] **IAUTH-05**: User sees consent screen showing requesting app and requested scopes

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Obsidian Import (Triage)

- **OBSI-08**: SHACL fix guidance engine suggests fixes for validation violations on imported data
- **OBSI-09**: Click-to-edit lint triage workflow for reviewing imported objects
- **OBSI-10**: LLM-assisted type classification for ambiguous notes

### Identity (Advanced)

- **IDNT-01**: did:web DID Documents served at resolution paths
- **IDNT-02**: RDF graph signing with URDNA2015 canonicalization + Ed25519
- **IDNT-03**: Verifiable Credentials issuance (authorship attestation)
- **IDNT-04**: did:webvh migration for verifiable identity history

### Collaboration

- **COLLAB-01**: RDF Patch change log for named graph sync
- **COLLAB-02**: Linked Data Notifications for cross-instance awareness
- **COLLAB-03**: Cross-instance permissions using WebID

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Full Solid Pod server | Different problem (app-data separation), no SPARQL |
| AT Protocol / did:plc integration | Incompatible data models, enormous effort |
| Real-time CRDT co-editing | W3C CRDT for RDF CG still pre-standard |
| Full ActivityPub S2S federation | Wrong use case for PKM, enormous complexity |
| Blockchain-based DIDs | Unnecessary complexity for self-hosted app |
| Obsidian vault write-back/sync | One-way import only for v2.5 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (populated by roadmapper) | | |

**Coverage:**
- v2.5 requirements: 20 total
- Mapped to phases: 0
- Unmapped: 20

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after initial definition*
