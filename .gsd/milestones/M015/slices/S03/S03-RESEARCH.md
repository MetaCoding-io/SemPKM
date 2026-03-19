# S03 — Research: Settings, E2E tests, and user guide

**Date:** 2026-03-18

## Summary

S03 is low-risk, pattern-following work across three domains: (1) add a "Context Overlay" settings section to the existing options page, (2) write Playwright E2E tests proving badge + sidebar + link action against the Docker test stack, and (3) write user guide Chapter 33 documenting the entire context overlay feature. Additionally, EXT-14 through EXT-21 requirements need to be registered in REQUIREMENTS.md.

All three domains use established patterns from M014. The settings UI extends the existing options page with three controls (toggle, delay, timeout) following the same form layout. The E2E test reuses the persistent context fixture from `e2e/fixtures/extension.ts` and the `setupAndCreateApiKey()` helper from `extension-capture.spec.ts`. The user guide follows Chapter 32's structure and voice.

## Recommendation

Three independent tasks, parallelizable in principle but should be ordered: (1) settings UI first (smallest, unblocks E2E), (2) E2E tests second (proves everything works), (3) user guide last (documents proven behavior). Requirements registration can happen in any task.

## Implementation Landscape

### Key Files

**Settings UI (modify):**
- `extension/options/options.html` — Add a "Context Overlay" `<section>` between "Capture Defaults" and the save footer. Three controls: checkbox for `autoCheckContext`, number input for `contextCheckDelay` (ms), number input for `contextTimeout` (ms).
- `extension/options/options.js` — Wire the three new form fields into `loadSettings()` and `saveCurrentSettings()`. Follow the exact pattern used for `autoFillTitle`/`autoFillUrl`/`includeSelection` — DOM reference, load from settings, save to settings. Add `$autoCheckContext`, `$contextCheckDelay`, `$contextTimeout` DOM references.
- `extension/shared/storage.js` — No changes needed. `autoCheckContext`, `contextCheckDelay`, `contextTimeout` are already in DEFAULTS and SETTINGS_KEYS.

**E2E Tests (new):**
- `e2e/tests/25-extension/extension-context-overlay.spec.ts` — New test file. Import `test, expect` from `../../fixtures/extension`. Reuse the `setupAndCreateApiKey()`, `readSetupToken()`, `repoRoot()`, and `injectExtensionSettings()` helpers — either extract to a shared module or duplicate (simpler, matching M014 precedent of self-contained test files).

**User Guide (new + modify):**
- `docs/guide/33-context-overlay.md` — New chapter. Sections: overview, opening the sidebar (Alt+K), badge count behavior, grouped results, Open action, Link to this page, Add Evidence, auto-context settings, cross-browser notes, troubleshooting.
- `docs/guide/32-browser-extension.md` — Update navigation footer: `Next: [Chapter 33: Context Overlay](33-context-overlay.md)`
- `docs/guide/33-context-overlay.md` — Navigation footer: `Previous: [Chapter 32: Browser Extension](32-browser-extension.md) | Next: [Appendix A: ...](appendix-a-environment-variables.md)`
- `docs/guide/appendix-a-environment-variables.md` — Update Previous link if needed.
- `docs/guide/README.md` — Add Chapter 33 to TOC.
- `docs/guide/appendix-d-glossary.md` — Add "Context Overlay", "Context Badge", "Knowledge Sidebar" entries.

**Requirements (modify):**
- `.gsd/REQUIREMENTS.md` — Register EXT-14 through EXT-21 as active, then validate them based on E2E test results.

### E2E Test Strategy

The existing `extension-capture.spec.ts` pattern is the template. Key considerations:

1. **Fixture reuse** — `e2e/fixtures/extension.ts` provides `context` (persistent context with extension loaded) and `extensionId`. No changes needed.

2. **Settings injection** — Use `injectExtensionSettings()` on an extension page to set instanceUrl + apiKey into `chrome.storage.local`. Also inject `autoCheckContext: true` to ensure the context pipeline runs.

3. **Seed data** — The test needs at least one object in the graph whose `schema:url` matches a known URL. Two approaches:
   - Create a Note via the API with a `schema:url` property before testing the sidebar
   - Use a SPARQL query to verify the object exists after creation
   Best approach: create a Note via `POST /api/commands` with `schema:url` set to a known test URL, then navigate to that URL and check the badge.

4. **Badge verification** — `chrome.action.getBadgeText()` is not accessible from Playwright. Instead, open the sidebar and verify it shows results (the badge is set from the same data).

5. **Sidebar verification** — Navigate to `chrome-extension://${extensionId}/sidebar/sidebar.html` directly (side panels can be opened as pages in Playwright persistent context). Send a `getContextResults` message or set up the sidebar to load results. Alternative: the sidebar loads results on init by sending `getContextResults` to the service worker — if the cache is populated, results will render.

6. **Challenge: service worker context query pipeline** — The service worker's `chrome.tabs.onUpdated` listener fires for real tab navigations. In Playwright persistent context, navigating a page should trigger this. However, the debounce delay (2000ms default) means the test must wait. The service worker also needs to successfully call the API — the extension must be configured before navigation.

7. **Realistic test flow:**
   - Setup: create API key, inject extension settings
   - Create a Note object via API with `schema:url` = `http://localhost:3901/test-context-page`
   - Navigate a tab to `http://localhost:3901/test-context-page` (or any URL that matches)
   - Wait for debounce (2s) + query time (~1s) = wait ~5s
   - Open sidebar page and verify results appear
   - Test "Open" action (verify new tab opens with SemPKM URL)
   - Test "Link to this page" action (verify edge creation via SPARQL)

8. **Known limitation from KNOWLEDGE.md** — Persistent context navigating to `http://localhost:3901/browser/` can hang. Avoid navigating to workspace pages; use API-only verification (SPARQL queries) for state assertions.

### Build Order

1. **T01: Settings UI** — Add "Context Overlay" section to options page. Smallest task, unblocks E2E testing of settings round-trip. Verify: load options page, change settings, save, reload, confirm values persist.

2. **T02: E2E tests** — Write `extension-context-overlay.spec.ts`. Depends on settings being wirable (T01). Verify: `npx playwright test --project=extension extension-context-overlay` passes against Docker test stack. Also register EXT-14 through EXT-21 in REQUIREMENTS.md.

3. **T03: User guide** — Write Chapter 33, update navigation chain, add glossary entries. Verify: all links resolve, chapter follows existing voice/structure.

### Verification Approach

- **T01:** `node --check extension/options/options.js` passes. Manual or E2E verification that settings save/load round-trip works.
- **T02:** `npx playwright test --project=extension e2e/tests/25-extension/extension-context-overlay.spec.ts` passes against running Docker test stack.
- **T03:** Chapter 33 file exists with correct navigation links. README TOC updated. Glossary entries present.

## Constraints

- **Chromium-only E2E** — Firefox doesn't support `--load-extension` in Playwright. Extension E2E tests are Chromium-only per M014 precedent.
- **Persistent context quirks** — `chrome.storage.sync` is unreliable in persistent context; use `injectExtensionSettings()` to write directly to `chrome.storage.local` (per KNOWLEDGE.md).
- **No workspace page navigation in persistent context** — navigating to `http://localhost:3901/browser/` can hang. Use API-only verification (SPARQL, `/api/commands`) instead.
- **Service worker debounce delay** — Default 2000ms debounce means E2E tests must wait at least 3s after navigation before checking sidebar results.
- **Options page is an ES module** (`<script type="module">`) — it imports from `../shared/api-client.js` and `../shared/storage.js`. New code must follow the same import pattern.

## Common Pitfalls

- **Badge not testable via Playwright** — `chrome.action.getBadgeText()` requires extension API access not available from Playwright page context. Test the sidebar results instead (same underlying data).
- **Service worker may be terminated** — MV3 service workers shut down after ~30s idle. If the test takes too long between navigation and sidebar check, the cache may be lost. Keep test steps tight.
- **SHACL form required fields** — If the E2E test creates objects via the popup, set `form.noValidate = true` before clicking Save (per KNOWLEDGE.md). But creating objects via API (`POST /api/commands`) avoids this entirely.
- **Sidebar page vs Side Panel** — In Playwright, open the sidebar HTML directly as a page (`chrome-extension://${extensionId}/sidebar/sidebar.html`) rather than trying to open the Side Panel API programmatically. The sidebar JS works the same way — it sends messages to the service worker regardless of how it's opened.

## Open Risks

- **Context query returning zero results in E2E** — If the seed Note's `schema:url` doesn't match the test URL, the sidebar shows empty state. Must ensure the Note is created with the exact URL the test navigates to, and that the context-query endpoint's URL matching works for localhost URLs.
- **Service worker not processing tab events in persistent context** — The `chrome.tabs.onUpdated` listener may behave differently in Playwright's persistent context. Mitigation: also test by sending `refreshContextResults` message directly from the sidebar, bypassing the tab listener.
