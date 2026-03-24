---
estimated_steps: 5
estimated_files: 1
skills_used:
  - test
---

# T01: Backend integration test proving cross-service context loop

**Slice:** S07 — End-to-End Integration & Acceptance
**Milestone:** M037

## Description

Create `backend/tests/test_context_integration.py` — an integration test file that wires real `ContextService`, `RulesEngine`, `PersonaService`, `NotificationService`, and `ContextBroadcast` together using in-memory SQLite (not mocks). This is the one remaining verification gap: individual slice tests mock adjacent services, but the full chain has never been proven with real service instances.

The test exercises the context update endpoint's integration hook in `backend/app/context/router.py` — the code path that chains context persist → SSE broadcast → rule evaluation → persona switch → notification dispatch/suppression.

Firebase dispatch is the only thing mocked (no real FCM in tests). All other services use real implementations backed by a shared in-memory SQLite database.

## Steps

1. **Set up test fixtures with real services.** Create an in-memory SQLite async engine with `create_async_engine("sqlite+aiosqlite://")`, run `Base.metadata.create_all`, and create a `session_factory`. Instantiate real `ContextService(session_factory)`, `RulesEngine(session_factory)`, `PersonaService(session_factory)`, `NotificationService(session_factory, context_service=context_service, firebase_app=None)`, and `ContextBroadcast()`. Register all on a FastAPI test app's `app.state` matching the attribute names in `main.py` lifespan: `context_service`, `context_broadcast`, `rules_engine`, `persona_service`, `notification_service`. Add `app.state.shutdown_event = asyncio.Event()`. Mount the context router. Override `get_current_user_or_api` to return a test `User`. Override `get_context_service`, `get_context_broadcast`, `get_rules_engine`, `get_persona_service`, `get_notification_service` dependency functions.

2. **Seed database helper.** Write async helpers to: (a) create a User row in the `users` table, (b) create a Persona row and return its UUID, (c) create a ContextRule row with conditions dict and persona_id, (d) create NotificationPreferences for the user. Use the session_factory directly for seeding — these aren't going through the API.

3. **Write test cases (8+ tests):**
   - `test_full_loop_context_to_persona_switch` — Seed user, persona "Work", rule {location_zone: "office"} → Work persona. POST `/api/context/update` with `{"location_zone": "office"}`. Assert response has `location_zone: "office"`. Call `persona_service.get_active(user_id)` and assert it's the Work persona.
   - `test_notification_dispatched_on_zone_change` — Same setup. Mock `NotificationService.send_to_user` (patch the method, not the whole service). POST context with location_zone. Assert `send_to_user` was called with notification_type="context_changes".
   - `test_notification_suppressed_calendar_busy` — Seed NotificationPreferences with suppress_when_busy=True. First POST context with calendar_busy=True. Then POST with location_zone change. Assert `send_to_user` is NOT called (or called with suppression). Verify via the `should_suppress` method returning `(True, "calendar_busy")`.
   - `test_notification_suppressed_quiet_hours` — Seed NotificationPreferences with quiet_start="00:00", quiet_end="23:59" (always quiet). POST context with location_zone. Verify notification suppressed.
   - `test_context_staleness_via_ttl` — POST context, then GET `/api/context/current` with a zero-TTL service (or manipulate `updated_at`). Assert `is_stale: true` in response.
   - `test_no_rule_match` — Seed user with no rules. POST context. Assert response succeeds, persona unchanged (get_active returns None or original).
   - `test_rule_priority_ordering` — Seed two rules matching the same context with different priorities and different target personas. POST context. Assert higher-priority persona is activated.
   - `test_redundant_switch_skipped` — POST context matching a rule twice. Assert persona_service.activate called only once (second update sees active persona already matches). Verify via mock/spy on activate method.

4. **Verify all new tests pass:** `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py -v`

5. **Verify no regression:** `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py tests/test_rules_engine.py tests/test_rules_router.py tests/test_zone_service.py tests/test_zone_router.py tests/test_notification_service.py tests/test_notification_router.py -v` — all 176 existing tests still pass.

## Must-Haves

- [ ] Real services (not mocks) for ContextService, RulesEngine, PersonaService, ContextBroadcast
- [ ] NotificationService with real suppression logic but mocked FCM dispatch (firebase_app=None)
- [ ] In-memory SQLite with all context tables created via Base.metadata.create_all
- [ ] 8+ test cases covering: full loop, notification dispatch, suppression (busy + quiet hours), staleness, no-match, priority, redundant switch
- [ ] All tests pass in isolation (`-v` shows green)
- [ ] Zero regression in existing 176 context/rules/notification tests

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py -v` — 8+ tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py tests/test_rules_engine.py tests/test_rules_router.py tests/test_zone_service.py tests/test_zone_router.py tests/test_notification_service.py tests/test_notification_router.py -v` — all 176 existing tests pass

## Inputs

- `backend/app/context/router.py` — the integration hub with update_context() chaining all services
- `backend/app/context/service.py` — ContextService with update() and get_current()
- `backend/app/context/rules_engine.py` — RulesEngine with evaluate() and CRUD
- `backend/app/context/notification_service.py` — NotificationService with should_suppress() and send_to_user()
- `backend/app/context/broadcast.py` — ContextBroadcast SSE fan-out
- `backend/app/persona/service.py` — PersonaService with activate() and get_active()
- `backend/app/persona/models.py` — Persona SQLAlchemy model
- `backend/app/auth/models.py` — User SQLAlchemy model (needed for FK resolution in Base.metadata)
- `backend/app/context/models.py` — UserContext SQLAlchemy model
- `backend/app/context/rules_models.py` — ContextRule SQLAlchemy model
- `backend/app/context/notification_models.py` — DeviceToken and NotificationPreferences models
- `backend/app/dependencies.py` — dependency function signatures for overrides
- `backend/tests/test_rules_engine.py` — reference for in-memory SQLite fixture pattern
- `backend/tests/test_notification_service.py` — reference for NotificationService test setup

## Expected Output

- `backend/tests/test_context_integration.py` — integration test file with 8+ tests, all passing
