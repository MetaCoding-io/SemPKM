---
id: T02
parent: S02
milestone: M028
provides:
  - AI Insights section in sidebar with progressive rendering of claims, matches, suggestions, and summary
  - 6 rendering functions (_initAIInsights, _renderUnavailable, _renderClaimsSection, _renderMatchesSection, _renderSuggestionsSection, _renderSummarySection) plus _createAISubGroup helper
  - Generation ID stale-update guard for aiInsightsProgress messages
  - Dismissed IRI filtering before suggestion rendering
  - Full CSS for confidence badges (4 colors), indicator badges (4 colors), suggestion action buttons, summary panel, loading states
key_files:
  - extension/sidebar/sidebar.js
  - extension/sidebar/sidebar.html
  - extension/sidebar/sidebar.css
key_decisions:
  - AI Insights section uses same collapsible group pattern as context results (_renderGroup) via shared _createAISubGroup helper
  - Accept/Dismiss buttons rendered with data attributes for T03 wiring — no click handlers yet (T03 scope)
  - Loading text transitions are driven by aiInsightsProgress section messages, not by timeouts
  - Total AI item count in status badge computed by DOM query after summary arrives (single source of truth)
patterns_established:
  - _createAISubGroup(title, count) returns {section, body} for reusable collapsible sub-groups in AI sections
  - Stale-update check pattern: compare message.generationId === _aiGenerationId before rendering
  - Dismissed IRI filtering via Array.filter with indexOf check against _aiDismissedIris
observability_surfaces:
  - "[SemPKM Sidebar] AI Insights: init, generationId=" — logged on _initAIInsights
  - "[SemPKM Sidebar] AI Insights: progress section=, generationId=" — logged per progress message
  - "[SemPKM Sidebar] AI Insights: stale progress" — logged when discarding mismatched generationId
  - DOM: #ai-insights[hidden], #ai-loading[hidden], #ai-unavailable[hidden] — inspect visibility states
  - DOM: [data-suggestion-type], [data-target-iri], [data-suggestion-index] — suggestion card data attributes
duration: 18m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Sidebar AI Insights rendering with progressive loading

**Build AI Insights sidebar section with progressive rendering of claims (4 confidence badge colors), graph matches (4 indicator badge colors), suggestions with Accept/Dismiss buttons, summary panel, and loading state transitions**

## What Happened

Added the AI Insights container to sidebar.html after `#evidence-prompt` with inner section divs: `#ai-unavailable`, `#ai-loading`, `#ai-claims`, `#ai-matches`, `#ai-suggestions`, `#ai-summary`, wrapped in a collapsible `#ai-toggle` header.

In sidebar.js, added 12 DOM refs for AI elements, `_aiGenerationId` and `_aiDismissedIris` state variables. Implemented `_initAIInsights()` which increments the generation counter, shows loading state, fetches dismissed suggestions, and sends `getAIInsights` to the service worker. Added `chrome.runtime.onMessage` listener for `aiInsightsProgress` that checks generationId for stale-update protection, routes by section name (unavailable/claims/matches/suggestions/summary), filters dismissed IRIs from suggestions, updates loading text progressively, and computes total item count for the status badge.

Six rendering functions: `_renderUnavailable()` shows the LLM config message; `_renderClaimsSection(claims)` creates claim cards with confidence and type badges; `_renderMatchesSection(matches, gaps)` nests matched objects under claim headers with indicator badges, and renders research gaps as alert-style cards with amber left border; `_renderSuggestionsSection(suggestions)` renders cards with Accept/Dismiss buttons and data attributes for T03 wiring; `_renderSummarySection(summary)` renders text in a styled panel. All use the `_createAISubGroup()` helper for collapsible sub-groups.

In sidebar.css, added ~280 lines covering: `.ai-message` (unavailable state), `.ai-loading` + `.spinner-sm`, confidence badges (established=green, likely=blue, possible=amber, speculative=gray), indicator badges (contradicts=red, corroborates=green, contested=amber, related=gray), claim type badges, match items/meta/claim headers, research gap cards, suggestion cards with `.btn-accept` (teal) and `.btn-dismiss` (muted), summary panel, and `:empty` hiding for section containers.

`_initAIInsights()` is called from within the `chrome.tabs.query` callback in `init()` to ensure `_currentTabUrl` is available. The AI toggle button reuses the same expand/collapse pattern as context result groups.

## Verification

- `node --check extension/sidebar/sidebar.js` — passes (zero syntax errors)
- 12 occurrences of the 6 rendering functions + `_initAIInsights` found in sidebar.js
- `#ai-insights` container present in sidebar.html
- All 4 confidence badge CSS rules present
- All 4 indicator badge CSS rules present
- `.btn-accept` and `.btn-dismiss` CSS rules present with hover/disabled states
- All 5 AI section ID selectors present in CSS

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 2 | `grep -c render/init functions sidebar.js` | 0 (12) | ✅ pass | <1s |
| 3 | `grep 'ai-insights' sidebar.html` | 0 | ✅ pass | <1s |
| 4 | `grep badge-confidence-* sidebar.css` | 0 (4 rules) | ✅ pass | <1s |
| 5 | `grep badge-indicator-* sidebar.css` | 0 (4 rules) | ✅ pass | <1s |
| 6 | `grep btn-accept\|btn-dismiss sidebar.css` | 0 (6 rules) | ✅ pass | <1s |
| 7 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 8 | `node --check extension/shared/api-client.js` | 0 | ✅ pass | <1s |
| 9 | `grep -c SW handler types service-worker.js` | 0 (24) | ✅ pass | <1s |
| 10 | `grep -c sidebar render functions sidebar.js` | 0 (8) | ✅ pass | <1s |
| 11 | `grep ai-claims\|...\|ai-unavailable sidebar.css` | 0 (7) | ✅ pass | <1s |
| 12 | `node extension/tests/test-ai-client.js` | — | ⏭️ skip (T04) | — |

## Diagnostics

- **Progressive loading inspection:** Open sidebar, watch `#ai-loading-text` transition through: "Analyzing page…" → "Matching against your graph…" → "Finding relationships…" → "Generating summary…" → hidden.
- **Stale-update check:** Filter sidebar console for `AI Insights: stale` — appears when rapid page navigations trigger multiple `_initAIInsights` calls.
- **Unavailable state:** When service worker sends `section: 'unavailable'`, `#ai-unavailable` becomes visible with the LLM configuration message.
- **Suggestion data attributes:** Inspect `.ai-suggestion-card` elements for `data-suggestion-type`, `data-target-iri`, `data-target-label`, `data-suggestion-index` — these are wired by T03.
- **Status badge:** `#ai-status-badge` shows total AI item count after summary arrives; hidden if count is 0.

## Deviations

None — implemented exactly as planned. The `_createAISubGroup()` helper was added as a shared utility rather than inlining the collapsible pattern in each renderer, reducing code duplication.

## Known Issues

- Accept/Dismiss buttons are rendered but have no click handlers yet — T03 wires these.
- No timeout on `#ai-loading` — if the pipeline hangs, loading spinner remains indefinitely. T03 or a future task may add a timeout.

## Files Created/Modified

- `extension/sidebar/sidebar.html` — Added `#ai-insights` container with `#ai-toggle`, `#ai-body`, `#ai-unavailable`, `#ai-loading`, `#ai-claims`, `#ai-matches`, `#ai-suggestions`, `#ai-summary` inner elements. File grew from 70 to 95 lines.
- `extension/sidebar/sidebar.js` — Added 12 AI DOM refs, `_aiGenerationId`/`_aiDismissedIris` state, `_initAIInsights()`, `_renderUnavailable()`, `_createAISubGroup()`, `_renderClaimsSection()`, `_renderMatchesSection()`, `_renderSuggestionsSection()`, `_renderSummarySection()`, `aiInsightsProgress` message listener, AI toggle wiring. File grew from 556 to 1033 lines.
- `extension/sidebar/sidebar.css` — Added ~280 lines for AI section header, loading state, spinner-sm, unavailable message, confidence badges (4 colors), indicator badges (4 colors), claim type badge, match items/meta/claim headers, research gap cards, suggestion cards/buttons, summary panel, and section container empty-hide rules. File grew from 591 to 957 lines.
- `.gsd/milestones/M028/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix).
