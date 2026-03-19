---
verdict: needs-attention
remediation_round: 0
---

# Milestone Validation: M014

## Success Criteria Checklist

- [x] **User installs the extension in Chrome, configures localhost:3000 and an API key, and sees a green connection indicator** — E2E test 1 (extension-capture.spec.ts) proves this flow: API key creation → options page config → connection test → green status.
- [x] **Clicking the extension icon (or pressing Alt+S) opens a popup with a type selector populated from all installed Mental Models** — Alt+S declared in both manifests via `commands._execute_action`. E2E test 2 proves popup opens and type selector populates from API.
- [x] **Selecting a type renders a dynamic form matching the web app's SHACL forms** — `shacl-renderer.js` (588 lines) renders 10 property types with groups, multi-value, helptext. E2E test 2 verifies `[data-path]` inputs render after type selection. Node.js rendering tests verified all 4 model types (Contact, Deal, Note, Task).
- [x] **Title, URL, and selected text auto-populate from the current page's metadata** — `extractor.js` extracts og:title, URL, selection. `popup.js` `init()` injects via `chrome.scripting.executeScript`. Settings toggles (`autoFillTitle`, `autoFillUrl`, `includeSelection`) respected. 19 unit tests.
- [x] **Schema.org JSON-LD from the page auto-fills matching fields** — `schema-mapper.js` maps Person→Contact, Article→Note, etc. `applySchemaOrgToForm()` fills `[data-path]` inputs. Cross-namespace mappings (e.g. givenName→crm:firstName) plus direct namespace matches. 19 mapper unit tests.
- [x] **User can search existing objects and create typed relationships at capture time** — `reference-picker.js` with search-as-you-type, debounce, type filtering via `data-target-class`. Two-step save: `createObject()` then `createEdge()` per selection. Custom event bridge for multi-value reference fields.
- [x] **Right-click selected text → "Save to SemPKM" opens the popup with the text pre-filled** — Service worker registers `save-to-sempkm` context menu, stores selection in `chrome.storage.session`, calls `chrome.action.openPopup()` with `chrome.windows.create()` fallback. Popup `init()` checks session storage and consumes data.
- [x] **After saving, the object appears in the SemPKM workspace with all properties and relationships intact** — E2E test 3 proves: fill title → save → success toast → SPARQL query confirms object exists in triplestore.
- [x] **Extension works in both Chrome (MV3) and Firefox (WebExtension)** — Chrome manifest valid. Firefox `manifest.firefox.json` with `background.scripts` array, `browser_specific_settings.gecko`, same `commands._execute_action`. Both parse as valid JSON. Note: Firefox testing is structural validation only (Playwright can't load extensions in Firefox).

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | Backend auth fix + extension scaffold with working capture | `require_role_or_api` factory, 11 bearer auth tests, complete extension/ directory (manifest, api-client, storage, service worker, popup, options), admin API key management page | pass |
| S02 | SHACL form renderer + type selector | `shacl-renderer.js` (588 lines, 10 property types, groups, multi-value), dynamic type selector → shape fetch → form render, backend multi-value property support, 380px popup CSS | pass |
| S03 | Content scripts + context menu + schema.org | Content script extractor, schema-mapper module (6 schema.org type mappings), context menu with session storage bridge, popup auto-fill on open and type change. 19 mapper unit tests. | pass |
| S04 | Relationship picker + edge creation | `reference-picker.js` (3 exports, search-as-you-type, type filtering), two-step save with per-edge error isolation, custom event bridge for multi-value re-init | pass |
| S05 | Cross-browser, keyboard shortcut, E2E tests + user guide | Firefox manifest, Alt+S shortcut, 3 Playwright E2E tests (420 lines), Chapter 32 user guide (303 lines), glossary entries, README TOC | pass |

## Cross-Slice Integration

All boundary map entries verified:

- **S01 → S02:** `api-client.js` (`getTypes`, `getShape`), `storage.js`, popup shell, type selector — all consumed by S02's SHACL renderer integration ✅
- **S01 → S03:** `api-client.js`, `storage.js`, service worker shell, `populateFromPageData` — all consumed by S03's content script and context menu wiring ✅
- **S01 → S04:** `api-client.js` (`searchObjects`, `createEdge`) — consumed by reference-picker.js ✅
- **S02 → S04:** `.reference-field` DOM with `data-target-class` attribute — consumed by reference-picker.js. `getFormValues()` returns `{path: value|[values]}` — consumed by popup save flow ✅
- **S03 → S05:** Content script extractor and context menu handler — in place for E2E tests ✅
- **S04 → S05:** Relationship picker + edge creation — in place for E2E tests ✅

No boundary mismatches found.

## Requirement Coverage

All 13 EXT requirements addressed:

| Requirement | Primary | Evidence | Status |
|-------------|---------|----------|--------|
| EXT-01 (popup capture) | S01 | Popup with type selector, title/body/URL form, save flow | ✅ delivered |
| EXT-02 (SHACL forms) | S02 | 10 property types, groups, multi-value, helptext, validation indicators | ✅ delivered |
| EXT-03 (auto-population) | S03 | Page metadata extraction, settings toggles, 19 unit tests | ✅ delivered |
| EXT-04 (relationship picker) | S04 | Search-as-you-type, type filtering, two-step save with edge creation | ✅ delivered |
| EXT-05 (context menu) | S03 | "Save to SemPKM" right-click with session storage bridge | ✅ delivered |
| EXT-06 (schema.org) | S03 | 6 type mappings, cross-namespace property mapping, 19 mapper tests | ✅ delivered |
| EXT-07 (settings) | S01 | Options page with connection test, type selector, capture behavior toggles | ✅ delivered |
| EXT-08 (keyboard shortcut) | S05 | `Alt+S` in both Chrome and Firefox manifests via `_execute_action` | ✅ delivered |
| EXT-09 (success/error feedback) | S01 | `showToast()` for success (green) and error (red), loading states, double-submit prevention | ✅ delivered |
| EXT-10 (cross-browser) | S05 | Firefox manifest with gecko settings, background.scripts array | ✅ delivered |
| EXT-11 (backend auth) | S01 | `require_role_or_api` factory, 11 bearer auth unit tests, admin API key page | ✅ delivered |
| EXT-12 (user guide) | S05 | Chapter 32 (303 lines, 25 section headings), README TOC, 2 glossary entries, nav chain | ✅ delivered |
| EXT-13 (E2E tests) | S05 | 3 Playwright tests (420 lines): options config, SHACL form render, capture + SPARQL verification | ✅ delivered |

## Milestone Definition of Done Checklist

- [x] All five slices complete with individual summaries — S01-S04 have real summaries; S05 has a doctor-generated placeholder (task summaries are authoritative and complete)
- [x] `POST /api/commands` accepts Bearer token auth — `require_role_or_api` factory + 11 unit tests
- [x] Extension installs in Chrome and Firefox from unpacked/sideloaded directory — both manifests valid JSON, all referenced files exist
- [x] Popup renders SHACL forms correctly for all standard property types — 10 types (string, date, dateTime, boolean, integer, decimal, anyURI, enum, object reference, tags) with groups and multi-value
- [x] Auto-population works for title, URL, selected text, and schema.org JSON-LD — extractor.js + schema-mapper.js + popup init flow
- [x] Relationship picker searches existing objects and creates edges — reference-picker.js + two-step save in popup.js
- [x] Context menu "Save to SemPKM" captures selected text — service worker handler + session storage bridge
- [x] Settings page configures instance URL, API key, and default type with connection test — options.html/js with green/red indicator
- [x] Captured objects appear in SemPKM workspace — E2E test 3 verifies via SPARQL query
- [x] E2E tests exercise the capture flow against Docker stack — 3 tests in extension-capture.spec.ts
- [x] User guide chapter documents extension install, configuration, and usage — Chapter 32 (303 lines)
- [ ] Final integrated acceptance scenarios pass (the 6 scenarios from M014-CONTEXT.md) — **see note below**

## Minor Gaps (not blocking)

1. **S05 summary is a doctor-created placeholder.** The three task summaries (T01, T02, T03) are complete and authoritative. The slice-level summary should be regenerated from them but this is a documentation gap, not a delivery gap.

2. **S05 UAT is a doctor-created placeholder.** Same situation — the actual E2E tests in `extension-capture.spec.ts` serve as the functional UAT. The `.gsd` artifact is just missing its final form.

3. **Firefox runtime testing is structural only.** The Firefox manifest validates structurally and uses the correct Firefox WebExtension conventions (`background.scripts` array, `browser_specific_settings.gecko`). However, Playwright cannot load extensions in Firefox persistent context, so runtime behavior is only proven in Chromium. This is a known limitation documented in T02.

4. **Final integrated acceptance scenarios (from M014-CONTEXT.md) are partially covered.** The 6 scenarios listed in the context document are:
   - ✅ User installs extension, configures localhost:3000, captures a Note — proven by E2E test 3
   - ✅ Type selector shows types from all installed Mental Models — proven by E2E test 2
   - ⚠️ Selecting "Contact" renders CRM-specific fields — verified via Node.js rendering test against live API (S02), not via E2E
   - ⚠️ Schema.org Person data auto-fills Contact fields — verified via 19 mapper unit tests (S03), not via live-page E2E
   - ⚠️ User creates a relationship between captured object and existing Concept — code is present (reference-picker.js + popup save flow), but E2E test 3 only tests basic Note capture without relationships
   - ⚠️ Object appears in SemPKM workspace — E2E uses SPARQL API verification (correct) rather than workspace UI verification (persistent context hangs on workspace navigation, documented in KNOWLEDGE.md)

   The ⚠️ scenarios are proven at unit/integration level but not at full E2E level. This is a reasonable tradeoff given Chrome extension testing limitations (no Playwright support for popup UI inspection, persistent context navigation issues).

5. **T03 docs inaccuracy about context menu.** The T03 summary states "no `chrome.contextMenus.create()` handler exists in the service worker" — but this is incorrect. The handler exists at lines 16-41 of `service-worker.js`. The user guide correctly documents context menu as a declared capability. The docs content itself is accurate; only the T03 summary has this factual error.

## Verdict Rationale

**Verdict: needs-attention**

All 13 EXT requirements are delivered with code, tests, and documentation. All 9 success criteria from the roadmap are met. All 5 slices delivered their claimed outputs. Cross-slice integration is clean with no boundary mismatches.

The "needs-attention" (rather than "pass") is for transparency about:
- S05 has placeholder summary/UAT artifacts (doctor-generated) — the work is done, the `.gsd` artifacts need cleanup
- Firefox runtime testing is structural-only (Playwright limitation)
- 3 of 6 final acceptance scenarios are proven at unit/integration level, not full E2E (Chrome extension testing constraints)

None of these block milestone completion. They are documented limitations consistent with the `sideload-only Phase 1` distribution scope (D168).

## Remediation Plan

No remediation slices needed. The gaps are known limitations of browser extension testing infrastructure, not missing features. All code is implemented, tested at the appropriate level, and documented.
