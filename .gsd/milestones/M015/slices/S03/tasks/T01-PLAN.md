---
estimated_steps: 6
estimated_files: 3
---

# T01: Add Context Overlay settings section to options page and register requirements

**Slice:** S03 — Settings, E2E tests, and user guide
**Milestone:** M015

## Description

Add a "Context Overlay" section to the extension options page (between "Capture Defaults" and the save footer) with three controls: an autoCheckContext checkbox toggle, a contextCheckDelay number input (ms), and a contextTimeout number input (ms). These keys already exist in `extension/shared/storage.js` DEFAULTS from S01 — this task only adds UI and wires them into the existing load/save cycle.

Also register EXT-14 through EXT-21 as active requirements in `.gsd/REQUIREMENTS.md`.

## Steps

1. **Read existing options page files** — `extension/options/options.html` and `extension/options/options.js` to confirm current structure and patterns.

2. **Add Context Overlay HTML section** to `extension/options/options.html`. Insert between the "Capture Defaults" `</section>` closing tag and the "Save Actions" `<section class="settings-footer">`. The section should contain:
   - `<h2 class="section-title">Context Overlay</h2>`
   - Checkbox: `<input type="checkbox" id="auto-check-context" checked>` with label "Automatically check for related objects when browsing"
   - Number input: `<input type="number" id="context-check-delay" min="500" max="10000" step="500">` with label "Check delay (ms)" and hint "How long to wait after page load before checking (default: 2000ms)"
   - Number input: `<input type="number" id="context-timeout" min="1000" max="30000" step="1000">` with label "Request timeout (ms)" and hint "Maximum time to wait for context query response (default: 5000ms)"

3. **Wire DOM references** in `extension/options/options.js`. Add three const references following the existing pattern:
   ```js
   const $autoCheckContext   = document.getElementById('auto-check-context');
   const $contextCheckDelay  = document.getElementById('context-check-delay');
   const $contextTimeout     = document.getElementById('context-timeout');
   ```

4. **Update `loadSettings()`** to populate the three new fields from stored settings:
   ```js
   $autoCheckContext.checked = settings.autoCheckContext !== false;
   $contextCheckDelay.value = settings.contextCheckDelay || 2000;
   $contextTimeout.value = settings.contextTimeout || 5000;
   ```

5. **Update `saveCurrentSettings()`** to include the three new fields in the settings object:
   ```js
   autoCheckContext: $autoCheckContext.checked,
   contextCheckDelay: parseInt($contextCheckDelay.value, 10) || 2000,
   contextTimeout: parseInt($contextTimeout.value, 10) || 5000,
   ```

6. **Register requirements EXT-14 through EXT-21** in `.gsd/REQUIREMENTS.md`. Add them to the Active section with status `active`, class `core-capability`, source `design (BROWSER-EXTENSION-DESIGN.md)`:
   - EXT-14: Badge shows context count after page load, cached per URL
   - EXT-15: Sidebar opens via Alt+K showing grouped results from context query
   - EXT-16: Open action navigates to SemPKM object in new tab
   - EXT-17: Link to this page action creates schema:url edge
   - EXT-18: Add Evidence action captures highlighted text and creates linked Evidence object
   - EXT-19: Auto-context toggle in settings controls badge/check behavior
   - EXT-20: URL→results cache (LRU, max 100) in service worker memory
   - EXT-21: Cross-browser support (Chrome Side Panel + Firefox sidebar_action)

   Also add them to the Traceability table with primary owner `M015/S01` (for EXT-14 through EXT-18, EXT-20, EXT-21), `M015/S03` (for EXT-19).

## Must-Haves

- [ ] "Context Overlay" section renders between Capture Defaults and Save footer
- [ ] autoCheckContext checkbox, contextCheckDelay number input, contextTimeout number input all present
- [ ] loadSettings() populates all three new fields from storage
- [ ] saveCurrentSettings() persists all three new fields to storage
- [ ] `node --check extension/options/options.js` passes
- [ ] EXT-14 through EXT-21 registered in REQUIREMENTS.md Active section

## Verification

- `node --check extension/options/options.js` — no syntax errors
- `node --check extension/options/options.html` is not applicable (HTML), but visually inspect the section structure
- `grep "auto-check-context" extension/options/options.html` finds the checkbox
- `grep "contextCheckDelay" extension/options/options.js` finds load/save wiring
- `grep "EXT-14" .gsd/REQUIREMENTS.md` confirms requirement registration
- `grep -c "EXT-1[4-9]\|EXT-2[0-1]" .gsd/REQUIREMENTS.md` returns ≥ 16 (8 requirements × 2 sections each)

## Observability Impact

- **Settings persistence:** After saving, `chrome.storage.sync` will contain `autoCheckContext` (boolean), `contextCheckDelay` (number), `contextTimeout` (number). Inspectable in devtools Application > Storage > chrome.storage.sync.
- **Console signals:** `[SemPKM] Settings saved` logged on save; `[SemPKM] Options page loaded` logged on init. Both already exist — no new logging added.
- **Failure visibility:** If DOM IDs are missing or mistyped, `loadSettings()` will throw a `TypeError` on `null.checked` / `null.value` access — visible in extension devtools console immediately on page load.

## Inputs

- `extension/options/options.html` — current options page HTML structure (inlined in slice context)
- `extension/options/options.js` — current load/save logic with DOM refs pattern (inlined in slice context)
- `extension/shared/storage.js` — DEFAULTS already contains `autoCheckContext: true`, `contextCheckDelay: 2000`, `contextTimeout: 5000` (no changes needed here)
- `.gsd/REQUIREMENTS.md` — current requirements file (needs EXT-14 through EXT-21 added)
- S01 summary — settings keys defined in storage.js DEFAULTS

## Expected Output

- `extension/options/options.html` — has new "Context Overlay" section with three form controls
- `extension/options/options.js` — DOM refs + loadSettings + saveCurrentSettings updated for three new fields
- `.gsd/REQUIREMENTS.md` — EXT-14 through EXT-21 registered as active with correct metadata
