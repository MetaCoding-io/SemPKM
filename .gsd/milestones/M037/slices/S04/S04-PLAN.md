# S04: Mobile Geofencing & Location Zones

**Goal:** Users can define geofence zones in the mobile app and receive context updates when entering/leaving a zone, with zone data persisted server-side via a CRUD API.
**Demo:** Create a "Home" and "Office" zone in the mobile app's map UI, simulate a location change, and observe the workspace context indicator update with the zone name.

## Must-Haves

- Backend `context_zones` table (Alembic migration 020) with name, lat, lon, radius, user_id
- Zone CRUD API: `GET/POST/PUT/DELETE /api/context/zones` scoped by authenticated user
- `expo-location` geofencing background task defined at module scope via `TaskManager.defineTask`
- Two-step permission flow: foreground → background location, with pre-explanation UX
- `expo-location` plugin configured in `app.json` with background mode and permission description
- Zone management screen with `react-native-maps` MapView showing circles + draggable markers
- Geofence registration via `startGeofencingAsync` that calls `POST /api/context/update` on zone enter/exit
- API client extended with zone CRUD methods matching backend Pydantic models

## Proof Level

- This slice proves: integration (backend CRUD + mobile geofencing + location permissions)
- Real runtime required: yes (mobile geofencing requires device/simulator with location simulation)
- Human/UAT required: yes (on-device location simulation for geofence trigger verification)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_zone_service.py tests/test_zone_router.py -v` — all pass
- `cd mobile && npx tsc --noEmit` — zero TypeScript errors
- `rg "TaskManager.defineTask" mobile/src/services/geofencing.ts` — task defined at module scope (not inside component)
- `rg "startGeofencingAsync" mobile/src/services/geofencing.ts` — geofence registration present
- `rg "requestBackgroundPermissionsAsync" mobile/src/services/permissions.ts` — background permission request present
- `rg "expo-location" mobile/app.json` — plugin configured with permission description
- Manual: open Zones tab → map renders, can add zone, zone appears in backend `GET /api/context/zones`

## Observability / Diagnostics

- Runtime signals: `context.zone_crud` structured log in zone service, `geofence.transition` console.log in mobile task
- Inspection surfaces: `GET /api/context/zones` for zone state, `GET /api/context/current` for location_zone after transition
- Failure visibility: geofencing task logs errors to console, API client throws `SemPKMError` with HTTP status
- Redaction constraints: zone coordinates are not PII per D336 but are stored server-side only, not in RDF

## Integration Closure

- Upstream surfaces consumed: `POST /api/context/update` from S01, API client from S03, `SessionProvider` / `parseSession` from S03
- New wiring introduced: `zone_router` added to FastAPI app, `zone_service` on `app.state`, geofencing background task imported in root `_layout.tsx`
- What remains before milestone is truly usable end-to-end: S05 (calendar/activity), S06 (push notifications), S07 (integration acceptance)

## Tasks

- [x] **T01: Backend zone model, migration 020, and CRUD API with tests** `est:1.5h`
  - Why: The mobile app needs server-side zone storage and retrieval before it can register geofences. This follows the exact CRUD pattern from `context_rules` (S02).
  - Files: `backend/app/context/zone_models.py`, `backend/app/context/zone_service.py`, `backend/app/context/zone_router.py`, `backend/migrations/versions/020_context_zones.py`, `backend/app/main.py`, `backend/app/dependencies.py`, `backend/tests/test_zone_service.py`, `backend/tests/test_zone_router.py`
  - Do: Create `ContextZone` SQLAlchemy model (id UUID, user_id FK, name str 100, latitude float, longitude float, radius_meters float default 200, enabled bool, created_at, updated_at). Create Alembic migration 020 chaining from 019. Build `ZoneService` with CRUD methods (create, list_for_user, get, update, delete) scoped by user_id. Build zone router with 4 endpoints at `/api/context/zones`. Register service and router in `main.py` and `dependencies.py`. Write pytest unit tests for service CRUD and router endpoints following `test_context_service.py` / `test_rules_router.py` patterns. Validate radius bounds (min 50, max 10000) and name length in Pydantic models.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_zone_service.py tests/test_zone_router.py -v` — all pass
  - Done when: All zone CRUD tests pass, migration chains correctly from 019, endpoints return correct status codes (201 create, 204 delete, 404 missing)

- [x] **T02: Mobile geofencing service, permissions, and app.json config** `est:1.5h`
  - Why: The geofencing background task and permission flow are the critical mobile plumbing that must exist before the zone UI can trigger geofence registration. The TaskManager.defineTask call MUST be at module scope and imported before the app renders.
  - Files: `mobile/src/services/geofencing.ts`, `mobile/src/services/permissions.ts`, `mobile/src/api/client.ts`, `mobile/app.json`, `mobile/src/app/_layout.tsx`, `mobile/package.json`
  - Do: Install `expo-location` and `expo-task-manager` via `npx expo install`. Create `geofencing.ts` with `TaskManager.defineTask('sempkm-geofence-task', ...)` at module scope — the callback reads credentials from `expo-secure-store` `getItemAsync('session')`, parses them, and calls `POST /api/context/update` with `location_zone` set to the region identifier. Export `registerGeofences(zones)` and `stopGeofencing()` functions. Create `permissions.ts` with `requestLocationPermissions()` that does foreground-then-background permission requests, returning a status object. Import geofencing module in root `_layout.tsx` so the task is registered before app renders. Add `expo-location` plugin to `app.json` with `locationAlwaysAndWhenInUsePermission` string and `UIBackgroundModes: ["location"]` for iOS. Extend `SemPKMClient` in `client.ts` with `getZones()`, `createZone()`, `updateZone()`, `deleteZone()` methods and `Zone` interface.
  - Verify: `cd mobile && npx tsc --noEmit` — zero errors; `rg "TaskManager.defineTask" mobile/src/services/geofencing.ts` returns a match
  - Done when: TypeScript compiles, geofencing task defined at module scope, imported in root layout, app.json has expo-location plugin, API client has zone CRUD methods

- [ ] **T03: Mobile zone management UI with map** `est:2h`
  - Why: Replaces the placeholder zones screen with a full map-based zone editor where users can create, edit, and delete geofence zones. This is the user-facing surface that ties backend zone CRUD to mobile geofence registration.
  - Files: `mobile/src/app/(app)/(tabs)/zones.tsx`, `mobile/src/components/ZoneEditor.tsx`, `mobile/package.json`
  - Do: Install `react-native-maps` via `npx expo install`. Replace placeholder `zones.tsx` with zone management screen: top half is `MapView` with `Circle` overlays for each zone and `showsUserLocation={true}`, bottom half is a `FlatList` of zones with name, radius badge, enable/disable switch, and delete button. Add floating action button to create new zone. Build `ZoneEditor.tsx` modal component for add/edit with name input, radius slider (50-1000m), and map tap or marker drag to set center. On zone create/update, call API client zone methods then call `registerGeofences()` from T02 to sync geofences. On zone delete, remove from API then re-register remaining zones. Request location permissions via T02's `requestLocationPermissions()` when first zone is created. Show zone count and iOS 20-region soft warning when approaching 15+ zones.
  - Verify: `cd mobile && npx tsc --noEmit` — zero errors; `rg "MapView" mobile/src/app/\(app\)/\(tabs\)/zones.tsx` returns a match
  - Done when: TypeScript compiles, zones screen shows MapView with circle overlays, zone CRUD operations call backend API, geofence registration syncs with zone changes, permission request triggers on first zone creation

## Files Likely Touched

- `backend/app/context/zone_models.py`
- `backend/app/context/zone_service.py`
- `backend/app/context/zone_router.py`
- `backend/migrations/versions/020_context_zones.py`
- `backend/app/main.py`
- `backend/app/dependencies.py`
- `backend/tests/test_zone_service.py`
- `backend/tests/test_zone_router.py`
- `mobile/src/services/geofencing.ts`
- `mobile/src/services/permissions.ts`
- `mobile/src/api/client.ts`
- `mobile/src/app/_layout.tsx`
- `mobile/app.json`
- `mobile/package.json`
- `mobile/src/app/(app)/(tabs)/zones.tsx`
- `mobile/src/components/ZoneEditor.tsx`
