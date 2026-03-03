# SemPKM Future Milestones Planning

**Created:** 2026-02-26
**Context:** Planning session after v2.0 completion. Captures feature ideas, milestone breakdown, dependency map, parallelization strategy, and architectural decisions.

---

## Key Architectural Decision: No VSCode/Theia

**Decision:** Stay with the current FastAPI + htmx + vanilla JS stack. Do NOT adopt Theia or VSCode as the IDE shell.

**Rationale:**
- Theming is already substantially done (theme.css, CSS custom properties, dark mode Phase 13, settings Phase 15). Full user-configurable themes are a CSS variable extension problem, not an architecture problem.
- Flexible panel layout (more than Split.js) is achievable with **GoldenLayout** (pure JS, no framework required) — handles arbitrary drag-to-dock panel rearrangement with saved layout configs. Integrates cleanly with htmx-rendered panel content.
- Adopting Theia/VSCode would mean a complete frontend rewrite, extension model, and a new paradigm with massive complexity. Not justified when the current stack can deliver the UX goals.

**What this means for future phases:**
- Theming: CSS variable token sets + theme picker in settings
- Flexible panels: GoldenLayout integration phase
- Dashboards: Store layout configs in RDF, apply via GoldenLayout API

---

## Parallelization Strategy

The biggest lever for parallel execution is **research milestones** where all phases run simultaneously, followed by **implementation milestones** where independent features overlap in plans.

**Research milestone pattern:**
- All research phases spawn in parallel (4+ agents at once)
- Each produces a RESEARCH.md and recommendation
- Synthesis phase reviews all research, makes final decisions
- Then plan implementation phases with confidence

**Implementation milestone pattern:**
- Features with independent backends (search, VFS, SPARQL) can be parallel plans within a phase
- Features that share UI components (dashboards, panels) must sequence after shared infrastructure

---

## Milestone: v2.1 — Research & Architecture Decisions

**Goal:** Resolve all major open questions before building. No implementation — research and decisions only.

**All phases run in parallel.**

### Phase 20: Full-Text Search + Vector Store Research
**Agent focus:** What is the right search technology for SemPKM?

Key questions:
- Are there open-source RDF triplestores with built-in FTS (RDF4J, Apache Jena, Oxigraph)?
- RDF4J's Lucene integration — current state, query syntax, config?
- OpenSearch as a sidecar: index `urn:sempkm:current` graph, sync via webhooks?
- pgvector / sentence-transformers for semantic similarity search?
- How does FTS compose with SPARQL filtering?
- What does the write path look like (index on EventStore.commit)?

Output: RESEARCH.md with recommended approach, indexing strategy, query API design.

### Phase 21: SPARQL Interface Research
**Agent focus:** What is the most modern, beautiful SPARQL UI to integrate?

Key questions:
- Zazuko Yasgui — current state (2025/2026), license, embed options?
- Other modern SPARQL UIs (SPARQL Playground, Triply, etc.)?
- Iframe embed vs. sidecar deployment vs. custom implementation?
- Autocomplete: how does it work in Yasgui (schema-aware, prefix-aware)?
- "Pills" / inline object rendering for query results — does Yasgui support it or do we build it?
- Saved queries + query history: server-side (user-scoped RDF storage) or localStorage?
- Integration with SemPKM's existing `/sparql` debug endpoint?

Output: RESEARCH.md with recommended approach, integration plan, UI mockup description.

### Phase 22: Virtual Filesystem — Technology Validation
**Agent focus:** Validate the WebDAV approach from `.planning/research/virtual-filesystem.md` and identify implementation risks.

Existing research: `.planning/research/virtual-filesystem.md` — comprehensive, covers prior art, design, protocol choices.

Key questions to validate:
- `wsgidav` + FastAPI integration — current state, async support?
- FUSE as alternative — `fusepy` / `pyfuse3` current state on Linux?
- What's the minimum viable MountSpec vocabulary (start with `flat` and `tag-groups` strategies)?
- How does the write path integrate with EventStore.commit?
- WebDAV discovery — will macOS Finder / Linux file managers mount it without config?
- Performance: SPARQL on every readdir() — acceptable? Caching strategy?

Output: RESEARCH.md with implementation plan, phased rollout (read-only first, then writes), risks.

### Phase 23: UI Shell Architecture Research
**Agent focus:** GoldenLayout for flexible panels + theming token system design.

Key questions:
- GoldenLayout 2.x vs alternatives (Flexlayout-model, Dockview) — feature comparison, bundle size, htmx compatibility?
- How does GoldenLayout interact with htmx partial renders inside panels?
- Layout persistence: JSON config → store in RDF as user preference, load on workspace init?
- Theme token system: what CSS custom property vocabulary covers all components (sidebar, tabs, editor, graph, forms, modals)?
- Model-contributed themes: how does a Mental Model declare a theme bundle?
- Can GoldenLayout handle the "Dashboards" use case (named saved layouts)?

Output: RESEARCH.md with GoldenLayout integration design, CSS token vocabulary, theme contribution spec.

---

## Milestone: v2.2 — Data Discovery

**Goal:** Make the knowledge graph findable and queryable. Three independent features, mostly parallel.

### Phase 24: Full-Text Search Implementation
Implement the technology chosen in Phase 20 research.

Likely plans:
- Backend: index integration (RDF4J Lucene or OpenSearch sidecar), EventStore hook, search API endpoint
- Frontend: search UI (command palette integration, search results panel, filter by type/date)

### Phase 25: SPARQL Interface Integration
Implement the approach chosen in Phase 21 research.

Likely plans:
- Integration: embed Yasgui (or chosen tool) as a special tab / bottom panel tab
- Enhancements: saved queries (RDF storage, user-scoped), query history, inline object pills in results
- Polish: autocomplete schema-aware, prefix auto-complete from PrefixRegistry

### Phase 26: Virtual Filesystem MVP
Implement the WebDAV approach validated in Phase 22 research.

Likely plans:
- Read-only WebDAV server: wsgidav + FastAPI mount, MountSpec model, SPARQL-to-directory mapping
- Markdown+frontmatter rendering: SHACL-driven frontmatter fields, body property rendering
- MountSpec UI: configure mounts via Settings page
- (Optional next milestone) Write support with SHACL validation on parse-back

---

## Milestone: v2.3 — Shell & Navigation

**Goal:** Dashboards, flexible panels, full theming. Depends on v2.2 UI shell research (Phase 23).

### Phase 27: GoldenLayout Integration
Replace or extend Split.js with GoldenLayout for arbitrary drag-to-dock panel rearrangement.

- GoldenLayout initialization, panel registry, htmx content loading into panels
- Layout persistence (JSON config in RDF as user preference)
- Migration from existing Split.js panel model

### Phase 28: Dashboards (Named Layouts)
User-defined and model-provided named workspace layouts (Bases equivalent).

- Dashboard data model (RDF storage, user-scoped + model-provided)
- Dashboard picker UI (sidebar section or command palette)
- Mental Model manifest: `dashboards` key for model-provided layouts
- Default dashboards for basic-pkm model (e.g. "Research Mode", "Writing Mode")

### Phase 29: Full Theming System
User-selectable themes; model-contributed theme bundles.

- CSS custom property token vocabulary (finalized from Phase 23 research)
- Built-in themes: Dark+, Light, High Contrast, Solarized
- Theme picker in settings
- Mental Model manifest: `theme` key for model-contributed themes
- Theme preview in settings

---

## Milestone: v2.4 — Low-Code & Workflows

**Goal:** SemPKM as a platform for structured user interactions. Depends on v2.3 shell being stable.

### Phase 30: Low-Code UI Builder
Users compose basic components tied to SemPKM actions. Notion + Airflow inspired.

- Component palette: form fields, buttons, text blocks, object references, view embeds
- Layout canvas: drag-and-drop component placement
- Action binding: bind components to SemPKM commands (object.create, object.patch, etc.)
- Save as Mental Model artifact (user-created "App")

Design principle: NOT a general-purpose UI builder. Components are SemPKM-native. No arbitrary HTML/JS injection.

### Phase 31: Minimal Workflow Orchestration
Orchestrated sequences of views/forms — not n8n (no business logic engine). Think CRM onboarding.

- Workflow definition: sequence of steps, each a form or view, with conditions
- Step types: form (SHACL-validated), confirmation, object reference picker, note append
- Example: "Add Client" → "Add Project" → "Add Invoice" → "Log success to note body"
- Trigger types: manual (sidebar entry), webhook (event-triggered), model-provided workflow
- State: workflow instance stored as RDF (current step, collected values, outcome)

Design principle: Complement n8n for complex business logic. SemPKM workflows are UI-orchestration only — for data collection and structured entry, not computation.

---

## Tech Debt Phases (schedule across milestones)

These are from CONCERNS.md. Schedule as plan slots within feature milestones rather than dedicated phases.

**High priority (Phase 19 scope):**
- Label cache invalidation after writes
- datetime.now() → datetime.now(timezone.utc) in browser router
- EventStore DI in browser router write handlers
- CORS wildcard + credentials fix
- Debug endpoint owner-only guard
- IRI validation before SPARQL interpolation

**Medium priority (schedule in v2.1-v2.2):**
- Alembic migration runner at startup (replace create_all)
- SMTP email delivery implementation
- Session cleanup job (expired sessions accumulate)
- ViewSpecService TTL cache (two SPARQL queries per lookup)
- source_model attribution for multi-model installs
- validation/report.py hash() fallback → raise instead

**Lower priority (v2.3+):**
- browser/router.py monolith split into sub-routers
- LabelService Redis cache for multi-worker deployments
- Dependency pinning in pyproject.toml

---

## Standing Decisions for All Future Phases

1. **E2E tests required**: Every phase with user-visible behavior must add/update Playwright tests in `e2e/tests/`. Gate enforced in execute-plan.md.
2. **User guide docs required**: Any user-visible feature must be reflected in `docs/`. Gate enforced in execute-plan.md.
3. **No VSCode/Theia**: Current stack handles theming and flexible panels. Do not revisit unless constraints change dramatically.
4. **VFS uses WebDAV first**: FUSE is an option but WebDAV is the starting point (cross-platform, existing HTTP infra).
5. **Workflows are UI-orchestration only**: Do not replicate n8n. Deep n8n integration is the answer for complex business logic.
6. **Mental Models stay the extensibility mechanism**: Themes, dashboards, workflows, apps — all contributed via Mental Model manifests.

---

## Milestone: (Future) Collaboration & Federation

**Goal:** Enable multi-instance knowledge sharing with data sovereignty. Self-hosted SemPKM instances sync named graphs, notify each other of changes, and authenticate cross-instance users. Real-time co-editing deferred until CRDT-for-RDF ecosystem matures.

**Depends on:** SPARQL Interface milestone (permissions infrastructure needed for cross-instance access control)

**Research:** [`collaboration-architecture.md`](collaboration-architecture.md) — comprehensive analysis of SOLID, ActivityPub, RDF sync, CRDTs, and hypertext collaboration patterns (40+ sources)

### Phase A: RDF Patch Change Tracking

Wrap triplestore writes to emit RDF Patch log entries. Foundation for all sync.

- Patch log model (SQLAlchemy or append-only file per named graph)
- EventStore integration: each commit() emits corresponding RDF Patch entries
- Patch replay: apply a patch sequence to bring a graph to a target version
- Graph versioning: monotonic version counter per named graph

Key tech: [RDF Patch format](https://afs.github.io/rdf-patch/), [Jelly-Patch](https://jelly-rdf.github.io/dev/) (binary, when Python impl lands)

### Phase B: Named Graph Sync API

HTTP sync endpoint for exchanging patches between SemPKM instances.

- `GET /api/sync/{graph}?since={version}` — returns patches since version
- `POST /api/sync/{graph}` — accept and apply incoming patches
- Remote configuration: list of peer instances with sync direction (push/pull/both)
- Conflict detection: reject patches when base version has diverged (manual merge)
- [SPARQL Graph Store Protocol](https://w3c.github.io/sparql-graph-store-protocol/) for full graph bootstrap

### Phase C: Cross-Instance Notifications

[Linked Data Notifications (LDN)](https://www.w3.org/TR/ldn/) for change awareness + [Webmention](https://www.w3.org/TR/webmention/) for cross-references.

- LDN Inbox endpoint: receive notifications as JSON-LD
- Subscription model: instance B subscribes to graph changes on instance A
- Notification triggers pull-based sync from Phase B
- Webmention: when an object references a URL on another instance, notify them

### Phase D: Federated Identity (WebID)

[WebID](https://www.w3.org/wiki/WebID) for cross-instance user identity + ACL on shared graphs.

- Each SemPKM user gets a WebID (profile URL resolving to RDF)
- WebID authentication for incoming sync/API requests
- Named graph ACL: grant read/write to specific WebIDs
- Local auth system unchanged; WebID layered on top for federation

### Phase E: Collaboration UI

User-facing features for managing shared graphs and remote instances.

- Settings: manage remote instances (add, remove, sync status)
- Graph sharing: select named graphs to share, set permissions per WebID
- Sync status: visual indicator of sync state per graph (synced, pending, conflict)
- Incoming changes: notification panel for cross-instance activity

### Phase F: Real-Time Collaboration (Deferred)

CRDT-based concurrent editing — **build only when ecosystem is ready.**

- Watch: [W3C CRDT for RDF CG](https://www.w3.org/community/crdt4rdf/), [NextGraph](https://nextgraph.org/), [m-ld](https://m-ld.org/)
- Integrate when a mature Python/JS library exists
- Scope: concurrent editing of individual resources within shared named graphs
- Until then, Layer 1 (patch-based async sync) handles collaboration

---

## Milestone: (Future) Identity & Authentication

**Goal:** Make SemPKM users verifiable identities on the web. Serve WebID profiles, provide IndieAuth login, issue DID-based identifiers, sign knowledge graphs cryptographically, and issue Verifiable Credentials for knowledge attestation.

**Depends on:** Can start independently (Phases A-B have no dependencies). Phases C-D depend on Collaboration & Federation milestone (cross-instance sharing needs signed graphs).

**Research:** [`decentralized-identity.md`](decentralized-identity.md) — comprehensive analysis of DIDs, VCs, WebID, IndieAuth, did:web, did:plc, RDF graph signing (50+ sources)

### Phase A: WebID Profiles + rel="me"

Serve user URLs as RDF via content negotiation. Immediate interop with Solid ecosystem and fediverse.

- Content negotiation on `/users/{username}`: Turtle for RDF clients, HTML for browsers
- FOAF/schema.org properties from existing user data in triplestore
- `rel="me"` links on profile pages for [RelMeAuth](https://indieweb.org/RelMeAuth) fediverse verification
- Key tech: existing RDF4J + FastAPI content negotiation

### Phase B: IndieAuth Provider

[IndieAuth](https://indieauth.spec.indieweb.org/) (OAuth2 + URL-as-identity) lets SemPKM users sign into other IndieWeb services.

- Authorization endpoint: `/auth/indieauth/authorize`
- Token endpoint: `/auth/indieauth/token`
- Server metadata at `rel=indieauth-metadata`
- Mandatory PKCE per current spec
- Python libs: [indieweb-utils](https://indieweb-utils.readthedocs.io/en/latest/indieauth.html), [Punyauth](https://github.com/cleverdevil/punyauth), [Alto](https://github.com/capjamesg/alto)

### Phase C: did:web DID Documents + Graph Signing

[did:web](https://w3c-ccg.github.io/did-method-web/) maps to existing HTTPS. Each user gets a globally resolvable DID.

- Generate Ed25519 key pairs per user (server-managed, stored encrypted)
- Serve DID Documents at `/.well-known/did.json` (instance) and `/users/{username}/did.json` (per-user)
- Sign named graphs: [URDNA2015](https://www.w3.org/news/2024/rdf-dataset-canonicalization-is-a-w3c-recommendation/) canonicalization → SHA-256 → Ed25519 signature
- Store proofs as RDF in triplestore (native JSON-LD)
- Key risk: key management UX — users must never handle keys directly

### Phase D: Verifiable Credentials

[VC 2.0](https://www.w3.org/TR/vc-data-model-2.0/) (W3C Rec, May 2025) for knowledge attestation.

- Issue authorship/contribution VCs using DID assertion keys
- VC verification endpoint: `/api/vc/verify`
- Credential types: authorship, membership, data integrity certificates
- VCs stored as RDF named graphs (JSON-LD is RDF)
- Cross-instance knowledge sharing with signed, verifiable provenance

### Phase E: did:webvh Migration (Future)

Upgrade from did:web to [did:webvh](https://identity.foundation/didwebvh/v0.3/) for verifiable history.

- `did.jsonl` cryptographic version chain
- Pre-rotation for key compromise recovery
- Optional witness support
- Python implementation exists (~1500 LOC)
- Build when [DID Methods WG](https://w3c.github.io/did-methods-wg-charter/2025/did-methods-wg.html) standardizes web-based method

### What NOT to Build
- Full Solid Pod provider (different problem, no SPARQL)
- AT Protocol / did:plc integration (incompatible data models, depends on plc.directory)
- Blockchain-based DIDs (unnecessary complexity)
- Custom DID method (use existing methods)
- Full SSI wallet (overkill for PKM)

---

## Milestone: (Future) Global Lint Status

**Goal:** Provide a workspace-wide SHACL validation dashboard so users can see every violation, warning, and info across all objects at a glance, filter and search results, read actionable fix guidance, and click directly into the offending object to fix issues in a continuous triage workflow.

**Depends on:** v2.3 (dockview panel infrastructure, object view redesign for field-focus targets). Can start research independently.

**Builds on:** Existing `ValidationService` + `AsyncValidationQueue` pipeline (runs pyshacl after every EventStore.commit()), `ValidationReport`/`ValidationResult` dataclasses, per-object `lint_panel.html`, `/api/validation/latest` endpoint.

### Phase A: Global Validation Data Model and API

Extend the validation pipeline to persist per-object, per-result detail and expose it via paginated API endpoints.

- New storage: individual `ValidationResult` records queryable by focus_node, severity, path, constraint_component
- Storage options: RDF named graph (`urn:sempkm:lint-results`) vs. SQLAlchemy model — research trade-offs
- API: `GET /api/lint/results?severity=Violation&type=Note&page=1` with filtering, sorting, pagination
- Incremental validation: only re-validate objects whose triples changed in the commit (performance at scale)
- Existing `ValidationReportSummary` for aggregate counts remains; new detail layer adds per-result access

### Phase B: Global Lint Dashboard UI

Dockview panel or dedicated page showing all validation results across all objects.

- Summary bar: total violations / warnings / infos with color-coded badges
- Result list: table or card layout with object label, severity icon, property path, message, timestamp
- Filters: severity toggles, type dropdown (from ModelRegistry), keyword search
- Sorting: by severity, object name, property path, timestamp
- Pagination or virtual scroll for large result sets
- Status bar indicator: persistent badge showing knowledge base health at a glance
- Design: htmx partials + CSS custom properties, following existing SemPKM patterns

### Phase C: Fix Guidance Engine

Generate human-readable, actionable fix messages from SHACL shape metadata.

- Template registry: maps `sh:sourceConstraintComponent` URIs to message templates
- Built-in templates for top 10 constraint types:
  - `sh:MinCountConstraintComponent` → "This field requires at least {minCount} value(s) -- add a {propertyName} to fix"
  - `sh:MaxCountConstraintComponent` → "This field allows at most {maxCount} value(s) -- remove extras to fix"
  - `sh:DatatypeConstraintComponent` → "Expected {datatype} but got {actualValue} -- update the value format"
  - `sh:PatternConstraintComponent` → "Value must match pattern {pattern} -- check formatting"
  - `sh:ClassConstraintComponent` → "Value must be an instance of {class} -- select the right type"
  - `sh:MinLengthConstraintComponent`, `sh:MaxLengthConstraintComponent`, `sh:InConstraintComponent`, `sh:NodeKindConstraintComponent`, `sh:HasValueConstraintComponent`
- Shape-author override: if `sh:description` is set on the property shape, use it as the guidance message
- Mental Model helptext: models can provide `sempkm:fixGuidance` annotations on shapes for domain-specific advice
- Graceful fallback: unknown constraint types get "Constraint violated on {path} -- check the value against the shape definition"

### Phase D: Click-to-Edit Triage Workflow

Wire the global lint dashboard to the object editing workflow for continuous issue resolution.

- Click a lint result row → open object in dockview pane (or focus existing pane) → scroll to field
- Extend `jumpToField()` to work cross-pane (currently only works within the active object's lint tab)
- After save: lint dashboard refreshes to show updated results (resolved issues disappear)
- Sequential triage: user works through list top-to-bottom, fixing each issue without leaving the lint view
- Keyboard navigation: arrow keys through lint results, Enter to open, Escape to return to lint view

### What NOT to Build
- Auto-fix engine (programmatic correction of violations) -- too risky, bypasses user intent
- Custom validation rules outside SHACL -- SHACL is the constraint language, extend via shapes
- Cross-object relationship validation (orphan detection, referential integrity) -- separate graph-health feature
- Real-time collaborative lint (multi-user live updates) -- depends on Collaboration milestone

---

## Research Artifacts

- `virtual-filesystem.md` — Comprehensive prior art + design for VFS feature (ready for Phase 22 validation)
- `collaboration-architecture.md` — SOLID, ActivityPub, RDF sync, CRDTs, hypertext collaboration research (2026-03-03)
- `decentralized-identity.md` — DIDs, VCs, WebID, IndieAuth, RDF graph signing research (2026-03-03)

---

*Created: 2026-02-26 — planning session after v2.0 milestone completion*
