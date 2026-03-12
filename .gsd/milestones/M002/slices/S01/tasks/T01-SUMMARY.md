---
id: T01
parent: S01
milestone: M002
provides:
  - per-IP rate limiting on auth endpoints via slowapi
key_files:
  - backend/app/auth/rate_limit.py
  - backend/app/auth/router.py
  - backend/app/main.py
  - backend/pyproject.toml
key_decisions:
  - Limiter instance in a dedicated module (app.auth.rate_limit) rather than inline in router.py, so main.py can import it for state/middleware registration without circular imports
patterns_established:
  - slowapi rate limiting pattern: Limiter in shared module → decorator on router endpoints → state + middleware + exception handler in main.py
observability_surfaces:
  - HTTP 429 responses with Retry-After header on rate limit exceeded
  - slowapi logs rate limit events at WARNING level in API container logs
duration: 10min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Add rate limiting to auth endpoints with slowapi

**Added per-IP rate limiting (5/min magic-link, 10/min verify) using slowapi with in-memory storage.**

## What Happened

1. Added `slowapi>=0.1.9` to `backend/pyproject.toml` dependencies
2. Created `backend/app/auth/rate_limit.py` with a shared `Limiter` instance using `get_remote_address` as the key function (reads client IP from `X-Forwarded-For`, which nginx already forwards)
3. In `backend/app/auth/router.py`: imported the limiter, added `@limiter.limit("5/minute")` to `request_magic_link` and `@limiter.limit("10/minute")` to `verify_token` — route decorators are above limiter decorators as required
4. In `backend/app/main.py`: imported slowapi components, set `app.state.limiter`, added `SlowAPIMiddleware`, registered `_rate_limit_exceeded_handler` for `RateLimitExceeded` exceptions
5. Rebuilt the Docker API container and verified rate limiting works both directly (port 8001) and through nginx (port 3000)

## Verification

- `docker compose exec api python -c "from slowapi import Limiter; print('OK')"` → OK
- `grep 'slowapi' backend/pyproject.toml` → `"slowapi>=0.1.9"` present
- `grep -c 'limiter.limit' backend/app/auth/router.py` → 2
- Rapid-fire curl test (7× POST to `/api/auth/magic-link`): requests 1-5 return HTTP 200, requests 6-7 return HTTP 429 ✓
- Same test through nginx proxy (port 3000): identical results ✓

### Slice-level verification status (T01)

| Check | Result |
|-------|--------|
| `grep 'slowapi' backend/pyproject.toml` | ✅ PASS |
| `grep 'limiter.limit' backend/app/auth/router.py \| wc -l` → 2 | ✅ PASS |
| escape_sparql_regex importable and correct | ⬜ Future (T04) |
| escape_sparql_regex used in views/service.py | ⬜ Future (T04) |
| Token log line conditional | ⬜ Future (T02) |
| require_role owner on debug endpoints | ⬜ Future (T03) |
| BASE_NAMESPACE in production guide | ⬜ Future (T05) |

## Diagnostics

- **Rate limit active?** `curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"email":"test@example.com"}' http://localhost:8001/api/auth/magic-link` — repeat 6× rapidly, 6th should return 429
- **Server-side events:** `docker compose logs api | grep -i "rate limit"` for rate limit log entries
- **State resets on container restart** (in-memory storage, no persistence)

## Deviations

- Created a dedicated `backend/app/auth/rate_limit.py` module for the `Limiter` instance rather than defining it inline in `router.py`. This avoids circular imports since both `router.py` (decorators) and `main.py` (state/middleware) need the same instance.

## Known Issues

- Rate limit counters are in-memory and reset on container restart. Acceptable for single-instance deployment; would need Redis backend for multi-replica scaling.

## Files Created/Modified

- `backend/pyproject.toml` — added `slowapi>=0.1.9` dependency
- `backend/app/auth/rate_limit.py` — **new** — shared Limiter instance with `get_remote_address` key function
- `backend/app/auth/router.py` — imported limiter, added `@limiter.limit()` decorators to magic-link (5/min) and verify (10/min) endpoints
- `backend/app/main.py` — imported slowapi components, registered limiter state, middleware, and exception handler
