# S07: End-to-End Integration & Acceptance

**Goal:** Prove the full context→rules→persona→notification loop in a single integration test, and document the mobile app + context system in a user guide chapter.
**Demo:** `cd backend && python -m pytest tests/test_context_integration.py -v` passes 8+ tests exercising real cross-service wiring. `docs/guide/48-mobile-app-context.md` exists and all three guide indexes reference chapter 48.

## Must-Haves

- Integration test using real services (not mocks) backed by in-memory SQLite — proving context update → rule evaluation → persona switch → SSE event → notification dispatch/suppression in a single test file
- Notification suppression tests covering quiet hours and calendar_busy
- Context staleness test via TTL
- No-rule-match test (context update succeeds without persona change)
- User guide chapter 48 covering mobile app installation, onboarding, zone config, context dashboard, rules, notifications, workspace indicator, and troubleshooting
- All three guide index files updated (README.md, index.html, guide.html)
- All 176+ existing tests still pass (regression)

## Proof Level

- This slice proves: final-assembly
- Real runtime required: no (in-memory SQLite)
- Human/UAT required: no (full device loop is UAT — this proves the backend integration programmatically)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py -v` — 8+ tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py tests/test_rules_engine.py tests/test_rules_router.py tests/test_zone_service.py tests/test_zone_router.py tests/test_notification_service.py tests/test_notification_router.py -v` — all 176 existing tests still pass
- `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py -v -k "diagnostic" 2>&1 | grep -q "PASSED"` — diagnostic/failure-path tests exercise error-handling branches (rule eval failure and notification dispatch failure are logged, not raised)
- `test -f docs/guide/48-mobile-app-context.md` — guide chapter exists
- `grep -q '48-mobile-app-context' docs/guide/README.md && grep -q '48-mobile-app-context' docs/guide/index.html && grep -q '48-mobile-app-context' backend/app/templates/guide.html` — all three indexes reference chapter 48

## Observability / Diagnostics

- Runtime signals: structured logs from ContextService, RulesEngine, PersonaService, and NotificationService are exercised in integration tests — log assertions confirm the chain fires
- Inspection surfaces: `POST /api/notifications/test` endpoint serves as the diagnostic surface for push delivery; `POST /api/context/rules/test` for rule evaluation
- Failure visibility: integration test failures will show which step in the chain broke (context persist, rule eval, persona switch, notification dispatch, or suppression)

## Integration Closure

- Upstream surfaces consumed: `ContextService` (S01), `ContextBroadcast` (S01), `RulesEngine` (S02), `PersonaService` (existing), `NotificationService` (S06), context router integration hook (S02+S06)
- New wiring introduced in this slice: none — integration test exercises existing wiring
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Backend integration test proving cross-service context loop** `est:45m`
  - Why: Individual slice tests mock adjacent services. The full chain — context update → rule evaluation → persona switch → SSE event → notification dispatch/suppression — has never been tested with real service instances wired together. This is the only remaining verification gap.
  - Files: `backend/tests/test_context_integration.py`
  - Do: Create integration test file using real `ContextService`, `RulesEngine`, `PersonaService`, `NotificationService` (with mock FCM only), and `ContextBroadcast` backed by in-memory SQLite. Wire into a FastAPI test app following the existing `httpx.AsyncClient` pattern. Test cases: (1) full loop — POST context with location_zone matching a rule → persona switches → persona_switched SSE event emitted → notification dispatched, (2) notification suppression via calendar_busy, (3) notification suppression via quiet hours, (4) context staleness via TTL, (5) no-rule-match — context updates without persona change, (6) multiple updates — second update with same zone skips redundant switch, (7) rule priority ordering — higher priority wins, (8) notification suppression when master toggle disabled.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py -v` — 8+ tests pass. Then run all existing context/rules/notification tests to confirm no regression.
  - Done when: integration test passes with 8+ test cases covering the full loop, suppression, staleness, and edge cases; all 176+ existing tests still pass.

- [ ] **T02: User guide chapter 48 and index updates** `est:30m`
  - Why: The mobile app and context system need user-facing documentation. Three index files must stay in sync per KNOWLEDGE.md rule.
  - Files: `docs/guide/48-mobile-app-context.md`, `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`
  - Do: Write chapter 48 covering: overview (mobile app as context provider, not full client), installation (Expo dev build), onboarding (instance URL + API key), zone configuration (map interface, geofence limits), context dashboard, auto-persona rules (Settings UI), push notification preferences (quiet hours, suppress when busy), workspace context indicator (sidebar chip), and troubleshooting (stale context, permission revocation, offline behavior). Follow the style of chapter 33 (Context Overlay) — feature overview, setup steps, usage walkthrough, troubleshooting. Add chapter 48 entry to all three guide indexes: README.md ToC line, index.html sidebar `<li>`, guide.html `<button>` with smartphone icon.
  - Verify: `test -f docs/guide/48-mobile-app-context.md && grep -q '48-mobile-app-context' docs/guide/README.md && grep -q '48-mobile-app-context' docs/guide/index.html && grep -q '48-mobile-app-context' backend/app/templates/guide.html`
  - Done when: chapter 48 exists with substantive content (200+ lines), all three index files reference it.

## Files Likely Touched

- `backend/tests/test_context_integration.py` (new)
- `docs/guide/48-mobile-app-context.md` (new)
- `docs/guide/README.md` (modified)
- `docs/guide/index.html` (modified)
- `backend/app/templates/guide.html` (modified)
