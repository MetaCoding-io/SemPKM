---
estimated_steps: 4
estimated_files: 4
---

# T03: Admin UI — ops log page, route, and sidebar link

**Slice:** S02 — Operations Log & PROV-O Foundation
**Milestone:** M005

## Description

Create the admin-facing operations log page at `/admin/ops-log`. This is the visible surface that makes the operations log useful. Follows existing admin page patterns (`admin/models.html`, `admin/webhooks.html`) — extends `base.html`, uses `dashboard-layout` class, htmx partial rendering, `require_role("owner")`.

The page shows a reverse-chronological table of activities with filtering by activity type and cursor-based "Load more" pagination.

## Steps

1. Add `GET /admin/ops-log` route to `backend/app/admin/router.py` — accepts optional `activity_type` and `cursor` query params, calls `list_activities()`, renders `admin/ops_log.html` template with htmx partial support. Import `get_ops_log_service` from dependencies. For htmx requests with a cursor, render only the table rows block (for append-based pagination).
2. Create `backend/app/templates/admin/ops_log.html` — extends `base.html`. Contains: page heading "Operations Log", lead text, activity type filter `<select>` with htmx (`hx-get="/admin/ops-log" hx-target="#ops-log-table" hx-include="this"`), table with columns (Time, Activity, Type, Actor, Status, Duration), each row with expandable detail (related resources, error message via `<details>`), and "Load more" button that fetches next page via cursor. Duration computed as difference between `ended_at` and `started_at`. Format timestamps as relative ("2 minutes ago") with title showing full ISO.
3. Add "Operations Log" card to `backend/app/templates/admin/index.html` — third card in the `dashboard-cards` grid, linking to `/admin/ops-log` with htmx navigation.
4. Add "Operations Log" nav link to `backend/app/templates/components/_sidebar.html` — in the Admin group after the Webhooks link, using `activity` Lucide icon, with same htmx navigation pattern.

## Must-Haves

- [ ] `/admin/ops-log` route renders correctly for both full-page and htmx partial requests
- [ ] Activity type filter narrows displayed entries
- [ ] Cursor-based pagination with "Load more" button
- [ ] Table shows Time, Activity, Type, Actor, Status, Duration columns
- [ ] Failed activities show error details in expandable row
- [ ] Sidebar link appears under Admin group with `activity` icon
- [ ] Admin index page has Operations Log card
- [ ] Owner role required

## Verification

- Docker stack running → navigate to `/admin/ops-log` → page renders with table headers
- Sidebar shows "Operations Log" link with activity icon
- Admin index page shows "Operations Log" card
- If ops log entries exist (from T02 instrumentation), they appear in the table
- Filter dropdown changes displayed results

## Inputs

- `backend/app/services/ops_log.py` — `list_activities()` returns `(list[dict], next_cursor)`
- `backend/app/admin/router.py` — existing admin route patterns (`admin_index`, `admin_models`)
- `backend/app/templates/admin/index.html` — dashboard card layout to extend
- `backend/app/templates/admin/models.html` — reference for htmx partial rendering pattern
- `backend/app/templates/components/_sidebar.html` — Admin group nav links

## Expected Output

- `backend/app/admin/router.py` — new `admin_ops_log()` route
- `backend/app/templates/admin/ops_log.html` — complete ops log page template
- `backend/app/templates/admin/index.html` — Operations Log card added
- `backend/app/templates/components/_sidebar.html` — Operations Log nav link added

## Observability Impact

- **New inspection surface:** `/admin/ops-log` page renders all prov:Activity instances from `urn:sempkm:ops-log` named graph — visible to any owner user via browser
- **Failure visibility:** Failed activities display with red status badge and expandable `<details>` showing the error message (sourced from `sempkm:errorMessage` predicate)
- **Filter diagnostics:** Activity type filter (`?activity_type=model.install` etc.) enables narrowing to specific operation categories for debugging
- **No new log signals:** This task adds only UI rendering — all underlying log/SPARQL signals were added in T01/T02
