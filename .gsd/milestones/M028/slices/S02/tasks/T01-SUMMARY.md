---
id: T01
parent: S02
milestone: M028
provides:
  - 5 message handlers in service worker for AI Insights pipeline (getAIInsights, getPageContent, acceptSuggestion, dismissSuggestion, getDismissedSuggestions)
  - AI result caching via LRU (aiCache) and stale-update guard via _aiGenerationId counter
key_files:
  - extension/background/service-worker.js
key_decisions:
  - Progressive messaging via chrome.runtime.sendMessage with generationId for stale-update protection
  - Per-step error isolation in AI pipeline — each API call wrapped in independent try/catch
patterns_established:
  - AI pipeline steps use incremental aiInsightsProgress messages with section identifiers and generationId
  - acceptSuggestion maps 4 suggestion types to distinct API command sequences matching addEvidence pattern
  - Dismissed suggestions stored per-URL in chrome.storage.local with key pattern dismissed_${url}
observability_surfaces:
  - "[SemPKM] AI Insights: ..." console logs for each pipeline step
  - "[SemPKM] AI acceptSuggestion: ..." console logs for suggestion acceptance
  - "[SemPKM] AI dismissSuggestion: ..." console logs for dismissal persistence
  - chrome.storage.local dismissed_${url} keys inspectable in DevTools
duration: 20m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Service worker AI pipeline and page content extraction

**Add 5 AI Insights message handlers to service worker: getAIInsights pipeline with progressive messaging, getPageContent, acceptSuggestion (4 type mappings), dismissSuggestion, getDismissedSuggestions**

## What Happened

Added `_aiGenerationId` counter and `aiCache` LRU (50 entries) alongside existing state variables. Implemented all 5 message handlers inside the existing `chrome.runtime.onMessage.addListener` block:

1. **`getPageContent`** — Extracts `document.body.innerText` from active tab via `chrome.scripting.executeScript`, truncates to 8000 chars, returns `{content, url, title}`. Handles `chrome.runtime.lastError` for restricted pages.

2. **`getAIInsights`** — Core pipeline orchestrator. Increments `_aiGenerationId`, checks `aiCache`, extracts page content, then sequentially calls: `GET /api/llm/status` → `POST /api/ai/detect-claims` → `POST /api/ai/match-claims` → `POST /api/ai/suggest-relationships` → `POST /api/ai/summarize`. Each step sends `{type: 'aiInsightsProgress', section, data, generationId}` via `chrome.runtime.sendMessage`. Each step has independent try/catch. Results cached in `aiCache` keyed by URL. LLM-unavailable path sends `section: 'unavailable'` and stops pipeline.

3. **`acceptSuggestion`** — Maps 4 suggestion types to API commands: `link` → `edge.create` with `schema:url`, `evidence` → two-step `object.create` (Evidence) + `edge.create` (supports), `supports` → `edge.create` (supports), `contradicts` → `edge.create` (refutes). Error handling mirrors existing `addEvidence` pattern.

4. **`dismissSuggestion`** — Reads/appends to `chrome.storage.local` key `dismissed_${url}`, deduplicates before write.

5. **`getDismissedSuggestions`** — Reads dismissed array from `chrome.storage.local`, returns `{dismissed: [...]}` (empty array if no key).

All handlers use `return true` for async `sendResponse` and follow existing coding patterns (async IIFE for complex handlers, callback-based for simple storage operations).

## Verification

- `node --check extension/background/service-worker.js` — passes (zero errors)
- All 5 message handler types found in file (24 total occurrences)
- `aiInsightsProgress` appears 13 times (all progress message sends)
- `generationId` appears 17 times (all progress messages + sendResponse)
- `chrome.storage.local` appears 4 times (dismiss read/write, getDismissed read)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 2 | `grep -c 'getAIInsights\|acceptSuggestion\|...' service-worker.js` | 0 (24) | ✅ pass | <1s |
| 3 | `grep -c 'aiInsightsProgress' service-worker.js` | 0 (13) | ✅ pass | <1s |
| 4 | `grep -c 'generationId' service-worker.js` | 0 (17) | ✅ pass | <1s |
| 5 | `grep -c 'chrome.storage.local' service-worker.js` | 0 (4) | ✅ pass | <1s |
| 6 | `node --check extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 7 | `node --check extension/shared/api-client.js` | 0 | ✅ pass | <1s |
| 8 | `grep 'ai-insights' sidebar.html` | 1 | ⏭️ skip (T02) | <1s |
| 9 | `grep render functions sidebar.js` | 0 (0) | ⏭️ skip (T02) | <1s |
| 10 | `grep css rules sidebar.css` | 1 | ⏭️ skip (T02) | <1s |

## Diagnostics

- **Pipeline tracing:** Filter service worker console for `[SemPKM] AI Insights:` to see each step (status check, content extraction, detect-claims, match-claims, suggest-relationships, summarize) with timing.
- **Accept/dismiss tracing:** Filter for `[SemPKM] AI acceptSuggestion:` and `[SemPKM] AI dismissSuggestion:`.
- **Dismiss inspection:** In DevTools Application → Storage → chrome.storage.local, look for keys matching `dismissed_*`.
- **Cache inspection:** `aiCache` is in-memory only; inspect via service worker console (`aiCache` reference).
- **Stale-update protection:** `_aiGenerationId` increments on each `getAIInsights` call; sidebar should discard progress messages with non-matching `generationId`.

## Deviations

None — implemented exactly as planned.

## Known Issues

None.

## Files Created/Modified

- `extension/background/service-worker.js` — Added `_aiGenerationId` counter, `aiCache` LRU, and 5 message handlers (`getPageContent`, `getAIInsights`, `acceptSuggestion`, `dismissSuggestion`, `getDismissedSuggestions`). File grew from 508 to 951 lines.
- `.gsd/milestones/M028/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix).
