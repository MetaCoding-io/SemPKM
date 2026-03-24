---
estimated_steps: 4
estimated_files: 2
skills_used:
  - test
---

# T03: Unit tests for ContextService and context API endpoints

**Slice:** S01 — Backend Context API & Workspace Indicator
**Milestone:** M037

## Description

Write comprehensive unit tests proving the context domain contract: ContextService upsert semantics, TTL staleness detection, and API endpoint behavior (auth, rate limiting, SSE content type, payload validation). Follow the established test patterns from `test_persona_service.py` (in-memory SQLite) and router tests using httpx TestClient.

## Steps

1. Create `backend/tests/test_context_service.py` with in-memory SQLite async session factory (same fixture pattern as `test_persona_service.py`). Tests:
   - `test_update_creates_context` — first update creates a row, returns ContextData with correct fields
   - `test_update_upserts_existing` — second update for same user overwrites fields, not appends
   - `test_update_partial_fields` — update with only location_zone leaves other fields unchanged
   - `test_get_current_returns_none_for_unknown_user` — no row → None
   - `test_get_current_fresh_context_not_stale` — just-updated context has `is_stale=False`
   - `test_get_current_stale_context` — context with old `updated_at` (use TTL=1 second + asyncio.sleep(1.5) or mock) has `is_stale=True`
   - `test_get_current_includes_ttl_seconds` — returned data includes the TTL value
   - `test_update_returns_all_fields` — verify all fields present in ContextData
   - `test_calendar_busy_default_false` — new context without explicit calendar_busy has False
   - `test_device_id_stored` — device_id persists across updates

2. Create `backend/tests/test_context_router.py` using httpx AsyncClient with the FastAPI app (or TestClient). Tests:
   - `test_post_update_success` — POST /api/context/update with valid JSON returns 200
   - `test_post_update_empty_body` — POST with `{}` returns 200 (all fields optional)
   - `test_get_current_after_update` — POST then GET /api/context/current returns the posted values
   - `test_get_current_no_context` — GET before any POST returns null/empty context
   - `test_post_update_requires_auth` — POST without credentials returns 401
   - `test_get_current_requires_auth` — GET without credentials returns 401
   - `test_get_stream_content_type` — GET /api/context/stream returns `text/event-stream` content type
   - `test_post_update_rate_limit` — multiple rapid POSTs eventually return 429 (if rate limiting is testable — may need to mock or use slowapi test mode)

3. For router tests, use the fixture pattern from existing test files (e.g., `backend/tests/conftest.py` or inline fixtures). The test client should have an authenticated session. If the app is complex to stand up for router tests, use a minimal FastAPI test app with just the context router and mocked dependencies.

4. Run the full test suite: `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py -v`

## Must-Haves

- [ ] ≥8 service tests covering upsert, TTL, partial update, missing user
- [ ] ≥6 router tests covering POST/GET success, auth enforcement, SSE content type
- [ ] TTL staleness test proves `is_stale` transitions from False to True
- [ ] Upsert test proves one row per user (not append)
- [ ] All tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py -v` — all tests pass with 0 failures

## Inputs

- `backend/app/context/service.py` — ContextService under test (created in T01)
- `backend/app/context/models.py` — UserContext model (created in T01)
- `backend/app/context/router.py` — API endpoints under test (created in T02)
- `backend/app/context/broadcast.py` — ContextBroadcast (created in T01)
- `backend/app/main.py` — app with context router wired (modified in T02)
- `backend/tests/test_persona_service.py` — test pattern to follow (in-memory SQLite fixtures)

## Expected Output

- `backend/tests/test_context_service.py` — ≥8 unit tests for ContextService
- `backend/tests/test_context_router.py` — ≥6 endpoint tests for context API
