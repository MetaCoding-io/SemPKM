---
id: T03
parent: S04
milestone: M037
provides:
  - Full zone management screen with MapView, Circle overlays, and zone CRUD UI
  - ZoneEditor modal component for creating and editing geofence zones
  - Geofence sync after every zone mutation via registerGeofences()
  - Permission request flow triggered on first zone creation
key_files:
  - mobile/src/app/(app)/(tabs)/zones.tsx
  - mobile/src/components/ZoneEditor.tsx
key_decisions:
  - Used LongPressEvent (not MapPressEvent) for onLongPress handler — react-native-maps types distinguish press actions
  - Geofence sync failures are non-blocking (logged as warning, don't prevent zone CRUD)
  - Zone list capped at 45% max height with map getting the remaining flex space
patterns_established:
  - ZoneEditor uses center prop from parent rather than managing its own map — separation of map interaction from form state
  - API client instantiated via getClient() helper using useSession/parseSession pattern from dashboard screen
  - Zone item long-press opens edit mode, single press centers map on zone
observability_surfaces:
  - zones.geofence_sync_failed console.warn on registration failure
  - Alert.alert surfaces API error details to user
  - iOS region limit warning badge at 15+ enabled zones
  - Circle overlay color signals enabled (blue) vs disabled (grey) state
duration: 8 min
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Mobile zone management UI with map

**Replace placeholder zones screen with MapView-based zone management UI featuring Circle overlays, CRUD operations, geofence sync, and permission flow**

## What Happened

Built the complete zone management screen in two files:

1. **ZoneEditor.tsx** (`mobile/src/components/ZoneEditor.tsx`): Bottom-sheet modal for creating/editing zones. Features name TextInput (max 100 chars), radius stepper (50–1000m in 50m increments), read-only coordinate display set by map tap in parent, and Save/Cancel actions. Pre-fills all fields in edit mode; shows "Tap the map to set the zone center" instruction in create mode.

2. **zones.tsx** (`mobile/src/app/(app)/(tabs)/zones.tsx`): Full screen replacement with two visual regions:
   - **Map section** (top, flex): MapView with `showsUserLocation`, Circle overlays per zone (blue for enabled, grey for disabled), Markers with name callout. Long-press opens the editor with tapped coordinates.
   - **Zone list section** (bottom, max 45%): FlatList with zone items showing name (bold), radius badge, coordinates, enable/disable Switch, and delete button. Tapping centers the map on the zone; long-pressing opens the edit modal. Pull-to-refresh via FlatList `onRefresh`.
   - **FAB**: Circular blue button at bottom-right opens the editor in create mode.
   - **Loading/error/empty states**: ActivityIndicator on mount, error view with retry, empty state with instructions.
   - **Permission flow**: Calls `requestLocationPermissions()` on first zone creation. Shows Alert if background permission is denied.
   - **Geofence sync**: After every create/update/delete/toggle, calls `registerGeofences()` with current enabled zones.
   - **iOS limit warning**: Badge appears when 15+ zones are enabled (approaching the 20-region hard limit).

Installed `react-native-maps@1.27.2` via `npx expo install`. Used default map provider (Apple Maps on iOS, Google Maps on Android — no API key needed).

## Verification

- TypeScript compiles with zero errors (`npx tsc --noEmit`)
- MapView, Circle, registerGeofences, requestLocationPermissions all present in zones.tsx
- ZoneEditor.tsx component exists
- Backend tests (44/44) still pass
- All slice-level pattern checks pass (TaskManager, startGeofencingAsync, requestBackgroundPermissionsAsync, expo-location plugin)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd mobile && npx tsc --noEmit` | 0 | ✅ pass | 3.4s |
| 2 | `rg "MapView" mobile/src/app/(app)/(tabs)/zones.tsx` | 0 | ✅ pass | <0.1s |
| 3 | `rg "Circle" mobile/src/app/(app)/(tabs)/zones.tsx` | 0 | ✅ pass | <0.1s |
| 4 | `rg "registerGeofences" mobile/src/app/(app)/(tabs)/zones.tsx` | 0 | ✅ pass | <0.1s |
| 5 | `rg "requestLocationPermissions" mobile/src/app/(app)/(tabs)/zones.tsx` | 0 | ✅ pass | <0.1s |
| 6 | `test -f mobile/src/components/ZoneEditor.tsx` | 0 | ✅ pass | <0.1s |
| 7 | `cd backend && .venv/bin/python -m pytest tests/test_zone_service.py tests/test_zone_router.py -v` | 0 | ✅ pass (44/44) | 0.90s |
| 8 | `rg "TaskManager.defineTask" mobile/src/services/geofencing.ts` | 0 | ✅ pass | <0.1s |
| 9 | `rg "startGeofencingAsync" mobile/src/services/geofencing.ts` | 0 | ✅ pass | <0.1s |
| 10 | `rg "requestBackgroundPermissionsAsync" mobile/src/services/permissions.ts` | 0 | ✅ pass | <0.1s |
| 11 | `rg "expo-location" mobile/app.json` | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Zone list state**: Visible in the UI — each zone shows name, radius badge, coordinates, and enabled/disabled switch
- **Backend state**: `GET /api/context/zones` returns all zones for the authenticated user
- **Geofence sync**: After any mutation, `registerGeofences()` is called. Failures logged as `zones.geofence_sync_failed` — non-blocking
- **Error display**: API errors shown via `Alert.alert()` with server error detail
- **Visual indicators**: Circle overlay color (blue=enabled, grey=disabled), zone count badge (top-left), iOS limit warning (top-right at 15+)

## Deviations

- Used `LongPressEvent` type instead of `MapPressEvent` for the `onLongPress` handler — `react-native-maps` types distinguish the `action` discriminant between press and long-press events.
- Used double-quoted string to avoid escaping the apostrophe in "won't" in the Alert message — minor string literal adjustment.

## Known Issues

None.

## Files Created/Modified

- `mobile/src/app/(app)/(tabs)/zones.tsx` — replaced: full zone management screen with MapView, Circle overlays, FlatList, FAB, CRUD, geofence sync, permissions
- `mobile/src/components/ZoneEditor.tsx` — new: modal component for zone create/edit with name input, radius stepper, coordinate display
- `mobile/package.json` — modified: react-native-maps@1.27.2 added
- `.gsd/milestones/M037/slices/S04/tasks/T03-PLAN.md` — modified: added Observability Impact section
