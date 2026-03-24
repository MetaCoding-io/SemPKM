---
id: S04
parent: M037
milestone: M037
provides:
  - Backend zone CRUD API at /api/context/zones (GET, POST, PUT, DELETE) with Pydantic validation
  - ContextZone SQLAlchemy model and Alembic migration 020 (context_zones table)
  - ZoneService with full CRUD scoped by user_id
  - expo-location geofencing background task (TaskManager.defineTask at module scope)
  - Foreground-then-background location permission request utilities
  - Zone CRUD methods on SemPKMClient API client (getZones, createZone, updateZone, deleteZone)
  - Zone management screen with MapView, Circle overlays, FlatList, FAB, and ZoneEditor modal
  - Geofence re-registration on every zone mutation
requires:
  - slice: S01
    provides: POST /api/context/update endpoint consumed by geofence background task
  - slice: S03
    provides: API client, SessionProvider/parseSession, Expo project scaffold with navigation tabs
affects:
  - S05 (calendar/activity — uses same POST /api/context/update flow)
  - S07 (integration acceptance — geofence trigger is the starting point of the full loop)
key_files:
  - backend/app/context/zone_models.py
  - backend/app/context/zone_service.py
  - backend/app/context/zone_router.py
  - backend/migrations/versions/020_context_zones.py
  - backend/tests/test_zone_service.py
  - backend/tests/test_zone_router.py
  - mobile/src/services/geofencing.ts
  - mobile/src/services/permissions.ts
  - mobile/src/api/client.ts
  - mobile/src/app/(app)/(tabs)/zones.tsx
  - mobile/src/components/ZoneEditor.tsx
key_decisions:
  - Zone data stored in SQLite per D336 privacy-by-design — coordinates are server-side only, not in RDF
  - deleteZone on API client uses inline fetch (not generic request<T>()) to handle 204 No Content
  - GeofenceZone interface defined locally in geofencing.ts to avoid circular dependency with side-effect import
  - Geofence sync failures are non-blocking — logged as warning, don't prevent zone CRUD
  - LongPressEvent type used for map long-press (react-native-maps distinguishes press/long-press actions)
patterns_established:
  - Background task reads credentials from SecureStore directly (no React context in OS-triggered callbacks)
  - Geofence console logs use structured keys with "geofence." prefix for greppability
  - ZoneEditor uses center prop from parent rather than managing its own map state
  - API client instantiated via getClient() helper using useSession/parseSession pattern
  - Service tests with FK to users table need `import app.auth.models` for Base.metadata resolution
observability_surfaces:
  - context.zone_crud structured log on backend create/update/delete
  - GET /api/context/zones inspection endpoint for zone state
  - geofence.transition / geofence.api_error / geofence.network_error console logs in mobile
  - geofence.registered / geofence.stopped state change logs
  - isGeofencingActive() programmatic check
  - zones.geofence_sync_failed console.warn on registration failure
  - Circle overlay color signals enabled (blue) vs disabled (grey) state
  - iOS region limit warning badge at 15+ enabled zones
drill_down_paths:
  - .gsd/milestones/M037/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M037/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M037/slices/S04/tasks/T03-SUMMARY.md
duration: 28 min
verification_result: passed
completed_at: 2026-03-23
---

# S04: Mobile Geofencing & Location Zones

**Backend zone CRUD API + expo-location geofencing background task + MapView-based zone management UI — users can define geofence zones in the mobile app and trigger context updates on zone enter/exit**

## What Happened

Built the full geofencing stack across backend and mobile in three tasks:

**T01 — Backend zone CRUD** created the `ContextZone` SQLAlchemy model (UUID PK, user_id FK with CASCADE, name, lat/lon, radius 50–10000m, enabled flag, timestamps), Alembic migration 020 chaining from 019, `ZoneService` with full CRUD scoped by user_id, and a zone router with 4 endpoints at `/api/context/zones`. Pydantic validation enforces coordinate bounds (lat ±90, lon ±180) and radius limits. The service and router are wired into `app.state` and `dependencies.py` following the established context pattern. 44 tests cover all CRUD operations, auth enforcement, validation edge cases, and user isolation.

**T02 — Geofencing service and permissions** created the core mobile plumbing. `geofencing.ts` calls `TaskManager.defineTask('sempkm-geofence-task', ...)` at module top-level — the callback reads session credentials from SecureStore (no React context available in OS-triggered callbacks), parses them, and POSTs to `/api/context/update` with `location_zone` set to the region identifier on zone enter (or null on exit). `permissions.ts` implements the required foreground-then-background permission request sequence. The API client gained `Zone` interface and 4 CRUD methods. `app.json` was configured with `expo-location` and `expo-task-manager` plugins, including `UIBackgroundModes: ["location"]` for iOS. The geofencing module is side-effect imported in root `_layout.tsx` to ensure task registration before app render.

**T03 — Zone management UI** replaced the placeholder zones screen with a full MapView-based interface. The top section shows a map with Circle overlays per zone (blue for enabled, grey for disabled) and user location. The bottom section is a FlatList with name, radius badge, enable/disable Switch, and delete button. A floating action button opens the ZoneEditor modal for creating zones; long-press on map sets coordinates. ZoneEditor supports name input (100 char max), radius stepper (50–1000m in 50m increments), and coordinate display. Every mutation (create/update/delete/toggle) calls `registerGeofences()` to sync the geofence registrations. Permission request triggers on first zone creation. An iOS region limit warning appears at 15+ enabled zones.

## Verification

- **Backend tests:** 44/44 passed — `test_zone_service.py` (18 tests: CRUD, user isolation, missing/wrong-user returns None) + `test_zone_router.py` (26 tests: all endpoints, auth enforcement, Pydantic validation, boundary values, 404 handling)
- **TypeScript:** `npx tsc --noEmit` — zero errors across all mobile source files
- **Pattern checks:** All 7 slice-level verification commands pass — TaskManager.defineTask at module scope, startGeofencingAsync present, requestBackgroundPermissionsAsync present, expo-location in app.json, MapView in zones.tsx
- **Migration chain:** migration 020 correctly chains from 019 via `down_revision`

## Requirements Advanced

- CTX-07 (Zone CRUD API) — backend endpoints fully implemented with validation and auth
- CTX-08 (Geofencing background task) — TaskManager.defineTask at module scope, registerGeofences/stopGeofencing exported
- CTX-09 (Location permissions) — foreground-then-background sequence implemented
- CTX-14 (Zone config via map) — full MapView UI with circle overlays and marker placement

## Requirements Validated

- CTX-07 — 44 pytest tests prove CRUD, validation, auth, and user isolation
- CTX-08 — TypeScript compiles, task defined at module scope, imported in root layout
- CTX-09 — permission utilities compile and follow iOS/Android required sequence

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- `deleteZone()` on API client uses inline fetch instead of generic `request<T>()` to handle 204 No Content without JSON parse failure — minor implementation detail, no impact on API contract.
- `GeofenceZone` interface defined locally in `geofencing.ts` rather than importing `Zone` from `api/client.ts` — avoids circular dependency since geofencing.ts is a side-effect module imported at root scope.

## Known Limitations

- **No offline queue:** If the device is offline when a geofence transition fires, the POST to `/api/context/update` will fail silently (logged as `geofence.network_error`). CTX-15 (offline queue with retry) is explicitly deferred per milestone scope.
- **iOS 20-region hard limit:** iOS limits geofence monitoring to 20 regions. The UI warns at 15+ but does not hard-block creation. Users with 20+ zones will have unpredictable monitoring.
- **No on-device testing in CI:** Geofencing requires a real device or simulator with location simulation. All verification is TypeScript compilation + backend unit tests. Runtime behavior is UAT-only.

## Follow-ups

- S05 uses the same `POST /api/context/update` flow for calendar events and activity detection.
- S07 will exercise the full loop: geofence trigger → context update → rule evaluation → persona switch.
- Consider adding a retry mechanism in the geofence background task for transient network failures (currently best-effort).

## Files Created/Modified

- `backend/app/context/zone_models.py` — ContextZone SQLAlchemy model
- `backend/app/context/zone_service.py` — ZoneService with CRUD methods
- `backend/app/context/zone_router.py` — Zone CRUD API router (4 endpoints)
- `backend/migrations/versions/020_context_zones.py` — Alembic migration creating context_zones table
- `backend/app/main.py` — modified: zone_service on app.state, zone_router included
- `backend/app/dependencies.py` — modified: get_zone_service dependency
- `backend/tests/test_zone_service.py` — 18 service unit tests
- `backend/tests/test_zone_router.py` — 26 router unit tests
- `mobile/src/services/geofencing.ts` — background task, registerGeofences, stopGeofencing
- `mobile/src/services/permissions.ts` — foreground-then-background permission utilities
- `mobile/src/api/client.ts` — modified: Zone interface and 4 CRUD methods
- `mobile/app.json` — modified: expo-location + expo-task-manager plugins, UIBackgroundModes
- `mobile/src/app/_layout.tsx` — modified: side-effect import for geofencing task registration
- `mobile/package.json` — modified: expo-location, expo-task-manager, react-native-maps added
- `mobile/src/app/(app)/(tabs)/zones.tsx` — full zone management screen
- `mobile/src/components/ZoneEditor.tsx` — zone create/edit modal

## Forward Intelligence

### What the next slice should know
- S05 (calendar/activity) uses the same `POST /api/context/update` with different fields (`calendar_event`, `calendar_busy`, `activity`, `time_period`). The API client's existing `updateContext()` method from S01 handles this — no new endpoint needed.
- The geofencing background task pattern (`TaskManager.defineTask` at module scope, SecureStore credential read, side-effect import in `_layout.tsx`) should be replicated for any future background task (e.g., activity detection interval timer).

### What's fragile
- The geofence task reads credentials from SecureStore synchronously — if the session format changes in `_layout.tsx`'s `SessionProvider`, the task's `parseSession()` call in `geofencing.ts` must be updated too. The `GeofenceZone` interface is a local copy of the `Zone` shape, not a shared import.
- iOS background location permission can be revoked by the user at any time. The app doesn't currently detect revocation and re-prompt — it just fails silently on the next geofence event.

### Authoritative diagnostics
- Backend zone state: `GET /api/context/zones` with auth header — returns all zones for the user
- Mobile geofence events: filter device console for `geofence.` prefix (structured key namespace)
- Geofence registration state: call `isGeofencingActive()` from any mobile component

### What assumptions changed
- None — the slice delivered as planned. The expo-location and react-native-maps packages installed and compiled without issues.
