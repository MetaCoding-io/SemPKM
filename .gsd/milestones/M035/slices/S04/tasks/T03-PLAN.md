---
estimated_steps: 3
estimated_files: 3
skills_used: []
---

# T03: Ollama compose variant, cloud tier helper, and cost tracking

**Slice:** S04 — LLM Test Harness & E2E Integration
**Milestone:** M035

## Description

Create the remaining two tiers of the 3-tier LLM test strategy: an Ollama Docker Compose variant for local real-inference testing, and TypeScript helpers for automatic tier selection and cloud cost tracking with budget caps. These are infrastructure files used by developers and CI — they don't modify any existing application code.

## Steps

1. **Create `docker-compose.test-ollama.yml`** that extends the test stack with an Ollama service:
   - Use Docker Compose `include` or services overlay approach (reference `docker-compose.test.yml` services)
   - Add `ollama` service using `ollama/ollama:latest` image
   - Mount a named volume `ollama_models` at `/root/.ollama` for model cache persistence
   - Add a `deploy.resources.reservations.devices` block for GPU passthrough (optional, documented)
   - Healthcheck: `curl -f http://localhost:11434/api/tags` (Ollama's model list endpoint)
   - Override the `api` service to add `depends_on: ollama: condition: service_healthy`
   - Document in a comment: after `docker compose -f docker-compose.test-ollama.yml up -d`, run `docker compose -f docker-compose.test-ollama.yml exec ollama ollama pull llama3.2:1b` to download a small test model
   - The LLM config is set at test time via API: `PUT /browser/llm/config` with `api_base_url: http://ollama:11434` and `default_model: llama3.2:1b`
   - Network: `sempkm-test`

2. **Create `e2e/helpers/llm-tier.ts`** — tier auto-selection helper:
   - Export type `LlmTier = 'mock' | 'ollama' | 'cloud'`
   - Export `getLlmTier(): LlmTier` — checks in order:
     - `process.env.LLM_TEST_TIER` → use that value directly (explicit override)
     - `process.env.OPENAI_API_KEY` is set → `'cloud'`
     - `process.env.OLLAMA_API_URL` is set → `'ollama'`
     - Default → `'mock'`
   - Export `getLlmConfig(tier: LlmTier): { apiBaseUrl: string; model: string; apiKey: string }`:
     - `'mock'` → `{ apiBaseUrl: 'http://mock-llm:8080', model: 'test-model', apiKey: 'sk-mock-test-key' }`
     - `'ollama'` → `{ apiBaseUrl: process.env.OLLAMA_API_URL || 'http://ollama:11434', model: process.env.OLLAMA_MODEL || 'llama3.2:1b', apiKey: 'ollama' }`
     - `'cloud'` → `{ apiBaseUrl: process.env.OPENAI_API_BASE || 'https://api.openai.com', model: process.env.OPENAI_MODEL || 'gpt-4o-mini', apiKey: process.env.OPENAI_API_KEY || '' }`
   - Export `async configureLlmForTier(request: APIRequestContext, baseURL: string, tier?: LlmTier): Promise<LlmTier>` — calls `PUT /browser/llm/config` three times to set `api_base_url`, `default_model`, and `api_key` for the detected tier. Returns the tier used.

3. **Create `e2e/helpers/cost-tracker.ts`** — token counting and budget cap:
   - Export class `CostTracker`:
     - Constructor takes `{ budgetUsd?: number; costPer1kPromptTokens?: number; costPer1kCompletionTokens?: number }` with defaults `{ budgetUsd: 1.0, costPer1kPromptTokens: 0.00015, costPer1kCompletionTokens: 0.0006 }` (gpt-4o-mini pricing)
     - `addPromptTokens(count: number)` — accumulate prompt token count
     - `addCompletionTokens(count: number)` — accumulate completion token count
     - `estimateCompletionTokensFromContent(content: string)` — rough estimate: `Math.ceil(content.length / 4)` (same heuristic as CopilotService)
     - `totalCostUsd(): number` — compute cost from accumulated tokens
     - `assertBudget()` — throws if `totalCostUsd()` exceeds `budgetUsd`
     - `report(): { promptTokens: number; completionTokens: number; totalCostUsd: number; budgetUsd: number; budgetRemaining: number }` — return a summary object
   - Export `function printCostReport(tracker: CostTracker): void` — logs the report to console in a formatted table

## Must-Haves

- [ ] Ollama compose file is valid (`docker compose -f docker-compose.test-ollama.yml config --quiet`)
- [ ] Tier helper exports `getLlmTier()`, `getLlmConfig()`, and `configureLlmForTier()` functions
- [ ] Cost tracker exports `CostTracker` class with `addPromptTokens()`, `addCompletionTokens()`, `totalCostUsd()`, `assertBudget()`, and `report()`
- [ ] All three files are self-contained with no new npm dependencies

## Verification

- `docker compose -f docker-compose.test-ollama.yml config --quiet` — validates without errors
- `node -e "require('fs').readFileSync('e2e/helpers/llm-tier.ts','utf8')"` — file exists and is readable
- `node -e "require('fs').readFileSync('e2e/helpers/cost-tracker.ts','utf8')"` — file exists and is readable
- `grep -c "getLlmTier\|getLlmConfig\|configureLlmForTier" e2e/helpers/llm-tier.ts` — returns 3+
- `grep -c "CostTracker\|assertBudget\|totalCostUsd" e2e/helpers/cost-tracker.ts` — returns 3+

## Inputs

- `docker-compose.test.yml` — base test stack (T01 output with mock-llm service)
- `e2e/fixtures/auth.ts` — for `APIRequestContext` type import in tier helper

## Expected Output

- `docker-compose.test-ollama.yml` — Ollama Docker Compose variant
- `e2e/helpers/llm-tier.ts` — LLM tier auto-selection helper
- `e2e/helpers/cost-tracker.ts` — token counting and budget cap utility

## Observability Impact

- **Tier selection logging:** `getLlmTier()` returns the resolved tier — callers can log which tier was activated for each test run, enabling CI debugging when the wrong backend is selected.
- **Cost report:** `printCostReport()` emits a formatted token-cost summary to the console after cloud-tier test runs. CI logs capture this for per-run budget auditing.
- **Budget enforcement:** `assertBudget()` throws a descriptive error (`Budget exceeded: $X.XX / $Y.YY`) when cloud costs exceed the cap — test suite fails fast with a clear message rather than silently accumulating charges.
- **Ollama health:** The compose healthcheck (`curl -f http://localhost:11434/api/tags`) surfaces Ollama readiness in `docker compose ps` and container logs. GPU passthrough issues are visible as repeated healthcheck failures.
- **Inspection surfaces:** `docker compose -f docker-compose.test-ollama.yml ps` shows Ollama service health. `docker compose exec ollama ollama list` shows cached models.
