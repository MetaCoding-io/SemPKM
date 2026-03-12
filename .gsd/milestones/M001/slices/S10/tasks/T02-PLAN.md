# T02: 10-bug-fixes-and-cleanup-architecture 02

**Slice:** S10 — **Milestone:** M001

## Description

Fix the autocomplete dropdown clipping and views explorer lazy-load bugs.

Purpose: Reference property autocomplete dropdowns are clipped by `overflow-y: auto` on `.object-form-section`, making suggestions invisible or partially hidden. The views explorer section shows "Loading..." forever because `hx-trigger="click once"` only fires when the user clicks the section header. This plan fixes both issues.

Output: Fully visible autocomplete dropdowns and eagerly loaded views explorer tree.

## Must-Haves

- [ ] "Autocomplete dropdown for reference properties renders fully visible on top of all content"
- [ ] "Clicking an autocomplete suggestion populates both the search input and the hidden IRI field"
- [ ] "Views explorer section loads its tree content on workspace initialization without requiring a user click"

## Files

- `frontend/static/css/forms.css`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/forms/_field.html`
