---
estimated_steps: 5
estimated_files: 2
skills_used: []
---

# T01: Upgrade mock LLM server with SSE streaming and copilot canned responses

**Slice:** S04 — LLM Test Harness & E2E Integration
**Milestone:** M035

## Description

The existing mock LLM server (`e2e/mock-llm-api/server.py`, 348 lines) only returns single JSON responses for claim detection (M028). The copilot endpoint (`POST /api/copilot/chat`) sends `stream: True` to the LLM and expects SSE-formatted chunks in the OpenAI streaming format. This task upgrades the mock server to support SSE streaming and adds pattern-matched canned responses for copilot scenarios, then adds the `mock-llm` service to `docker-compose.test.yml`.

## Steps

1. **Read the existing server** and understand the current handler structure. The server uses stdlib `http.server` only — no pip dependencies (it runs on `python:3.12-slim`).

2. **Add request body parsing** in `do_POST` for `/v1/chat/completions`. Parse the JSON body and check the `stream` field. Also extract the last user message content for pattern matching.

3. **Add copilot-specific canned responses** using message-content pattern matching:
   - If user message contains "how many" or "project" → return a response containing a fenced SPARQL block: ` ```sparql\nSELECT (COUNT(?s) AS ?count) WHERE { ?s a <http://example.org/bpkm#Project> }\n``` `
   - If user message contains "create" AND "task" → return a response containing a fenced JSON block: ` ```json\n{"action": "create_object", "type": "http://example.org/bpkm#Task", "label": "Review Q1 goals", "properties": {"http://purl.org/dc/terms/title": "Review Q1 goals"}}\n``` `
   - If user message contains "summarize" or "context" → return a prose response referencing objects (e.g., "Based on the linked Project and its 3 associated Tasks...")
   - Default → return a generic helpful response ("I can help you explore your knowledge graph...")
   - Keep the original CLAIMS_RESPONSE for when messages contain "claim" or "extract" keywords (backward compat with M028 AI extension tests)

4. **Implement SSE streaming** for when `stream: true`:
   - Set response headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`
   - Split the canned response content into words
   - For each word, emit an SSE chunk: `data: {"id":"chatcmpl-mock-stream","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"word "}}]}\n\n`
   - After all words, emit `data: [DONE]\n\n`
   - Flush after each chunk
   - When `stream: false` (or absent), return the existing single JSON envelope format

5. **Add `mock-llm` service to `docker-compose.test.yml`** following the `mock-linear` pattern exactly:
   - Image: `python:3.12-slim`
   - Volume: `./e2e/mock-llm-api:/app:ro`
   - Working dir: `/app`
   - Command: `python server.py`
   - Healthcheck: `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"`
   - Network: `sempkm-test`
   - Add to `api` service's `depends_on` with `condition: service_healthy`

6. **Extend the selftest** with new checks:
   - Streaming POST with `"stream": true` → verify SSE output starts with `data: ` and contains `[DONE]`
   - SPARQL-triggering message → verify response content contains `SELECT`
   - Create-task message → verify response content contains `create_object`
   - Non-streaming POST still works (existing claims check)

## Must-Haves

- [ ] SSE streaming produces valid OpenAI streaming chunk format (`data: {...}\n\n` lines ending with `data: [DONE]\n\n`)
- [ ] Pattern matching routes "how many projects" → SPARQL block, "create task" → JSON block, default → generic
- [ ] Non-streaming mode still works (backward compatibility with M028 claims detection)
- [ ] `mock-llm` service in `docker-compose.test.yml` follows the exact same pattern as `mock-linear`
- [ ] Selftest passes with all new checks plus existing checks

## Verification

- `python e2e/mock-llm-api/server.py --selftest` — all checks pass
- `docker compose -f docker-compose.test.yml config --quiet` — validates without errors

## Inputs

- `e2e/mock-llm-api/server.py` — existing mock LLM server (348 lines, stdlib only)
- `docker-compose.test.yml` — existing Docker test stack with 4 mock services

## Expected Output

- `e2e/mock-llm-api/server.py` — upgraded with SSE streaming, copilot canned responses, extended selftest
- `docker-compose.test.yml` — updated with `mock-llm` service
