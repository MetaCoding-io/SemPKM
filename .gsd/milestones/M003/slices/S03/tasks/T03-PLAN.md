---
estimated_steps: 4
estimated_files: 2
---

# T03: Frontend dynamic mount dropdown injection and mode persistence

**Slice:** S03 — VFS-Driven Explorer Modes
**Milestone:** M003

## Description

Add client-side JavaScript that fetches the user's VFS mounts on page load and dynamically injects them as `<option>` entries in the explorer mode dropdown. Handle mount mode persistence: if the user's stored mode is `mount:xxx` and the mount still exists, restore it; if the mount was deleted, fall back to by-type. This is the bridge that makes mount modes visible and selectable in the UI.

## Steps

1. **Add `initExplorerMountOptions()` async function in workspace.js.** After `initExplorerMode()` runs (which sets up the change listener and restores the default mode), call this function. It fetches `GET /api/vfs/mounts` (using the existing fetch with credentials), and for each mount in the response, creates an `<option value="mount:{id}">{name} ({strategy})</option>` element. If mounts exist, wrap them in an `<optgroup label="VFS Mounts">` for visual separation from built-in modes, then append to `#explorer-mode-select`.

2. **Re-run mode restore after mount injection.** After injecting mount options, check `localStorage.getItem('sempkm_explorer_mode')`. If it starts with `mount:`, validate the option exists in the now-populated dropdown, set `dropdown.value`, and trigger `htmx.trigger(dropdown, 'change')` to load the mount tree. This handles the timing issue: `initExplorerMode()` ran before mounts were in the DOM, so a stored `mount:xxx` mode was skipped as invalid. The re-check after injection fixes this.

3. **Handle error cases gracefully.** If the fetch fails (network error, 401), skip injection — the dropdown works with just built-in modes. If the response is empty (no mounts), skip injection. If a stored mount mode's mount was deleted (option not found after injection), the stored mode remains invalid and the user stays on the fallback mode set by `initExplorerMode()` (by-type).

4. **Wire into init flow.** Call `initExplorerMountOptions()` from `init()` after `initExplorerMode()`. Since it's async (uses `fetch`), it doesn't block other init work. The dropdown is functional immediately with built-in modes; mount options appear shortly after as the fetch completes.

## Must-Haves

- [ ] Mount options appear in dropdown after page load (fetched from `/api/vfs/mounts`)
- [ ] Options use `mount:{id}` value format matching backend parser
- [ ] VFS mount options visually grouped (optgroup) separate from built-in modes
- [ ] Stored `mount:xxx` mode restores correctly after mount options are injected
- [ ] Deleted mount in localStorage falls back to by-type gracefully
- [ ] Fetch failure does not break the dropdown or other init functions
- [ ] Existing mode switching (by-type, hierarchy, by-tag) unaffected

## Verification

- Browser: create a mount via Settings, reload workspace → mount appears in explorer dropdown
- Browser: select mount mode → mount tree loads; reload → mount mode restores
- Browser: delete mount via Settings, reload → falls back to by-type
- Browser: existing modes (by-type, hierarchy, by-tag) still switch correctly
- Browser console: no errors during init or mount fetch

## Observability Impact

- Signals added/changed: None (client-side only; fetch errors logged to console)
- How a future agent inspects this: `document.querySelectorAll('#explorer-mode-select option[value^="mount:"]')` shows injected mount options; `localStorage.getItem('sempkm_explorer_mode')` shows stored mode
- Failure state exposed: Fetch failure silently degrades (no mount options); console.warn if fetch fails

## Inputs

- `frontend/static/js/workspace.js` — `initExplorerMode()`, `init()`, `EXPLORER_MODE_KEY` from S01
- `GET /api/vfs/mounts` — REST endpoint returning JSON array of mount dicts with `id`, `name`, `strategy`
- T01 backend — `mount:` prefix parsing in `explorer_tree` must be deployed

## Expected Output

- `frontend/static/js/workspace.js` — `initExplorerMountOptions()` function added, called from `init()`
