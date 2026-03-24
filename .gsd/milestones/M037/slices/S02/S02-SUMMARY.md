---
id: S02
milestone: M037
title: "Auto-Persona Rules Engine & Settings UI"
status: complete
started: 2026-03-23
completed: 2026-03-24
tasks_completed: 4
tasks_total: 4
test_count: 45
test_pass: 45
---

# S02: Auto-Persona Rules Engine & Settings UI — Summary

**Delivered:** Context-aware auto-persona switching works end-to-end. Users create rules in the Settings UI mapping context conditions (location, activity, time period, calendar busy) to workspace personas. When a context update matches a rule, the backend activates the target persona and pushes a `persona_switched` SSE event — the workspace UI switches and shows a toast notification within seconds.

## What Was Built

### T01: ContextRule Model, Migration & RulesEngine Service
- `ContextRule` SQLAlchemy model with UUID PK, user_id FK, name, priority, JSON conditions, persona_id, enabled flag, timestamps
- Alembic migration 019: `context_rules` table + `manual_override` boolean column on `user_context`
- `RulesEngine` class with `evaluate(user_id, context_data) → Optional[str]` — loads enabled rules sorted by priority DESC / created_at ASC, first-match-wins with AND condition matching
- CRUD methods (create, list, get, update, delete) all scoped by user_id for authorization
- 19 unit tests covering priority ordering, AND conditions, disabled rules, empty/null conditions, tiebreakers, and CRUD authorization

### T02: Rules CRUD API Router & Integration Hook
- 5-endpoint API at `/api/context/rules`: GET (list), POST (create, 201), PUT (update), DELETE (204), POST /test (read-only evaluation)
- Integration hook in `update_context()`: after context broadcast → evaluate rules → compare with active persona → activate if different → broadcast `persona_switched` SSE event
- Rule evaluation errors are caught and logged — never break the context update response
- Redundant persona switches skipped by comparing active persona ID before calling activate()
- `get_rules_engine` and `get_persona_service` dependency functions added to `dependencies.py`
- RulesEngine registered on `app.state.rules_engine` during lifespan startup
- 26 router tests covering CRUD, test endpoint, auth enforcement, and integration hook

### T03: Settings UI — Context Rules Category
- "Context Rules" sidebar button with brain icon in `settings_page.html`
- `_context_rules.html` template partial: rule list with cards (name, persona badge, priority, condition tags, enable toggle, edit/delete), inline edit form per card, collapsible "New Rule" section, "Test against current context" button
- Browser route `GET /browser/settings/context-rules` serving the partial via `settings.py`
- JS fetch() for API mutations + htmx.ajax() reload pattern (JSON API returns JSON, not HTML fragments)
- ~180 lines of CSS: rule cards, condition tags, inline forms, test result badges

### T04: Frontend SSE Handler & Toast Notification
- `persona_switched` event listener on the existing EventSource in `context-indicator.js`
- Calls `window.switchPersona(persona_id)` on the workspace layout API
- Toast notification appended to `document.body` (escapes dockview stacking context) with 3-second auto-dismiss + CSS fade-out animation
- Graceful fallback: logs console warning if `switchPersona` is undefined; catches JSON parse errors

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| `tests/test_rules_engine.py` | 19 | ✅ All pass |
| `tests/test_rules_router.py` | 26 | ✅ All pass |
| **Total** | **45** | **✅ All pass** |

## Key Decisions

- **D343** (planning): AND-condition JSON dict, first-match-wins by priority — implemented as planned
- **D344** (planning): Synchronous rule evaluation in request handler — implemented as planned
- **Rule errors never break context update:** Integration hook wrapped in try/except. Persona switching is best-effort, not a gate on context persistence.
- **JS fetch() + htmx reload for Settings panels:** JSON API endpoints return JSON, so htmx `hx-post` alone can't handle the round-trip. After successful mutation, `htmx.ajax('GET', ...)` reloads the panel.
- **Toast on document.body:** Dockview panel stacking context traps z-index. Body-appended fixed-position toast is the standard escape pattern (consistent with D293).

## Integration Seams

**Upstream consumed (from S01):**
- `ContextService.get_current()` — used by test endpoint
- `ContextBroadcast.publish()` — used to emit `persona_switched` SSE events
- `EventSource('/api/context/stream')` — used to receive `persona_switched` events

**New wiring introduced:**
- `app.state.rules_engine` — RulesEngine registered in main.py lifespan
- `app.state.persona_service` — accessed via request.app.state in integration hook
- `context_rules_router` — mounted in main.py after context router
- `GET /browser/settings/context-rules` — browser route for Settings UI partial

**Downstream for S06:**
- `RulesEngine.evaluate()` return value can indicate notification suppression via `calendar_busy` context field

## Observability

- `context.rule_matched` structured log (user_id, rule_name, persona_id) on every match
- `context.no_rule_matched` structured log (user_id) when no rule fires
- `context.persona_switched` structured log (user_id, persona_id, persona_name) on auto-switch
- `context.rule_evaluation_failed` error log with traceback on evaluation errors
- `context.rule_created/updated/deleted` CRUD audit logs
- `GET /api/context/rules` — list all rules (inspection surface)
- `POST /api/context/rules/test` — evaluate against current context, read-only (diagnostic surface)
- `persona_switched` SSE event with persona_id, persona_name, rule_name fields
- Console: `[context-indicator] window.switchPersona not available` when workspace.js hasn't loaded
- Console: `[context-indicator] persona_switched parse error` when SSE payload is malformed

## Known Issues

1. **rule_name "auto" in SSE event:** The integration hook hardcodes `rule_name: "auto"` instead of passing the matched rule's actual name. The frontend correctly displays the rule name when provided but suppresses the generic "auto" label. Low-priority cosmetic fix — the actual rule name is logged server-side.
2. **manual_override deferred:** Migration 019 adds the `manual_override` column, but no read/write logic exists yet. Manual persona switch → suppress auto-switch → clear on next context update is the intended flow. Can be wired when needed.
3. **DELETE fetch abort in browser:** The DELETE fetch shows `net::ERR_ABORTED` in Playwright network logs because the panel reload aborts the in-flight request. The delete actually succeeds (HTTP 204) before the abort.

## Files Created/Modified

**New files:**
- `backend/app/context/rules_models.py` — ContextRule SQLAlchemy model
- `backend/app/context/rules_engine.py` — RulesEngine service (evaluate + CRUD)
- `backend/app/context/rules_router.py` — CRUD + test API router (5 endpoints)
- `backend/migrations/versions/019_context_rules.py` — context_rules table + manual_override column
- `backend/tests/test_rules_engine.py` — 19 unit tests
- `backend/tests/test_rules_router.py` — 26 router tests
- `backend/app/templates/browser/_context_rules.html` — Settings UI partial

**Modified files:**
- `backend/app/context/router.py` — integration hook for auto-persona switching
- `backend/app/dependencies.py` — get_rules_engine, get_persona_service
- `backend/app/main.py` — RulesEngine registration, router mount
- `backend/app/browser/settings.py` — context_rules_panel route
- `backend/app/templates/browser/settings_page.html` — Context Rules sidebar button + panel
- `frontend/static/css/settings.css` — rule card styles
- `frontend/static/js/context-indicator.js` — persona_switched handler + toast
- `frontend/static/css/context-indicator.css` — toast styles
