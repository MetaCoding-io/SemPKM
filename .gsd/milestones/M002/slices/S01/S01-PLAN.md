# S01: Security Hardening

**Goal:** Auth endpoints are rate-limited, magic link tokens stay out of production logs, the event console is owner-only, SPARQL filter text is fully escaped against regex injection, and BASE_NAMESPACE deployment risks are documented.
**Demo:** `POST /api/auth/magic-link` 6× in 60 s returns 429 on the 6th call. Token log line only appears when SMTP is not configured or delivery fails. `/debug/events` returns 403 for non-owner users. A filter search with regex metacharacters like `foo.*bar` executes safely without altering query semantics. Production deployment guide explains BASE_NAMESPACE collision risk.

## Must-Haves

- Per-IP rate limiting on `/api/auth/magic-link` (5/minute) and `/api/auth/verify` (10/minute) via slowapi
- Magic link token logged only when SMTP is not configured OR when SMTP delivery fails (fallback path)
- Event console endpoint requires `require_role("owner")`
- Reusable `escape_sparql_regex()` function in `backend/app/sparql/utils.py` escaping all SPARQL regex metacharacters: `. * + ? ^ $ { } ( ) | [ ] \` plus `"`
- Both `views/service.py` escaping sites replaced with the shared function
- `BASE_NAMESPACE` section added to production deployment guide with IRI collision warning and checklist item

## Proof Level

- This slice proves: contract
- Real runtime required: yes (Docker containers for rate limit and auth testing)
- Human/UAT required: no

## Verification

- `docker compose exec api python -c "from app.sparql.utils import escape_sparql_regex; assert escape_sparql_regex('foo.*bar') == r'foo\\.\\*bar'; print('PASS')"` — escaping function importable and correct
- `rg 'escape_sparql_regex' backend/app/views/service.py` — both call sites use the shared function
- `rg 'logger\.info.*Magic link token' backend/app/auth/router.py` — token log line is inside conditional branch, not at top level
- `grep 'require_role.*owner' backend/app/debug/router.py | wc -l` — returns 2 (both endpoints use owner role)
- `grep 'slowapi' backend/pyproject.toml` — dependency present
- `grep 'limiter.limit' backend/app/auth/router.py | wc -l` — returns 2 (both endpoints decorated)
- `grep 'BASE_NAMESPACE' docs/guide/20-production-deployment.md` — section exists in production guide
- Manual: hit rate-limited endpoint 6× rapidly → 429 on 6th (verified in T01)

## Observability / Diagnostics

- Runtime signals: slowapi returns `429 Too Many Requests` with `Retry-After` header on rate limit hit; auth router logs magic link token only in dev/fallback paths; rate limit state is in-memory (resets on container restart)
- Inspection surfaces: `docker compose logs api | grep "rate limit\|429"` for rate limit events; slowapi default handler returns plaintext 429
- Failure visibility: if rate limiting isn't working, auth endpoints accept unlimited requests — detectable by rapid-fire curl returning 200s instead of 429
- Redaction constraints: magic link tokens must never appear in logs when SMTP is configured and delivery succeeds

## Integration Closure

- Upstream surfaces consumed: `backend/app/auth/router.py` (auth endpoints), `backend/app/debug/router.py` (event console), `backend/app/views/service.py` (SPARQL filter escaping), `backend/app/main.py` (app instance for middleware), `docs/guide/20-production-deployment.md` (deployment docs)
- New wiring introduced in this slice: slowapi `Limiter` instance + `SlowAPIMiddleware` on FastAPI app; `backend/app/sparql/utils.py` new module imported by views service
- What remains before the milestone is truly usable end-to-end: S03 adds unit tests for the escaping function; all other slices are independent

## Tasks

- [x] **T01: Add rate limiting to auth endpoints with slowapi** `est:45m`
  - Why: SEC-01 — auth endpoints have zero rate limiting, allowing brute-force and enumeration attacks
  - Files: `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/auth/router.py`
  - Do: Add slowapi dependency, create limiter instance with `get_remote_address` key func, register `SlowAPIMiddleware` + exception handler on app, decorate `/api/auth/magic-link` (5/min) and `/api/auth/verify` (10/min) with `@limiter.limit()`. Route decorator must be above limiter decorator. Docker rebuild required after pyproject.toml change.
  - Verify: `docker compose exec api python -c "from slowapi import Limiter; print('OK')"` succeeds; curl the magic-link endpoint 6× rapidly → 6th returns HTTP 429
  - Done when: both auth endpoints return 429 when rate limit exceeded, middleware is registered, dependency is in pyproject.toml

- [x] **T02: Conditional token logging, owner-only event console, and SPARQL regex escaping** `est:45m`
  - Why: SEC-02 (token logging), SEC-03 (event console access), SEC-04 (SPARQL escaping) — three small, independent fixes that each touch one file
  - Files: `backend/app/auth/router.py`, `backend/app/debug/router.py`, `backend/app/sparql/utils.py` (new), `backend/app/views/service.py`
  - Do: (1) Move `logger.info("Magic link token…")` inside the `if not smtp_configured:` branch and add it to the SMTP failure fallback. (2) Change event console endpoint from `Depends(get_current_user)` to `Depends(require_role("owner"))`. (3) Create `backend/app/sparql/utils.py` with `escape_sparql_regex()` escaping `\ " . * + ? ^ $ { } ( ) | [ ]`. (4) Replace both inline escaping blocks in `views/service.py` with calls to the shared function.
  - Verify: `rg 'logger\.info.*Magic link token' backend/app/auth/router.py` shows line is inside conditional; `grep require_role backend/app/debug/router.py` shows both endpoints; `docker compose exec api python -c "from app.sparql.utils import escape_sparql_regex; print(escape_sparql_regex('test.*[abc]'))"` outputs properly escaped string; `rg escape_sparql_regex backend/app/views/service.py` shows 2 import usages
  - Done when: token not logged when SMTP works, event console is owner-only, SPARQL filter text fully escaped via shared utility

- [x] **T03: Document BASE_NAMESPACE production guidance** `est:20m`
  - Why: SEC-05 — deployers using the default `example.org` namespace will have IRI collisions across instances with no warning
  - Files: `docs/guide/20-production-deployment.md`
  - Do: Add a "Namespace Configuration" section (before Production Checklist) explaining what BASE_NAMESPACE does, why the default is dangerous in production, and how to set it. Add `BASE_NAMESPACE` to the production checklist. Reference the appendix env var docs.
  - Verify: `grep -c 'BASE_NAMESPACE' docs/guide/20-production-deployment.md` returns ≥3 (section heading, body, checklist item)
  - Done when: production guide has clear BASE_NAMESPACE guidance and checklist item

## Files Likely Touched

- `backend/pyproject.toml`
- `backend/app/main.py`
- `backend/app/auth/router.py`
- `backend/app/debug/router.py`
- `backend/app/sparql/utils.py` (new)
- `backend/app/views/service.py`
- `docs/guide/20-production-deployment.md`
