---
estimated_steps: 5
estimated_files: 15
skills_used:
  - review
  - best-practices
---

# T02: Access control gaps + auth/session findings, assemble S01-FINDINGS.md (A01, A07)

**Slice:** S01 — Injection, Access Control & Authentication Findings (A01, A03, A07)
**Milestone:** M042

## Description

Systematically scan all FastAPI routers for access control gaps (missing auth dependencies, missing role checks, IDOR vectors) and review the authentication/session management subsystem for weaknesses. Then assemble the final S01-FINDINGS.md combining these A01/A07 findings with T01's A03 injection triage.

## Steps

1. **Systematic auth dependency scan (A01)** — For every `include_router` call in `backend/app/main.py`, open the corresponding router module and verify:
   - Every endpoint has `Depends(get_current_user)` or `Depends(require_role(...))` or `Depends(get_current_user_or_api)`
   - Document any endpoint that lacks auth (intentionally public endpoints like `/api/health` are fine if documented; undocumented gaps are findings)
   - Check that `indieauth_public_router` endpoints are genuinely safe to expose unauthenticated
   - Check federation inbox POST endpoint — it uses `Depends(VerifyHTTPSignature())` but is this sufficient?
   - Check the `_is_html_route()` function for routes that should return JSON 401 but aren't excluded

2. **IDOR and authorization analysis (A01)** — Review object-access endpoints:
   - `GET /browser/objects/{iri}` — does it check object ownership or just authentication?
   - Canvas endpoints — can user A access user B's canvas?
   - Saved queries — ownership check on update/delete?
   - Dashboard/workflow CRUD — ownership validation?
   - SPARQL `all_graphs` — does role check prevent member from accessing event/admin graphs?
   - Document the CORS `Access-Control-Allow-Origin: *` finding: interaction with session cookies (SameSite=Lax mitigates cross-origin cookie sending for most methods, but what about Bearer tokens from any origin?)

3. **Session and cookie security (A07)** — Review:
   - Session token generation: entropy source, length, collision resistance
   - Session expiry: is it enforced server-side? Can expired sessions be used?
   - Concurrent sessions: are they limited? Can a stolen token be used alongside the legitimate one?
   - Cookie flags: httponly, secure, samesite — verify the actual code matches documented behavior
   - `cookie_secure: bool = True` default but `COOKIE_SECURE=false` for local dev — is this clearly documented?
   - Magic link token: lifecycle (generation, single-use enforcement, expiry), rate limiting adequacy
   - Demo mode: `settings.demo_mode` bypass — what exactly does it bypass and is it safe?

4. **API token and rate limiting (A07)** — Review:
   - API token creation, storage (SHA-256 hashed), revocation
   - Token scope: are API tokens scoped or do they grant full user access?
   - Rate limiting coverage: which endpoints have rate limits beyond auth routes?
   - Credential enumeration: does the login/magic-link flow reveal whether an email exists?

5. **Assemble S01-FINDINGS.md** — Create the final findings document:
   - Read T01's SPARQL triage output from `.gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md`
   - Structure: `## A01: Broken Access Control` findings, `## A03: Injection` findings (from T01), `## A07: Identification and Authentication Failures` findings
   - Each finding formatted as: `### F-NNN: Title` with Severity, OWASP Category, Exploit Scenario, Affected Files, Remediation, and Localhost Mitigation (where severity differs for local-only deployment)
   - Include the SPARQL Injection Classification summary table from T01
   - Write to `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md`

## Must-Haves

- [ ] Every router's auth dependency status documented (protected / intentionally public / gap)
- [ ] IDOR analysis for object, canvas, query, dashboard, workflow endpoints
- [ ] CORS wildcard finding with exploit scenario
- [ ] Session lifecycle assessment (entropy, expiry, revocation, concurrency)
- [ ] Cookie security flags documented with any gaps
- [ ] API token security assessment
- [ ] Rate limiting coverage documented
- [ ] S01-FINDINGS.md assembled with A01 + A03 (from T01) + A07 sections
- [ ] Every finding has severity, OWASP mapping, exploit scenario, affected files, remediation

## Verification

- `test -f .gsd/milestones/M042/slices/S01/S01-FINDINGS.md`
- `grep -c "^### F-" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md` returns >= 5
- `grep -q "## A01" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md`
- `grep -q "## A03" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md`
- `grep -q "## A07" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md`
- `grep -q "SPARQL Injection Classification" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md`

## Inputs

- `.gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md` — T01's SPARQL injection classification and non-SPARQL injection findings
- `backend/app/main.py` — all `include_router` calls, `_is_html_route()`, Jinja2 config, middleware stack
- `backend/app/auth/dependencies.py` — `get_current_user`, `get_current_user_or_api`, `require_role`, `optional_current_user`
- `backend/app/auth/router.py` — login flow, cookie setting, magic link, rate limiting
- `backend/app/auth/models.py` — User, UserSession, ApiToken models
- `backend/app/auth/service.py` — session creation, token generation, expiry logic
- `backend/app/config.py` — `cookie_secure`, `demo_mode`, `session_duration_days`, security-relevant settings
- `backend/app/auth/rate_limit.py` — rate limiter configuration
- `frontend/nginx.conf` — CORS headers, proxy configuration
- `backend/app/federation/inbox.py` — federation inbox auth (HTTP Signatures)
- `backend/app/indieauth/router.py` — public IndieAuth endpoints
- `backend/app/browser/objects.py` — object access patterns (IDOR check)
- `backend/app/canvas/router.py` — canvas access patterns
- `backend/app/sparql/router.py` — SPARQL role enforcement, `all_graphs` check

## Expected Output

- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md` — complete findings for A01, A03, A07 with severity ratings, exploit scenarios, affected files, and remediation guidance
