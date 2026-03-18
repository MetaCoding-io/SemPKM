# S05: Cross-browser, Keyboard Shortcut, E2E Tests + User Guide — Research

**Date:** 2026-03-18
**Status:** Complete

## Summary

S05 is a polish-and-verification slice. The extension is functionally complete from S01–S04: popup capture, SHACL forms, auto-population, schema.org, context menu, and relationship picker all work. S05 adds: (1) Firefox manifest for cross-browser support, (2) Alt+S keyboard shortcut via Chrome's `commands` API, (3) E2E Playwright tests for the capture flow against the Docker stack, and (4) a user guide chapter documenting installation, configuration, and usage.

The biggest technical question was E2E testing. Playwright supports Chrome extension testing via `chromium.launchPersistentContext()` with `--load-extension` args — this works for Chromium only (not Firefox or headless). The popup is accessible at `chrome-extension://{extensionId}/popup.html` as a regular page, which sidesteps the popup-interaction problem. The extension ID is extracted from the service worker URL. This is a well-documented Playwright pattern.

Firefox extension E2E is not feasible via Playwright — Firefox doesn't support the `--load-extension` flag. The Firefox manifest is a static file change (different `background` format + `browser_specific_settings.gecko`), verifiable by structural checks only.

## Recommendation

Four concerns, three tasks:

1. **Firefox manifest + keyboard shortcut** — Create `manifest.firefox.json`, clean up dead imports in service-worker.js, add `commands._execute_action` to both manifests. Low risk.

2. **E2E tests** — Playwright tests using persistent context with extension loaded. Test popup as a regular page at `chrome-extension://{id}/popup.html`. Chromium-only project in playwright config. Heaviest task.

3. **User guide** — Chapter 32 documenting sideload install (Chrome + Firefox), API key generation, extension settings, capture workflows, keyboard shortcut, and troubleshooting.

Build order: manifest changes first (1), then E2E tests (2), then docs (3).

## Implementation Landscape

### Key Files

**Existing extension files:**
- `extension/manifest.json` — Chrome MV3 manifest. Needs `commands` key added for keyboard shortcut. Currently has NO `commands` key.
- `extension/background/service-worker.js` — 40 lines. Imports `getClient` and `getSettings` from `../shared/storage.js` but **never calls either function**. These dead imports force `"type": "module"` in the manifest, which Firefox MV3 background scripts don't support. Removing them makes the file self-contained.
- `extension/shared/storage.js` — Already has `typeof chrome !== 'undefined'` guard. The `browser.*` polyfill consideration is moot — Firefox WebExtensions provide `chrome.*` as an alias anyway.
- `extension/popup/popup.js` (686 lines) — Uses `chrome.storage.session`, `chrome.tabs.query`, `chrome.scripting.executeScript`, `chrome.runtime.openOptionsPage`. Firefox provides `chrome.*` compat layer.
- `extension/options/options.js` (235 lines) — Only uses `chrome.*` indirectly via `storage.js` imports. No direct `chrome.*` calls.

**New files to create:**
- `extension/manifest.firefox.json` — Firefox manifest with `background.scripts` array (not `service_worker`), `browser_specific_settings.gecko.id`, and `commands._execute_action`.
- `e2e/tests/25-extension/extension-capture.spec.ts` — Extension capture flow E2E test.
- `e2e/fixtures/extension.ts` — Fixture launching persistent Chromium context with extension.
- `docs/guide/32-browser-extension.md` — User guide chapter.

**Files to modify:**
- `extension/manifest.json` — Add `commands._execute_action` for Alt+S.
- `extension/background/service-worker.js` — Remove dead `import` line (making it non-module, compatible with both browsers).
- `e2e/playwright.config.ts` — Add `extension` project.
- `docs/guide/README.md` — Add Chapter 32 to TOC.
- `docs/guide/appendix-d-glossary.md` — Add glossary entries.

### Chrome `commands` API for Keyboard Shortcut

The `_execute_action` command is a special Chrome command that opens the extension popup. No JS handler needed.

```json
"commands": {
  "_execute_action": {
    "suggested_key": {
      "default": "Alt+S",
      "mac": "Alt+S"
    },
    "description": "Open SemPKM Capture"
  }
}
```

Users can override in `chrome://extensions/shortcuts`. Firefox uses the same `commands` manifest key. Both manifests get this block.

### Firefox Manifest

Firefox MV3 (109+) key differences from Chrome:

1. `background.scripts: ["background/service-worker.js"]` array instead of `background.service_worker` string
2. `browser_specific_settings.gecko.id: "sempkm@sempkm.org"` required for persistent storage
3. No `"type": "module"` in background — Firefox MV3 background scripts run as classic scripts

The ES module constraint is solved by removing the dead imports from `service-worker.js`. The file currently has `import { getClient, getSettings } from '../shared/storage.js'` but never calls either function. Without imports, Chrome doesn't need `"type": "module"` either — remove it from the Chrome manifest too. The service worker body uses only `chrome.*` APIs directly.

The Firefox manifest structure:
```json
{
  "manifest_version": 3,
  "name": "SemPKM Capture",
  "version": "0.1.0",
  "background": { "scripts": ["background/service-worker.js"] },
  "browser_specific_settings": {
    "gecko": { "id": "sempkm@sempkm.org", "strict_min_version": "109.0" }
  },
  "commands": { "_execute_action": { ... } },
  ...rest same as Chrome manifest minus background.type
}
```

### E2E Test Architecture

**Playwright extension fixture pattern** (from official docs):

```typescript
import { test as base, chromium, type BrowserContext } from '@playwright/test';
import path from 'path';

export const test = base.extend<{ context: BrowserContext; extensionId: string }>({
  context: async ({}, use) => {
    const pathToExtension = path.join(__dirname, '../../extension');
    const context = await chromium.launchPersistentContext('', {
      channel: 'chromium',
      args: [
        `--disable-extensions-except=${pathToExtension}`,
        `--load-extension=${pathToExtension}`,
      ],
    });
    await use(context);
    await context.close();
  },
  extensionId: async ({ context }, use) => {
    let [sw] = context.serviceWorkers();
    if (!sw) sw = await context.waitForEvent('serviceworker');
    const extensionId = sw.url().split('/')[2];
    await use(extensionId);
  },
});
```

**Test flow:**
1. Launch persistent context with extension loaded
2. Create API key: login as owner via magic link → `POST /admin/api-keys` → get plaintext token
3. Navigate to `chrome-extension://{id}/options/options.html` → fill instance URL (`http://localhost:3901`) + API key → save settings
4. Navigate to `chrome-extension://{id}/popup/popup.html` → verify type selector populated
5. Select a type (e.g. Note) → verify SHACL form renders (dynamic-form has children)
6. Fill title → click Save → verify success toast
7. Navigate to `http://localhost:3901/browser/` → verify object exists in workspace

**API key creation:** `POST /admin/api-keys` requires owner session cookie. Test logs in as owner first (same `loginViaApi` pattern from `e2e/fixtures/auth.ts`), then creates the key via the admin endpoint.

**Separate Playwright project:** Extension tests need `launchPersistentContext` which is incompatible with the default project fixtures. Add to `playwright.config.ts`:

```typescript
{
  name: 'extension',
  testMatch: /25-extension\/.*\.spec\.ts/,
  use: { /* no devices — custom context in fixture */ },
  retries: 0,
}
```

### User Guide Chapter

`docs/guide/32-browser-extension.md` sections:
1. Overview — what the extension does
2. Installation (Chrome) — sideload from `extension/` directory
3. Installation (Firefox) — sideload using `manifest.firefox.json`
4. Generating an API Key — admin page walkthrough
5. Configuration — settings page (instance URL, API key, connection test, default type, capture preferences)
6. Capturing Objects — popup workflow (icon click or Alt+S, type selection, form filling, save)
7. Auto-population — title/URL/selection extraction, schema.org JSON-LD
8. Context Menu — right-click "Save to SemPKM"
9. Relationship Picker — searching and linking existing objects
10. Keyboard Shortcut — Alt+S and how to customize
11. Troubleshooting — common issues

Update `docs/guide/README.md` TOC. Add glossary entries (Browser Extension, API Token). Navigation chain: Ch 31 → Ch 32 → Appendix A.

### Build Order

1. **T01: Firefox manifest + keyboard shortcut + service-worker cleanup** — All manifest-level changes. Create `manifest.firefox.json`, remove dead imports from `service-worker.js`, remove `"type": "module"` from Chrome manifest background, add `commands._execute_action` to both manifests. Verify syntax.

2. **T02: E2E Playwright tests** — Create extension fixture in `e2e/fixtures/extension.ts`, write capture flow test in `e2e/tests/25-extension/extension-capture.spec.ts`, add `extension` project to `playwright.config.ts`. Run against Docker stack.

3. **T03: User guide + glossary + README** — Write `docs/guide/32-browser-extension.md`, update README TOC, add glossary entries. Navigation chain update.

### Verification Approach

**T01:**
- `node --check extension/background/service-worker.js` passes
- Both manifests parse as valid JSON
- Chrome manifest has `commands._execute_action` with `Alt+S`
- Firefox manifest has `background.scripts`, `browser_specific_settings.gecko.id`, `commands`
- `rg "^import " extension/background/service-worker.js` returns empty (no imports)
- Chrome manifest has no `"type": "module"` in background section

**T02:**
- `cd e2e && npx playwright test --project=extension` passes against running Docker stack
- Tests prove: options page saves settings, popup loads types, form renders, object creation succeeds, object visible in workspace

**T03:**
- `docs/guide/32-browser-extension.md` exists with all 11 sections
- README TOC includes Chapter 32
- Glossary has new entries
- Navigation chain: Ch 31 → Ch 32 → Appendix A

## Constraints

- Playwright extension tests require `chromium.launchPersistentContext()` — cannot use normal context or default project fixtures.
- Firefox extension E2E is not possible via Playwright — Firefox doesn't support `--load-extension`.
- Extension tests are Chromium-only — separate Playwright project.
- `chrome.storage.session` may behave differently in Playwright's persistent context — popup's context menu pre-fill check has try/catch already.

## Common Pitfalls

- **Service worker ES module imports in Firefox** — Firefox MV3 background scripts don't support `import` statements. Current `service-worker.js` imports `getClient` and `getSettings` but never calls them. Remove these dead imports so the file works as a plain script in both browsers. Also remove `"type": "module"` from Chrome manifest `background` section.
- **Extension ID instability** — Chromium extension ID changes across persistent context launches. Test fixture must extract it dynamically from the service worker URL each time.
- **API key creation for tests** — Extension needs a Bearer token. Test must create one via `POST /admin/api-keys` with owner session cookie. The admin router returns plaintext token only once on creation.
- **`chrome.storage.sync` in persistent context** — May fall back to `chrome.storage.local`. `storage.js` already handles this with `chrome.storage.sync || chrome.storage.local` fallback.

## Sources

- Playwright Chrome extension testing: https://playwright.dev/docs/chrome-extensions — persistent context fixture, `--load-extension`, service worker ID extraction
- Chrome MV3 commands API: `_execute_action` wires to popup open automatically
- M014 research: Firefox manifest differences, `browser_specific_settings.gecko.id` requirement
