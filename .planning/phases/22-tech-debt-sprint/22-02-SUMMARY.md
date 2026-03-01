---
phase: 22-tech-debt-sprint
plan: 02
subsystem: auth
tags: [smtp, aiosmtplib, email, magic-link, async]

# Dependency graph
requires:
  - phase: none
    provides: existing magic link auth endpoint with TODO stub
provides:
  - async SMTP email delivery service (send_magic_link_email)
  - app_base_url config setting for email link construction
  - graceful SMTP failure fallback to console logging
affects: [auth, deployment, config]

# Tech tracking
tech-stack:
  added: [aiosmtplib]
  patterns: [async email delivery with bool return for graceful fallback]

key-files:
  created: [backend/app/services/email.py]
  modified: [backend/app/auth/router.py, backend/pyproject.toml, backend/app/config.py]

key-decisions:
  - "send_magic_link_email returns bool (not raises) so caller can fall through to console fallback"
  - "Lazy import of email service inside if smtp_configured block (only loaded when needed)"
  - "SMTP failure falls through to console fallback (returns token in response) instead of returning generic 'email sent' message"
  - "app_base_url config setting avoids request.base_url returning internal container URL behind nginx"

patterns-established:
  - "Email service returns bool for success/failure; caller decides fallback behavior"
  - "Lazy import pattern for optional service dependencies"

requirements-completed: [TECH-02]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 22 Plan 02: SMTP Email Delivery Summary

**Async SMTP email delivery for magic link login using aiosmtplib with graceful console fallback on failure**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T02:35:17Z
- **Completed:** 2026-03-01T02:37:11Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created async email service module with send_magic_link_email function
- Replaced TODO stub in magic link endpoint with real SMTP delivery
- Added aiosmtplib dependency and app_base_url config setting
- SMTP failure gracefully falls through to console token logging

## Task Commits

Each task was committed atomically:

1. **Task 1: Create EmailService and add aiosmtplib dependency** - `aed3e3a` (feat)
2. **Task 2: Wire email service into magic link endpoint** - `0337552` (feat)

## Files Created/Modified
- `backend/app/services/email.py` - Async SMTP email delivery service with send_magic_link_email
- `backend/app/auth/router.py` - Magic link endpoint now calls email service when SMTP configured
- `backend/pyproject.toml` - Added aiosmtplib>=3.0 dependency
- `backend/app/config.py` - Added app_base_url setting for email link URL construction

## Decisions Made
- send_magic_link_email returns bool (not raises) so the caller can fall through to console fallback on failure
- Lazy import of email service inside the if smtp_configured block (module only loaded when SMTP is configured)
- On SMTP failure, endpoint falls through to console fallback (returns token in response) rather than returning a misleading "email sent" message
- app_base_url config setting resolves the pitfall where request.base_url returns internal container URL (http://api:8000) instead of public URL behind nginx
- username/password set to None (not empty string) when not configured, telling aiosmtplib to skip authentication
- start_tls=True for TLS negotiation on port 587 (standard submission port)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- aiosmtplib and pydantic_settings not installed in local host Python environment (Docker-deployed app) -- verification adapted to use AST parsing instead of runtime imports

## User Setup Required

None - no external service configuration required. SMTP settings are optional; when not configured, magic link tokens continue to be logged to console.

## Next Phase Readiness
- Email delivery infrastructure complete for magic links
- Same email service pattern can be extended for invitation emails
- SMTP configuration is opt-in; local development workflow unchanged

## Self-Check: PASSED

All 5 files verified present. Both task commits (aed3e3a, 0337552) verified in git log.

---
*Phase: 22-tech-debt-sprint*
*Completed: 2026-03-01*
