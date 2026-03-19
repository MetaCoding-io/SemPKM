---
id: T02
parent: S01
milestone: M015
provides:
  - Service worker context pipeline (tab listener → debounce → query → rank → cache → badge)
  - Pure utility module with rankResults, groupByType, LRUCache via globalThis.SemPKMContextUtils
  - Message handlers for sidebar communication (getContextResults, refreshContextResults)
  - Alt+K command handler to open side panel
key_files:
  - extension/shared/context-utils.js
  - extension/background/service-worker.js
key_decisions:
  - Inline fetch in service worker instead of importing ES module api-client.js (classic SW can't use import)
  - globalThis + module.exports dual-export pattern for context-utils.js (works in importScripts, Node require, and ES module wrapper)
patterns_established:
  - _getApiConfig() reads storage directly in service worker context (no ES module dependency)
  - importScripts('../shared/context-utils.js') for classic service worker loading
observability_surfaces:
  - "[SemPKM]" prefixed console logs for tab detection, cache hit/miss, query start/success/error, sidebar open
  - Badge "!" with red background on query error; teal badge with result count on success
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Build service worker context pipeline with debounce, cache, and badge

**Added context-utils.js (rankResults, groupByType, LRUCache) and extended service worker with tab navigation listener, 2s debounce, context query pipeline, per-tab badge, sidebar messaging, and Alt+K command handler**

## What Happened

Created `extension/shared/context-utils.js` as a pure utility module with three exports: `rankResults()` sorts by match_type priority (url > title > keyword) and truncates to 10; `groupByType()` clusters results by type_label preserving first-seen order; `LRUCache` is a Map-based LRU with configurable max size. The module assigns to `globalThis.SemPKMContextUtils` for service worker `importScripts()` and also supports `module.exports` for Node.js tests.

Extended `extension/background/service-worker.js` with the full context pipeline. The service worker can't import ES modules, so API calls use inline `fetch()` with `_getApiConfig()` reading credentials from `chrome.storage.sync`. The pipeline: `chrome.tabs.onUpdated` fires → filter for `status === 'complete'` + http URLs → check `autoCheckContext` setting → debounce via `setTimeout` (keyed by tabId, delay from `contextCheckDelay` setting) → `_handleTabReady` checks LRU cache → if miss, extract keywords from title, call `/api/context-query` with AbortController timeout → rank results → cache → set badge. Badge shows count (teal) or "!" (red) on error.

Added message handlers: `getContextResults` returns cached results for the active tab; `refreshContextResults` forces a re-query bypassing cache. Added `chrome.commands.onCommand` listener for `open-context-sidebar` (Alt+K) using `chrome.sidePanel.open()` with Firefox `browser.sidebarAction.open()` fallback. All lifecycle events logged with `[SemPKM]` prefix.

## Verification

All four plan-specified checks pass:
- `node --check extension/shared/context-utils.js` — syntax OK
- `node --check extension/background/service-worker.js` — syntax OK
- LRU smoke test (eviction at capacity 3) — passes
- Rank smoke test (URL match sorts before keyword match) — passes

Additional: groupByType smoke test (3 groups, null→"Other" mapping) passes.

Slice-level syntax checks: `node --check extension/shared/context-utils.js && node --check extension/shared/api-client.js` — all pass. `node --test extension/tests/test-context-utils.js` — test file not yet created (T04). Sidebar sideload verification pending T03.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/shared/context-utils.js` | 0 | ✅ pass | 15.1s |
| 2 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | 12.4s |
| 3 | LRU smoke test (eviction at max 3) | 0 | ✅ pass | 7.4s |
| 4 | Rank smoke test (URL before keyword) | 0 | ✅ pass | 3.1s |
| 5 | groupByType smoke test (3 groups, null→Other) | 0 | ✅ pass | <1s |
| 6 | Slice syntax: api-client.js + context-utils.js | 0 | ✅ pass | <1s |

## Diagnostics

- Open `chrome://extensions` → service worker "Inspect" → Console tab to see `[SemPKM]` prefixed logs
- Badge "!" (red) = query error; numeric (teal) = result count; empty = no results or unconfigured
- Cache state: `contextCache` is an LRU in service worker memory; cleared on service worker restart
- Debounce timers: `_debounceTimers` Map keyed by tabId; cleaned up on tab removal

## Deviations

None. Implementation follows the plan exactly, including the `globalThis` export pattern, inline fetch for the service worker (can't import ES modules), and the dual-message handler pattern.

## Known Issues

None.

## Files Created/Modified

- `extension/shared/context-utils.js` — new: pure functions (rankResults, groupByType, LRUCache) with globalThis + module.exports export
- `extension/background/service-worker.js` — extended: importScripts, tab listener with debounce, context query pipeline, LRU cache, per-tab badge, message handlers, Alt+K sidebar command, tab cleanup
