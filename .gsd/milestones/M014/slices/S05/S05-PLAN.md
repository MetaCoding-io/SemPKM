# S05: Cross-browser, keyboard shortcut, E2E tests + user guide

**Goal:** Extension works in Firefox via separate manifest, Alt+S opens the popup, E2E tests verify the capture flow against Docker stack, and user guide documents everything.
**Demo:** Firefox manifest passes structural validation. Alt+S keyboard shortcut is declared in both manifests. Playwright extension tests create an API key, configure the extension, capture a Note, and verify it appears in the workspace. Chapter 32 user guide documents installation, configuration, and usage for both browsers.

## Must-Haves

- Firefox manifest (`manifest.firefox.json`) with `background.scripts` array, `browser_specific_settings.gecko`, and `commands._execute_action`
- Chrome manifest has `commands._execute_action` with `Alt+S` shortcut
- Dead imports removed from `service-worker.js` (no `import` statements — works as classic script)
- `"type": "module"` removed from Chrome manifest background section
- E2E Playwright fixture using `chromium.launchPersistentContext` with `--load-extension`
- E2E test: options page saves settings → popup loads types → form renders → object created → visible in workspace
- `extension` project in `playwright.config.ts`
- User guide `docs/guide/32-browser-extension.md` with 11 sections covering install, config, and usage
- README TOC updated with Chapter 32
- Glossary entries for Browser Extension and API Token
- Navigation chain: Ch 31 → Ch 32 → Appendix A

## Proof Level

- This slice proves: final-assembly (all 13 EXT requirements validated)
- Real runtime required: yes (E2E tests run against Docker stack with extension loaded)
- Human/UAT required: no (Playwright automates the Chrome extension flow)

## Verification

- Both manifests parse as valid JSON: `node -e "JSON.parse(require('fs').readFileSync('extension/manifest.json'))"` and same for `manifest.firefox.json`
- `node --check extension/background/service-worker.js` passes
- `rg "^import " extension/background/service-worker.js` returns empty (no imports)
- Chrome manifest has `commands._execute_action` with `Alt+S`
- Chrome manifest background has no `"type": "module"`
- Firefox manifest has `background.scripts`, `browser_specific_settings.gecko.id`, `commands._execute_action`
- `cd e2e && npx playwright test --project=extension` passes against running Docker stack
- `docs/guide/32-browser-extension.md` exists with all 11 sections
- `grep "32.*Browser Extension" docs/guide/README.md` matches
- `grep "Browser Extension\|API Token" docs/guide/appendix-d-glossary.md` returns 2+ matches

## Observability / Diagnostics

- Runtime signals: E2E tests produce Playwright HTML report + trace on failure
- Inspection surfaces: `npx playwright show-report` for test results; extension popup DevTools console for `[SemPKM]` log lines
- Failure visibility: Playwright trace captures screenshots and DOM snapshots on test failure; console log assertions catch silent JS errors

## Integration Closure

- Upstream surfaces consumed: S01 (extension scaffold, api-client, storage, popup, options, service worker), S02 (SHACL renderer, type selector), S03 (content script, context menu, schema-mapper), S04 (reference picker, edge creation)
- New wiring introduced in this slice: `extension` Playwright project in config, Firefox manifest file, keyboard shortcut commands in both manifests
- What remains before the milestone is truly usable end-to-end: nothing — S05 is the final slice

## Tasks

- [ ] **T01: Firefox manifest + keyboard shortcut + service-worker cleanup** `est:30m`
  - Why: Firefox compatibility requires a separate manifest (different background format, gecko settings). Keyboard shortcut (Alt+S) needs `commands._execute_action` in both manifests. Dead imports in service-worker.js block Firefox which doesn't support ES module background scripts.
  - Files: `extension/manifest.json`, `extension/manifest.firefox.json`, `extension/background/service-worker.js`
  - Do: Create Firefox manifest mirroring Chrome but with `background.scripts` array, `browser_specific_settings.gecko`, and `commands`. Add `commands._execute_action` to Chrome manifest. Remove dead `import` line from service-worker.js. Remove `"type": "module"` from Chrome manifest background.
  - Verify: Both manifests parse as valid JSON. `node --check` passes on service-worker.js. `rg "^import " extension/background/service-worker.js` returns empty. Both manifests have `commands._execute_action` with Alt+S. Chrome manifest background has no `type` key. Firefox manifest has `browser_specific_settings.gecko.id`.
  - Done when: Both manifests are valid, service worker has no imports, keyboard shortcut declared in both

- [ ] **T02: E2E Playwright tests for extension capture flow** `est:1h30m`
  - Why: EXT-13 requires automated E2E tests proving the full capture round-trip. Extension tests need `launchPersistentContext` which is incompatible with normal Playwright projects. This is the heaviest task in the slice.
  - Files: `e2e/fixtures/extension.ts`, `e2e/tests/25-extension/extension-capture.spec.ts`, `e2e/playwright.config.ts`
  - Do: Create extension fixture with persistent Chromium context loading extension via `--load-extension`. Extract extension ID from service worker URL. Write tests: (1) create API key via admin login, (2) configure options page with instance URL + API key + verify connection, (3) open popup → verify types loaded, (4) select type → verify SHACL form renders, (5) fill title → save → verify success toast, (6) navigate to workspace → verify object exists. Add `extension` project to playwright config (Chromium-only, no retries, custom testMatch).
  - Verify: `cd e2e && npx playwright test --project=extension` passes against Docker stack
  - Done when: Extension E2E tests pass proving options config → popup capture → workspace verification round-trip

- [ ] **T03: User guide chapter + glossary + README TOC** `est:45m`
  - Why: EXT-12 requires documentation covering installation, configuration, and usage for both browsers. This is the final deliverable closing out M014.
  - Files: `docs/guide/32-browser-extension.md`, `docs/guide/README.md`, `docs/guide/appendix-d-glossary.md`, `docs/guide/31-api-surface.md`
  - Do: Write Chapter 32 with 11 sections (Overview, Chrome install, Firefox install, API key generation, Settings config, Capturing objects, Auto-population, Context menu, Relationship picker, Keyboard shortcut, Troubleshooting). Add to README TOC after Ch 31. Add Browser Extension and API Token glossary entries. Update navigation chain: Ch 31 next → Ch 32, Ch 32 prev/next → Ch 31/Appendix A.
  - Verify: File exists with all 11 section headings. README has Ch 32 link. Glossary has both entries. Navigation chain links correct.
  - Done when: User guide chapter covers all extension features, README TOC updated, glossary complete, navigation chain wired

## Files Likely Touched

- `extension/manifest.json`
- `extension/manifest.firefox.json` (new)
- `extension/background/service-worker.js`
- `e2e/fixtures/extension.ts` (new)
- `e2e/tests/25-extension/extension-capture.spec.ts` (new)
- `e2e/playwright.config.ts`
- `docs/guide/32-browser-extension.md` (new)
- `docs/guide/README.md`
- `docs/guide/appendix-d-glossary.md`
- `docs/guide/31-api-surface.md`
