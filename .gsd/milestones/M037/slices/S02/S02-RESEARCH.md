# S02 Research: Auto-Persona Rules Engine & Settings UI

## Summary

This slice is **targeted complexity** — known backend patterns (SQLAlchemy model, service, router, Alembic migration) applied to a new domain (context rule evaluation), plus a Settings UI category with CRUD that's novel in shape (rule builder with conditions/action) but follows established settings page patterns. The risky part is the integration seam: hooking rule evaluation into the context update flow and triggering a persona switch visible in the workspace via SSE.

## Recommendation

Build bottom-up: model + migration → service (RulesEngine with `evaluate()`) → API router with CRUD + test endpoint → hook into context update flow → settings UI panel → frontend auto-switch handler. The service and router are testable in isolation before wiring into the live context flow.

## Implementation Landscape

### What Exists (S01 Delivered)

| Component | Location | What S02 Uses |
|-----------|----------|---------------|
| `ContextService` | `backend/app/context/service.py` | `get_current(user_id)` → context dict with `is_stale` |
| `ContextBroadcast` | `backend/app/context/broadcast.py` | `publish()` called after every context update in router |
| Context router | `backend/app/context/router.py` | `update_context()` calls `broadcast.publish()` — the hook point |
| SSE event type | `context_update` | S02 adds `persona_switched` event type to same stream |
| `PersonaService` | `backend/app/persona/service.py` | `activate(persona_id, user_id)` — the action for rule match |
| `app.state.persona_service` | `backend/app/main.py` lifespan | Available to rules engine via dependency injection |
| Context indicator | `frontend/static/js/context-indicator.js` | SSE EventSource consuming `/api/context/stream` — add `persona_switched` handler |
| `switchPersona(id)` | `frontend/static/js/workspace.js` line 2565 | Full save→fetch→activate→apply cycle — NOT exposed on window yet |
| Settings page | `backend/app/templates/browser/settings_page.html` | Sidebar category pattern — add "Context Rules" button + panel |
| Settings router | `backend/app/browser/settings.py` | Pattern for settings sub-routes |

### What S02 Creates

**Backend:**
1. **`ContextRule` SQLAlchemy model** (`backend/app/context/rules_models.py` or extend `models.py`)
   - Fields: `id` (UUID), `user_id` (FK users), `name` (String 255), `priority` (Integer, default 0), `conditions` (JSON — dict of field→value matches), `persona_id` (FK personas), `enabled` (Boolean), `created_at`, `updated_at`
   - JSON conditions model: `{"location_zone": "office", "time_period": "work_hours"}` — simple equality matching, all conditions must match (AND logic)

2. **Alembic migration 019** — `context_rules` table

3. **`RulesEngine` class** (`backend/app/context/rules_engine.py`)
   - `evaluate(user_id, context_data) → Optional[str]` — returns persona_id if a rule matches
   - Loads enabled rules for user, sorted by priority descending
   - First-match wins (highest priority)
   - Condition matching: each key in conditions dict must equal the corresponding context field
   - Returns `None` if no rule matches or if matched persona is already active

4. **Rules API router** (`backend/app/context/rules_router.py`)
   - `GET /api/context/rules` — list user's rules
   - `POST /api/context/rules` — create rule
   - `PUT /api/context/rules/{id}` — update rule
   - `DELETE /api/context/rules/{id}` — delete rule
   - `POST /api/context/rules/test` — evaluate rules against current context, return match result

5. **Integration hook** in context router — after `broadcast.publish()` in `update_context()`, call `rules_engine.evaluate()` and if a persona switch is needed, call `persona_service.activate()` then broadcast a `persona_switched` SSE event

**Frontend:**
6. **Settings UI panel** — "Context Rules" category in settings page
   - List existing rules (htmx-loaded)
   - Create/edit form: rule name, condition fields (dropdowns for location_zone/activity/time_period + checkbox for calendar_busy), target persona (dropdown populated from `/api/personas`), priority, enabled toggle
   - Delete button with confirmation
   - "Test against current context" button

7. **Auto-switch handler** in `context-indicator.js` — listen for `persona_switched` SSE event, call exposed `switchPersona(id)` to apply in workspace
   - Requires exposing `switchPersona` on `window` in workspace.js

### Architecture Decisions

**Rule condition model: JSON dict with AND semantics**
- Each condition is a field-name→value pair. All conditions must match for the rule to fire.
- This covers the roadmap's stated use case: "at office during work hours → Work persona" = `{"location_zone": "office", "time_period": "work_hours"}`
- OR logic and complex expressions are out of scope. If needed later, the JSON structure can evolve.
- `null`/missing fields in conditions are ignored (not matched against)

**First-match-wins with priority ordering**
- Rules are evaluated in `priority` descending order. First match returns.
- This gives users predictable control — higher priority rules override lower ones.
- If no rule matches, no persona switch occurs (status quo preserved).

**Manual override suppression**
- The boundary map specifies: "Manual persona switch takes priority until next context change"
- Implementation: when the user manually switches persona, set a flag on the context row (e.g., `manual_override: true`). When context next changes (new POST /api/context/update), clear the flag and re-evaluate rules.
- Simplest approach: add `manual_override` boolean to `user_context` table (migration 019 can add this column too).

**SSE event for persona switch**
- New event type `persona_switched` on the existing context SSE stream (`/api/context/stream`)
- Data: `{"persona_id": "...", "persona_name": "...", "rule_name": "..."}`
- The context-indicator.js already has EventSource on this stream — add a handler for this event type

### Integration Hook: Where Rule Evaluation Runs

The cleanest hook is inside `update_context()` in `backend/app/context/router.py`, immediately after the `broadcast.publish()` call. This is synchronous with the request — the mobile app POSTs context, the router evaluates rules, and if a switch happens, the SSE event goes out in the same request cycle.

Alternative: subscribe to ContextBroadcast from RulesEngine. This decouples the evaluation from the HTTP request but adds complexity (subscriber lifecycle, error handling). The synchronous approach is simpler and sufficient — rule evaluation is fast (one DB query + in-memory matching).

### Settings UI Pattern

The settings page uses hardcoded category buttons in the sidebar and corresponding panel divs. Adding "Context Rules" means:
1. Add a `<button>` to `settings_page.html` sidebar
2. Add a `<div class="settings-category-panel">` with `hx-get="/browser/context/rules"` `hx-trigger="load"` for lazy loading
3. Create a `_context_rules.html` template partial with rule list + create/edit form
4. Add browser routes in a new file or extend the context router

The IndieAuth pattern (`_indieauth_settings.html`) is the closest precedent — htmx loads content on demand into a settings panel div.

### Key Risks

1. **Race condition on rapid context updates**: Two quick POSTs could both evaluate rules. The persona service's `activate()` uses SELECT→UPDATE in a transaction, so the worst case is two sequential activations — the last one wins. This is acceptable.

2. **Stale context in rule evaluation**: If context is stale (`is_stale: true`), should rules still fire? Probably not — stale context means the mobile app hasn't reported in, so the last-known context may no longer be accurate. The rules engine should skip evaluation when context is stale. But the `update_context()` endpoint is the write path — context is never stale at write time (we just wrote it). Staleness only matters for the `/test` endpoint.

3. **No personas exist**: If the user has no personas, rule evaluation is a no-op. The rules engine should handle this gracefully.

### File Organization

All new backend code goes in `backend/app/context/`:
- `rules_models.py` — ContextRule SQLAlchemy model
- `rules_engine.py` — RulesEngine class
- `rules_router.py` — CRUD + test API endpoints
- Templates: `backend/app/templates/browser/_context_rules.html`
- Migration: `backend/migrations/versions/019_context_rules.py`
- Tests: `backend/tests/test_rules_engine.py`, `backend/tests/test_rules_router.py`

Frontend:
- Modify `frontend/static/js/context-indicator.js` — add persona_switched handler
- Modify `frontend/static/js/workspace.js` — expose `switchPersona` on window
- Modify `backend/app/templates/browser/settings_page.html` — add Context Rules category
- New CSS in `frontend/static/css/settings.css` — rule builder styles (or inline in template)

### Existing Test Patterns

S01 established the test pattern for context:
- In-memory SQLite engine via `create_async_engine("sqlite+aiosqlite://")` 
- `Base.metadata.create_all` for table creation
- `async_sessionmaker` fixtures
- Class-based test organization (`TestContextServiceUpdate`, etc.)

The rules engine tests follow the same pattern. The router tests use `httpx.AsyncClient` with the FastAPI `TestClient` equivalent.

### Verification Strategy

1. **Unit tests**: RulesEngine.evaluate() with various condition combos, priority ordering, no-match cases, disabled rules
2. **Router tests**: CRUD endpoints, test endpoint, auth enforcement
3. **Integration**: POST context update → verify persona_switched SSE event emitted (mock broadcast subscriber)
4. **Browser verification**: Settings UI CRUD, test button, auto-switch visible on context change
