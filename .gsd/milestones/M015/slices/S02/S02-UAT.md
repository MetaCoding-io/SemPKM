# S02: In-context actions — Link to page and Add Evidence — UAT

**Milestone:** M015
**Written:** 2026-03-18

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: Both actions require a running SemPKM instance with installed Mental Models (Research Workflow for Claims) and the extension sideloaded in Chrome. Artifact inspection alone cannot verify the API round-trip.

## Preconditions

1. Docker test stack running (`docker compose -f docker-compose.test.yml up -d`)
2. Research Workflow Mental Model installed (provides Claim type for Evidence action)
3. Extension sideloaded in Chrome with valid instance URL and API key configured in options
4. At least one object visible in sidebar context results (navigate to a page with URL or keyword matches)
5. At least one Claim object exists in the graph (for Evidence action testing)

## Smoke Test

Open sidebar via Alt+K on any page that produces context results. Verify "Link to page" button appears on all results (solid border, not dashed). Verify "Add Evidence" button appears only on Claim-type results (amber border). Click "Link to page" on any result — should see "✓ Linked to this page" toast within 2 seconds.

## Test Cases

### 1. Link to page — happy path

1. Navigate to a page (e.g. `https://example.com/article`)
2. Open sidebar via Alt+K
3. Wait for context results to load
4. Click "Link to page" on any result
5. **Expected:** Button shows "Linking…" and is disabled during the API call
6. **Expected:** Green toast "✓ Linked to this page" appears
7. **Expected:** Button re-enables after completion
8. Open the linked object in SemPKM workspace (click "Open" button)
9. Check Relations panel
10. **Expected:** A `schema:url` edge exists pointing to the page URL

### 2. Link to page — API error handling

1. Open extension options and set an invalid API key
2. Navigate to a page and open sidebar
3. Click "Link to page" on any result
4. **Expected:** Red error toast appears with API error detail (e.g. "401 Unauthorized" or similar)
5. **Expected:** Button re-enables after the error

### 3. Link to page — unconfigured extension

1. Open extension options and clear the instance URL
2. Open sidebar via Alt+K
3. Click "Link to page" on any result
4. **Expected:** Toast shows "SemPKM not configured" or similar guidance message

### 4. Add Evidence — button visibility

1. Navigate to a page that matches both a Claim and a non-Claim object (e.g. a Note)
2. Open sidebar via Alt+K
3. **Expected:** "Add Evidence" button (amber border) appears only on Claim-type results
4. **Expected:** Non-Claim results show "Link to page" button but no "Add Evidence" button

### 5. Add Evidence — happy path

1. Navigate to a page with text content
2. Open sidebar via Alt+K
3. Click "Add Evidence" on a Claim result
4. **Expected:** Evidence capture prompt panel appears with instructions ("Select text on the page, then click Capture")
5. Switch to the page tab and select some text
6. Switch back to sidebar and click "Capture"
7. **Expected:** Selected text preview appears in the prompt panel
8. **Expected:** Button shows "Capturing…" and is disabled during API call
9. **Expected:** Green toast "✓ Evidence captured and linked" appears
10. Open SemPKM workspace and search for the new Evidence object
11. **Expected:** Evidence object exists with the selected text as body content and the page URL as source
12. **Expected:** Evidence object has a `res:supports` edge pointing to the original Claim

### 6. Add Evidence — cancel flow

1. Open sidebar and click "Add Evidence" on a Claim
2. **Expected:** Evidence capture prompt panel appears
3. Click "Cancel"
4. **Expected:** Prompt panel hides, sidebar returns to results view
5. **Expected:** No API calls made, no objects created

### 7. Add Evidence — empty selection

1. Open sidebar and click "Add Evidence" on a Claim
2. Do NOT select any text on the page
3. Click "Capture"
4. **Expected:** Error toast or validation message indicating no text was selected
5. **Expected:** No API calls made

## Edge Cases

### Tab URL tracking across navigation

1. Open sidebar via Alt+K on page A
2. Navigate to page B in the same tab (without closing sidebar)
3. Click "Link to page" on a result
4. **Expected:** The edge's target URL is page B (not page A) — sidebar tracks current tab URL

### Partial failure in Evidence creation

1. Simulate a scenario where object.create succeeds but edge.create fails (e.g. by temporarily breaking the edge endpoint)
2. **Expected:** Error toast includes the Evidence IRI for manual linking
3. **Expected:** The Evidence object exists in the graph (orphaned but recoverable)
4. **Expected:** Service worker console shows step-by-step logs: "creating evidence object", "evidence created <IRI>", "linking evidence to claim", then error

### Double-click prevention

1. Click "Link to page" and immediately click it again before the first call completes
2. **Expected:** Button is disabled after first click, second click is a no-op
3. **Expected:** Only one edge.create API call is made

## Failure Signals

- Toast shows error instead of success — check service worker console for `[SemPKM]` prefixed logs
- Button stays in "Linking…" / "Capturing…" state indefinitely — API call may have hung, check network tab
- "Add Evidence" button appears on non-Claim results — type_iri conditional check is wrong
- Evidence capture returns empty text despite selecting on page — `chrome.scripting.executeScript` may lack permission on that page
- Edge appears in graph but with wrong predicate — check service worker hardcoded predicate strings

## Requirements Proved By This UAT

- EXT-17 — Link action creates schema:url edge with correct source/target, visible in Relations panel
- EXT-18 — Evidence capture flow: prompt → text selection → Evidence object created → linked to Claim via res:supports

## Not Proven By This UAT

- EXT-14 (badge count) — tested in S01, not retested here
- EXT-15 (sidebar grouped results) — tested in S01, not retested here
- EXT-16 (open action) — tested in S01, not retested here
- EXT-19 (auto-context settings) — deferred to S03
- EXT-20 (URL caching) — tested in S01, not retested here
- EXT-21 (cross-browser) — Firefox sidebar testing deferred to S03
- Automated E2E Playwright tests — deferred to S03

## Notes for Tester

- The Evidence action only appears on Claim-type results. You need the Research Workflow model installed with at least one Claim object. Create one manually if needed: type = `urn:sempkm:model:research:Claim`, add a label like "Test Claim".
- The `chrome.scripting.executeScript` call may fail on protected pages (chrome://, extension pages, web store). Test on regular HTTP pages.
- Service worker console is the most authoritative diagnostic — open `chrome://extensions`, find SemPKM, click "service worker" under "Inspect views".
- The evidence prompt panel replaces the results view (hidden toggle, not overlay). This is intentional — the sidebar is narrow and overlaying would be unusable.
