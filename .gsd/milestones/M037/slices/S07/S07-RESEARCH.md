# S07 Research: End-to-End Integration & Acceptance

## Summary

S07 is the final slice — no new technology, no new infrastructure. It produces two things: (1) a backend integration test proving the full context→rules→persona→notification loop in a single test file, and (2) a user guide chapter documenting the mobile app and context system. Both are straightforward applications of established patterns.

**Calibration: Light research.** All components exist and are individually tested (176 tests across S01–S06). The work is wiring verification and documentation.

## Recommendation

Two tasks:

1. **Backend integration test** (`backend/tests/test_context_integration.py`) — a pytest file that wires ContextService, RulesEngine, PersonaService, NotificationService, and ContextBroadcast together using real (in-memory SQLite) database sessions rather than mocks. Proves: context update → rule evaluation → persona switch → SSE event → notification dispatch/suppression. This is the only gap — individual slices tested each component in isolation but never the cross-component flow.

2. **User guide chapter** (`docs/guide/48-mobile-app-context.md`) + updates to all three guide index files (README.md, index.html, guide.html). Covers: mobile app installation, onboarding, zone configuration, context dashboard, context rules, auto-persona switching, push notification preferences, workspace context indicator.

## Implementation Landscape

### Integration Test — What Needs Proving

The context router (`backend/app/context/router.py`) is the integration hub. Its `update_context()` function already chains:
1. `ContextService.update()` → persist context
2. `ContextBroadcast.publish()` → SSE event
3. `RulesEngine.evaluate()` → rule match
4. `PersonaService.activate()` → persona switch
5. `ContextBroadcast.publish()` → `persona_switched` SSE event
6. `NotificationService.send_to_user()` → push notification (fire-and-forget)

Individual slice tests mock adjacent services. The integration test should use the real FastAPI app with real service instances (backed by in-memory SQLite) to prove:

- **Full loop:** POST context update with `location_zone=office` → rule matches → persona switches → `persona_switched` SSE event emitted → notification dispatched
- **Suppression:** POST context update with `calendar_busy=true` → notification suppressed
- **Staleness:** Context older than TTL returns `is_stale=true` from `GET /current`
- **No-match:** POST context that doesn't match any rule → no persona switch, no error

### Existing Test Pattern

All 8 existing test files use `httpx.AsyncClient` with `FastAPI()` test apps and dependency overrides. The integration test should follow the same pattern but wire real services instead of mocks:

```python
# Pattern from test_context_router.py:
app = FastAPI()
app.state.rules_engine = RulesEngine(session_factory)  # real, not mock
app.state.persona_service = PersonaService(session_factory)  # real
app.state.notification_service = notification_service  # mock FCM only
app.state.context_broadcast = ContextBroadcast()  # real
```

Firebase dispatch should be mocked (no real FCM in tests), but `should_suppress()` logic should use real service with real preferences in the database.

### Test Count Estimate

~8-12 tests covering:
- Full context→persona→notification loop (happy path)
- Rule priority ordering (higher priority rule wins)
- Notification suppression via quiet hours
- Notification suppression via calendar_busy
- Context staleness via TTL
- No-rule-match (context update succeeds, no persona change)
- Manual override flag (if wired — currently deferred per S02)
- Multiple context updates (second update with same zone = no redundant switch)

### User Guide — Scope

Next chapter number: **48**. File: `docs/guide/48-mobile-app-context.md`.

Per KNOWLEDGE.md "User guide has THREE files that must stay in sync":
1. `docs/guide/README.md` — add `48. [Mobile App & Context](48-mobile-app-context.md)` to the table of contents
2. `docs/guide/index.html` — add `<li><a href="#" data-file="48-mobile-app-context.md">48. Mobile App & Context</a></li>` in the appropriate section
3. `backend/app/templates/guide.html` — add a `<button class="docs-chapter-item" hx-get="/guide/48-mobile-app-context.md" ...>` entry

The chapter should cover:
- Mobile app overview (what it does, what it doesn't — it's a context provider, not a full client)
- Installation (Expo dev build, TestFlight)
- Onboarding (instance URL + API key)
- Zone configuration (map interface, geofence limits)
- Context dashboard (server vs device display)
- Auto-persona rules (Settings UI → Context Rules)
- Push notification preferences (quiet hours, suppress when busy)
- Workspace context indicator (sidebar chip, SSE-driven)
- Troubleshooting (stale context, permission revocation, offline behavior)

### Existing Guide Pattern

Chapter 33 (Context Overlay, 257 lines) is a good length/style reference — feature overview, setup steps, usage walkthrough, troubleshooting. Chapter 30 (Workspace Personas) covers the persona system that context rules build on.

### File Inventory — What Gets Created/Modified

**New files:**
- `backend/tests/test_context_integration.py` — integration test (~200-300 lines)
- `docs/guide/48-mobile-app-context.md` — user guide chapter (~200-300 lines)

**Modified files:**
- `docs/guide/README.md` — add chapter 48 to ToC
- `docs/guide/index.html` — add chapter 48 sidebar link
- `backend/app/templates/guide.html` — add chapter 48 button

### Task Seams

The two deliverables are completely independent — integration test touches only `backend/tests/`, guide chapter touches only `docs/` and one template. They can be parallel tasks or sequential in either order.

**T01: Integration test** — backend-only, can run `cd backend && python -m pytest tests/test_context_integration.py -v` to verify. Needs real SQLAlchemy session factory setup (pattern exists in other test files that create in-memory SQLite databases).

**T02: User guide chapter + index updates** — docs-only, verification is confirming the file exists and all three index files reference chapter 48.

### Verification

- All 176+ existing tests still pass (regression)
- New integration tests pass
- `docs/guide/48-mobile-app-context.md` exists with substantive content
- All three guide indexes reference chapter 48: `grep '48-mobile' docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html`

### Risks

None meaningful. The integration test is the only piece with any complexity — it needs to set up a real database with users, personas, rules, and notification preferences, then drive the context update endpoint. The pattern for this exists across the test suite.
