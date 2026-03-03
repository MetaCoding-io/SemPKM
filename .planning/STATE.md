---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Shell, Navigation & Views
status: unknown
last_updated: "2026-03-03T19:23:44.488Z"
progress:
  total_phases: 15
  completed_phases: 15
  total_plans: 38
  completed_plans: 38
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.
**Current focus:** v2.3 Shell, Navigation & Views — Phase 33 in progress

## Current Position

Phase: 34 of 34 (E2E Test Coverage) — In Progress
Current Plan: 1 of 2
Status: Completed 34-01 — SPARQL/VFS/FTS test fixes with zero test.skip()
Last activity: 2026-03-03 - Completed 34-01: E2E test coverage fixes

Progress: [█████████░] 95% (6.5/7 phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 11 (v2.3)
- Average duration: 3.5 min
- Total execution time: 39 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 29-fts-fuzzy-search | 2 | 3 min | 1.5 min |
| 30-dockview-phase-a-migration | 3 | 15 min | 5.0 min |
| 31-object-view-redesign | 2 | 11 min | 5.5 min |
| 32-carousel-views-and-view-bug-fixes | 2 | 6 min | 3.0 min |
| 33-named-layouts-and-vfs-settings-restore | 2 | 4 min | 2.0 min |
| 34-e2e-test-coverage | 1 | 4 min | 4.0 min |

*Updated after each plan completion*

## Accumulated Context

### Key Decisions

Full decision log in PROJECT.md Key Decisions table.

- DEC-04: dockview-core 4.11.0 replaces Split.js for editor-pane area (Phase A only); CSS bridge file already in place from v2.2
- Research: LuceneSail `term~1` fuzzy syntax confirmed HIGH confidence; 5-char length threshold to avoid short-token noise
- 29-01: 5-char threshold for fuzzy expansion (tokens <5 chars stay exact to avoid dictionary-scan noise)
- 29-01: ~1 edit distance only (not ~2); fuzzyPrefixLength=2 in TTL for index performance (requires volume reset)
- 29-01: fuzzy field echoed in API response body so clients can confirm mode was applied
- 29-02: Toggle ID 'search-fuzzy-toggle' (not 'fts-' prefix) so change listener filter never removes the toggle
- 29-02: sempkm_fts_fuzzy localStorage key follows existing sempkm_ namespace convention
- 30-01: DockviewComponent CDN global resolved via DockviewCore.DockviewComponent || window.DockviewComponent
- 30-01: WorkspaceLayout retained as thin metadata sidecar; renderGroupTabBar is no-op stub
- 30-01: New sessionStorage key sempkm_workspace_layout_dv (old key cleared on init)
- 30-01: Bridge CSS loaded BEFORE dockview.css for token override precedence
- 30-02: toggleObjectMode dirty check reads _tabMeta[objectIri].dirty (not layout.groups iteration)
- 30-02: objectSaved uses panel.api.setTitle() for live dockview tab title updates
- 30-02: Ctrl+1-4 group focus uses dv.groups[idx].focus() (dockview native)
- 30-03: Bridge CSS must load AFTER dockview.css (corrects 30-01 decision — overrides need later load)
- 30-03: CDN global is window['dockview-core'] (hyphenated), not DockviewCore
- 30-03: createComponent must return { element, init() } — element property required by IContentRenderer
- 31-01: CSS grid-template-rows 0fr/1fr for smooth properties slide animation (no max-height hack)
- 31-01: Properties badge in toolbar controls both read+edit face collapse simultaneously
- 31-01: sempkm_props_collapsed localStorage key stores per-IRI collapse preference as JSON object
- 31-01: Default: collapsed when body exists, expanded when no body content
- 31-02: expandProperties must use waitForFunction (not waitForSelector) when both read/edit face elements coexist behind 3D flip
- 31-02: showTypePicker creates empty dockview panel when no active panel exists (empty workspace Ctrl+N)
- 32-01: All view htmx targets use closest .group-editor-area (not #editor-area) for dockview compatibility
- 32-01: Card accordion collapse state is ephemeral (no localStorage persistence); all groups expanded by default
- 32-01: "Ungrouped" replaces "(No value)" and sorts last via tuple key (x[0] == "Ungrouped", x[0])
- 32-02: Two-container pattern eliminates _carouselSwitching flag -- carousel bar outside .carousel-view-body swap target
- 32-02: sempkm_carousel_view localStorage key maps type_iri to spec_iri for per-type view persistence
- 32-02: outerHTML swap with select: '.carousel-view-body' extracts only view body from response
- 33-01: sempkm_layout_current key replaces sempkm_workspace_layout_dv (localStorage, not sessionStorage)
- 33-01: sempkm_layouts registry stores named layouts as { name: { layout, savedAt } } in localStorage
- 33-01: beforeunload handler as belt-and-suspenders alongside onDidLayoutChange for layout persistence
- 33-01: SessionStorage migration reads old key once on init, copies to localStorage, clears sessionStorage
- 33-02: Save As uses ninja-keys shadowRoot input for inline naming (no prompt/modal per CONTEXT.md locked decision)
- 33-02: Layout commands in dedicated 'Layout' section of command palette
- 33-02: User popover Layouts item opens palette directly to layout-restore parent submenu
- 33-02: Toast notifications auto-dismiss after 3s (5s for partial restore with skipped items)
- 34-01: VFS WebDAV tests use vfsBasicAuth custom fixture (API token creation/cleanup per test)
- 34-01: PROPFIND discovery for .md file paths instead of hardcoded URL-encoded titles
- 34-01: wsgidav uses ns0: XML namespace prefix (not D:) and /basic-pkm/ model-prefixed paths

### Pending Todos

1. Add edit form helptext property to SHACL types (ui) — carried from v2.0

### Known Tech Debt

- Cookie secure=False (local dev only — production config deferred)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- empty_shapes_loader dead code
- E2E tests for SPARQL/FTS/VFS use test.skip() graceful degradation — resolved in Phase 34

### Blockers/Concerns

- Carousel bar + 3D flip toggle visual coexistence in object view header unresolved — prototype before committing VIEW-02 implementation (Phase 32)
- Named layout user preference storage in triplestore is a first-use pattern — validate SPARQL UPDATE design before LayoutService (Phase 33)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 16 | Document future milestone: SPARQL interface with permissions, autocomplete, UI pills, query history, saved queries, named queries with views | 2026-03-03 | 2e8e2f6 | [16-document-future-milestone-sparql-interfa](./quick/16-document-future-milestone-sparql-interfa/) |
| 17 | Save collaboration architecture research to planning docs with source links and reference from future milestone | 2026-03-03 | 833da8a | [17-save-collaboration-architecture-research](./quick/17-save-collaboration-architecture-research/) |
| 18 | Research Web Components for Mental Model UI contribution (htmx interop, security model, manifest design, phased roadmap) | 2026-03-03 | dcdad2c | [18-research-web-components-for-mental-model](./quick/18-research-web-components-for-mental-model/) |
| 19 | Research SHACL and OWL logical inference for mental models (owlrl, SHACL-AF rules, DASH, 4-phase roadmap) | 2026-03-03 | fd6bd98 | [19-research-shacl-and-owl-logical-inference](./quick/19-research-shacl-and-owl-logical-inference/) |
| 20 | Save decentralized identity research and add Identity & Authentication future milestone | 2026-03-03 | d63c2e0 | [20-save-decentralized-identity-research-and](./quick/20-save-decentralized-identity-research-and/) |
| 21 | Design interactive Obsidian import wizard UX flow (OpenRefine-style reconciliation, fuzzy matching, htmx wizard) | 2026-03-03 | dbbaeb4 | [21-research-ux-ui-flow-for-interactive-obsi](./quick/21-research-ux-ui-flow-for-interactive-obsi/) |
| 22 | Plan future milestone for Global Lint Status (13 LINT-* requirements, 4-phase sketch, fix guidance engine) | 2026-03-03 | e077d81 | [22-plan-future-milestone-for-global-lint-st](./quick/22-plan-future-milestone-for-global-lint-st/) |

## Session Continuity

Last session: 2026-03-03
Stopped at: Completed 34-01-PLAN.md (E2E test coverage fixes)
Resume file: Phase 34 in progress. Next: 34-02
