# S05 Research: Mobile Calendar & Activity Detection

## Summary

S05 adds three context enrichment services to the mobile app: calendar event reading via `expo-calendar`, activity detection via `expo-sensors` (Accelerometer), and time-of-day classification (pure computation). All three feed into the existing `SemPKMClient.updateContext()` from S03, which POSTs to `/api/context/update` from S01. The backend already has `calendar_event`, `calendar_busy`, `activity`, and `time_period` fields on the `UserContext` model — no backend changes needed.

This is targeted work with known APIs applied to established patterns. The geofencing service from S04 provides the template for background task registration and credential-less context dispatch. The main engineering question is activity classification from raw accelerometer data — there's no built-in classifier in Expo, so a simple heuristic (acceleration magnitude variance over a sliding window) is needed.

**Risk:** Low-medium. Calendar and time-of-day are straightforward. Activity detection heuristic accuracy is inherently imperfect — the roadmap says "stationary/walking/driving" but accelerometer-only classification can't reliably distinguish driving from sitting (both are low-variance). Pedometer step counting can confirm walking but not driving. Acceptable for MVP — label as "best effort."

## Requirements Targeted

| Req | Description | How This Slice Addresses It |
|-----|-------------|---------------------------|
| CTX-12 | Mobile app reads device calendar for current event context | `expo-calendar` reads events, posts `calendar_event` + `calendar_busy` to context API |
| CTX-13 | Mobile app detects activity type (stationary/walking/driving) | Accelerometer heuristic + Pedometer step counting classifies activity, posts `activity` field |
| (implicit) | Time-of-day classification | Pure-computation service classifies current time into morning/work_hours/evening/night, posts `time_period` field |

## Recommendation

Build three independent service modules (`calendar.ts`, `activity.ts`, `time-period.ts`) under `mobile/src/services/`, each following the geofencing.ts credential-read + direct-fetch pattern for context dispatch. Wire them into the dashboard screen's lifecycle and/or a foreground polling interval. No backend changes required.

**Calendar monitoring strategy:** Foreground polling. `expo-calendar` has no push/subscription API — the app must poll `getEventsAsync()` on an interval to detect event boundaries. Poll every 60 seconds while the app is in the foreground. Use `AppState` change listener to re-check on app foregrounding. Background calendar checking is not possible without `expo-background-task` registration, and the accuracy need doesn't justify the battery cost.

**Activity detection strategy:** Accelerometer sampling at 1 Hz (1000ms interval), computing magnitude variance over a 10-sample sliding window. Classify: variance < 0.01 → stationary, variance < 0.15 → walking, variance ≥ 0.15 → driving/vehicle. Supplement with `Pedometer.watchStepCount()` — if step count is increasing, override to "walking" regardless of variance. Foreground only — Accelerometer subscriptions stop when the app is backgrounded.

**Time-of-day strategy:** Compute from `new Date()` against configurable hour boundaries. Default: morning (5:00–8:59), work_hours (9:00–16:59), evening (17:00–20:59), night (21:00–4:59). Re-evaluate on every context push and on app foreground.

## Implementation Landscape

### What Exists (Consume)

| File | Role | How S05 Uses It |
|------|------|----------------|
| `mobile/src/api/client.ts` | `SemPKMClient.updateContext()` | Calendar, activity, and time-period services call this to push context |
| `mobile/src/ctx.tsx` | `parseSession()` + `useSession()` | Get credentials for API client instantiation |
| `mobile/src/services/geofencing.ts` | Background task pattern | Template for module-scope task definition, SecureStore credential read |
| `mobile/src/app/(app)/(tabs)/index.tsx` | Dashboard screen | Displays context fields including calendar, activity, time_period already |
| `backend/app/context/router.py` | `POST /api/context/update` | Accepts `calendar_event`, `calendar_busy`, `activity`, `time_period` fields |
| `backend/app/context/models.py` | `UserContext` model | Already has all needed columns — no migration needed |
| `mobile/package.json` | Dependencies | Already has `expo-sensors` is NOT installed. Has `expo-task-manager`. |
| `mobile/app.json` | App config | Needs `expo-calendar` plugin entry for calendar permissions |

### What Must Be Built

| Component | Files | Complexity |
|-----------|-------|-----------|
| Calendar service | `mobile/src/services/calendar.ts` | Medium — permission request, getCalendarsAsync, getEventsAsync, event boundary detection, context dispatch |
| Activity detection service | `mobile/src/services/activity.ts` | Medium — Accelerometer subscription, sliding window, magnitude variance classification, Pedometer supplement |
| Time-of-day service | `mobile/src/services/time-period.ts` | Low — pure date computation with configurable boundaries |
| Context orchestrator hook | `mobile/src/hooks/useContextServices.ts` | Medium — coordinates all three services, manages intervals, handles AppState changes, deduplicates context updates |
| Dashboard integration | Modify `mobile/src/app/(app)/(tabs)/index.tsx` | Low — wire useContextServices hook, show active monitoring status |
| App config | Modify `mobile/app.json` | Low — add expo-calendar plugin entry |
| Package install | Modify `mobile/package.json` | Low — `npx expo install expo-calendar expo-sensors` |

### Dependencies to Install

```bash
cd mobile && npx expo install expo-calendar expo-sensors
```

`expo-calendar` requires a plugin entry in `app.json`:
```json
[
  "expo-calendar",
  {
    "calendarPermission": "SemPKM reads your calendar to detect meetings and focus blocks for automatic context updates."
  }
]
```

`expo-sensors` does not require a plugin entry — the Accelerometer and Pedometer work without native config changes. However, on Android 12+ (API 31), high-frequency sensor sampling (>200Hz) requires `HIGH_SAMPLING_RATE_SENSORS` permission — our 1Hz rate is well below this threshold.

## Key Patterns

### Calendar Service Pattern

```typescript
// mobile/src/services/calendar.ts
import * as Calendar from 'expo-calendar';

export async function getCurrentCalendarEvent(): Promise<{
  title: string | null;
  busy: boolean;
}> {
  const { status } = await Calendar.getCalendarPermissionsAsync();
  if (status !== 'granted') return { title: null, busy: false };
  
  const calendars = await Calendar.getCalendarsAsync();
  const now = new Date();
  const windowEnd = new Date(now.getTime() + 5 * 60_000); // 5 min lookahead
  
  const events = await Calendar.getEventsAsync(
    calendars.map(c => c.id),
    now,
    windowEnd,
  );
  
  if (events.length === 0) return { title: null, busy: false };
  
  // Pick the current event (or soonest starting)
  const current = events[0];
  return {
    title: current.title ?? null,
    busy: current.availability === 'busy' || current.availability == null,
  };
}
```

### Activity Classification Heuristic

The accelerometer reports `{ x, y, z }` in g-forces. Magnitude = `sqrt(x² + y² + z²)`. At rest, magnitude ≈ 1.0g (gravity). Movement adds variance:

- **Stationary:** magnitude variance < 0.01 over 10 samples (phone on desk or in pocket, no motion)
- **Walking:** variance 0.01–0.15 (rhythmic acceleration pattern)
- **Driving/Vehicle:** variance ≥ 0.15 OR (low variance + high step count = walking override)

The Pedometer provides a "walking" ground truth — if `Pedometer.watchStepCount()` reports increasing steps, the user is walking regardless of accelerometer variance.

### Context Orchestrator Pattern

A `useContextServices()` custom hook that:
1. Starts Accelerometer subscription on mount (1Hz)
2. Starts calendar polling interval (60s)
3. Computes time-period on each push
4. Listens for `AppState` changes to re-check calendar on foreground
5. Batches all three fields into a single `updateContext()` call to avoid hitting the 12/min rate limit
6. Debounces changes — only pushes when a field actually changed
7. Returns current detected state for dashboard display
8. Cleans up subscriptions on unmount

### Rate Limit Consideration

The backend enforces 12/min on `/api/context/update`. Three services polling independently could easily exceed this. The orchestrator must batch: collect all changed fields, push once per interval (minimum 10 seconds between pushes). The geofencing background task also calls this endpoint — the orchestrator should account for that by using a conservative push interval (30–60 seconds).

## Constraints

1. **No background calendar/activity monitoring.** `expo-calendar` and Accelerometer are foreground-only APIs. Background context enrichment would require `expo-background-task` which has OS-imposed minimum intervals (15+ minutes on iOS) and unreliable scheduling. Not worth the complexity for MVP — geofencing already handles the critical background signal (location).

2. **Calendar permission is separate from location permission.** Users must grant calendar access independently. The service should degrade gracefully when denied — `calendar_event: null, calendar_busy: false`.

3. **Activity classification is heuristic, not ground truth.** The accelerometer alone cannot reliably distinguish "driving" from "riding in a car while others drive" from "sitting on a vibrating train." The classification is best-effort. Label it clearly in the UI ("Detected activity").

4. **Time-period boundaries should be user-configurable eventually** but hardcoded defaults are fine for S05. The settings screen could gain a "Context Preferences" section in a future slice.

5. **Accelerometer availability varies.** Some Android devices don't have accelerometers. `Accelerometer.isAvailableAsync()` must be checked before subscribing. Degrade to "unknown" activity.

## Natural Task Decomposition

1. **T01: Calendar service + app config** — Install `expo-calendar`, add plugin to `app.json`, implement `calendar.ts` service with permission request, event fetching, and current-event detection. Unit-testable logic.

2. **T02: Activity detection service** — Install `expo-sensors` (if not already via expo), implement `activity.ts` with Accelerometer subscription, sliding window magnitude variance, Pedometer supplement, and activity classification. Pure logic + sensor wiring.

3. **T03: Time-period service + context orchestrator + dashboard wiring** — Implement `time-period.ts` (trivial), build `useContextServices.ts` hook that coordinates all three services with AppState monitoring, rate-limit-aware batching, and change deduplication. Wire into dashboard screen. Verify TypeScript compilation and all services present.

## Verification Approach

- `cd mobile && npx tsc --noEmit` — zero TypeScript errors
- All service files exist under `mobile/src/services/`
- `expo-calendar` plugin present in `app.json`
- `expo-calendar` and `expo-sensors` in `package.json` dependencies
- `useContextServices` hook imported in dashboard screen
- Calendar service handles permission denied gracefully (returns null/false)
- Activity service handles unavailable accelerometer (returns "unknown")
- Time-period classification covers all 24 hours without gaps
- Context orchestrator batches updates (doesn't call updateContext per-service)

## Skill Recommendations

The following skills could improve planner/executor quality for this slice:
- `expo/skills@building-native-ui` (21K installs) — relevant for React Native component patterns
- `callstackincubator/agent-skills@react-native-best-practices` (8.2K installs) — general RN best practices

Install: `npx skills add expo/skills@building-native-ui` / `npx skills add callstackincubator/agent-skills@react-native-best-practices`
