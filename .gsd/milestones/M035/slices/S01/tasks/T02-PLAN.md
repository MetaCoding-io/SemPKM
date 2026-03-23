---
estimated_steps: 4
estimated_files: 4
skills_used:
  - review
---

# T02: Create copilot chat SSE endpoint and wire routers into main.py

**Slice:** S01 — Copilot Chat with SPARQL Generation
**Milestone:** M035

## Description

Create the `/api/copilot/chat` SSE streaming endpoint that powers the copilot. This endpoint receives user messages, injects schema context into the system prompt via CopilotService, and proxies the streaming LLM response. It also detects SPARQL code blocks in the streamed response and emits special SSE events for the approval flow. Additionally, wire both the existing `ai_router` (from M028, currently orphaned) and the new `copilot_router` into `main.py`, and add the nginx SSE proxy config.

## Steps

1. **Create `backend/app/api/copilot.py`** with a `copilot_router = APIRouter(prefix="/api/copilot", tags=["copilot"])`. Implement `POST /chat` endpoint:
   - Accept JSON body: `{"messages": [...], "model": "optional", "conversation_id": "optional"}`
   - Auth: `get_current_user_or_api` (dual-auth, same as ai_router endpoints)
   - Fetch LLM config via `LLMConfigService`. If not configured, return SSE error event and close.
   - Build schema context via `CopilotService.build_schema_context(db)`.
   - Build system prompt via `CopilotService.build_system_prompt(schema_context)`.
   - Prepend system message to the user's messages array.
   - Stream the response via httpx to the configured LLM endpoint (same SSE proxy pattern as `backend/app/api/ai.py` `llm_stream()`).
   - Parse the streamed content: accumulate tokens, detect ```sparql code fences. When a complete SPARQL block is detected, emit a custom SSE event `event: sparql_query\ndata: {"query": "...", "valid": bool, "error": "..."}` using `CopilotService.validate_query()`.
   - Include `X-Accel-Buffering: no` and `Cache-Control: no-cache` headers.

2. **Create `POST /api/copilot/approve`** endpoint in the same file:
   - Accept JSON body: `{"query": "sparql string", "action": "approve|reject|edit", "edited_query": "optional"}`
   - On approve: execute query via `CopilotService.execute_query()`, format results via `CopilotService.format_results()`, return JSON with results.
   - On reject: return `{"status": "rejected"}`.
   - On edit: re-validate the edited query, then execute if valid.

3. **Wire routers into `backend/app/main.py`**:
   - Add `from app.api.ai import ai_router` and `from app.api.copilot import copilot_router`.
   - Add `app.include_router(ai_router)` after the existing `api_surface_router` include.
   - Add `app.include_router(copilot_router)` right after `ai_router`.
   - Ensure the placement is before `browser_router` (which has catch-all patterns).

4. **Add nginx SSE location block in `frontend/nginx.conf`**:
   - Add a location block for `/api/copilot/chat` with SSE proxy settings, right after the existing `/api/lint/stream` SSE block. Use the same pattern: `proxy_buffering off`, `proxy_cache off`, `proxy_read_timeout 300s`, `X-Accel-Buffering no`, `Connection ''`.
   - Also ensure the generic `/api/` location continues to handle `/api/copilot/approve`.

## Must-Haves

- [ ] `POST /api/copilot/chat` returns SSE stream with schema-aware system prompt
- [ ] SPARQL detection in stream emits `sparql_query` SSE event with validation result
- [ ] `POST /api/copilot/approve` executes approved queries and returns formatted results
- [ ] `ai_router` from `app.api.ai` wired into main.py (enables 6 existing AI endpoints)
- [ ] `copilot_router` wired into main.py
- [ ] nginx.conf has SSE proxy config for `/api/copilot/chat`

## Verification

- `grep -q "ai_router" backend/app/main.py && grep -q "copilot_router" backend/app/main.py` — both routers registered
- `grep -q "api/copilot" frontend/nginx.conf` — nginx SSE config present
- `cd backend && python -c "from app.api.copilot import copilot_router; print('import OK')"` — module imports cleanly

## Observability Impact

- Signals added/changed: structured logging for copilot chat requests (user, model, schema_context_size, sparql_detected), approval actions (query, action, result_count), and errors
- How a future agent inspects this: `rg "copilot" backend/app/main.py` confirms wiring; `/api/llm/status` confirms LLM availability; server logs show copilot request flow
- Failure state exposed: SSE error events for LLM unavailable, LLM timeout, SPARQL validation failure

## Inputs

- `backend/app/services/copilot.py` — CopilotService from T01
- `backend/app/api/ai.py` — existing ai_router to wire into main.py
- `backend/app/services/llm.py` — LLMConfigService for config and API key
- `backend/app/main.py` — router registration
- `frontend/nginx.conf` — proxy configuration

## Expected Output

- `backend/app/api/copilot.py` — new copilot router with /chat and /approve endpoints
- `backend/app/main.py` — modified to include ai_router and copilot_router
- `frontend/nginx.conf` — modified with SSE proxy location for /api/copilot/chat
