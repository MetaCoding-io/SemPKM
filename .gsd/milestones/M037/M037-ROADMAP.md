# M037: User Context & Mobile App

**Vision:** SemPKM gains awareness of the user's real-world context — location, activity, time-of-day, calendar — via a React Native mobile app. The backend stores ephemeral context state, evaluates rules to auto-switch workspace personas, streams context to the workspace UI, and dispatches context-filtered push notifications. This is the first mobile surface for SemPKM and the foundation for all context-aware features.

## Success Criteria

- User can push context updates to the backend via API (location zone, activity, time period, calendar event) and see them reflected in the workspace sidebar within seconds
- Workspace persona automatically switches when context matches a configured rule (e.g., arriving at "office" during work hours activates "Work" persona)
- Context that hasn't been updated within the TTL window (default 15 min) is displayed as "Unknown" in the workspace
- Mobile app (iOS + Android) connects to a SemPKM instance via API key, monitors geofence zones, and pushes context updates on zone enter/exit
- Mobile app reads device calendar and detects activity type (stationary/walking/driving)
- Push notifications are dispatched via FCM and suppressed when context rules indicate quiet periods (e.g., focus blocks, outside work hours)
- Context rules are manageable through the SemPKM settings UI (create, edit, delete, test)

## Key Risks / Unknowns

- **React Native build chain (HIGH)** — Zero React Native/Expo experience in this project. Metro bundler, native compilation, and EAS Build are entirely new. The simplest possible app must prove connectivity before adding native features.
- **iOS background location permission (HIGH)** — Apple requires "Always Allow" location for geofencing, with heavy App Store review scrutiny. Geofencing (region monitoring) is the review-friendly approach, but permission flow UX must be compelling.
- **Android background restrictions (MEDIUM)** — Android 12+ requires a foreground service notification for persistent location monitoring. The geofencing API via expo-location handles this, but the visible notification is mandatory.
- **Context staleness (MEDIUM)** — If the mobile app loses connectivity or is killed by the OS, context becomes stale. TTL mechanism and graceful degradation to "Unknown" must work reliably.
- **Push notification infrastructure (MEDIUM)** — Firebase project setup, service account credentials, FCM/APNs routing. Entirely new infrastructure with no existing pattern in the codebase.

## Proof Strategy

- React Native build chain → retire in S03 by shipping a real mobile app that connects to the SemPKM API, displays current context, and proves the Expo build pipeline works
- iOS/Android background location → retire in S04 by registering geofences that trigger context updates when the user enters/exits a zone on a real device
- Context staleness → retire in S01 by implementing TTL-based staleness detection that marks context as "Unknown" when stale, verified via timed test
- Push infrastructure → retire in S06 by dispatching a real FCM notification from the backend to a registered mobile device

## Verification Classes

- Contract verification: pytest unit tests for ContextService, RulesEngine, NotificationService; API endpoint tests via httpx TestClient; Alembic migration up/down
- Integration verification: curl/httpx posting context → SSE stream delivering update to browser EventSource; rule match → PersonaService.activate() call; mobile app → API → workspace indicator chain
- Operational verification: context TTL expiry marking stale; mobile app backgrounding and reconnection; push notification delivery latency
- UAT / human verification: persona auto-switch visible in workspace within 60s of geofence trigger; mobile app onboarding flow; settings UI rule management; context indicator readability

## Milestone Definition of Done

This milestone is complete only when all are true:

- Backend Context API stores and streams context with TTL-based staleness
- Auto-persona rules engine evaluates context changes and triggers PersonaService.activate()
- Settings UI provides full CRUD for context rules with test-against-current-context
- Mobile app (Expo/React Native) connects via API key, monitors geofences, reads calendar, detects activity
- Mobile geofence enter/exit triggers context update → rule evaluation → persona switch visible in workspace
- Push notifications dispatch via FCM with context-aware filtering (suppress during focus blocks)
- Workspace sidebar context indicator shows real-time context via SSE
- Final integration test proves the full loop: mobile geofence trigger → backend context → persona switch → workspace update

## Requirement Coverage

- Covers: CTX-01, CTX-02, CTX-03, CTX-04, CTX-05, CTX-06, CTX-07, CTX-08, CTX-09, CTX-10, CTX-11, CTX-12, CTX-13
- Partially covers: CTX-14 (zone config via map — text-based lat/lon entry as fallback if map library proves too complex)
- Leaves for later: CTX-15 (offline queue with retry — best-effort in S04, full resilience deferred), CTX-16 (multi-device — last-reporting device wins, but no conflict resolution UI), CTX-19 (version checking)
- Orphan risks: CTX-17 (rate limiting — lightweight per-user throttle in S01, not a full rate-limiting system), CTX-18 (context deletion on account removal — handled via CASCADE FK, no separate work)

## Slices

- [x] **S01: Backend Context API & Workspace Indicator** `risk:high` `depends:[]`
  > After this: user can POST context updates via API, see them in real-time in the workspace sidebar via SSE, and stale context (>15 min) shows as "Unknown" — all verified in the running Docker stack

- [x] **S02: Auto-Persona Rules Engine & Settings UI** `risk:high` `depends:[S01]`
  > After this: user can create context→persona rules in the Settings UI, POST a context update that matches a rule, and watch the workspace persona switch automatically — verified in the browser

- [x] **S03: Mobile App Foundation & API Connection** `risk:high` `depends:[S01]`
  > After this: user can install the Expo dev build on a phone, enter their SemPKM instance URL and API key, and see their current context state displayed in the mobile app — verified on a real device or simulator

- [x] **S04: Mobile Geofencing & Location Zones** `risk:high` `depends:[S03]`
  > After this: user can define home/office geofence zones in the mobile app, and entering or leaving a zone pushes a context update to the backend — verified by observing the workspace context indicator change after a simulated or real zone transition

- [x] **S05: Mobile Calendar & Activity Detection** `risk:medium` `depends:[S03]`
  > After this: mobile app reads the device calendar and detects activity type (stationary/walking/driving), enriching context updates with calendar event name and activity — verified by checking context API response after calendar event starts

- [ ] **S06: Push Notifications with Context Filtering** `risk:medium` `depends:[S01,S02]`
  > After this: backend dispatches push notifications to registered mobile devices via FCM, suppressing notifications during configured quiet periods (focus blocks, outside work hours) — verified by receiving a test notification on the mobile device

- [ ] **S07: End-to-End Integration & Acceptance** `risk:low` `depends:[S01,S02,S03,S04,S05,S06]`
  > After this: the full loop is proven on real hardware — user installs mobile app, configures zones, arrives at office geofence, workspace persona switches within 60 seconds, calendar focus block suppresses notifications, and workspace sidebar shows "Office • Work Hours • Focus Block"

## Boundary Map

### S01 (Context API & Indicator)

Produces:
- `POST /api/context/update` — accepts JSON context snapshot (location_zone, activity, time_period, calendar_event, calendar_busy, device_id), stores in SQLite `user_context` table
- `GET /api/context/current` — returns current context with `is_stale` flag based on configurable TTL
- `GET /api/context/stream` — SSE stream pushing `context_update` and `context_stale` events via `ContextBroadcast` (same fan-out pattern as `LintBroadcast`)
- `ContextService` registered as `app.state.context_service` — used by rules engine (S02) and notification service (S06)
- `ContextBroadcast` registered as `app.state.context_broadcast` — used by SSE endpoint and rules engine
- Alembic migration 018 creating `user_context` table with FK to `users.id`
- Workspace sidebar context indicator element consuming `EventSource('/api/context/stream')`
- Per-user rate throttle on context update endpoint (max 1 update per 5 seconds)

Consumes:
- `get_current_user_or_api` dual-auth from `backend/app/auth/dependencies.py`
- `LintBroadcast` pattern from `backend/app/lint/broadcast.py`
- `app.state.*` registration pattern from `backend/app/main.py` lifespan

### S01 → S02

Produces:
- `ContextService.get_current(user_id)` method returning current context dict
- `ContextBroadcast.publish()` called on every context update — S02 hooks rule evaluation here

### S02 (Rules Engine & Settings UI)

Produces:
- `context_rules` SQLite table (Alembic migration 019) with JSON conditions and persona_id action
- `RulesEngine` class with `evaluate(user_id, context) → Optional[persona_id]` — called on every context update
- `POST/GET/PUT/DELETE /api/context/rules` — CRUD endpoints for context rules
- `POST /api/context/rules/test` — test a rule against current context (returns match/no-match)
- "Context Rules" category in Settings page with rule builder UI
- SSE `persona_switched` event emitted when auto-switch triggers
- Manual override: `POST /api/personas/{id}/activate` sets override flag, suppresses auto-switch until next context change

Consumes:
- `ContextService.get_current()` from S01
- `ContextBroadcast` publish hook from S01
- `PersonaService.activate()` from `backend/app/persona/service.py`
- Settings page category pattern from `backend/app/templates/browser/settings_page.html`

### S02 → S06

Produces:
- `RulesEngine.evaluate()` return value indicating whether notifications should be suppressed (calendar_busy flag, quiet period rules)

### S03 (Mobile App Foundation)

Produces:
- `mobile/` directory with Expo project structure (app.json, package.json, tsconfig.json)
- `mobile/src/api/client.ts` — API client with Bearer token auth (mirrors extension/shared/api-client.js pattern)
- Onboarding screen: instance URL + API key input, connection test, secure storage
- Context dashboard screen: displays current context from `GET /api/context/current`
- Expo Router navigation setup with tab bar (Dashboard, Zones, Settings)

Consumes:
- `GET /api/context/current` from S01
- Bearer token auth from `backend/app/auth/dependencies.py`

### S03 → S04

Produces:
- API client instance configured with instance URL and token
- Navigation scaffold with Zones tab ready for map UI
- Secure storage of instance credentials

### S03 → S05

Produces:
- API client for `POST /api/context/update`
- Context update dispatch function that S05 calendar/activity services call

### S04 (Geofencing & Location Zones)

Produces:
- Zone configuration screen with map (react-native-maps) for placing circular geofences
- `expo-location` `startGeofencingAsync` registration for configured zones
- `expo-task-manager` `TaskManager.defineTask` background task that calls `POST /api/context/update` on zone enter/exit
- Zone CRUD API: `POST/GET/PUT/DELETE /api/context/zones` — stores zone definitions server-side per user
- Alembic migration 020 for `context_zones` table (name, lat, lon, radius, user_id)

Consumes:
- API client from S03
- `POST /api/context/update` from S01
- Background location permissions (iOS "Always Allow", Android foreground service)

### S05 (Calendar & Activity)

Produces:
- `expo-calendar` integration reading current/upcoming events from device calendar
- Activity detection via `expo-sensors` (Accelerometer) classifying stationary/walking/driving
- Time-of-day classification (morning/work_hours/evening/night with configurable boundaries)
- Context update enrichment: calendar_event, calendar_busy, activity, time_period fields

Consumes:
- Context update dispatch function from S03
- `POST /api/context/update` from S01

### S06 (Push Notifications)

Produces:
- `device_tokens` SQLite table (Alembic migration 021) storing FCM tokens per user per device
- `POST /api/notifications/register` — device token registration endpoint
- `NotificationService` using `firebase-admin` Python SDK for FCM dispatch
- `notification_preferences` per-user settings (which notification types, quiet hours)
- Context-aware filtering: suppress notifications when calendar_busy=true or outside configured work hours
- Mobile app notification handler via `expo-notifications`

Consumes:
- `ContextService.get_current()` from S01 for filtering decisions
- `RulesEngine` quiet-period evaluation from S02
- `firebase-admin` service account credentials (see SECRETS manifest)
- `expo-notifications` `getDevicePushTokenAsync()` for native FCM token

### S07 (Integration & Acceptance)

Produces:
- Integration test script exercising the full loop: geofence trigger → context update → rule evaluation → persona switch → workspace indicator update → notification filtering
- Updated user guide chapter documenting context setup, mobile app installation, zone configuration, and rule management

Consumes:
- All of S01–S06 running together in Docker Compose + mobile app on device/simulator
