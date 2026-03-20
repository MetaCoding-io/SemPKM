# S03: Demo tour + dashboard + CTA banner — UAT

**Milestone:** M025
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven for static checks + live-runtime for tour flow)
- Why this mode is sufficient: Static checks verify code structure and wiring. Live-runtime tests (run against demo Docker stack) verify the actual user experience. The tour, dashboard, and CTA banner are interactive UI features that require a running stack with seed data to fully validate.

## Preconditions

1. Demo Docker stack running: `docker compose -f docker-compose.demo.yml up -d` from project root
2. Seed script executed: `docker compose -f docker-compose.demo.yml exec api python /app/scripts/seed-demo-data.py`
3. Demo instance accessible at `http://localhost:3902/browser/`
4. Browser with JavaScript enabled, localStorage available
5. No prior `sempkm_demo_tour_done` or `sempkm_demo_cta_dismissed` in localStorage (use incognito/private window for clean state)

## Smoke Test

Open `http://localhost:3902/browser/` in a fresh incognito window. Within 2 seconds of the workspace loading, a Driver.js tour popover should appear highlighting the Explorer pane. If the tour auto-starts, the slice basically works.

## Test Cases

### 1. Tour auto-starts on first visit

1. Open a fresh incognito window
2. Navigate to `http://localhost:3902/browser/`
3. Wait for the workspace to fully load (sidebar visible, dockview initialized)
4. **Expected:** After ~1.5 seconds, a Driver.js popover appears highlighting the `#section-objects` element with title "Explorer" and description mentioning browsing objects

### 2. Tour navigates through all 7 steps

1. Start from Test 1 (tour auto-started)
2. Click "Next" on step 1 (Explorer)
3. **Expected:** Graph view opens in editor area, step 2 popover highlights `.group-editor-area` with "Graph View" title
4. Click "Next" on step 2
5. **Expected:** A seed Note object tab opens, step 3 popover highlights the object view with "Object View" title
6. Click "Next" on step 3
7. **Expected:** Bottom panel opens (validation/lint), step 4 popover highlights `#bottom-panel` with "Validation & Linting" title
8. Click "Next" on step 4
9. **Expected:** Canvas tab opens, step 5 popover highlights `.group-editor-area` with "Spatial Canvas" title
10. Click "Next" on step 5
11. **Expected:** Demo Dashboard tab opens, step 6 popover mentions cross-view context filtering
12. Click "Next" on step 6
13. **Expected:** Step 7 centered popover with "Ready to Try SemPKM?" title and Done button with GitHub link
14. Click "Done"
15. **Expected:** Tour dismisses, no JS console errors throughout

### 3. localStorage flag set after tour completion

1. Complete the tour (Test 2)
2. Open browser DevTools → Application → Local Storage
3. **Expected:** `sempkm_demo_tour_done` key exists with value `'1'`

### 4. CTA banner appears after tour completion

1. Complete the tour (Test 2)
2. Look at the bottom of the workspace
3. **Expected:** A blue/accent-colored banner slides up with rocket icon, "Try SemPKM" heading, install description, "Get Started" button (links to GitHub), and X dismiss button

### 5. CTA banner dismiss persists

1. With CTA banner visible (Test 4), click the X dismiss button
2. **Expected:** Banner slides down and disappears
3. Open DevTools → Local Storage
4. **Expected:** `sempkm_demo_cta_dismissed` key exists with value `'1'`
5. Refresh the page
6. **Expected:** CTA banner does NOT reappear

### 6. Tour does NOT re-start on page refresh

1. Complete the tour (Test 2) so `sempkm_demo_tour_done` is set
2. Refresh the page
3. **Expected:** Workspace loads normally without the tour auto-starting
4. **Expected:** CTA banner is visible (unless dismissed)

### 7. Manual tour restart via button

1. After tour has completed (localStorage flag set)
2. Look for a floating play-circle button in the bottom-right corner of the workspace
3. Click the restart button
4. **Expected:** Tour starts again from step 1

### 8. Manual tour restart via console

1. Open browser DevTools → Console
2. Type `window.startDemoTour()` and press Enter
3. **Expected:** Tour starts from step 1, console shows `[SemPKM] Demo tour started`

### 9. Demo Dashboard exists in explorer

1. In the workspace sidebar, expand the DASHBOARDS section
2. **Expected:** "Demo Dashboard" appears in the list
3. Click "Demo Dashboard"
4. **Expected:** Dashboard tab opens showing blocks with data (table view-embed and graph view-embed in sidebar-main layout)

### 10. CTA banner shows on return visit (tour previously completed)

1. Complete the tour in one session
2. Close the browser tab (don't dismiss the CTA)
3. Open a new tab, navigate to `http://localhost:3902/browser/`
4. **Expected:** CTA banner is visible (tour flag is set, CTA dismissed flag is not)

### 11. No CTA banner on non-demo instance

1. Start a regular (non-demo) Docker stack (`docker compose up -d`)
2. Log in and navigate to the workspace
3. **Expected:** No CTA banner visible, no restart button visible, `window.startDemoTour()` may exist but auto-start does not fire

## Edge Cases

### Tour with missing navigation globals

1. If any workspace navigation function (e.g., `openGenericViewTab`) is undefined
2. **Expected:** Tour continues in degraded mode — popover shows without highlighted element, no JS crash. `typeof` guards prevent errors.

### Tour dismissal before completion

1. Start the tour, then press Escape or click the X on any step before completing all 7
2. **Expected:** Tour dismisses. `sempkm_demo_tour_done` is still set (onDestroyStarted fires regardless of step). CTA banner appears.

### Dashboard opened before seed script runs

1. If the seed script's Phase 4 hasn't run (no dashboard with UUID `aaaaaaaa-bbbb-...`)
2. Tour step 6 calls `openDashboardTab`
3. **Expected:** A dashboard tab opens but may show empty/error content. Tour continues to step 7 without crashing.

### Rapid clicking through tour steps

1. Click "Next" rapidly without waiting for navigation to complete
2. **Expected:** Some steps may show popovers without proper element highlighting (DOM not yet loaded). Tour should not crash or enter an invalid state.

## Failure Signals

- **Tour doesn't auto-start:** Check `demo_mode` template context (view source for `{% if demo_mode %}`), check localStorage for pre-existing `sempkm_demo_tour_done` flag, check browser console for `[SemPKM] Driver.js not loaded` warning
- **Tour step shows wrong element or no highlight:** Navigation function may have failed silently — check console for errors, check 500ms timeout sufficiency
- **CTA banner never appears:** Check that `sempkm:demo-tour-done` event is dispatched (add `document.addEventListener('sempkm:demo-tour-done', () => console.log('EVENT'))` before tour), check `sempkm_demo_cta_dismissed` not set
- **Dashboard empty or missing:** Verify seed script Phase 4 ran (`docker compose exec api python /app/scripts/seed-demo-data.py --verify-only` should show Dashboards ≥ 1), check UUID match between seed script and dashboard_specs table
- **JS console errors during tour:** Any uncaught exceptions during navigation or step transitions indicate a wiring problem

## Requirements Proved By This UAT

- DEMO-04 (pending registration) — Demo tour completes 7 steps without errors on fresh anonymous session
- DEMO-05 (pending registration) — Pre-built demo dashboard renders with data and cross-view context filtering
- DEMO-06 (pending registration) — CTA banner visible after tour completion with install link
- DEMO-03 (partial) — Browser-level visibility of sample data via dashboard

## Not Proven By This UAT

- Tour pacing and perceived quality (subjective — needs human gut check on timing, animations, text clarity)
- Cross-view context filtering actually filtering (clicking a table row → graph updates) — needs interactive runtime test
- Tour completion time under 3 minutes — needs a timed run
- SSL/deployment configuration — covered by S04
- E2E Playwright automation — covered by S04

## Notes for Tester

- Use incognito/private windows for clean localStorage state. The tour and CTA both rely on localStorage flags — stale flags from previous tests will prevent auto-start or re-showing the banner.
- To reset all demo state: `localStorage.removeItem('sempkm_demo_tour_done'); localStorage.removeItem('sempkm_demo_cta_dismissed')` then refresh.
- The 500ms navigation delays are tuned for local Docker. On remote or slow instances, steps may need more time to load destination views.
- The CTA "Get Started" button links to the GitHub repo — verify the URL is correct and accessible.
- Pay attention to visual quality: does the tour feel smooth? Are popovers positioned well? Does the CTA banner animation feel polished?
