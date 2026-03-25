# M043: Security Hardening - Injection, Auth & Access Control Fixes

**Vision:** Close all actionable findings from the M042 security audit. Fix the 3 high-severity SPARQL injection vectors, add missing authentication, harden the auth subsystem (single-use magic links, token scopes, session management), consolidate SPARQL escape functions, fix CORS ownership, add rate limits, and add safety warnings for misconfiguration.

## Success Criteria

- All 3 confirmed-exploitable SPARQL injection vectors (F-006, F-007, F-008) are blocked — crafted IRI payloads return 400 or are sanitized
- All 6 unauthenticated app endpoints (F-001) require get_current_user
- Magic link tokens are single-use — replay within 10-min window returns 401
- API tokens support fine-grained scopes enforced per-endpoint
- CORS headers come from FastAPI only — no CORS headers in nginx.conf
- Rate limits enforced on SPARQL, copilot, token creation, and batch command endpoints
- Session management: revoke-all-devices UI in Settings, max 10 concurrent sessions, daily cleanup
- No-SMTP magic links restricted to existing/invited users
- Startup warnings for demo_mode + non-localhost and cookie_secure mismatch
- All existing E2E and unit tests pass after changes

## Slices

- [ ] **S01: SPARQL Injection & Escape Consolidation** `risk:high` `depends:[]`
  > After this: Crafted IRI payloads to /browser/views/generic/table?type=PAYLOAD, /browser/apps/right-pane-sections?iri=PAYLOAD, and VFS mount creation all return 400. Favorites rejects malicious IRIs at storage time.

- [ ] **S02: Access Control & CORS Fixes** `risk:medium` `depends:[]`
  > After this: Unauthenticated GET to /browser/apps/explorer returns 401. CORS preflight handled by FastAPI only — no duplicate headers from nginx.

- [ ] **S03: Auth Hardening — Magic Links, Token Scopes, Sessions** `risk:high` `depends:[]`
  > After this: Magic link replay returns 401. New API token creation UI shows scope checkboxes. Settings page has 'Log out all devices' button. Token created with sparql:read scope gets 403 on object mutation.

- [ ] **S04: Rate Limits, Warnings & Documentation** `risk:low` `depends:[S02]`
  > After this: SPARQL endpoint returns 429 after 60 requests/minute. Startup log shows warning when demo_mode=true with non-localhost URL. ARCHITECTURE.md documents shared-data model.

## Boundary Map

```
IN SCOPE:
- SPARQL injection fixes (IRI validation, escape consolidation)
- Authentication on app endpoints
- Magic link single-use tokens
- Fine-grained API token scopes
- CORS consolidation to backend
- Rate limiting on 4 endpoint groups
- Session management hardening
- No-SMTP magic link restriction
- Setup endpoint guard
- Startup warnings (demo mode, cookie_secure)
- Documentation of shared-data model

OUT OF SCOPE:
- Multi-tenant / per-object ownership (D356 — not a goal)
- Result size pagination for SPARQL console
- SPARQL UPDATE endpoint
- Redis-based session store
- OAuth token revocation
- Frontend UI changes beyond Settings revoke-all button
```
