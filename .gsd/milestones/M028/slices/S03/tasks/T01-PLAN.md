---
estimated_steps: 6
estimated_files: 2
---

# T01: Create mock LLM server and add to Docker compose

**Slice:** S03 — E2E tests and user guide
**Milestone:** M028

## Description

Create a mock OpenAI-compatible LLM server for E2E testing that returns canned claim JSON responses. This is the gating dependency for the E2E test — without a deterministic LLM server, the AI endpoints return 503 and the pipeline can't execute. Follow the established `e2e/mock-jira-api/server.py` pattern exactly (BaseHTTPRequestHandler + `--selftest` mode).

The mock must serve three endpoints:
- `POST /v1/chat/completions` — returns an OpenAI-format response with `choices[0].message.content` containing structured claim JSON
- `GET /v1/models` — returns a model list (used by the LLM connection test in Settings)
- `GET /health` — liveness check for Docker healthcheck

## Steps

1. **Create `e2e/mock-llm-api/server.py`** following the `e2e/mock-jira-api/server.py` pattern:
   - Import from `http.server` (BaseHTTPRequestHandler, HTTPServer), `json`, `sys`, `email` (for selftest)
   - Set `PORT = 8080`
   - Define canned response data:
     - `MODELS_RESPONSE` — `{"object": "list", "data": [{"id": "test-model", "object": "model", "created": 1700000000, "owned_by": "test"}]}`
     - `CLAIMS_RESPONSE` — The content string that the mock LLM "generates". Must be valid JSON matching the `_parse_claims_response()` parser expectations: `{"claims": [{"text": "Climate change is accelerating global ice loss", "confidence": "likely", "type": "factual"}, {"text": "Arctic sea ice extent reached a record low in 2023", "confidence": "established", "type": "statistical"}, {"text": "Current models underestimate permafrost thaw rates", "confidence": "speculative", "type": "analytical"}]}`
     - `CHAT_COMPLETION_RESPONSE` — Full OpenAI envelope: `{"id": "chatcmpl-mock-001", "object": "chat.completion", "created": 1700000000, "model": "test-model", "choices": [{"index": 0, "message": {"role": "assistant", "content": <CLAIMS_RESPONSE as string>}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}`
   - Implement `MockLLMHandler(BaseHTTPRequestHandler)`:
     - `do_GET()`: route `/health` → 200 `{"status":"ok"}`, `/v1/models` → 200 `MODELS_RESPONSE`, else → 404
     - `do_POST()`: route `/v1/chat/completions` → 200 `CHAT_COMPLETION_RESPONSE`, else → 404
     - `_json_response(status, body)` helper: send_response, send Content-Type header, end_headers, write json.dumps(body)
     - `_log_request(method, path)` helper: print to stderr for debugging
     - Suppress default request logging with `log_message` override
   - Implement `selftest()` function:
     - Construct test requests using the same `SilentHandler` subclass pattern from `mock-jira-api/server.py`
     - Test cases: (1) `GET /health` → 200, (2) `GET /v1/models` → 200 with "test-model" in response, (3) `POST /v1/chat/completions` → 200 with claims array in response content, (4) `GET /unknown` → 404, (5) `POST /unknown` → 404
     - Print `[mock-llm] selftest: N/N checks passed` and `sys.exit(0)` on success, `sys.exit(1)` on failure
   - Implement `__main__` block: `--selftest` → selftest(), else start server on `0.0.0.0:8080`

2. **Add `mock-llm` service to `docker-compose.test.yml`**:
   - Add after the `mock-monday` service block (before `frontend`)
   - Follow the exact pattern of `mock-jira`:
     ```yaml
     mock-llm:
       image: python:3.12-slim
       volumes:
         - ./e2e/mock-llm-api:/app:ro
       working_dir: /app
       command: ["python", "server.py"]
       healthcheck:
         test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
         interval: 3s
         timeout: 3s
         retries: 5
       networks:
         - sempkm-test
     ```
   - Add `mock-llm` to the `api` service's `depends_on` section with `condition: service_healthy`
   - **Do NOT add a `MOCK_LLM_URL` environment variable** to the api service — the LLM URL is configured at runtime via the Settings API (stored in SQLite InstanceConfig), not via env vars

3. **Verify selftest passes**: Run `python e2e/mock-llm-api/server.py --selftest` from the working directory

## Must-Haves

- [ ] `e2e/mock-llm-api/server.py` exists with `BaseHTTPRequestHandler` serving 3 endpoints
- [ ] `POST /v1/chat/completions` returns OpenAI-format response with `choices[0].message.content` containing valid claim JSON
- [ ] `GET /v1/models` returns model list with "test-model"
- [ ] `GET /health` returns 200 with `{"status":"ok"}`
- [ ] `--selftest` mode validates all endpoints and reports pass/fail
- [ ] `docker-compose.test.yml` has `mock-llm` service with healthcheck on `/health`
- [ ] `api` service depends on `mock-llm` with `condition: service_healthy`
- [ ] No `MOCK_LLM_URL` env var added to api service

## Verification

- `python e2e/mock-llm-api/server.py --selftest` — reports all checks passed, exits 0
- `grep "mock-llm" docker-compose.test.yml` — returns service definition and api depends_on entry
- `python3 -c "import ast; ast.parse(open('e2e/mock-llm-api/server.py').read())"` — syntax valid
- `grep -c "MOCK_LLM_URL" docker-compose.test.yml` — returns 0 (no env var added)

## Inputs

- `e2e/mock-jira-api/server.py` — reference pattern for mock server structure, selftest, Docker integration
- `docker-compose.test.yml` — existing mock service configuration to follow
- S01 Summary — documents that `_parse_claims_response()` uses 3-strategy JSON parsing; the mock should return clean JSON (strategy 1: direct `json.loads`) in `{"claims": [{text, confidence, type}]}` format
- S01 Summary — documents that `POST /api/ai/detect-claims` calls `POST /v1/chat/completions` non-streaming with `stream: false`

## Expected Output

- `e2e/mock-llm-api/server.py` — new file (~250-350 lines): Mock OpenAI-compatible server with canned claim extraction response
- `docker-compose.test.yml` — modified: `mock-llm` service added, api depends_on updated

## Observability Impact

**New signals:**
- `[mock-llm]` prefixed stderr log lines for every request (method + path) — visible in `docker compose logs mock-llm`
- Docker healthcheck on `GET /health` — surfaces as healthy/unhealthy in `docker compose ps`

**Inspection:**
- `python e2e/mock-llm-api/server.py --selftest` — offline endpoint validation with per-check ✓/✗ output
- Selftest prints summary: `[mock-llm] selftest: N/N checks passed` and exits 0 on success, 1 on failure

**Failure state:**
- Unrecognized paths return `{"message": "Not Found"}` with HTTP 404 — structured JSON, not HTML error pages
- If mock-llm is unhealthy, Docker blocks `api` service startup (depends_on with service_healthy condition)
