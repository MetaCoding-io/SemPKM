---
id: T02
parent: S01
milestone: M002
provides:
  - conditional token logging (tokens only logged when SMTP unconfigured or delivery fails)
  - owner-only event console endpoint
  - reusable escape_sparql_regex() function for SPARQL filter injection prevention
key_files:
  - backend/app/auth/router.py
  - backend/app/debug/router.py
  - backend/app/sparql/utils.py
  - backend/app/views/service.py
key_decisions:
  - escape_sparql_regex placed in app.sparql.utils (not in views/service.py) for reuse by any future SPARQL filter code
patterns_established:
  - SPARQL regex escaping via shared utility instead of inline .replace() chains
observability_surfaces:
  - "Token leak detection: `docker compose logs api | grep 'Magic link token'` should show tokens only when SMTP is not configured"
  - "Event console access: non-owner users get 403 on /debug/events"
duration: 8 minutes
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Conditional token logging, owner-only event console, and SPARQL regex escaping

**Moved magic link token logging inside conditional branches, restricted event console to owners, and extracted SPARQL regex escaping into a shared utility.**

## What Happened

Three independent security fixes:

1. **SEC-02 — Conditional token logging:** Removed the unconditional `logger.info("Magic link token ...")` line from `request_magic_link()`. Added it in two conditional paths only: (a) inside `if not sent:` when SMTP delivery fails, and (b) inside `if not smtp_configured:` for local dev. When SMTP is configured and delivery succeeds, no token appears in logs.

2. **SEC-03 — Owner-only event console:** Changed the `/events` endpoint dependency from `get_current_user` to `require_role("owner")`. Both debug endpoints (`/sparql` and `/events`) now require the owner role.

3. **SEC-04 — SPARQL regex escaping:** Created `backend/app/sparql/utils.py` with `escape_sparql_regex()` that escapes all 14 SPARQL regex metacharacters (`\ " . * + ? ^ $ { } ( ) | [ ]`) in the correct order (backslash first). Replaced both inline `.replace()` chains in `views/service.py` with calls to the shared function.

## Verification

- `rg -n 'logger.info.*Magic link token' backend/app/auth/router.py` — lines 142 and 150, both inside conditional blocks (3-indent under `if not sent:` and 2-indent under `if not smtp_configured:`)
- `grep -c 'require_role.*owner' backend/app/debug/router.py` — returns 2
- `python3 -c "from app.sparql.utils import escape_sparql_regex; assert escape_sparql_regex(r'foo.*[bar]+(x)') == r'foo\.\*\[bar\]\+\(x\)'; print('PASS')"` — PASS
- `rg 'escape_sparql_regex' backend/app/views/service.py` — 1 import + 2 call sites
- `rg 'filter_text\.replace' backend/app/views/service.py` — no matches (inline escaping removed)
- Slice-level checks: slowapi present, limiter decorators count=2, require_role owner count=2 — all pass
- T03 check (BASE_NAMESPACE docs) — not yet, expected

## Diagnostics

- **Token leak detection:** `docker compose logs api | grep "Magic link token"` — should only show tokens in dev (no SMTP) or SMTP failure scenarios
- **Event console access control:** Authenticate as a member user and `GET /debug/events` — should return 403
- **SPARQL escaping:** Import and test: `python3 -c "from app.sparql.utils import escape_sparql_regex; print(escape_sparql_regex('test.*input'))"`

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/auth/router.py` — moved token logger.info into conditional branches (SMTP failure and no-SMTP paths)
- `backend/app/debug/router.py` — changed event console dependency from get_current_user to require_role("owner")
- `backend/app/sparql/utils.py` — new file with escape_sparql_regex() function
- `backend/app/views/service.py` — added import and replaced 2 inline escaping blocks with escape_sparql_regex()
