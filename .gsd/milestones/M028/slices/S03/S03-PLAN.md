# S03: E2E tests and user guide

**Goal:** Playwright E2E test with mock LLM server exercises full AI Insights flow; Chapter 40 user guide documents AI features; all three navigation files updated.
**Demo:** `python e2e/mock-llm-api/server.py --selftest` passes; E2E test file exercises sidebar → claims → matches → accept suggestion → SPARQL verify edge; `grep "40-ai-features" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` returns matches in all 3 files.

## Must-Haves

- Mock LLM server serving OpenAI-compatible `/v1/chat/completions` with canned claim JSON, `/v1/models`, and `/health`
- Mock LLM server added to `docker-compose.test.yml` as `mock-llm` service on `sempkm-test` network
- Playwright E2E test in `e2e/tests/25-extension/extension-ai-insights.spec.ts` exercising full AI Insights flow
- E2E test configures LLM settings via `PUT /browser/settings/llm/config` pointing at `http://mock-llm:8080`
- E2E test verifies graceful degradation (LLM not configured → `#ai-unavailable` visible)
- E2E test verifies claim rendering in `#ai-claims`
- E2E test verifies Accept suggestion creates edge verified via SPARQL
- Chapter 40 user guide at `docs/guide/40-ai-features.md` covering claim detection, graph matching, suggestions, summaries, prerequisites, troubleshooting
- All 3 navigation files updated: `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`
- Chapter 39 navigation footer updated: Next → Chapter 40
- Glossary entries added to `docs/guide/appendix-d-glossary.md`

## Proof Level

- This slice proves: final-assembly (E2E test exercises full stack through mock LLM)
- Real runtime required: yes (Docker test stack with mock LLM server)
- Human/UAT required: no

## Verification

- `python e2e/mock-llm-api/server.py --selftest` — must report all checks passed
- `e2e/tests/25-extension/extension-ai-insights.spec.ts` exists with ≥3 test cases (graceful degradation, claims render, accept suggestion)
- `grep "mock-llm" docker-compose.test.yml` — returns service definition
- `grep "40-ai-features" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — returns matches in all 3 files
- `docs/guide/40-ai-features.md` exists with sections for claim detection, graph matching, suggestions, summaries, troubleshooting
- `tail -3 docs/guide/39-notion-import.md` — contains "Chapter 40" in navigation footer
- `grep -c "AI Insights\|Claim Detection\|Graph Matching" docs/guide/appendix-d-glossary.md` — returns ≥3
- `python -c "import subprocess, sys; r = subprocess.run(['python', 'e2e/mock-llm-api/server.py', '--selftest'], capture_output=True, text=True); sys.exit(0 if 'passed' in r.stdout and r.returncode == 0 else 1)"` — selftest passes with structured pass/fail output
- `grep "ai-unavailable\|configureLLM\|SPARQL\|sempkm:Edge" e2e/tests/25-extension/extension-ai-insights.spec.ts | wc -l` — returns ≥4 (E2E test covers graceful degradation AND edge verification failure paths)

## Integration Closure

- Upstream surfaces consumed: S01 backend AI endpoints (`/api/ai/detect-claims`, `/api/ai/match-claims`, `/api/ai/suggest-relationships`, `/api/ai/summarize`, `/api/llm/status`), S02 extension sidebar (`sidebar.js`, `sidebar.html`, `service-worker.js`), LLM config API (`PUT /browser/settings/llm/config`)
- New wiring introduced in this slice: `mock-llm` Docker service in `docker-compose.test.yml`, E2E test configures LLM settings at runtime via Settings API
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Observability / Diagnostics

**Runtime signals:**
- Mock LLM server logs all requests to stderr: `[mock-llm] POST /v1/chat/completions` — visible in `docker compose logs mock-llm`
- Mock LLM healthcheck at `GET /health` returns `{"status":"ok"}` — Docker uses this for service readiness
- API service logs LLM connection attempts to stderr; `docker compose logs api | grep -i llm` surfaces configuration issues
- E2E test failures produce Playwright trace files in `e2e/test-results/` with screenshots and network logs

**Inspection surfaces:**
- `python e2e/mock-llm-api/server.py --selftest` — validates all mock endpoints without Docker
- `docker compose -f docker-compose.test.yml ps` — shows mock-llm health status
- `curl http://localhost:8080/health` (inside mock-llm container) — liveness check
- `curl http://localhost:8080/v1/models` — returns model list confirming server is operational

**Failure visibility:**
- Mock LLM returns HTTP 404 with `{"message": "Not Found"}` for unrecognized paths — structured JSON errors
- Selftest prints per-check pass/fail with `✓`/`✗` markers and exits non-zero on any failure
- Docker healthcheck failures surface as `unhealthy` status in `docker compose ps`, blocking dependent services

**Redaction constraints:**
- Mock server uses hardcoded test data only; no real API keys or user data are involved
- The `api_key` used in E2E tests is the literal string `"test-key"` — not a real credential

## Tasks

- [x] **T01: Create mock LLM server and add to Docker compose** `est:45m`
  - Why: The E2E test needs a deterministic LLM that returns canned claim JSON. Without this, AI endpoints return 503 ("LLM not configured") and the pipeline can't execute.
  - Files: `e2e/mock-llm-api/server.py`, `docker-compose.test.yml`
  - Do: Create `e2e/mock-llm-api/server.py` following the `e2e/mock-jira-api/server.py` pattern exactly (BaseHTTPRequestHandler, `--selftest` mode, canned responses). Serve 3 endpoints: `POST /v1/chat/completions` (returns OpenAI-format response with `choices[0].message.content` containing `{"claims": [...]}` JSON), `GET /v1/models` (returns model list for connection test), `GET /health` (liveness). Add `mock-llm` service to `docker-compose.test.yml` with Python 3.12-slim image, volume mount, healthcheck, and `sempkm-test` network.
  - Verify: `python e2e/mock-llm-api/server.py --selftest` reports all checks passed; `grep "mock-llm" docker-compose.test.yml` returns service definition
  - Done when: Mock LLM server passes selftest and is wired into Docker compose

- [x] **T02: Create Playwright E2E test for AI Insights flow** `est:1h`
  - Why: Proves the full AI pipeline works end-to-end: extension sidebar → backend AI endpoints → mock LLM → graph matching → accept suggestion → edge creation. Validates EXT-32.
  - Files: `e2e/tests/25-extension/extension-ai-insights.spec.ts`
  - Do: Create E2E test using the `extension.ts` persistent context fixture. Reuse `setupAndCreateApiKey()` and `injectExtensionSettings()` helpers from `extension-context-overlay.spec.ts` (copy into this file). Test phases: (1) graceful degradation — before LLM config, open sidebar, verify `#ai-unavailable` shows; (2) configure LLM — three `PUT /browser/settings/llm/config` calls (api_base_url → `http://mock-llm:8080`, api_key → `test-key`, default_model → `test-model`) using owner session cookie; (3) seed a Note with `schema:url`; (4) open sidebar, inject settings, trigger AI pipeline via `chrome.runtime.sendMessage({type: 'getAIInsights'})`; (5) wait for `#ai-claims` to populate, verify claim cards; (6) accept a suggestion, verify edge via SPARQL query. **Critical constraint:** `api_base_url` must be `http://mock-llm:8080` (Docker-internal hostname, NOT localhost) because the Python backend inside Docker makes the LLM call.
  - Verify: File exists with ≥3 serial test cases; `node -e "require('typescript').createProgram(['e2e/tests/25-extension/extension-ai-insights.spec.ts'], {noEmit: true})"` or syntax check passes
  - Done when: E2E test file covers graceful degradation, claims rendering, and accept-suggestion-with-SPARQL-verification

- [x] **T03: Write Chapter 40 user guide and update navigation** `est:40m`
  - Why: Documents AI features for users. Validates EXT-33. Updates all 3 navigation files per KNOWLEDGE.md rule.
  - Files: `docs/guide/40-ai-features.md`, `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`, `docs/guide/39-notion-import.md`, `docs/guide/appendix-d-glossary.md`
  - Do: Write Chapter 40 covering: overview of AI Insights, prerequisites (LLM configuration, Research model for matching), claim detection (what it does, confidence levels), graph matching (contradiction/corroboration indicators), relationship suggestions (accept/dismiss), personalized summaries, troubleshooting (LLM not configured, no Research model, slow responses). Add TOC entry to README.md after line 68 (Notion Import). Add sidebar entry to index.html after Notion Import entry. Add button to guide.html between Notion Import and Appendix A. Update Chapter 39 nav footer: Next → Chapter 40. Add Chapter 40 nav footer: Previous → Chapter 39, Next → Appendix A. Add 3 glossary entries (AI Insights, Claim Detection, Graph Matching) to appendix-d-glossary.md.
  - Verify: `grep "40-ai-features" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` returns matches in all 3 files; `tail -3 docs/guide/39-notion-import.md` contains "Chapter 40"; `grep -c "AI Insights\|Claim Detection\|Graph Matching" docs/guide/appendix-d-glossary.md` ≥ 3
  - Done when: Chapter 40 exists with all sections, all 3 navigation files updated, Chapter 39 footer updated, 3 glossary entries added

## Files Likely Touched

- `e2e/mock-llm-api/server.py` (new)
- `docker-compose.test.yml`
- `e2e/tests/25-extension/extension-ai-insights.spec.ts` (new)
- `docs/guide/40-ai-features.md` (new)
- `docs/guide/README.md`
- `docs/guide/index.html`
- `backend/app/templates/guide.html`
- `docs/guide/39-notion-import.md`
- `docs/guide/appendix-d-glossary.md`
