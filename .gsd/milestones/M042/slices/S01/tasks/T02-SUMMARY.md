---
id: T02
parent: S01
milestone: M042
provides:
  - Complete S01-FINDINGS.md with 20 findings across A01, A03, A07 OWASP categories
  - Systematic auth dependency audit of all 40+ routers
  - IDOR analysis confirming flat authorization model (canvas/dashboard/workflow are user-scoped)
  - CORS wildcard interaction analysis with session cookies and Bearer tokens
  - Session lifecycle assessment (entropy adequate, sliding window, no concurrent limits)
  - Cookie security configuration documented (httponly/samesite/secure flags)
  - API token security assessment (unscoped — full user privileges)
  - Rate limiting coverage map showing gaps beyond auth endpoints
  - Magic link token replay vulnerability documented
  - Federation inbox HTTP Signature verification assessment
key_files:
  - .gsd/milestones/M042/slices/S01/S01-FINDINGS.md
key_decisions:
  - Classified 20 discrete findings (5 A01, 6 A03, 9 A07) with severity ratings for cloud deployment
  - Identified 6 unauthenticated browser/apps endpoints as the easiest-to-fix access control gap
  - Confirmed CORS wildcard is safe for session cookies (SameSite=Lax) but problematic for Bearer tokens
patterns_established:
  - Auth dependency scan pattern: for each include_router in main.py, check every endpoint for Depends(get_current_user) or equivalent
  - Flat authorization vs user-scoped resources: RDF objects are shared, SQL-backed resources (canvas, dashboards, workflows, tokens) are user-scoped
observability_surfaces:
  - none (static analysis artifact, no runtime component)
duration: 40m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Access control gaps + auth/session findings, assemble S01-FINDINGS.md (A01, A07)

**Assembled S01-FINDINGS.md with 20 security findings across A01 (Broken Access Control), A03 (Injection from T01), and A07 (Auth Failures), each with severity ratings, exploit scenarios, affected files, and remediation guidance.**

## What Happened

Systematically audited every FastAPI router for authentication and authorization:

1. **Auth dependency scan:** Enumerated all `include_router` calls in `main.py` (40+ routers) and verified each endpoint's auth dependency. Found 6 unauthenticated endpoints on `browser/apps.py` — the `apps_explorer`, `app_page`, `right_pane_sections`, `views_explorer_apps`, `app_view_tab`, and `commands_list` endpoints all lack `get_current_user`. Intentionally public endpoints (`/api/health`, `/.well-known/webfinger`, `/api/monitoring/config`, `/api/auth/status`, IndieAuth metadata/token/introspect) documented with justification.

2. **IDOR analysis:** Confirmed SemPKM uses a flat authorization model — all RDF objects in `urn:sempkm:current` are shared. SQL-backed resources (canvas, dashboards, workflows, saved queries, API tokens) are properly user-scoped with `user_id` filtering. No IDOR vectors found because the shared model is intentional.

3. **CORS analysis:** nginx adds `Access-Control-Allow-Origin: *` unconditionally on `/api/` responses. The FastAPI middleware also adds `*` when `CORS_ORIGINS` is empty. Session cookies are protected by `SameSite=Lax`, but Bearer tokens can be used cross-origin.

4. **Session/cookie review:** Token generation uses `secrets.token_urlsafe(32)` — 256-bit entropy, adequate. Cookies set `httponly=True`, `samesite="lax"`, `secure=settings.cookie_secure`. Sliding window renewal at 50% of 30-day lifetime. No concurrent session limit. No periodic cleanup.

5. **Magic link analysis:** Tokens signed via `itsdangerous` with 600s expiry but no single-use enforcement — replay within the 10-minute window is possible.

6. **API token review:** SHA-256 hashed storage, revocation via delete, user-scoped listing/deletion. But tokens are unscoped — they inherit full user role privileges.

7. **Rate limiting:** Only on `magic-link` (5/min) and `verify` (10/min). No limits on SPARQL, copilot, commands, or token creation.

8. **Assembly:** Combined all A01/A07 findings with T01's A03 SPARQL triage into the final S01-FINDINGS.md with standardized finding format.

## Verification

All slice-level verification checks pass:
- File exists at expected path
- 20 discrete findings (≥5 required)
- Severity count matches finding count (20 = 20)
- A01, A03, A07 sections all present
- SPARQL Injection Classification table present

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M042/slices/S01/S01-FINDINGS.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "^### F-" S01-FINDINGS.md` (20) | 0 | ✅ pass | <1s |
| 3 | `grep -c "Severity:" S01-FINDINGS.md` (20 = finding count) | 0 | ✅ pass | <1s |
| 4 | `grep -q "## A01" S01-FINDINGS.md` | 0 | ✅ pass | <1s |
| 5 | `grep -q "## A03" S01-FINDINGS.md` | 0 | ✅ pass | <1s |
| 6 | `grep -q "## A07" S01-FINDINGS.md` | 0 | ✅ pass | <1s |
| 7 | `grep -q "SPARQL Injection Classification" S01-FINDINGS.md` | 0 | ✅ pass | <1s |

## Diagnostics

Static analysis artifact — no runtime diagnostics. Review `S01-FINDINGS.md` for the complete findings register. The summary table at the bottom provides a severity breakdown and prioritized remediation list. Each finding includes affected file paths for targeted code review.

## Deviations

- Found 20 findings instead of the estimated ≥5 — the systematic router scan revealed more access control nuances than anticipated
- Setup routes endpoint (`POST /api/setup/configure-instance`) found without auth guard — not mentioned in the plan but material for A01

## Known Issues

None — this is a findings document, not a code change. Remediation is tracked in the findings themselves for future implementation slices.

## Files Created/Modified

- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md` — Complete security findings document with 20 findings across A01 (5), A03 (6), A07 (9) categories
- `.gsd/milestones/M042/slices/S01/S01-PLAN.md` — Marked T02 as complete
