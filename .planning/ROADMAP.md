# Roadmap: SemPKM

## Milestones

- ✅ **v1.0 MVP** — Phases 1-9 (shipped 2026-02-23) — [Full details](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 Tighten Web UI** — Phases 10-19 (shipped 2026-03-01) — [Full details](milestones/v2.0-ROADMAP.md)
- ✅ **v2.1 Architecture Decision Gate** — Phases 20-22 (shipped 2026-03-01) — [Full details](milestones/v2.1-ROADMAP.md)
- 🚧 **v2.2 Data Discovery** — Phases 23-28 (in progress)

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

### 🚧 v2.2 Data Discovery (Phases 23-28)

**Milestone Goal:** Implement committed architectural decisions from v2.1 — SPARQL console, FTS keyword search, WebDAV VFS, CSS token expansion for v2.3 prep — then close with UI polish and integration E2E testing.

- [x] **Phase 23: SPARQL Console** — Yasgui CDN embed with custom YASR renderer for SemPKM object links and localStorage persistence (completed 2026-03-01)
- [x] **Phase 24: FTS Keyword Search** — RDF4J LuceneSail indexing, SPARQL FTS predicates, Ctrl+K command palette integration (completed 2026-03-01)
- [x] **Phase 25: CSS Token Expansion** — Two-tier primitive/semantic token architecture, expanding from ~40 to ~91 tokens (completed 2026-03-01)
- [ ] **Phase 26: VFS MVP Read-Only** — wsgidav WebDAV mount via a2wsgi bridge, SyncTriplestoreClient, Markdown+frontmatter file rendering
- [ ] **Phase 27: VFS Write + Auth** — Write path diff engine, API token Basic auth, MountSpec settings UI
- [ ] **Phase 28: UI Polish + Integration Testing** — Expander icon fixes, sidebar panel rearrangement, contextual view indicators, Playwright E2E suites

## Phase Details

### Phase 23: SPARQL Console
**Goal**: Users can execute SPARQL queries against their knowledge base through an embedded Yasgui interface with SemPKM-aware result rendering
**Depends on**: Nothing (zero backend changes required — existing `/api/sparql` endpoint is Yasgui-compatible)
**Requirements**: SPARQL-01, SPARQL-02, SPARQL-03
**Success Criteria** (what must be TRUE):
  1. User can open the SPARQL Console from the workspace and execute arbitrary SPARQL queries against the live triplestore
  2. Query results table renders SemPKM object IRIs as clickable links that open the object in the browser
  3. User's query tabs and history survive a full browser session close and reopen (localStorage key: `sempkm-sparql`)
  4. SPARQL Console is accessible to any authenticated user (not owner-only), with the existing session cookie handling auth transparently
  5. Dark mode overrides apply to the Yasgui UI so the console matches the workspace theme
**Plans**: TBD

Plans:
- [ ] 23-01: Yasgui CDN embed, SPARQL Console route, base template
- [ ] 23-02: Custom YASR cell renderer for SemPKM IRIs, dark mode overrides

### Phase 24: FTS Keyword Search
**Goal**: Users can search their entire knowledge base by keyword with results showing object type, label, and matching text snippet, integrated into the Ctrl+K command palette
**Depends on**: LuceneSail JAR verification and Turtle config validation (infrastructure prerequisites, not phase dependencies)
**Requirements**: FTS-01, FTS-02, FTS-03
**Success Criteria** (what must be TRUE):
  1. User can type a keyword into the Ctrl+K command palette and see matching objects from across the knowledge base
  2. Each search result shows the object type icon, object label, and the matching text snippet that triggered the result
  3. Searching by a term that appears only in a property value (not the object label) still returns the object in results
  4. Search results are scoped to the current state graph (`urn:sempkm:current`) — event graph contents do not appear in results
  5. A dedicated `GET /api/search` endpoint returns structured JSON results usable by any consumer (palette, future UIs)
**Plans**: 2 plans

Plans:
- [ ] 24-01-PLAN.md — LuceneSail JAR verification, sempkm-repo.ttl + Docker volume, SearchService
- [ ] 24-02-PLAN.md — GET /api/search endpoint, Ctrl+K palette integration, result rendering

### Phase 25: CSS Token Expansion
**Goal**: The CSS token system is expanded from ~40 to ~91 tokens using a two-tier primitive/semantic architecture, replacing all hardcoded values in workspace/style/forms/views CSS — enabling consistent theming for new surfaces in v2.2 and the Dockview migration bridge in v2.3
**Depends on**: Nothing (independent prerequisite for v2.3 dockview work)
**Requirements**: None (infrastructure preparatory phase — enables v2.3 CSS-01/DOCK-01)
**Success Criteria** (what must be TRUE):
  1. `theme.css` contains ~91 CSS custom property declarations organized as primitive tokens (`--_*`) and semantic tokens (`--color-*`, `--tab-*`, `--panel-*`, `--spacing-*`, `--font-size-*`, `--sidebar-*`, `--graph-*`)
  2. Dark mode overrides only touch semantic tokens — primitive token values never change between themes
  3. All hardcoded color, spacing, and typography values in `workspace.css`, `style.css`, `forms.css`, and `views.css` are replaced with token references (no behavior changes, pure refactor)
  4. A `dockview-sempkm-bridge.css` pattern file maps `--dv-*` Dockview variables to SemPKM semantic tokens, ready for the v2.3 Phase A migration
**Plans**: TBD

Plans:
- [ ] 25-01: Add new token definitions to theme.css, audit and replace hardcoded values in CSS files, create dockview bridge pattern

### Phase 26: VFS MVP Read-Only
**Goal**: Users can mount SemPKM objects as files via a WebDAV endpoint, browsing and reading object bodies as Markdown files with SHACL-derived frontmatter using any WebDAV client (macOS Finder, Windows Explorer, Linux Nautilus)
**Depends on**: Nothing at code level (three new Python packages and SyncTriplestoreClient are created within this phase)
**Requirements**: VFS-01, VFS-02
**Success Criteria** (what must be TRUE):
  1. User can connect a WebDAV client (e.g., macOS Finder "Connect to Server") to the `/dav/` endpoint and see a directory of objects
  2. Each object appears as a `.md` file whose body is the object's body content and whose frontmatter contains SHACL-derived properties (type, IRI, title, and key predicates)
  3. Opening a file in a text editor via the WebDAV mount shows the current state of the object — not stale or cached data
  4. The WebDAV mount is read-only — no writes, no DELETE, no MOVE operations succeed
**Plans**: TBD

Plans:
- [ ] 26-01: Python packages, SyncTriplestoreClient, nginx WebDAV proxy block
- [ ] 26-02: SemPKMDAVProvider, MountCollection (flat strategy), ResourceFile (Markdown+frontmatter rendering)
- [ ] 26-03: wsgidav mount in main.py, TTL cache for directory listings, end-to-end mount validation

### Phase 27: VFS Write + Auth
**Goal**: The WebDAV VFS supports API token authentication (enabling native OS WebDAV clients to authenticate without browser sessions) and the write path allows editing object bodies through the WebDAV mount
**Depends on**: Phase 26 (read-only VFS validated)
**Requirements**: VFS-03
**Success Criteria** (what must be TRUE):
  1. User can generate a revocable API token from the Settings page and use it as the Basic auth password with their SemPKM username to authenticate a WebDAV client
  2. Revoking a token from Settings immediately invalidates any active WebDAV sessions using that token
  3. User can edit a `.md` file body through the WebDAV mount and the change is reflected in the SemPKM object browser (write propagates through the event store)
  4. Mount configuration (endpoint URL, token instructions) is visible and actionable in the Settings page under a "Virtual Filesystem" section
**Plans**: TBD

Plans:
- [ ] 27-01: API token data model, generation endpoint, custom wsgidav HTTPAuthenticator
- [ ] 27-02: Write path (PATCH body via DAV PUT), ETag concurrency, frontmatter round-trip
- [ ] 27-03: Settings UI — VFS mount config, token generation/revocation UI

### Phase 28: UI Polish + Integration Testing
**Goal**: Visual rough edges from prior phases are fixed, sidebar panels can be rearranged by the user, object-contextual panels are visually distinguished from global views, and all v2.2 features have dedicated Playwright E2E integration test files
**Depends on**: Phases 23, 24, 26 (features must exist to be tested)
**Requirements**: POLSH-01, POLSH-02, POLSH-03, POLSH-04
**Success Criteria** (what must be TRUE):
  1. Sidebar tree expander/collapse icons are visible and correctly styled in both light and dark themes (no invisible-on-background icon state)
  2. User can drag or swap sidebar panels between the left and right sidebar in the object browser — the new position persists across page reloads
  3. Panels displaying data scoped to the currently open object show a visual indicator (e.g., badge, border, or label) distinguishing them from global/unscoped panels
  4. Playwright test file `e2e/tests/sparql-console.spec.ts` covers Yasgui load, query execution, and IRI link rendering
  5. Playwright test file `e2e/tests/fts-search.spec.ts` covers keyword search via Ctrl+K, result display, and snippet visibility
  6. Playwright test file `e2e/tests/vfs-webdav.spec.ts` covers WebDAV endpoint availability, directory listing, and file content correctness
**Plans**: TBD

Plans:
- [ ] 28-01: Expander icon theme fixes, sidebar panel rearrangement (lightweight swap, no dockview)
- [ ] 28-02: Object-contextual view indicator, E2E test files for SPARQL, FTS, and VFS

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
| 23. SPARQL Console | 2/2 | Complete    | 2026-03-01 | - |
| 24. FTS Keyword Search | 2/2 | Complete   | 2026-03-01 | - |
| 25. CSS Token Expansion | 1/1 | Complete    | 2026-03-01 | - |
| 26. VFS MVP Read-Only | 2/3 | In Progress|  | - |
| 27. VFS Write + Auth | v2.2 | 0/? | Not started | - |
| 28. UI Polish + Integration Testing | v2.2 | 0/? | Not started | - |

---
*Roadmap created: 2026-02-21*
*v1.0 archived: 2026-02-23*
*v2.0 archived: 2026-03-01*
*v2.1 archived: 2026-03-01*
*v2.2 roadmap expanded: 2026-02-28*
