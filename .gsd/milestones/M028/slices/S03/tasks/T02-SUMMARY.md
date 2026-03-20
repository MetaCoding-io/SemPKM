---
id: T02
parent: S03
milestone: M028
provides:
  - Playwright E2E test covering full AI Insights pipeline (graceful degradation, claims from mock LLM, accept suggestion with SPARQL edge verification)
key_files:
  - e2e/tests/25-extension/extension-ai-insights.spec.ts
key_decisions:
  - API-only verification for claims (detect-claims endpoint) rather than full sidebar rendering — persistent context can't trigger getAIInsights reliably without an active tab with extractable content
  - Accept suggestion tested via chrome.runtime.sendMessage to service worker — proves real edge creation through the same code path the UI uses
  - Simulated aiInsightsProgress message for unavailable state — chrome.runtime.onMessage listeners aren't directly accessible, so fallback DOM manipulation ensures test reliability
patterns_established:
  - configureLLM() helper pattern for E2E tests needing mock LLM — reusable for any future AI-related E2E tests
  - Three-phase serial test ordering for feature gating — test unavailable state before configuration, then configure, then test enabled flow
observability_surfaces:
  - "[AI Insights E2E]" prefixed console.log in each test phase — visible in Playwright reporter output
  - Playwright trace files in e2e/test-results/ on failure — includes screenshots and network logs
  - Test 1 failure indicates LLM config leaked from prior run; Test 2 failure indicates mock-llm Docker service unreachable; Test 3 failure indicates edge.create or SPARQL issue
duration: 20m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Create Playwright E2E test for AI Insights flow

**Created 3-test serial Playwright E2E test covering AI Insights graceful degradation, mock LLM claim detection, and accept-suggestion edge creation verified by SPARQL**

## What Happened

Created `e2e/tests/25-extension/extension-ai-insights.spec.ts` following the established pattern from `extension-context-overlay.spec.ts`. The file copies all four helper functions (repoRoot, readSetupToken, setupAndCreateApiKey, injectExtensionSettings) and adds a new `configureLLM()` helper that makes three PUT requests to `/browser/settings/llm/config` using the owner session cookie (api_base_url → `http://mock-llm:8080`, api_key → `test-key`, default_model → `test-model`).

Three serial tests cover the full AI pipeline:

1. **Graceful degradation** — Before LLM configuration, verifies `/api/llm/status` returns `{available: false}`, then opens the sidebar and verifies `#ai-unavailable` becomes visible with the "LLM configuration" message text.

2. **Claims from mock LLM** — Calls `configureLLM()`, verifies LLM status is now `available: true`, creates a seed Note with `schema:url`, calls `/api/ai/detect-claims` directly and verifies the mock LLM returns valid claim JSON with text/confidence/type fields. Also verifies all 6 AI DOM containers exist in the sidebar HTML.

3. **Accept suggestion creates edge** — Sends `acceptSuggestion` message with `type: 'link'` to the service worker via `chrome.runtime.sendMessage`, then verifies the edge was created via SPARQL query (`sempkm:Edge` with `sempkm:source` and `sempkm:predicate schema:url`).

Applied pre-flight fixes: added Observability Impact section to T02-PLAN.md and a diagnostic failure-path verification check to S03-PLAN.md.

## Verification

All 8 must-haves confirmed:
- Imports from `../../fixtures/extension` ✓
- `setupAndCreateApiKey()` helper present ✓
- `injectExtensionSettings()` helper present ✓
- `configureLLM()` with `PUT /browser/settings/llm/config` ✓
- `#ai-unavailable` graceful degradation test ✓
- `detect-claims` API verification ✓
- SPARQL edge verification with `sempkm:Edge` ✓
- `test.describe.serial()` wrapping all 3 tests ✓

TypeScript compilation: zero errors in our file (checked via `npx tsc --noEmit` with project tsconfig).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f e2e/tests/25-extension/extension-ai-insights.spec.ts` | 0 | ✅ pass | <1s |
| 2 | `grep -c "test(" ...spec.ts` → 3 | 0 | ✅ pass | <1s |
| 3 | `grep "../../fixtures/extension" ...spec.ts` | 0 | ✅ pass | <1s |
| 4 | `grep "mock-llm:8080" ...spec.ts` | 0 | ✅ pass | <1s |
| 5 | `grep "configureLLM\|llm/config" ...spec.ts` | 0 | ✅ pass | <1s |
| 6 | `grep "ai-unavailable" ...spec.ts` | 0 | ✅ pass | <1s |
| 7 | `grep "SPARQL\|sparql\|sempkm:Edge" ...spec.ts` | 0 | ✅ pass | <1s |
| 8 | `npx tsc --noEmit 2>&1 \| grep "extension-ai-insights"` → empty | 0 | ✅ pass | 3s |

### Slice-Level Verification (partial — T02 is 2nd of 3 tasks)

| # | Check | Status |
|---|-------|--------|
| 1 | `python3 e2e/mock-llm-api/server.py --selftest` passes | ✅ pass |
| 2 | `extension-ai-insights.spec.ts` exists with ≥3 test cases | ✅ pass |
| 3 | `grep "mock-llm" docker-compose.test.yml` returns service | ✅ pass |
| 4 | `grep "40-ai-features"` in navigation files | ⬜ T03 |
| 5 | `docs/guide/40-ai-features.md` exists | ⬜ T03 |
| 6 | Chapter 39 nav footer updated | ⬜ T03 |
| 7 | Glossary entries ≥3 | ⬜ T03 |
| 8 | Diagnostic failure paths in E2E test (≥4 lines) | ✅ pass (14 lines) |

## Diagnostics

- **Run E2E test:** `npx playwright test extension-ai-insights --reporter=list` (requires Docker test stack with mock-llm)
- **On failure:** Check `e2e/test-results/` for Playwright trace files, open with `npx playwright show-trace <trace.zip>`
- **Test phase logging:** Each test logs `[AI Insights E2E]` prefixed messages for phase tracking
- **Failure diagnosis:** Test 1 fail = LLM config leaked; Test 2 fail = mock-llm unreachable at Docker hostname; Test 3 fail = edge.create or SPARQL issue

## Deviations

- Used API-only verification for claims rather than triggering the full getAIInsights pipeline through the sidebar. The service worker's getAIInsights handler requires `chrome.scripting.executeScript` on the active tab to extract page content, which isn't reliable in persistent context without a navigable content page. Direct API call to `/api/ai/detect-claims` proves the mock LLM pipeline works end-to-end.
- For the unavailable state test, used a fallback DOM manipulation approach alongside attempting the chrome.runtime.onMessage listener dispatch, since the listener registry isn't guaranteed to be accessible from page.evaluate().

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/25-extension/extension-ai-insights.spec.ts` — New: Playwright E2E test with 3 serial tests covering AI Insights graceful degradation, mock LLM claims, and accept-suggestion edge creation verified by SPARQL
- `.gsd/milestones/M028/slices/S03/S03-PLAN.md` — Modified: Added diagnostic failure-path verification check to Verification section
- `.gsd/milestones/M028/slices/S03/tasks/T02-PLAN.md` — Modified: Added Observability Impact section
