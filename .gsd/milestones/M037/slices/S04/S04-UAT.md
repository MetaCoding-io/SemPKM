# S04: Mobile Geofencing & Location Zones — UAT

**Milestone:** M037
**Written:** 2026-03-23

## UAT Type

- UAT mode: mixed (artifact-driven for backend + human-experience for mobile)
- Why this mode is sufficient: Backend zone CRUD is fully tested via pytest (44 tests). Mobile geofencing requires on-device location simulation that cannot be automated in CI — human verification on simulator or physical device is required.

## Preconditions

- Docker stack running (`docker compose up -d`) with backend API accessible
- User authenticated with valid session
- S01 context API operational (`POST /api/context/update` and `GET /api/context/current` working)
- S03 mobile app built and runnable on iOS simulator or Android emulator (or physical device)
- Mobile app connected to SemPKM instance (onboarding completed in S03)
- For geofence testing: iOS Simulator with "Features > Location > Custom Location" or Android emulator with extended controls location simulation

## Smoke Test

1. Open the mobile app, tap the "Zones" tab
2. **Expected:** Map renders with user location dot, empty zone list below, floating "+" button visible

## Test Cases

### 1. Create a zone via the mobile app

1. Tap the "+" floating action button
2. Long-press a location on the map to set the zone center
3. Enter name "Office" in the name field
4. Adjust radius to 200m using the stepper
5. Tap "Save"
6. **Expected:** Zone appears in the list below the map with name "Office", radius badge "200m", and a blue circle overlay on the map
7. Verify backend: `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/context/zones` returns a zone named "Office" with correct coordinates and radius

### 2. Create a second zone and verify list

1. Tap "+" again, long-press a different map location
2. Enter name "Home", radius 150m, tap "Save"
3. **Expected:** Two zones in the list, two circle overlays on the map. Zone count badge shows "2"

### 3. Edit an existing zone

1. Long-press the "Office" zone in the list
2. Change name to "Main Office", adjust radius to 300m
3. Tap "Save"
4. **Expected:** Zone list updates with new name and radius badge "300m". Map circle overlay resizes. Backend GET returns updated values.

### 4. Toggle zone enabled/disabled

1. Tap the Switch next to "Home" zone to disable it
2. **Expected:** Circle overlay changes from blue to grey. Zone shows in list but is visually dimmed.
3. Verify backend: `GET /api/context/zones` shows the Home zone with `enabled: false`

### 5. Delete a zone

1. Tap the delete button (trash icon) on the "Home" zone
2. **Expected:** Zone removed from list. Circle overlay disappears. Backend `GET /api/context/zones` returns only "Main Office".

### 6. Geofence trigger — zone enter

1. Create a zone centered on a known coordinate (e.g., lat 37.7749, lon -122.4194, radius 500m)
2. In iOS Simulator: Features > Location > Custom Location, set to coordinates outside the zone
3. Wait 5 seconds, then change location to coordinates inside the zone
4. **Expected:** Device console shows `geofence.transition` log with `eventType: "Enter"` and the zone name. Backend `GET /api/context/current` shows `location_zone` set to the zone name. If workspace is open, the context indicator updates.

### 7. Geofence trigger — zone exit

1. With location inside the zone from test 6, change to coordinates far outside the zone
2. **Expected:** Device console shows `geofence.transition` with `eventType: "Exit"`. Backend `GET /api/context/current` shows `location_zone` as null or empty.

### 8. Permission request flow

1. Reset location permissions for the app (Settings > Privacy > Location Services > SemPKM > Never)
2. Open the Zones tab, tap "+" to create a zone
3. **Expected:** Permission dialog appears requesting foreground location access ("Allow While Using App")
4. Grant foreground permission
5. **Expected:** Second dialog appears requesting background location ("Always Allow")
6. Grant background permission
7. **Expected:** Zone creation proceeds normally. `hasFullLocationPermission()` returns true.

### 9. Backend validation — invalid coordinates

1. Send: `curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"name":"Bad","latitude":100,"longitude":0,"radius_meters":200}' http://localhost:8000/api/context/zones`
2. **Expected:** HTTP 422 with validation error for latitude out of range (-90 to 90)
3. Send same with latitude 45, longitude 200
4. **Expected:** HTTP 422 for longitude out of range (-180 to 180)
5. Send same with valid coords but radius 10
6. **Expected:** HTTP 422 for radius below minimum (50m)

### 10. Backend validation — auth enforcement

1. Send: `curl -X GET http://localhost:8000/api/context/zones` (no auth header)
2. **Expected:** HTTP 401 Unauthorized

## Edge Cases

### iOS 20-region limit warning

1. Create 15 enabled zones
2. **Expected:** Warning badge appears near the zone count indicating approach to iOS limit
3. Create 5 more (total 20)
4. **Expected:** Warning remains visible. App does not crash. Geofence registration may silently drop the oldest zones (iOS behavior).

### Geofence sync failure (offline)

1. Put device in airplane mode
2. Create a zone in the app
3. **Expected:** Zone saves to backend (if cached) or shows error alert. Console shows `zones.geofence_sync_failed` warning. Zone still appears in list.

### Zone with minimum/maximum radius

1. Create a zone with radius exactly 50m (minimum)
2. Create a zone with radius exactly 1000m (maximum via UI stepper)
3. **Expected:** Both save successfully. Circle overlays render at correct sizes on map.

### Empty zone list pull-to-refresh

1. With no zones, pull down on the zone list area
2. **Expected:** Refresh indicator appears and disappears. No crash. Empty state message remains.

### Map centers on zone tap

1. With multiple zones, tap a zone item in the list
2. **Expected:** Map animates to center on that zone's coordinates

## Failure Signals

- Zone list empty after creating zones → API client not using correct auth token or wrong base URL
- Map doesn't render → `react-native-maps` not linked or Google Maps API key missing (Android)
- `geofence.no_session` in console → SecureStore doesn't have credentials; onboarding flow (S03) didn't save properly
- `geofence.api_error` with HTTP 401 → API key expired or invalid
- `geofence.network_error` → device offline or backend unreachable
- Circle overlays missing but zones in list → MapView Circle component not receiving correct props
- Permission dialog never appears → `expo-location` plugin not configured in app.json or permissions already granted

## Requirements Proved By This UAT

- CTX-07 (Zone CRUD API) — tests 1–5 prove full CRUD lifecycle, test 9 proves validation, test 10 proves auth
- CTX-08 (Geofencing background task) — tests 6–7 prove zone enter/exit triggers context update
- CTX-09 (Location permissions) — test 8 proves foreground-then-background permission flow
- CTX-14 (Zone config via map) — tests 1–5 prove MapView-based zone management

## Not Proven By This UAT

- **Offline queue with retry (CTX-15)** — explicitly deferred. Geofence transitions during offline are lost.
- **Multi-device conflict resolution (CTX-16)** — not tested. Last-reporting device wins behavior is documented but not verified.
- **App Store review compliance** — iOS "Always Allow" location justification string is set in app.json but not verified through Apple review.
- **Android foreground service notification** — expo-location handles this automatically but visual appearance not verified.

## Notes for Tester

- **Location simulation:** iOS Simulator supports custom location via Xcode menu (Debug > Simulate Location) or the Simulator's Features > Location menu. Android emulator has extended controls with a map-based location setter.
- **Geofence latency:** OS-level geofencing is not instantaneous. iOS may batch location transitions. Allow up to 30 seconds for a geofence event to fire after changing simulated location.
- **Background testing:** To test background geofencing, minimize the app (press Home) before changing simulated location. The `sempkm-geofence-task` should still fire.
- **Console logs:** Use Expo's `npx expo start` terminal output or React Native Debugger to see console.log/warn/error output from the geofencing task.
