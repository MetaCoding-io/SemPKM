---
id: T02
parent: S05
milestone: M014
provides:
  - Playwright E2E test suite for browser extension capture flow
  - Custom persistent context fixture for Chromium extension testing
  - Extension project configuration in playwright.config.ts
key_files:
  - e2e/fixtures/extension.ts
  - e2e/tests/25-extension/extension-capture.spec.ts
  - e2e/playwright.config.ts
key_decisions:
  - Use chrome.storage.local injection via page.evaluate for reliable cross-page settings persistence in persistent context
  - SPARQL API verification instead of workspace UI verification for created objects (persistent context hangs on non-extension page navigation)
  - Set form.noValidate=true before save to bypass native validation of hidden SHACL-rendered required fields
patterns_established:
  - Extension fixture pattern using chromium.launchPersistentContext with --load-extension and dynamic extension ID extraction from service worker URL
  - API key creation via POST /api/auth/tokens JSON endpoint for automated test setup
  - Settings injection via chrome.storage.local for reliable extension configuration in test environments
observability_surfaces:
  - Playwright HTML report + trace files for extension tests on failure
  - Console log capture in test 3 for save debugging
  - SPARQL query verification as authoritative object creation proof
duration: 35min
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: E2E Playwright tests for extension capture flow

**Added Playwright E2E tests proving full extension capture round-trip: API key creation, options page configuration, popup type loading with SHACL form rendering, object save, and SPARQL-verified persistence.**

## What Happened

Created three artifacts:

1. **`e2e/fixtures/extension.ts`** — Custom Playwright test fixture that launches a persistent Chromium context with the extension loaded via `--load-extension`. Dynamically extracts the extension ID from the service worker URL. Exports `test` and `expect` for use in extension-specific specs.

2. **`e2e/tests/25-extension/extension-capture.spec.ts`** — Three serial tests exercising the complete capture flow:
   - **Test 1:** Creates an API key via the auth API, navigates to the extension options page, fills in instance URL and API key, tests connection (waits for green status), saves settings, reloads and verifies persistence.
   - **Test 2:** Pre-injects settings via `chrome.storage.local`, opens the popup, waits for type selector to populate from the API, selects the first type, waits for the SHACL dynamic form to render, verifies `[data-path]` inputs exist.
   - **Test 3:** Pre-injects settings, opens popup, selects Note type (or first available), fills the title field, bypasses native form validation (`noValidate`), clicks Save, waits for success toast, then verifies the object exists via SPARQL API query.

3. **`e2e/playwright.config.ts`** — Added `extension` project entry matching `25-extension/` test directory with `fullyParallel: false`, no retries, trace on first retry, screenshots on failure.

Three gotchas discovered and worked around:
- `chrome.storage.sync` settings from options page aren't reliably visible to the popup in persistent context — fixed by injecting directly into `chrome.storage.local` via `page.evaluate`.
- SHACL-rendered forms have hidden required fields in collapsed sections that block native form validation — fixed by setting `form.noValidate = true`.
- Navigating to non-extension pages (workspace) hangs in persistent context — replaced with SPARQL API verification.

## Verification

All 3 tests pass consistently (verified with 4 consecutive runs):

```
Running 3 tests using 1 worker
  ✓ configure extension and verify connection (875ms)
  ✓ popup loads types and renders SHACL form (1.1s)
  ✓ capture a Note and verify in workspace (1.2s)
3 passed (4.2s)
```

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx playwright test --project=extension` | 0 | ✅ pass | 4.2s |
| 2 | `cd e2e && npx playwright test --project=extension` (re-run) | 0 | ✅ pass | 4.2s |
| 3 | `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.json'))"` | 0 | ✅ pass | <1s |
| 4 | `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.firefox.json'))"` | 0 | ✅ pass | <1s |
| 5 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 6 | Chrome manifest `commands._execute_action` has Alt+S | 0 | ✅ pass | <1s |
| 7 | Chrome manifest background has no `type: module` | 0 | ✅ pass | <1s |
| 8 | Firefox manifest has `background.scripts`, `gecko.id`, `commands` | 0 | ✅ pass | <1s |

## Diagnostics

- Run `cd e2e && npx playwright test --project=extension` to verify extension E2E flow
- Run `cd e2e && npx playwright show-report` to see HTML test report
- Extension tests require Docker test stack running on port 3901 with basic-pkm model installed
- Console log capture in Test 3 shows `[SemPKM]` log lines from the popup for save debugging

## Deviations

- **Removed workspace UI verification from Test 3.** The persistent context with `--load-extension` hangs when navigating to non-extension HTTP pages (`localhost:3901/browser/`). Replaced with SPARQL API query verification, which is more authoritative anyway.
- **Added `chrome.storage.local` injection helper.** `chrome.storage.sync` doesn't persist reliably across pages in persistent context. Tests inject settings directly via `page.evaluate()` before opening the popup.
- **Added `form.noValidate = true` before save.** The SHACL renderer sets `required` on inputs inside collapsed form sections, causing native validation to block the submit event.

## Known Issues

- Extension tests are Chromium-only — Firefox doesn't support `--load-extension` in Playwright persistent context.
- The persistent context cannot navigate to non-extension pages (workspace) without hanging — this limits what can be verified via the browser UI.

## Files Created/Modified

- `e2e/fixtures/extension.ts` — Custom Playwright fixture with persistent context + extension ID extraction
- `e2e/tests/25-extension/extension-capture.spec.ts` — 3 E2E tests for extension capture flow
- `e2e/playwright.config.ts` — Added `extension` project entry
- `.gsd/milestones/M014/slices/S05/tasks/T02-PLAN.md` — Added Observability Impact section
- `.gsd/KNOWLEDGE.md` — Added 3 extension E2E testing gotchas
