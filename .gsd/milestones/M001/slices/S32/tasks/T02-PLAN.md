# T02: 32-carousel-views-and-view-bug-fixes 02

**Slice:** S32 — **Milestone:** M001

## Description

Add the carousel tab bar to type-level browse views so users can switch between Table View, Cards View, and Graph View for a type without using the old broken view-type-switcher. The tab bar appears above the view body for types with multiple manifest views and persists the user's last-selected view per type IRI in localStorage.

Purpose: This is the primary feature of Phase 32 -- the carousel tab bar replaces the removed view-type-switcher (from Plan 01) as the sole view-switching affordance. It provides a cleaner, more visible navigation pattern that persists user preferences.

Output: A working carousel tab bar on all multi-view types, with localStorage persistence, instant view switching via htmx, and a loading spinner during view fetch.

## Must-Haves

- [ ] "For a type with multiple manifest views, a tab bar appears above the view body listing each view by name"
- [ ] "Clicking a carousel tab switches the view content instantly (no page reload)"
- [ ] "The active carousel tab is visually indicated with a bottom border accent"
- [ ] "Active tab selection persists per type IRI in localStorage across sessions"
- [ ] "If the saved view no longer exists in the manifest, the first view is shown silently"
- [ ] "Types with only one view spec show no carousel tab bar"
- [ ] "Tab labels use prettified display names: 'Table View', 'Cards View', 'Graph View' (per user decision)"
- [ ] "While a view fetches server data, a spinner shows in the view body area; the tab bar stays interactive"
- [ ] "The carousel tab bar is outside the htmx swap target -- switching views replaces only the view body, not the tab bar"

## Files

- `backend/app/templates/browser/carousel_tab_bar.html`
- `backend/app/templates/browser/view_toolbar.html`
- `backend/app/templates/browser/cards_view.html`
- `backend/app/templates/browser/table_view.html`
- `backend/app/templates/browser/graph_view.html`
- `frontend/static/css/views.css`
- `frontend/static/js/workspace.js`
