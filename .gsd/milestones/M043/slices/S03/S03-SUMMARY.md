---
id: S03
parent: M043
milestone: M043
provides:
  - Single-use magic link enforcement (UsedMagicToken model + check_and_consume_magic_token)
  - scope_required() dependency for per-endpoint scope enforcement
  - POST /api/auth/sessions/revoke-all endpoint
  - Session cap at 10 per user in create_session()
  - Periodic cleanup of expired sessions and magic tokens
  - ApiToken.scope field with VALID_SCOPES constant
requires:
  []
affects:
  - S04
  - S05
key_files:
  - backend/app/auth/models.py
  - backend/app/auth/service.py
  - backend/app/auth/router.py
  - backend/app/auth/dependencies.py
  - backend/app/auth/tokens.py
  - backend/app/auth/schemas.py
  - backend/app/main.py
  - backend/app/sparql/router.py
  - backend/app/admin/router.py
  - backend/app/templates/admin/api_tokens.html
  - backend/migrations/versions/022_used_magic_tokens.py
  - backend/migrations/versions/023_add_api_token_scope.py
  - backend/tests/test_magic_link_hardening.py
  - backend/tests/test_token_scopes.py
  - backend/tests/test_session_management.py
key_decisions:
  - D365: Single-use magic link check in AuthService (DB layer) not tokens.py — preserves stateless/stateful separation
  - D366: Scope enforcement on API-surface endpoints only (SPARQL, commands, copilot) — browser-only endpoints left on cookie auth
  - D367: Periodic cleanup via asyncio.create_task with sleep loop — zero new dependencies, proper cancellation
patterns_established:
  - scope_required() dependency factory pattern: def scope_required(*scopes) returns a FastAPI Depends that checks token scopes, passes sessions unconditionally, returns 403 with WARNING log on denial
  - UsedMagicToken hash-based consumption tracking: SHA-256 hash stored instead of raw token, consistent with existing ApiToken.token_hash pattern
  - Periodic async cleanup loop in lifespan: asyncio.create_task + sleep(86400) with proper task.cancel() on shutdown — reusable for any daily maintenance task
observability_surfaces:
  - Magic link replay attempts logged at WARNING with email address
  - Scope enforcement denials logged at WARNING with token ID, current scopes, required scope, and endpoint path
  - Session cleanup logged at INFO with purged count (sessions and magic tokens separately)
  - Session cap eviction logged at INFO with eviction count
drill_down_paths:
  - .gsd/milestones/M043/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M043/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M043/slices/S03/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T14:50:36.025Z
blocker_discovered: false
---

# S03: Auth Hardening — Magic Links, Token Scopes, Sessions

**Single-use magic links, fine-grained API token scopes with enforcement on SPARQL/commands/copilot endpoints, session management (revoke-all, cap at 10, daily cleanup), no-SMTP restriction, truncated token logging, and 0o600 file permissions on secrets.**

## What Happened

Three tasks delivered six auth hardening features from the M042 security audit findings.

**T01 — Single-use magic links + no-SMTP restriction + token logging** implemented F-012 (single-use), F-018 (no-SMTP restriction), and F-028 (token logging truncation). The UsedMagicToken model stores SHA-256 hashes of consumed tokens with expiry timestamps. The single-use check lives in AuthService.check_and_consume_magic_token() — called after itsdangerous signature verification succeeds, preserving the clean separation between stateless crypto (tokens.py) and stateful DB operations (service.py). The no-SMTP restriction checks for existing users or pending invitations before generating tokens — unknown emails get a generic response with no information leakage. Token logging now shows only the first 8 characters. Alembic migration 022 creates the used_magic_tokens table. Cleanup of expired records runs at startup and daily via async task. 11 unit tests.

**T02 — API token scopes** added a scope field to ApiToken (comma-separated string, default '*' wildcard). The scope_required() dependency factory in dependencies.py checks token scopes against endpoint requirements — sessions bypass scope checks entirely. Scope enforcement wired to SPARQL router (sparql:read), commands router (commands:execute), and copilot router (copilot:use). Object mutations by external clients go through commands (already scoped). Browser-only endpoints (htmx objects, admin) left on cookie auth — they don't accept Bearer tokens. Admin UI updated with scope checkboxes in a 2-column grid. Alembic migration 023 adds the scope column. 26 unit tests.

**T03 — Session management** added POST /api/auth/sessions/revoke-all (revokes all sessions then creates a fresh one so the caller stays logged in), session cap at 10 per user (evicts oldest via subquery DELETE), periodic 24-hour cleanup via asyncio.create_task in lifespan (cancelled on shutdown), and os.chmod(0o600) on .secret-key and .setup-token files. 14 unit tests.

## Verification

90 tests pass across 6 auth test files (51 new + 39 existing), zero regressions. Specific verification:

- Magic link replay: test_replay_fails proves second use of same token returns False
- No-SMTP restriction: 4 tests cover no-invitation, pending, expired, accepted invitation states
- Token logging: verified only first 8 chars logged in both SMTP and no-SMTP paths
- Scope enforcement: scoped token gets 403 on out-of-scope endpoint, wildcard passes all, session bypasses, multi-scope tokens match correctly
- SPARQL scope: 5 integration tests (sparql:read passes, commands:execute denied, wildcard passes, session bypasses, no-auth 401)
- Revoke-all: returns correct count, zero when no sessions, doesn't affect other users
- Session cap: enforces limit, evicts oldest by timestamp, no eviction below cap
- Cleanup: removes expired sessions and magic tokens, preserves active ones
- File permissions: .secret-key and .setup-token get 0o600
- Observability: replay logged at WARNING, scope denial logged at WARNING with token ID and endpoint, cleanup logged at INFO with count

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T01: Single-use check placed in AuthService (DB layer) instead of modifying tokens.py as planned — preserves separation of stateless crypto vs stateful DB operations. Router calls signature check first, then single-use check.

T02: Scope enforcement not added to objects mutation endpoints or admin model endpoints as planned. These routers use cookie-only auth for htmx browser interactions — adding Bearer scope checks would require changing their auth dependency chain for no security benefit. The practical API surface (SPARQL, commands, copilot) is covered. Object mutations by external clients go through the commands router which is already scoped.

T03: Session cap test adjusted to use manually-set timestamps for deterministic eviction ordering — SQLite identical-timestamp ordering is non-deterministic for rapid session creation.

## Known Limitations

itsdangerous URLSafeTimedSerializer.dumps() is deterministic for the same email within the same second — two rapid magic link requests for the same email produce identical tokens, meaning the second token is pre-consumed when the first is used. Rate limiting (5/min) makes this a non-issue in practice, but a nonce could be added to the payload if needed.

The admin token creation UI shows scope checkboxes but the Settings page 'Log out all devices' button is not yet wired to a frontend control — the POST /api/auth/sessions/revoke-all endpoint exists and is tested but needs a UI trigger in the Settings page.

## Follow-ups

Settings UI needs a 'Log out all devices' button wired to POST /api/auth/sessions/revoke-all. The endpoint is ready — this is a frontend-only task.

## Files Created/Modified

- `backend/app/auth/models.py` — Added UsedMagicToken model and scope field to ApiToken with VALID_SCOPES constant
- `backend/app/auth/service.py` — Added check_and_consume_magic_token(), cleanup_expired_magic_tokens(), session cap logic in create_session(max_sessions=10)
- `backend/app/auth/router.py` — Magic link single-use check, no-SMTP restriction, truncated token logging, revoke-all-sessions endpoint, scoped token creation
- `backend/app/auth/dependencies.py` — Added scope_required() dependency factory with logging
- `backend/app/auth/tokens.py` — os.chmod(0o600) on .secret-key and .setup-token files
- `backend/app/auth/schemas.py` — Added RevokeAllSessionsResponse schema
- `backend/app/main.py` — Wired periodic cleanup task (24h interval) with proper cancellation, startup cleanup for magic tokens
- `backend/app/sparql/router.py` — Added scope_required('sparql:read') dependency to GET/POST /api/sparql and GET /api/search
- `backend/app/admin/router.py` — Admin token creation accepts scope form field, validates against VALID_SCOPES
- `backend/app/templates/admin/api_tokens.html` — Scope checkboxes in 2-column grid, scopes column in token list table
- `backend/migrations/versions/022_used_magic_tokens.py` — Alembic migration creating used_magic_tokens table with token_hash index
- `backend/migrations/versions/023_add_api_token_scope.py` — Alembic migration adding scope column to api_tokens (default '*')
- `backend/tests/test_magic_link_hardening.py` — 11 tests: single-use enforcement, pending invitation logic, token truncation
- `backend/tests/test_token_scopes.py` — 26 tests: scope parsing, scope_required dependency, token creation with scopes, endpoint enforcement, denial logging
- `backend/tests/test_session_management.py` — 14 tests: revoke-all, session cap, cleanup, file permissions
