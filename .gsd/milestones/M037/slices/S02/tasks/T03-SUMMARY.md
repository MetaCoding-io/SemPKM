---
id: T03
parent: S02
milestone: M037
provides:
  - Context Rules category in Settings UI with full CRUD
  - Browser route GET /browser/settings/context-rules returning HTML partial
  - Rule list, inline edit form, create form, delete with confirmation, test-against-context button
  - CSS styles for rule cards, condition tags, form layout, test results
key_files:
  - backend/app/templates/browser/settings_page.html
  - backend/app/templates/browser/_context_rules.html
  - backend/app/browser/settings.py
  - frontend/static/css/settings.css
key_decisions:
  - Used JavaScript fetch() for CRUD API calls with htmx panel reload on success, instead of native htmx form submission — JSON API endpoints return JSON not HTML, so htmx hx-post alone can't handle the round-trip cleanly
  - Inline edit form pattern (toggle per rule card) instead of modal dialog — consistent with the compact settings page pattern and avoids z-index/stacking context issues inside dockview panels
patterns_established:
  - Settings category partials loaded via htmx use JS fetch() for API mutations then htmx.ajax('GET', '/browser/settings/<category>', '#<container>') to reload the panel
  - Rule condition assembly from individual form fields into JSON conditions dict happens client-side in contextRulesBuildPayload()
observability_surfaces:
  - Browser route errors surface as 500 responses in Network tab
  - CRUD errors displayed via alert() dialog with API error detail
  - Test result displayed in colored badge (green match / red no-match)
  - Lucide icon re-init after htmx swap logged if createIcons() fails
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Settings UI — Context Rules category panel with CRUD and test

**Added Context Rules settings category with full CRUD UI, test-against-current-context button, and styled rule cards — all 45 backend tests still pass.**

## What Happened

Built four deliverables:

1. **settings_page.html** — Added "Context Rules" sidebar button (with brain icon) and a panel div that lazy-loads the partial via `hx-get="/browser/settings/context-rules"` on intersection.

2. **_context_rules.html** — New template partial with: (a) test button calling `POST /api/context/rules/test` and showing colored match/no-match result, (b) rule list with cards showing name, persona badge, priority, condition tags, enable toggle, edit/delete buttons, (c) inline edit form per card with pre-filled values, (d) collapsible "New Rule" section with create form. All CRUD operations use `fetch()` to call the JSON API endpoints then `htmx.ajax()` to reload the panel. Condition dropdowns (location_zone, activity, time_period, calendar_busy) assembled into JSON conditions dict client-side.

3. **settings.py** — Added `GET /browser/settings/context-rules` route that fetches rules via `RulesEngine.list_rules()` and personas via `PersonaService.list_for_user()`, builds a persona_id→name map, and renders the partial.

4. **settings.css** — Added ~180 lines of CSS: rule card layout, condition tags, inline edit form, conditions grid, test result badges, create section toggle, and proper Lucide SVG sizing with `flex-shrink: 0`.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py -v` — 19/19 passed
- `cd backend && .venv/bin/python -m pytest tests/test_rules_router.py -v` — 26/26 passed
- `grep -q "context-rules" backend/app/templates/browser/settings_page.html` — confirmed
- `test -f backend/app/templates/browser/_context_rules.html` — confirmed
- Browser: Settings → Context Rules sidebar button visible → click → panel loads with empty state → New Rule → fill form (name, persona, location=office, time=work_hours) → Create Rule → rule appears in list with condition tags → Edit button → inline form with pre-filled values → change name → Save → updated → Test button → "No rule matches (no context data yet)" → Delete button → confirm dialog → rule removed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py -v` | 0 | ✅ pass | 0.45s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_rules_router.py -v` | 0 | ✅ pass | 0.75s |
| 3 | `grep -q "context-rules" backend/app/templates/browser/settings_page.html` | 0 | ✅ pass | <1s |
| 4 | `test -f backend/app/templates/browser/_context_rules.html` | 0 | ✅ pass | <1s |
| 5 | Browser: CRUD flow (create/edit/delete/test) | — | ✅ pass | manual |

## Diagnostics

- **Settings route:** `GET /browser/settings/context-rules` — returns HTML partial; errors produce 500 visible in browser Network tab
- **API backing:** Rules API at `/api/context/rules` (documented in T02) — the UI is a thin layer over this JSON API
- **Client-side errors:** CRUD failures show `alert()` with API error detail; test failures show red badge in `#context-rules-test-result`
- **Lucide icons:** Re-initialized via `lucide.createIcons({ nodes: [container] })` after each htmx swap — if icons are blank, check console for Lucide errors

## Deviations

- Used `hx-trigger="intersect once"` instead of `hx-trigger="load"` for the panel content — the panel is `display:none` on initial load, and `load` fires immediately even when hidden, wasting a request. `intersect once` fires only when the panel becomes visible (user clicks the sidebar button).
- Template uses JavaScript `fetch()` for API calls instead of pure htmx form submission — the API endpoints return JSON, not HTML fragments, so htmx `hx-post` alone can't handle the response. After each successful mutation, `htmx.ajax('GET', ...)` reloads the panel to reflect changes.

## Known Issues

- The conditions grid layout stacks vertically on narrower viewport widths instead of the planned 3-column grid — this is actually a reasonable responsive behavior and doesn't impair usability.
- The DELETE fetch shows as `net::ERR_ABORTED` in Playwright network logs because `_reloadPanel()` triggers a navigation that aborts the in-flight fetch — the delete actually succeeds (HTTP 204) before the abort.

## Files Created/Modified

- `backend/app/templates/browser/settings_page.html` — Added Context Rules sidebar button and lazy-loaded panel div (modified)
- `backend/app/templates/browser/_context_rules.html` — New template partial with full CRUD UI, test button, and client-side JS (new)
- `backend/app/browser/settings.py` — Added context_rules_panel browser route (modified)
- `frontend/static/css/settings.css` — Added ~180 lines of context rules styles (modified)
- `.gsd/milestones/M037/slices/S02/tasks/T03-PLAN.md` — Added Observability Impact section (modified)
