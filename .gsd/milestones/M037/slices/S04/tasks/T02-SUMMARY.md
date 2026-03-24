---
id: T02
parent: S04
milestone: M037
provides:
  - Geofencing background task with TaskManager.defineTask at module scope
  - Location permission request utilities (foreground-then-background sequence)
  - Zone CRUD methods on SemPKMClient API client
  - app.json plugins for expo-location and expo-task-manager
  - Root layout side-effect import for background task registration
key_files:
  - mobile/src/services/geofencing.ts
  - mobile/src/services/permissions.ts
  - mobile/src/api/client.ts
  - mobile/app.json
  - mobile/src/app/_layout.tsx
key_decisions:
  - deleteZone uses inline fetch rather than generic request<T>() to handle 204 No Content without JSON parsing
  - GeofenceZone interface defined locally in geofencing.ts to avoid circular dependency with api/client.ts
patterns_established:
  - Background task reads credentials from SecureStore directly (no React context available in OS-triggered callbacks)
  - Geofence task logs use structured keys (geofence.transition, geofence.api_error, etc.) for greppability
observability_surfaces:
  - geofence.transition console.log on every enter/exit event
  - geofence.task_error / geofence.api_error / geofence.network_error console.error on failures
  - geofence.registered / geofence.stopped console.log on state changes
  - isGeofencingActive() programmatic check
duration: 8 min
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Mobile geofencing service, permissions, and app.json config

**Install expo-location and expo-task-manager, create geofencing background task at module scope, permission utilities, Zone CRUD on API client, and configure app.json plugins**

## What Happened

Built the mobile geofencing plumbing layer across 5 files:

1. **Geofencing service** (`geofencing.ts`): `TaskManager.defineTask('sempkm-geofence-task', ...)` called at module top-level. The callback reads session credentials from `expo-secure-store` (no React context), parses them, and POSTs to `/api/context/update` with `location_zone` set to the region identifier on enter or null on exit. Exported functions: `registerGeofences()` maps enabled zones to `LocationRegion` objects and calls `startGeofencingAsync`; `stopGeofencing()` and `isGeofencingActive()` for lifecycle control.

2. **Permission utilities** (`permissions.ts`): `requestLocationPermissions()` does the required foreground-then-background sequence — checks/requests foreground first, then only requests background if foreground was granted. `hasFullLocationPermission()` returns boolean for both levels. `getPermissionStatus()` returns both levels for UI display.

3. **API client** (`client.ts`): Added `Zone` and `ZoneCreatePayload` interfaces matching the backend Pydantic models. Added `getZones()`, `createZone()`, `updateZone()`, `deleteZone()` methods. Delete uses inline fetch to handle 204 No Content (the generic `request<T>()` would fail trying to parse an empty body).

4. **app.json**: Added `expo-location` plugin with `locationAlwaysAndWhenInUsePermission` description, `expo-task-manager` plugin, and `UIBackgroundModes: ["location"]` in `ios.infoPlist`.

5. **Root layout** (`_layout.tsx`): Side-effect import `import '@/services/geofencing'` added before the SessionProvider — ensures the task is registered at module scope before any component renders.

## Verification

- TypeScript compiles with zero errors
- All 7 pattern-based verification checks pass
- Backend tests (44/44) still pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd mobile && npx tsc --noEmit` | 0 | ✅ pass | 10.2s |
| 2 | `rg "TaskManager.defineTask" mobile/src/services/geofencing.ts` | 0 | ✅ pass | <0.1s |
| 3 | `rg "startGeofencingAsync" mobile/src/services/geofencing.ts` | 0 | ✅ pass | <0.1s |
| 4 | `rg "requestBackgroundPermissionsAsync" mobile/src/services/permissions.ts` | 0 | ✅ pass | <0.1s |
| 5 | `rg "expo-location" mobile/app.json` | 0 | ✅ pass | <0.1s |
| 6 | `rg "services/geofencing" mobile/src/app/_layout.tsx` | 0 | ✅ pass | <0.1s |
| 7 | `rg "getZones\|createZone\|updateZone\|deleteZone" mobile/src/api/client.ts` | 0 | ✅ pass | <0.1s |
| 8 | `cd backend && .venv/bin/python -m pytest tests/test_zone_service.py tests/test_zone_router.py -v` | 0 | ✅ pass (44/44) | 0.94s |

## Diagnostics

- **Geofence events**: Filter device console for `geofence.` prefix — all runtime signals use this namespace
- **Registration state**: Call `isGeofencingActive()` to check if the background task is running
- **Credential issues**: `geofence.no_session`, `geofence.invalid_session`, `geofence.session_parse_error` distinguish the failure mode
- **API failures**: `geofence.api_error` includes HTTP status; `geofence.network_error` includes the error message
- **Zone API client**: Throws `SemPKMError` with status code on any non-ok response

## Deviations

- Added `ZoneCreatePayload` as a separate interface (rather than `Omit<Zone, 'id' | 'created_at' | 'updated_at'>`) for clearer API surface — the Omit utility type is equivalent but less readable in IDE tooltips.
- `deleteZone()` uses inline fetch instead of the generic `request<T>()` method to handle 204 No Content without attempting JSON parse.
- `GeofenceZone` interface defined locally in geofencing.ts rather than importing `Zone` from api/client.ts — avoids circular dependency since geofencing.ts is a side-effect module imported at root scope.

## Known Issues

None.

## Files Created/Modified

- `mobile/src/services/geofencing.ts` — new: background task definition at module scope, registerGeofences/stopGeofencing/isGeofencingActive exports
- `mobile/src/services/permissions.ts` — new: foreground-then-background permission request sequence, hasFullLocationPermission, getPermissionStatus
- `mobile/src/api/client.ts` — modified: added Zone, ZoneCreatePayload interfaces and 4 CRUD methods
- `mobile/app.json` — modified: added expo-location plugin with permission string, expo-task-manager plugin, UIBackgroundModes
- `mobile/src/app/_layout.tsx` — modified: added side-effect import for geofencing task registration
- `mobile/package.json` — modified: expo-location ~55.1.4, expo-task-manager ~55.0.10 added by npx expo install
- `.gsd/milestones/M037/slices/S04/tasks/T02-PLAN.md` — added Observability Impact section
