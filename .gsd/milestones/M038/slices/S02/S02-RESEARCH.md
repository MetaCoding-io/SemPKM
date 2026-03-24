# S02: Schedule Rules Engine + Daily Plan Generation — Research

## Summary

Straightforward application of known patterns. Rules are JSON in StateClient (per roadmap boundary map), daily plan is RDF via CommandClient (queryable by copilot). The rules engine is a pure-function evaluator (no DB, no SQLAlchemy — unlike M037's context rules which use Postgres). UI is htmx fragments in the existing sidebar+main layout. No new dependencies needed.

**Risk:** Low-medium. The rules data model and evaluation logic are simple. The riskiest part is the daily plan generation SPARQL — selecting appropriate MediaItems per rule match, ordering by time slot, and handling sources with no available content.

## Recommendation

Build in this order:
1. Rules service (pure functions: CRUD, evaluate, serialize) — establishes data model, enables testing immediately
2. Ontology extension (DailyMediaPlan + PlanEntry types) — needed before plan generation can create RDF
3. Plan generation service (pure functions: build plan from rules + items + context) — heaviest logic
4. App routes + templates (rule builder UI, today view, plan trigger) — wires everything together
5. Tests covering rules CRUD, evaluation, plan generation, and route handlers

## Implementation Landscape

### What Exists (from S01)

| Component | Location | Relevance |
|-----------|----------|-----------|
| App entrypoint | `apps/media-scheduler/app.py` | Add new routes + `generate-plan` task handler here |
| Podcast service | `apps/media-scheduler/services/podcast_service.py` | IRI minting pattern, SPARQL query patterns to reuse |
| Model ontology | `models/media-scheduler/ontology/media-scheduler.jsonld` | Extend with DailyMediaPlan + PlanEntry classes |
| SHACL shapes | `models/media-scheduler/shapes/media-scheduler.jsonld` | Extend with PlanEntry shape (for workspace browsing) |
| ViewSpecs | `models/media-scheduler/views/media-scheduler.jsonld` | No changes needed — plan is shown in app UI, not workspace views |
| App manifest | `apps/media-scheduler/manifest.yaml` | Add `generate-plan` task definition |
| Main template | `apps/media-scheduler/frontend/templates/main.html` | Rework layout: add tab navigation (Sources, Today, Rules) |
| App CSS | `apps/media-scheduler/frontend/static/styles.css` | Extend with rule-builder and plan-view styles |
| Tests | `backend/tests/test_media_scheduler.py` | Extend with rules + plan generation tests |
| M037 context service | `backend/app/context/service.py` | `ContextData` shape: `location_zone`, `activity`, `time_period`, `calendar_event`, `calendar_busy`, `device_id` |
| M037 context API | `backend/app/context/router.py` | `GET /api/context/current` → `{"context": {...}}` |
| StateClient | `backend/sdk/sempkm_app_sdk/clients/state.py` | `get(key) → str|None`, `set(key, value)` — stores strings, JSON must be serialized |
| CommandClient | `backend/sdk/sempkm_app_sdk/clients/commands.py` | `object.create`, `object.patch`, bulk batch for plan entries |
| GraphClient | `backend/sdk/sempkm_app_sdk/clients/graph.py` | SPARQL read queries for items, plan entries |

### What Must Be Created

| Component | File | Description |
|-----------|------|-------------|
| Rules service | `apps/media-scheduler/services/rules_service.py` | Pure functions: rule schema, CRUD via StateClient JSON, evaluate(context) → matched rules |
| Plan service | `apps/media-scheduler/services/plan_service.py` | Pure functions: build_plan(rules, items, context, date) → plan entries; SPARQL for item selection |
| Ontology extension | `models/media-scheduler/ontology/media-scheduler.jsonld` | Add `ms:DailyMediaPlan`, `ms:PlanEntry` classes + properties |
| Shapes extension | `models/media-scheduler/shapes/media-scheduler.jsonld` | Add `ms:PlanEntryShape` with time slot + item reference |
| App routes | `apps/media-scheduler/app.py` | Add 5-6 routes: rules CRUD, today view, generate-plan trigger |
| Rule builder template | `apps/media-scheduler/frontend/templates/rules.html` | htmx form: condition builder + action selector |
| Today view template | `apps/media-scheduler/frontend/templates/today.html` | Agenda-style plan display with time slots and media items |
| CSS additions | `apps/media-scheduler/frontend/static/styles.css` | Tab navigation, rule builder, today view styles |
| Test extension | `backend/tests/test_media_scheduler.py` | ~40 new tests: rules CRUD, evaluation, plan generation |

### StateClient JSON Pattern for Rules

Rules are stored as a JSON array under a single StateClient key `schedule_rules`. Each rule is:

```json
{
  "id": "uuid-string",
  "name": "Commute Podcasts",
  "priority": 10,
  "enabled": true,
  "conditions": {
    "location_zone": null,
    "activity": "commuting",
    "time_period": null,
    "time_range": null
  },
  "action": {
    "type": "source_type",
    "value": "podcast"
  }
}
```

**Condition fields** (AND-matched, null = wildcard — same semantics as M037 `RulesEngine.evaluate()`):
- `location_zone` — matches `context.location_zone` (e.g. "home", "office", "gym")
- `activity` — matches `context.activity` (e.g. "commuting", "exercising", "working", "relaxing")
- `time_period` — matches `context.time_period` (e.g. "morning", "afternoon", "evening", "night")
- `time_range` — local time range like `{"start": "12:00", "end": "13:00"}` — matches if current local time is within range

**Action types:**
- `source_type` — play from any source of this type (e.g. "podcast", "youtube", "spotify")
- `source_iri` — play from a specific source by IRI
- `category` — play from any source in this category by IRI

**Priority:** Higher number wins. Ties broken by array position. Specific time rules should have higher priority than context rules, and context rules higher than defaults.

### RDF Model for Daily Plan

The daily plan needs two new OWL classes:

**ms:DailyMediaPlan** — one per day
- `dcterms:date` (xsd:date) — the plan date
- `dcterms:created` (xsd:dateTime) — when generated
- `ms:planStatus` (xsd:string) — "active", "completed", "regenerating"

**ms:PlanEntry** — ordered entry within a plan
- `ms:plan` (ObjectProperty → ms:DailyMediaPlan) — parent plan
- `ms:mediaItem` (ObjectProperty → ms:MediaItem) — the scheduled item
- `ms:slotStart` (xsd:time or xsd:string) — start time like "08:30"
- `ms:slotEnd` (xsd:time or xsd:string) — end time (computed from start + duration)
- `ms:slotOrder` (xsd:integer) — position in the plan (for ordering)
- `ms:entryStatus` (xsd:string) — "pending", "active", "completed", "skipped"
- `ms:ruleId` (xsd:string) — which rule produced this entry (for debugging/audit)

IRI pattern: `urn:sempkm:app:media-scheduler:plan-{YYYY-MM-DD}` and `urn:sempkm:app:media-scheduler:entry-{plan_date}-{order}`.

### Plan Generation Algorithm

1. **Fetch context** — call `GET /api/context/current` via platform client
2. **Load rules** — `StateClient.get("schedule_rules")` → parse JSON → sort by priority desc
3. **Evaluate rules against context** — same AND-match logic as M037. Time range check adds: if rule has `time_range`, check if current time falls within it
4. **For each matched rule** — query MediaItems matching the action:
   - `source_type` → `FILTER(?sourceType = "{value}")` on items via their source
   - `source_iri` → `FILTER(?source = <{iri}>)` on items
   - `category` → join through `ms:category` on source
   - Only items with `ms:status = "queued"` (not completed/skipped/playing)
   - Order by `dcterms:created DESC` (newest first) with configurable limit
5. **Build time slots** — assign items to time slots based on their duration:
   - Start from current time (or plan start hour if generating for full day)
   - Each item gets `slotStart = previous_end` and `slotEnd = slotStart + duration`
   - Items without duration get a default slot (30 min for podcasts, 15 min for videos, 4 min for tracks)
6. **Delete old plan** — remove today's existing plan entries (if regenerating)
7. **Create new plan** — bulk-create DailyMediaPlan + PlanEntry objects via CommandClient

### Context Fetching from App

The app's internal platform client (available via `ctx._get_platform_client()`) can call the platform's own API:

```python
platform = ctx._get_platform_client()
resp = await platform.get("/api/context/current")
data = resp.json()  # {"context": {"location_zone": "office", "activity": "working", ...}}
```

This is a new pattern — no existing app calls a platform API endpoint. The platform client is authenticated with the app token, and the context endpoint uses `get_current_user_or_api` which accepts Bearer tokens. **Verify this works** — if the app token isn't recognized by the context auth dependency, the call will 401. Mitigation: check `get_current_user_or_api` implementation; worst case, pass context as a parameter to the generate-plan task or read it from the request context on manual trigger.

### UI Layout Approach

The current main.html has a sidebar (sources) + main area (items). S02 transforms this into a tabbed interface:

**Tab bar** in the main area header:
- **Today** — daily plan agenda view (default)
- **Episodes** — existing items list (moved from current default)
- **Rules** — rule list + builder

The sidebar remains sources-only. Tab switching is pure htmx: each tab loads a different `/_fragments/...` endpoint into the main content area. Pattern matches workspace tab navigation (click → `hx-get` → swap inner content).

**Today view** — vertical timeline/agenda:
- Current time indicator line
- Plan entries as cards: thumbnail, title, source name, duration, time slot, status badge
- "Now Playing" highlight on the current entry
- "Generate Plan" button (manual trigger)
- Empty state when no plan exists

**Rules view:**
- Rule list with enable/disable toggles, priority badges, delete buttons
- "Add Rule" button opens inline form
- Condition builder: dropdowns for location_zone, activity, time_period + optional time range inputs
- Action selector: radio group (source_type/source_iri/category) + value selector
- Priority number input
- Save/cancel buttons

### Constraints and Gotchas

1. **StateClient stores strings only** — rules JSON must be `json.dumps()`/`json.loads()`. Maximum value size is limited by SPARQL literal length in RDF4J (typically 10MB+, not a practical concern for rules JSON).

2. **StateClient uses SPARQL UPDATE under the hood** — but it goes through `/api/sparql` which (per KNOWLEDGE.md) does NOT support UPDATE. The StateClient bypasses this — it POSTs to `/api/sparql` which is the read endpoint. **Check:** Does `StateClient.set()` actually work? It sends SPARQL UPDATE (DELETE+INSERT) via POST to `/api/sparql`. The `/api/sparql` endpoint routes through `scope_to_current_graph()` which may reject UPDATE operations. If StateClient.set() doesn't work, rules storage needs a different approach. Mitigation: test `StateClient.set()` manually; if broken, store rules as RDF properties on a sentinel object via `object.patch`.

3. **htmx URLs must use `/app/media-scheduler/` proxy prefix** (KNOWLEDGE.md rule). Every `hx-get` and `hx-post` in templates must be prefixed.

4. **Lucide icons in flex containers need `flex-shrink: 0`** (CLAUDE.md rule). Tab bar buttons will contain Lucide icons.

5. **DailyMediaPlan deletion before regeneration** — the app permissions include `object.create` and `object.patch` but NOT `object.delete`. Plan regeneration either (a) patches old entries to "replaced" status and creates new ones, or (b) needs `object.delete` added to manifest permissions. Option (a) is cleaner — avoids growing the permission surface.

6. **Time zone handling** — plan dates should be naive dates (just YYYY-MM-DD), and time slots should be local time strings (HH:MM). The context system doesn't provide timezone info, and we're dealing with local schedule times.

7. **The `sourceType` sh:in enum is `["podcast", "youtube", "spotify"]`** — the "inactive" soft-delete value used by S01's unsubscribe isn't in the enum. This means the SHACL shape technically rejects patched inactive sources. This is an S01 issue, not S02, but note it for awareness — poll queries filter by sourceType anyway.

### File Change Map

| File | Change Type | Description |
|------|-------------|-------------|
| `apps/media-scheduler/services/rules_service.py` | CREATE | Rules data model, CRUD, evaluate(), serialize/deserialize |
| `apps/media-scheduler/services/plan_service.py` | CREATE | Plan generation: item selection SPARQL, slot allocation, plan creation |
| `apps/media-scheduler/app.py` | MODIFY | Add ~8 routes (rules CRUD, today view, plan generation) + `generate-plan` task |
| `apps/media-scheduler/manifest.yaml` | MODIFY | Add `generate-plan` task definition |
| `apps/media-scheduler/frontend/templates/main.html` | MODIFY | Add tab navigation (Today/Episodes/Rules) |
| `apps/media-scheduler/frontend/templates/today.html` | CREATE | Today plan view — agenda layout |
| `apps/media-scheduler/frontend/templates/rules.html` | CREATE | Rules list view |
| `apps/media-scheduler/frontend/templates/rule-form.html` | CREATE | Add/edit rule form |
| `apps/media-scheduler/frontend/static/styles.css` | MODIFY | Tab nav, today view, rules builder styles |
| `models/media-scheduler/ontology/media-scheduler.jsonld` | MODIFY | Add DailyMediaPlan, PlanEntry classes + 6 properties |
| `models/media-scheduler/shapes/media-scheduler.jsonld` | MODIFY | Add DailyMediaPlanShape, PlanEntryShape |
| `backend/tests/test_media_scheduler.py` | MODIFY | ~40 new tests for rules + plan services |

### Natural Task Boundaries

**T01: Rules service + ontology extension** (~60% of the logic)
- Create `rules_service.py` with pure functions: rule schema validation, CRUD (load/save/add/update/delete via StateClient), evaluate(context, rules) → matched rules
- Extend ontology with DailyMediaPlan + PlanEntry classes
- Extend shapes with PlanEntry shape
- Unit tests for rules evaluation, CRUD, serialization

**T02: Plan generation service** (~25% of the logic)
- Create `plan_service.py` with: item selection SPARQL, slot allocation, plan creation via CommandClient bulk
- Context fetching helper
- `generate-plan` task handler in app.py
- Add task to manifest
- Unit tests for plan building and slot allocation

**T03: UI (routes + templates + CSS)** (~15% of the logic)
- Add app routes for rules CRUD, today view, plan trigger
- Tab navigation in main.html
- Today view template (agenda layout)
- Rules list + rule form templates
- CSS for all new UI
- Verify htmx proxy prefix on all URLs

### Verification Strategy

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` — all tests pass (existing 64 + ~40 new)
- Rules evaluation: test with various context combinations, priority ordering, wildcard conditions
- Plan generation: test with mock items, verify slot allocation math, verify dedup of plan entries
- Template rendering: verify htmx URLs all use proxy prefix
- Manifest: verify `generate-plan` task is valid YAML
