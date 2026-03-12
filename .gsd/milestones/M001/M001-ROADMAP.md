# M001: Migration

**Vision:** SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences.

## Success Criteria


## Slices

- [x] **S01: Core Data Foundation — completed 2026 02 21** `risk:medium` `depends:[]`
  > After this: unit tests prove Core Data Foundation — completed 2026-02-21 works
- [x] **S02: Semantic Services — completed 2026 02 21** `risk:medium` `depends:[S01]`
  > After this: unit tests prove Semantic Services — completed 2026-02-21 works
- [x] **S03: Mental Model System — completed 2026 02 22** `risk:medium` `depends:[S02]`
  > After this: unit tests prove Mental Model System — completed 2026-02-22 works
- [x] **S04: Admin Shell and Object Creation — completed 2026 02 22** `risk:medium` `depends:[S03]`
  > After this: unit tests prove Admin Shell and Object Creation — completed 2026-02-22 works
- [x] **S05: Data Browsing and Visualization — completed 2026 02 22** `risk:medium` `depends:[S04]`
  > After this: unit tests prove Data Browsing and Visualization — completed 2026-02-22 works
- [x] **S06: User and Team Management — completed 2026 02 22** `risk:medium` `depends:[S05]`
  > After this: unit tests prove User and Team Management — completed 2026-02-22 works
- [x] **S07: Route Protection and Provenance — completed 2026 02 23** `risk:medium` `depends:[S06]`
  > After this: unit tests prove Route Protection and Provenance — completed 2026-02-23 works
- [x] **S08: Integration Bug Fixes — completed 2026 02 23** `risk:medium` `depends:[S07]`
  > After this: unit tests prove Integration Bug Fixes — completed 2026-02-23 works
- [x] **S09: Provenance and Redirect Micro Fixes — completed 2026 02 23** `risk:medium` `depends:[S08]`
  > After this: unit tests prove Provenance and Redirect Micro-Fixes — completed 2026-02-23 works
- [x] **S10: Bug Fixes And Cleanup Architecture** `risk:medium` `depends:[S09]`
  > After this: Fix the body loading experience and editor editability issues.
- [x] **S11: Read Only Object View** `risk:medium` `depends:[S10]`
  > After this: Build the read-only object view backend, template, and styling so that objects display a polished property table and rendered Markdown body by default.
- [x] **S12: Sidebar And Navigation** `risk:medium` `depends:[S11]`
  > After this: Restructure the sidebar from a flat nav list with Unicode emoji icons into a grouped, collapsible navigation system with Lucide SVG icons, section headers, and a collapse-to-icon-rail toggle (Ctrl+B).
- [x] **S13: Dark Mode And Visual Polish** `risk:medium` `depends:[S12]`
  > After this: Create the CSS custom property token system with light and dark theme definitions, the anti-FOUC inline script, the theme toggle UI in the user popover, command palette theme entries, and migrate all hardcoded colors across the four CSS files to use tokens.
- [x] **S14: Split Panes And Bottom Panel** `risk:medium` `depends:[S13]`
  > After this: Build the WorkspaceLayout foundation: a new workspace-layout.
- [x] **S15: Settings System And Node Type Icons** `risk:medium` `depends:[S14]`
  > After this: Build the settings infrastructure layer: database model, service, FastAPI endpoints, client JS module, and workspace keyboard/tab integration.
- [x] **S16: Event Log Explorer** `risk:medium` `depends:[S15]`
  > After this: Build the EventQueryService backend and wire the event log timeline into the bottom panel.
- [x] **S17: Llm Connection Configuration** `risk:medium` `depends:[S16]`
  > After this: Implement LLM connection configuration: secure API key storage via Fernet encryption in InstanceConfig, owner-only settings UI with masked key field, and backend endpoints for saving config, testing the connection, and fetching available models.
- [x] **S18: Tutorials And Documentation** `risk:medium` `depends:[S17]`
  > After this: Integrate Driver.
- [x] **S19: Bug Fixes And E2e Test Hardening** `risk:medium` `depends:[S18]`
  > After this: Fix all backend bugs from the CONCERNS.
- [x] **S20: Architecture Decision Commit — completed 2026 02 28** `risk:medium` `depends:[S19]`
  > After this: unit tests prove Architecture Decision Commit — completed 2026-02-28 works
- [x] **S21: Research Synthesis — completed 2026 02 28** `risk:medium` `depends:[S20]`
  > After this: unit tests prove Research Synthesis — completed 2026-02-28 works
- [x] **S22: Tech Debt Sprint — completed 2026 03 01** `risk:medium` `depends:[S21]`
  > After this: unit tests prove Tech Debt Sprint — completed 2026-03-01 works
- [x] **S23: SPARQL Console — completed 2026 03 01** `risk:medium` `depends:[S22]`
  > After this: unit tests prove SPARQL Console — completed 2026-03-01 works
- [x] **S24: FTS Keyword Search — completed 2026 03 01** `risk:medium` `depends:[S23]`
  > After this: unit tests prove FTS Keyword Search — completed 2026-03-01 works
- [x] **S25: CSS Token Expansion — completed 2026 03 01** `risk:medium` `depends:[S24]`
  > After this: unit tests prove CSS Token Expansion — completed 2026-03-01 works
- [x] **S26: VFS MVP Read Only — completed 2026 03 01** `risk:medium` `depends:[S25]`
  > After this: unit tests prove VFS MVP Read-Only — completed 2026-03-01 works
- [x] **S27: VFS Write + Auth — completed 2026 03 01** `risk:medium` `depends:[S26]`
  > After this: unit tests prove VFS Write + Auth — completed 2026-03-01 works
- [x] **S28: UI Polish + Integration Testing — completed 2026 03 01** `risk:medium` `depends:[S27]`
  > After this: unit tests prove UI Polish + Integration Testing — completed 2026-03-01 works
- [x] **S29: Fts Fuzzy Search** `risk:medium` `depends:[S28]`
  > After this: Implement typo-tolerant fuzzy search in the backend by adding `_normalize_query()` to `SearchService` and exposing a `fuzzy: bool` parameter on the `/api/search` endpoint.
- [x] **S30: Dockview Phase A Migration** `risk:medium` `depends:[S29]`
  > After this: Replace the Split.
- [x] **S31: Object View Redesign** `risk:medium` `depends:[S30]`
  > After this: Redesign the object tab so the Markdown body is the primary content in both view and edit modes, with RDF properties hidden behind a collapsible toggle badge in the toolbar.
- [x] **S32: Carousel Views And View Bug Fixes** `risk:medium` `depends:[S31]`
  > After this: Fix all broken htmx targets in view templates (dockview migration broke `#editor-area` references), redesign cards group-by as collapsible accordion sections, and remove the old broken view-type-switcher buttons from the view toolbar.
- [x] **S33: Named Layouts And Vfs Settings Restore** `risk:medium` `depends:[S32]`
  > After this: Create the named layouts data layer and fix VFS Settings icon visibility.
- [x] **S34: E2e Test Coverage** `risk:medium` `depends:[S33]`
  > After this: Fix existing E2E tests that skip or target wrong endpoints: rewrite SPARQL console tests for the actual admin page, fix VFS WebDAV auth to use Basic auth with API tokens (wsgidav does NOT accept session cookies), and verify FTS tests pass as-is.
- [x] **S35: Owl2 Rl Inference** `risk:medium` `depends:[S34]`
  > After this: Build the complete backend inference engine: owlrl dependency, InferenceService with selective entailment filtering, API endpoints for triggering inference and managing inferred triples (list, dismiss, promote), SQLite metadata table for per-triple state, and event log integration.
- [x] **S36: Shacl Af Rules** `risk:medium` `depends:[S35]`
  > After this: Extend the Mental Model manifest, loader, and registry to support an optional `rules` entrypoint, and extend the inference pipeline to execute SHACL-AF rules via `pyshacl.
- [x] **S37: Global Lint Data Model Api** `risk:medium` `depends:[S36]`
  > After this: Build the lint data model, storage layer, and REST API endpoints for querying structured SHACL validation results.
- [x] **S38: Global Lint Dashboard Ui** `risk:medium` `depends:[S37]`
  > After this: Build the global lint dashboard backend endpoint, HTML template, and workspace tab registration.
- [x] **S39: Edit Form Helptext And Bug Fixes** `risk:medium` `depends:[S38]`
  > After this: Add `sempkm:editHelpText` SHACL annotation support to edit forms.
- [x] **S40: E2e Test Coverage V24** `risk:medium` `depends:[S39]`
  > After this: Create Playwright E2E tests for the two major v2.
- [x] **S41: Gap Closure Rules Flip Vfs** `risk:medium` `depends:[S40]`
  > After this: Wire the rules graph into model install and add validation enqueue after promote_triple.
- [x] **S42: Vfs Browser Fix** `risk:medium` `depends:[S41]`
  > After this: Fix three bugs preventing the VFS browser from functioning: (1) wrong LabelService method name causing 500 errors on object listing, (2) wrong SPARQL predicate causing model names to fall back to IDs, (3) htmx `revealed` trigger without `once` causing infinite retry loops on error.
- [x] **S43: Inference E2e Test Gap** `risk:medium` `depends:[S42]`
  > After this: Fix the `_store_inferred_triples` Literal bug and add an E2E test covering the full inference user story: create a one-sided relationship, run inference, verify the inverse triple appears.
- [x] **S44: UI Cleanup — completed 2026 03 08** `risk:medium` `depends:[S43]`
  > After this: unit tests prove UI Cleanup — completed 2026-03-08 works
- [x] **S45: Obsidian Vault Scanner — completed 2026 03 08** `risk:medium` `depends:[S44]`
  > After this: unit tests prove Obsidian Vault Scanner — completed 2026-03-08 works
- [x] **S46: Obsidian Mapping UI — completed 2026 03 08** `risk:medium` `depends:[S45]`
  > After this: unit tests prove Obsidian Mapping UI — completed 2026-03-08 works
- [x] **S47: Obsidian Batch Import — completed 2026 03 08** `risk:medium` `depends:[S46]`
  > After this: unit tests prove Obsidian Batch Import — completed 2026-03-08 works
- [x] **S48: WebID Profiles — completed 2026 03 08** `risk:medium` `depends:[S47]`
  > After this: unit tests prove WebID Profiles — completed 2026-03-08 works
- [x] **S49: IndieAuth Provider — completed 2026 03 08** `risk:medium` `depends:[S48]`
  > After this: unit tests prove IndieAuth Provider — completed 2026-03-08 works
- [x] **S50: User Guide & Documentation — completed 2026 03 09** `risk:medium` `depends:[S49]`
  > After this: unit tests prove User Guide & Documentation — completed 2026-03-09 works
- [x] **S51: Spatial Canvas UX — completed 2026 03 09** `risk:medium` `depends:[S50]`
  > After this: unit tests prove Spatial Canvas UX — completed 2026-03-09 works
- [x] **S52: Bug Fixes Security** `risk:medium` `depends:[S51]`
  > After this: Fix two known regressions: (1) lint dashboard filter controls overflow on narrow viewports, and (2) event log fails to render badges, diffs, and undo for compound operation types like "body.
- [x] **S53: Sparql Power User** `risk:medium` `depends:[S52]`
  > After this: Build the backend data layer and API endpoints for SPARQL query history, saved queries, result enrichment, and ontology vocabulary.
- [x] **S54: Sparql Advanced** `risk:medium` `depends:[S53]`
  > After this: Implement SPARQL query sharing: data models, migration, API endpoints, and full frontend UI for sharing saved queries between users.
- [x] **S55: Browser Ui Polish** `risk:medium` `depends:[S54]`
  > After this: Add hover-reveal action buttons (refresh, plus) to the OBJECTS section header in the nav tree, and extend the command palette with per-type "Create X" entries.
- [x] **S56: Vfs Mountspec** `risk:medium` `depends:[S55]`
  > After this: Create the MountSpec RDF vocabulary, a MountService for CRUD operations on mount definitions, and REST API endpoints for the settings UI to consume.
- [x] **S57: Spatial Canvas** `risk:medium` `depends:[S56]`
  > After this: Snap-to-grid alignment, edge label polish, and keyboard navigation for the spatial canvas.
- [x] **S58: Federation** `risk:medium` `depends:[S57]`
  > After this: RDF Patch serialization, EventStore extensions for federation, and patch export API.
