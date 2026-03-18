---
estimated_steps: 7
estimated_files: 3
---

# T02: E2E Playwright tests for extension capture flow

**Slice:** S05 — Cross-browser, keyboard shortcut, E2E tests + user guide
**Milestone:** M014

## Description

Write Playwright E2E tests that prove the browser extension's full capture flow against the Docker test stack. Extension testing in Playwright requires `chromium.launchPersistentContext()` with `--load-extension` args — this is fundamentally different from the normal test projects and needs its own fixture and config project.

The test flow: create an API key via admin login → configure the extension options page → open the popup → verify type selector populates → select a type → verify SHACL form renders → fill title → save → verify object appears in workspace.

**Key constraints:**
- Playwright extension testing is Chromium-only — Firefox doesn't support `--load-extension`
- Persistent context doesn't share cookies/state with the normal test projects — auth must be done within the test
- Extension ID changes on every launch — extract dynamically from service worker URL
- The popup is accessible as a regular page at `chrome-extension://{id}/popup/popup.html`
- The options page is at `chrome-extension://{id}/options/options.html`
- `chrome.storage.session` may behave differently in persistent context — existing try/catch in popup handles this
- Docker test stack runs on port 3901

**Load the `test` skill** (`~/.gsd/agent/skills/test/SKILL.md`) before writing tests.

## Steps

1. **Create extension fixture** at `e2e/fixtures/extension.ts`. Export a custom `test` base that extends Playwright's `test` with two fixtures:
   - `context`: launches `chromium.launchPersistentContext('')` with args `--disable-extensions-except={pathToExtension}` and `--load-extension={pathToExtension}` where `pathToExtension` is resolved to the repo's `extension/` directory. Use `headless: false` since Chrome extensions don't work in headless mode (use `--headless=new` via arg if `CI` env is set).
   - `extensionId`: waits for the service worker via `context.waitForEvent('serviceworker')`, extracts the extension ID from `sw.url().split('/')[2]`.

   The fixture should also export the `expect` from Playwright.

2. **Create API key helper.** Within the test file (not a separate module), write a helper function that:
   - Creates a new API request context for `http://localhost:3901`
   - Reads the setup token from Docker: `docker compose -f docker-compose.test.yml exec -T api cat /app/data/.setup-token` (using `execSync` from the repo root)
   - Claims the instance if needed (POST `/auth/setup` with setup token)
   - Logs in as owner via magic link: POST `/auth/magic-link` → extract token from logs → POST `/auth/verify`
   - Creates an API key: POST `/admin/api-keys` with the session cookie → returns the plaintext token from the response
   - Returns `{ apiKey, ownerCookies }` for use in tests

   This mirrors the existing `e2e/fixtures/auth.ts` pattern but adapted for the persistent context flow.

3. **Write the extension capture spec** at `e2e/tests/25-extension/extension-capture.spec.ts`. Use the custom `test` from the fixture. Tests:

   **Test 1: "configure extension and verify connection"**
   - Call the API key helper to get a valid API key
   - Navigate to `chrome-extension://${extensionId}/options/options.html`
   - Fill in Instance URL (`http://localhost:3901`) and API Key
   - Click "Test Connection" → wait for green status indicator
   - Click Save
   - Verify settings persisted by reloading and checking fields still populated

   **Test 2: "popup loads types and renders SHACL form"**
   - Navigate to `chrome-extension://${extensionId}/popup/popup.html`
   - Wait for type selector to have options (not just the default "Select a type...")
   - Verify at least one type appears (the Docker stack has basic-pkm installed)
   - Select a type (e.g., the first real option)
   - Wait for `#dynamic-form` to have children (SHACL form rendered)
   - Verify at least one `[data-path]` input exists in the form

   **Test 3: "capture a Note and verify in workspace"**
   - Navigate to popup
   - Select "Note" type from the dropdown (find option containing "Note")
   - Wait for form to render
   - Fill in dcterms:title field (find input with `data-path` containing "title")
   - Click Save button
   - Wait for success toast (`.toast.success` or similar)
   - Open a new page in the context, navigate to `http://localhost:3901/browser/`
   - Login as owner (use magic link flow in the browser page)
   - Search or look for the created object by title
   - Verify it appears in the workspace

   Use `test.describe.serial()` so tests run in order (Test 1 configures, Test 2/3 depend on config).

4. **Add extension project to playwright.config.ts.** Add a new project entry:
   ```typescript
   {
     name: 'extension',
     testMatch: /25-extension\/.*\.spec\.ts/,
     use: {
       /* Extension tests use custom persistent context — no default browser */
       trace: 'on-first-retry',
       screenshot: 'only-on-failure',
       video: 'off',
     },
     fullyParallel: false,
     retries: 0,
   }
   ```
   Place it after the `federation` project entry.

5. **Create the test directory.** Ensure `e2e/tests/25-extension/` exists.

6. **Run the tests.** Start the Docker test stack if not running (`docker compose -f docker-compose.test.yml up -d` from repo root). Then `cd e2e && npx playwright test --project=extension`. Debug any failures — common issues:
   - Service worker may not register immediately — add waiting logic in fixture
   - `chrome.storage.sync` may not work in persistent context — extension's `storage.js` has fallback to `chrome.storage.local`
   - Options page save may need a small delay before popup tests
   - Type selector population is async via API call — wait for options count > 1

7. **Verify tests pass cleanly.** All tests green. If a test is flaky, add appropriate waits or retry logic within the test.

## Must-Haves

- [ ] `e2e/fixtures/extension.ts` exports custom `test` with persistent context + extension ID fixtures
- [ ] `e2e/tests/25-extension/extension-capture.spec.ts` has 3 tests proving config → capture → workspace round-trip
- [ ] `e2e/playwright.config.ts` has `extension` project entry matching `25-extension/` test directory
- [ ] Tests pass against Docker test stack: `cd e2e && npx playwright test --project=extension`
- [ ] Extension ID extracted dynamically (not hardcoded)

## Verification

- `cd e2e && npx playwright test --project=extension` — all tests pass
- Tests prove: options page saves settings with connection test, popup loads types from API, SHACL form renders for a type, object creation succeeds, created object visible in workspace

## Inputs

- `extension/` directory — complete extension from S01-S04 (including T01 manifest cleanup)
- `e2e/fixtures/auth.ts` — existing auth pattern to reference for API key creation
- `e2e/playwright.config.ts` — existing config to extend with new project
- Docker test stack on port 3901 with basic-pkm model installed

## Expected Output

- `e2e/fixtures/extension.ts` — Custom Playwright test fixture with persistent context + extension loading
- `e2e/tests/25-extension/extension-capture.spec.ts` — 3 E2E tests exercising extension capture flow
- `e2e/playwright.config.ts` — Updated with `extension` project entry
