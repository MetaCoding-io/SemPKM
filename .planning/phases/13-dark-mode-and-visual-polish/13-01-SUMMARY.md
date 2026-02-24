---
phase: 13-dark-mode-and-visual-polish
plan: 01
subsystem: ui
tags: [css-custom-properties, dark-mode, theming, anti-fouc, ninja-keys, lucide]

# Dependency graph
requires:
  - phase: 12-sidebar-and-navigation
    provides: sidebar layout, user popover with Popover API, Lucide icons
provides:
  - CSS custom property token system (theme.css) with 35+ light/dark tokens
  - Anti-FOUC inline script preventing wrong-theme flash
  - Theme toggle UI in user popover (Sun/Monitor/Moon icons)
  - Theme toggle via command palette (Theme Light/Dark/System)
  - theme.js toggle logic with localStorage persistence and sempkm:theme-changed event
  - All four CSS files migrated to use var(--color-*) tokens exclusively
  - ninja-keys CSS variable overrides for themed command palette
affects: [13-02, 13-03, 14-editor-groups, 15-settings-system]

# Tech tracking
tech-stack:
  added: [theme.css, theme.js]
  patterns: [css-custom-property-tokens, data-theme-attribute, anti-fouc-inline-script, no-transition-class]

key-files:
  created:
    - frontend/static/css/theme.css
    - frontend/static/js/theme.js
  modified:
    - frontend/static/css/style.css
    - frontend/static/css/workspace.css
    - frontend/static/css/forms.css
    - frontend/static/css/views.css
    - backend/app/templates/base.html
    - backend/app/templates/components/_sidebar.html
    - frontend/static/js/workspace.js

key-decisions:
  - "CSS custom property token system in theme.css as single source of truth for all colors"
  - "data-theme attribute on html element for clean CSS specificity (not class-based)"
  - "Anti-FOUC inline script reads localStorage synchronously before any stylesheets render"
  - "Crossfade transition on specific layout elements only (not * universally) to prevent perf issues"
  - "Active tab accent color changed from primary blue to teal (var(--color-accent)) per user decision"
  - "no-transition class removed via requestAnimationFrame to prevent initial load animation"

patterns-established:
  - "Token naming: --color-{category}[-variant] (bg, surface, text, border, accent, primary, success, error, warning)"
  - "Dark overrides on html[data-theme='dark'] selector in theme.css only"
  - "sempkm:theme-changed CustomEvent dispatched on every theme switch for third-party integration"
  - "Theme buttons use data-theme-value attribute for active state tracking"

requirements-completed: [DARK-01, DARK-02, DARK-04]

# Metrics
duration: 8min
completed: 2026-02-24
---

# Phase 13 Plan 01: CSS Token System and Dark Mode Foundation Summary

**CSS custom property token system with 35+ light/dark tokens, anti-FOUC inline script, tri-state theme toggle (Sun/Monitor/Moon + command palette), and full migration of ~430 hardcoded colors across four CSS files to semantic token references**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-24T03:00:05Z
- **Completed:** 2026-02-24T03:08:14Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Created theme.css with complete light and dark CSS custom property token set (35+ tokens covering surfaces, text, borders, accent, primary, semantic status, shadows, and misc)
- Anti-FOUC inline script in base.html head prevents wrong-theme flash on page load
- Theme toggle UI in user popover with 3-icon row (Sun/Monitor/Moon) and command palette entries (Theme: Light/Dark/System Default)
- Migrated all ~385 hardcoded hex and ~45 rgba values across style.css, workspace.css, forms.css, and views.css to var(--color-*) token references
- ninja-keys command palette styled via CSS variable overrides in theme.css
- highlight.js theme switching via id="hljs-theme" attribute on link tag

## Task Commits

Each task was committed atomically:

1. **Task 1: Create theme.css token system, anti-FOUC script, and theme.js toggle** - `f7707e8` (feat)
2. **Task 2: Migrate all hardcoded colors in CSS files to theme tokens** - `c61d405` (feat)

## Files Created/Modified
- `frontend/static/css/theme.css` - CSS custom property token definitions for light and dark modes, crossfade transitions, theme button styles, ninja-keys overrides
- `frontend/static/js/theme.js` - Theme toggle logic, localStorage persistence, third-party integration (ninja-keys dark class, highlight.js stylesheet swap), sempkm:theme-changed event
- `backend/app/templates/base.html` - Anti-FOUC inline script, theme.css link (first stylesheet), hljs-theme id, theme.js script tag
- `backend/app/templates/components/_sidebar.html` - Replaced disabled Theme link with 3-icon theme row (Sun/Monitor/Moon)
- `frontend/static/js/workspace.js` - Added Theme: Light/Dark/System Default command palette entries
- `frontend/static/css/style.css` - Removed duplicate :root color tokens, migrated remaining hardcoded colors to tokens
- `frontend/static/css/workspace.css` - Full migration of ~181 hardcoded colors to tokens, removed ninja-keys overrides (moved to theme.css)
- `frontend/static/css/forms.css` - Full migration of ~56 hardcoded colors to tokens
- `frontend/static/css/views.css` - Full migration of ~119 hardcoded colors to tokens

## Decisions Made
- Used CSS custom property token system in theme.css as single source of truth (standard approach, zero dependencies)
- data-theme attribute on html element rather than class for clean CSS specificity and semantic clarity
- Anti-FOUC script placed inline in head before all stylesheet links for synchronous execution
- Crossfade transition (150ms) applied only to specific layout elements (body, sidebar, content-area, tabs, etc.) rather than universally on * to prevent performance issues
- Active tab border-bottom color changed from --color-primary (blue) to --color-accent (teal) per user's "teal/cyan accent" decision
- no-transition class pattern: set during FOUC prevention, removed after first paint via requestAnimationFrame
- Dark mode palette follows "softer Dark+" direction: warmer grays (#1e2127 bg, #282c34 surface), teal accent (#56b6c2), muted text (#abb2bf)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Token system ready for Phase 13-02 (CodeMirror, Cytoscape, and third-party dark mode integration)
- sempkm:theme-changed event wired up for editor.js and graph.js to listen for theme switches
- highlight.js theme switching ready via id="hljs-theme" attribute
- Tab styling tokens in place for Phase 13-03 (rounded tabs, close button polish)

## Self-Check: PASSED

- All created files verified on disk
- Both task commits verified in git log (f7707e8, c61d405)
- No hardcoded hex/rgba values remaining in migrated CSS files

---
*Phase: 13-dark-mode-and-visual-polish*
*Completed: 2026-02-24*
