# T01: 19-bug-fixes-and-e2e-test-hardening 01

**Slice:** S19 — **Milestone:** M001

## Description

Fix all backend bugs from the CONCERNS.md audit: EventStore DI, label cache invalidation, datetime UTC, CORS misconfiguration, cookie secure env var, debug endpoint auth guard, and IRI validation.

Purpose: These are correctness and security bugs in the backend that affect data integrity (stale labels, wrong timestamps), session security (cookie), API safety (CORS, IRI injection), and access control (debug endpoints). None are new features — all are hardening of existing behavior.
Output: Cleaned `browser/router.py` with DI-injected EventStore, label cache invalidation after every commit, UTC datetimes; `config.py` with CORS_ORIGINS and COOKIE_SECURE env vars; `main.py` with conditional CORS; `auth/router.py` using settings.cookie_secure; `debug/router.py` with require_role("owner"); IRI validation helper applied at all 6 SPARQL interpolation points.

## Must-Haves

- [ ] "After any write (save body, create object, patch object, undo), label cache is immediately invalidated for the affected IRIs — stale labels do not persist after rename"
- [ ] "All timestamps written to the triplestore from browser router use UTC — consistent with EventStore timestamps"
- [ ] "EventStore is injected via FastAPI DI in all 4 write handlers — no ad-hoc EventStore(client) constructions remain"
- [ ] "CORS config does not combine allow_origins='*' with allow_credentials=True — CORS_ORIGINS env var controls origins"
- [ ] "COOKIE_SECURE env var controls session cookie secure flag — default True for production safety"
- [ ] "/sparql and /commands debug pages require owner role — non-owner authenticated users receive 403"
- [ ] "Decoded IRIs are validated as absolute URIs before SPARQL interpolation — malformed IRIs return 400"

## Files

- `backend/app/dependencies.py`
- `backend/app/browser/router.py`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/auth/router.py`
- `backend/app/debug/router.py`
