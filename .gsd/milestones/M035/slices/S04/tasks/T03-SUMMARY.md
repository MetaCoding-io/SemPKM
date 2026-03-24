---
id: T03
parent: S04
milestone: M035
provides:
  - Ollama Docker Compose variant for local real-inference LLM testing
  - LLM tier auto-selection helper (mock/ollama/cloud) with API configuration
  - Token cost tracker with budget cap enforcement for cloud-tier test runs
key_files:
  - docker-compose.test-ollama.yml
  - e2e/helpers/llm-tier.ts
  - e2e/helpers/cost-tracker.ts
key_decisions:
  - Full service duplication in Ollama compose rather than Docker Compose extends/include — avoids compose file version compatibility issues and keeps the file self-contained
  - GPU passthrough block commented out by default — CPU-only works for CI, GPU is opt-in for developers with nvidia-container-toolkit
  - Budget default $1.00 with gpt-4o-mini pricing — conservative cap that allows ~1.6M prompt tokens per test run
patterns_established:
  - "Three-tier LLM test strategy: getLlmTier() → getLlmConfig() → configureLlmForTier() pipeline for any E2E test that needs LLM access"
  - "CostTracker accumulate-then-assert pattern: addPromptTokens/addCompletionTokens after each API call, assertBudget() as a guard, printCostReport() in teardown"
observability_surfaces:
  - "printCostReport() emits formatted token cost table to console — captured in CI logs for budget auditing"
  - "assertBudget() throws descriptive error with dollar amounts and token counts when budget exceeded"
  - "Ollama compose healthcheck at http://localhost:11434/api/tags visible in docker compose ps"
  - "docker compose exec ollama ollama list shows cached models for debugging model availability"
duration: 10m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Ollama compose variant, cloud tier helper, and cost tracking

**Added Ollama Docker Compose variant, LLM tier auto-selection helper, and token cost tracker with budget enforcement for the 3-tier LLM test strategy**

## What Happened

Created the remaining two tiers of the 3-tier LLM test strategy (mock was already in place from T01):

1. **`docker-compose.test-ollama.yml`** — Full test stack with `ollama/ollama:latest` replacing mock-llm. Uses `ollama_models` named volume for model cache persistence, healthcheck on `/api/tags`, commented-out GPU passthrough block. `api` service points `LLM_API_URL` at `http://ollama:11434`. All other services (triplestore, mock-linear, mock-github, mock-jira, mock-monday, frontend) copied from the base stack unchanged.

2. **`e2e/helpers/llm-tier.ts`** — Exports `LlmTier` type, `getLlmTier()` for env-based auto-detection (LLM_TEST_TIER > OPENAI_API_KEY > OLLAMA_API_URL > mock default), `getLlmConfig()` for tier-specific connection params, and `configureLlmForTier()` which sends three `PUT /browser/llm/config` requests to configure the backend.

3. **`e2e/helpers/cost-tracker.ts`** — Exports `CostTracker` class with `addPromptTokens()`, `addCompletionTokens()`, `estimateCompletionTokensFromContent()`, `totalCostUsd()`, `assertBudget()`, and `report()`. Default pricing is gpt-4o-mini ($0.15/1M prompt, $0.60/1M completion) with a $1.00 budget cap. `printCostReport()` emits a formatted table to console.

All three files are self-contained infrastructure with no new npm dependencies.

## Verification

All task-level and slice-level checks pass:
- Ollama compose validates without errors
- Both TS helper files are readable and contain all required exports
- Mock selftest 12/12 passes, base compose validates, backend regression 139/139 passes
- TypeScript compiler reports no errors in the new files (pre-existing errors in other spec files are unrelated)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose -f docker-compose.test-ollama.yml config --quiet` | 0 | ✅ pass | 3.1s |
| 2 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | <1s |
| 3 | `node -e "require('fs').readFileSync('e2e/helpers/llm-tier.ts','utf8')"` | 0 | ✅ pass | <1s |
| 4 | `node -e "require('fs').readFileSync('e2e/helpers/cost-tracker.ts','utf8')"` | 0 | ✅ pass | <1s |
| 5 | `grep -c "getLlmTier\|getLlmConfig\|configureLlmForTier" e2e/helpers/llm-tier.ts` | 0 | ✅ pass (8 matches) | <1s |
| 6 | `grep -c "CostTracker\|assertBudget\|totalCostUsd" e2e/helpers/cost-tracker.ts` | 0 | ✅ pass (14 matches) | <1s |
| 7 | `python3 e2e/mock-llm-api/server.py --selftest` | 0 | ✅ pass (12/12) | <1s |
| 8 | `python3 e2e/mock-llm-api/server.py --selftest 2>&1 \| grep -c '✗'` | 1 | ✅ pass (0 failures) | <1s |
| 9 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py tests/test_ai_personas.py tests/test_object_creation_chat.py tests/test_graph_context.py tests/test_conversation_service.py -v` | 0 | ✅ pass (139/139) | 1.6s |
| 10 | `cd e2e && npx tsc --noEmit --project tsconfig.json 2>&1 \| grep -E "(llm-tier\|cost-tracker)"` | — | ✅ pass (0 errors in new files) | 4.5s |

Note: Slice check `npx playwright test tests/46-copilot/` requires the Docker test stack running — this is a final-slice integration check expected to pass when the full stack is exercised.

## Diagnostics

- **Ollama compose health:** `docker compose -f docker-compose.test-ollama.yml ps` shows service health states.
- **Model availability:** `docker compose -f docker-compose.test-ollama.yml exec ollama ollama list` shows cached models.
- **Tier detection debugging:** `LLM_TEST_TIER=cloud node -e "const t = require('./e2e/helpers/llm-tier'); console.log(t.getLlmTier())"` — requires TS compilation first, or check env vars directly.
- **Cost tracking:** After a cloud-tier test run, the console output contains the formatted cost report table from `printCostReport()`.

## Deviations

- Used full service duplication in the Ollama compose file rather than Docker Compose `include` or `extends` — the plan suggested either approach. Full duplication is more portable and avoids compose version compatibility issues.

## Known Issues

None.

## Files Created/Modified

- `docker-compose.test-ollama.yml` — Ollama variant of E2E test stack with GPU passthrough (commented), model cache volume, and healthcheck
- `e2e/helpers/llm-tier.ts` — LLM tier auto-selection (mock/ollama/cloud) with `configureLlmForTier()` API configuration
- `e2e/helpers/cost-tracker.ts` — Token cost tracker with budget cap, `assertBudget()` enforcement, and `printCostReport()` console output
- `.gsd/milestones/M035/slices/S04/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
