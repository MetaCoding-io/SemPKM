---
id: S02
milestone: M038
outcome: success
tasks_completed: 3
tasks_total: 3
test_count: 164
duration: ~58m
completed_at: 2026-03-23
---

# S02 Summary: Schedule Rules Engine + Daily Plan Generation

## What This Slice Delivered

Users can create schedule rules mapping context conditions (location, activity, time period, time range) to media sources, trigger daily plan generation, and see an ordered time-slot agenda for today. The slice added two new services (rules + plan generation), extended the media-scheduler ontology with DailyMediaPlan/PlanEntry types, added 8 htmx routes, and reworked the app from a single-view layout to a 3-tab interface (Today / Episodes / Rules).

## Key Artifacts

| File | Role |
|------|------|
| `apps/media-scheduler/services/rules_service.py` | Rules CRUD + AND-matching evaluation (pure functions + async StateClient I/O) |
| `apps/media-scheduler/services/plan_service.py` | Plan generation orchestration: context→rules→items→dedup→slots→patch-old→bulk-create |
| `apps/media-scheduler/app.py` | 8 new htmx routes (today, rules CRUD, plan generate, current-suggestion) + generate-plan task handler |
| `apps/media-scheduler/frontend/templates/main.html` | 3-tab interface replacing single-view layout |
| `apps/media-scheduler/frontend/templates/today.html` | Agenda-style plan view with time slots, status badges, now-playing indicator |
| `apps/media-scheduler/frontend/templates/rules.html` + `rules-list.html` | Rules management with toggle/delete, inner partial for htmx swap |
| `apps/media-scheduler/frontend/templates/rule-form.html` | Inline rule builder with condition dropdowns, action radios, time range inputs |
| `apps/media-scheduler/frontend/static/styles.css` | Tab bar, plan entry cards, rule cards, status badge variants, form styles |
| `models/media-scheduler/ontology/media-scheduler.jsonld` | DailyMediaPlan, PlanEntry OWL classes + 8 properties |
| `models/media-scheduler/shapes/media-scheduler.jsonld` | DailyMediaPlanShape, PlanEntryShape with status enums |
| `apps/media-scheduler/manifest.yaml` | `generate-plan` scheduled task (6h interval) |
| `backend/tests/test_media_scheduler.py` | 164 tests total (64 S01 + 48 rules + 39 plan + 13 UI-related assertions) |

## Architecture Decisions

- **D354:** Time range rules fail-closed when `current_time` missing from context — safety for context-driven automation
- **D355:** Old plan entries patched to `entryStatus="replaced"` instead of deleted — avoids `object.delete` permission, preserves plan history

## Patterns Established

1. **Rules stored as JSON in StateClient** keyed by `RULES_STATE_KEY`. CRUD via `load_rules`/`save_rules` helpers. `evaluate_rules` is a pure function (no I/O) — takes rules list + context dict, returns matched rules sorted by priority descending.

2. **AND-matching with null=wildcard for simple conditions.** Each condition field (`location_zone`, `activity`, `time_period`) matches if null or equal. `time_range` is a dict with `start`/`end` HH:MM strings supporting midnight wrapping (start > end).

3. **Plan generation pipeline:** `fetch_context()` → `evaluate_rules()` → `build_item_query()` per action → dedup items by IRI → `allocate_slots()` → patch old entries to "replaced" → bulk-create new entries via CommandClient. Returns structured summary dict for logging.

4. **Default durations per source type:** podcast 1800s, youtube 900s, spotify 240s, unknown defaults to 1800s. `allocate_slots()` is a pure function — sequential time assignment from configurable start hour.

5. **Template partial pattern for htmx swap:** `rules.html` includes `rules-list.html` via Jinja2 `{% include %}`. CRUD routes return the inner partial for `#ms-rules-list` innerHTML swap. Full page load returns the wrapper that includes the partial.

6. **Tab switching via `msSelectTab()` JS function** — manages active state + `htmx.ajax()` fragment loading into `#ms-tab-content`. Today tab loads on page init via `hx-trigger="load"`.

## What S05 Should Know

- **RulesEngine surface:** Import `evaluate_rules` from `rules_service` — it's a pure function. Takes `(rules_list, context_dict)` → `List[rule_dicts]` sorted by priority. S05 needs to call this on every context SSE event (with debounce per D349).
- **Plan regeneration:** `generate_plan(ctx, date_str=None, context_override=None)` is the entry point. Pass `context_override` to skip the HTTP context fetch. Returns `{plan_iri, date, rules_matched, entries_created}`.
- **Current suggestion endpoint:** `GET /_fragments/current-suggestion` returns minimal HTML suitable for the mobile widget in S05.
- **Today SPARQL:** Filters PlanEntry objects by date string in plan title, excludes "replaced" status, orders by `slotOrder`. Time-slot now-playing detection is server-side (comparing current UTC time against slot start/end).

## Verification Evidence

| Check | Result |
|-------|--------|
| `pytest tests/test_media_scheduler.py -v` | 164 passed ✅ |
| `grep -c "async def test_\|def test_"` | 164 (≥100 required) ✅ |
| htmx URL prefix audit | All URLs use `/app/media-scheduler/` ✅ |
| Error/edge case tests (`-k "invalid or error or empty"`) | 31 passed ✅ |
| Templates exist (today, rules, rules-list, rule-form) | 4/4 present ✅ |
| Route count (14 decorators) | 14 ✅ |
| Python AST parse on app.py | Clean ✅ |

## Known Issues

None.
