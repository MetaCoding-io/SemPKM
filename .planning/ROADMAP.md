# Roadmap: SemPKM

## Milestones

- ✅ **v1.0 MVP** — Phases 1-9 (shipped 2026-02-23) — [Full details](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 Tighten Web UI** — Phases 10-19 (shipped 2026-03-01) — [Full details](milestones/v2.0-ROADMAP.md)
- ✅ **v2.1 Architecture Decision Gate** — Phases 20-22 (shipped 2026-03-01) — [Full details](milestones/v2.1-ROADMAP.md) — [Archive](milestones/v2.1-REQUIREMENTS.md)
- ✅ **v2.2 Data Discovery** — Phases 23-28 (shipped 2026-03-01) — [Full details](milestones/v2.2-ROADMAP.md)
- 🚧 **v2.3 Shell, Navigation & Views** — Phases 29-34 (in progress)
- (future) **SPARQL Interface** -- Rich SPARQL query experience with permissions, autocomplete, pills, history, saved queries, and named query views
- (future) **Collaboration & Federation** -- Multi-instance sync via RDF Patch, cross-instance notifications (LDN), federated identity (WebID), and future CRDT-based real-time co-editing — [Research](research/collaboration-architecture.md)
- (future) **Identity & Authentication** -- WebID profiles, IndieAuth provider, did:web DIDs, RDF graph signing, Verifiable Credentials for knowledge attestation — [Research](research/decentralized-identity.md)
- (future) **Global Lint Status** -- Workspace-wide SHACL validation dashboard with filtering, fix guidance, and click-to-edit inline triage workflow
- (future) **SHACL/OWL Inference** -- OWL 2 RL inference via owlrl for automatic bidirectional links (inverseOf), RDFS entailments, SHACL-AF rules for model-contributed derivations, DASH vocabulary for richer form metadata — [Research](research/shacl-owl-inference.md)
- (future) **Obsidian Import Wizard** -- In-app 6-step wizard replacing external Python scripts: vault scan, OpenRefine-style type mapping, property mapping with fuzzy matching, relationship mapping, preview with SHACL validation, SSE-streamed import execution — [Research](research/obsidian-import-wizard-ux.md)
- (future) **Web Components for Mental Models** -- Allow Mental Models to contribute custom frontend UI (Jinja2 macro bundles → light DOM Custom Elements → component SDK); model-served JS/CSS via nginx, CSP-restricted, sempkm-prefixed tag names — [Research](research/web-components-for-mental-models.md)

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

### 🚧 v2.3 Shell, Navigation & Views (In Progress)

**Milestone Goal:** Complete dockview Phase A migration (replacing Split.js editor-pane area), redesign the object view to be markdown-first with manifest-driven carousel views, add named workspace layouts, improve FTS with fuzzy search, and close v2.2 bugs.

- [x] **Phase 29: FTS Fuzzy Search** — Typo-tolerant search via LuceneSail `term~1` operator with user-controlled toggle in Ctrl+K palette (backend complete 2026-03-02; frontend 29-02 pending)
- [x] **Phase 30: Dockview Phase A Migration** — Replace Split.js editor-pane area with dockview-core panels; remove old HTML5 drag system (complete 2026-03-02)
- [x] **Phase 31: Object View Redesign** — Markdown-first object view with properties collapsed by default and single-click reveal (complete 2026-03-03)
- [x] **Phase 32: Carousel Views and View Bug Fixes** — Manifest-declared per-type view tab bar, concept cards group-by fix, broken view switch buttons removed (completed 2026-03-03)
- [ ] **Phase 33: Named Layouts and VFS Settings Restore** — User-named workspace layout save/restore via Command Palette; VFS Settings UI restored
- [ ] **Phase 34: E2E Test Coverage** — Remove all test.skip() from SPARQL/FTS/VFS suites; add v2.3 feature coverage

## Phase Details

### Phase 29: FTS Fuzzy Search
**Goal**: Users can find objects despite typos using fuzzy matching toggled from the Ctrl+K palette
**Depends on**: Nothing (fully independent)
**Requirements**: FTS-04
**Success Criteria** (what must be TRUE):
  1. User types a misspelled query (e.g. "knowlege") in Ctrl+K palette and sees results for the correct object
  2. User can toggle fuzzy mode on/off from within the Ctrl+K palette; the toggle state persists across sessions via localStorage
  3. Tokens shorter than 5 characters are matched exactly even when fuzzy mode is on (no noise from short-token approximate expansion)
  4. Multi-word queries fuzzy-match each qualifying token independently (e.g. "alice smth" finds "Alice Smith")
**Plans**: 2 plans

Plans:
- [x] 29-01-PLAN.md — Backend: _normalize_query() in SearchService, fuzzy param on /api/search, fuzzyPrefixLength TTL config (complete 2026-03-02)
- [ ] 29-02-PLAN.md — Frontend: fuzzy toggle command in ninja-keys Ctrl+K palette with localStorage persistence

### Phase 30: Dockview Phase A Migration
**Goal**: Users manage object tabs through dockview-core panels with native drag-to-reorder and group splitting; old HTML5 drag system is gone
**Depends on**: Phase 29 (parallel is fine; DOCK-01 is sequenced after to isolate risk)
**Requirements**: DOCK-01
**Success Criteria** (what must be TRUE):
  1. User can open multiple object tabs and drag them to reorder or split into side-by-side groups using dockview native drag handles
  2. Workspace tab layout (group geometry) is automatically saved and restored after a browser reload
  3. Object tabs opened inside dockview panels continue to fire `sempkm:tab-activated` and `sempkm:tabs-empty` events with the same payload shape as before
  4. CodeMirror and Cytoscape visualizations render correctly when their containing panel is shown after being hidden (no zero-size blank panels)
  5. htmx attributes on content loaded inside dockview panels remain active (forms submit, relations load, linting works)
**Plans**: 3 plans

Plans:
- [x] 30-01-PLAN.md — Core dockview init: rewrite workspace-layout.js with DockviewComponent, update workspace.html CDN, activate bridge.css (complete 2026-03-02)
- [x] 30-02-PLAN.md — Caller updates: workspace.js tab functions + object_tab.html typeIcon push to dockview API (complete 2026-03-02)
- [x] 30-03-PLAN.md — CSS cleanup: remove old editor-group/drag rules from workspace.css + human verification checkpoint (complete 2026-03-02)

### Phase 31: Object View Redesign
**Goal**: Users see the object body (Markdown) by default with properties hidden; a single click reveals or collapses properties; preference is remembered per object
**Depends on**: Phase 30 (visual coexistence with dockview panels validated before committing final layout)
**Requirements**: VIEW-01
**Success Criteria** (what must be TRUE):
  1. Opening any object tab shows the rendered Markdown body immediately without properties visible
  2. User clicks a "N properties" toggle badge and the full property list expands inline without a page reload
  3. User collapses properties, reloads the page, and reopens the same object — properties remain collapsed (preference stored per object IRI)
  4. The existing CSS 3D flip to edit mode is unaffected and still reachable from the view header
**Plans**: 2 plans

Plans:
- [x] 31-01-PLAN.md — Template restructuring (body-first layout, properties badge, collapsible sections, CSS transitions, localStorage persistence, Split.js removal) (complete 2026-03-03)
- [x] 31-02-PLAN.md — E2E verification and test fixes (expandProperties dual-face fix, showTypePicker empty workspace fix) (complete 2026-03-03)

### Phase 32: Carousel Views and View Bug Fixes
**Goal**: Object types with multiple manifest-declared views expose a tab bar; users switch views instantly; concept cards group-by works; broken view switch buttons are gone
**Depends on**: Phase 30 (carousel bar wires into dockview panels), Phase 31 (tab bar must coexist with new object view header)
**Requirements**: VIEW-02, BUG-01, BUG-03
**Success Criteria** (what must be TRUE):
  1. For an object type with multiple views declared in the manifest, a tab bar appears above the view body listing each view by name; clicking a tab switches the view instantly
  2. The active carousel view tab persists per type IRI across sessions (returning to the type shows the same view the user last selected)
  3. Concept cards view correctly groups objects by the configured group-by predicate without breaking layout or mixing groups
  4. The broken graph/card/table view switch buttons are absent from the object view; the carousel tab bar is the only view-switching affordance
**Plans**: TBD

### Phase 33: Named Layouts and VFS Settings Restore
**Goal**: Users can save, restore, and delete named workspace layouts from the Command Palette; VFS mount configuration is accessible from the Settings page
**Depends on**: Phase 30 (named layouts require dockview `toJSON()` to be live)
**Requirements**: DOCK-02, BUG-02
**Success Criteria** (what must be TRUE):
  1. User opens the Command Palette, invokes "Layout: Save as...", names the layout, and it appears as a restorable option in future palette sessions
  2. User restores a named layout and the editor groups and panel geometry match what was saved
  3. User deletes a named layout from the Command Palette and it no longer appears
  4. Named layouts survive browser reload (persisted to localStorage and/or backend API)
  5. User navigates to Settings and can see, generate, and revoke VFS API tokens from a working Settings UI
**Plans**: TBD

### Phase 34: E2E Test Coverage
**Goal**: The full Playwright test suite passes against the live stack with no test.skip() calls; v2.3 features have coverage
**Depends on**: Phases 29-33 complete (tests cover live features)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. All SPARQL console E2E tests run and pass against the live stack without any `test.skip()` wrapper
  2. All FTS keyword search E2E tests (including fuzzy toggle behavior) run and pass against the live stack without any `test.skip()` wrapper
  3. All WebDAV VFS E2E tests run and pass against the live stack without any `test.skip()` wrapper
  4. New Playwright tests cover dockview panel management, carousel view switching, fuzzy FTS toggle, and named layout save/restore
**Plans**: TBD

### (Future) SPARQL Interface

**Milestone Goal:** Transform the basic Yasgui SPARQL console into a first-class query interface with graph-aware permissions, intelligent autocomplete from loaded ontologies, visual IRI pills in the editor, server-side query history, saved/shared queries with parameterization, and named queries that serve as reusable views in the object browser.

**Depends on:** v2.3 complete (dockview panels, object view redesign, named layouts provide the shell infrastructure)

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

### (Future) Global Lint Status

**Milestone Goal:** Provide a global view of SHACL validation health across the entire knowledge base. Users can see all violations, warnings, and infos at a glance, filter and search results, read actionable fix guidance for each issue, and click directly into the offending object's edit form to resolve issues in a continuous triage workflow.

**Depends on:** v2.3 complete (dockview panels provide the panel infrastructure for the lint view; object view redesign provides the field-focus jump target)

**Builds on existing infrastructure:**
- `ValidationService` + `AsyncValidationQueue` (backend/app/services/validation.py, backend/app/validation/queue.py) -- already runs pyshacl after every commit
- `ValidationReport` / `ValidationResult` dataclasses (backend/app/validation/report.py) -- already parse per-result severity, focus_node, path, message, source_shape, constraint_component
- `lint_panel.html` -- existing per-object lint tab with jumpToField() click handler
- `/api/validation/latest` endpoint -- existing polling endpoint for latest report summary
- SHACL shapes in Mental Model packages (orig_specs/models/*/shapes.ttl)

**Estimated Phases (sketch -- to be refined during milestone planning):**

1. **Global Validation API and Data Model** -- Extend the validation pipeline to store per-object, per-result detail (not just aggregate counts) in a queryable format; new API endpoints for listing all results with pagination
   - Requirements: LINT-01, LINT-02
   - Key risk: Performance of full-graph SHACL validation at scale (hundreds of objects); may need incremental validation (only re-validate objects touched by the commit) rather than full re-validation
   - Research needed: pyshacl incremental validation capabilities; whether to store individual ValidationResult triples in the triplestore or use SQLAlchemy for fast querying
   - Likely approach: Store individual ValidationResult records in a `urn:sempkm:lint-results` named graph with focus_node, severity, path, message, source_shape; or use a new SQLAlchemy model for SQL-level filtering/pagination

2. **Global Lint Dashboard UI** -- Dockview panel (or dedicated page accessible from sidebar/Command Palette) showing a filterable, searchable list of all validation results across all objects with summary counts
   - Requirements: LINT-03, LINT-04, LINT-05, LINT-06, LINT-07
   - Key risk: Rendering performance for large result sets; need virtual scrolling or pagination for 100+ results
   - Likely approach: htmx-driven table with server-side filtering/sorting; severity filter toggles, type dropdown from ModelRegistry, keyword search input; summary badges in status bar or sidebar
   - Design note: Follow existing SemPKM patterns (htmx partials, Lucide icons, CSS custom properties) -- not a JS framework component

3. **Fix Guidance Engine** -- Generate human-readable, actionable fix messages from SHACL constraint metadata; built-in templates for common constraint types; Mental Model shape authors can provide custom sh:description text
   - Requirements: LINT-08, LINT-09, LINT-10
   - Key risk: Message quality for complex constraints (sh:or, sh:qualifiedValueShape, custom SPARQL constraints); 80/20 rule -- handle the 10 most common constraint components well, fallback gracefully for exotic ones
   - Research needed: Full inventory of SHACL constraint components used in existing shapes; whether sh:description and sh:name are consistently populated in community SHACL shape sets
   - Likely approach: FixGuidanceService with a template registry mapping sh:sourceConstraintComponent URIs to message templates; templates use shape metadata (sh:name, sh:description, sh:minCount value, sh:datatype value) as interpolation variables

4. **Click-to-Edit Inline Triage Workflow** -- Each lint result row is a clickable link that opens (or focuses) the object in a dockview pane and scrolls to the relevant field; after save, lint view reflects the updated state
   - Requirements: LINT-11, LINT-12, LINT-13
   - Key risk: Field-focus accuracy (property path to DOM element mapping); the existing jumpToField() function uses property path matching which may need hardening for nested shapes or multi-valued fields
   - Depends on: Phase 1 (results data), Phase 2 (lint dashboard UI), Phase 3 (fix guidance)
   - Likely approach: Extend existing jumpToField() into a workspace-level function that can open-then-focus; use sempkm:tab-activated event to trigger scroll-to-field after panel loads; lint panel listens for save events to refresh its result list

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
| 32. Carousel Views and View Bug Fixes | 2/2 | Complete    | 2026-03-03 | - |
| 33. Named Layouts and VFS Settings Restore | v2.3 | 0/? | Not started | - |
| 34. E2E Test Coverage | v2.3 | 0/? | Not started | - |

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
