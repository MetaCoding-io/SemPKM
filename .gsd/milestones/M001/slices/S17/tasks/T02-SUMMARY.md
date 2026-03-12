---
id: T02
parent: S17
milestone: M001
provides: []
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 
verification_result: passed
completed_at: 
blocker_discovered: false
---
# T02: 17-llm-connection-configuration 02

**# Phase 17 Plan 02: SSE Streaming Proxy Endpoint Summary**

## What Happened

# Phase 17 Plan 02: SSE Streaming Proxy Endpoint Summary

**One-liner:** SSE streaming proxy endpoint POST /browser/llm/chat/stream using httpx aiter_lines passthrough, plus nginx location block with proxy_buffering off for real-time LLM response delivery.

## What Was Built

### SSE Streaming Endpoint (`backend/app/browser/router.py`)

New endpoint `POST /browser/llm/chat/stream` added to the LLM Connection Configuration section:

- Accepts JSON body `{"messages": [...], "model": "optional-override"}`
- Retrieves encrypted API key via `LLMConfigService.get_decrypted_api_key()`
- Uses `httpx.AsyncClient(timeout=300.0)` with `client.stream()` + `aiter_lines()` for upstream SSE passthrough
- Returns `StreamingResponse(media_type="text/event-stream")` with `X-Accel-Buffering: no` and `Cache-Control: no-cache` headers
- Graceful error path: when LLM is not configured, yields `data: {"error": "LLM not configured"}\n\n` + `data: [DONE]\n\n`
- Exception handler yields SSE-formatted error event so the client always receives a clean termination
- Accessible to any authenticated user via `get_current_user` (not owner-only)

The `if line:` guard skips empty keep-alive lines that some providers send, and the 300s timeout accommodates long-form LLM responses.

### nginx SSE Location Block (`frontend/nginx.conf`)

New dedicated location block added before the catch-all `location /`:

```nginx
location /browser/llm/chat/stream {
    proxy_pass http://api:8000/browser/llm/chat/stream;
    proxy_buffering off;
    proxy_http_version 1.1;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    proxy_set_header Cache-Control "no-cache";
    proxy_set_header Connection "keep-alive";
    add_header X-Accel-Buffering "no";
    # + standard proxy headers (Host, X-Real-IP, Cookie, etc.)
}
```

Block ordering in nginx.conf:
1. `location /css/`
2. `location /js/`
3. `location = /setup.html`
4. `location = /login.html`
5. `location = /invite.html`
6. `location /api/`
7. **NEW: `location /browser/llm/chat/stream`** (line 49)
8. `location /` catch-all (line 69)

## Decisions Made

1. **aiter_lines() over aiter_bytes()** — `aiter_lines()` buffers across HTTP chunk boundaries, ensuring complete SSE lines are yielded; `aiter_bytes()` can split lines mid-chunk breaking SSE framing
2. **300s timeout** — Long LLM completions (multi-turn, large context) can take minutes; 10s would abort legitimate requests
3. **X-Accel-Buffering: no on response** — Defense-in-depth: tells nginx not to buffer even if the location block is missed or a future nginx reconfig drops it
4. **get_current_user (not require_role)** — The streaming endpoint is for end users (future AI Copilot), not admin config; owner sets config, all authenticated users consume it
5. **nginx location before catch-all** — Explicit placement is conventional best practice; avoids ambiguity even though nginx longest-prefix matching would select it anyway

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `backend/app/browser/router.py` contains `@router.post("/llm/chat/stream")`
- [x] `StreamingResponse` with `media_type="text/event-stream"` present
- [x] `aiter_lines()` used for upstream SSE passthrough
- [x] `X-Accel-Buffering: no` header on StreamingResponse
- [x] `frontend/nginx.conf` has `location /browser/llm/chat/stream` block
- [x] `proxy_buffering off` directive present in SSE location block
- [x] `proxy_read_timeout 300s` present
- [x] `proxy_http_version 1.1` present
- [x] nginx SSE block at line 49, before catch-all `location /` at line 69

## Self-Check: PASSED
