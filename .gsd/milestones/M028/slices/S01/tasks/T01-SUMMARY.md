---
id: T01
parent: S01
milestone: M028
provides:
  - POST /api/llm/stream SSE proxy with dual auth (cookie + Bearer)
  - GET /api/llm/status availability endpoint for feature gating
  - ai_router module mounted in main.py
  - well-known discovery updated with AI endpoint paths and capabilities
key_files:
  - backend/app/api/ai.py
  - backend/app/main.py
  - backend/app/api/router.py
  - backend/tests/test_llm_proxy.py
key_decisions:
  - Used JSONResponse for /llm/status instead of a Pydantic model — keeps it simple for a two-field response
  - Provider extracted via urlparse hostname from api_base_url
patterns_established:
  - AI router pattern: ai_router = APIRouter(prefix="/api", tags=["ai"]) — all AI endpoints in one module
  - Test pattern for AI endpoints: _build_ai_app() with dependency_overrides for get_db_session, patch LLMConfigService methods
observability_surfaces:
  - GET /api/llm/status — returns {available, provider} for extension feature gating
  - logger.debug on LLM stream requests (user email, model)
  - logger.warning on LLM proxy errors with exc_info=True
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Create AI router with LLM streaming proxy and status endpoint

**Added /api/llm/stream SSE proxy and /api/llm/status endpoint with dual Bearer+cookie auth, mounted ai_router in main.py, updated well-known discovery with AI capabilities**

## What Happened

Created `backend/app/api/ai.py` with the `ai_router` module containing two endpoints:

1. **POST /api/llm/stream** — SSE streaming proxy for OpenAI-compatible chat completions. Copied the streaming pattern from the existing `llm_chat_stream()` in `browser/settings.py` but switched the auth dependency to `get_current_user_or_api` for dual-auth support (cookie + Bearer token). Returns `X-Accel-Buffering: no` header for nginx compatibility. Yields SSE error `{"error": "LLM not configured"}` + `[DONE]` when no API base URL is configured.

2. **GET /api/llm/status** — Returns `{available: bool, provider: string|null}` by checking `LLMConfigService.get_config()`. Provider is the hostname extracted from the configured API base URL via `urlparse`.

Mounted the router in `main.py` right after `api_surface_router`. Updated the well-known discovery document in `router.py` with all planned AI endpoint paths (llm_stream, llm_status, detect_claims, match_claims, suggest_relationships, summarize) and added `llm-stream` and `ai-insights` to the capabilities list.

## Verification

All 8 tests pass covering: auth rejection (401 for both endpoints), LLM-not-configured degradation (SSE error for stream, `available: false` for status), Bearer token auth, cookie auth, SSE stream format with correct headers, and provider extraction from URL.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose exec api python -m pytest tests/test_llm_proxy.py -v` | 0 | ✅ pass | 0.75s |
| 2 | `grep -n "ai_router" backend/app/main.py` | 0 | ✅ pass (line 18 import, line 566 mount) | — |
| 3 | `grep "llm_stream\|llm_status\|ai-insights\|llm-stream" backend/app/api/router.py` | 0 | ✅ pass (all entries present) | — |
| 4 | LSP diagnostics on backend/app/api/ai.py | — | ✅ pass (no diagnostics) | — |

Slice-level verification (partial — T01 is intermediate):
- `test_llm_proxy.py` — ✅ 8/8 pass
- `test_ai_endpoints.py` — not yet created (T04)
- `test_claim_detection.py` — not yet created (T02)
- `test_claim_matching.py` — not yet created (T03)

## Diagnostics

- `GET /api/llm/status` returns current LLM availability — use this to probe before calling AI endpoints
- LLM-not-configured returns clear SSE error message (not 500)
- `logger.debug` on stream requests shows user email and model
- `logger.warning` on proxy errors includes `exc_info=True`

## Deviations

None — implementation followed the plan exactly.

## Known Issues

- Dev container `--no-dev` build excludes pytest; test deps must be installed into the venv at runtime via `uv pip install` before running tests. This is expected for the Docker dev workflow.

## Files Created/Modified

- `backend/app/api/ai.py` — new module with ai_router, POST /api/llm/stream, GET /api/llm/status
- `backend/app/main.py` — added ai_router import and include_router call
- `backend/app/api/router.py` — updated well-known endpoints dict and capabilities list
- `backend/tests/test_llm_proxy.py` — 8 unit tests covering auth, SSE format, degradation paths
