# S01: URL Sync & History Navigation

**Goal:** Wire the History API to dockview panel activation so the URL reflects the active tab, back/forward navigates tab history, and deep links from ?tab= work on page load.
**Demo:** After this: Open object A → URL shows ?tab=A → open B → URL shows ?tab=B → back → A focused → URL shows A. Paste bookmarked URL → correct object opens.

## Tasks
- [x] **T01: Wire History API pushState/popstate to dockview panel activation — URL reflects active tab, back/forward switches tabs, stale entries cleaned up** — Wire URL updates to dockview panel activation and back/forward navigation.

1. In workspace-layout.js, extend the onDidActivePanelChange handler to call history.pushState with ?tab=<panelId> (skip ephemeral __new-object- tabs)
2. Add a _navigatingFromHistory guard flag that suppresses pushState when a panel activation is triggered by popstate
3. Add a window popstate listener that reads state.tabId and activates the corresponding panel via panel.api.setActive() (with guard flag set)
4. If the panel referenced by popstate no longer exists (was closed), update URL with replaceState to remove stale ?tab=
5. Use replaceState (not pushState) for the initial page load state to avoid double-entry in history
6. Ensure existing ?panel=sparql handling in initBottomPanel is unaffected
  - Estimate: 30min
  - Files: frontend/static/js/workspace-layout.js, frontend/static/js/workspace.js
  - Verify: Start dev stack. Open /browser/. Open object A → check URL has ?tab= with A's IRI. Open object B → URL updates. Press back → A is focused, URL shows A. Press forward → B focused. Open 5 tabs, navigate back through all of them — no loop, no duplicate entries. Verify ?panel=sparql still works.
- [x] **T02: Added deep-link handler that opens and focuses the correct tab type from ?tab= query parameter on initial page load** — Handle the ?tab= query parameter on initial page load to open the referenced tab.

1. In workspace.js, after initWorkspaceLayout() completes (where dockview layout is restored), read ?tab= from the URL
2. If ?tab= is present:
   a. Check if the panel is already open (may have been restored from layout). If so, just focus it with setActive()
   b. If not open, determine the tab type from the ID format (raw IRI = object tab, 'view:*' = view tab, 'special:*' = special tab, etc.) and call the appropriate open*Tab() function
   c. For object tabs, call openTab(iri) — label will be fetched by the htmx partial
3. Do NOT clean the ?tab= from URL after processing — keeping it makes the URL persistently bookmarkable
4. Ensure this works with replaceState initial state from T01 (no duplicate history entry)
  - Estimate: 20min
  - Files: frontend/static/js/workspace.js
  - Verify: Navigate to /browser/?tab=<known-object-iri>. Object tab opens and is focused. URL still shows ?tab=. Refresh the page — same object tab opens. Navigate to /browser/?tab=view:<viewId> — view tab opens.
- [x] **T03: Added 6 Playwright E2E tests covering URL sync, back/forward navigation, deep-linking, stale entry cleanup, and ephemeral tab exclusion — all pass on Chromium and Firefox** — Write Playwright E2E tests proving the URL sync and history navigation work.

1. Create e2e/tests/55-browser-history/history.spec.ts
2. Test cases:
   a. Open an object → URL contains ?tab= with the object IRI
   b. Open object A, open object B → URL shows B → page.goBack() → URL shows A, tab A is active → page.goForward() → URL shows B, tab B is active
   c. Navigate to /browser/?tab=<iri> → object tab opens with correct content
   d. Open two objects, close one, press back → URL updates correctly (no error from missing panel)
3. Use existing E2E helpers (openTab from dockview.ts, SEL selectors)
4. Add history-related selectors to selectors.ts if needed
  - Estimate: 25min
  - Files: e2e/tests/55-browser-history/history.spec.ts, e2e/helpers/selectors.ts
  - Verify: cd e2e && npx playwright test tests/55-browser-history/history.spec.ts --headed
