---
id: T04
parent: S03
milestone: M007
provides:
  - Chain builder UI for composing multi-level strategy chains (max 3 levels) with add/remove/preset controls
  - Filename template text input with {title}, {date}, {type}, {id} variable hint
  - collectFormData() sends strategy as array for chains, string for single (backward compat)
  - populateEditForm() restores chain levels and filename template when editing existing mounts
  - resetMountForm() clears chain levels and filename template
key_files:
  - backend/app/templates/browser/_vfs_settings.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
key_decisions:
  - Chain level selects exclude "flat" option — flat cannot appear in a chain
  - mountStrategyChanged() scans ALL chain levels to determine strategy-specific field visibility
  - updateAddChainButton() called from initMountForm() to set initial visibility on page load
patterns_established:
  - _chainLevelCount module-scoped counter tracks additional chain levels (beyond first select)
  - clearChainLevels() used by both resetMountForm() and applyChainPreset() for consistent cleanup
  - addChainLevel(strategyValue) accepts optional pre-set value for both edit restoration and preset application
observability_surfaces:
  - DOM inspection: #strategy-chain-container .chain-level-row count and select values
  - Form data shape: strategy is string for single, array for chains; filename_template present when non-empty
  - Add-level button: #add-chain-level-btn display style indicates flat/max state
duration: 40m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T04: UI — chain builder + filename template field

**Added chain builder UI with add/remove/preset controls and filename template input to the VFS mount form, with full create/edit/reset lifecycle support.**

## What Happened

Implemented all 5 plan steps:

1. **HTML template** (`_vfs_settings.html`): Replaced the bare strategy `<select>` with a flex row containing the select + "+ Add level" button. Added `#strategy-chain-container` div for dynamically-added chain levels, preset buttons row ("Tag → Date", "Type → Tag", "Type → Date"), and filename template text input with variable hint showing `{title}`, `{date}`, `{type}`, `{id}`.

2. **CSS** (`workspace.css`): Added styles for `.strategy-chain-row` (flex layout), `.chain-level-row` (with `↳` pseudo-element prefix), `.chain-level-remove` (× button with danger hover), `.chain-presets` (button group), and `.mount-form-hint` (variable hint with code styling).

3. **Chain builder JS** (`workspace.js`): Added `_chainLevelCount` counter, `addChainLevel(strategyValue)`, `removeChainLevel()`, `applyChainPreset(strategies)`, `clearChainLevels()`, and `updateAddChainButton()`. All exposed on `window` for inline event handlers. Chain level selects exclude "flat" (can't chain with flat). Each chain level select triggers re-evaluation of strategy-specific field visibility.

4. **Updated `mountStrategyChanged()`**: Now scans ALL chain levels — if ANY level is by-tag/by-property, shows group_by_property; if ANY is by-date, shows date_property. Also calls `updateAddChainButton()`.

5. **Updated `collectFormData()`**: Checks for chain level rows. If present, sends `strategy` as array. If single, sends as string (backward compat). Collects `filename_template` when non-empty. Strategy-specific field inclusion also checks all strategies in chain.

6. **Updated `populateEditForm()`**: Uses `mount.strategy_chain` array to restore chain levels on edit. Calls `clearChainLevels()` first, sets first strategy, then `addChainLevel(value)` for each subsequent. Sets filename template from `mount.filename_template`.

7. **Updated `resetMountForm()`**: Calls `clearChainLevels()` and clears filename template input.

8. **Added `updateAddChainButton()` call to `initMountForm()`**: Ensures button is hidden on initial page load when default strategy is "flat".

## Verification

**Browser verification (14 assertions, all PASS):**
- Chain builder visible with strategy select, "+ Add level" button, chain container, presets, and filename template
- "+ Add level" hidden when strategy is flat
- "+ Add level" visible when strategy is non-flat (by-type, by-tag, etc.)
- Clicking "+ Add level" adds chain level row with ↳ prefix, strategy select, × remove button
- Clicking "+ Add level" twice reaches max 3 total — button hidden (verified via `display === 'none'`)
- "Tag → Date" preset correctly sets first=by-tag, chain level=by-date (verified via JS evaluation)
- Both group_by_property and date_property fields shown when chain includes by-tag and by-date
- `collectFormData()` sends `strategy: "by-date"` (string) for single strategy — backward compat confirmed
- `collectFormData()` sends `strategy: ["by-tag","by-date"]` (array) for chains — confirmed via fetch intercept
- `filename_template` included in form data when non-empty — confirmed
- Created chain mount via API (`["by-tag","by-date"]` + `filename_template: "{date}-{title}"`)
- Clicked Edit on saved chain mount → form correctly restored with chain levels and filename template

**Slice-level tests:** `pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py` — 98 passed in 0.55s

**Slice verification status (T04 is final task):**
- ✅ All existing + new tests pass (98 passed)
- ✅ Filename template tests: expansion, missing variables, backward compat, dedup, bogus variable passthrough
- ✅ Chain tests: validation (max 3), pipe-delimited parse/format, chain depth narrowing
- ✅ Pydantic normalization: str and list input, rejects >3 levels, rejects invalid strategies
- ✅ Browser: mount form shows chain builder, create with 2-level chain, edit restores chain levels
- ✅ Backward compat: single-strategy mounts send string, not array
- ✅ Diagnostic: {bogus} passes through (covered by test_bogus_variable_passthrough)
- ✅ Diagnostic: chain depth > 3 raises ValueError (covered by test_four_level_chain_raises)

## Diagnostics

- **Chain state in DOM:** `document.querySelectorAll('#strategy-chain-container .chain-level-row').length` — number of additional chain levels
- **Form data inspection:** Intercept `mountSubmitForm` fetch call — body contains `strategy` (string or array) and optional `filename_template`
- **Add-level button state:** `document.getElementById('add-chain-level-btn').style.display` — `'none'` when flat or max 3
- **Failure shape:** No expected JS errors. If chain levels don't appear after clicking "+", check `_chainLevelCount` consistency

## Deviations

None.

## Known Issues

- Scope dropdown shows "Custom SPARQL..." with "all" in textarea when editing mounts that have `sparql_scope: "all"` — pre-existing issue in the scope handling logic, not introduced by this task.

## Files Created/Modified

- `backend/app/templates/browser/_vfs_settings.html` — Chain builder UI (strategy-chain-row, chain-container, presets), filename template input
- `frontend/static/js/workspace.js` — Chain management functions (add/remove/preset/clear/update), updated collectFormData/populateEditForm/resetMountForm/mountStrategyChanged/initMountForm
- `frontend/static/css/workspace.css` — Chain builder styles (strategy-chain-row, chain-level-row, chain-presets, mount-form-hint)
