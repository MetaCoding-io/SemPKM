---
estimated_steps: 4
estimated_files: 3
skills_used: []
---

# T01: Calendar service with expo-calendar integration

**Slice:** S05 — Mobile Calendar & Activity Detection
**Milestone:** M037

## Description

Install `expo-calendar` and `expo-sensors` into the mobile project, configure the `expo-calendar` plugin in `app.json` with a calendar permission string, and implement a calendar service that reads device calendar events. This directly addresses requirement CTX-12: "Mobile app reads device calendar for current event context."

The service must handle the full lifecycle: requesting permission, reading calendars, fetching events in a time window around "now", and returning the current/upcoming event title + busy status. When permission is denied, it returns null/false gracefully.

## Steps

1. Run `cd mobile && npx expo install expo-calendar expo-sensors` to add both packages. Verify they appear in `package.json` dependencies.

2. Add the `expo-calendar` plugin entry to `mobile/app.json` under `plugins` with the permission string: `"SemPKM reads your calendar to detect meetings and focus blocks for automatic context updates."` Note: `expo-sensors` does not require a plugin entry (1Hz sampling is well below Android's HIGH_SAMPLING_RATE_SENSORS threshold).

3. Create `mobile/src/services/calendar.ts` with:
   - `requestCalendarPermission()` — requests calendar read permission via `Calendar.requestCalendarPermissionsAsync()`. Returns `boolean` (granted or not). Caches the permission status in a module-level variable to avoid repeated OS prompts.
   - `getCurrentCalendarEvent()` — returns `Promise<{ title: string | null; busy: boolean }>`. If permission not granted, returns `{ title: null, busy: false }`. Otherwise: gets all calendars via `Calendar.getCalendarsAsync()`, fetches events from `now` to `now + 5 minutes` via `Calendar.getEventsAsync()`, picks the current event (or soonest starting), extracts title and busy status (`availability === 'busy'` or availability is null/undefined).
   - Handle edge cases: no calendars found, no events in window, event with empty title.

4. Verify TypeScript compiles: `cd mobile && npx tsc --noEmit`.

## Must-Haves

- [ ] `expo-calendar` and `expo-sensors` in `mobile/package.json` dependencies
- [ ] `expo-calendar` plugin in `mobile/app.json` with permission string
- [ ] `calendar.ts` exports `requestCalendarPermission` and `getCurrentCalendarEvent`
- [ ] Permission denied returns `{ title: null, busy: false }` (graceful degradation)
- [ ] TypeScript compiles with zero errors

## Verification

- `cd mobile && npx tsc --noEmit` — zero errors
- `grep -q '"expo-calendar"' mobile/package.json` — dependency present
- `grep -q '"expo-sensors"' mobile/package.json` — dependency present
- `grep -q 'expo-calendar' mobile/app.json` — plugin configured
- `test -f mobile/src/services/calendar.ts` — file exists

## Inputs

- `mobile/package.json` — current dependency list (needs expo-calendar, expo-sensors added)
- `mobile/app.json` — current Expo config (needs expo-calendar plugin added to plugins array)
- `mobile/src/services/geofencing.ts` — reference pattern for service module structure

## Observability Impact

- **New signals:** `calendar.permission_granted`, `calendar.permission_denied`, `calendar.events_fetched` (with count), `calendar.no_calendars`, `calendar.error` — all structured console logs for Expo dev tools filtering.
- **Inspection:** `requestCalendarPermission()` returns boolean and caches status in a module-level variable. `getCurrentCalendarEvent()` returns typed `{ title, busy }` — inspectable in any caller's state.
- **Failure visibility:** Permission denied → returns `{ title: null, busy: false }` (never throws). API errors from `Calendar.*` are caught and logged with `calendar.error` key before returning graceful default. No calendars found → logged as `calendar.no_calendars`.

## Expected Output

- `mobile/package.json` — updated with expo-calendar and expo-sensors dependencies
- `mobile/app.json` — updated with expo-calendar plugin entry
- `mobile/src/services/calendar.ts` — new file with requestCalendarPermission and getCurrentCalendarEvent
