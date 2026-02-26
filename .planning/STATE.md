# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations -- no blank-page syndrome, no schema setup.
**Current focus:** v2.0 Tighten Web UI -- Phase 18 in progress (Tutorials and Documentation)

## Current Position

Phase: 18 of 18 (Tutorials and Documentation)
Plan: 2 of 2 (complete)
Status: Phase 18 complete — all plans done (DOCS-01 through DOCS-04)
Last activity: 2026-02-24 - Completed 18-02: Driver.js Guided Tours (tutorials.js)

Progress: [##########] 100% (v2.0) -- 18-02 complete (24/24 plans)

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

### Pending Todos

1. Add edit form helptext property to SHACL types (ui)

### Known Tech Debt (from v1.0)

- Cookie secure=False (needs production config)
- SMTP deferred (magic link tokens logged to console)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- empty_shapes_loader dead code

### Blockers/Concerns

- Split.js has no dynamic pane API -- editor group data model must be designed before read-only view changes `#editor-area` targeting (addressed: Phase 10 plan 10-03 designs the model, Phase 14 implements)
- Shepherd.js v14 is AGPL-3.0 -- using Driver.js (MIT) instead (addressed in REQUIREMENTS.md)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Add copyright notice to docs site | 2026-02-24 | 1ad8949 | [1-add-copyright-notice-to-docs-site](./quick/1-add-copyright-notice-to-docs-site/) |
| 2 | Research gist ontology applicability to SemPKM Mental Models | 2026-02-24 | af5d5ef | [2-research-how-the-gist-ontology-can-be-us](./quick/2-research-how-the-gist-ontology-can-be-us/) |
| 3 | Research Hypothes.is and W3C Web Annotation technology for SemPKM integration | 2026-02-24 | 8d62fe1 | [3-research-hypothes-is-annotation-technolo](./quick/3-research-hypothes-is-annotation-technolo/) |
| 4 | Display user guide markdown files in Docs tab with in-tab viewer | 2026-02-25 | dd4a563 | [4-display-user-guide-markdown-files-in-doc](./quick/4-display-user-guide-markdown-files-in-doc/) |

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed quick task 4 (display-user-guide-markdown-files-in-doc)
Resume: v2.0 complete — all 24 plans across 18 phases finished; quick tasks ongoing
