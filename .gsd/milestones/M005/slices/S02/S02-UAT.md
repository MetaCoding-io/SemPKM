# S02: Operations Log & PROV-O Foundation — UAT

**Milestone:** M005
**Written:** 2026-03-14

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: Ops log requires triplestore writes and reads via SPARQL — must verify against running Docker stack. Admin UI rendering and htmx interactions require browser verification.

## Preconditions

- Docker stack running (`docker compose up -d` from project root)
- At least one user with `owner` role exists and is logged in
- A mental model is available for install (e.g. `basic-pkm`)

## Smoke Test

Navigate to `/admin/ops-log` — page renders with heading "Operations Log", a filter dropdown, and a table with column headers (Time, Activity, Type, Actor, Status, Duration). If no activities have been logged yet, the table body shows "No operations logged yet."

## Test Cases

### 1. Page renders with correct layout

1. Log in as owner
2. Navigate to `/admin/ops-log`
3. **Expected:** Page shows "Operations Log" heading, lead text describing the log, an "Activity Type" filter dropdown defaulting to "All Types", and a table with 6 columns: Time, Activity, Type, Actor, Status, Duration

### 2. Sidebar navigation link exists and works

1. From any admin page, look at the sidebar under the Admin group
2. Find "Operations Log" link with an activity icon
3. Click it
4. **Expected:** Page navigates to `/admin/ops-log` via htmx (no full page reload), sidebar link shows active state

### 3. Admin index card exists and links correctly

1. Navigate to `/admin` (admin dashboard)
2. Look for "Operations Log" card in the dashboard grid
3. Click the "View Operations Log" button on the card
4. **Expected:** Navigates to `/admin/ops-log`

### 4. Model install generates ops log entry

1. Navigate to `/admin/models`
2. Install a mental model (e.g. `basic-pkm` or any available model)
3. After successful install, navigate to `/admin/ops-log`
4. **Expected:** Top entry shows activity type "Model Install", status badge showing "success" (green), actor showing current user identifier, and a recent timestamp. Duration column shows how long the install took (e.g. "2.3s").

### 5. Model remove generates ops log entry

1. Navigate to `/admin/models`
2. Remove the previously installed model
3. Navigate to `/admin/ops-log`
4. **Expected:** Top entry shows activity type "Model Remove", status "success", actor is current user

### 6. Inference run generates ops log entry

1. Ensure a model is installed with inference rules
2. Navigate to inference and trigger a run
3. Navigate to `/admin/ops-log`
4. **Expected:** Entry with type "Inference Run", status "success", label summarizing inferred/new counts (e.g. "Inferred 42 triples (12 new)")

### 7. Activity type filter narrows results

1. Navigate to `/admin/ops-log` with multiple activity types present
2. Select "Model Install" from the filter dropdown
3. **Expected:** Only model install entries shown; other types hidden. No content duplication (heading/filter should not repeat). Table updates via htmx without full page reload.
4. Select "All Types" again
5. **Expected:** All entries shown again

### 8. Error details expand for failed activities

1. Trigger a failing operation (or seed a failed entry via SPARQL console)
2. Navigate to `/admin/ops-log`
3. Find the failed entry (red "failed" status badge)
4. Click the expandable ▸ summary on the entry
5. **Expected:** Error message displays in red monospace text inside a `<details>` element

### 9. Owner role required

1. Log in as a non-owner user (member or guest)
2. Navigate to `/admin/ops-log`
3. **Expected:** "Access Denied" page shown, not the ops log

### 10. SPARQL console shows raw ops log data

1. Open the SPARQL console
2. Execute: `SELECT * WHERE { GRAPH <urn:sempkm:ops-log> { ?s ?p ?o } } LIMIT 50`
3. **Expected:** Results show triples with PROV-O predicates: `prov:startedAtTime`, `prov:endedAtTime`, `prov:wasAssociatedWith`, `sempkm:activityType`, `rdfs:label`. Resource IRIs follow pattern `urn:sempkm:ops-log:{uuid}`.

## Edge Cases

### Empty log state

1. On a fresh instance with no operations performed (or after clearing the graph)
2. Navigate to `/admin/ops-log`
3. **Expected:** Table shows "No operations logged yet." message, no errors, filter dropdown still functional

### Filter with no matching results

1. Navigate to `/admin/ops-log`
2. Select an activity type that has no entries (e.g. "Validation Run" if none have run)
3. **Expected:** Empty table with appropriate message, no JS errors

### Rapid successive operations

1. Install then immediately remove a model
2. Navigate to `/admin/ops-log`
3. **Expected:** Both entries appear in correct reverse-chronological order with distinct timestamps

## Failure Signals

- `/admin/ops-log` returns 500 or shows error page — route/template broken
- Operations (model install, inference) fail or slow down after ops log wiring — fire-and-forget wrapper broken
- Filter dropdown causes duplicate heading/controls — htmx target-aware rendering broken
- No entries appear after performing logged operations — instrumentation not wired or triplestore write failing
- "Access Denied" when logged in as owner — role check misconfigured
- SPARQL console shows no triples in `urn:sempkm:ops-log` graph — service not writing to correct graph

## Requirements Proved By This UAT

- LOG-01 — Operations log in admin/debug shows timestamped, structured entries for system activities (model install, inference, validation)
- LOG-01 (PROV-O) — Operations log entries use PROV-O vocabulary (prov:Activity, prov:wasAssociatedWith, prov:startedAtTime) — verified via SPARQL console test case

## Not Proven By This UAT

- Pagination under load (cursor-based pagination with many entries) — unit tests cover logic, but UAT doesn't generate enough entries to exercise cursor pagination
- Validation run logging — requires triggering validation queue worker which runs asynchronously; may not be easily triggered in manual UAT
- E2E Playwright automation — deferred to S09

## Notes for Tester

- The ops log is fire-and-forget — if triplestore writes fail, the primary operation still succeeds. Watch the Python logs for WARNING messages indicating failed ops log writes.
- Duration values are computed server-side from `prov:startedAtTime` and `prov:endedAtTime`. They may show "—" if the activity type doesn't record an end time.
- Actor display is shortened: `urn:sempkm:user:{id}` → `user:{id}`, `urn:sempkm:system` → `system`.
- The filter dropdown uses htmx `hx-get` with `hx-target="#ops-log-table"` — verify no layout shift or content duplication when filtering.
