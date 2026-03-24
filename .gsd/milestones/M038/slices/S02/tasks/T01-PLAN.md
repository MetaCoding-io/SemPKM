---
estimated_steps: 5
estimated_files: 5
skills_used:
  - test
  - review
---

# T01: Rules service + ontology extension

**Slice:** S02 — Schedule Rules Engine + Daily Plan Generation
**Milestone:** M038

## Description

Create the rules service (pure-function CRUD and evaluation logic for schedule rules stored as JSON in StateClient) and extend the media-scheduler ontology with DailyMediaPlan + PlanEntry classes needed by plan generation. Add the generate-plan task to the app manifest. Write comprehensive unit tests for rules evaluation and CRUD.

Rules are stored as a JSON array under StateClient key `schedule_rules`. Each rule has: id (uuid), name, priority (int, higher wins), enabled (bool), conditions (location_zone, activity, time_period, time_range — null means wildcard), and action (type + value). Evaluation uses AND-matching: all non-null conditions must match the context for the rule to fire. Rules are sorted by priority descending; ties broken by array position.

## Steps

1. **Create `apps/media-scheduler/services/rules_service.py`** with:
   - Constants: `RULES_STATE_KEY = "schedule_rules"`, default durations dict
   - `validate_rule(rule_dict) → rule_dict` — validates required fields, generates UUID if missing, sets defaults
   - `load_rules(state_client) → list[dict]` — `state.get(RULES_STATE_KEY)` → `json.loads()` → list, returns `[]` if None
   - `save_rules(state_client, rules) → None` — `state.set(RULES_STATE_KEY, json.dumps(rules))`
   - `add_rule(state_client, rule_dict) → dict` — validates, appends, saves, returns validated rule
   - `update_rule(state_client, rule_id, updates) → dict|None` — finds by id, merges updates, saves, returns updated rule or None
   - `delete_rule(state_client, rule_id) → bool` — removes by id, saves, returns success
   - `toggle_rule(state_client, rule_id) → dict|None` — flips `enabled`, saves, returns updated rule
   - `evaluate_rules(rules, context) → list[dict]` — pure function: filters enabled rules, AND-matches conditions vs context dict, checks time_range if present, sorts by priority desc, returns matched rules
   - `_matches_condition(rule_conditions, context) → bool` — null=wildcard, string values must match exactly, time_range checks `context.get("current_time", "")` falls within start/end

2. **Extend `models/media-scheduler/ontology/media-scheduler.jsonld`** — add to the `@graph` array:
   - `ms:DailyMediaPlan` OWL class with rdfs:label "Daily Media Plan", rdfs:comment
   - `ms:PlanEntry` OWL class with rdfs:label "Plan Entry", rdfs:comment
   - `ms:planStatus` DatatypeProperty (domain: DailyMediaPlan, range: xsd:string) — "active", "completed", "regenerating"
   - `ms:plan` ObjectProperty (domain: PlanEntry, range: DailyMediaPlan)
   - `ms:mediaItem` ObjectProperty (domain: PlanEntry, range: MediaItem)
   - `ms:slotStart` DatatypeProperty (domain: PlanEntry, range: xsd:string) — time like "08:30"
   - `ms:slotEnd` DatatypeProperty (domain: PlanEntry, range: xsd:string)
   - `ms:slotOrder` DatatypeProperty (domain: PlanEntry, range: xsd:integer)
   - `ms:entryStatus` DatatypeProperty (domain: PlanEntry, range: xsd:string)
   - `ms:ruleId` DatatypeProperty (domain: PlanEntry, range: xsd:string)

3. **Extend `models/media-scheduler/shapes/media-scheduler.jsonld`** — add to the `@graph` array:
   - `ms:DailyMediaPlanShape` NodeShape targeting ms:DailyMediaPlan with properties: dcterms:date (xsd:date, required), dcterms:created (xsd:dateTime), ms:planStatus (xsd:string, sh:in ["active", "completed", "regenerating"])
   - `ms:PlanEntryShape` NodeShape targeting ms:PlanEntry with properties: ms:plan (class DailyMediaPlan, required), ms:mediaItem (class MediaItem, required), ms:slotStart (xsd:string), ms:slotEnd (xsd:string), ms:slotOrder (xsd:integer), ms:entryStatus (xsd:string, sh:in ["pending", "active", "completed", "skipped", "replaced"]), ms:ruleId (xsd:string)
   - Add PropertyGroup `ms:PlanEntryScheduleGroup` (order 1) and `ms:PlanEntryStatusGroup` (order 2)

4. **Update `apps/media-scheduler/manifest.yaml`** — add a second task entry under `tasks:`:
   ```yaml
   - id: "generate-plan"
     description: "Generate or regenerate today's media plan"
     interval: "6h"
     configurable: true
     retryPolicy:
       maxRetries: 1
       backoffMultiplier: 2
       maxBackoff: "5m"
   ```

5. **Add ~20 rule tests to `backend/tests/test_media_scheduler.py`** — import rules_service via same importlib pattern as podcast_service. Test classes:
   - `TestRuleValidation` — validate_rule with valid rule, missing fields get defaults, missing name raises
   - `TestRuleCRUD` — load_rules empty, add_rule, update_rule, delete_rule, toggle_rule with AsyncMock StateClient
   - `TestRuleEvaluation` — evaluate with matching context, no match, wildcard conditions, priority ordering, disabled rules filtered, time_range matching, empty rules list, multiple matches sorted by priority

## Must-Haves

- [ ] rules_service.py has validate_rule, load_rules, save_rules, add_rule, update_rule, delete_rule, toggle_rule, evaluate_rules
- [ ] evaluate_rules correctly AND-matches conditions, handles null wildcards, sorts by priority desc
- [ ] Time range condition checks current_time string against start/end
- [ ] Ontology has DailyMediaPlan and PlanEntry classes with all 6 new properties
- [ ] Shapes have DailyMediaPlanShape and PlanEntryShape with appropriate constraints
- [ ] Manifest has generate-plan task with 6h interval
- [ ] ≥20 new rule-related tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "rule or Rule"` — all rule tests pass
- `python3 -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); types=[n['@id'] for n in d['@graph'] if n.get('@type')=='owl:Class']; assert 'ms:DailyMediaPlan' in types and 'ms:PlanEntry' in types"`
- `python3 -c "import yaml; m=yaml.safe_load(open('apps/media-scheduler/manifest.yaml')); ids=[t['id'] for t in m['tasks']]; assert 'generate-plan' in ids"`

## Inputs

- `apps/media-scheduler/services/podcast_service.py` — MS_NS, APP_NS constants to reuse
- `models/media-scheduler/ontology/media-scheduler.jsonld` — existing ontology to extend
- `models/media-scheduler/shapes/media-scheduler.jsonld` — existing shapes to extend
- `apps/media-scheduler/manifest.yaml` — existing manifest to add task
- `backend/tests/test_media_scheduler.py` — existing test file to extend with rule tests

## Expected Output

- `apps/media-scheduler/services/rules_service.py` — new rules service module
- `models/media-scheduler/ontology/media-scheduler.jsonld` — extended with DailyMediaPlan + PlanEntry
- `models/media-scheduler/shapes/media-scheduler.jsonld` — extended with new shapes
- `apps/media-scheduler/manifest.yaml` — extended with generate-plan task
- `backend/tests/test_media_scheduler.py` — extended with ≥20 rule tests
