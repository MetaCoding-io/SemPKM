---
estimated_steps: 7
estimated_files: 5
---

# T01: Create AI router with LLM streaming proxy and status endpoint

**Slice:** S01 — Backend AI endpoints with Bearer auth
**Milestone:** M028

## Description

Create the new AI router module at `backend/app/api/ai.py` and mount it in the application. Add two endpoints:

1. `POST /api/llm/stream` — Bearer-authenticated SSE proxy for OpenAI-compatible chat completions. This is a copy of the existing `llm_chat_stream()` at `backend/app/browser/settings.py` (around line 218) but using `get_current_user_or_api` (dual-auth: cookie + Bearer) instead of `get_current_user` (cookie-only). This is the gating dependency for the entire M028 milestone — without it, the browser extension cannot call the LLM.

2. `GET /api/llm/status` — Returns `{available: bool, provider: string|null}` by checking LLMConfigService for configured API base URL. Used by the extension for feature gating (EXT-31).

**Key patterns to follow:**
- The existing LLM proxy is at `backend/app/browser/settings.py` — search for `@settings_router.post("/llm/chat/stream")`. Copy the SSE streaming pattern, httpx async client, error handling, and `X-Accel-Buffering: no` header.
- All `/api/` endpoints use `get_current_user_or_api` from `backend/app/auth/dependencies.py` (line 224). This accepts both session cookies and `Authorization: Bearer <token>` headers.
- The LLM config is stored via `LLMConfigService` in `backend/app/services/llm.py`. Use `get_config()` to check availability and `get_decrypted_api_key()` to get the key for proxying.
- Router mounting pattern: add `from app.api.ai import ai_router` and `app.include_router(ai_router)` in `backend/app/main.py` near the existing `api_surface_router` line.
- Update the well-known discovery document in `backend/app/api/router.py` to include new endpoint paths and capabilities.

**Relevant skill:** `test` — for generating pytest unit tests.

## Steps

1. Create `backend/app/api/ai.py` with `ai_router = APIRouter(prefix="/api", tags=["ai"])`.
2. Add `POST /llm/stream` endpoint that:
   - Depends on `get_current_user_or_api` and `get_db_session`
   - Reads LLM config via `LLMConfigService().get_config(db)`
   - If `api_base_url` is empty, returns SSE error `{"error": "LLM not configured"}`
   - Reads request JSON body for `messages` and optional `model`
   - Decrypts API key via `LLMConfigService().get_decrypted_api_key(db)`
   - Uses `httpx.AsyncClient(timeout=300.0)` to stream `POST /v1/chat/completions` to the configured LLM
   - Returns `StreamingResponse` with `media_type="text/event-stream"` and `X-Accel-Buffering: no`
   - Catches exceptions and yields SSE error + `[DONE]`
3. Add `GET /llm/status` endpoint that:
   - Depends on `get_current_user_or_api` and `get_db_session`
   - Reads LLM config, returns `{available: bool, provider: string|null}` where `provider` is extracted from the API base URL hostname
4. Mount `ai_router` in `backend/app/main.py` — add import and `app.include_router(ai_router)` near the `api_surface_router` line (around line 564).
5. Update the well-known endpoint in `backend/app/api/router.py`:
   - Add `"llm_stream": "/api/llm/stream"`, `"llm_status": "/api/llm/status"`, `"detect_claims": "/api/ai/detect-claims"`, `"match_claims": "/api/ai/match-claims"`, `"suggest_relationships": "/api/ai/suggest-relationships"`, `"summarize": "/api/ai/summarize"` to the `endpoints` dict
   - Add `"llm-stream"` and `"ai-insights"` to the `capabilities` list
6. Write `backend/tests/test_llm_proxy.py` with tests:
   - `test_llm_status_returns_unavailable_when_not_configured` — mock empty LLMConfigService, assert `{available: false, provider: null}`
   - `test_llm_status_returns_available_with_config` — mock LLMConfigService with base_url, assert `{available: true, provider: "..."}`
   - `test_llm_status_requires_auth` — no auth header, assert 401
   - `test_llm_stream_returns_error_when_not_configured` — mock empty config, assert SSE error message
   - `test_llm_stream_accepts_bearer_token` — mock config + httpx stream, assert SSE data flows
   - `test_llm_stream_accepts_cookie_auth` — same with cookie instead of Bearer
   - `test_llm_stream_returns_401_without_auth` — no auth, assert 401
7. Run tests to verify: `cd backend && python -m pytest tests/test_llm_proxy.py -v`

## Must-Haves

- [ ] `POST /api/llm/stream` returns SSE with `X-Accel-Buffering: no` header
- [ ] `GET /api/llm/status` returns `{available, provider}` JSON
- [ ] Both endpoints accept Bearer token via `get_current_user_or_api`
- [ ] Both endpoints accept session cookie auth (dual-auth)
- [ ] LLM-not-configured returns SSE error (stream) / `{available: false}` (status), not 500
- [ ] Router mounted in main.py, well-known updated with new capabilities
- [ ] All unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_llm_proxy.py -v` — all tests pass
- Check `ai_router` appears in `main.py` include_router calls
- Check `/.well-known/sempkm` response model includes new endpoints and capabilities

## Observability Impact

- Signals added: `logger.debug` on LLM stream requests (user email, model requested), `logger.warning` on LLM proxy errors
- How a future agent inspects this: `GET /api/llm/status` returns current LLM availability
- Failure state exposed: LLM not configured → clear JSON/SSE error message (not 500)

## Inputs

- `backend/app/browser/settings.py` lines ~218-290 — existing LLM chat stream to copy pattern from
- `backend/app/auth/dependencies.py` line 224 — `get_current_user_or_api` dependency
- `backend/app/services/llm.py` — `LLMConfigService` with `get_config()` and `get_decrypted_api_key()`
- `backend/app/api/router.py` — existing well-known endpoint and api_surface_router
- `backend/app/main.py` lines ~562-597 — router mounting section
- `backend/tests/test_commands_bearer_auth.py` — reference for Bearer auth test patterns (fixtures, mock user/session/token setup)

## Expected Output

- `backend/app/api/ai.py` — new module with `ai_router`, `POST /api/llm/stream`, `GET /api/llm/status`
- `backend/app/main.py` — updated with `ai_router` import and mount
- `backend/app/api/router.py` — updated well-known with new endpoints/capabilities
- `backend/tests/test_llm_proxy.py` — 7+ unit tests all passing
