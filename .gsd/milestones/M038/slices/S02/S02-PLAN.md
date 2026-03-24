# S02: Schedule Rules Engine + Daily Plan Generation

**Goal:** Users create schedule rules mapping context conditions to media sources, trigger daily plan generation, and see an ordered time-slot plan for today.
**Demo:** User opens Media Scheduler, creates a rule "when commuting, play podcasts", triggers plan generation, and sees today's plan with time-slotted podcast episodes in the Today tab.

## Must-Haves

- Rules CRUD: create, read, update, delete schedule rules stored as JSON in StateClient
- Rule evaluation: AND-match conditions (location_zone, activity, time_period, time_range) against context, priority ordering, wildcard null conditions
- DailyMediaPlan and PlanEntry OWL classes + SHACL shapes in the ontology
- Plan generation: evaluate rules → query matching MediaItems → allocate time slots → bulk-create plan entries via CommandClient
- `generate-plan` scheduled task in manifest
- Tab navigation UI (Today / Episodes / Rules) in main.html
- Today view showing agenda-style plan with time slots, item info, and status badges
- Rules view with list, enable/disable toggles, inline add/edit form
- All htmx URLs use `/app/media-scheduler/` proxy prefix
- ~40 new unit tests covering rules CRUD, evaluation, plan generation, and slot allocation

## Proof Level

- This slice proves: contract + integration (rules evaluate, plan generates, UI renders)
- Real runtime required: no (unit tests with mocked SDK clients prove logic; template rendering verified by htmx URL audit)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` — all tests pass (existing 64 + ~40 new ≥ 100 total)
- `grep -c "async def test_\|def test_" backend/tests/test_media_scheduler.py` — returns ≥ 100
- Rules evaluation tests: wildcard matching, priority ordering, time range checks, empty rules
- Plan generation tests: slot allocation math, default durations, dedup, empty item handling
- `rg 'hx-get="|hx-post="' apps/media-scheduler/frontend/templates/ | grep -v '/app/media-scheduler/'` — returns empty (all htmx URLs prefixed)
- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "invalid or error or empty" --no-header -q 2>&1 | tail -1` — failure-path tests present and passing (validates error handling coverage)

## Observability / Diagnostics

- Runtime signals: `logger.info` on plan generation (rules matched count, items selected, entries created); `logger.warning` on context fetch failure, empty plan
- Inspection surfaces: `generate-plan` task return dict (`rules_matched`, `entries_created`, `plan_iri`); plan stored as RDF queryable via SPARQL
- Failure visibility: context fetch 401/timeout logged with error; plan generation errors propagated to task scheduler with error count
- Redaction constraints: none (no secrets in rules or plan data)

## Integration Closure

- Upstream surfaces consumed: `apps/media-scheduler/services/podcast_service.py` (MS_NS, MEDIA_ITEM_TYPE constants, IRI patterns), `models/media-scheduler/ontology/media-scheduler.jsonld` (extended), `models/media-scheduler/shapes/media-scheduler.jsonld` (extended), M037 context API (`GET /api/context/current`)
- New wiring introduced in this slice: `generate-plan` task handler, 8 new routes in app.py, tab navigation replaces single-view main.html
- What remains before the milestone is truly usable end-to-end: S03 (YouTube), S04 (Spotify), S05 (context-driven real-time adaptation + mobile), S06 (stats), S07 (E2E tests)

## Tasks

- [x] **T01: Rules service + ontology extension** `est:1h30m`
  - Why: Establishes the rules data model (JSON in StateClient), pure-function CRUD and evaluation logic, and extends the ontology with DailyMediaPlan + PlanEntry types needed by plan generation
  - Files: `apps/media-scheduler/services/rules_service.py`, `models/media-scheduler/ontology/media-scheduler.jsonld`, `models/media-scheduler/shapes/media-scheduler.jsonld`, `apps/media-scheduler/manifest.yaml`, `backend/tests/test_media_scheduler.py`
  - Do: Create rules_service.py with rule schema validation, CRUD (load_rules/save_rules/add_rule/update_rule/delete_rule via StateClient JSON), evaluate(context, rules) → matched rules sorted by priority. Extend ontology JSON-LD with DailyMediaPlan and PlanEntry classes + 6 new properties. Extend shapes JSON-LD with DailyMediaPlanShape and PlanEntryShape. Add generate-plan task to manifest. Write ~20 unit tests for rules evaluation, CRUD, serialization.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "rule"` — all rule tests pass
  - Done when: rules_service.py exists with working CRUD + evaluate(), ontology has DailyMediaPlan + PlanEntry, manifest has generate-plan task, ≥20 new rule-related tests pass

- [x] **T02: Plan generation service + task handler** `est:1h30m`
  - Why: Builds the core plan generation logic — selecting items per matched rule, allocating time slots, and creating plan entries as RDF via CommandClient. Wires the generate-plan scheduled task.
  - Files: `apps/media-scheduler/services/plan_service.py`, `apps/media-scheduler/app.py`, `backend/tests/test_media_scheduler.py`
  - Do: Create plan_service.py with: fetch_context() helper (GET /api/context/current via platform client), build_item_selection_sparql(action) for each action type (source_type/source_iri/category), allocate_time_slots(items, start_time) with default durations (1800s podcast, 900s video, 240s track), generate_plan(ctx, date, context) that orchestrates rules→items→slots→bulk create. In app.py add generate-plan task handler that calls generate_plan(). Old plan entries get patched to "replaced" status before new ones are created (no object.delete needed). Write ~20 tests for slot allocation, item selection SPARQL construction, plan generation flow with mocked clients.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "plan"` — all plan tests pass
  - Done when: plan_service.py exists with working generate_plan(), app.py has generate-plan task handler, ≥20 new plan-related tests pass

- [x] **T03: UI routes + templates + CSS** `est:1h30m`
  - Why: Wires rules service and plan service to the user via htmx fragment routes, tab navigation, today view, and rules builder UI
  - Files: `apps/media-scheduler/app.py`, `apps/media-scheduler/frontend/templates/main.html`, `apps/media-scheduler/frontend/templates/today.html`, `apps/media-scheduler/frontend/templates/rules.html`, `apps/media-scheduler/frontend/templates/rule-form.html`, `apps/media-scheduler/frontend/static/styles.css`
  - Do: Add 8 routes to app.py: rules list (GET /_fragments/rules), rule form (GET /_fragments/rules/add), rule create (POST /_fragments/rules), rule update (POST /_fragments/rules/{id}), rule delete (POST /_fragments/rules/{id}/delete), rule toggle (POST /_fragments/rules/{id}/toggle), today view (GET /_fragments/today), plan trigger (POST /_fragments/plan/generate). Rework main.html with tab bar (Today/Episodes/Rules) using htmx tab switching. Create today.html (agenda layout: time slots, item cards, status badges, "Generate Plan" button, empty state). Create rules.html (rule list with priority badges, enable/disable toggles, delete buttons). Create rule-form.html (condition dropdowns for location_zone/activity/time_period, optional time range inputs, action type radio + value selector, priority input). Extend styles.css with tab nav, today view, rule builder styles. All htmx URLs use /app/media-scheduler/ proxy prefix. Lucide icons in flex containers get flex-shrink: 0.
  - Verify: `rg 'hx-get="|hx-post="' apps/media-scheduler/frontend/templates/ | grep -v '/app/media-scheduler/'` — returns empty; all 4 templates exist and render valid HTML structure
  - Done when: Tab navigation works (Today/Episodes/Rules), today view shows plan entries or empty state, rules view shows rule list with add/edit/delete/toggle, all htmx URLs prefixed

## Files Likely Touched

- `apps/media-scheduler/services/rules_service.py` (CREATE)
- `apps/media-scheduler/services/plan_service.py` (CREATE)
- `apps/media-scheduler/app.py` (MODIFY — add routes + task handler)
- `apps/media-scheduler/manifest.yaml` (MODIFY — add generate-plan task)
- `apps/media-scheduler/frontend/templates/main.html` (MODIFY — tab navigation)
- `apps/media-scheduler/frontend/templates/today.html` (CREATE)
- `apps/media-scheduler/frontend/templates/rules.html` (CREATE)
- `apps/media-scheduler/frontend/templates/rule-form.html` (CREATE)
- `apps/media-scheduler/frontend/static/styles.css` (MODIFY)
- `models/media-scheduler/ontology/media-scheduler.jsonld` (MODIFY)
- `models/media-scheduler/shapes/media-scheduler.jsonld` (MODIFY)
- `backend/tests/test_media_scheduler.py` (MODIFY)
