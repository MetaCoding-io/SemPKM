---
estimated_steps: 4
estimated_files: 3
skills_used:
  - react-best-practices
---

# T03: Mobile zone management UI with map

**Slice:** S04 — Mobile Geofencing & Location Zones
**Milestone:** M037

## Description

Replace the placeholder `zones.tsx` screen with a full map-based zone management UI. Users see their zones as circles on a map, can add/edit/delete zones, and zone changes automatically sync geofence registrations with the OS.

The screen has two visual regions: a `MapView` (upper portion) showing zone circles and the user's location, and a zone list (lower portion) with CRUD controls. A floating action button triggers zone creation. A modal (`ZoneEditor`) handles add/edit with name input, radius slider, and map tap for center placement.

## Steps

1. **Install `react-native-maps`** — Run `cd mobile && npx expo install react-native-maps`. Verify it appears in `package.json`. Use the default map provider (Apple Maps on iOS, Google Maps on Android — no API key needed).

2. **Build `ZoneEditor.tsx` modal component** in `mobile/src/components/ZoneEditor.tsx`. Props: `visible: boolean`, `zone?: Zone` (for edit), `onSave: (data) => void`, `onCancel: () => void`. Contains: name `TextInput` (max 100 chars), radius slider (`Slider` from `@react-native-community/slider` or a simple custom range via `TextInput` + stepper buttons — keep it simple, a numeric input with +/- buttons for 50-1000m range is fine), latitude/longitude display (read-only, set via map tap in parent), and Save/Cancel buttons. For new zones, show instruction text "Tap the map to set the zone center". For editing, pre-fill all fields from the existing zone.

3. **Replace `zones.tsx` with full zone management screen**:
   - **State**: zones array (fetched from `getZones()`), selected zone for editing, new zone center from map tap, editor modal visible.
   - **Top section (MapView)**: `<MapView>` with `showsUserLocation={true}`, `style={{ flex: 1 }}`. Render a `<Circle>` per zone (fillColor `rgba(37, 99, 235, 0.15)`, strokeColor `#2563eb`, strokeWidth 2). Render a `<Marker>` at each zone center with the zone name as callout. On map long-press (`onLongPress`), capture coordinates for new zone center and open editor.
   - **Bottom section (zone list)**: `FlatList` with zone items showing: name (bold), radius badge (e.g. "200m"), enabled/disabled `Switch`, delete `TouchableOpacity`. Tapping a zone item centers the map on it. Swipe or button to delete (calls `deleteZone()` then `registerGeofences()` to sync).
   - **Floating action button**: positioned absolute bottom-right, circular blue button with "+" icon. Opens `ZoneEditor` in create mode.
   - **Permission flow**: When user creates the first zone, call `requestLocationPermissions()` from T02's `permissions.ts`. If background permission is denied, show an `Alert` explaining that geofencing won't work in the background. Proceed with zone creation regardless (zones are stored server-side even without location permissions).
   - **Geofence sync**: After any zone create/update/delete, call `registerGeofences(enabledZones)` to update the OS geofence registrations. Show zone count and a warning text when 15+ zones exist (iOS 20-region limit).
   - **Loading/error states**: Show `ActivityIndicator` while fetching zones. Show error text with retry on API failure. Empty state: "No zones configured. Tap + to add your first zone."

4. **Wire API client and fetch zones on mount** — Use `useEffect` to fetch zones when screen mounts. Use `useSession()` + `parseSession()` to get credentials and instantiate `SemPKMClient`. Handle the case where session is null (shouldn't happen behind auth guard, but be defensive). Pull-to-refresh via `FlatList` `onRefresh`.

## Must-Haves

- [ ] Placeholder zones screen replaced with MapView + zone list
- [ ] Zones rendered as Circle overlays on MapView
- [ ] Zone create/edit via ZoneEditor modal
- [ ] Zone CRUD calls backend API (getZones, createZone, updateZone, deleteZone)
- [ ] Geofence registration syncs after any zone change via `registerGeofences()`
- [ ] Permission request triggered on first zone creation
- [ ] Loading, error, and empty states handled
- [ ] TypeScript compiles with zero errors

## Verification

- `cd mobile && npx tsc --noEmit` — zero TypeScript errors
- `rg "MapView" "mobile/src/app/(app)/(tabs)/zones.tsx"` — MapView present
- `rg "Circle" "mobile/src/app/(app)/(tabs)/zones.tsx"` — Circle overlay present
- `rg "registerGeofences" "mobile/src/app/(app)/(tabs)/zones.tsx"` — geofence sync wired
- `rg "requestLocationPermissions" "mobile/src/app/(app)/(tabs)/zones.tsx"` — permission request wired
- `test -f mobile/src/components/ZoneEditor.tsx` — editor component exists

## Inputs

- `mobile/src/app/(app)/(tabs)/zones.tsx` — existing placeholder to replace
- `mobile/src/services/geofencing.ts` — `registerGeofences()` function from T02
- `mobile/src/services/permissions.ts` — `requestLocationPermissions()` from T02
- `mobile/src/api/client.ts` — `SemPKMClient` with zone CRUD methods from T02
- `mobile/src/ctx.tsx` — `useSession()`, `parseSession()` for auth

## Expected Output

- `mobile/src/app/(app)/(tabs)/zones.tsx` — full zone management screen with map
- `mobile/src/components/ZoneEditor.tsx` — zone add/edit modal component
- `mobile/package.json` — modified: react-native-maps added

## Observability Impact

- **New signals:** `zones.geofence_sync_failed` console.warn on registration failure after zone mutation. All zone CRUD errors surface via `Alert.alert()` with the server's error detail.
- **Inspection:** Zone list state visible in the UI. Backend `GET /api/context/zones` shows the authoritative server state. Enabled/disabled toggle state reflects in Circle overlay color (blue=enabled, grey=disabled).
- **Failure visibility:** Loading spinner on mount, error state with retry button on API failure, empty state when no zones exist. Permission denial shows an explanatory Alert. iOS region limit warning badge appears at 15+ enabled zones.
- **Geofence sync:** After every create/update/delete, `registerGeofences()` is called with the current enabled-zone set. Failures are logged to console but don't block the UI (zone CRUD succeeds even if geofence registration fails).
