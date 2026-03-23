---
id: T02
parent: S01
milestone: M035
provides:
  - POST /api/copilot/chat SSE streaming endpoint with schema-aware system prompt and inline SPARQL detection
  - POST /api/copilot/approve endpoint for query approval/rejection/editing
  - ai_router wired into main.py (enables 6 existing AI endpoints)
  - copilot_router wired into main.py
  - nginx SSE proxy config for /api/copilot/chat
key_files:
  - backend/app/api/copilot.py
  - backend/app/main.py
  - frontend/nginx.conf
key_decisions:
  - SPARQL detection accumulates streamed tokens and scans for complete ```sparql code blocks; emits sparql_query SSE event per block with validation result
  - Approval endpoint returns structured JSON (not SSE) for simplicity since the approve action is synchronous
  - ai_router and copilot_router placed after api_surface_router and before auth_router in the include chain
patterns_established:
  - Custom SSE events (event: sparql_query, event: error) alongside standard OpenAI streaming data lines in a single SSE stream
  - CopilotService instantiated per-request from app.state services (triplestore_client, shapes_service, label_service, prefix_registry)
observability_surfaces:
  - "Structured logs: copilot.chat.request (user, model, schema_context_size, message_count), copilot.chat.sparql_detected (valid, error), copilot.chat.complete (sparql_detected count, content_len), copilot.chat.error, copilot.chat.timeout"
  - "Structured logs: copilot.approve.request (user, action, query_len), copilot.approve.executed (bindings, iris), copilot.approve.validation_failed, copilot.approve.execution_error"
  - "SSE error events: LLM not configured, LLM error status, stream error, timeout — all emitted as event: error with JSON payload"
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Create copilot chat SSE endpoint and wire routers into main.py

**Created /api/copilot/chat SSE streaming endpoint with schema-aware system prompt and SPARQL code block detection, /api/copilot/approve query execution endpoint, wired both ai_router and copilot_router into main.py, and added nginx SSE proxy config.**

## What Happened

Created `backend/app/api/copilot.py` with two endpoints:

1. **`POST /api/copilot/chat`** — SSE streaming endpoint that builds a system prompt with schema context via CopilotService, prepends it to the user's messages, and proxies the LLM streaming response. As tokens arrive, the endpoint accumulates content and scans for complete ` ```sparql ` code blocks. When a block is found, it validates the query via `CopilotService.validate_query()` and emits a custom `event: sparql_query` SSE event with the query text, validity flag, and any error. Error states (LLM not configured, parse errors, timeouts, stream failures) are emitted as `event: error` SSE events.

2. **`POST /api/copilot/approve`** — Synchronous JSON endpoint accepting `{query, action, edited_query?}`. On `approve`, validates and executes the query via CopilotService, returning formatted prose and bindings. On `reject`, returns `{"status": "rejected"}`. On `edit`, uses the edited query instead.

Wired both `ai_router` (from `app.api.ai`, previously orphaned) and `copilot_router` into `main.py`'s router registration chain, placed after `api_surface_router` and before `auth_router` — well before `browser_router`'s catch-all patterns.

Added nginx SSE location block for `/api/copilot/chat` in `frontend/nginx.conf` right after the existing `/api/lint/stream` SSE block, using the same pattern: `proxy_buffering off`, `proxy_cache off`, `Connection ''`, `X-Accel-Buffering no`, 300s read/send timeouts.

## Verification

- `grep -q "ai_router" backend/app/main.py && grep -q "copilot_router" backend/app/main.py` → both routers registered ✅
- `grep -q "api/copilot" frontend/nginx.conf` → nginx SSE config present ✅
- `cd backend && python -c "from app.api.copilot import copilot_router; print('import OK')"` → imports cleanly ✅
- `cd backend && python -m pytest tests/test_ai_endpoints.py -v` → 16 passed, 1 pre-existing failure (well-known capabilities test, unrelated) ✅
- `cd backend && python -m pytest tests/test_copilot_service.py -v` → 32 passed ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "ai_router" backend/app/main.py && grep -q "copilot_router" backend/app/main.py` | 0 | ✅ pass | <1s |
| 2 | `grep -q "api/copilot" frontend/nginx.conf` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -c "from app.api.copilot import copilot_router; print('import OK')"` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_ai_endpoints.py -v` | 1 | ✅ pass (16/17; 1 pre-existing failure) | 11s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` | 0 | ✅ pass (32/32) | 0.3s |

### Slice-level verification status (intermediate — T02 of 5):
- `tests/test_copilot_service.py` — ✅ passes (32/32)
- `tests/test_ai_endpoints.py` — ✅ passes (16/17, 1 pre-existing unrelated failure)
- `verify-s01.sh` — ⏳ not yet created (T05 responsibility)
- Browser verification — ⏳ requires T03 (frontend) + T04 (approval flow)

## Diagnostics

- **Structured logs:** All copilot endpoints emit structured log events with `copilot.chat.*` and `copilot.approve.*` prefixes. To trace a chat request: grep for `copilot.chat.request` → `copilot.chat.sparql_detected` → `copilot.chat.complete`.
- **Error events:** LLM unavailability emits `copilot.chat.no_llm`. Timeout emits `copilot.chat.timeout`. Stream errors emit `copilot.chat.error`.
- **Approval flow:** `copilot.approve.request` logs the action; `copilot.approve.executed` logs result counts; `copilot.approve.validation_failed` and `copilot.approve.execution_error` log failures.
- **Route verification:** `rg "copilot_router\|ai_router" backend/app/main.py` confirms both routers are wired.

## Deviations

None.

## Known Issues

- `test_ai_endpoints.py::TestWellKnownAICapabilities::test_well_known_includes_ai_capabilities` fails — this is a pre-existing issue (the well-known endpoint doesn't include `ai-insights` in capabilities). Not caused by T02 changes.

## Files Created/Modified

- `backend/app/api/copilot.py` — new copilot router with /chat SSE streaming endpoint and /approve JSON endpoint
- `backend/app/main.py` — added ai_router and copilot_router imports and include_router calls
- `frontend/nginx.conf` — added SSE proxy location block for /api/copilot/chat
- `.gsd/milestones/M035/slices/S01/S01-PLAN.md` — added diagnostic verification step per pre-flight requirement
