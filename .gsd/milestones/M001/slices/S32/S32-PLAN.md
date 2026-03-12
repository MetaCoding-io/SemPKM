# S32: Carousel Views And View Bug Fixes

**Goal:** Fix all broken htmx targets in view templates (dockview migration broke `#editor-area` references), redesign cards group-by as collapsible accordion sections, and remove the old broken view-type-switcher buttons from the view toolbar.
**Demo:** Fix all broken htmx targets in view templates (dockview migration broke `#editor-area` references), redesign cards group-by as collapsible accordion sections, and remove the old broken view-type-switcher buttons from the view toolbar.

## Must-Haves


## Tasks

- [x] **T01: 32-carousel-views-and-view-bug-fixes 01** `est:3min`
  - Fix all broken htmx targets in view templates (dockview migration broke `#editor-area` references), redesign cards group-by as collapsible accordion sections, and remove the old broken view-type-switcher buttons from the view toolbar.

Purpose: The dockview migration (Phase 30) replaced the single `#editor-area` div with per-panel `.group-editor-area` containers, silently breaking all htmx swaps in view templates (filtering, sorting, pagination, group-by). This plan fixes the root cause and cleans up the broken view switch buttons that the carousel tab bar will replace in Plan 02.

Output: Working view templates with correct htmx targets, accordion-style card groups, and the old view-type-switcher removed.
- [x] **T02: 32-carousel-views-and-view-bug-fixes 02** `est:3min`
  - Add the carousel tab bar to type-level browse views so users can switch between Table View, Cards View, and Graph View for a type without using the old broken view-type-switcher. The tab bar appears above the view body for types with multiple manifest views and persists the user's last-selected view per type IRI in localStorage.

Purpose: This is the primary feature of Phase 32 -- the carousel tab bar replaces the removed view-type-switcher (from Plan 01) as the sole view-switching affordance. It provides a cleaner, more visible navigation pattern that persists user preferences.

Output: A working carousel tab bar on all multi-view types, with localStorage persistence, instant view switching via htmx, and a loading spinner during view fetch.

## Files Likely Touched

- `backend/app/templates/browser/view_toolbar.html`
- `backend/app/templates/browser/cards_view.html`
- `backend/app/templates/browser/table_view.html`
- `backend/app/templates/browser/pagination.html`
- `backend/app/templates/browser/search_suggestions.html`
- `backend/app/views/service.py`
- `frontend/static/css/views.css`
- `backend/app/templates/browser/carousel_tab_bar.html`
- `backend/app/templates/browser/view_toolbar.html`
- `backend/app/templates/browser/cards_view.html`
- `backend/app/templates/browser/table_view.html`
- `backend/app/templates/browser/graph_view.html`
- `frontend/static/css/views.css`
- `frontend/static/js/workspace.js`
