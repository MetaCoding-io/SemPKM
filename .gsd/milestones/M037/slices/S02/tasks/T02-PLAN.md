---
estimated_steps: 5
estimated_files: 5
skills_used:
  - test
---

# T02: Rules CRUD API router, integration hook, and router tests

**Slice:** S02 — Auto-Persona Rules Engine & Settings UI
**Milestone:** M037

## Description

Build the HTTP API layer for context rules and wire the critical integration hook: when a context update arrives, evaluate rules and auto-switch the persona. This is the core integration seam — the context router's `update_context()` endpoint gains rule evaluation logic that calls `PersonaService.activate()` and broadcasts a `persona_switched` SSE event.

## Steps

1. Create `backend/app/context/rules_router.py` with a FastAPI APIRouter (prefix `/api/context/rules`, tags `["context-rules"]`):
   - `GET /` — list rules for authenticated user. Returns JSON array of rule objects (id, name, conditions, persona_id, priority, enabled, created_at, updated_at). Uses `RulesEngine.list_rules(user_id)`.
   - `POST /` — create rule. Pydantic request model: `name` (str, required), `conditions` (dict, required), `persona_id` (str, required), `priority` (int, default 0), `enabled` (bool, default True). Returns created rule.
   - `PUT /{rule_id}` — update rule. All fields optional. Returns updated rule or 404.
   - `DELETE /{rule_id}` — delete rule. Returns 204 on success, 404 if not found.
   - `POST /test` — evaluate all user's rules against current context (via `ContextService.get_current()` + `RulesEngine.evaluate()`). Returns `{"match": true, "persona_id": "...", "rule_name": "..."}` or `{"match": false}`. No side effects — read-only evaluation.
   - All endpoints require auth via `get_current_user_or_api`.

2. Add `get_rules_engine` dependency function to `backend/app/dependencies.py`:
   - `async def get_rules_engine(request: Request) -> RulesEngine:` — returns `request.app.state.rules_engine`
   - Also add `get_persona_service` if it doesn't exist: `async def get_persona_service(request: Request) -> PersonaService:` — returns `request.app.state.persona_service`

3. Wire into `backend/app/main.py`:
   - Import `RulesEngine` from `app.context.rules_engine`
   - Register `app.state.rules_engine = RulesEngine(async_session_factory)` in the lifespan
   - Import and include the rules router: `app.include_router(rules_router)`

4. Add integration hook to `backend/app/context/router.py` in `update_context()`:
   - After the existing `broadcast.publish(...)` call, add rule evaluation:
   ```python
   # Auto-persona rule evaluation
   rules_engine = request.app.state.rules_engine
   persona_service = request.app.state.persona_service
   # Check manual override — skip evaluation if set
   current_ctx = await service.get_current(user.id)
   # Clear manual_override flag on context update (new context = re-evaluate)
   # Evaluate rules
   matched_persona_id = await rules_engine.evaluate(user.id, fields)
   if matched_persona_id:
       # Check if already the active persona
       active = await persona_service.get_active(user.id)
       if not active or str(active.id) != matched_persona_id:
           result = await persona_service.activate(uuid.UUID(matched_persona_id), user.id)
           if result:
               await broadcast.publish(SSEEvent(
                   event="persona_switched",
                   data={"persona_id": matched_persona_id, "persona_name": result.name, "rule_name": "auto"}
               ))
   ```
   - Add `import uuid` if not already imported
   - The `data` field in SSEEvent needs to be serialized — use `json.dumps()` or a dict-compatible approach matching how `context_update` events are serialized (check existing `dataclasses.asdict()` pattern)

5. Write `backend/tests/test_rules_router.py` — router-level tests using `httpx.AsyncClient`:
   - Test fixtures: db_engine, session_factory, app with overridden dependencies, client
   - Follow the pattern from `test_context_router.py` for app setup
   - Tests: POST create rule (201), GET list rules (empty, then with rules), GET list only returns current user's rules, PUT update rule, DELETE rule (204), DELETE nonexistent (404), POST test endpoint (match and no-match), auth enforcement on all endpoints (401 without auth)
   - Integration test: create a rule, POST context update, verify persona_switched event would be emitted (mock the broadcast to capture events)
   - Target: 12-18 tests

## Must-Haves

- [ ] All 5 CRUD+test endpoints work with correct HTTP status codes
- [ ] Rules are scoped to the authenticated user (no cross-user access)
- [ ] Integration hook evaluates rules on every context update
- [ ] `persona_switched` SSE event broadcast when auto-switch triggers
- [ ] Active persona check prevents redundant switches
- [ ] `get_rules_engine` dependency function registered
- [ ] Rules router mounted in main.py
- [ ] All router tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rules_router.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py tests/test_rules_router.py -v` — both test suites pass together

## Observability Impact

- Signals added: `context.rule_matched` log on rule match during integration hook; `persona_switched` SSE event with persona_id, persona_name, rule_name
- How a future agent inspects: `GET /api/context/rules` shows all rules; `POST /api/context/rules/test` tests evaluation; SSE stream shows `persona_switched` events
- Failure state exposed: rule evaluation errors logged with traceback in context router; persona activation failures logged by PersonaService

## Inputs

- `backend/app/context/rules_engine.py` — RulesEngine class from T01
- `backend/app/context/rules_models.py` — ContextRule model from T01
- `backend/app/context/router.py` — existing context router (add integration hook)
- `backend/app/context/service.py` — ContextService.get_current()
- `backend/app/context/broadcast.py` — ContextBroadcast for SSE publishing
- `backend/app/persona/service.py` — PersonaService.activate() and get_active()
- `backend/app/main.py` — lifespan registration and router mounting
- `backend/app/dependencies.py` — dependency function registration
- `backend/tests/test_context_router.py` — test pattern reference

## Expected Output

- `backend/app/context/rules_router.py` — CRUD + test API router
- `backend/app/context/router.py` — modified with integration hook
- `backend/app/main.py` — modified with RulesEngine registration + router mount
- `backend/app/dependencies.py` — modified with get_rules_engine (and get_persona_service if needed)
- `backend/tests/test_rules_router.py` — comprehensive router tests
