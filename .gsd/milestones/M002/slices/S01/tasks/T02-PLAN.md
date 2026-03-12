---
estimated_steps: 5
estimated_files: 4
---

# T02: Conditional token logging, owner-only event console, and SPARQL regex escaping

**Slice:** S01 — Security Hardening
**Milestone:** M002

## Description

Three independent security fixes bundled into one task since each is small and touches a different file:
1. **SEC-02:** Move the magic link token log line inside the `if not smtp_configured:` branch (and the SMTP failure fallback) so tokens never appear in production logs when email delivery succeeds.
2. **SEC-03:** Change the event console endpoint from `get_current_user` to `require_role("owner")` to match the SPARQL console's access control.
3. **SEC-04:** Create a reusable `escape_sparql_regex()` function in `backend/app/sparql/utils.py` and replace both inline escaping blocks in `views/service.py` with calls to it.

## Steps

1. In `backend/app/auth/router.py`: remove the unconditional `logger.info("Magic link token for %s: %s", body.email, token)` line. Add it inside the `if not smtp_configured:` branch (before the response return). Also add it inside the SMTP failure fallback path (the `if not sent:` branch) so the token is still available when delivery fails.
2. In `backend/app/debug/router.py`: change `user: User = Depends(get_current_user)` to `user: User = Depends(require_role("owner"))` on the `event_console_page` endpoint. Update the docstring. `require_role` is already imported on line 5.
3. Create `backend/app/sparql/utils.py` with an `escape_sparql_regex(text: str) -> str` function. It must escape all SPARQL regex metacharacters in order: first `\` (to `\\`), then `"` (to `\"`), then each of `. * + ? ^ $ { } ( ) | [ ]`. Return the escaped string.
4. In `backend/app/views/service.py`: import `escape_sparql_regex` from `app.sparql.utils`. Replace both inline escaping blocks (`escaped = filter_text.replace("\\", "\\\\").replace('"', '\\"')` at ~line 363 and ~line 516) with `escaped = escape_sparql_regex(filter_text)`.
5. Verify all three changes: check log line placement, check debug router dependency, import and test the escape function, confirm views/service.py uses it.

## Must-Haves

- [ ] Token `logger.info` line only executes when SMTP is not configured OR when SMTP delivery fails
- [ ] Token `logger.info` line does NOT execute before the SMTP check or when SMTP delivery succeeds
- [ ] Event console endpoint uses `require_role("owner")`
- [ ] `backend/app/sparql/utils.py` exists with `escape_sparql_regex()` function
- [ ] Function escapes all 14 metacharacters: `\ " . * + ? ^ $ { } ( ) | [ ]`
- [ ] Both `views/service.py` call sites use the shared function instead of inline escaping

## Verification

- `rg -n 'logger\.info.*Magic link token' backend/app/auth/router.py` — line appears only inside conditional branches (indented under `if not smtp_configured` and `if not sent`)
- `grep -c 'require_role.*owner' backend/app/debug/router.py` — returns 2
- `docker compose exec api python -c "from app.sparql.utils import escape_sparql_regex; assert escape_sparql_regex(r'foo.*[bar]+(x)') == r'foo\\.\\*\\[bar\\]\\+\\(x\\)'; print('PASS')"` — escaping works
- `rg 'escape_sparql_regex' backend/app/views/service.py` — shows import and 2 call sites
- `rg 'filter_text\.replace' backend/app/views/service.py` — returns no matches (inline escaping removed)

## Observability Impact

- Signals added/changed: magic link token no longer appears in production logs when SMTP succeeds — reduces exposure of sensitive auth material; event console now returns 403 for non-owners instead of rendering the page
- How a future agent inspects this: `docker compose logs api | grep "Magic link token"` should show tokens only in dev environments (SMTP unconfigured); test access control by authenticating as a member user and hitting `/debug/events`
- Failure state exposed: if token logging fix regresses, tokens will appear in `docker compose logs` even with SMTP configured — detectable by log grep

## Inputs

- `backend/app/auth/router.py` — lines 125-150: current unconditional token logging and SMTP fallback logic
- `backend/app/debug/router.py` — line 22: current `get_current_user` dependency on event console
- `backend/app/views/service.py` — lines ~363 and ~516: inline escaping blocks to replace
- S01-RESEARCH.md — SPARQL regex metacharacter list and escaping strategy

## Expected Output

- `backend/app/auth/router.py` — token log line moved inside conditional branches
- `backend/app/debug/router.py` — event console uses `require_role("owner")`
- `backend/app/sparql/utils.py` — new file with `escape_sparql_regex()` function
- `backend/app/views/service.py` — both escaping sites use shared function
