---
id: T04
parent: S02
milestone: M028
provides:
  - 5 AI methods on SemPKMClient: getLLMStatus, detectClaims, matchClaims, suggestRelationships, summarizePage
  - 22 Node.js unit tests covering all AI methods, request construction, headers, and error handling
key_files:
  - extension/shared/api-client.js
  - extension/tests/test-ai-client.js
key_decisions:
  - ESM test file with .js extension works on Node v24 (auto-detects import syntax) — no .mjs needed and no package.json "type":"module" required
patterns_established:
  - mockFetch(status, body) pattern with fetchCalls capture array for testing _request()-based client methods
observability_surfaces:
  - node --test extension/tests/test-ai-client.js — 22 tests / 7 suites verify all AI method contracts
  - grep -c for method names on api-client.js returns ≥6 as health signal
duration: 8m
verification_result: passed
completed_at: 2026-03-20T12:16:00-04:00
blocker_discovered: false
---

# T04: Add SemPKMClient AI methods and Node.js unit tests

**Added 5 AI methods (getLLMStatus, detectClaims, matchClaims, suggestRelationships, summarizePage) to SemPKMClient with 22 passing Node.js unit tests covering request construction, headers, and error handling.**

## What Happened

Added 5 new methods to `SemPKMClient` in `extension/shared/api-client.js`, all following the existing `_request()` pattern:
- `getLLMStatus()` — GET /api/llm/status
- `detectClaims({content, url, title})` — POST /api/ai/detect-claims
- `matchClaims({claims})` — POST /api/ai/match-claims
- `suggestRelationships({url, title, claims})` — POST /api/ai/suggest-relationships
- `summarizePage({content, graph_context})` — POST /api/ai/summarize

Created `extension/tests/test-ai-client.js` with 22 test cases across 7 suites using `node:test` and `node:assert/strict`. Tests mock global `fetch` to verify URL paths, HTTP methods, request body serialization, Authorization/Content-Type/Accept headers, default parameter values, and error handling across 401/400/500/503 status codes. Each error test confirms `SemPKMError` is thrown with correct `.status` and `.detail`.

Node v24 auto-detects ESM syntax in `.js` files so no `.mjs` extension or package.json `"type":"module"` was needed.

## Verification

- `node --check extension/shared/api-client.js` — zero errors
- `node --check extension/tests/test-ai-client.js` — zero errors
- `node --test extension/tests/test-ai-client.js` — 22 pass, 0 fail, 0 skipped (66ms)
- `grep -c 'getLLMStatus\|detectClaims\|matchClaims\|suggestRelationships\|summarizePage' extension/shared/api-client.js` — returns 6

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | 0.020s |
| 2 | `node --check extension/sidebar/sidebar.js` | 0 | ✅ pass | 0.020s |
| 3 | `node --check extension/shared/api-client.js` | 0 | ✅ pass | 0.020s |
| 4 | `node --test extension/tests/test-ai-client.js` | 0 | ✅ pass (22/22) | 0.103s |
| 5 | `grep -c 'getAIInsights\|acceptSuggestion\|...' service-worker.js` | 0 | ✅ pass (24) | <0.01s |
| 6 | `grep -c '_renderAIInsights\|...' sidebar.js` | 0 | ✅ pass (8) | <0.01s |
| 7 | `grep 'ai-insights' sidebar.html` | 0 | ✅ pass | <0.01s |
| 8 | `grep -c 'ai-claims\|...' sidebar.css` | 0 | ✅ pass (7) | <0.01s |
| 9 | `grep -c method names api-client.js` | 0 | ✅ pass (6) | <0.01s |

All 9 slice-level verification checks pass. This is the final task (T04) of slice S02.

## Diagnostics

- **Test regression:** Run `node --test extension/tests/test-ai-client.js` — any failure message identifies the exact method, field, or error path that broke.
- **Method presence:** `grep -c 'getLLMStatus\|detectClaims\|matchClaims\|suggestRelationships\|summarizePage' extension/shared/api-client.js` — should return ≥6.
- **Error shape:** All 5 methods throw `SemPKMError` on non-200 responses with `.status` (HTTP code) and `.detail` (backend error string) properties.

## Deviations

- Test file produces 22 tests (exceeds the plan's ~15-20 estimate) — added tests for default parameter values and LLM-unavailable response to improve coverage.

## Known Issues

None.

## Files Created/Modified

- `extension/shared/api-client.js` — Added 5 AI methods (~75 lines with JSDoc): getLLMStatus, detectClaims, matchClaims, suggestRelationships, summarizePage
- `extension/tests/test-ai-client.js` — New file (~250 lines): 22 unit tests covering all methods, request construction, headers, default parameters, and error handling
- `.gsd/milestones/M028/slices/S02/tasks/T04-PLAN.md` — Added Observability Impact section (pre-flight fix)
