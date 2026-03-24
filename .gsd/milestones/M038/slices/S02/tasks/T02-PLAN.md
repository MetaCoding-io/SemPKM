---
estimated_steps: 5
estimated_files: 3
skills_used:
  - test
  - review
---

# T02: Plan generation service + task handler

**Slice:** S02 — Schedule Rules Engine + Daily Plan Generation
**Milestone:** M038

## Description

Create the plan generation service that orchestrates: evaluate rules against context → query matching MediaItems via SPARQL → allocate time slots → bulk-create DailyMediaPlan + PlanEntry objects via CommandClient. Wire the `generate-plan` task handler in app.py. Write comprehensive unit tests for plan building and slot allocation.

The plan generation flow:
1. Fetch current context from `GET /api/context/current` via platform HTTP client
2. Load rules from StateClient, evaluate against context (using rules_service.evaluate_rules)
3. For each matched rule, build a SPARQL query to select queued MediaItems matching the rule's action (source_type, source_iri, or category filter)
4. Allocate time slots: start from a configurable hour (default 08:00), assign each item start/end based on duration (defaults: 1800s podcast, 900s video, 240s track)
5. Patch any existing plan entries for today to "replaced" status (avoids needing object.delete permission)
6. Bulk-create DailyMediaPlan + PlanEntry objects via CommandClient

IRI patterns: `urn:sempkm:app:media-scheduler:plan-{YYYY-MM-DD}` for plans, `urn:sempkm:app:media-scheduler:entry-{YYYY-MM-DD}-{order}` for entries.

## Steps

1. **Create `apps/media-scheduler/services/plan_service.py`** with:
   - Constants: `DEFAULT_DURATIONS = {"podcast": 1800, "youtube": 900, "spotify": 240}`, `PLAN_START_HOUR = 8`, `MAX_ITEMS_PER_RULE = 5`, IRI templates
   - `mint_plan_iri(date_str) → str` — `urn:sempkm:app:media-scheduler:plan-{date_str}`
   - `mint_entry_iri(date_str, order) → str` — `urn:sempkm:app:media-scheduler:entry-{date_str}-{order:03d}`
   - `build_item_query(action, limit=5) → str` — builds SPARQL SELECT for queued MediaItems:
     - action type `source_type` → `FILTER(?sourceType = "{value}")` joining item→source→sourceType
     - action type `source_iri` → `FILTER(?source = <{value}>)` on items
     - action type `category` → `FILTER(?category = <{value}>)` joining source→category
     - Always filters `ms:status = "queued"`, orders by `dcterms:created DESC`, applies LIMIT
   - `allocate_slots(items, start_hour=8) → list[dict]` — pure function: assigns slotStart/slotEnd based on item duration (or default by source type), returns list of `{item_iri, title, source_type, duration, slot_start, slot_end, slot_order, rule_id}`
   - `async fetch_context(platform_client) → dict` — `GET /api/context/current`, returns context dict or empty dict on failure (logged warning, not raised)
   - `async get_existing_plan_entries(graph_client, plan_iri) → list[str]` — SPARQL query for entry IRIs belonging to a plan
   - `async generate_plan(ctx, date_str=None, context_override=None) → dict` — full orchestration:
     1. date_str defaults to today (YYYY-MM-DD)
     2. Fetch context (or use override)
     3. Load + evaluate rules via rules_service
     4. For each matched rule, query items via graph_client
     5. Collect items (dedup by IRI), allocate slots
     6. Patch existing entries to "replaced" if plan already exists
     7. Bulk-create plan + entries via CommandClient
     8. Return summary dict: `{plan_iri, date, rules_matched, entries_created}`

2. **Import rules_service in plan_service.py** — use same importlib fallback pattern from app.py:
   ```python
   try:
       from services.rules_service import load_rules, evaluate_rules
   except ModuleNotFoundError:
       # importlib fallback for test context
   ```

3. **Add generate-plan task handler to `apps/media-scheduler/app.py`**:
   ```python
   @media_scheduler_app.task("generate-plan")
   async def generate_plan_task(ctx: AppContext) -> dict:
       return await generate_plan(ctx)
   ```
   Import `generate_plan` from plan_service using the same importlib fallback pattern. Also import `fetch_context` for potential manual trigger use.

4. **Add a helper to app.py for platform client access** — The context API needs the platform's HTTP client. `ctx` has `ctx.http` (the app's HTTP client) which is configured with the platform base URL and auth. Use `ctx.http` directly for the context fetch: `await ctx.http.get("/api/context/current")`.

5. **Add ~20 plan tests to `backend/tests/test_media_scheduler.py`**:
   - `TestPlanIriMinting` — mint_plan_iri, mint_entry_iri with date strings
   - `TestBuildItemQuery` — source_type action, source_iri action, category action, verify SPARQL structure
   - `TestAllocateSlots` — empty items, single item with duration, multiple items sequential slots, items without duration get defaults, mixed source types
   - `TestGeneratePlan` — mock context fetch + rules + graph queries + command client; verify plan IRI, entry count, slot ordering; test with no matching rules returns empty plan; test with existing plan patches old entries to "replaced"
   - Import plan_service via importlib pattern, mock rules_service functions at the module level

## Must-Haves

- [ ] plan_service.py has generate_plan(), build_item_query(), allocate_slots(), fetch_context()
- [ ] build_item_query handles all 3 action types (source_type, source_iri, category)
- [ ] allocate_slots correctly chains slot times: each entry starts where the previous ended
- [ ] Default durations: 1800s (podcast), 900s (youtube), 240s (spotify)
- [ ] Old plan entries get patched to "replaced" status, not deleted
- [ ] generate-plan task handler in app.py delegates to plan_service.generate_plan()
- [ ] Context fetch failure doesn't crash plan generation (returns empty plan with warning)
- [ ] ≥20 new plan-related tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "plan or Plan or slot or Slot"` — all plan tests pass
- `grep -c "generate_plan\|generate-plan" apps/media-scheduler/app.py` — returns ≥ 2 (import + handler)

## Inputs

- `apps/media-scheduler/services/rules_service.py` — load_rules, evaluate_rules functions (from T01)
- `apps/media-scheduler/services/podcast_service.py` — MS_NS, APP_NS, MEDIA_ITEM_TYPE constants
- `apps/media-scheduler/app.py` — existing app to add task handler
- `models/media-scheduler/ontology/media-scheduler.jsonld` — DailyMediaPlan/PlanEntry types (from T01)
- `backend/tests/test_media_scheduler.py` — existing test file to extend

## Expected Output

- `apps/media-scheduler/services/plan_service.py` — new plan generation service
- `apps/media-scheduler/app.py` — extended with generate-plan task handler
- `backend/tests/test_media_scheduler.py` — extended with ≥20 plan tests

## Observability Impact

- **New signals:** `logger.info` on plan generation start (rules matched count, items selected, entries created); `logger.warning` on context fetch failure, empty context, item query failure, old entry patch failure; `logger.error` on plan creation failure.
- **Inspection surface:** `generate_plan()` returns a structured summary dict (`plan_iri`, `date`, `rules_matched`, `entries_created`, optional `error`) — the task scheduler logs this automatically. Plan + entry objects are stored as RDF queryable via SPARQL (`?plan a ms:DailyMediaPlan`, `?entry a ms:PlanEntry`).
- **Failure visibility:** Context fetch errors return empty plan (not crash) with warning. Item query errors per-rule are logged and skipped. CommandClient errors surface in the return dict's `error` field.
- **Future agent inspection:** Call `generate_plan(ctx, date_str="YYYY-MM-DD", context_override={...})` with a mock or real context to test end-to-end. Check `allocate_slots()` output for slot math. Use `build_item_query(action)` to inspect the SPARQL generated for a given action.
