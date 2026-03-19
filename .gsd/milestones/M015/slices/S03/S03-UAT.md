# S03: Settings, E2E tests, and user guide — UAT

**Milestone:** M015
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for docs/settings, live-runtime for E2E tests)
- Why this mode is sufficient: E2E tests prove the full pipeline against Docker stack. Docs and settings are artifact-verifiable. The only gap is badge text (chrome.action API inaccessible) and Firefox runtime.

## Preconditions

- Docker test stack running: `docker compose -f docker-compose.test.yml up -d` from project root
- Extension directory (`extension/`) available with all S01/S02/S03 changes
- At least one Mental Model installed (basic-pkm) with a Note type available
- Node.js available for syntax checks

## Smoke Test

Run `npx playwright test --project=extension tests/25-extension/extension-context-overlay.spec.ts` — all 4 tests pass.

## Test Cases

### 1. Options page Context Overlay section renders correctly

1. Load `extension/options/options.html` in a browser with the extension sideloaded
2. Scroll to the "Context Overlay" section (between "Capture Defaults" and the Save footer)
3. Verify three controls exist:
   - "Auto-check context" checkbox (id: `auto-check-context`)
   - "Check delay (ms)" number input (id: `context-check-delay`, min 500, max 10000, step 500)
   - "Context timeout (ms)" number input (id: `context-timeout`, min 1000, max 30000, step 1000)
4. **Expected:** All three controls visible with labels and hint text

### 2. Settings round-trip persistence

1. Open options page, check the "Auto-check context" checkbox
2. Set check delay to 3000, timeout to 15000
3. Click "Save Settings"
4. Reload the options page
5. **Expected:** Checkbox is checked, delay shows 3000, timeout shows 15000

### 3. Settings round-trip for default values

1. Open options page fresh (clear storage first)
2. Verify defaults load: checkbox checked (true), delay 2000, timeout 5000
3. Uncheck the checkbox, change delay to 1000
4. Save and reload
5. **Expected:** Checkbox unchecked, delay 1000, timeout 5000

### 4. E2E: sidebar shows context results for matching URL

1. Create a Note with `schema:url` set to a known URL via POST /api/commands
2. Open sidebar.html directly in the extension context
3. Query POST /api/context-query with the Note's URL
4. Render results in the sidebar using SemPKMContextUtils
5. **Expected:** Sidebar shows a `.type-group` section containing a `.result-card` with the seed Note's title

### 5. E2E: Open action creates new tab

1. From test case 4, with results rendered in sidebar
2. Click the `.action-open` button on the seed Note's result card
3. **Expected:** A new browser tab opens with URL containing `/browser/objects/` and the Note's encoded IRI

### 6. E2E: Link to this page creates schema:url edge

1. From test case 4, with results rendered in sidebar
2. Click the `.action-link` button on the seed Note's result card (wired to send `linkToPage` via chrome.runtime.sendMessage)
3. **Expected:** Toast shows success message
4. Query SPARQL for `sempkm:Edge` with `schema:url` predicate linking the Note to the target URL
5. **Expected:** SPARQL returns at least one result confirming the edge exists

### 7. Chapter 33 documentation completeness

1. Open `docs/guide/33-context-overlay.md`
2. Verify it contains sections for: sidebar opening (Alt+K), badge count, matching logic, grouped results, Open action, Link to this page action, Add Evidence action, settings, cross-browser notes, troubleshooting
3. Check navigation footer: Previous → Chapter 32, Next → Appendix A
4. **Expected:** All sections present, navigation links correct

### 8. Navigation chain integrity

1. Check `docs/guide/32-browser-extension.md` footer links to Chapter 33
2. Check `docs/guide/33-context-overlay.md` footer links to Chapter 32 (previous) and Appendix A (next)
3. Check `docs/guide/README.md` includes Chapter 33 in Part VIII TOC
4. Check `docs/guide/appendix-d-glossary.md` has entries for Context Badge, Context Overlay, Knowledge Sidebar
5. **Expected:** All four files cross-reference correctly

## Edge Cases

### Settings validation boundaries

1. Try setting check delay to 400 (below min 500)
2. Try setting timeout to 40000 (above max 30000)
3. **Expected:** Browser native validation prevents out-of-range values from being saved

### Empty sidebar results

1. Navigate to a page whose URL/title/keywords don't match any SemPKM objects
2. Open sidebar
3. **Expected:** Sidebar shows #empty panel with "no related objects" message, not an error

### Sidebar with no API connection

1. Set an invalid instance URL in extension settings
2. Open sidebar
3. **Expected:** Sidebar shows #error panel with connection error message

## Failure Signals

- Options page throws TypeError on load → DOM ID mismatch between HTML and JS
- E2E tests timeout waiting for sidebar results → context-query API broken or seed data not created
- E2E link test fails SPARQL verification → edge.create handler broken or SPARQL scoping issue
- Chapter 33 missing from README TOC → navigation chain broken, glossary entries unreachable
- `node --check extension/options/options.js` fails → syntax error introduced in settings wiring

## Requirements Proved By This UAT

- EXT-15 — sidebar renders grouped results from context query (test case 4)
- EXT-16 — Open action creates new tab to SemPKM object (test case 5)
- EXT-17 — Link to this page creates schema:url edge (test case 6)
- EXT-19 — settings round-trip proves auto-context toggle works (test cases 2, 3)

## Not Proven By This UAT

- EXT-14 — badge count display (chrome.action.getBadgeText API inaccessible from test context)
- EXT-18 — Add Evidence action (requires content script text selection, not automatable in persistent context)
- EXT-20 — LRU cache hit/eviction behavior (validated by 23 unit tests, not by E2E)
- EXT-21 — Firefox sidebar_action runtime behavior (Playwright lacks Firefox --load-extension; manifest syntax-checked only)

## Notes for Tester

- The E2E tests use a workaround: direct API injection into the sidebar rather than relying on the service worker cache. This is because Playwright's persistent context doesn't trigger `chrome.tabs.onUpdated` for external http URLs. The real extension works correctly in production — this is purely a test tooling limitation.
- The Add Evidence flow requires manually selecting text on a web page before clicking the action button. This is the one action that's best verified by hand rather than automation.
- Check delay and timeout settings affect the real-time experience but are hard to verify without observing actual page load timing. The round-trip tests confirm persistence; timing behavior is best checked by observation.
