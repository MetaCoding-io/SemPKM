---
estimated_steps: 5
estimated_files: 6
skills_used:
  - react-best-practices
---

# T02: Mobile geofencing service, permissions, and app.json config

**Slice:** S04 — Mobile Geofencing & Location Zones
**Milestone:** M037

## Description

Install the native location packages, create the geofencing background task and permission utilities, extend the API client with zone CRUD methods, and configure `app.json` for background location. This is the critical mobile plumbing layer — everything must be right for geofencing to work when the OS fires events in the background.

**Key constraint:** `TaskManager.defineTask()` MUST be called at the top-level scope of a module, NOT inside a React component, `useEffect`, or async function. The task definition module must be imported in the root `_layout.tsx` before the app renders, so the OS can find the task handler when a geofence transition fires (even if the app was killed).

**Background task API access:** The geofencing callback runs outside the React component tree — no hooks, no context. Credentials must be read directly from `expo-secure-store` via `getItemAsync('session')`. The S03 session format is JSON `{ instanceUrl, apiKey }` stored under key `'session'`.

## Steps

1. **Install packages** — Run `cd mobile && npx expo install expo-location expo-task-manager` to get SDK 55-compatible versions. Verify they appear in `package.json` dependencies.

2. **Create `mobile/src/services/geofencing.ts`** — Define the geofencing background task:
   ```typescript
   import * as TaskManager from 'expo-task-manager';
   import * as Location from 'expo-location';
   import * as SecureStore from 'expo-secure-store';

   const GEOFENCE_TASK = 'sempkm-geofence-task';

   // MUST be at module scope — not inside any component or function
   TaskManager.defineTask(GEOFENCE_TASK, async ({ data, error }) => {
     if (error) { console.error('geofence.task_error', error); return; }
     const { eventType, region } = data as {
       eventType: Location.GeofencingEventType;
       region: Location.LocationRegion;
     };
     // Read credentials from secure store (no React context available)
     const raw = await SecureStore.getItemAsync('session');
     if (!raw) { console.warn('geofence.no_session'); return; }
     const { instanceUrl, apiKey } = JSON.parse(raw);
     const zoneName = eventType === Location.GeofencingEventType.Enter
       ? region.identifier : null;
     // POST context update
     await fetch(`${instanceUrl}/api/context/update`, {
       method: 'POST',
       headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
       body: JSON.stringify({ location_zone: zoneName }),
     });
   });
   ```
   Export functions: `registerGeofences(zones: Zone[])` — calls `Location.startGeofencingAsync(GEOFENCE_TASK, regions)` mapping zones to `{ identifier: zone.name, latitude, longitude, radius: zone.radius_meters }`. Only registers enabled zones. Export `stopGeofencing()` — calls `Location.stopGeofencingAsync(GEOFENCE_TASK)`. Export `isGeofencingActive()` — calls `Location.hasStartedGeofencingAsync(GEOFENCE_TASK)`.

3. **Create `mobile/src/services/permissions.ts`** — Export `requestLocationPermissions()` that returns `{ foreground: PermissionStatus, background: PermissionStatus }`. Sequence: check foreground first (`getForegroundPermissionsAsync`), request if not granted, then check background (`getBackgroundPermissionsAsync`), request if not granted. Export `hasFullLocationPermission()` that checks both are granted. Export `getPermissionStatus()` for UI display.

4. **Extend API client** — Add `Zone` interface to `mobile/src/api/client.ts`: `{ id: string, name: string, latitude: number, longitude: number, radius_meters: number, enabled: boolean, created_at: string, updated_at: string }`. Add methods to `SemPKMClient`: `getZones(): Promise<Zone[]>` (GET `/api/context/zones`), `createZone(zone: Omit<Zone, 'id' | 'created_at' | 'updated_at'>): Promise<Zone>` (POST), `updateZone(id: string, zone: Partial<Zone>): Promise<Zone>` (PUT), `deleteZone(id: string): Promise<void>` (DELETE, expect 204 no body).

5. **Configure app.json and root import** — Add to `app.json` `plugins` array: `["expo-location", { "locationAlwaysAndWhenInUsePermission": "SemPKM uses your location to detect when you arrive at or leave configured zones (home, office, etc.) and automatically adjust your workspace." }]` and `"expo-task-manager"`. Add `"UIBackgroundModes": ["location"]` to `ios.infoPlist`. Import the geofencing module at the top of `mobile/src/app/_layout.tsx`: `import '@/services/geofencing';` (side-effect import to register the task at module scope).

## Must-Haves

- [ ] `expo-location` and `expo-task-manager` installed (in package.json)
- [ ] `TaskManager.defineTask` call at module top-level in `geofencing.ts` — NOT inside a component
- [ ] Geofence task reads credentials from SecureStore, not React context
- [ ] `registerGeofences()` calls `startGeofencingAsync` with correct region shape
- [ ] `requestLocationPermissions()` does foreground-then-background sequence
- [ ] API client has Zone interface + 4 CRUD methods matching backend models
- [ ] `app.json` has expo-location plugin with permission description and UIBackgroundModes
- [ ] Geofencing module imported in root `_layout.tsx`

## Verification

- `cd mobile && npx tsc --noEmit` — zero TypeScript errors
- `rg "TaskManager.defineTask" mobile/src/services/geofencing.ts` — match found
- `rg "startGeofencingAsync" mobile/src/services/geofencing.ts` — match found
- `rg "requestBackgroundPermissionsAsync" mobile/src/services/permissions.ts` — match found
- `rg "expo-location" mobile/app.json` — plugin configured
- `rg "services/geofencing" mobile/src/app/_layout.tsx` — side-effect import present
- `rg "getZones\|createZone\|updateZone\|deleteZone" mobile/src/api/client.ts` — all 4 methods present

## Inputs

- `mobile/src/api/client.ts` — existing API client to extend with zone methods
- `mobile/src/ctx.tsx` — `parseSession()` function that decodes SecureStore session format
- `mobile/app.json` — existing Expo config to add plugins to
- `mobile/src/app/_layout.tsx` — root layout where geofencing import goes
- `mobile/package.json` — dependencies list (add expo-location, expo-task-manager)
- `backend/app/context/zone_router.py` — backend zone API endpoints (from T01) to match

## Expected Output

- `mobile/src/services/geofencing.ts` — geofencing background task + registration functions
- `mobile/src/services/permissions.ts` — location permission request utilities
- `mobile/src/api/client.ts` — modified: Zone interface + 4 CRUD methods added
- `mobile/app.json` — modified: expo-location plugin, expo-task-manager, UIBackgroundModes
- `mobile/src/app/_layout.tsx` — modified: geofencing side-effect import added
- `mobile/package.json` — modified: expo-location and expo-task-manager added

## Observability Impact

**New runtime signals:**
- `geofence.transition` — console.log on every geofence enter/exit with event type and region identifier
- `geofence.task_error` — console.error when the OS reports a task error
- `geofence.no_session` / `geofence.invalid_session` / `geofence.session_parse_error` — console.warn when credentials are missing or malformed
- `geofence.api_error` — console.error with HTTP status on failed context updates
- `geofence.network_error` — console.error with message on fetch failures
- `geofence.registered` — console.log with count when geofences are successfully registered
- `geofence.stopped` — console.log when geofencing is deactivated

**Inspection:**
- All signals are in the device/simulator console log (via `npx expo start` or Xcode console)
- `isGeofencingActive()` can be called programmatically to check if the task is running
- Zone API client errors throw `SemPKMError` with HTTP status code for caller inspection

**Failure visibility:**
- Background task errors are logged immediately with structured keys (greppable)
- Session parse failures distinguish between missing session, missing fields, and JSON parse errors
- API failures include the HTTP status code for diagnosis
