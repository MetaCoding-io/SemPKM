# S03: E2E tests and user guide — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S03 delivers two independent outputs: (1) a Playwright E2E test with a mock LLM server exercising the full AI Insights flow (sidebar → claims → matches → accept suggestion → verify edge via SPARQL), and (2) Chapter 40 user guide documenting AI features with all three navigation files updated.

The work is straightforward — all patterns are established. The mock LLM server follows the exact pattern of `e2e/mock-jira-api/server.py` (Python HTTP server with selftest mode, Docker service in docker-compose.test.yml). The E2E test follows `extension-context-overlay.spec.ts` (persistent context fixture, direct API calls for setup/injection, chrome.runtime.sendMessage for sidebar interactions). The user guide follows the Chapter 39 pattern (markdown file, README.md + index.html + guide.html updates, navigation chain, glossary entries).

The one subtlety is that the LLM is not configured via environment variable — it's stored in SQLite `instance_config` rows via `LLMConfigService.save_config()`. The E2E test must configure LLM settings through the Settings API (`PUT /browser/settings/llm/config`) to point at the mock LLM server before the AI pipeline can execute.

## Recommendation

Split into three independent tasks: (1) mock LLM server + Docker compose integration, (2) E2E Playwright test, (3) Chapter 40 user guide + navigation updates. Tasks 1 and 3 are fully independent. Task 2 depends on Task 1.

Build the mock LLM server first — it unblocks the E2E test and can be verified with `--selftest` in isolation.

## Implementation Landscape

### Key Files

**Mock LLM Server (new):**
- `e2e/mock-llm-api/server.py` — new mock OpenAI-compatible server. Must serve `POST /v1/chat/completions` (non-streaming, returns canned claim JSON), `GET /v1/models` (for connection test), `GET /health` (liveness). Follow `e2e/mock-jira-api/server.py` pattern exactly (BaseHTTPRequestHandler + `--selftest` mode).

**Docker Compose:**
- `docker-compose.test.yml` — add `mock-llm` service (Python 3.12-slim, mount `./e2e/mock-llm-api`, healthcheck on `/health`, network `sempkm-test`). Add `MOCK_LLM_URL: http://mock-llm:8080` to api environment is NOT needed — LLM URL is stored in SQLite InstanceConfig, not env vars. The E2E test configures this at runtime via the Settings API.

**E2E Test (new):**
- `e2e/tests/25-extension/extension-ai-insights.spec.ts` — new test file using the `extension.ts` persistent context fixture. Phases: setup auth + API key → configure LLM settings via PUT `/browser/settings/llm/config` (point api_base_url at `http://localhost:{MOCK_LLM_PORT}`) → seed a Note with schema:url → install research model → open sidebar → trigger AI insights → verify claims render → verify matches render → accept a "link" suggestion → verify edge via SPARQL.

**User Guide (new):**
- `docs/guide/40-ai-features.md` — new chapter covering: claim detection (what it does, how it works), graph matching (contradiction/corroboration), relationship suggestions (accept/dismiss), personalized summaries, prerequisites (LLM configuration), troubleshooting (LLM not configured, no Research model).

**Navigation Files (modify):**
- `docs/guide/README.md` — add `40. [AI Features](40-ai-features.md)` after line 39 (Notion Import)
- `docs/guide/index.html` — add `<li><a href="#" data-file="40-ai-features.md">40. AI Features</a></li>` after the Notion Import entry
- `backend/app/templates/guide.html` — add `<button>` element for Chapter 40 between Notion Import and Appendix A
- `docs/guide/39-notion-import.md` — update navigation footer: Next → Chapter 40
- `docs/guide/40-ai-features.md` — navigation footer: Previous → Chapter 39, Next → Appendix A
- `docs/guide/appendix-a-environment-variables.md` — no new env vars needed (LLM is configured in-app via Settings, not env vars)
- `docs/guide/appendix-d-glossary.md` — add glossary entries: AI Insights, Claim Detection, Graph Matching

### Build Order

1. **Task 1: Mock LLM server** — Create `e2e/mock-llm-api/server.py` serving OpenAI-compatible `/v1/chat/completions` with canned claim extraction response. Add to `docker-compose.test.yml`. Verify with `python server.py --selftest`.

2. **Task 2: E2E Playwright test** — Create `extension-ai-insights.spec.ts`. The test must:
   - Set up auth + API key (reuse `setupAndCreateApiKey()` from `extension-context-overlay.spec.ts`)
   - Configure LLM settings via three `PUT /browser/settings/llm/config` calls (api_base_url → mock LLM URL, api_key → "test-key", default_model → "test-model") using the owner session cookie
   - Optionally install the research model for Claim matching (or skip — match-claims works without it, returns empty matches)
   - Create a seed Note with a known `schema:url`
   - Open sidebar, inject settings, trigger AI insights pipeline
   - Wait for `#ai-claims` to populate (claims from mock LLM)
   - Verify suggestion cards render in `#ai-suggestions`
   - Click Accept on a suggestion
   - Verify edge created via SPARQL query
   - Verify graceful degradation: when LLM not configured, `#ai-unavailable` shows

3. **Task 3: Chapter 40 user guide** — Write `40-ai-features.md`, update all 3 navigation files, update Chapter 39 nav footer, add glossary entries.

### Verification Approach

**Task 1:** `python e2e/mock-llm-api/server.py --selftest` — must report all checks passed.

**Task 2:** The E2E test can be run with `npx playwright test e2e/tests/25-extension/extension-ai-insights.spec.ts` against the Docker test stack (requires `docker compose -f docker-compose.test.yml up -d`). Since extension tests need persistent context, they're Chromium-only.

**Task 3:** Verify: `docs/guide/40-ai-features.md` exists with expected sections, `grep "40-ai-features" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` returns matches in all 3 files, navigation footer chain is correct (Ch 39 → Ch 40 → Appendix A).

## Constraints

- **LLM config is in SQLite, not env vars** — The mock LLM URL must be set at runtime via `PUT /browser/settings/llm/config` with an owner session cookie, not via docker-compose environment variables. The `LLMConfigService.save_config()` stores api_base_url in `instance_config` table.
- **Extension tests use persistent context** — `chromium.launchPersistentContext()` with `--load-extension`. No Firefox support. Import from `../../fixtures/extension`.
- **Mock LLM must be accessible from the API container** — The API container makes the actual LLM call via httpx. The mock LLM runs in Docker on the `sempkm-test` network, so the API container addresses it as `http://mock-llm:8080`. But the E2E test configures the api_base_url from the host perspective — so the URL stored in InstanceConfig must be `http://mock-llm:8080` (the Docker-internal hostname), NOT `http://localhost:PORT`.
- **Three navigation files must be updated together** — `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html` (per KNOWLEDGE.md rule "User guide has THREE files that must stay in sync").

## Common Pitfalls

- **Mock LLM URL must use Docker-internal hostname** — The api_base_url set via the Settings API is used by the Python backend (inside Docker) to call the LLM. It must be `http://mock-llm:8080`, not `http://localhost:XXXX`. The E2E test runs on the host but configures a URL used inside Docker.
- **LLM config requires owner role** — `PUT /browser/settings/llm/config` uses `require_role("owner")`. The E2E test's owner session cookie handles this.
- **Claim detection needs non-empty content** — `POST /api/ai/detect-claims` returns 400 if content is empty. The sidebar extracts content via `chrome.scripting.executeScript` from the active tab. In the E2E test, inject content directly or navigate to a real page.
- **chrome.storage.sync unreliability** — Per KNOWLEDGE.md, use `chrome.storage.local` injection for settings (not sync). The existing `injectExtensionSettings()` helper from `extension-context-overlay.spec.ts` handles this correctly.
- **Mock response must match parser expectations** — The `_parse_claims_response()` in `ai.py` uses a 3-strategy parser. The mock LLM should return clean JSON (strategy 1: direct `json.loads`) to avoid parser edge cases. The response must be in the `{"claims": [{...}]}` format, wrapped in the standard OpenAI `choices[0].message.content` envelope.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Mock API server pattern | `e2e/mock-jira-api/server.py` | Established pattern: BaseHTTPRequestHandler + selftest mode + Docker service |
| Extension test fixture | `e2e/fixtures/extension.ts` | Persistent context with `--load-extension`, service worker ID extraction |
| Auth + API key setup | `setupAndCreateApiKey()` in `extension-context-overlay.spec.ts` | Proven helper: setup token → magic link → session cookie → API key creation |
| Settings injection | `injectExtensionSettings()` in `extension-context-overlay.spec.ts` | Works around chrome.storage.sync unreliability |
| SPARQL edge verification | Pattern from `extension-context-overlay.spec.ts` test 4 | Proven SPARQL query for `sempkm:Edge` verification |
| User guide chapter structure | `docs/guide/39-notion-import.md` | Most recent chapter — follow its heading structure, nav footer pattern |

## Sources

- `e2e/mock-jira-api/server.py` — reference mock server (BaseHTTPRequestHandler, `--selftest`, canned responses)
- `e2e/tests/25-extension/extension-context-overlay.spec.ts` — reference extension E2E test (persistent context, API setup, sidebar interaction, SPARQL verification)
- `e2e/fixtures/extension.ts` — extension test fixture (persistent context, service worker ID)
- `docker-compose.test.yml` — existing mock service configuration (mock-linear, mock-github, mock-jira, mock-monday)
- `backend/app/api/ai.py` — all 6 AI endpoints (line 536: detect-claims uses `/v1/chat/completions` non-streaming)
- `backend/app/services/llm.py` — LLMConfigService (api_base_url stored in InstanceConfig SQLite table)
- `backend/app/browser/settings.py` line 113 — `PUT /browser/settings/llm/config` for configuring LLM base URL
- `extension/background/service-worker.js` line 476 — AI pipeline orchestrator (getAIInsights handler)
- `extension/sidebar/sidebar.html` — AI Insights DOM structure (#ai-insights, #ai-claims, #ai-matches, #ai-suggestions, #ai-summary, #ai-unavailable)
- `docs/guide/39-notion-import.md` — most recent user guide chapter (navigation footer pattern)
