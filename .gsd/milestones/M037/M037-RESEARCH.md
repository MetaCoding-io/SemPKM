# M037 Research: User Context & Mobile App

## Executive Summary

M037 introduces React Native (via Expo) as an entirely new platform surface, a backend Context API, automatic persona switching, and push notification infrastructure. This is the largest technology-introduction milestone since the project's inception — every prior milestone used Python + vanilla JS. The research identifies Expo (managed workflow with development builds) as the recommended framework, `firebase-admin` Python SDK for server-side push, and a careful slice ordering that proves the backend context loop before touching mobile native APIs.

**Key finding:** The Expo SDK has first-class `startGeofencingAsync` and `TaskManager.defineTask` for background geofencing — this works in the managed workflow with development builds (not Expo Go). No need to eject to bare React Native. This simplifies the build chain significantly.

**Key risk:** iOS background location requires "Always Allow" permission, which Apple App Store review scrutinizes heavily. Geofencing (region monitoring) is the battery-friendly approach Apple prefers over continuous GPS — the context doc gets this right.

---

## Codebase Exploration

### Persona System (M012) — Integration Point

**Files:** `backend/app/persona/service.py`, `backend/app/persona/router.py`, `backend/app/persona/models.py`

The PersonaService has a clean `activate(persona_id, user_id)` method that:
1. Verifies persona exists and belongs to user
2. Deactivates all user's personas
3. Activates the target
4. Returns PersonaData

This is the exact hook for context-driven auto-switching. The context rule engine calls `PersonaService.activate()` when a rule match changes.

**Important constraint:** The activate method is async and requires a SQLAlchemy session. The rule engine must run within an async context (which is natural for FastAPI background tasks or SSE event handlers).

**Persona model fields:** `id, user_id, name, layout_json, sidebar_positions_json, explorer_mode, is_active, created_at, updated_at`. No context metadata — the mapping from context→persona lives in a separate rules table.

### Authentication — Mobile App Access

**File:** `backend/app/auth/dependencies.py`

`get_current_user_or_api()` already supports dual auth: session cookie (browser) OR Bearer token (API). The mobile app authenticates the same way as the browser extension — via Bearer token from `ApiToken` table. No new auth work needed.

The extension's `shared/api-client.js` shows the pattern: store instance URL + API key, use `Authorization: Bearer {key}` header on every request. The mobile app needs an equivalent in React Native (trivially `fetch()` with headers).

### SSE Broadcasting Pattern

**File:** `backend/app/lint/broadcast.py`

The project has a mature SSE fan-out pattern: `LintBroadcast` manages `asyncio.Queue` subscribers, publishes `SSEEvent` instances formatted as SSE wire protocol. The context stream (`GET /api/context/stream`) follows this exact pattern — a `ContextBroadcast` class with subscribe/publish.

SSE consumers in the frontend use `new EventSource('/api/lint/stream')` — the workspace context indicator uses the same approach with `new EventSource('/api/context/stream')`.

### Alembic Migrations

**Latest:** `017_ai_personas.py` (revision 017, depends on 016). Pattern is straightforward: `op.create_table()` with SQLAlchemy column types. The context tables (user_context, context_rules, device_tokens) each get their own migration file. Convention: sequential numeric revision IDs.

### App State Registration

**File:** `backend/app/main.py`

Services are registered as `app.state.{service_name}` during lifespan startup. Pattern: instantiate with `async_session_factory`, store on app state, access via `request.app.state.{name}` in routes. The ContextService and NotificationService follow this pattern.

### Existing Push/Notification Infrastructure

**Finding: None exists.** No FCM, no APNs, no device token storage, no notification dispatch. This is entirely new infrastructure. The webhook system (`backend/app/services/webhooks.py`) dispatches outbound HTTP POSTs to registered URLs — conceptually similar but structurally different from push notifications.

### Settings System

**Model:** `UserSetting` in `backend/app/auth/models.py` — key/value pairs per user. Context rules could be stored here as JSON, or (better) in a dedicated `context_rules` table for proper schema enforcement and querying.

---

## Technology Decisions

### Expo (Managed Workflow) vs Bare React Native

**Recommendation: Expo with development builds.**

Reasons:
- `expo-location` provides `startGeofencingAsync()` that wraps CLLocationManager (iOS) and GeofencingClient (Android) — cross-platform from a single API
- `expo-task-manager` (`TaskManager.defineTask`) handles background task registration for both platforms
- `expo-notifications` provides unified push notification API with Expo Push Token abstraction (wraps FCM + APNs)
- `expo-calendar` provides read-only calendar access
- Development builds (via EAS Build or local `npx expo prebuild`) support all native modules — no need for Expo Go
- The managed workflow with CNG (Continuous Native Generation) auto-generates native projects from `app.json` config plugins

**Concern addressed:** One third-party source claimed Expo doesn't support background geofencing. This is outdated — Expo's own documentation shows `startGeofencingAsync` with `TaskManager.defineTask` working in development builds. The limitation is Expo Go (the sandbox app), not the managed workflow itself.

**Alternative rejected:** `react-native-background-geolocation` by Transistor Software is more feature-rich but requires a paid license for Android release builds. Expo's built-in geofencing is sufficient for the 3-5 zone use case.

### Push Notification Server-Side

**Recommendation: `firebase-admin` Python SDK.**

The Firebase Admin SDK for Python handles FCM message dispatch to both Android and iOS. It requires a Firebase project + service account JSON credentials. The `messaging.send()` and `messaging.send_each()` APIs handle single and batch sends.

**Alternative:** `pyfcm` is a lighter wrapper but `firebase-admin` is Google's official SDK with better maintenance and documentation.

**Expo integration:** The mobile app uses `expo-notifications` to get either an Expo Push Token (if using Expo Push Service) or a native device push token (for direct FCM). Using Expo Push Service is simpler (abstracts FCM/APNs) but adds a dependency on Expo's servers. Direct FCM is more self-hosted-friendly.

**Recommendation: Direct FCM via `firebase-admin`.** Aligns with SemPKM's self-hosted philosophy. The mobile app calls `Notifications.getDevicePushTokenAsync()` to get the native FCM/APNs token and registers it with the SemPKM backend.

### Context Storage: SQLite (Ephemeral) Not RDF

The context doc correctly specifies SQLite for context data — not the RDF triplestore. Context is ephemeral state (current location zone, current activity, current time period), not knowledge. It doesn't belong in the knowledge graph.

**Tables needed:**
- `user_context` — current context per user (single row per user, upserted on each update)
- `context_rules` — IF/THEN rules mapping context conditions to persona activation
- `device_tokens` — FCM device tokens per user (multiple devices per user)
- `notification_preferences` — per-user notification filtering rules

### Monorepo Structure

The project currently has an empty root `package.json`. The mobile app lives in a new `mobile/` directory with its own `package.json`, `app.json`, and TypeScript config. Build tooling (Metro bundler) is scoped to `mobile/`.

```
mobile/
  app.json          — Expo app config
  package.json      — RN/Expo dependencies
  tsconfig.json     — TypeScript config
  src/
    api/            — API client (mirrors extension/shared/api-client.js)
    screens/        — React Native screens
    services/       — Location, notifications, calendar
    context/        — React context providers
  app/              — Expo Router file-based routing
```

---

## Risk Analysis

### 1. iOS Background Location Permission (HIGH)

iOS requires "Always Allow" location for geofencing. Apple's App Store review process scrutinizes this heavily — apps must demonstrate a clear user-facing reason. Apple's guidelines specifically call out geofencing as an acceptable use case, but the justification in the App Store submission must be compelling.

**Mitigation:** Build geofencing with clear user benefit messaging. The permission dialog must explain: "SemPKM uses your location to automatically switch your workspace when you arrive at or leave configured zones like your office or home." The `app.json` config plugin sets `NSLocationAlwaysAndWhenInUseUsageDescription`.

**Note:** App Store submission is explicitly out of scope for M037 (TestFlight/internal distribution first). This buys time to refine the permission flow.

### 2. React Native Build Chain (HIGH)

This project has zero React Native experience. The build chain (Metro, Babel, native compilation, EAS Build) is entirely new. Debugging native module issues requires understanding iOS/Android build systems.

**Mitigation:** Use Expo's managed workflow to minimize native config. Use EAS Build for cloud compilation (avoids local Xcode/Android Studio setup requirements). Start with the simplest possible app (connect to API, display data) before adding native features.

### 3. Android Background Restrictions (MEDIUM)

Android 12+ requires a foreground service notification for persistent location monitoring. The geofencing API itself is battery-efficient, but the foreground notification is mandatory and visible to the user.

**Mitigation:** Use Android's geofencing API via `expo-location` which handles the foreground service requirement. The notification text should be informative: "SemPKM is monitoring your location zones."

### 4. Context Staleness (MEDIUM)

If the mobile app loses connectivity or is killed by the OS, the backend's context becomes stale. Without a TTL mechanism, the workspace might show "At Office" when the user left hours ago.

**Mitigation:** Context records include `updated_at` timestamp. The backend applies a configurable TTL (default 15 minutes). The workspace indicator shows "Unknown" when context is stale. The SSE stream sends periodic heartbeats and staleness events.

### 5. Push Notification Infrastructure Complexity (MEDIUM)

Firebase setup requires creating a Firebase project, configuring iOS/Android app credentials, and managing a service account JSON file on the backend. This is new operational overhead.

**Mitigation:** Make push notifications a later slice. The core value (context → auto-persona) works without push. Push is additive.

### 6. Geofence Region Limits (LOW)

iOS limits to 20 simultaneous monitored regions. Android allows 100. Most users need 3-5 zones.

**Impact:** Low — well within limits. Document the limit in the UI (show max zone count).

---

## Slice Boundary Analysis

### Natural boundaries:

1. **Backend Context API** — Pure backend, no mobile dependency. Can be tested with curl/httpx. Proves the data model, SSE streaming, and TTL mechanism. This is the foundation everything else depends on.

2. **Auto-Persona Rules Engine** — Backend-only. Depends on Context API. Evaluates rules on context update, calls PersonaService.activate(). Can be tested by POSTing fake context updates.

3. **Workspace Context Indicator** — Frontend-only (htmx/vanilla JS). Depends on Context API SSE stream. Small scope — a sidebar element that listens to EventSource and displays current context.

4. **Mobile App Foundation** — Expo project setup, onboarding flow (instance URL + API key), API client, basic context dashboard. No native features yet — just proves the app can talk to the backend.

5. **Mobile Geofencing + Location** — The core native feature. Zone configuration UI (map), geofencing registration, background task that pushes context updates on zone enter/exit.

6. **Mobile Calendar + Activity Detection** — Read device calendar for current event context. Activity detection (stationary/walking/driving) via device motion.

7. **Push Notifications** — Firebase setup, device token registration, notification dispatch from backend, context-aware filtering.

### Recommended ordering (by risk):

1. Backend Context API (proves the data model — everything depends on this)
2. Workspace Context Indicator (smallest visual proof the system works end-to-end)
3. Auto-Persona Rules Engine (the key value proposition — context drives workspace)
4. Mobile App Foundation (first React Native code — highest technology risk)
5. Mobile Geofencing (core native feature — second highest risk)
6. Mobile Calendar + Activity (lower risk — standard Expo APIs)
7. Push Notifications (most infrastructure — lowest priority, additive value)

The first three slices deliver a working context-aware workspace with no mobile app — context can be pushed via API (e.g., from a script, another tool, or manual testing). This de-risks the backend before investing in the mobile build chain.

---

## Patterns to Reuse

| Pattern | Source | Use In M037 |
|---------|--------|-------------|
| SSE fan-out broadcast | `backend/app/lint/broadcast.py` | `ContextBroadcast` for real-time context streaming |
| Service + Router + Model | `backend/app/persona/` | `backend/app/context/` module structure |
| Bearer token API auth | `backend/app/auth/dependencies.py` | Mobile app authentication |
| `app.state.{service}` registration | `backend/app/main.py` lifespan | ContextService, NotificationService |
| Alembic migration numbering | `backend/migrations/versions/017_*` | Migration 018+ for context tables |
| Extension API client pattern | `extension/shared/api-client.js` | `mobile/src/api/client.ts` |
| AppScheduler tick pattern | `backend/app/apps/scheduler.py` | Context TTL checker (periodic staleness scan) |

---

## Boundary Contracts

### Context Update API

```
POST /api/context/update
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "location_zone": "office",        // null if unknown
  "activity": "stationary",         // stationary|walking|driving|cycling|unknown
  "time_period": "work_hours",      // morning|work_hours|evening|night
  "calendar_event": "Focus Block",  // current event title, null if none
  "calendar_busy": true,            // in a meeting/focus block
  "device_id": "uuid"               // identifies the source device
}
```

### Context Read API

```
GET /api/context/current
Authorization: Bearer {api_key} OR Cookie

{
  "location_zone": "office",
  "activity": "stationary",
  "time_period": "work_hours",
  "calendar_event": "Focus Block",
  "calendar_busy": true,
  "updated_at": "2026-03-23T15:00:00Z",
  "is_stale": false,
  "active_rule": {"id": "uuid", "name": "Office Focus"}
}
```

### Context SSE Stream

```
GET /api/context/stream
Authorization: Cookie (browser)

event: context_update
data: {"location_zone":"office","activity":"stationary",...}

event: persona_switched
data: {"persona_id":"uuid","persona_name":"Work","triggered_by":"rule:uuid"}

event: context_stale
data: {"last_update":"2026-03-23T14:45:00Z","ttl_seconds":900}
```

### Rule Model

```
{
  "id": "uuid",
  "name": "Office Work Hours",
  "conditions": {
    "location_zone": "office",
    "time_period": "work_hours"
  },
  "action": {
    "type": "activate_persona",
    "persona_id": "uuid"
  },
  "priority": 10,
  "enabled": true
}
```

Conditions use AND logic within a rule. Multiple rules are evaluated by priority (highest first). First matching rule wins.

---

## Candidate Requirements

These should be reviewed during planning — not auto-included:

### Table Stakes (should become requirements)

- **CTX-01:** Backend Context API stores per-user context with configurable TTL (default 15 min)
- **CTX-02:** Context SSE stream pushes real-time updates to workspace
- **CTX-03:** Context rules engine evaluates conditions on each update, triggers persona switch
- **CTX-04:** Mobile app (Expo/React Native) connects to SemPKM instance via API key
- **CTX-05:** Mobile app monitors geofence zones and pushes enter/exit events as context updates
- **CTX-06:** Workspace sidebar shows current context indicator with SSE-driven updates
- **CTX-07:** Context rule management UI in settings (CRUD rules)
- **CTX-08:** Manual persona switch overrides auto-switching until next context change

### Expected Behaviors (likely needed)

- **CTX-09:** Device token registration endpoint for push notification setup
- **CTX-10:** Push notifications dispatched via Firebase Admin SDK
- **CTX-11:** Context-aware notification filtering (suppress work notifications outside work hours)
- **CTX-12:** Mobile app reads device calendar for current event context
- **CTX-13:** Mobile app detects activity type (stationary/walking/driving)

### Advisory (could defer)

- **CTX-14:** Zone configuration via interactive map in mobile app (could use text-based lat/lon entry as MVP)
- **CTX-15:** Offline context queue with retry on reconnect
- **CTX-16:** Multiple simultaneous device support (context from last-reporting device wins)

### Missing from Context Doc

- **CTX-17:** Context API rate limiting (mobile could flood backend if misconfigured)
- **CTX-18:** Context data deletion on user account removal (GDPR-friendly)
- **CTX-19:** Mobile app version checking against backend API version

---

## Available Agent Skills

The following professional skills are relevant to this milestone and available for installation:

| Skill | Install Command | Installs | Relevance |
|-------|----------------|----------|-----------|
| Vercel React Native | `npx skills add vercel-labs/agent-skills@vercel-react-native-skills` | 68.9K | Core RN development patterns |
| Callstack RN Best Practices | `npx skills add callstackincubator/agent-skills@react-native-best-practices` | 8.2K | Architecture and performance |
| Expo Building Native UI | `npx skills add expo/skills@building-native-ui` | 20.9K | Expo-specific UI patterns |
| Expo Native Data Fetching | `npx skills add expo/skills@native-data-fetching` | 15.4K | API client patterns |
| Expo Dev Client | `npx skills add expo/skills@expo-dev-client` | 12.4K | Development build setup |
| Expo Deployment | `npx skills add expo/skills@expo-deployment` | 12.4K | EAS Build and distribution |

**Recommendation:** Install `vercel-labs/agent-skills@vercel-react-native-skills` (highest installs, broadest coverage) and `expo/skills@building-native-ui` (Expo-specific) before starting mobile app slices (S04+).

---

## Open Questions Resolved

1. **React Native vs Flutter:** React Native via Expo. The JS ecosystem familiarity, the existing `api-client.js` pattern in the extension, and Expo's first-class geofencing/notification support make this clear.

2. **Geofence limits:** iOS 20, Android 100. For 3-5 user zones, this is a non-issue. Document in the zone editor UI.

3. **Calendar scope:** Read-only via `expo-calendar`. Only current/upcoming event titles and times for context detection. No calendar sync (that's M018-M021).

4. **Context update frequency:** Event-driven, not polling. Updates on: geofence enter/exit, calendar event start/end, significant activity change. Battery-efficient.

5. **Offline context:** Local queue with retry. Queued updates apply TTL on receipt at backend.

---

## Dependencies and New Backend Packages

| Package | Purpose | Version |
|---------|---------|---------|
| `firebase-admin` | FCM push notification dispatch | ~6.x |

The `firebase-admin` SDK is the only new Python dependency. It requires a Firebase project and service account credentials (stored encrypted, similar to the existing LLM key encryption pattern in `cryptography`).

The mobile app has its own `package.json` — its dependencies don't affect the backend's `pyproject.toml`.
