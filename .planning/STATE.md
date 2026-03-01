---
gsd_state_version: 1.0
milestone: v2.2
milestone_name: Data Discovery
status: between_milestones
last_updated: "2026-03-01"
progress:
  total_phases: 22
  completed_phases: 22
  total_plans: 36
  completed_plans: 36
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.
**Current focus:** v2.2 Data Discovery — planning next milestone (FTS, SPARQL console, VFS MVP)

## Current Position

Phase: — (between milestones)
Status: v2.1 complete — 3 phases, 9 plans, 9/9 requirements satisfied
Last activity: 2026-03-01 — v2.1 milestone archived

Progress: [██████████] 100% (v2.1 complete) — ready for v2.2

## v2.1 Phase Summary (COMPLETE)

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 20. Architecture Decision Commit | Formalize 4 research tracks as committed decisions | DEC-01, DEC-02, DEC-03, DEC-04 | Complete (2026-02-28) |
| 21. Research Synthesis | Produce DECISIONS.md with v2.2 guidance | SYN-01 | Complete (2026-02-28) |
| 22. Tech Debt Sprint | Alembic, SMTP, session cleanup, ViewSpec cache | TECH-01, TECH-02, TECH-03, TECH-04 | Complete (2026-03-01) |

## v2.2 Phase Structure (PLANNED)

See `.planning/DECISIONS.md` for full rationale and implementation readiness checklist.

| Phase | Name | Requirements | Depends On |
|-------|------|--------------|------------|
| 23. SPARQL Console | Yasgui CDN embed + custom YASR renderer | SPARQL-01, SPARQL-02, SPARQL-03 | None |
| 24. FTS Keyword Search | LuceneSail indexing, SPARQL FTS, Ctrl+K | FTS-01, FTS-02, FTS-03 | None |
| 25. CSS Token Expansion | 40 → ~91 tokens, two-tier architecture | — (v2.3 prerequisite) | None |
| 26. VFS MVP read-only | wsgidav WebDAV mount, MountSpec vocab | VFS-01, VFS-02, VFS-03 | None |
| 27. VFS Write + Auth | Write path, API token auth design | — | Phase 26 |

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 26
- Total execution time: across 9 phases
- v2.0 estimated plans: ~23

**v2.0 Metrics:**

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 10    | 01   | 2min     | 2     | 3     |
| 10    | 03   | 2min     | 2     | 6     |
| 11    | 01   | 4min     | 2     | 7     |
| 11    | 02   | session  | 15    | 12    |
| 12    | 01   | 4min     | 2     | 8     |
| 12    | 02   | 2min     | 2     | 3     |
| 13    | 01   | 8min     | 2     | 9     |
| 13    | 02   | 2min     | 2     | 3     |
| 13    | 03   | 2min     | 2     | 2     |
| 13    | 04   | 2min     | 2     | 4     |
| 14    | 01   | 4min     | 2     | 5     |
| 14    | 02   | 3min     | 2     | 2     |
| 14    | 03   | 60min    | 3     | 4     |
| 15    | 01   | 6min     | 2     | 11    |
| 15    | 02   | 3min     | 3     | 5     |
| 15    | 03   | 4min     | 2     | 9     |
| 16    | 01   | 12min    | 2     | 4     |
| 16    | 02   | 2min     | 2     | 3     |
| 16    | 03   | 3min     | 2     | 6     |
| 17    | 01   | 4min     | 2     | 8     |
| 17    | 02   | 1min     | 2     | 2     |
| 18    | 01   | 4min     | 2     | 8     |
| 18    | 02   | 2min     | 2     | 2     |
| 19    | 01   | 13min    | 2     | 6     |
| 19    | 02   | 28min    | 2     | 8     |
| Phase 20 P01 | 2min | 2 tasks | 1 files |
| Phase 20 P02 | 2min | 2 tasks | 1 files |
| Phase 20 P02 | 2min | 2 tasks | 1 files |
| Phase 20 P03 | 2min | 2 tasks | 1 files |
| Phase 22 P01 | 2min | 2 tasks | 4 files |
| Phase 22 P02 | 2min | 2 tasks | 4 files |
| Phase 22 P03 | 4min | 2 tasks | 3 files |
| Phase 20 P03 | 2min | 2 tasks | 1 files |
| Phase 20 P04 | 2min | 2 tasks | 1 files |
| Phase 20 P05 | 5min | 3 tasks | 2 files |
| Phase 21 P01 | 3min | 2 tasks | 1 files |
| Phase 21 P01 | 3min | 2 tasks | 1 files |

## Accumulated Context

### Key Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table.

v2.0 roadmap decisions:
- Phase 10 includes editor group data model DESIGN (not implementation) to prevent Split.js pitfall (Pitfall 1 from research)
- Driver.js replaces Shepherd.js (MIT vs AGPL-3.0 licensing issue)
- WORK-06 (rounded tabs) grouped with Phase 13 (dark mode/visual polish) since both are CSS styling
- ERR-01 (styled 403) grouped with Phase 13 (visual polish) since it is a template/styling task
- Settings system (Phase 15) placed after dark mode (Phase 13) -- dark mode uses CSS-only approach first, migrates to settings consumer later
- (10-01) Promise.race with 3s timeout replaces setInterval polling for editor loading -- deterministic failure time
- (10-01) Skeleton loading uses CSS-only shimmer animation (no JS animation dependency)
- (10-02) position: fixed + getBoundingClientRect for dropdown overflow escape rather than removing overflow-y: auto from form sections
- (10-03) Cleanup registry uses element IDs as keys with arrays of teardown functions; htmx:beforeCleanupElement walks descendants
- (10-03) Split.js instances tracked globally in window._sempkmSplits with destroy-before-recreate guard
- (11-01) Multi-valued properties stored as dict[str, list[str]] -- backward compatible with existing edit form templates
- (11-01) Edit mode initialization deferred via _initEditMode_ function to prevent CodeMirror/Split.js waste on read-only views
- (11-01) CDN-loaded marked.js + highlight.js + DOMPurify for client-side Markdown rendering (no server-side dependency)
- (11-01) Reference tooltips show "TypeLabel: ObjectLabel" format derived from SHACL sh:class target_class
- (11-02) JS setTimeout at animation midpoint for face visibility swap (CSS backface-visibility unreliable in complex DOM)
- (11-02) Body predicate unification: detect SHACL Body property by name, use model-specific path for save
- (11-02) dcterms:created/modified excluded from edit form, modified auto-updated on save
- (11-02) Lazy-loaded ref-pill popovers reuse graph-popover CSS for visual consistency
- (12-01) Lucide icons via CDN with htmx:afterSwap re-initialization for dynamic content
- (12-01) CSS custom property --sidebar-width drives synchronized sidebar/content transitions
- (12-01) Ctrl+B remapped from Split.js pane toggle to sidebar collapse toggle
- (12-02) HTML Popover API (popover="auto") for user menu -- light-dismiss, top-layer stacking, focus management without custom JS
- (12-02) Deterministic avatar color via hash of user name string, 8-color palette
- (12-02) Popover Lucide icons re-initialized via toggle event listener on each open
- (13-01) CSS custom property token system in theme.css as single source of truth for all colors (35+ tokens)
- (13-01) data-theme attribute on html element for theme state (not class-based)
- (13-01) Anti-FOUC inline script in head before stylesheets reads localStorage synchronously
- (13-01) Crossfade transitions on specific layout elements only (not * universally) to prevent perf issues
- (13-01) Active tab accent changed from primary blue to teal (var(--color-accent)) per user decision
- (13-01) no-transition class pattern: set during FOUC prevention, removed via requestAnimationFrame
- (13-02) Compartment.reconfigure() for CodeMirror theme switching -- preserves cursor, undo history without recreation
- (13-02) Cytoscape style().fromJson().update() for live graph style rebuild -- avoids destruction and relayout
- (13-02) Theme.js central dispatcher calls switchEditorThemes and switchGraphTheme directly plus event backup
- (13-03) Tab bar align-items: flex-end for tab pop-forward visual effect
- (13-03) Close button opacity 0 default with parent hover selectors for contextual visibility
- (13-03) 403 page fully standalone with own anti-FOUC script and theme.css (no base.html dependency)
- (13-03) Error panel button classes prefixed btn-error- to avoid workspace .btn-primary collision
- (13-04) Explicit Ctrl+K keydown handler in initKeyboardShortcuts() because hotkeys-js ignores events on INPUT/TEXTAREA/SELECT
- (13-04) ninja-keys CDN pinned to v1.2.2 to prevent unpinned resolution breakage
- (14-01) workspace-layout.js as separate IIFE module (workspace.js was 1024 lines; separation per RESEARCH.md recommendation)
- (14-01) Ctrl+\\ reassigned from toggleSidebar to splitRight; sidebar stays on Ctrl+B (Phase 12)
- (14-01) gutterSize:1 with CSS ::after pseudo-element for 9px pointer hit-target (Pitfall 2 solution)
- (14-01) Tab objects normalize both .id and .iri fields for backward compat with old sessionStorage data
- (14-01) splitRight duplicates active tab into new group (duplicate objects allowed per CONTEXT.md)
- (14-02) renderGroupTabBar refactored from innerHTML string-building to DOM createElement/appendChild for event listener attachment
- (14-02) recreateGroupSplit explicitly creates #editor-groups-container div (Plan 01 cleared it with innerHTML='')
- (14-02) isDragging flag with setTimeout(0) reset on dragend guards against accidental tab switch after short drag (Pitfall 3)
- (14-02) Context menu positions via viewport-clamped clientX/clientY with menuRect correction; Escape + click-outside dismiss
- (14-03) CSS height transition (height: 0 -> Npx with overflow:hidden) for smooth panel open/close -- avoids layout jump from display:none toggle
- (14-03) Bottom panel DOM detached and re-inserted around recreateGroupSplit to survive Split.js reinitialization
- (14-03) panelState.height stored as percentage not pixels -- scales correctly on window resize
- (14-03) DOM preservation pattern for Split.js recreation: save real DOM nodes, wipe container, re-insert before recreate
- (15-01) SettingsService uses installed_models_dir=/app/models (matches Docker mount from main.py)
- (15-01) get_settings_service creates SettingsService per-request (stateless, no app.state needed)
- (15-01) special:settings tab skips right-pane section loading (no relations/lint for settings page)
- (15-01) settings.js auto-fetches on DOM ready to warm cache before consumers call SemPKMSettings.get()
- (15-02) settingChanged() -> SemPKMSettings.set() -> sempkm:setting-changed CustomEvent -> theme.js setTheme() -- no direct coupling between settings UI and theme module
- (15-02) 300ms DOMContentLoaded delay for server-theme sync allows settings.js auto-fetch to complete; anti-FOUC script applied localStorage theme before first paint so delay is safe
- (15-02) localStorage write-through on every theme change keeps anti-FOUC fast-path accurate for future page loads
- (15-02) Modified badge and Reset button rendered server-side (Jinja2) based on user_overrides presence; removed client-side on reset without page reload
- (15-03) IconService per-request creation (stateless, matches SettingsService approach)
- (15-03) iconToShape mapping translates Lucide icon names to Cytoscape shapes; unmapped icons default to ellipse
- (15-03) window._sempkmIcons fetched on workspace init as client-side cache for graph shapes and tab icons
- (15-03) basic-pkm icons use actual types (Note/Concept/Project/Person); plan examples (Source/Tag) were not in the model
- (16-01) EventQueryService uses GROUP_CONCAT SPARQL primary + Python OrderedDict fallback for affectedIRI grouping (RDF4J compatibility)
- (16-01) Event log object links use openTab() JS (nav tree pattern) not hx-get/#editor-area (dynamic per group, not stable DOM ID)
- (16-01) Panel lazy-load: .panel-placeholder check guards against re-loading already-loaded content in initPanelTabs() and _applyPanelState()
- (16-02) dict_without filter registered in main.py (global Jinja2 env) not in router -- filters are env-level config, not per-route
- (16-02) urlencode filter overridden as dict-capable (urllib.parse.urlencode) -- built-in Jinja2 urlencode handles scalars only; dict_without|urlencode chain requires dict encoding
- (16-02) Event log object links use hx-get for click-to-filter (not openTab()) -- filtering the timeline vs navigating to the object are distinct actions
- (16-03) loop.index IDs used for htmx diff targets (not hx-target='next') for htmx version compatibility
- (16-03) build_compensation() uses concrete Literal values in materialize_deletes (not Variable) -- undo targets specific known old values
- (16-03) edge.create undo uses operation_type='edge.create.undo' to distinguish compensating event in event log
- (17-01) PBKDF2HMAC with SHA256 derives Fernet key from secret_key; fixed salt (stability over secrecy for InstanceConfig)
- (17-01) save_config skips empty string api_key to prevent overwriting existing key with blank input
- (17-01) api_key_set bool returned from get_config, never the key value; settings/data endpoint pops llm.api_key
- (17-01) 600ms debounced client-side saves via fetch PUT (no form submission, instant UX feedback)
- (17-02) aiter_lines() over aiter_bytes() for upstream SSE passthrough -- buffers across HTTP chunk boundaries for complete lines
- (17-02) StreamingResponse X-Accel-Buffering: no as defense-in-depth even without nginx location match
- (17-02) /browser/llm/chat/stream accessible to any authenticated user (get_current_user) for future AI Copilot
- (18-01) special:docs tab follows exact special:settings pattern -- same openDocsTab/openSettingsTab structure, same isSpecial guard extension
- (18-01) StaticFiles mount for docs/guide/ guarded by is_dir() check to prevent startup crash when docs/ volume not mounted
- (18-01) Driver.js CSS link placed before JS script tag in base.html (prevents unstyled overlay flash per RESEARCH.md Pitfall 4)
- (18-02) Read/edit toggle selector is .mode-toggle (not [data-action=toggle-edit]) -- confirmed from object_tab.html template inspection
- (18-02) getActiveEditorArea() and showTypePicker() already exposed as window globals -- no changes to workspace.js needed
- (19-01) Conditional CORS: empty CORS_ORIGINS means wildcard without credentials; non-empty means specific origins with credentials (CORS spec compliance)
- (19-01) COOKIE_SECURE defaults True; set COOKIE_SECURE=false for local HTTP dev
- (19-01) IRI validation uses urlparse scheme+netloc; urn: IRIs rejected (no netloc) -- acceptable since all object IRIs are https://
- (19-01) EventStore commit result captured in undo_event to enable label_service.invalidate()
- (19-02) Tab active guard in switchTabInGroup: if group.activeTabId === tabId return early (no htmx reload)
- (19-02) Tag pill match uses 'tags' in prop.path — matches bpkm:tags IRI (urn:sempkm:model:basic-pkm:tags, xsd:string)
- (19-02) Nav tree tooltip: event-delegated, single shared element, type_label resolved server-side in tree_children endpoint
- (19-02) Graph node hover tooltip confirmed correct — typeLabel already in node data from views service, no changes needed

v2.1 roadmap decisions:
- Phase 20 decisions committed: DEC-01 LuceneSail, DEC-02 Yasgui CDN, DEC-03 wsgidav+a2wsgi, DEC-04 dockview-core
- Phase 20 (DEC) runs before Phase 21 (SYN) — synthesis requires all 4 decisions to be committed first
- Phase 22 (TECH) is independent — can run in parallel with Phases 20 and 21
- Research is complete for all 4 DEC phases; Phase 20 formalizes existing RESEARCH.md files (no new research)
- 3 phases chosen for standard depth: natural delivery boundaries align with the 3 requirement categories (DEC, SYN, TECH)

v2.1 Phase 20 execution decisions (20-01):
- (20-01) LuceneSail chosen for FTS: zero new containers, zero sync infra, SPARQL-native integration, ships with RDF4J 5.0.1 distribution
- (20-01) OpenSearch/Jena/Oxigraph/GraphDB explicitly ruled out with specific rationale; pgvector semantic search deferred to Phase 20b (blocked on PostgreSQL migration)
- (20-01) Three highest-priority implementation prerequisites: (1) verify LuceneSail JAR in Docker image, (2) validate Turtle config for RDF4J 5.x unified namespace, (3) validate FROM clause graph scoping

v2.1 Phase 20 execution decisions (20-02):
- (20-02) @zazuko/yasgui v4.5.0 via CDN embed chosen for SPARQL Console — de facto standard, MIT-licensed, zero backend changes needed
- (20-02) Eight alternatives explicitly ruled out: sib-swiss, Comunica, AtomGraph, custom CodeMirror build, iframe, sidecar container, npm build step, TriplyDB fork
- (20-02) Custom YASR table cell renderer for SemPKM IRI-to-object-browser links committed as design (satisfies SPARQL-02)
- (20-02) localStorage persistence with key sempkm-sparql committed (satisfies SPARQL-03)

v2.1 Phase 20 execution decisions (20-03):
- (20-03) wsgidav + a2wsgi WSGI/ASGI bridge chosen for WebDAV VFS — Docker-compatible, HTTP-only, no kernel-level access required
- (20-03) FUSE explicitly ruled out: requires SYS_ADMIN Docker cap prohibited by AWS Fargate, Fly.io, Railway managed hosting
- (20-03) Read-only first MVP: defer write path (diff engine, ETag concurrency, python-frontmatter round-trips) to Phase 22d
- (20-03) Three new Python packages required: wsgidav>=4.3.3,<5.0, a2wsgi>=1.10, python-frontmatter>=1.1.0
- (20-03) SyncTriplestoreClient needed: DAVProvider runs in WSGI thread pool, cannot use httpx.AsyncClient
- (20-03) API token Basic auth pattern committed (username=SemPKM username, password=revocable token) — design deferred to Phase 22c

v2.1 Phase 20 execution decisions (20-04):
- (20-04) dockview-core chosen over GoldenLayout 2: DOM reparenting in GoldenLayout breaks htmx event handlers; dockview-core has zero deps, first-class vanilla TypeScript support, CSS custom property theming via --dv-* variables
- (20-04) Incremental Split.js migration committed: Phase A (inner editor-pane split) -> Phase B (full workspace) -> Phase C (floating panels); Phase A in v2.3, B and C deferred
- (20-04) CSS token expansion (from ~40 to ~91 tokens, two-tier primitive + semantic architecture) is v2.2-eligible preparatory work independent of Dockview migration
- (20-04) Bundle size measurement is a prerequisite action before deciding CDN vs vendor loading for dockview-core

v2.1 Phase 22 execution decisions (22-01):
- (22-01) asyncio.to_thread wraps Alembic command.upgrade to avoid nested event loop (env.py uses asyncio.run internally)
- (22-01) AlembicConfig and alembic_command aliases avoid name collision with existing Config usage in main.py
- (22-01) Startup session cleanup pattern: call cleanup after service creation, log only if non-zero purged

v2.1 Phase 21 synthesis decisions (21-01):
- (21-01) v2.2 phases 23-27 sequencing: SPARQL Console first (no prerequisites, ships immediately), FTS second (JAR verification needed first), CSS token expansion third (independent prep for v2.3 Dockview migration), VFS read-only MVP fourth (SyncTriplestoreClient needed), VFS auth+settings fifth (API token auth design required)
- (21-01) Dockview Phase A deferred to v2.3 Phase 1; CSS token expansion (~40 to ~91 tokens) is the only UI Shell work in v2.2
- (21-01) SyncTriplestoreClient (sync httpx.Client) is a required new component for wsgidav WSGI thread pool — cannot share the async TriplestoreClient
- (21-01) API token auth (Basic auth with revocable token as password) must be designed before Phase 27 (VFS write+auth) but not Phase 26 (VFS read-only MVP)
- (21-01) Three auth patterns co-exist in v2.2: session cookie (Yasgui + all browser features), API token Basic auth (wsgidav VFS), LuceneSail inherits existing SPARQL auth with no changes

v2.1 Phase 22 execution decisions (22-02):
- (22-02) send_magic_link_email returns bool (not raises) so caller can fall through to console fallback on SMTP failure
- (22-02) Lazy import of email service inside if smtp_configured block (module only loaded when needed)
- (22-02) SMTP failure falls through to console fallback (returns token) instead of generic "email sent" message
- (22-02) app_base_url config setting avoids request.base_url returning internal container URL behind nginx

### Pending Todos

1. Add edit form helptext property to SHACL types (ui)

### Known Tech Debt (from v1.0/v2.0)

- Cookie secure=False (needs production config)
- SMTP deferred (magic link tokens logged to console) — DONE (Phase 22 Plan 02)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- empty_shapes_loader dead code
- Alembic migration runner not yet in place — DONE (Phase 22 Plan 01)
- Session cleanup job not yet implemented — DONE (Phase 22 Plan 01)
- ~~ViewSpecService TTL cache not yet implemented~~ — completed in Phase 22 Plan 03
- Bottom panel SPARQL/AI Copilot tabs are placeholder stubs (implementation in future milestones)
- Edit form helptext property not yet in SHACL types (pending todo)

### Blockers/Concerns

None for v2.1.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Add copyright notice to docs site | 2026-02-24 | 1ad8949 | [1-add-copyright-notice-to-docs-site](./quick/1-add-copyright-notice-to-docs-site/) |
| 2 | Research gist ontology applicability to SemPKM Mental Models | 2026-02-24 | af5d5ef | [2-research-how-the-gist-ontology-can-be-us](./quick/2-research-how-the-gist-ontology-can-be-us/) |
| 3 | Research Hypothes.is and W3C Web Annotation technology for SemPKM integration | 2026-02-24 | 8d62fe1 | [3-research-hypothes-is-annotation-technolo](./quick/3-research-hypothes-is-annotation-technolo/) |
| 4 | Display user guide markdown files in Docs tab with in-tab viewer | 2026-02-25 | dd4a563 | [4-display-user-guide-markdown-files-in-doc](./quick/4-display-user-guide-markdown-files-in-doc/) |
| 5 | please integrate the user guide in docs/ to the main website in docs/index.html | 2026-02-27 | 8d2bc12 | [5-please-integrate-the-user-guide-in-docs-](./quick/5-please-integrate-the-user-guide-in-docs-/) |
| 6 | transform docs/guide/index.html into a two-panel markdown reader using marked.js CDN | 2026-02-27 | d045017 | [6-transform-docs-guide-index-html-into-a-t](./quick/6-transform-docs-guide-index-html-into-a-t/) |
| 7 | Replace carousel SVG placeholders with real screenshots (6 slides total) | 2026-02-27 | 34eb922 | [7-replace-carousel-svg-placeholders-with-r](./quick/7-replace-carousel-svg-placeholders-with-r/) |
| 8 | Integrate e2e screenshots into user guide chapters | 2026-02-27 | 3159159 | [8-review-e2e-screenshots-and-integrate-the](./quick/8-review-e2e-screenshots-and-integrate-the/) |
| 9 | Standardize navigation footers on all 27 user guide pages | 2026-02-28 | e6c92e5 | [9-fix-user-guide-navigation-footer-links](./quick/9-fix-user-guide-navigation-footer-links/) |

## Session Continuity

Last session: 2026-02-28
Stopped at: Phase 21 Plan 01 complete — DECISIONS.md created, SYN-01 satisfied
Resume: v2.1 complete — run /gsd:plan-phase for v2.2 (Phase 23: SPARQL Console)
