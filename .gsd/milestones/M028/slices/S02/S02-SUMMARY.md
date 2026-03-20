---
id: S02
parent: M028
milestone: M028
provides:
  - AI Insights sidebar section with progressive rendering (claims → matches → suggestions → summary)
  - 5 service worker message handlers for AI pipeline orchestration (getAIInsights, getPageContent, acceptSuggestion, dismissSuggestion, getDismissedSuggestions)
  - 6 sidebar rendering functions (_initAIInsights, _renderUnavailable, _renderClaimsSection, _renderMatchesSection, _renderSuggestionsSection, _renderSummarySection)
  - Accept creates object+edge via two-step POST /api/commands pattern (4 suggestion type mappings)
  - Dismiss persists per-URL in chrome.storage.local and filters on subsequent loads
  - 5 new SemPKMClient AI methods (getLLMStatus, detectClaims, matchClaims, suggestRelationships, summarizePage)
  - 22 Node.js unit tests for AI client methods
  - Generation ID stale-update guard against results from prior page navigations
  - LLM-unavailable path shows "AI features require LLM configuration" message
requires:
  - slice: S01
    provides: 6 AI backend endpoints (detect-claims, match-claims, suggest-relationships, summarize, llm/status, llm/stream) with dual Bearer+cookie auth
affects:
  - S03
key_files:
  - extension/background/service-worker.js
  - extension/sidebar/sidebar.js
  - extension/sidebar/sidebar.html
  - extension/sidebar/sidebar.css
  - extension/shared/api-client.js
  - extension/tests/test-ai-client.js
key_decisions:
  - Progressive messaging via chrome.runtime.sendMessage with generationId for stale-update protection — each pipeline step sends a typed progress message that sidebar checks against current generation before rendering
  - Per-step error isolation in AI pipeline — if detect-claims fails, suggest-relationships still attempts; partial results render
  - Closure-based event handlers for Accept/Dismiss — captures suggestion object and DOM refs at render time, avoids data-attribute parsing at click time
  - Accept maps 4 suggestion types to distinct API command sequences (link → edge.create with schema:url, evidence → object.create + edge.create, supports → edge.create with res:supports, contradicts → edge.create with res:refutes)
patterns_established:
  - aiInsightsProgress message protocol with section identifiers (unavailable/claims/matches/suggestions/summary) and generationId for stale-update guard
  - _createAISubGroup(title, count) helper for reusable collapsible sub-groups in AI sections
  - Dismissed IRI filtering via Array.filter with indexOf check against in-memory _aiDismissedIris array (synced from chrome.storage.local on init)
  - mockFetch(status, body) + fetchCalls capture pattern for testing SemPKMClient methods in Node.js
observability_surfaces:
  - "[SemPKM] AI Insights: ..." console logs in service worker for each pipeline step (status check, content extraction, detect-claims, match-claims, suggest-relationships, summarize)
  - "[SemPKM Sidebar] AI Insights: init, generationId=..." and progress/stale messages in sidebar console
  - "[SemPKM] AI acceptSuggestion: ..." / "[SemPKM] AI dismissSuggestion: ..." console logs
  - chrome.storage.local keys dismissed_${url} inspectable in DevTools
  - DOM inspection: #ai-insights[hidden], #ai-loading[hidden], #ai-unavailable[hidden] for visibility states
  - node --test extension/tests/test-ai-client.js — 22 tests / 7 suites for API client contract verification
drill_down_paths:
  - .gsd/milestones/M028/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M028/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M028/slices/S02/tasks/T03-SUMMARY.md
  - .gsd/milestones/M028/slices/S02/tasks/T04-SUMMARY.md
duration: 58m
verification_result: passed
completed_at: 2026-03-20
---

# S02: Extension sidebar AI Insights UI

**Full AI Insights sidebar section with progressive rendering of claims, graph matches, relationship suggestions (Accept/Dismiss), and personalized summaries — consuming S01 backend endpoints via service worker message passing with generation-guarded stale-update protection.**

## What Happened

**T01 — Service worker AI pipeline** (20m): Added 5 message handlers to the service worker's existing `chrome.runtime.onMessage.addListener` block. The core `getAIInsights` handler orchestrates a sequential pipeline: extract page content via `chrome.scripting.executeScript` (truncated to 8000 chars) → check LLM status → detect claims → match claims → suggest relationships → summarize. Each step sends a typed `aiInsightsProgress` message with a `generationId` counter for stale-update protection. Each step has independent try/catch so partial results render (e.g., claims show even if match-claims fails). `acceptSuggestion` maps 4 suggestion types to distinct API command sequences matching the existing `addEvidence` pattern. `dismissSuggestion`/`getDismissedSuggestions` persist per-URL IRI arrays in `chrome.storage.local`. An `aiCache` LRU (50 entries) caches AI results per URL.

**T02 — Sidebar rendering** (18m): Added `#ai-insights` container to sidebar.html with inner section divs (`#ai-unavailable`, `#ai-loading`, `#ai-claims`, `#ai-matches`, `#ai-suggestions`, `#ai-summary`). Implemented 6 rendering functions in sidebar.js: `_initAIInsights()` starts the pipeline and sets up the `chrome.runtime.onMessage` listener for progress messages; `_renderClaimsSection()` creates claim cards with 4-color confidence badges (established=green, likely=blue, possible=amber, speculative=gray); `_renderMatchesSection()` nests matched objects under claim headers with 4-color indicator badges (contradicts=red, corroborates=green, contested=amber, related=gray) and renders research gaps as alert-style cards; `_renderSuggestionsSection()` renders cards with Accept/Dismiss buttons and data attributes; `_renderSummarySection()` renders a styled text panel; `_renderUnavailable()` shows the LLM configuration message. Loading text transitions progressively as each section arrives. A `_createAISubGroup()` helper provides reusable collapsible sub-groups. Added ~280 lines of CSS covering all badge variants, suggestion cards, summary panel, loading states, and empty-hide rules.

**T03 — Accept/Dismiss wiring** (12m): Wired click handlers on suggestion buttons using IIFE closures. Accept flow: disable buttons → "Accepting..." → send `acceptSuggestion` message → on success show green toast + replace buttons with "✓ Accepted" badge → on error re-enable + red toast. Dismiss flow: disable buttons → send `dismissSuggestion` → fade-out animation → remove card → update count badge or hide empty group. Dismissed IRIs pushed to in-memory `_aiDismissedIris` array so re-renders also filter without another chrome.storage round-trip. CSS additions: `.accepted` card state, `.accepted-badge`, `fadeSlideOut` keyframes animation.

**T04 — SemPKMClient AI methods + tests** (8m): Added 5 methods to `SemPKMClient` following the existing `_request()` pattern. Created `test-ai-client.js` with 22 Node.js unit tests across 7 suites verifying URL paths, HTTP methods, body serialization, Authorization/Content-Type/Accept headers, default parameters, and error handling (401/400/500/503 → `SemPKMError` with `.status` and `.detail`).

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `node --check extension/background/service-worker.js` | ✅ pass |
| 2 | `node --check extension/sidebar/sidebar.js` | ✅ pass |
| 3 | `node --check extension/shared/api-client.js` | ✅ pass |
| 4 | `node --test extension/tests/test-ai-client.js` — 22 pass, 0 fail | ✅ pass |
| 5 | Service worker has ≥5 message handler types (found 24) | ✅ pass |
| 6 | Sidebar has all 5 rendering functions + extras (found 8) | ✅ pass |
| 7 | `#ai-insights` container in sidebar.html | ✅ pass |
| 8 | CSS rules for ai-claims/ai-matches/ai-suggestions/ai-summary/ai-unavailable | ✅ pass |
| 9 | `dismissed_` key pattern in service-worker.js chrome.storage.local | ✅ pass |
| 10 | `acceptSuggestion` and `dismissSuggestion` message sends in sidebar.js | ✅ pass |

## Requirements Advanced

- EXT-29 — Accept/dismiss UI for AI suggestions: Accept creates object+edge via two-step pattern with 4 type mappings; Dismiss persists per-URL in chrome.storage.local and filters on subsequent loads. Fully implemented, awaiting E2E verification in S03.
- EXT-30 — Progressive loading: AI Insights section renders claims first, then matches, then suggestions, then summary as each API call completes. Loading text transitions progressively. Fully implemented, awaiting E2E verification in S03.
- EXT-31 — Graceful degradation when LLM unavailable: When LLM status returns `available: false`, sidebar shows "AI features require LLM configuration" message and stops pipeline. Fully implemented, awaiting E2E verification in S03.

## Requirements Validated

- none (E2E tests in S03 needed for full validation of EXT-29, EXT-30, EXT-31)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None — all 4 tasks executed as planned with zero deviations.

## Known Limitations

- No timeout on `#ai-loading` — if the pipeline hangs, the loading spinner remains indefinitely.
- V1 does not invalidate `aiCache` after Accept — accepted suggestions may reappear with "Accepted" badge state if cache serves stale data before navigation.
- Service worker uses direct `fetch()` calls (not SemPKMClient methods) for AI endpoints because service-worker.js is a classic script, not an ES module.

## Follow-ups

- S03 will add Playwright E2E tests with a mock LLM server exercising the full sidebar AI flow (claim detection → match → accept → verify edge).
- S03 will write Chapter 40 user guide documenting AI features.

## Files Created/Modified

- `extension/background/service-worker.js` — Added `_aiGenerationId` counter, `aiCache` LRU (50 entries), and 5 message handlers (getAIInsights pipeline, getPageContent, acceptSuggestion with 4 type mappings, dismissSuggestion, getDismissedSuggestions). File grew from 508 to 951 lines.
- `extension/sidebar/sidebar.js` — Added 12 AI DOM refs, generation ID state, `_initAIInsights()`, 5 section renderers, `_createAISubGroup()` helper, `aiInsightsProgress` message listener, Accept/Dismiss click handlers with loading states and toast notifications. File grew from 556 to ~1050 lines.
- `extension/sidebar/sidebar.html` — Added `#ai-insights` container with toggle header, loading state, unavailable message, and 4 section containers. File grew from 70 to 95 lines.
- `extension/sidebar/sidebar.css` — Added ~315 lines for AI section styling: confidence badges (4 colors), indicator badges (4 colors), claim type badges, match items, research gap cards, suggestion cards with Accept/Dismiss buttons, summary panel, accepted state, fade-out animation, loading spinner, unavailable message, empty-hide rules. File grew from 591 to ~970 lines.
- `extension/shared/api-client.js` — Added 5 AI methods (~75 lines with JSDoc): getLLMStatus, detectClaims, matchClaims, suggestRelationships, summarizePage.
- `extension/tests/test-ai-client.js` — New file (~250 lines): 22 unit tests across 7 suites covering all AI methods, request construction, headers, default parameters, and error handling.

## Forward Intelligence

### What the next slice should know
- The sidebar AI Insights section is fully wired end-to-end: service worker pipeline → progress messages → sidebar rendering → accept/dismiss actions. S03 E2E tests should focus on mocking the 5 backend AI endpoints and verifying the sidebar renders each section correctly.
- The `aiInsightsProgress` message protocol uses `section` identifiers: `unavailable`, `claims`, `matches`, `suggestions`, `summary`. The E2E mock LLM server needs to make the backend return valid JSON for each endpoint in sequence.
- Accept creates edges via `POST /api/commands` with the same Bearer auth pattern as all other extension API calls.

### What's fragile
- The generation ID stale-update guard (`_aiGenerationId`) works but rapid navigations during slow LLM calls could leave the loading spinner visible if the final `summary` message arrives with a stale ID. The loading state hides only when all sections complete for the current generation.
- The `aiCache` keyed by URL means the same page content always returns cached results until cache eviction — there's no TTL, only LRU (50 entries).

### Authoritative diagnostics
- `node --test extension/tests/test-ai-client.js` — 22 tests prove the SemPKMClient API contract is correct. If backend schemas change, these tests break first.
- Service worker console filtered by `[SemPKM] AI Insights:` shows the exact pipeline step that failed when debugging runtime issues.
- `chrome.storage.local` → `dismissed_*` keys show per-URL dismiss state.

### What assumptions changed
- No assumptions changed — S01 backend endpoints matched the contract exactly as documented in the boundary map.
