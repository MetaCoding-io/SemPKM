---
phase: 23-sparql-console
plan: 02
subsystem: ui
tags: [yasgui, sparql, css, dark-mode, iri-links, yasr]

# Dependency graph
requires:
  - phase: 23-01
    provides: Yasgui SPARQL console integrated in workspace bottom panel with CDN loading and lazy init
provides:
  - YASR custom URI formatter rendering SemPKM object IRIs as clickable pill links
  - Dark mode CSS overrides for entire Yasgui UI (tab bar, YASQE editor, YASR table)
  - isSemPKMObjectIri() detection function excluding well-known vocabulary prefixes
  - MutationObserver fallback for YASR formatter API unavailability
affects: [28-ui-polish]

# Tech tracking
tech-stack:
  added: []
  patterns: [yasr-uri-formatter, mutation-observer-fallback, css-custom-property-scoping]

key-files:
  created: []
  modified:
    - backend/app/browser/router.py
    - backend/app/templates/browser/workspace.html
    - frontend/static/css/theme.css

key-decisions:
  - "YASR uriFormatter API used as primary approach with MutationObserver as fallback"
  - "IRI pill links use accent color tokens for visual consistency across themes"
  - "Both BEM-style and legacy Yasgui class names targeted in dark mode overrides"

patterns-established:
  - "YASR formatter pattern: register before Yasgui instantiation via plugins.table.defaults.uriFormatter"
  - "IRI detection pattern: base_namespace startsWith check with vocabulary prefix exclusion list"

requirements-completed: [SPARQL-02]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 23 Plan 02: YASR IRI Click-Through and Dark Mode Summary

**Custom YASR cell renderer for SemPKM IRI pill links with openTab() integration, plus comprehensive Yasgui dark mode CSS overrides using existing theme tokens**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T05:26:00Z
- **Completed:** 2026-03-01T05:28:16Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- SemPKM object IRIs in SPARQL result table cells render as styled teal pill links (.sparql-iri-link)
- Clicking an IRI pill link calls window.openTab(iri, label) to open the object in the active editor group
- Well-known vocabulary IRIs (rdf:, rdfs:, skos:, foaf:, schema:, owl:, dcterms:, xsd:, shacl:, prov:, urn:sempkm:) are excluded from link rendering
- Yasgui UI matches dark workspace theme with comprehensive CSS overrides for tab bar, CodeMirror editor, control bar, result table, and plugin controls
- Theme toggle between light and dark updates Yasgui appearance immediately via CSS attribute selector (no page reload)

## Task Commits

Each task was committed atomically:

1. **Task 1: Pass base_namespace to workspace template and register YASR URI formatter** - `7eabea8` (feat)
2. **Task 2: Add Yasgui dark mode CSS overrides and IRI link styles to theme.css** - `c1e0c3a` (feat)

## Files Created/Modified
- `backend/app/browser/router.py` - Added base_namespace to workspace template context from settings
- `backend/app/templates/browser/workspace.html` - Injected SEMPKM_BASE_NAMESPACE global, added isSemPKMObjectIri(), shortenSemPkmIri(), registerYasrFormatter(), and MutationObserver fallback
- `frontend/static/css/theme.css` - Added .sparql-iri-link pill styles and html[data-theme="dark"] .yasgui overrides for all UI components

## Decisions Made
- Used YASR plugins.table.defaults.uriFormatter as primary approach (recommended by Yasgui API docs) with MutationObserver as automatic fallback if the API is unavailable in the CDN build
- IRI pill links use existing accent color tokens (--color-accent, --color-accent-subtle, --color-accent-muted) for visual consistency
- Both BEM-style class names (yasgui__tab, yasr__plugin-control) and legacy names (tab, controlbar, pluginSelector) are targeted in dark mode overrides to handle Yasgui v4.5.0's mixed naming convention

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 23 (SPARQL Console) is now fully complete: Plan 01 delivered Yasgui integration, Plan 02 adds IRI click-through and dark mode
- E2E test coverage for SPARQL console (sparql-console.spec.ts) is deferred to Phase 28 (POLSH-04)
- Phase 24 (FTS Keyword Search) can proceed independently; Phase 28 depends on this phase being complete

## Self-Check: PASSED

All files and commits verified:
- backend/app/browser/router.py: FOUND
- backend/app/templates/browser/workspace.html: FOUND
- frontend/static/css/theme.css: FOUND
- 23-02-SUMMARY.md: FOUND
- Commit 7eabea8: FOUND
- Commit c1e0c3a: FOUND

---
*Phase: 23-sparql-console*
*Completed: 2026-03-01*
