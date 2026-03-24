# S02: Auto-Persona Rules Engine & Settings UI

**Goal:** Context-aware auto-persona switching works end-to-end: rules engine evaluates context changes, triggers PersonaService.activate(), and the workspace persona switches visibly via SSE. Settings UI provides full CRUD for context rules with test-against-current-context.
**Demo:** User creates a rule in Settings ("Office Work → Work persona"), POSTs a context update matching that rule, and watches the workspace persona switch automatically — visible in the persona indicator.

## Must-Haves

- ContextRule SQLAlchemy model with JSON conditions (AND logic) + persona_id action + priority ordering
- Alembic migration 019 creating `context_rules` table and adding `manual_override` column to `user_context`
- RulesEngine with `evaluate(user_id, context) → Optional[persona_id]` — first-match-wins by priority
- CRUD API: GET/POST/PUT/DELETE `/api/context/rules` + POST `/api/context/rules/test`
- Integration hook: context update → rule evaluation → persona activation → SSE `persona_switched` event
- Manual override: manual persona switch suppresses auto-switch until next context update clears the flag
- Settings UI "Context Rules" category with rule list, create/edit form, delete, and test button
- Frontend handler for `persona_switched` SSE event calling `window.switchPersona(id)`

## Proof Level

- This slice proves: integration — rule evaluation triggered by context update drives a real persona switch visible in the workspace
- Real runtime required: yes (Docker stack for browser verification)
- Human/UAT required: no (automated tests + browser assertion)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py -v` — unit tests for RulesEngine logic (priority ordering, AND conditions, disabled rules, no-match, stale skip)
- `cd backend && .venv/bin/python -m pytest tests/test_rules_router.py -v` — router tests for CRUD + test endpoint + integration hook + auth enforcement
- Browser verification: navigate to Settings → Context Rules → create a rule → POST context matching the rule → verify persona_switched SSE event triggers workspace persona change

## Observability / Diagnostics

- Runtime signals: `context.rule_matched` structured log (user_id, rule_name, persona_id) on every rule match; `context.no_rule_matched` when no rule fires; `context.persona_switched` when auto-switch activates
- Inspection surfaces: `GET /api/context/rules` returns all rules with enabled/disabled state; `POST /api/context/rules/test` tests evaluation without side effects
- Failure visibility: rule evaluation exceptions logged with traceback; persona activation failure logged by PersonaService; `manual_override` flag visible in `GET /api/context/current`
- Redaction constraints: none (no secrets in context rules)

## Integration Closure

- Upstream surfaces consumed: `ContextService.get_current()` and `ContextBroadcast.publish()` from S01; `PersonaService.activate()` from persona package; `app.state.persona_service` from main.py lifespan
- New wiring introduced in this slice: rules engine evaluation hook in context router's `update_context()` endpoint; `persona_switched` SSE event type on context stream; `get_rules_engine` dependency in `dependencies.py`; rules CRUD router mounted in `main.py`
- What remains before the milestone is truly usable end-to-end: mobile app (S03-S05) to push context from a real device; push notifications (S06) for proactive alerts

## Tasks

- [x] **T01: ContextRule model, migration, and RulesEngine service with unit tests** `est:45m`
  - Why: The data model and evaluation logic are the foundation — everything else (API, UI, integration) depends on them
  - Files: `backend/app/context/rules_models.py`, `backend/app/context/rules_engine.py`, `backend/migrations/versions/019_context_rules.py`, `backend/tests/test_rules_engine.py`
  - Do: Create ContextRule SQLAlchemy model (id UUID, user_id FK, name, priority int, conditions JSON, persona_id str, enabled bool, timestamps). Write Alembic migration 019 creating `context_rules` table and adding `manual_override` boolean to `user_context`. Implement RulesEngine class with `evaluate(user_id, context_data) → Optional[str]` — loads enabled rules sorted by priority desc, first-match-wins with AND condition matching. Write comprehensive unit tests: priority ordering, AND conditions, partial condition match (subset), disabled rules skipped, no-match returns None, empty rules returns None.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py -v` — all tests pass
  - Done when: RulesEngine correctly evaluates context against rules with priority ordering, AND logic, and all unit tests pass

- [x] **T02: Rules CRUD API router, integration hook, and router tests** `est:45m`
  - Why: The API layer exposes rules management and wires auto-evaluation into the context update flow — this is the critical integration seam
  - Files: `backend/app/context/rules_router.py`, `backend/app/context/router.py`, `backend/app/main.py`, `backend/app/dependencies.py`, `backend/tests/test_rules_router.py`
  - Do: Create rules_router.py with GET/POST/PUT/DELETE `/api/context/rules` CRUD + POST `/api/context/rules/test` (evaluate against current context, return match result without side effects). Add `get_rules_engine` dependency function. Mount rules router in main.py. Add integration hook in context router's `update_context()`: after broadcast.publish(), call rules_engine.evaluate() — if persona_id returned and differs from active persona, call persona_service.activate() and broadcast `persona_switched` SSE event. Implement manual_override logic: manual persona activate sets flag, context update clears it and re-evaluates. Write router tests covering CRUD operations, test endpoint, auth enforcement, and integration hook (mock persona_service to verify activate called on rule match).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_rules_router.py -v` — all tests pass
  - Done when: All CRUD endpoints work, test endpoint returns match/no-match, context update triggers rule evaluation and persona switch with SSE event

- [ ] **T03: Settings UI — Context Rules category panel with CRUD and test** `est:40m`
  - Why: Users need a UI to create, edit, delete, and test context rules — without this the feature is API-only
  - Files: `backend/app/templates/browser/settings_page.html`, `backend/app/templates/browser/_context_rules.html`, `backend/app/browser/settings.py`, `frontend/static/css/settings.css`
  - Do: Add "Context Rules" button to settings sidebar in settings_page.html. Add corresponding panel div with htmx load trigger. Create `_context_rules.html` template partial: rule list (htmx-loaded), create/edit form with fields (name, condition dropdowns for location_zone/activity/time_period, calendar_busy checkbox, target persona dropdown from `/api/personas`, priority number, enabled toggle), delete button with confirmation, "Test against current context" button that POSTs to `/api/context/rules/test`. Add browser settings route to serve the partial. Style the rule builder form in settings.css matching existing settings patterns.
  - Verify: Start Docker stack, navigate to Settings, verify Context Rules category appears, create/edit/delete a rule through the UI, test button shows match result
  - Done when: Full CRUD works through the Settings UI with test button showing match/no-match against current context

- [ ] **T04: Frontend auto-switch handler — SSE persona_switched event** `est:20m`
  - Why: The workspace must react to auto-persona switches — without this handler, the backend switches the persona but the UI doesn't update
  - Files: `frontend/static/js/context-indicator.js`
  - Do: Add `persona_switched` event listener to the existing EventSource in context-indicator.js. On receiving the event (data: `{persona_id, persona_name, rule_name}`), call `window.switchPersona(persona_id)` to apply the workspace layout change. Show a brief toast/notification indicating the auto-switch (e.g., "Switched to Work persona (rule: Office Hours)"). Handle edge case: if `window.switchPersona` is undefined, log a warning and skip.
  - Verify: Browser verification — POST context update that matches a rule, observe persona_switched SSE event triggers `switchPersona` call and workspace persona changes
  - Done when: Auto-persona switch triggered by context update is visible in the workspace within seconds, with a brief notification indicating the rule that triggered it

## Files Likely Touched

- `backend/app/context/rules_models.py` (new)
- `backend/app/context/rules_engine.py` (new)
- `backend/app/context/rules_router.py` (new)
- `backend/app/context/router.py` (modified — integration hook)
- `backend/app/context/models.py` (modified — manual_override awareness)
- `backend/app/main.py` (modified — mount rules router, register RulesEngine)
- `backend/app/dependencies.py` (modified — get_rules_engine)
- `backend/migrations/versions/019_context_rules.py` (new)
- `backend/tests/test_rules_engine.py` (new)
- `backend/tests/test_rules_router.py` (new)
- `backend/app/templates/browser/settings_page.html` (modified)
- `backend/app/templates/browser/_context_rules.html` (new)
- `backend/app/browser/settings.py` (modified)
- `frontend/static/css/settings.css` (modified)
- `frontend/static/js/context-indicator.js` (modified)
