# S03: Auth Hardening — Magic Links, Token Scopes, Sessions — UAT

**Milestone:** M043
**Written:** 2026-03-25T14:50:36.026Z

# S03: Auth Hardening — Magic Links, Token Scopes, Sessions — UAT

**Milestone:** M043
**Written:** 2026-03-25

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All features are backend auth mechanisms testable via HTTP requests. 51 unit tests cover all paths including edge cases. No frontend-only behavior to verify beyond the admin token UI.

## Preconditions

- Docker test stack running (`docker compose -f docker-compose.test.yml up -d`)
- At least one user account exists (setup completed)
- SMTP not configured (default dev mode) for no-SMTP restriction tests

## Smoke Test

Request a magic link, use it to log in, then attempt to use the same link again. The second attempt should return HTTP 401 with "Token has already been used".

## Test Cases

### 1. Magic link single-use enforcement (F-012)

1. POST `/api/auth/magic-link` with a registered email address
2. Copy the token from the server console (first 8 chars shown, full token in dev mode)
3. GET `/api/auth/verify?token=<token>` — should return 200 and set session cookie
4. GET `/api/auth/verify?token=<token>` again with the same token
5. **Expected:** HTTP 401 with `{"detail": "Token has already been used"}`. Server log shows WARNING: "Magic link replay attempt for <email>"

### 2. No-SMTP restriction for unknown emails (F-018)

1. POST `/api/auth/magic-link` with an email that has no user account and no pending invitation
2. **Expected:** HTTP 200 with generic "If this email is registered…" message. No token generated (nothing appears in console). No information leakage about whether the account exists.

### 3. No-SMTP allows known users and invited users

1. POST `/api/auth/magic-link` with a registered user's email
2. **Expected:** HTTP 200 with token shown in console (first 8 chars in log)
3. POST `/api/auth/magic-link` with an email that has a pending (non-expired) invitation
4. **Expected:** HTTP 200 with token shown in console

### 4. Token logging truncation (F-028)

1. Trigger magic link generation for a valid user
2. Check server logs for the INFO message
3. **Expected:** Log shows `Magic link token for user@example.com: abcd1234...` — only first 8 characters, not the full token

### 5. API token creation with scopes

1. Navigate to Admin > API Tokens
2. Click "Create Token", enter a name
3. Check only the "sparql:read" scope checkbox
4. Submit the form
5. **Expected:** Token created. Token list table shows "sparql:read" in the Scopes column. Success banner shows the assigned scope.

### 6. Scoped token enforcement — allowed endpoint

1. Create an API token with scope "sparql:read"
2. GET `/api/sparql?query=SELECT * WHERE { ?s ?p ?o } LIMIT 1` with `Authorization: Bearer <token>`
3. **Expected:** HTTP 200 with SPARQL results

### 7. Scoped token enforcement — denied endpoint

1. Using the same "sparql:read" token from test 6
2. POST `/api/commands` with `Authorization: Bearer <token>` and a valid command body
3. **Expected:** HTTP 403 with message about insufficient scope. Server log shows WARNING with token ID, current scopes (sparql:read), required scope (commands:execute), and endpoint path.

### 8. Wildcard token has full access

1. Create an API token with no scope checkboxes selected (defaults to wildcard *)
2. Use it against `/api/sparql`, `/api/commands`, `/api/copilot/chat`
3. **Expected:** All requests succeed (200 or appropriate success status). No scope denial.

### 9. Session revoke-all endpoint

1. Log in from the current browser, note the session cookie
2. POST `/api/auth/sessions/revoke-all` with the current session cookie
3. **Expected:** HTTP 200 with `{"revoked_sessions": N}` where N is the count of revoked sessions. A new session cookie is set in the response. The old session is invalidated but the user remains logged in via the new session.

### 10. Session cap enforcement

1. Log in 11 times (create 11 sessions for the same user, e.g., via magic link in 11 different browser contexts)
2. **Expected:** After the 11th login, only 10 sessions exist. The oldest session was evicted. Server log shows INFO about session eviction.

### 11. File permissions on secrets (F-038)

1. Check file permissions on `data/.secret-key` and `data/.setup-token` inside the API container
2. `docker compose exec api ls -la data/.secret-key data/.setup-token`
3. **Expected:** Both files show `-rw-------` (0600) permissions

## Edge Cases

### Expired magic token cleanup

1. Wait for daily cleanup cycle (or manually trigger cleanup_expired_magic_tokens)
2. Check used_magic_tokens table
3. **Expected:** Rows with expires_at < now() are deleted. Active (non-expired) rows are preserved.

### Session auth bypasses scope checks

1. Log in via browser (session cookie auth)
2. Access `/api/sparql` via the browser session
3. **Expected:** Request succeeds regardless of any scope constraints — session auth is not subject to scope enforcement

### Multiple scopes on one token

1. Create a token with scopes "sparql:read,commands:execute"
2. Test against both `/api/sparql` and `/api/commands`
3. **Expected:** Both succeed. Testing against `/api/copilot/chat` returns 403.

## Failure Signals

- Magic link replay returns 200 instead of 401 — single-use enforcement broken
- Scoped token accesses out-of-scope endpoint without 403 — scope enforcement not wired
- No WARNING log on scope denial — observability gap
- Revoke-all leaves user logged out (no new session created) — fresh session logic broken
- .secret-key or .setup-token has permissions other than 0600 — chmod not applied

## Requirements Proved By This UAT

- No tracked requirements directly affected — this slice addresses M042 audit findings (F-012, F-013, F-016, F-018, F-028, F-038)

## Not Proven By This UAT

- Settings page "Log out all devices" UI button — endpoint exists but no frontend control yet
- Rate limiting on token creation — deferred to S04
- Full E2E regression — deferred to S05

## Notes for Tester

- The admin token UI scope checkboxes default to wildcard when none are selected — this is intentional for backward compatibility
- Existing tokens from before migration 023 get scope='*' automatically
- The periodic cleanup runs every 24 hours — for manual testing, call the cleanup methods directly or wait for the cycle
