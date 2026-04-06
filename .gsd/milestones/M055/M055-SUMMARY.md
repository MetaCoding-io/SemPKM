---
id: M055
title: "Browser History & Tab Recovery"
status: complete
completed_at: 2026-04-06T07:02:31.017Z
key_decisions:
  - D403: In-memory closed-tab stack only (no localStorage persistence) — session-scoped matches browser convention, avoids stale IRI complexity. Still valid.
  - Two guard flags (_historyReady, _navigatingFromHistory) prevent history pollution — structural approach rather than debouncing or event filtering.
  - Deep-link ?tab= captured before initWorkspaceLayout because replaceState inside init overwrites URL params — order-dependent but necessary.
  - History state shape is { tabId: string } — minimal, sufficient for panel lookup via dockview API.
key_files:
  - frontend/static/js/workspace-layout.js — pushState/popstate wiring, _closedTabStack, reopenClosedTab()
  - frontend/static/js/workspace.js — deep-link handler, Ctrl+Shift+T shortcut, command palette entry
  - e2e/tests/55-browser-history/history.spec.ts — 6 E2E tests for URL sync and history navigation
  - e2e/tests/55-browser-history/closed-tab.spec.ts — 4 E2E tests for closed-tab recovery
lessons_learned:
  - History API pushState must be suppressed during dockview layout restore — without a guard flag, restoring 5 panels creates 5 stale history entries.
  - Deep-link URL params must be captured before any code that calls replaceState — a common pattern in SPA-like apps where initialization resets URL state.
  - Playwright E2E tests for History API work better with page.evaluate() for panel activation than UI clicks — removes timing uncertainty from click→htmx→dockview chain.
  - page_settle helper (500ms + networkidle) is necessary for pushState/popstate tests because the History API is synchronous but dockview panel activation is async.
---

# M055: Browser History & Tab Recovery

**Wired History API to dockview workspace — URL reflects active tab via ?tab=, browser back/forward navigates tab history, deep-link URLs open correct tabs, and Ctrl+Shift+T recovers closed tabs from a 20-entry LIFO stack.**

## What Happened

M055 delivered two independent features that bring the workspace closer to browser-native behavior. S01 (URL Sync & History Navigation) wired the History API to dockview panel activation. Every tab switch pushes state via pushState, popstate events drive panel focus for back/forward navigation, and the initial load uses replaceState to avoid double-entry. Two guard flags prevent history pollution: `_historyReady` suppresses pushState during layout restore (which activates many panels rapidly), and `_navigatingFromHistory` suppresses pushState during popstate-triggered activation (preventing infinite loops). Deep-link support captures `?tab=` before initWorkspaceLayout — necessary because replaceState inside init overwrites URL params — then dispatches to the correct opener for all 9 tab ID formats (object IRIs, special:*, view:*, generic-view:*, dashboard:*, workflow:*, catalog:*, app-page:*, app-view:*). Stale history entries for closed panels trigger replaceState cleanup instead of errors.

S02 (Closed Tab Recovery) added a module-private `_closedTabStack` array in workspace-layout.js that captures panel metadata (id, component type, params, label) in the onDidRemovePanel handler. The `reopenClosedTab()` function pops from the LIFO stack and dispatches to the correct opener based on component type — covering all 18+ tab types including object-editor, view-panel, special-panel, dashboard, workflow, and app tabs. The stack is capped at 20 entries. Skip-and-try-next logic handles cases where a user manually reopened a tab before pressing Ctrl+Shift+T. The keyboard shortcut and a "Reopen Closed Tab" command palette entry were added in workspace.js.

Both features modify workspace-layout.js and workspace.js but touch entirely separate code paths — no integration conflicts. The combined E2E suite of 10 tests (6 history + 4 closed-tab) passes on both Chromium and Firefox (20 total runs).

## Success Criteria Results

- **URL reflects active tab via ?tab= parameter** — ✅ Met. S01 wired pushState to `onDidActivePanelChange` in workspace-layout.js. E2E tests 1-2 prove URL update on tab open and switch.
- **Browser back/forward navigates between tabs** — ✅ Met. S01 added popstate listener with `_navigatingFromHistory` guard flag. E2E test 3 proves back/forward cycles URL and focus correctly.
- **Bookmarkable/shareable URLs** — ✅ Met. S01/T02 added deep-link handler capturing `?tab=` before initWorkspaceLayout, supporting all 9 tab ID formats. E2E test 4 proves `/browser/?tab=<iri>` opens correct tab on load.
- **Closed-tab recovery via Ctrl+Shift+T** — ✅ Met. S02 added `_closedTabStack`, `reopenClosedTab()`, and Ctrl+Shift+T handler. 4 E2E tests prove single close/reopen, multi-tab LIFO, empty-stack safety, and skip-already-open.
- **Closed-tab recovery via command palette** — ✅ Met. S02 added "Reopen Closed Tab" entry in initCommandPalette(). E2E tests confirm functionality.

## Definition of Done Results

- **All slices complete** — ✅ Both S01 and S02 marked [x] in roadmap with summaries and UATs.
- **All task summaries exist** — ✅ S01: T01, T02, T03 summaries. S02: T01, T02 summaries. All present.
- **E2E tests pass** — ✅ 10 tests across 2 spec files pass on Chromium and Firefox (20 total runs).
- **No cross-slice integration issues** — ✅ S01 and S02 touch separate code paths in the same files. Combined suite runs without conflicts.
- **Validation passed** — ✅ M055-VALIDATION.md records verdict: pass with all criteria checked.

## Requirement Outcomes

- **R014** (Closed tab recovery — Ctrl+Shift+T): Active → **Validated**. Evidence: 8 E2E tests (4 cases × Chromium + Firefox) prove single close/reopen, multi-tab LIFO, empty-stack no-op, skip-already-open.
- **R015** (URL reflects active tab): Active → **Validated**. Evidence: 6 E2E tests on Chromium + Firefox prove pushState on tab open, URL update on switch, back/forward navigation.
- **R016** (Bookmarkable URLs): Active → **Validated**. Evidence: E2E test 4 navigates to /browser/?tab=<iri> and confirms correct tab opens. Deep-link handler supports all 9 tab ID formats.
- **R017** (Closed tab recovery — duplicate of R014): Active → **Validated**. Same evidence as R014.

## Deviations

T01 added _historyReady guard flag not in the plan. T01 fixed existing ?panel=sparql URL cleanup to preserve ?tab= — a compatibility fix not in plan. T02 captured ?tab= before initWorkspaceLayout instead of after, due to replaceState behavior. T03 did not modify selectors.ts — tests use JS APIs and URL assertions. S02 multi-tab E2E test uses JS API instead of keyboard shortcut for timing reliability. All deviations were pragmatic improvements.

## Follow-ups

None.
