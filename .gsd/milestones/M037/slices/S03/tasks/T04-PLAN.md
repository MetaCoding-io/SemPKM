---
estimated_steps: 4
estimated_files: 4
skills_used:
  - react-best-practices
---

# T04: Dashboard, Tab Navigation & Settings

**Slice:** S03 — Mobile App Foundation & API Connection
**Milestone:** M037

## Description

Create the tab navigator with three tabs (Dashboard, Zones, Settings), the context dashboard screen with pull-to-refresh, a zones placeholder for S04, and a settings screen with connection info and sign-out. This completes the mobile app's core navigation and functionality.

## Steps

1. Create `mobile/src/app/(app)/(tabs)/_layout.tsx` — tab navigator:
   - Import `Tabs` from `expo-router`
   - Import `Ionicons` from `@expo/vector-icons`
   - Configure 3 tabs:
     - `index` — title "Dashboard", icon `home-outline` / `home`
     - `zones` — title "Zones", icon `map-outline` / `map`
     - `settings` — title "Settings", icon `settings-outline` / `settings`
   - Use `tabBarActiveTintColor` for active tab highlighting

2. Create `mobile/src/app/(app)/(tabs)/index.tsx` — dashboard screen:
   - Import `useSession` from `../../../ctx`, `SemPKMClient` and `ContextResponse` from `../../../api/client`
   - State: `context: ContextResponse | null`, `loading: boolean`, `error: string | null`, `refreshing: boolean`
   - `fetchContext()` function: parse session JSON to get instanceUrl/apiKey, create SemPKMClient, call getCurrentContext(), set state
   - Call `fetchContext()` on mount via `useEffect`
   - Render a `ScrollView` with `RefreshControl` (onRefresh calls fetchContext with refreshing state)
   - Display context fields with labels: "Location" → `context.location_zone ?? "Not set"`, "Activity" → `context.activity ?? "Not set"`, "Time Period" → `context.time_period ?? "Not set"`, "Calendar" → `context.calendar_event ?? "None"`
   - Staleness indicator: green circle (fresh), red circle (stale, `is_stale === true`), with "Last updated: {relative time}" text
   - Empty state when context is null and no error: "No context data yet. Context updates will appear here when sent from this device."
   - Error state: show error message with retry button
   - Loading state: ActivityIndicator centered

3. Create `mobile/src/app/(app)/(tabs)/zones.tsx` — placeholder:
   - Simple screen with centered text: "Zone Management" heading, "Coming in a future update. You'll be able to define geofence zones here." subtext
   - Import Ionicons, show a map-pin icon above the text
   - This screen will be replaced in S04

4. Create `mobile/src/app/(app)/(tabs)/settings.tsx` — settings screen:
   - Import `useSession` from `../../../ctx`
   - Parse session JSON to extract instanceUrl
   - Display: "Connected to" label with instance URL below it
   - Display: "App Version" with value from expo-constants or hardcoded "1.0.0"
   - "Sign Out" button: calls `signOut()` from useSession, which clears credentials and triggers redirect to sign-in via route guard
   - Style the sign-out button with red/destructive appearance

## Must-Haves

- [ ] Tab navigator with 3 tabs: Dashboard, Zones, Settings — each with icon
- [ ] Dashboard fetches and displays context from `GET /api/context/current`
- [ ] Dashboard shows staleness indicator (green=fresh, red=stale)
- [ ] Dashboard has pull-to-refresh via RefreshControl
- [ ] Dashboard shows empty state when no context exists
- [ ] Zones screen shows placeholder text for S04
- [ ] Settings shows connected instance URL
- [ ] Settings has working sign-out button that clears credentials
- [ ] Zero TypeScript errors

## Verification

- `cd mobile && npx tsc --noEmit` exits with code 0
- `test -f mobile/src/app/\(app\)/\(tabs\)/_layout.tsx` — tab layout exists
- `test -f mobile/src/app/\(app\)/\(tabs\)/index.tsx` — dashboard exists
- `test -f mobile/src/app/\(app\)/\(tabs\)/zones.tsx` — zones placeholder exists
- `test -f mobile/src/app/\(app\)/\(tabs\)/settings.tsx` — settings exists
- `grep -q "RefreshControl" mobile/src/app/\(app\)/\(tabs\)/index.tsx` — pull-to-refresh implemented
- `grep -q "signOut" mobile/src/app/\(app\)/\(tabs\)/settings.tsx` — sign-out wired

## Inputs

- `mobile/src/api/client.ts` — SemPKMClient for context fetching (from T02)
- `mobile/src/ctx.tsx` — useSession for auth state and sign-out (from T02)
- `mobile/src/app/(app)/_layout.tsx` — route guard (from T03)

## Expected Output

- `mobile/src/app/(app)/(tabs)/_layout.tsx` — tab navigator with 3 tabs
- `mobile/src/app/(app)/(tabs)/index.tsx` — context dashboard with pull-to-refresh
- `mobile/src/app/(app)/(tabs)/zones.tsx` — placeholder for S04
- `mobile/src/app/(app)/(tabs)/settings.tsx` — connection info and sign-out
