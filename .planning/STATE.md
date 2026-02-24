# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations -- no blank-page syndrome, no schema setup.
**Current focus:** v2.0 Tighten Web UI -- Phase 15 in progress (Settings System and Node Type Icons)

## Current Position

Phase: 15 of 18 (Settings System and Node Type Icons)
Plan: 1 of 3 (complete)
Status: Phase 15 plan 01 complete (Settings infrastructure: DB model, service, API, client JS, Ctrl+,)
Last activity: 2026-02-24 - Completed 15-01 (Settings Infrastructure)

Progress: [######░░░░] 62% (v2.0) -- 15-01 complete (15/24 plans)

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

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 15-01-PLAN.md (Settings Infrastructure)
Resume: Begin 15-02 (Settings UI)
