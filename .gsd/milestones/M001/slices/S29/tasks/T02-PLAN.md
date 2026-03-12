# T02: 29-fts-fuzzy-search 02

**Slice:** S29 — **Milestone:** M001

## Description

Add a user-controlled fuzzy toggle command to the Ctrl+K palette (ninja-keys) in `workspace.js`. The toggle persists its state in localStorage and appends `&fuzzy=true` to FTS fetch calls when enabled.

Purpose: FTS-04 requires fuzzy mode to be a user-controlled toggle in the Ctrl+K palette that persists across sessions. The backend fuzzy endpoint (Plan 01) is now live; this plan wires the UI side.

Output: Modified `workspace.js` with a `search-fuzzy-toggle` command in ninja-keys, localStorage persistence under `sempkm_fts_fuzzy`, and updated FTS fetch URL to conditionally include `&fuzzy=true`.

## Must-Haves

- [ ] "Ctrl+K palette shows a 'Search: Fuzzy Mode OFF (click to enable)' command on first open"
- [ ] "Clicking the fuzzy toggle command flips fuzzy mode on; the command title updates to 'Search: Fuzzy Mode ON (click to disable)'"
- [ ] "Fuzzy toggle state persists across browser sessions (localStorage key sempkm_fts_fuzzy)"
- [ ] "After enabling fuzzy mode, FTS queries include &fuzzy=true in the fetch URL"
- [ ] "The fuzzy toggle command is NOT removed from the palette when a search query is typed"
- [ ] "Existing E2E test assertion d.id.startsWith('fts-') for search results continues to pass (result IDs unchanged)"

## Files

- `frontend/static/js/workspace.js`
