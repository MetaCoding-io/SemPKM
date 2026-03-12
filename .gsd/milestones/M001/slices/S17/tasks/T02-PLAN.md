# T02: 17-llm-connection-configuration 02

**Slice:** S17 — **Milestone:** M001

## Description

Implement the SSE streaming proxy endpoint for LLM chat completions and configure nginx to not buffer it. This is the foundation for the AI Copilot (v2.1) — it proxies streaming responses from any OpenAI-compatible provider to the browser without accumulating the full response server-side.

Purpose: Without this endpoint, streaming LLM responses cannot be delivered to the browser in real-time. Without the nginx configuration, responses are silently buffered and arrive all at once at the end.
Output: POST /browser/llm/chat/stream FastAPI endpoint + nginx SSE location block.

## Must-Haves

- [ ] "POST /browser/llm/chat/stream accepts {messages, model} JSON and returns a text/event-stream response"
- [ ] "SSE chunks from the upstream LLM provider are forwarded to the browser without buffering"
- [ ] "nginx does not buffer the /browser/llm/chat/stream response (proxy_buffering off)"
- [ ] "The streaming endpoint is accessible to any authenticated user (not owner-only — future copilot needs it)"

## Files

- `backend/app/browser/router.py`
- `frontend/nginx.conf`
