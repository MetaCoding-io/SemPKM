# S04: Rate Limits, Warnings & Documentation — UAT

**Milestone:** M043
**Written:** 2026-03-25T15:31:21.682Z

## UAT: S04 — Rate Limits, Warnings & Documentation

### Preconditions
- Docker test stack running (`docker compose -f docker-compose.test.yml up -d`)
- Authenticated session (logged in as any user)
- At least one Mental Model installed (basic-pkm)

### Test 1: SPARQL Rate Limit (429 Response)
1. Open a terminal with curl access to the API
2. Send 61 POST requests to `/api/sparql` within 60 seconds with body `{"query": "SELECT ?s WHERE { ?s a ?o } LIMIT 1"}`
3. **Expected:** First 60 return 200. The 61st returns HTTP 429 with `Retry-After: 60` header
4. **Expected:** Container logs show WARNING with source IP and path `/api/sparql`

### Test 2: Copilot Rate Limit
1. Send 21 POST requests to `/api/copilot/chat` within 60 seconds
2. **Expected:** The 21st returns HTTP 429 with Retry-After header

### Test 3: Token Creation Rate Limit
1. Send 6 POST requests to `/api/auth/tokens` within 60 seconds
2. **Expected:** The 6th returns HTTP 429

### Test 4: Commands Rate Limit
1. Send 21 POST requests to `/api/commands` within 60 seconds
2. **Expected:** The 21st returns HTTP 429

### Test 5: SPARQL Query Timeout (504 Response)
1. Submit a SPARQL query that takes longer than 30 seconds (e.g., a complex cross-product query on a large dataset)
2. **Expected:** Returns HTTP 504 with message "Query timed out after 30 seconds"

### Test 6: Error Disclosure Protection
1. Trigger an unhandled exception in any endpoint (e.g., corrupt a required database table temporarily)
2. **Expected:** Response returns `{"detail": "Internal server error"}` — no stack trace, no internal details
3. **Expected:** Container logs show ERROR-level entry with full traceback

### Test 7: Failed Auth Attempt Logging
1. Send a POST to `/api/auth/verify` with an invalid token
2. **Expected:** Response returns 401
3. **Expected:** Container logs show WARNING with source IP mentioning invalid/expired token
4. Send a request with `Authorization: Bearer invalid-token-here` to any protected endpoint
5. **Expected:** Container logs show WARNING with source IP and token prefix `invalid-`

### Test 8: SecurityAuditLog Table
1. Log in via magic link flow
2. Query the security_audit_log table: `SELECT * FROM security_audit_log WHERE event_type = 'login_success'`
3. **Expected:** Row exists with correct user_id, source_ip, and detail containing email
4. Create an API token in Settings
5. **Expected:** Row exists with event_type='token_created', detail containing token name and scope
6. Click "Log out all devices" in Settings
7. **Expected:** Row exists with event_type='session_revoked_all', detail containing revoked count

### Test 9: Security Model Documentation
1. Open `docs/security-model.md`
2. **Expected:** Document covers: roles (owner/member/guest), shared-data model, authentication flow, API token scopes, audit trail, rate limits, SPARQL security, federation, secret management
3. Verify section headings match the security features implemented in M043

### Edge Cases
- Rate limit counter resets after 60 seconds — verify requests succeed again after the window expires
- Audit logging failure should not crash the auth operation — if DB is temporarily unavailable, login should still succeed
- 429 response must include `Retry-After` header for HTTP spec compliance
