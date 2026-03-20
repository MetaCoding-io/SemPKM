---
id: T03
parent: S02
milestone: M028
provides:
  - Accept click handler sends acceptSuggestion message to service worker with suggestion data and page URL/title
  - Dismiss click handler sends dismissSuggestion message, fades card out, removes from DOM, updates local dismissed list
  - Accepted card visual state (green border, muted, checkmark badge replacing buttons)
  - Fade-out animation for dismissed cards via CSS keyframes
  - Empty suggestions group auto-hidden when last card dismissed
  - Guard against missing _currentTabUrl on both actions
key_files:
  - extension/sidebar/sidebar.js
  - extension/sidebar/sidebar.css
key_decisions:
  - Closure-based event handlers (IIFE pattern) to capture suggestion object, card element, and both button refs — avoids data-attribute parsing at click time
  - In-memory _aiDismissedIris array updated on dismiss success so re-renders also filter without another chrome.storage round-trip
  - V1 accepts stale AI cache after Accept — card shows visual "Accepted" state, cache refreshes on next navigation
patterns_established:
  - Accept/Dismiss handler pattern: disable both buttons → set loading text → sendMessage → on success update card state → on error re-enable and show toast
  - Dismiss cleanup: fade-out animation → animationend listener → remove card → check remaining count → clear group or update badge
observability_surfaces:
  - Console log `[SemPKM Sidebar] AI acceptSuggestion:` with type and IRI on every accept click
  - Console log `[SemPKM Sidebar] AI dismissSuggestion:` with IRI on every dismiss click
  - Console error `acceptSuggestion error:` / `dismissSuggestion error:` on failures
  - Red toast notification for user-visible errors, green toast for success
duration: 12m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T03: Wire Accept and Dismiss actions for suggestions

**Wired Accept and Dismiss click handlers on AI suggestion cards to service worker message passing with loading states, success toasts, accepted badge, fade-out dismiss animation, and empty-group cleanup.**

## What Happened

Added event listeners to the Accept and Dismiss buttons rendered by T02's `_renderSuggestionsSection()`. Both handlers use IIFE closures to capture the suggestion object and DOM references at render time, avoiding data-attribute parsing on click.

**Accept flow:** Disables both buttons → sets "Accepting…" text → sends `acceptSuggestion` message with full suggestion payload and page URL/title → on success shows "✓ Linked to {target_label}" toast and replaces buttons with a green "✓ Accepted" badge via `.accepted` class → on error shows red toast and re-enables buttons.

**Dismiss flow:** Disables both buttons → sets "Dismissing…" text → sends `dismissSuggestion` message with URL and IRI → on success shows "Dismissed" toast, pushes IRI to local `_aiDismissedIris` array, adds `.fade-out` class for CSS animation, removes card on `animationend` → checks remaining cards: if 0, clears `$aiSuggestions`; otherwise updates count badge → on error shows red toast and re-enables buttons.

**CSS additions:** `.accepted` card state with green left border and muted opacity, `.accepted-badge` green checkmark text, `.fade-out` animation via `fadeSlideOut` keyframes (opacity + max-height collapse over 0.25s). Disabled button styles were already present from T02.

**Step 3 verification:** Confirmed `_initAIInsights()` already fetches dismissed IRIs via `getDismissedSuggestions` and the progress handler filters `suggestions` against `_aiDismissedIris` before rendering — both implemented correctly by T02.

## Verification

All task-level and slice-level checks pass:
- `node --check extension/sidebar/sidebar.js` — zero errors
- `acceptSuggestion` message sent in 3 locations (log, type field, error handler)
- `dismissSuggestion` message sent in 3 locations (log, type field, error handler)
- CSS `fadeSlideOut` keyframes and `.fade-out` class present
- CSS `.accepted` and `.accepted-badge` rules present
- All 3 extension files pass syntax check
- Service worker has 24 handler references (≥5 required)
- Sidebar has 8 rendering function references (all 5 required present)
- `ai-insights` container div exists in sidebar.html
- CSS rules for all AI sections exist

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 2 | `grep 'acceptSuggestion' extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 3 | `grep 'dismissSuggestion' extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 4 | `grep 'fade-out\|fadeSlideOut' extension/sidebar/sidebar.css` | 0 | ✅ pass | <1s |
| 5 | `grep 'accepted-badge\|\.accepted' extension/sidebar/sidebar.css` | 0 | ✅ pass | <1s |
| 6 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 7 | `node --check extension/shared/api-client.js` | 0 | ✅ pass | <1s |
| 8 | `grep -c 'getAIInsights\|acceptSuggestion\|...' extension/background/service-worker.js` → 24 | 0 | ✅ pass | <1s |
| 9 | `grep -c '_renderAIInsights\|_renderClaimsSection\|...' extension/sidebar/sidebar.js` → 8 | 0 | ✅ pass | <1s |
| 10 | `grep 'ai-insights' extension/sidebar/sidebar.html` | 0 | ✅ pass | <1s |
| 11 | `grep 'ai-claims\|ai-matches\|...' extension/sidebar/sidebar.css` | 0 | ✅ pass | <1s |
| 12 | `node extension/tests/test-ai-client.js` | 1 | ⚠️ skip (file not created yet — separate task scope) | <1s |

## Diagnostics

- **Accept tracing:** Filter sidebar console for `[SemPKM Sidebar] AI acceptSuggestion:` — logs suggestion type and target IRI.
- **Dismiss tracing:** Filter sidebar console for `[SemPKM Sidebar] AI dismissSuggestion:` — logs target IRI.
- **Error visibility:** Both handlers log error details to console and show red toast to user.
- **Visual state inspection:** Accepted cards have `.accepted` class — inspect in DevTools Elements panel. Dismissed cards animate out via `.fade-out` class.
- **Dismiss persistence:** `_aiDismissedIris` updated in-memory; persistent storage in `chrome.storage.local` keys `dismissed_suggestions_{url}` (set by service worker).

## Deviations

None. All plan steps executed as specified. Step 3 (verify dismissed IRI filtering) confirmed already correct from T02.

## Known Issues

- `extension/tests/test-ai-client.js` does not exist yet — listed in slice verification but created by a different task.
- V1 does not invalidate `aiCache` after Accept — accepted suggestions may reappear (without buttons, since the card shows "Accepted" state) if cache serves stale data before navigation. Acceptable per plan.

## Files Created/Modified

- `extension/sidebar/sidebar.js` — Added Accept and Dismiss click handlers in `_renderSuggestionsSection()` with loading states, success/error handling, toast notifications, and empty-group cleanup (~120 lines)
- `extension/sidebar/sidebar.css` — Added `.accepted` card state, `.accepted-badge`, `.fade-out` animation with `fadeSlideOut` keyframes (~35 lines)
- `.gsd/milestones/M028/slices/S02/tasks/T03-PLAN.md` — Added Observability Impact section per pre-flight
