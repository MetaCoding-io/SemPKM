# S04 Research: Mobile Geofencing & Location Zones

## Summary

S04 has two surfaces: (1) a backend zone CRUD API with Alembic migration, and (2) a mobile geofencing system using `expo-location` + `expo-task-manager` + `react-native-maps`. The backend side follows the exact CRUD pattern established by S02's `context_rules` (model → migration → router → service). The mobile side is the riskier half — it introduces three new Expo packages, requires a two-step permission flow (foreground then background), and has a critical constraint: `TaskManager.defineTask()` must be called at module scope, not inside a React component.

The geofencing API surface is clean: `startGeofencingAsync(taskName, regions[])` registers circular regions, and a background task fires on enter/exit. The task calls `POST /api/context/update` with `location_zone` set to the region name. No continuous GPS — event-driven only.

**Risk assessment:** The mobile geofencing code cannot be verified via automated test in CI — it requires a real device or simulator with location simulation. Verification will be structural (TypeScript compiles, correct API calls, proper permission sequencing) plus manual on-device testing.

## Recommendation

**Approach:** Build backend zone CRUD first (fully testable), then mobile geofencing service, then zone management UI with map. Four tasks:

1. **T01: Backend zone model, migration 020, and CRUD API** — `ContextZone` model, migration chaining from 019, zone router with 4 endpoints, zone service, unit tests. Follows `context_rules` pattern exactly.
2. **T02: Mobile geofencing service + background task** — Install `expo-location` + `expo-task-manager`, define geofencing background task at module scope, permission request utilities, geofence registration/teardown. Add API client methods for zone CRUD.
3. **T03: Mobile zone management UI with map** — Install `react-native-maps`, replace placeholder `zones.tsx` with map-based zone editor (MapView + Circle + draggable Marker), zone list, CRUD operations against backend API.
4. **T04: Permission flow UX + app.json config** — Configure expo-location plugin in app.json with background mode, build permission request flow with explanation modals before system dialogs, wire geofencing start/stop to zone changes.

T01 is fully independent. T02-T04 are sequential on the mobile side but all depend on T01's zone API.

## Implementation Landscape

### Backend: Zone CRUD (T01)

**Files to create:**
- `backend/app/context/zone_models.py` — `ContextZone` SQLAlchemy model (id UUID, user_id FK, name str 100, latitude float, longitude float, radius_meters float default 200, enabled bool, created_at, updated_at)
- `backend/app/context/zone_service.py` — `ZoneService` with CRUD methods (create, list_for_user, get, update, delete), scoped by user_id
- `backend/app/context/zone_router.py` — 4 endpoints at `/api/context/zones`: GET (list), POST (create, 201), PUT /{id} (update), DELETE /{id} (204)
- `backend/migrations/versions/020_context_zones.py` — chains from 019, creates `context_zones` table with FK to users.id (CASCADE), index on user_id

**Files to modify:**
- `backend/app/main.py` — register `zone_service` on `app.state`, include `zone_router`
- `backend/app/dependencies.py` — add `get_zone_service` dependency function

**Pattern to follow:** `context_rules` (rules_models.py → rules_engine.py → rules_router.py) is the 1:1 template. Same CRUD shape, same auth via `get_current_user_or_api`, same Pydantic request/response models.

**Constraint:** Zone coordinates (lat/lon) are stored for geofence registration but are NOT exposed to the RDF triplestore — privacy-by-design (D336 decision).

### Mobile: Geofencing Service (T02)

**Packages to install:**
```bash
cd mobile && npx expo install expo-location expo-task-manager
```
Both packages will resolve to `~55.0.x` matching SDK 55 (D337 confirms Expo managed workflow). Install via `npx expo install` to get version-locked packages.

**Critical constraint: `TaskManager.defineTask()` must be at top-level module scope.** It cannot be called inside a React component, useEffect, or async function. The task must be defined before the app renders. This means the geofencing task definition lives in a standalone module (e.g., `mobile/src/services/geofencing.ts`) that is imported at the app root (`_layout.tsx`).

**Geofencing task callback shape:**
```typescript
import * as TaskManager from 'expo-task-manager';
import * as Location from 'expo-location';

const GEOFENCE_TASK = 'sempkm-geofence-task';

TaskManager.defineTask(GEOFENCE_TASK, ({ data, error }) => {
  if (error) { console.error(error); return; }
  const { eventType, region } = data as {
    eventType: Location.GeofencingEventType;
    region: Location.LocationRegion;
  };
  // eventType is Enter (1) or Exit (2)
  // region.identifier is the zone name
  // Call POST /api/context/update with location_zone
});
```

**Permission sequence (order matters):**
1. `Location.requestForegroundPermissionsAsync()` — must be granted first
2. `Location.requestBackgroundPermissionsAsync()` — requires foreground granted; on Android 11+ opens system settings page
3. Only after both granted: `Location.startGeofencingAsync(taskName, regions)`

**Geofence registration:**
```typescript
await Location.startGeofencingAsync(GEOFENCE_TASK, [
  { identifier: 'office', latitude: 37.78, longitude: -122.43, radius: 200 },
  { identifier: 'home', latitude: 37.79, longitude: -122.44, radius: 150 },
]);
```
Calling `startGeofencingAsync` again with a new array replaces the previous registration — no need to stop/restart.

**API client additions needed:**
```typescript
// In mobile/src/api/client.ts
interface Zone {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  enabled: boolean;
}
async getZones(): Promise<Zone[]> { ... }
async createZone(zone: Omit<Zone, 'id'>): Promise<Zone> { ... }
async updateZone(id: string, zone: Partial<Zone>): Promise<Zone> { ... }
async deleteZone(id: string): Promise<void> { ... }
```

### Mobile: Zone Management UI (T03)

**Package to install:**
```bash
cd mobile && npx expo install react-native-maps
```

**UI structure for `zones.tsx`:**
- Top half: `<MapView>` with `<Circle>` overlay per zone and draggable `<Marker>` for zone centers
- Bottom half: scrollable zone list (FlatList) with zone name, radius, enable/disable toggle, edit/delete
- FAB or header button to add new zone
- Zone add/edit: modal or inline form with name input, radius slider (50-1000m), center from map tap or marker drag
- `showsUserLocation={true}` on MapView for orientation

**MapView Circle pattern:**
```tsx
<Circle
  center={{ latitude: zone.latitude, longitude: zone.longitude }}
  radius={zone.radius_meters}
  fillColor="rgba(37, 99, 235, 0.15)"
  strokeColor="#2563eb"
  strokeWidth={2}
/>
```

### Mobile: Permission Flow & Config (T04)

**app.json plugin additions:**
```json
{
  "plugins": [
    ["expo-location", {
      "locationAlwaysAndWhenInUsePermission": "SemPKM uses your location to detect when you arrive at or leave configured zones (home, office, etc.) and automatically adjust your workspace."
    }],
    "expo-task-manager"
  ],
  "ios": {
    "infoPlist": {
      "UIBackgroundModes": ["location"]
    }
  }
}
```

**Android permissions (auto-added by expo-location):** ACCESS_COARSE_LOCATION, ACCESS_FINE_LOCATION, FOREGROUND_SERVICE, FOREGROUND_SERVICE_LOCATION, ACCESS_BACKGROUND_LOCATION.

**Permission UX flow:**
1. User creates first zone → trigger permission request
2. Show explanation modal BEFORE system dialog (especially important for Android 11+ where background permission opens settings)
3. If foreground denied → show settings prompt
4. If foreground granted but background denied → geofencing won't work in background, show warning

## Constraints and Risks

### iOS 20-region limit
iOS `CLLocationManager` monitors at most 20 regions simultaneously. Most users need 3-5 zones. The zone creation UI should show a warning when approaching 15+ zones. Not a blocker — document and enforce soft limit.

### Android 100-geofence limit
Android's `GeofencingClient` supports up to 100 geofences. Not a practical concern.

### Development build required
`expo-location` background features (geofencing) do **not** work in Expo Go on iOS. A development build (`npx expo run:ios` or EAS Build) is required for testing. Expo Go on Android has partial support but is unreliable. The S03 summary confirms the Expo build pipeline works.

### TaskManager.defineTask at module scope
The geofencing task callback MUST be defined at the top level of a module, imported before the app renders. If defined inside a component or lazy-loaded, the task won't be registered when the OS fires the geofence event. This is a common gotcha — the planner must ensure the geofencing service module is imported in `_layout.tsx`.

### Background task API call without React context
The geofencing task callback runs outside the React component tree. It cannot use `useSession()` or any React hook. Credentials must be read directly from `expo-secure-store` (synchronous `getItem` is not available — use `getItemAsync` and handle the Promise). The S03 `useStorageState` hook stores session as `SecureStore.setItemAsync('session', json)` — the background task reads via `SecureStore.getItemAsync('session')`.

### Offline zone transitions
If the device is offline when a geofence transition fires, the `POST /api/context/update` will fail. Best-effort: log locally, retry on next transition. Full offline queue (CTX-15) is deferred per roadmap.

## Don't Hand-Roll

- **Geofencing** — use `expo-location` `startGeofencingAsync`. Do NOT use raw `react-native-background-geolocation` (paid library) or manual `watchPositionAsync` with distance calculations.
- **Background tasks** — use `expo-task-manager` `defineTask`. Do NOT use `expo-background-fetch` (wrong abstraction — that's for periodic fetch, not event-driven geofencing).
- **Map** — use `react-native-maps` `MapView` + `Circle` + `Marker`. Do NOT try to build a custom map with WebView or raw canvas.
- **Secure storage in background** — use `expo-secure-store` `getItemAsync()`. Do NOT store credentials in AsyncStorage (unencrypted).

## Skill Suggestions

**Installed and relevant:**
- `react-best-practices` — React component patterns, though this is React Native not web React
- `test` — for backend pytest unit tests on zone CRUD

**Available for install (not installed):**
- `jezweb/claude-skills@react-native-expo` (744 installs) — Expo/React Native patterns, could help with permission flows and native module config
- `mindrally/skills@expo-react-native-typescript` (334 installs) — TypeScript patterns for Expo apps

## Verification Strategy

**Backend (automated):**
- pytest unit tests for ZoneService CRUD (create, list, get, update, delete, user scoping)
- pytest router tests for all 4 endpoints (auth, validation, 404 on missing zone, user isolation)
- Alembic migration up/down test
- `cd mobile && npx tsc --noEmit` — TypeScript compilation

**Mobile (structural):**
- All new files exist and import correctly
- `TaskManager.defineTask` call is at module scope (not inside component)
- Permission request sequence: foreground → background → geofencing start
- `startGeofencingAsync` called with correct region shape
- API client zone methods match backend Pydantic models

**Mobile (manual, on-device):**
- Create zone in app → zone appears in backend `GET /api/context/zones`
- Simulate location change in simulator → geofence task fires → `POST /api/context/update` called → workspace context indicator shows new zone name
- iOS: "Always Allow" permission dialog appears with correct description text
- Android: foreground notification visible during background monitoring

## Open Questions

1. **Zone radius default and bounds** — Plan says radius in meters. Sensible default: 200m. Min: 50m (below this, GPS accuracy makes geofencing unreliable). Max: 10,000m (city-scale). The SHACL validation pattern doesn't apply here (SQLite, not RDF) — enforce in Pydantic model.

2. **react-native-maps provider** — Default uses Apple Maps on iOS and Google Maps on Android. Google Maps on iOS requires a Google Maps API key. Recommendation: use default provider (no API key needed). If Google Maps is needed later, it can be configured via `PROVIDER_GOOGLE` prop.

3. **Zone edit UX** — Two approaches: (a) inline edit on the map (tap zone → edit panel), (b) separate add/edit modal. Recommendation: modal for add, inline for edit. But this is a UX detail the executor can decide.
