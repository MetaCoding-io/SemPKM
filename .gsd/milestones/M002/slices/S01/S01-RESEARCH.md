# S01: Security Hardening — Research

**Date:** 2026-03-12

## Summary

S01 covers five security requirements (SEC-01 through SEC-05) targeting auth rate limiting, token logging, event console access control, SPARQL regex escaping, and deployment documentation. All five changes are well-scoped, low-coupling, and can be completed in a single task context window.

The auth endpoints (`/api/auth/magic-link` and `/api/auth/verify`) have zero rate limiting today. Magic link tokens are logged unconditionally via `logger.info` at `auth/router.py:133` regardless of SMTP configuration. The event console at `debug/router.py:21` uses `get_current_user` while its neighbor the SPARQL console already uses `require_role("owner")`. SPARQL filter text escaping in `views/service.py` only handles `\` and `"` — not the full set of SPARQL regex metacharacters. `BASE_NAMESPACE` documentation exists in the env var appendix but lacks explicit production guidance about IRI collision risks.

All five changes are leaf-node modifications with no cross-slice dependencies. The SPARQL escaping function should be extracted as a reusable utility since S03 will write unit tests against it.

## Recommendation

**Use slowapi for rate limiting (SEC-01).** It's the standard FastAPI rate limiting library (trust 9.4/10 on Context7), wraps flask-limiter's battle-tested algorithm, supports per-route decorators and in-memory storage. No need for Redis — the in-memory backend is fine for a single-instance app. Apply `@limiter.limit()` decorators to the two auth endpoints specifically, not as global middleware.

**Conditional logging for SEC-02.** Move the `logger.info("Magic link token for %s: %s", ...)` line inside the `if not smtp_configured:` branch. When SMTP is configured and delivery succeeds, the token should never appear in logs.

**One-line fix for SEC-03.** Change `Depends(get_current_user)` to `Depends(require_role("owner"))` on the event console endpoint in `debug/router.py`.

**Extract a reusable `escape_sparql_regex()` function for SEC-04.** Place it in `backend/app/sparql/utils.py` (new file) so both `views/service.py` call sites can use it, and S03 can unit-test it. The function must escape all SPARQL regex metacharacters: `\ " . * + ? ^ $ { } ( ) | [ ]`.

**Add a BASE_NAMESPACE section to Chapter 20 for SEC-05.** The production deployment guide already exists at `docs/guide/20-production-deployment.md` and has a production checklist. Add a subsection explaining the IRI collision risk and add `BASE_NAMESPACE` to the checklist.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Per-IP rate limiting on FastAPI endpoints | slowapi (`pip install slowapi`) | Battle-tested (wraps flask-limiter), supports per-route decorators, in-memory or Redis backends, handles `X-Forwarded-For` via `get_remote_address` |
| Signed token creation/verification | itsdangerous (already installed) | Already used in `auth/tokens.py` — no new dependency needed |
| SPARQL regex escaping | `re.escape()` pattern (stdlib) | Python's `re.escape` covers most metacharacters; adapt for SPARQL REGEX syntax differences |

## Existing Code and Patterns

- `backend/app/auth/router.py` — Lines 129-135: unconditional `logger.info` of magic link token. The fix point is clear — wrap in `if not smtp_configured:`. Lines 128-144 also show the SMTP detection logic already in place (`smtp_configured = bool(settings.smtp_host)`).
- `backend/app/debug/router.py` — Two endpoints: `/sparql` (line 12, uses `require_role("owner")`) and `/events` (line 21, uses `get_current_user`). The SPARQL console is the reference pattern for the event console fix.
- `backend/app/views/service.py` — Two identical escaping blocks at lines 363 and 516: `escaped = filter_text.replace("\\", "\\\\").replace('"', '\\"')`. Only escapes backslash and double-quote. Must be replaced with comprehensive regex escaping.
- `backend/app/main.py` — Lines 416-462: middleware and router registration. slowapi middleware and exception handler wire in here. The `app` object is created at line ~410. `app.state.limiter` pattern is standard.
- `frontend/nginx.conf` — Lines 48-53: `/api/` proxy already passes `X-Forwarded-For` via `proxy_add_x_forwarded_for`. This means `slowapi.util.get_remote_address` will see the real client IP, not the nginx container IP.
- `backend/app/config.py` — `base_namespace` default is `https://example.org/data/`. No production validation or warning exists.
- `docs/guide/20-production-deployment.md` — Existing production guide with a checklist at the bottom. `BASE_NAMESPACE` is not mentioned. The appendix (`appendix-a-environment-variables.md`) documents the variable but doesn't explain the IRI collision risk.
- `backend/app/auth/dependencies.py` — `require_role(*roles)` factory is already imported in `debug/router.py` (line 5) but not used on the event console endpoint.

## Constraints

- **No Redis required.** slowapi's in-memory storage is sufficient for a single-instance app. Don't introduce a new infrastructure dependency.
- **slowapi must be added to `pyproject.toml` dependencies.** Currently not installed. S05 will pin versions later, so use `>=0.1.9` floor for now (consistent with existing dependency style).
- **nginx already forwards X-Forwarded-For.** The `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` directive is set on all proxy locations. slowapi's `get_remote_address` will correctly extract client IP.
- **The limiter must be set on `app.state.limiter`** and `SlowAPIMiddleware` added, but only the two auth endpoints need `@limiter.limit()` decorators — no global default_limits.
- **SPARQL escaping must handle SPARQL REGEX semantics.** SPARQL uses XPath/XQuery-style regex (similar to Perl). Metacharacters: `. * + ? ^ $ { } ( ) | [ ] \`. The double-quote also needs escaping for the SPARQL string literal wrapper.
- **The escape function must be importable from a standalone module** so S03 can test it without importing the full views service.
- **Docker rebuild required** after adding slowapi to `pyproject.toml`.

## Common Pitfalls

- **slowapi decorator order matters.** The route decorator (`@router.post(...)`) must be above the limiter decorator (`@limiter.limit(...)`), not below. The docs are explicit about this. FastAPI's `APIRouter` works identically to `FastAPI` app for this purpose.
- **slowapi on APIRouter, not just FastAPI app.** slowapi works with `APIRouter` endpoints but the `Limiter` instance and middleware must be registered on the `FastAPI` app. The limiter can be imported from a shared module and used as a decorator on any router's endpoints.
- **Rate limit response format.** slowapi's default `_rate_limit_exceeded_handler` returns a `PlainTextResponse` with status 429. For the auth endpoints (JSON API), consider a custom handler that returns JSON `{"detail": "Rate limit exceeded"}` for consistency. However, the default handler is acceptable for an MVP — the status code 429 is what matters.
- **Token logging fix must handle SMTP failure fallback.** The current code has a fallback path: if SMTP is configured but delivery fails, it logs a warning and falls through to return the token directly. The token log line should fire in this fallback path too (user needs the token somehow). The fix is: move the `logger.info` from before the SMTP check to inside the `if not smtp_configured:` branch AND inside the SMTP failure fallback.
- **SPARQL regex vs Python regex.** SPARQL REGEX uses XPath syntax which is similar but not identical to Python regex. The key metacharacters to escape are the same set, but the escaping must produce valid SPARQL string content (double-quote and backslash escaping for the SPARQL string literal, plus regex metacharacter escaping for the regex engine).

## Open Risks

- **Rate limiting state lost on container restart.** In-memory storage means rate limit counters reset when the API container restarts. This is acceptable for the current single-instance deployment but should be noted. If the app ever scales to multiple workers/replicas, a shared backend (Redis/memcached) will be needed.
- **`get_remote_address` behind double proxy.** If someone deploys with an additional reverse proxy in front of nginx (e.g., Cloudflare → nginx → API), the `X-Forwarded-For` chain may have multiple IPs. slowapi's `get_remote_address` reads the first entry, which should be the client IP if proxies are configured correctly. This is a deployment concern, not a code concern.
- **Event console route overlap.** The debug router mounts `/events` and the browser router also mounts `/browser/events`. These are different prefixes so no conflict, but verify during implementation that the debug `/events` path doesn't collide with any browser router path.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | `wshobson/agents@fastapi-templates` (6.1K installs) | available — general FastAPI patterns |
| FastAPI | `fastapi/fastapi@fastapi` (343 installs) | available — official repo skill |
| slowapi | none found | N/A — library is simple enough; Context7 docs sufficient |

No skills are directly relevant enough to warrant installation for this slice. The work is straightforward library integration and code modifications, well-covered by the slowapi Context7 docs already retrieved.

## Sources

- slowapi integration pattern: per-route `@limiter.limit()` with `get_remote_address` key func, `SlowAPIMiddleware`, exception handler (source: [Context7 slowapi docs](/laurents/slowapi))
- SPARQL regex metacharacters: `. * + ? ^ $ { } ( ) | [ ] \` — same as XPath/XQuery regex (source: [SPARQL 1.1 spec, section 17.4.3.14](https://www.w3.org/TR/sparql11-query/#func-regex))
- Existing production deployment guide already covers HTTPS, firewall, PostgreSQL, but not `BASE_NAMESPACE` (source: `docs/guide/20-production-deployment.md`)
