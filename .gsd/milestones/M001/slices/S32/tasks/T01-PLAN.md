# T01: 32-carousel-views-and-view-bug-fixes 01

**Slice:** S32 — **Milestone:** M001

## Description

Fix all broken htmx targets in view templates (dockview migration broke `#editor-area` references), redesign cards group-by as collapsible accordion sections, and remove the old broken view-type-switcher buttons from the view toolbar.

Purpose: The dockview migration (Phase 30) replaced the single `#editor-area` div with per-panel `.group-editor-area` containers, silently breaking all htmx swaps in view templates (filtering, sorting, pagination, group-by). This plan fixes the root cause and cleans up the broken view switch buttons that the carousel tab bar will replace in Plan 02.

Output: Working view templates with correct htmx targets, accordion-style card groups, and the old view-type-switcher removed.

## Must-Haves

- [ ] "Cards group-by select changes the displayed grouping without page reload (htmx swap works inside dockview panel)"
- [ ] "Table sort headers update the table without page reload (htmx swap works inside dockview panel)"
- [ ] "Pagination prev/next/page-number links work inside dockview panels"
- [ ] "Cards groups render as collapsible accordion sections with count in header"
- [ ] "Objects missing the group-by value appear in an 'Ungrouped' section at the bottom"
- [ ] "All groups are expanded by default"
- [ ] "The old view-type-switcher buttons (.view-type-btn icons) are completely gone from the view toolbar"

## Files

- `backend/app/templates/browser/view_toolbar.html`
- `backend/app/templates/browser/cards_view.html`
- `backend/app/templates/browser/table_view.html`
- `backend/app/templates/browser/pagination.html`
- `backend/app/templates/browser/search_suggestions.html`
- `backend/app/views/service.py`
- `frontend/static/css/views.css`
