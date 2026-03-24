---
id: T03
parent: S02
milestone: M038
provides:
  - 8 new htmx fragment routes (today, rules CRUD, plan generate, current-suggestion)
  - Tab navigation UI (Today / Episodes / Rules) replacing single-view layout
  - today.html agenda view with time slots, status badges, now-playing indicator
  - rules.html + rules-list.html rule management with toggle/delete
  - rule-form.html inline form with condition dropdowns, action radios, time range
  - Extended CSS with tab bar, plan entry cards, rule cards, status badge variants
key_files:
  - apps/media-scheduler/app.py
  - apps/media-scheduler/frontend/templates/main.html
  - apps/media-scheduler/frontend/templates/today.html
  - apps/media-scheduler/frontend/templates/rules.html
  - apps/media-scheduler/frontend/templates/rules-list.html
  - apps/media-scheduler/frontend/templates/rule-form.html
  - apps/media-scheduler/frontend/static/styles.css
key_decisions:
  - Split rules-list.html from rules.html to enable htmx innerHTML swap on #ms-rules-list without nesting the wrapper
  - Tab switching uses htmx.ajax() from inline JS rather than hx-trigger="click" to keep active-state logic colocated
  - Today SPARQL filters on plan title containing date string rather than querying by plan IRI, avoiding need to mint IRI client-side
  - current-suggestion route returns minimal HTML for future S05 mobile widget use
patterns_established:
  - rules.html uses Jinja2 {% include "rules-list.html" %} to compose the full view, while CRUD routes return the inner partial for htmx swap
  - msSelectTab() JS function manages tab active state + htmx.ajax fragment loading
  - Plan entry now-playing detection uses server-side time comparison (no client JS)
observability_surfaces:
  - Routes log warnings on SPARQL failures and rule service errors via logger.warning
  - Plan generate route logs rules_matched and entries_created on success
  - All error states render as <div class="ms-error"> HTML fragments visible in the UI
  - Rule CRUD mutations logged by rules_service (add/toggle/delete)
duration: 18m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: UI routes + templates + CSS

**Added 8 htmx routes, tab navigation (Today/Episodes/Rules), agenda-style today view, rules management UI with inline form, and extended CSS for all new components.**

## What Happened

Reworked `main.html` from a single episodes view to a 3-tab interface: Today (default, calendar icon), Episodes (list-music icon), and Rules (sliders-horizontal icon). Tab clicks invoke `htmx.ajax()` to load fragments into `#ms-tab-content`. The Today tab loads on page init via `hx-trigger="load"`.

Created `today.html` with an agenda-style plan view: header with date and "Generate Plan" button, plan entry cards showing time slot gutter (start–end), item title (linked to enclosure if available), source name, duration badge, and status badge with color coding (pending/active/completed/skipped/replaced). Server-side now-playing detection highlights the entry whose time slot contains the current time. Empty state shows a prompt to generate a plan.

Created `rules.html` using `{% include "rules-list.html" %}` to compose the full view. The inner `rules-list.html` partial renders rule cards with name, priority badge, conditions summary, action summary, toggle button, and delete button (with confirm dialog). This split enables CRUD routes to return just the inner partial for `#ms-rules-list` innerHTML swap without DOM nesting issues.

Created `rule-form.html` with condition dropdowns (Activity, Location Zone, Time Period), optional time range checkbox with start/end time inputs, action type radio group (source_type/source_iri/category) with context-dependent value inputs, name field, priority number input, and Save/Cancel buttons. The form posts to the rules save route targeting the rules list.

Added 8 routes to `app.py`: `GET /_fragments/today` (SPARQL query for plan entries by date), `GET /_fragments/rules` (load rules from StateClient), `GET /_fragments/rules/add` (empty form), `POST /_fragments/rules` (save rule from form data), `POST /_fragments/rules/{id}/toggle`, `POST /_fragments/rules/{id}/delete`, `POST /_fragments/plan/generate` (triggers plan generation then re-renders today view), `GET /_fragments/current-suggestion` (minimal HTML for mobile widget).

Extended `styles.css` with tab bar (`.ms-tabs`, `.ms-tab`, `.ms-tab-active`), plan entry cards (`.ms-plan-entry`, `.ms-time-slot`, `.ms-now-playing`), status badges (`.ms-status-badge` with 5 color variants), rule cards (`.ms-rule-card`, `.ms-priority-badge`), rule form styling (`.ms-rule-form`, fieldsets, radio groups, time range fields), and suggestion widget. All SVG icons in flex containers have `flex-shrink: 0`.

## Verification

- All 164 existing tests pass — no regressions
- htmx URL prefix audit: all URLs in all templates use `/app/media-scheduler/` prefix
- All 4 template files exist (today.html, rules.html, rules-list.html, rule-form.html)
- CSS contains 9 occurrences of `ms-tab` (≥3 threshold)
- 14 route decorators in app.py (≥13 threshold: 6 original + 8 new)
- Python AST parse passes for app.py

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'hx-get="\|hx-post="' apps/media-scheduler/frontend/templates/ \| grep -v '/app/media-scheduler/'` | 1 (no matches) | ✅ pass | <1s |
| 2 | `test -f today.html && test -f rules.html && test -f rule-form.html && echo "OK"` | 0 | ✅ pass | <1s |
| 3 | `grep -c "ms-tab" apps/media-scheduler/frontend/static/styles.css` → 9 | 0 | ✅ pass | <1s |
| 4 | `grep -c "@media_scheduler_app.route" apps/media-scheduler/app.py` → 14 | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py --tb=short -q` → 164 passed | 0 | ✅ pass | 0.41s |
| 6 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` | 0 | ✅ pass | <1s |
| 7 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "invalid or error or empty"` → 31 passed | 0 | ✅ pass | 0.28s |

## Diagnostics

- **Route inspection:** `grep "@media_scheduler_app.route" apps/media-scheduler/app.py` lists all 14 registered routes.
- **Today SPARQL:** `TODAY_PLAN_SPARQL` constant in app.py — queries PlanEntry objects for a given date, joined with MediaItem data, filtered to exclude "replaced" status, ordered by slotOrder.
- **Rule form parsing:** The `rules_save_fragment` route parses form data into conditions dict + action dict, delegates to `add_rule()` from rules_service. Validation errors return `<div class="ms-error">` fragments.
- **Template rendering errors:** Surface as 500s in the app proxy log. All templates use safe Jinja2 patterns (conditional access with `if rule and rule.conditions`).
- **htmx URL audit:** `rg 'hx-get="|hx-post="' apps/media-scheduler/frontend/templates/` shows all htmx endpoints.

## Deviations

- Created `rules-list.html` as a separate partial (not in the original plan) to solve htmx innerHTML swap nesting — POST/toggle/delete routes return the inner partial while GET returns the full `rules.html` that includes it via `{% include %}`.
- The plan specified "rule update" route (`POST /_fragments/rules/{id}`) but I used the existing `add_rule` with optional `rule_id` form field for edit-save simplicity. A dedicated update route can be added if needed.

## Known Issues

None.

## Files Created/Modified

- `apps/media-scheduler/app.py` — MODIFIED: Added 8 new routes, rules_service imports, plan_service type constant imports, date import
- `apps/media-scheduler/frontend/templates/main.html` — MODIFIED: Replaced single-view with 3-tab interface (Today/Episodes/Rules)
- `apps/media-scheduler/frontend/templates/today.html` — NEW: Agenda-style daily plan view with time slots, status badges, empty state
- `apps/media-scheduler/frontend/templates/rules.html` — NEW: Rules view wrapper with header and includes rules-list.html
- `apps/media-scheduler/frontend/templates/rules-list.html` — NEW: Rules list partial for htmx swap (rule cards with toggle/delete)
- `apps/media-scheduler/frontend/templates/rule-form.html` — NEW: Inline rule creation form with conditions, actions, priority
- `apps/media-scheduler/frontend/static/styles.css` — MODIFIED: Added tab nav, plan entries, rule cards, status badges, form, suggestion widget styles
- `.gsd/milestones/M038/slices/S02/tasks/T03-PLAN.md` — MODIFIED: Added Observability Impact section
