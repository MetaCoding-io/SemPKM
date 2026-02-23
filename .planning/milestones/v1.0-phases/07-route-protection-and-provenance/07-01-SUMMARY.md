---
phase: 07-route-protection-and-provenance
plan: 01
subsystem: auth
tags: [fastapi, exception-handler, htmx, rdf, provenance, redirect]

# Dependency graph
requires:
  - phase: 06-user-and-team-management
    provides: "Auth dependencies (get_current_user, require_role), session cookie auth, magic link login"
provides:
  - "Custom HTTPException handler routing 401/403 to HTML responses for browser routes"
  - "Styled 403 Access Denied error template"
  - "EVENT_PERFORMED_BY_ROLE predicate and SYSTEM_ACTOR_IRI constant"
  - "EventStore.commit() with performed_by_role parameter"
  - "Frontend ?next= redirect-back flow after login"
affects: [07-route-protection-and-provenance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HTML vs API route exception routing via path prefix detection"
    - "HTMX partial error fragments vs full-page redirects"
    - "?next= redirect-back flow for post-login navigation"
    - "Role provenance in RDF event metadata"

key-files:
  created:
    - "backend/app/templates/errors/403.html"
  modified:
    - "backend/app/main.py"
    - "backend/app/events/models.py"
    - "backend/app/events/store.py"
    - "frontend/static/js/auth.js"

key-decisions:
  - "403 template is standalone HTML (not extending base.html) since user may not have sidebar access"
  - "Exception handler checks path prefix /api/ for API vs HTML routing distinction"
  - "HTMX requests detected via HX-Request header for inline error fragments"

patterns-established:
  - "_is_html_route() path-based routing: /api/* = JSON, everything else = HTML"
  - "auth-error CSS class for HTMX inline error fragments"
  - "?next= parameter propagation across all login/verify/invite flows"

requirements-completed: [INT-01, INT-02, INT-03]

# Metrics
duration: 3min
completed: 2026-02-22
---

# Phase 07 Plan 01: Auth Infrastructure Summary

**Custom HTML auth exception handler with 401 redirect, 403 error page, HTMX error fragments, EventStore role provenance, and ?next= redirect-back flow**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-23T04:25:26Z
- **Completed:** 2026-02-23T04:28:24Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Custom HTTPException handler routes 401/403 to HTML-appropriate responses (302 redirects, styled 403 pages, HTMX inline fragments) while preserving JSON responses for API routes
- EventStore.commit() extended with performed_by_role parameter for role provenance in RDF event metadata
- EVENT_PERFORMED_BY_ROLE and SYSTEM_ACTOR_IRI constants added for provenance queries
- Frontend auth.js updated with ?next= redirect-back flow across all login, verify, and invite paths

## Task Commits

Each task was committed atomically:

1. **Task 1: Custom HTML auth exception handler, 403 template, and EventStore extension** - `fd75e22` (feat)
2. **Task 2: Frontend redirect-back flow via ?next= parameter** - `8af1e65` (feat)

## Files Created/Modified
- `backend/app/templates/errors/403.html` - Styled Access Denied page with 403 error code, explanation, and workspace link
- `backend/app/main.py` - Custom auth_exception_handler routing 401/403 to HTML responses for browser routes
- `backend/app/events/models.py` - EVENT_PERFORMED_BY_ROLE predicate and SYSTEM_ACTOR_IRI constant
- `backend/app/events/store.py` - Extended commit() with performed_by_role parameter (backward compatible)
- `frontend/static/js/auth.js` - ?next= redirect-back flow in checkAuthStatus, handleLoginForm, handleVerifyToken, handleInviteAccept

## Decisions Made
- 403 template is standalone HTML rather than extending base.html, since a 403 user may not have sidebar/dashboard access
- Exception handler uses simple /api/ path prefix check for routing distinction (matching existing router structure)
- HTMX requests detected via HX-Request header to return inline error fragments instead of full-page responses

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Auth infrastructure ready for Plan 02 to add Depends(get_current_user) and Depends(require_role) to HTML routes
- Exception handler will automatically convert auth failures to appropriate HTML responses
- EventStore accepts performed_by_role for role-aware provenance tracking

---
*Phase: 07-route-protection-and-provenance*
*Completed: 2026-02-22*

## Self-Check: PASSED

- [x] backend/app/templates/errors/403.html exists
- [x] 07-01-SUMMARY.md exists
- [x] Commit fd75e22 found (Task 1)
- [x] Commit 8af1e65 found (Task 2)
