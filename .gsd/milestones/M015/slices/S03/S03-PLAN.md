# S03: Settings, E2E tests, and user guide

**Goal:** Auto-context toggle configurable in options page, Playwright E2E tests prove badge + sidebar + link action against Docker stack, user guide Chapter 33 documents the full context overlay feature, EXT-14 through EXT-21 requirements registered and validated.
**Demo:** Running `npx playwright test --project=extension extension-context-overlay` passes against Docker test stack; options page has a "Context Overlay" section with three controls; Chapter 33 exists in the user guide with correct navigation links.

## Must-Haves

- "Context Overlay" section in options page with autoCheckContext toggle, contextCheckDelay input, contextTimeout input — all persisting via storage round-trip
- E2E Playwright test proving: context query returns results for a Note with matching schema:url, sidebar displays grouped results, "Open" action creates a new tab, "Link to this page" action creates an edge verifiable via SPARQL
- User guide Chapter 33 covering sidebar, badge, actions, settings, cross-browser notes, troubleshooting
- EXT-14 through EXT-21 registered in REQUIREMENTS.md as active, then validated where E2E evidence supports it
- README TOC updated with Chapter 33
- Glossary entries for Context Overlay, Knowledge Sidebar, Context Badge

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker test stack for E2E)
- Human/UAT required: no

## Verification

- `npx playwright test --project=extension e2e/tests/25-extension/extension-context-overlay.spec.ts` passes against Docker test stack
- `node --check extension/options/options.js` passes (no syntax errors after settings changes)
- Chapter 33 file exists at `docs/guide/33-context-overlay.md` with navigation footer
- README.md TOC includes Chapter 33
- `grep -c "Context Overlay\|Knowledge Sidebar\|Context Badge" docs/guide/appendix-d-glossary.md` returns ≥ 3

## Integration Closure

- Upstream surfaces consumed: `extension/shared/storage.js` (settings keys from S01), `extension/sidebar/sidebar.js` (sidebar UI from S01/S02), `extension/background/service-worker.js` (context pipeline from S01/S02), `e2e/fixtures/extension.ts` (persistent context fixture from M014)
- New wiring introduced in this slice: options page ↔ context overlay settings keys, E2E test file exercising full context pipeline
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Add Context Overlay settings section to options page and register requirements** `est:30m`
  - Why: Options page needs UI controls for autoCheckContext (toggle), contextCheckDelay (ms), and contextTimeout (ms) — these keys already exist in storage.js DEFAULTS from S01 but have no UI. Also registers EXT-14 through EXT-21 requirements.
  - Files: `extension/options/options.html`, `extension/options/options.js`, `.gsd/REQUIREMENTS.md`
  - Do: Add a "Context Overlay" `<section>` between "Capture Defaults" and the save footer in options.html with three form controls. Wire DOM refs, loadSettings(), and saveCurrentSettings() in options.js following the existing pattern. Register EXT-14 through EXT-21 as active requirements.
  - Verify: `node --check extension/options/options.js` passes; storage round-trip confirmed by reading options.js code
  - Done when: Options page has the Context Overlay section with three controls, all three settings save/load correctly, EXT-14–EXT-21 registered in REQUIREMENTS.md

- [x] **T02: Write E2E Playwright tests for context overlay against Docker stack** `est:1h30m`
  - Why: Proves the full context pipeline works end-to-end: create seed data → navigate → wait for debounce → sidebar shows results → Open action works → Link action creates edge. Validates EXT-14 through EXT-19.
  - Files: `e2e/tests/25-extension/extension-context-overlay.spec.ts`
  - Do: New test file reusing setupAndCreateApiKey/injectExtensionSettings pattern from extension-capture.spec.ts. Create a Note with schema:url via POST /api/commands, inject extension settings including autoCheckContext:true, open sidebar page directly, send refreshContextResults message, verify grouped results render, test Open action, test Link to this page action with SPARQL verification.
  - Verify: `npx playwright test --project=extension extension-context-overlay` passes against running Docker test stack
  - Done when: All E2E tests pass, EXT-14 through EXT-19 validated in REQUIREMENTS.md

- [ ] **T03: Write user guide Chapter 33 and update navigation chain** `est:45m`
  - Why: Milestone definition of done requires user guide documentation. Chapter 33 covers the entire context overlay feature for end users.
  - Files: `docs/guide/33-context-overlay.md`, `docs/guide/32-browser-extension.md`, `docs/guide/README.md`, `docs/guide/appendix-d-glossary.md`
  - Do: Write Chapter 33 following Chapter 32's structure and voice. Cover sidebar (Alt+K), badge count, grouped results, all three actions (Open, Link, Add Evidence), auto-context settings, cross-browser notes, troubleshooting. Update ch32 footer to link to ch33. Update README TOC. Add glossary entries.
  - Verify: Chapter 33 exists with correct navigation; README TOC includes it; glossary has 3+ new entries
  - Done when: All docs files updated, navigation chain ch32 → ch33 → appendix-a is intact

## Observability / Diagnostics

- **Settings round-trip:** `chrome.storage.sync.get()` in devtools Application > Storage confirms autoCheckContext, contextCheckDelay, contextTimeout keys are persisted after save
- **Console logging:** options.js logs `[SemPKM] Settings saved` on successful persist and `[SemPKM] Options page loaded` on init — visible in extension devtools console
- **E2E test diagnostics:** Playwright test logs include test name, assertion failures with element snapshots, and Docker compose logs on failure
- **No secrets involved:** No API keys or tokens are processed in this slice's settings controls (they live in the existing Connection section)

## Files Likely Touched

- `extension/options/options.html`
- `extension/options/options.js`
- `e2e/tests/25-extension/extension-context-overlay.spec.ts`
- `docs/guide/33-context-overlay.md`
- `docs/guide/32-browser-extension.md`
- `docs/guide/README.md`
- `docs/guide/appendix-d-glossary.md`
- `.gsd/REQUIREMENTS.md`
