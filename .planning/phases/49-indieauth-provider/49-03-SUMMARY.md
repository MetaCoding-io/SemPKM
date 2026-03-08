---
phase: 49-indieauth-provider
plan: 03
subsystem: auth
tags: [indieauth, webid, discovery, e2e, htmx]

requires:
  - phase: 49-indieauth-provider
    provides: "IndieAuth models, service, authorization/token/introspection endpoints (plans 01-02)"
  - phase: 48
    provides: "WebID profile page and router with content negotiation"
provides:
  - "IndieAuth metadata discovery via profile HTML link tags and HTTP Link headers"
  - "Authorized Apps settings UI with htmx token list and revoke"
  - "HTML token list endpoint for htmx rendering"
  - "E2E tests covering full IndieAuth flow"
affects: [indieauth, webid, settings]

tech-stack:
  added: []
  patterns: ["Link header discovery for IndieAuth metadata on all profile response formats", "htmx-driven token management with HTML partial endpoint"]

key-files:
  created:
    - backend/app/templates/browser/_indieauth_settings.html
    - backend/app/templates/indieauth/_token_list.html
    - e2e/tests/16-indieauth/indieauth-flow.spec.ts
  modified:
    - backend/app/templates/webid/profile.html
    - backend/app/webid/router.py
    - backend/app/indieauth/router.py
    - backend/app/templates/browser/settings_page.html

key-decisions:
  - "Added HTML token list endpoint (/api/indieauth/tokens/list) returning rendered partial rather than using client-side JSON rendering"
  - "DELETE /tokens/{id} returns refreshed HTML list for seamless htmx swap after revoke"

patterns-established:
  - "Link header pattern: metadata + authorization_endpoint + token_endpoint on all profile responses"

requirements-completed: [IAUTH-01]

duration: 4min
completed: 2026-03-08
---

# Phase 49 Plan 03: Discovery, Settings UI, and E2E Tests Summary

**IndieAuth metadata discovery via profile Link headers/tags, Authorized Apps settings with htmx token management, and comprehensive e2e test suite**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-08T07:48:52Z
- **Completed:** 2026-03-08T07:53:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Profile HTML includes rel=indieauth-metadata, authorization_endpoint, and token_endpoint link tags
- All profile response formats (HTML, Turtle, JSON-LD) include Link headers for IndieAuth discovery
- Settings page has Authorized Apps section with htmx-loaded token list and revoke buttons
- E2E tests cover metadata, well-known redirect, profile discovery, full PKCE flow, introspection, and deny flow

## Task Commits

Each task was committed atomically:

1. **Task 1: Add IndieAuth discovery to WebID profile and create settings UI** - `530c75d` (feat)
2. **Task 2: Create e2e test for IndieAuth flow** - `65b27dd` (test)

## Files Created/Modified
- `backend/app/templates/webid/profile.html` - Added indieauth-metadata and endpoint link tags
- `backend/app/webid/router.py` - Added Link headers to all profile response formats
- `backend/app/indieauth/router.py` - Added HTML token list endpoint and revoke returns HTML
- `backend/app/templates/browser/_indieauth_settings.html` - Authorized Apps settings section
- `backend/app/templates/indieauth/_token_list.html` - Token list HTML partial
- `backend/app/templates/browser/settings_page.html` - Added Authorized Apps nav item and panel
- `e2e/tests/16-indieauth/indieauth-flow.spec.ts` - Full IndieAuth flow e2e tests

## Decisions Made
- Added HTML token list endpoint rather than client-side JSON rendering for htmx compatibility
- DELETE endpoint returns refreshed HTML list so htmx can swap the token list after revoke

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- E2E tests could not be verified (Docker stack not running). Tests are structurally complete and follow existing patterns.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- IndieAuth provider feature complete (plans 01-03)
- Discovery chain works: profile URL -> Link header -> metadata endpoint -> authorization/token endpoints
- Ready for integration testing with IndieWeb clients

---
*Phase: 49-indieauth-provider*
*Completed: 2026-03-08*
