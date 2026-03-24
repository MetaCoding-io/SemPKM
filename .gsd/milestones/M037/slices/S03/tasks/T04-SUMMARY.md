---
id: T04
parent: S03
milestone: M037
provides:
  - Tab navigator with Dashboard, Zones, Settings tabs using Ionicons
  - Context dashboard screen with pull-to-refresh, staleness indicator, error/empty/loading states
  - Zones placeholder screen for S04
  - Settings screen with connected instance URL, app version, and sign-out button
key_files:
  - mobile/src/app/(app)/(tabs)/_layout.tsx
  - mobile/src/app/(app)/(tabs)/index.tsx
  - mobile/src/app/(app)/(tabs)/zones.tsx
  - mobile/src/app/(app)/(tabs)/settings.tsx
key_decisions:
  - Sign-out uses Alert.alert confirmation dialog to prevent accidental credential clearing
  - Removed T03's placeholder (app)/index.tsx — it would shadow the (tabs)/index.tsx route since expo-router matches direct files before group children
  - App version sourced from expo-constants (expoConfig.version) with fallback chain to manifest2 then hardcoded 1.0.0
patterns_established:
  - Context field cards use ContextField sub-component with label/value pattern and muted styling for unset values
  - Staleness indicator uses green/red dot + relative time string from updated_at timestamp
  - Pull-to-refresh pattern: RefreshControl with separate refreshing state so loading spinner only shows on initial fetch
observability_surfaces:
  - "Dashboard errors: inline red text for network errors (status 0) and server errors (with detail from API). Never silent."
  - "Staleness: green dot = fresh, red dot = stale (is_stale from API). Relative timestamp from updated_at."
  - "Empty state: explicit 'No context data yet' message distinguishes no-data from error."
  - "Sign-out: Alert confirmation before clearing credentials; route guard auto-redirects to /sign-in."
duration: 6m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T04: Dashboard, Tab Navigation & Settings

**Created three-tab navigator with context dashboard (pull-to-refresh, staleness indicator, error/empty states), zones placeholder, and settings screen with connection info and sign-out.**

## What Happened

Created the `(tabs)/_layout.tsx` tab navigator using expo-router's `Tabs` component with three screens: Dashboard (home icon), Zones (map icon), Settings (gear icon). Active tabs use filled Ionicons variants; inactive use outline. Active tint is blue (#2563eb).

Built the dashboard screen (`index.tsx`) with full context lifecycle: loading state shows centered ActivityIndicator, error state shows red text with retry button, empty state shows a "No context data yet" message, and the data state renders context fields in card-style layout. Each field (Location, Activity, Time Period, Calendar) is a `ContextField` sub-component with uppercase label and large value text. Unset values are muted gray. A staleness banner at the top shows a green (fresh) or red (stale) dot with a relative time string. Pull-to-refresh uses React Native's `RefreshControl` with a separate `refreshing` state so the full-screen loading spinner only appears on initial fetch.

The zones screen is a simple placeholder with a map-pin icon and "Coming in a future update" text, ready for S04 replacement.

Settings screen shows the connected instance URL parsed from the session JSON, app version from expo-constants, and a destructive-styled Sign Out button. The sign-out uses Alert.alert for confirmation before clearing credentials — once cleared, the route guard in `(app)/_layout.tsx` auto-redirects to `/sign-in`.

Removed the T03 placeholder `(app)/index.tsx` which would have conflicted with the `(tabs)/index.tsx` route.

## Verification

All task-level and slice-level verification checks pass:
- TypeScript compiles with zero errors
- All four tab files exist
- RefreshControl is used in the dashboard
- signOut is wired in settings
- Metro bundler starts and prints "Waiting on http://localhost:8081"
- Core modules (client.ts, ctx.tsx, useStorageState.ts) exist
- All screens (sign-in.tsx, (tabs)/index.tsx, (tabs)/settings.tsx) exist

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd mobile && npx tsc --noEmit` | 0 | ✅ pass | ~3s |
| 2 | `test -f mobile/src/app/(app)/(tabs)/_layout.tsx` | 0 | ✅ pass | <1s |
| 3 | `test -f mobile/src/app/(app)/(tabs)/index.tsx` | 0 | ✅ pass | <1s |
| 4 | `test -f mobile/src/app/(app)/(tabs)/zones.tsx` | 0 | ✅ pass | <1s |
| 5 | `test -f mobile/src/app/(app)/(tabs)/settings.tsx` | 0 | ✅ pass | <1s |
| 6 | `grep -q "RefreshControl" mobile/src/app/(app)/(tabs)/index.tsx` | 0 | ✅ pass | <1s |
| 7 | `grep -q "signOut" mobile/src/app/(app)/(tabs)/settings.tsx` | 0 | ✅ pass | <1s |
| 8 | `cd mobile && CI=1 timeout 20 npx expo start --no-dev --non-interactive` (slice V2) | 0 | ✅ pass | ~20s |
| 9 | `test -f mobile/src/api/client.ts && test -f mobile/src/ctx.tsx && test -f mobile/src/hooks/useStorageState.ts` (slice V3) | 0 | ✅ pass | <1s |
| 10 | `test -f mobile/src/app/sign-in.tsx && test -f mobile/src/app/(app)/(tabs)/index.tsx && test -f mobile/src/app/(app)/(tabs)/settings.tsx` (slice V4) | 0 | ✅ pass | <1s |

## Diagnostics

- `cd mobile && npx tsc --noEmit` — TypeScript compilation health
- `grep -c "setError" mobile/src/app/(app)/(tabs)/index.tsx` — count error-setting paths in dashboard
- `grep "RefreshControl" mobile/src/app/(app)/(tabs)/index.tsx` — verify pull-to-refresh presence
- `grep "signOut" mobile/src/app/(app)/(tabs)/settings.tsx` — verify sign-out wiring
- Dashboard error display: SemPKMError.status === 0 → "Could not reach server"; other status → "Server error: {detail}"
- Empty state visible when `getCurrentContext()` returns null
- Sign-out observable: Alert confirmation → session cleared → route guard redirects to /sign-in

## Deviations

- Removed `mobile/src/app/(app)/index.tsx` (T03 placeholder) — necessary because expo-router matches direct files before group routes, which would prevent the `(tabs)/_layout.tsx` from rendering. Not in the task plan but required for correct tab navigation.
- Used `location-outline` icon for zones tab instead of `map-pin` — Ionicons doesn't have `map-pin`, and the plan specified `map-outline`/`map` which works for the tab bar. The zones screen body uses `location-outline` as a larger decorative icon since it better represents geofencing.

## Known Issues

None.

## Files Created/Modified

- `mobile/src/app/(app)/(tabs)/_layout.tsx` — Tab navigator with 3 tabs (Dashboard, Zones, Settings) using Ionicons
- `mobile/src/app/(app)/(tabs)/index.tsx` — Dashboard screen with context fetch, staleness indicator, pull-to-refresh, error/empty/loading states
- `mobile/src/app/(app)/(tabs)/zones.tsx` — Placeholder screen for zone management (S04)
- `mobile/src/app/(app)/(tabs)/settings.tsx` — Settings screen with instance URL, app version, sign-out button
- `mobile/src/app/(app)/index.tsx` — DELETED (T03 placeholder, conflicted with tabs group routing)
- `.gsd/milestones/M037/slices/S03/tasks/T04-PLAN.md` — Added Observability Impact section
