# Roadmap: SemPKM

## Milestones

- ✅ **v1.0 MVP** — Phases 1-9 (shipped 2026-02-23) — [Full details](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 Tighten Web UI** — Phases 10-19 (shipped 2026-03-01) — [Full details](milestones/v2.0-ROADMAP.md)
- ✅ **v2.1 Architecture Decision Gate** — Phases 20-22 (shipped 2026-03-01) — [Full details](milestones/v2.1-ROADMAP.md) — [Archive](milestones/v2.1-REQUIREMENTS.md)
- ✅ **v2.2 Data Discovery** — Phases 23-28 (shipped 2026-03-01) — [Full details](milestones/v2.2-ROADMAP.md)
- ✅ **v2.3 Shell, Navigation & Views** — Phases 29-34 (shipped 2026-03-03)
- 🚧 **v2.4 Inference & Polish** — Phases 35-40 (in progress) — [Research](research/shacl-owl-inference.md)
- (future) **SPARQL Interface** -- Rich SPARQL query experience with permissions, autocomplete, pills, history, saved queries, and named query views
- (future) **Obsidian Import & Lint Triage** -- In-app Obsidian import wizard, SHACL fix guidance engine, and click-to-edit lint triage workflow — [Research](research/obsidian-import-wizard-ux.md)
- (future) **Identity: WebID + IndieAuth** -- WebID profiles with content negotiation, IndieAuth provider with PKCE (Phases A-B) — [Research](research/decentralized-identity.md)
- (future) **Collaboration & Federation** -- Multi-instance sync via RDF Patch, LDN notifications, federated identity, collaboration UI — [Research](research/collaboration-architecture.md)
- (future) **Identity: DIDs + Verifiable Credentials** -- did:web documents, RDF graph signing, VC 2.0 issuance, did:webvh migration (Phases C-E) — [Research](research/decentralized-identity.md)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-9) — SHIPPED 2026-02-23</summary>

- [x] Phase 1: Core Data Foundation (4/4 plans) — completed 2026-02-21
- [x] Phase 2: Semantic Services (2/2 plans) — completed 2026-02-21
- [x] Phase 3: Mental Model System (3/3 plans) — completed 2026-02-22
- [x] Phase 4: Admin Shell and Object Creation (6/6 plans) — completed 2026-02-22
- [x] Phase 5: Data Browsing and Visualization (3/3 plans) — completed 2026-02-22
- [x] Phase 6: User and Team Management (4/4 plans) — completed 2026-02-22
- [x] Phase 7: Route Protection and Provenance (2/2 plans) — completed 2026-02-23
- [x] Phase 8: Integration Bug Fixes (1/1 plan) — completed 2026-02-23
- [x] Phase 9: Provenance and Redirect Micro-Fixes (1/1 plan) — completed 2026-02-23

**26 plans, ~354 tasks, 43/43 requirements satisfied**

</details>

<details>
<summary>✅ v2.0 Tighten Web UI (Phases 10-19) — SHIPPED 2026-03-01</summary>

- [x] Phase 10: Bug Fixes and Cleanup Architecture (3/3 plans) — completed 2026-02-23
- [x] Phase 11: Read-Only Object View (2/2 plans) — completed 2026-02-23
- [x] Phase 12: Sidebar and Navigation (2/2 plans) — completed 2026-02-23
- [x] Phase 13: Dark Mode and Visual Polish (4/4 plans) — completed 2026-02-24
- [x] Phase 14: Split Panes and Bottom Panel (3/3 plans) — completed 2026-02-24
- [x] Phase 15: Settings System and Node Type Icons (3/3 plans) — completed 2026-02-24
- [x] Phase 16: Event Log Explorer (3/3 plans) — completed 2026-02-24
- [x] Phase 17: LLM Connection Configuration (2/2 plans) — completed 2026-02-24
- [x] Phase 18: Tutorials and Documentation (2/2 plans) — completed 2026-02-25
- [x] Phase 19: Bug Fixes and E2E Test Hardening (3/3 plans) — completed 2026-02-27

**27 plans, 53 tasks, 46/46 requirements satisfied**

</details>

<details>
<summary>✅ v2.1 Architecture Decision Gate (Phases 20-22) — SHIPPED 2026-03-01</summary>

- [x] Phase 20: Architecture Decision Commit (5/5 plans) — completed 2026-02-28
- [x] Phase 21: Research Synthesis (1/1 plan) — completed 2026-02-28
- [x] Phase 22: Tech Debt Sprint (3/3 plans) — completed 2026-03-01

**9 plans, ~19 tasks, 9/9 requirements satisfied**

</details>

<details>
<summary>✅ v2.2 Data Discovery (Phases 23-28) — SHIPPED 2026-03-01</summary>

- [x] Phase 23: SPARQL Console (2/2 plans) — completed 2026-03-01
- [x] Phase 24: FTS Keyword Search (2/2 plans) — completed 2026-03-01
- [x] Phase 25: CSS Token Expansion (1/1 plan) — completed 2026-03-01
- [x] Phase 26: VFS MVP Read-Only (3/3 plans) — completed 2026-03-01
- [x] Phase 27: VFS Write + Auth (3/3 plans) — completed 2026-03-01
- [x] Phase 28: UI Polish + Integration Testing (3/3 plans) — completed 2026-03-01

**14 plans, 13/13 requirements satisfied**

</details>

<details>
<summary>✅ v2.3 Shell, Navigation & Views (Phases 29-34) — SHIPPED 2026-03-03</summary>

- [x] Phase 29: FTS Fuzzy Search (2/2 plans) — completed 2026-03-02
- [x] Phase 30: Dockview Phase A Migration (3/3 plans) — completed 2026-03-02
- [x] Phase 31: Object View Redesign (2/2 plans) — completed 2026-03-03
- [x] Phase 32: Carousel Views and View Bug Fixes (2/2 plans) — completed 2026-03-03
- [x] Phase 33: Named Layouts and VFS Settings Restore (2/2 plans) — completed 2026-03-03
- [x] Phase 34: E2E Test Coverage (2/2 plans) — completed 2026-03-03

**13 plans, 12/12 requirements satisfied**

</details>

### v2.4 Inference & Polish (In Progress)

**Milestone Goal:** Activate OWL 2 RL inference and SHACL-AF rules to deliver automatic bidirectional links and model-contributed derivations. Add a global lint dashboard for workspace-wide validation triage. Clear the backlog of tracked bugs and the edit form helptext TODO.

- [ ] **Phase 35: OWL 2 RL Inference** — Add `owlrl` dependency, materialize inverse/transitive triples into `urn:sempkm:inferred` named graph on every write
- [ ] **Phase 36: SHACL-AF Rules Support** — Enable `advanced=True` in pyshacl, add rules entrypoint to manifest, ship example rules in basic-pkm model
- [ ] **Phase 37: Global Lint Data Model & API** — Persist per-object, per-result validation detail; paginated API endpoints with filtering by severity, type, path
- [ ] **Phase 38: Global Lint Dashboard UI** — Filterable, sortable result table with severity badges, health indicator, auto-refresh
- [ ] **Phase 39: Edit Form Helptext + Bug Fix Batch** — `sempkm:editHelpText` SHACL annotation in edit forms; fix accent bar, card borders, Firefox Ctrl+K, tab bleed, dark chevrons, concept search
- [ ] **Phase 40: E2E Test Coverage for v2.4** — Playwright tests for inference, lint dashboard, helptext, and bug fix verifications

## Phase Details

### Phase 35: OWL 2 RL Inference
**Goal**: Users see automatic bidirectional links — adding a relationship in one direction automatically shows the inverse on the other object's detail page
**Depends on**: Nothing (v2.3 complete, clean start)
**Requirements**: INF-01
**Success Criteria** (what must be TRUE):
  1. User creates `ProjectA bpkm:hasParticipant PersonB`; PersonB's detail page automatically shows `participatesIn ProjectA` without manual entry
  2. Inferred triples are stored in a dedicated `urn:sempkm:inferred` named graph, separate from user-created data
  3. Inferred triples are visible in object views, relations panel, and graph visualization
  4. Deleting the source triple (hasParticipant) causes the inferred inverse to be removed on the next validation cycle
  5. Inference runs automatically on every write (integrated into the existing EventStore.commit() → AsyncValidationQueue pipeline)
**Plans**: TBD

### Phase 36: SHACL-AF Rules Support
**Goal**: Mental Models can declare SHACL rules that generate derived triples; basic-pkm ships example rules for inverse materialization and concept ancestry
**Depends on**: Phase 35 (inferred graph infrastructure must exist)
**Requirements**: INF-02
**Success Criteria** (what must be TRUE):
  1. pyshacl is called with `advanced=True` and processes `sh:rule` directives in shapes graphs
  2. Mental Model manifest supports an optional `rules` entrypoint pointing to a rules file (Turtle/JSON-LD)
  3. basic-pkm model ships at least one example SHACL rule (e.g., inverse participant rule via sh:SPARQLRule)
  4. Rule-derived triples are stored in the `urn:sempkm:inferred` named graph alongside OWL-derived triples
  5. Users see rule-derived data in object views without any manual action
**Plans**: TBD

### Phase 37: Global Lint Data Model & API
**Goal**: Per-object, per-result SHACL validation detail is stored in a queryable format with paginated API endpoints for listing results
**Depends on**: Phase 36 (inference must be stable before lint sees inferred data)
**Requirements**: LINT-01, LINT-02
**Success Criteria** (what must be TRUE):
  1. Individual ValidationResult records are stored with focus_node, severity, path, message, source_shape, constraint_component
  2. `GET /api/lint/results` returns paginated results with filtering by severity and object type
  3. Results update automatically after each EventStore.commit() via AsyncValidationQueue (no manual refresh)
  4. Per-object lint panel continues to work unchanged (backward compatible)
  5. Storage approach handles hundreds of objects without significant latency (< 2s for full-graph validation)
**Plans**: TBD

### Phase 38: Global Lint Dashboard UI
**Goal**: Users can see all validation results across all objects at a glance from a single filterable, sortable view
**Depends on**: Phase 37 (API endpoints must exist for the UI to consume)
**Requirements**: LINT-03, LINT-04, LINT-05, LINT-06, LINT-07
**Success Criteria** (what must be TRUE):
  1. Global lint view is accessible from sidebar or Command Palette as a dockview panel or dedicated page
  2. Summary bar shows total violations / warnings / infos with color-coded severity badges
  3. User can filter results by severity level, object type, and keyword search
  4. User can sort results by severity, object name, property path, or timestamp
  5. Status bar or sidebar shows a persistent health indicator badge (pass / N violations)
  6. Result list paginates or virtual-scrolls for large result sets (100+ results)
**Plans**: TBD

### Phase 39: Edit Form Helptext + Bug Fix Batch
**Goal**: Edit forms show contextual help text from SHACL annotations; all tracked CSS/UX bugs are fixed
**Depends on**: Phases 35-38 (inference and lint stable before cosmetic fixes)
**Requirements**: HELP-01, BUG-04, BUG-05, BUG-06, BUG-07, BUG-08, BUG-09
**Success Criteria** (what must be TRUE):
  1. SHACL shapes with `sempkm:editHelpText` render a collapsible markdown section below the corresponding field in edit forms
  2. basic-pkm model includes helptext annotations on at least 3 representative fields
  3. Tab accent bar color reflects the object's type (not uniform teal for all)
  4. Card view borders render correctly in both light and dark themes
  5. Firefox Ctrl+K opens ninja-keys (not Firefox address bar)
  6. Tab accent bar does not bleed into adjacent inactive tabs
  7. Panel chevron icons are visible in dark mode
  8. Concept search/linking works end-to-end (search finds concepts, links are created)
**Plans**: TBD

### Phase 40: E2E Test Coverage for v2.4
**Goal**: Playwright tests cover all v2.4 user-visible features
**Depends on**: Phases 35-39 complete (tests cover live features)
**Requirements**: TEST-05
**Success Criteria** (what must be TRUE):
  1. E2E tests verify bidirectional links appear after creating a relationship (inference working)
  2. E2E tests verify global lint dashboard loads, filters, and sorts results correctly
  3. E2E tests verify edit form helptext renders and collapses
  4. E2E tests verify each bug fix (accent bar, card borders, Ctrl+K, tab bleed, dark chevrons, concept search)
**Plans**: TBD

---

### Design Decision Gate

Before proceeding to the SPARQL Interface milestone, the following design decisions need resolution:

1. **SPARQL Interface direction** -- Extend Yasgui with custom plugins, or replace with standalone CodeMirror 6 + custom SPARQL mode? Affects scope of Phases 2-3.
2. **Obsidian Import Wizard UX** -- Approve the 6-step flow from [research](research/obsidian-import-wizard-ux.md)? LLM-assisted classification vs folder-based rules?
3. **Global Lint Phases C-D** -- Build fix guidance engine and click-to-edit triage in the next milestone, or defer further?

---

### (Future) SPARQL Interface

**Milestone Goal:** Transform the basic Yasgui SPARQL console into a first-class query interface with graph-aware permissions, intelligent autocomplete from loaded ontologies, visual IRI pills in the editor, server-side query history, saved/shared queries with parameterization, and named queries that serve as reusable views in the object browser.

**Depends on:** v2.4 complete. Ordered after Design Decision Gate to resolve SPARQL UI direction.

**Estimated Phases (sketch -- to be refined during milestone planning):**

1. **SPARQL Permissions and Policies** -- Graph-scoped query execution per role, admin-configurable execution policies (timeouts, result caps, UPDATE prohibition)
   - Requirements: SQ-01, SQ-02
   - Key risk: Performance impact of per-query graph scoping; may need query rewriting vs. RDF4J native graph access control

2. **SPARQL Autocomplete** -- Prefix, class, and property autocomplete in the query editor from prefix registry and installed Mental Model ontologies/SHACL shapes
   - Requirements: SQ-03, SQ-04, SQ-05
   - Key risk: Yasgui's CodeMirror integration may resist custom completers; may need to evaluate replacing Yasgui's editor with a standalone CodeMirror 6 instance + custom SPARQL mode
   - Research needed: Yasgui plugin architecture for autocompletion, CodeMirror 6 SPARQL language support landscape

3. **IRI Pills and Editor Enhancements** -- Visual pill rendering for IRIs and prefix declarations in the SPARQL editor; click-to-navigate and inline expand/collapse
   - Requirements: SQ-06, SQ-07
   - Key risk: CodeMirror decoration/widget API complexity; pills must not interfere with query parsing or copy-paste
   - Research needed: CodeMirror 6 decoration widgets, similar implementations in SPARQL editors (e.g., QLever UI, Wikidata Query Service)

4. **Server-Side Query History** -- Searchable, filterable query execution history persisted to the backend; cross-device access; execution metadata (duration, result count, timestamp)
   - Requirements: SQ-08, SQ-09
   - Key risk: Storage growth from query history; need retention policy and pagination
   - Likely approach: New SQLAlchemy model (QueryExecution) with user FK, query text, executed_at, duration_ms, result_count, status

5. **Saved Queries and Sharing** -- Named/bookmarked queries with descriptions, parameterization (template variables), sharing via links or published library
   - Requirements: SQ-10, SQ-11, SQ-12
   - Key risk: Template variable UX (how to define, prompt, and validate parameters); sharing permissions model
   - Likely approach: New SQLAlchemy model (SavedQuery) with owner, query text, name, description, params JSON, is_published flag

6. **Named Queries as Views** -- Promote saved queries to named views in the object browser; rendered via standard renderers (table, cards, graph); Mental Model manifest integration
   - Requirements: SQ-13, SQ-14, SQ-15
   - Key risk: Named query views must integrate with existing ViewSpecService and manifest view declaration format without breaking the current view pipeline
   - Depends on: Phase 5 (saved queries must exist), v2.3 Phase 32 (carousel view infrastructure)

### (Future) Obsidian Import & Lint Triage

**Milestone Goal:** Replace external Python import scripts with an in-app 6-step wizard for Obsidian vault import. Complete the global lint experience with fix guidance messages and a click-to-edit triage workflow.

**Depends on:** SPARQL Interface complete; v2.4 Global Lint Phases provide the dashboard infrastructure

**Estimated Phases (sketch):**

1. **Obsidian Vault Scanner** -- In-app vault upload, file tree parsing, frontmatter/tag/link extraction, summary statistics
2. **Type & Property Mapping** -- OpenRefine-style reconciliation UI for mapping vault content to Mental Model types and properties; fuzzy matching suggestions
3. **Relationship Mapping & Preview** -- Map Obsidian links to RDF relationships; SHACL validation preview of import results
4. **Import Execution** -- SSE-streamed batch import via Command API; progress tracking; rollback on failure
5. **Lint Fix Guidance Engine** -- Generate actionable fix messages from SHACL constraint metadata; template registry for top 10 constraint types; shape-author `sh:description` overrides
   - Requirements: LINT-08, LINT-09, LINT-10
6. **Lint Click-to-Edit Triage** -- Lint result rows open object in dockview pane and scroll to field; sequential triage workflow; keyboard navigation
   - Requirements: LINT-11, LINT-12, LINT-13

**Research:** [obsidian-import-wizard-ux.md](research/obsidian-import-wizard-ux.md)

---

### (Future) Identity: WebID + IndieAuth

**Milestone Goal:** Make SemPKM users verifiable identities on the web. Serve WebID profiles via content negotiation and provide IndieAuth login for interop with the IndieWeb ecosystem.

**Depends on:** Can start independently (no milestone dependencies)

**Estimated Phases (sketch):**

1. **WebID Profiles + rel="me"** -- Content negotiation on `/users/{username}` (Turtle for RDF clients, HTML for browsers); FOAF/schema.org properties; `rel="me"` links for fediverse verification
2. **IndieAuth Provider** -- Authorization endpoint, token endpoint, server metadata at `rel=indieauth-metadata`, mandatory PKCE; users can sign into IndieWeb services with their SemPKM URL

**Research:** [decentralized-identity.md](research/decentralized-identity.md) -- Phases A-B

---

### (Future) Collaboration & Federation

**Milestone Goal:** Enable multi-instance knowledge sharing with data sovereignty. SemPKM instances sync named graphs, notify each other of changes, and authenticate cross-instance users.

**Depends on:** Identity: WebID + IndieAuth (WebID provides the identity layer for federation)

**Estimated Phases (sketch):**

1. **RDF Patch Change Tracking** -- Patch log model, EventStore integration, patch replay, graph versioning
2. **Named Graph Sync API** -- HTTP sync endpoints for exchanging patches between instances; conflict detection
3. **Cross-Instance Notifications** -- LDN inbox endpoint, subscription model, Webmention for cross-references
4. **Federated Identity (WebID Auth)** -- WebID authentication for incoming sync/API requests; named graph ACL per WebID
5. **Collaboration UI** -- Settings for remote instances, graph sharing permissions, sync status indicators, incoming changes panel
6. **Real-Time Collaboration (Deferred)** -- CRDT-based concurrent editing; build only when ecosystem is ready (W3C CRDT for RDF CG, NextGraph, m-ld)

**Research:** [collaboration-architecture.md](research/collaboration-architecture.md)

---

### (Future) Identity: DIDs + Verifiable Credentials

**Milestone Goal:** Extend SemPKM's identity system with cryptographic identifiers and verifiable claims. Issue DID-based identifiers, sign knowledge graphs, and issue Verifiable Credentials for knowledge attestation.

**Depends on:** Collaboration & Federation (cross-instance sharing needs signed graphs)

**Estimated Phases (sketch):**

1. **did:web DID Documents + Graph Signing** -- Ed25519 key pairs per user, DID Documents at `/.well-known/did.json`, URDNA2015 canonicalization + SHA-256 + Ed25519 signatures, proofs as RDF
2. **Verifiable Credentials** -- VC 2.0 issuance using DID assertion keys, verification endpoint, authorship/membership/data-integrity credential types
3. **did:webvh Migration (Future)** -- Upgrade to did:webvh for verifiable history; cryptographic version chain; pre-rotation for key compromise recovery; build when DID Methods WG standardizes

**Research:** [decentralized-identity.md](research/decentralized-identity.md) -- Phases C-E

---

### Potential Ideas

Ideas with research completed but not yet committed to the roadmap. May be promoted to milestones in future planning sessions.

- **Web Components for Mental Models** -- Allow Mental Models to contribute custom frontend UI (Jinja2 macro bundles → light DOM Custom Elements → component SDK); model-served JS/CSS via nginx, CSP-restricted, sempkm-prefixed tag names — [Research](research/web-components-for-mental-models.md)
- **Low-Code UI Builder & Workflows** -- User-composed components tied to SemPKM actions (Notion + Airflow inspired); workflow orchestration for structured data collection sequences — [Research](research/future-milestones.md)
- **Full Theming System** -- User-selectable theme bundles (Dark+, Solarized, High Contrast); model-contributed themes via manifest; theme preview in settings
- **SHACL/OWL Inference Phases C-D** -- DASH vocabulary adoption for richer form metadata; RDF4J SchemaCachingRDFSInferencer for query-time RDFS inference — [Research](research/shacl-owl-inference.md)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Data Foundation | v1.0 | 4/4 | Complete | 2026-02-21 |
| 2. Semantic Services | v1.0 | 2/2 | Complete | 2026-02-21 |
| 3. Mental Model System | v1.0 | 3/3 | Complete | 2026-02-22 |
| 4. Admin Shell and Object Creation | v1.0 | 6/6 | Complete | 2026-02-22 |
| 5. Data Browsing and Visualization | v1.0 | 3/3 | Complete | 2026-02-22 |
| 6. User and Team Management | v1.0 | 4/4 | Complete | 2026-02-22 |
| 7. Route Protection and Provenance | v1.0 | 2/2 | Complete | 2026-02-23 |
| 8. Integration Bug Fixes | v1.0 | 1/1 | Complete | 2026-02-23 |
| 9. Provenance and Redirect Micro-Fixes | v1.0 | 1/1 | Complete | 2026-02-23 |
| 10. Bug Fixes and Cleanup Architecture | v2.0 | 3/3 | Complete | 2026-02-23 |
| 11. Read-Only Object View | v2.0 | 2/2 | Complete | 2026-02-23 |
| 12. Sidebar and Navigation | v2.0 | 2/2 | Complete | 2026-02-23 |
| 13. Dark Mode and Visual Polish | v2.0 | 4/4 | Complete | 2026-02-24 |
| 14. Split Panes and Bottom Panel | v2.0 | 3/3 | Complete | 2026-02-24 |
| 15. Settings System and Node Type Icons | v2.0 | 3/3 | Complete | 2026-02-24 |
| 16. Event Log Explorer | v2.0 | 3/3 | Complete | 2026-02-24 |
| 17. LLM Connection Configuration | v2.0 | 2/2 | Complete | 2026-02-24 |
| 18. Tutorials and Documentation | v2.0 | 2/2 | Complete | 2026-02-25 |
| 19. Bug Fixes and E2E Test Hardening | v2.0 | 3/3 | Complete | 2026-02-27 |
| 20. Architecture Decision Commit | v2.1 | 5/5 | Complete | 2026-02-28 |
| 21. Research Synthesis | v2.1 | 1/1 | Complete | 2026-02-28 |
| 22. Tech Debt Sprint | v2.1 | 3/3 | Complete | 2026-03-01 |
| 23. SPARQL Console | v2.2 | 2/2 | Complete | 2026-03-01 |
| 24. FTS Keyword Search | v2.2 | 2/2 | Complete | 2026-03-01 |
| 25. CSS Token Expansion | v2.2 | 1/1 | Complete | 2026-03-01 |
| 26. VFS MVP Read-Only | v2.2 | 3/3 | Complete | 2026-03-01 |
| 27. VFS Write + Auth | v2.2 | 3/3 | Complete | 2026-03-01 |
| 28. UI Polish + Integration Testing | v2.2 | 3/3 | Complete | 2026-03-01 |
| 29. FTS Fuzzy Search | v2.3 | 2/2 | Complete | 2026-03-02 |
| 30. Dockview Phase A Migration | v2.3 | 3/3 | Complete | 2026-03-02 |
| 31. Object View Redesign | v2.3 | 2/2 | Complete | 2026-03-03 |
| 32. Carousel Views and View Bug Fixes | v2.3 | 2/2 | Complete | 2026-03-03 |
| 33. Named Layouts and VFS Settings Restore | v2.3 | 2/2 | Complete | 2026-03-03 |
| 34. E2E Test Coverage | v2.3 | 2/2 | Complete | 2026-03-03 |
| 35. OWL 2 RL Inference | 3/4 | In Progress|  | - |
| 36. SHACL-AF Rules Support | v2.4 | 0/? | Planned | - |
| 37. Global Lint Data Model & API | v2.4 | 0/? | Planned | - |
| 38. Global Lint Dashboard UI | v2.4 | 0/? | Planned | - |
| 39. Edit Form Helptext + Bug Fix Batch | v2.4 | 0/? | Planned | - |
| 40. E2E Test Coverage for v2.4 | v2.4 | 0/? | Planned | - |

---
*Roadmap created: 2026-02-21*
*v1.0 archived: 2026-02-23*
*v2.0 archived: 2026-03-01*
*v2.1 archived: 2026-03-01*
*v2.2 roadmap expanded: 2026-02-28*
*v2.2 shipped: 2026-03-01 — full 4-panel drag-reorder enhancement landed post-ship on feature/mental-model-dashboard*
*v2.2 post-ship polish: 2026-03-01 — event log user names fix, tabular grid, Diff/Undo button colors, SPARQL Console to Admin nav, Event Console page (/events), diff arrow, relations panel collapsible rollup*
*v2.2 archived: 2026-03-01*
*v2.3 roadmap created: 2026-03-01 — Phases 29-34 defined*
*Future SPARQL Interface milestone documented: 2026-03-03 — 6 phase sketches, 15 requirements (SQ-01 through SQ-15)*
*Future Global Lint Status milestone documented: 2026-03-03 — 4 phase sketches, 13 requirements (LINT-01 through LINT-13)*
*Roadmap reordered: 2026-03-03 — v2.4 defined, milestones resequenced for agentic execution, Identity split into two milestones, Web Components moved to Potential Ideas*
*v2.3 shipped: 2026-03-03 — 13 plans, 12 requirements (FTS-04, DOCK-01/02, VIEW-01/02, BUG-01/02/03, TEST-01/02/03/04)*
*v2.4 roadmap created: 2026-03-03 — Phases 35-40 defined, 17 requirements (INF-01/02, LINT-01-07, HELP-01, BUG-04-09, TEST-05)*
