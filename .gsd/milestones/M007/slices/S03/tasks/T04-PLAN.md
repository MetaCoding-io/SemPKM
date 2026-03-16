---
estimated_steps: 5
estimated_files: 3
---

# T04: UI — chain builder + filename template field

**Slice:** S03 — VFS Composable Chains & Filename Templates
**Milestone:** M007

## Description

Add chain-level builder UI (strategy stacking with + button, max 3 levels, predefined combos) and filename template text input to the mount form. Update `collectFormData()` and mount populate/reset functions to handle both features. This is the final integration task — after this, both features are fully wired end-to-end.

## Steps

1. **Add chain builder UI** — In `backend/app/templates/browser/_vfs_settings.html`:
   - Below the existing strategy `<select>` (id=`mount-strategy`), add a container `<div id="strategy-chain-container">` for additional chain levels
   - Add an "Add level" button (`<button type="button" id="add-chain-level-btn" class="btn-sm">+ Add level</button>`) that appears next to the strategy select. Hide it when strategy is `flat` (flat can't be in a chain).
   - Each additional chain level is a row: `<div class="chain-level-row" data-chain-index="N">` containing a `<select>` with the same strategy options and a remove button (×).
   - Add a "Presets" section with quick-fill buttons: "Tag → Date", "Type → Tag", "Type → Date". Each button fills the chain levels.
   - Max 3 levels total (including the first). Disable "+ Add level" when at 3.
   - Add `filename_template` text input below the strategy section:
     ```html
     <div class="mount-form-row">
       <label class="mount-form-label" for="mount-filename-template">Filename template</label>
       <input type="text" id="mount-filename-template" class="settings-input"
              placeholder="{title} — or {date}-{title}, {type}/{title}, etc.">
       <div class="mount-form-hint">Variables: {title}, {date}, {type}, {id}</div>
     </div>
     ```

2. **Add chain builder JavaScript** — In `frontend/static/js/workspace.js`:
   - `addChainLevel()`: clone a strategy dropdown, insert into `#strategy-chain-container`, assign unique id `chain-strategy-{index}`. Increment chain count. Hide "+ Add level" at max 3. Show strategy-specific fields based on what strategies are in the chain.
   - `removeChainLevel(index)`: remove the row, reindex remaining. Re-show "+ Add level" if under 3.
   - `applyChainPreset(strategies)`: clear chain levels, set first strategy, add remaining levels. E.g., `applyChainPreset(["by-tag", "by-date"])` sets mount-strategy to "by-tag" and adds one chain level set to "by-date".
   - Strategy-specific fields visibility: scan ALL chain levels. If ANY level is by-tag or by-property, show group_by_property field. If ANY is by-date, show date_property field.
   - Expose functions on window: `window.addChainLevel`, `window.removeChainLevel`, `window.applyChainPreset`.

3. **Update collectFormData()** — In `frontend/static/js/workspace.js`:
   - After collecting the first strategy from `#mount-strategy`, check for chain level rows in `#strategy-chain-container`.
   - If chain levels exist, send `strategy` as an array: `[firstStrategy, ...chainLevelStrategies]`.
   - If only one level (no chain), send as string (backward compat).
   - Collect `filename_template` from `#mount-filename-template`. If non-empty, include in data.

4. **Update mountPopulateForm()** — In `frontend/static/js/workspace.js` (the function that fills the form when editing an existing mount):
   - Check if `mount.strategy_chain` exists and has length > 1. If so:
     - Set first strategy dropdown to `chain[0]`
     - Call `addChainLevel()` for each subsequent entry, setting the dropdown value
   - Set `#mount-filename-template` value from `mount.filename_template || ""`.

5. **Update resetMountForm()** — In `frontend/static/js/workspace.js`:
   - Clear all chain level rows from `#strategy-chain-container`
   - Reset chain counter to 0
   - Clear `#mount-filename-template` value
   - Re-show "+ Add level" button

## Must-Haves

- [ ] Chain builder UI: add/remove strategy levels (max 3 total)
- [ ] Predefined combo buttons populate chain levels correctly
- [ ] Strategy-specific fields (group_by_property, date_property) show when ANY chain level needs them
- [ ] Filename template text input with variable hint
- [ ] `collectFormData()` sends `strategy` as array for chains, string for single
- [ ] `mountPopulateForm()` restores chain levels and filename template on edit
- [ ] `resetMountForm()` clears chain levels and filename template
- [ ] "Add level" hidden when strategy is flat or at max 3

## Verification

- Browser: open VFS settings → create new mount → chain builder visible with + button
- Click "+ Add level" → second strategy dropdown appears → click again → third appears → + button disabled
- Click "Tag → Date" preset → first=by-tag, second=by-date auto-populated
- Remove second level → back to single strategy
- Save mount with chain → edit mount → chain levels restored
- Save mount with filename template → edit → template restored
- Save mount with single strategy → verify still sends string (backward compat)

## Inputs

- T03's async API: accepts `strategy: str | list[str]` and `filename_template`
- `backend/app/templates/browser/_vfs_settings.html` — existing mount form with strategy select, type filter checkboxes
- `frontend/static/js/workspace.js` — existing `collectFormData()`, `mountPopulateForm()`, `resetMountForm()`, `mountStrategyChanged()`
- `frontend/static/css/workspace.css` — mount form styles

## Expected Output

- `backend/app/templates/browser/_vfs_settings.html` — chain builder UI, filename template input
- `frontend/static/js/workspace.js` — chain JS functions, updated collect/populate/reset
- `frontend/static/css/workspace.css` — chain builder and filename template styles

## Observability Impact

This task is pure frontend UI — no new runtime signals, structured logs, or backend state changes. Observability is through DOM inspection:

- **Chain state:** `document.querySelectorAll('#strategy-chain-container .chain-level-row')` shows current chain levels. Each row's `select.value` gives the strategy.
- **Form data shape:** Intercept the form submit (`mountSubmitForm`) and inspect the fetch body — `strategy` is a string for single, array for chains; `filename_template` is present when non-empty.
- **Add-level button visibility:** `document.getElementById('add-chain-level-btn').style.display` — `'none'` when flat or at max 3.
- **Failure shape:** No JS errors expected. If chain levels don't appear, check that `_chainLevelCount` tracks correctly — it's a module-scoped var inside the VFS IIFE.
