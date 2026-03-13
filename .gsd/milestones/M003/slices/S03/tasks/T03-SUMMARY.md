---
id: T03
parent: S03
milestone: M003
provides:
  - initExplorerMountOptions() function for dynamic mount option injection into explorer dropdown
  - Mount mode persistence and restore after async mount fetch
  - Graceful fallback when stored mount is deleted or fetch fails
key_files:
  - frontend/static/js/workspace.js
key_decisions:
  - Idempotent optgroup injection — removes existing "VFS Mounts" optgroup before re-adding, safe for future re-invocations
  - Re-check localStorage after mount injection rather than modifying initExplorerMode() — preserves clean separation between built-in mode restore and mount-specific restore
patterns_established:
  - Async post-init enrichment pattern — initExplorerMode() runs synchronously with built-in options, then initExplorerMountOptions() fetches and injects mount options asynchronously without blocking other init work
observability_surfaces:
  - console.warn on fetch failure with error message
  - document.querySelectorAll('#explorer-mode-select option[value^="mount:"]') inspects injected options
  - localStorage.getItem('sempkm_explorer_mode') shows stored mode
duration: 20min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Frontend dynamic mount dropdown injection and mode persistence

**Added initExplorerMountOptions() that fetches VFS mounts on page load, injects them as optgroup options in the explorer dropdown, and restores stored mount modes after async injection.**

## What Happened

Added a single function `initExplorerMountOptions()` to workspace.js, called from `init()` right after `initExplorerMode()`. The function:

1. Fetches `GET /api/vfs/mounts` with credentials
2. If mounts exist, creates an `<optgroup label="VFS Mounts">` with `<option value="mount:{id}">` entries showing `{name} ({strategy})`
3. Appends the optgroup to `#explorer-mode-select`
4. Re-checks localStorage for a stored `mount:` mode that `initExplorerMode()` couldn't restore (mount options weren't in the DOM during initial restore), validates the option exists, and triggers the htmx change event to load the mount tree

Error handling: fetch failure logs a console.warn and silently degrades (dropdown works with built-in modes only). Empty mount list skips injection entirely. Deleted mount in localStorage stays invalid — the user sees the fallback mode (by-type) set by `initExplorerMode()`.

## Verification

- **Mount options appear after page load**: Created 2 mounts via API, reloaded workspace → both appeared in dropdown under "VFS Mounts" optgroup with correct `mount:{id}` values and `{name} ({strategy})` labels
- **Mount mode selection loads tree**: Selected "All Objects (flat)" → flat object list loaded in explorer tree
- **Mode persistence**: Selected mount mode, reloaded → stored `mount:` mode restored, tree reloaded automatically
- **Deleted mount fallback**: Deleted the selected mount via API, reloaded → fell back to "By Type" with standard tree (stale localStorage value harmlessly ignored)
- **Existing modes unaffected**: Verified By Type, Hierarchy, and By Tag all switch correctly with mount options present
- **No console errors**: Clean console on workspace load and mode switching (only pre-existing 500 from views/explorer endpoint, unrelated)
- **Backend tests**: `pytest tests/test_mount_explorer.py -v` — 17/17 passed
- **Network verification**: `GET /api/vfs/mounts → 200` confirmed in browser network logs on every workspace load
- **Manual curl**: `curl .../explorer/tree?mode=mount:{uuid}` → 200 with HTML tree content

### Slice-level checks status (T03 is intermediate, not final):
- ✅ `pytest tests/test_mount_explorer.py -v` — 17 passed
- ⬜ `e2e/tests/20-vfs-explorer/` — directory not yet created (expected for later task)
- ✅ Manual curl `/browser/explorer/tree?mode=mount:{uuid}` → 200
- ✅ Manual curl `/browser/explorer/mount-children?mount_id={uuid}&folder={value}` — endpoint available (tested in T01)

## Diagnostics

- Injected mount options: `document.querySelectorAll('#explorer-mode-select option[value^="mount:"]')` in browser console
- Stored mode: `localStorage.getItem('sempkm_explorer_mode')` — shows current persisted mode
- Fetch failure: `console.warn('SemPKM: could not load VFS mounts...')` logged with error message on network/auth failure
- Optgroup presence: `document.querySelector('#explorer-mode-select optgroup[label="VFS Mounts"]')` — null when no mounts exist

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js` — Added `initExplorerMountOptions()` function and wired it into `init()` after `initExplorerMode()`
