---
depends_on: [M051]
---

# M055: Browser History & Tab Recovery

**Gathered:** 2026-04-05
**Status:** Ready for planning

## Project Description

Research and implement browser history integration for the dockview workspace. The URL never changes while browsing — users can't bookmark, share, or use back/forward to navigate. Closing a tab is irreversible with no undo mechanism.

## Why This Milestone

This is a fundamental usability gap. Every other web app changes the URL as you navigate. Users expect to bookmark a view of their data, share a link, or press back to return to what they were looking at. The current workspace is a black hole from the browser's perspective — one URL for everything.

## User-Visible Outcome

### When this milestone is complete, the user can:

- See the URL update as they switch between object tabs (e.g. `/browser/?tab=urn:sempkm:...`)
- Bookmark a specific object view and return to it later
- Share a URL that opens a specific object or view
- Press back/forward to navigate between recently-viewed objects
- Press Ctrl+Shift+T or use "Reopen Closed Tab" in command palette to recover a closed tab

### Entry point / environment

- Entry point: http://localhost:4000/browser/
- Environment: Browser
- Live dependencies involved: none

## Completion Class

- Contract complete means: URL reflects active tab, back/forward navigates tab history, closed tab stack works
- Integration complete means: bookmarked URLs open the correct object/view
- Operational complete means: none

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Open object A → URL shows A's IRI → open object B → URL shows B's IRI → press back → A is focused → URL shows A
- Copy URL while viewing object A → open in new browser tab → object A opens
- Close a tab → Ctrl+Shift+T → tab reopens with same content
- F1 → "Reopen Closed Tab" → last closed tab reopens

## Risks and Unknowns

- **Multi-tab state** — the workspace can have N tabs open but the URL can only represent one thing. Need to decide: does the URL represent the focused tab only, or the full workspace state?
- **dockview serialization** — dockview has toJSON()/fromJSON() for full layout serialization, but encoding that in a URL query param would be huge
- **History API vs hash routing** — pushState gives clean URLs but requires server-side fallback. Hash routing is simpler but uglier.
- **Shared URL behavior** — should opening a shared URL add a tab to the existing workspace, or replace the workspace? Probably add-to-existing.

## Existing Codebase / Prior Art

- `frontend/static/js/workspace-layout.js` — dockview panel management with toJSON()/fromJSON()
- `frontend/static/js/named-layouts.js` — named layout save/restore in localStorage
- VS Code web, Figma, Linear — all handle URL ↔ workspace state differently. Research needed.

## Scope

### In Scope

- Research: how do IDE-in-browser apps handle URL ↔ workspace state?
- URL reflects active tab's object/view IRI
- Browser back/forward navigates tab focus history
- "Reopen Closed Tab" command (maintain closed-tab stack)
- Ctrl+Shift+T keyboard shortcut for undo close tab
- Bookmarkable URLs that restore the focused tab

### Out of Scope / Non-Goals

- Full workspace state in URL (all open tabs, panel positions)
- Real-time collaboration via shared URLs
- Deep linking into specific views or dashboard states

## Open Questions

- Should this be research-first (one slice of investigation) then implementation, or go straight to implementation?
- What's the URL format? `/browser/?tab=<encoded-iri>` or `/browser/object/<encoded-iri>`?
