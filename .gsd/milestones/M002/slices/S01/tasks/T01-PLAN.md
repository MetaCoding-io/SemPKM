---
estimated_steps: 5
estimated_files: 3
---

# T01: Add rate limiting to auth endpoints with slowapi

**Slice:** S01 — Security Hardening
**Milestone:** M002

## Description

Add per-IP rate limiting to the two auth endpoints (`/api/auth/magic-link` and `/api/auth/verify`) using slowapi. This prevents brute-force token guessing and email enumeration attacks. The limiter uses in-memory storage (no Redis) and `get_remote_address` for client IP extraction (nginx already forwards `X-Forwarded-For`).

## Steps

1. Add `slowapi>=0.1.9` to `backend/pyproject.toml` dependencies (use `>=` floor consistent with existing dep style — S05 will pin later)
2. Create a `Limiter` instance in `backend/app/auth/router.py` (or a shared module) using `get_remote_address` as the key function, with no global default limits
3. In `backend/app/main.py`: set `app.state.limiter = limiter`, add `SlowAPIMiddleware` to the app, register `_rate_limit_exceeded_handler` as the exception handler for `RateLimitExceeded`
4. Decorate the `request_magic_link` endpoint with `@limiter.limit("5/minute")` and the `verify_magic_link` endpoint with `@limiter.limit("10/minute")`. Ensure the `@router.post(...)` decorator is ABOVE the `@limiter.limit(...)` decorator. Both endpoint functions must accept a `request: Request` parameter (already present).
5. Rebuild Docker containers (`docker compose build api`) and verify: curl the magic-link endpoint 6× in rapid succession → the 6th request returns HTTP 429

## Must-Haves

- [ ] `slowapi>=0.1.9` in pyproject.toml
- [ ] `Limiter` instance created with `get_remote_address` key function
- [ ] `app.state.limiter` set and `SlowAPIMiddleware` registered on the FastAPI app
- [ ] `RateLimitExceeded` exception handler registered
- [ ] `/api/auth/magic-link` limited to 5/minute
- [ ] `/api/auth/verify` limited to 10/minute
- [ ] Route decorator above limiter decorator on both endpoints

## Verification

- `docker compose exec api python -c "from slowapi import Limiter; print('OK')"` — slowapi installed
- `grep 'slowapi' backend/pyproject.toml` — dependency present
- `grep -c 'limiter.limit' backend/app/auth/router.py` — returns 2
- Rapid-fire curl test: 6× POST to `/api/auth/magic-link` → 6th returns 429

## Observability Impact

- Signals added/changed: HTTP 429 responses with `Retry-After` header on rate limit exceeded; slowapi logs rate limit events at WARNING level
- How a future agent inspects this: `curl -s -o /dev/null -w "%{http_code}" -X POST ...` to check if rate limiting is active; `docker compose logs api | grep -i "rate limit"` for server-side events
- Failure state exposed: if rate limiting is misconfigured, repeated rapid requests all return 200/422 instead of 429

## Inputs

- `backend/app/auth/router.py` — existing auth endpoints with `Request` parameter already available
- `backend/app/main.py` — middleware registration section (lines ~420-440)
- `frontend/nginx.conf` — confirms `X-Forwarded-For` is already forwarded (no changes needed)
- S01-RESEARCH.md — slowapi integration pattern and decorator order requirement

## Expected Output

- `backend/pyproject.toml` — slowapi dependency added
- `backend/app/main.py` — limiter state + middleware + exception handler registered
- `backend/app/auth/router.py` — both endpoints decorated with rate limits
