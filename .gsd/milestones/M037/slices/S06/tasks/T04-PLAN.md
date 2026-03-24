---
estimated_steps: 5
estimated_files: 6
skills_used:
  - best-practices
---

# T04: Mobile app expo-notifications integration

**Slice:** S06 — Push Notifications with Context Filtering
**Milestone:** M037

## Description

Add push notification support to the React Native mobile app. Install `expo-notifications` and `expo-device`, implement a notification service that requests permission, retrieves the native FCM/APNs token, and registers it with the backend. Add notification preference API methods to the client. Update the settings screen with a notifications section showing permission status and a toggle. Wire the registration into the app layout so it runs after authentication.

## Steps

1. **Add dependencies and plugin config**:
   - Add `expo-notifications` and `expo-device` to `mobile/package.json` dependencies. (Use `"expo-notifications": "~0.29.x"` and `"expo-device": "~7.0.x"` — matching the Expo SDK version already in use.)
   - Add `"expo-notifications"` to the `plugins` array in `mobile/app.json`. For Android, configure the notification icon and channel:
     ```json
     ["expo-notifications", {
       "icon": "./assets/images/notification-icon.png",
       "color": "#208AEF"
     }]
     ```
   - If `expo-device` is not already in package.json, add it and add `"expo-device"` to plugins.

2. **Create `mobile/src/services/notifications.ts`**:
   - `registerForPushNotifications(client: SemPKMClient)`: Check `Device.isDevice` (simulators can't get push tokens). Call `Notifications.getPermissionsAsync()`. If not granted, call `Notifications.requestPermissionsAsync()`. If still not granted, return early. Call `Notifications.getDevicePushTokenAsync()` for native FCM/APNs token (NOT Expo push token — per D338). Call `client.registerPushToken(token.data, Platform.OS)`.
   - `setupNotificationHandler()`: Call `Notifications.setNotificationHandler({handleNotification: async () => ({shouldShowAlert: true, shouldPlaySound: true, shouldSetBadge: true})})` to show notifications even when app is in foreground. Register `addNotificationResponseReceivedListener` for tap-to-navigate handling (log for now — deep linking is S07 territory).
   - `setupAndroidChannel()`: For Android, create a default notification channel: `Notifications.setNotificationChannelAsync('default', {name: 'Default', importance: Notifications.AndroidImportance.MAX, vibrationPattern: [0, 250, 250, 250]})`.
   - Export all three functions.

3. **Add notification API methods to `mobile/src/api/client.ts`**:
   - Add TypeScript interfaces: `NotificationPreferences` (enabled, quiet_hours_start, quiet_hours_end, suppress_when_busy, enabled_types), `RegisterTokenPayload` (token, platform, device_name?), `TestNotificationResponse` (sent_count, suppressed, reason?).
   - Add methods to `SemPKMClient`:
     - `registerPushToken(token: string, platform: string, deviceName?: string)` → POST `/api/notifications/register`
     - `getNotificationPreferences()` → GET `/api/notifications/preferences`
     - `updateNotificationPreferences(prefs: Partial<NotificationPreferences>)` → PUT `/api/notifications/preferences`
     - `sendTestNotification()` → POST `/api/notifications/test`

4. **Update `mobile/src/app/(app)/(tabs)/settings.tsx`**:
   - Add a "Push Notifications" section between Connection and About sections.
   - Show current permission status (granted/denied/undetermined) via `Notifications.getPermissionsAsync()` on mount.
   - Add a "Request Permission" button if status is not granted.
   - Add an "Enable Notifications" toggle that calls `updateNotificationPreferences({enabled: true/false})`.
   - Add a "Send Test" button that calls `sendTestNotification()` and shows an Alert with the result.
   - Handle the `Device.isDevice` check — show "Not available on simulator" message when appropriate.

5. **Wire registration into app layout `mobile/src/app/(app)/_layout.tsx`**:
   - Import and call `setupNotificationHandler()` and `setupAndroidChannel()` in a top-level `useEffect` (runs once on mount).
   - After detecting a valid session, call `registerForPushNotifications(client)` where `client` is the SemPKMClient instance. This should be fire-and-forget (don't block the UI).
   - Wrap in try/catch — push registration failure must not break app startup.

## Must-Haves

- [ ] `expo-notifications` and `expo-device` in package.json
- [ ] `expo-notifications` plugin in app.json
- [ ] `notifications.ts` service with permission request, native token retrieval, backend registration
- [ ] `getDevicePushTokenAsync()` used (NOT Expo push token — D338)
- [ ] `Device.isDevice` check (simulators can't get tokens)
- [ ] Client methods for register, preferences CRUD, test send
- [ ] Settings screen shows notification permission status + toggle
- [ ] Android notification channel setup
- [ ] Registration runs after authentication in app layout
- [ ] TypeScript compiles without errors

## Verification

- `cd mobile && npx tsc --noEmit` — TypeScript compiles without errors
- `grep -q "expo-notifications" mobile/package.json` — dependency added
- `grep -q "expo-notifications" mobile/app.json` — plugin configured
- `test -f mobile/src/services/notifications.ts` — service file exists
- `grep -q "registerPushToken" mobile/src/api/client.ts` — client method added
- `grep -q "getDevicePushTokenAsync" mobile/src/services/notifications.ts` — native token used (not Expo token)

## Inputs

- `mobile/package.json` — existing dependencies to extend
- `mobile/app.json` — existing plugins array to extend
- `mobile/src/api/client.ts` — SemPKMClient to add notification methods
- `mobile/src/services/permissions.ts` — existing permission request pattern
- `mobile/src/app/(app)/(tabs)/settings.tsx` — existing settings screen to extend
- `mobile/src/app/(app)/_layout.tsx` — app layout for registration wiring

## Expected Output

- `mobile/package.json` — modified: expo-notifications, expo-device dependencies
- `mobile/app.json` — modified: expo-notifications plugin
- `mobile/src/services/notifications.ts` — new: permission request, token registration, handlers
- `mobile/src/api/client.ts` — modified: notification API methods + interfaces
- `mobile/src/app/(app)/(tabs)/settings.tsx` — modified: Push Notifications section
- `mobile/src/app/(app)/_layout.tsx` — modified: notification setup + registration on auth

## Observability Impact

- **New runtime signals:** `notifications.permission_status` (granted/denied/undetermined), `notifications.token_registered` (platform, token prefix), `notifications.handler_setup` (foreground display enabled), `notifications.registration_error` (error message)
- **Inspection surface:** Settings screen shows live permission status (granted/denied/undetermined), enable toggle state, and test-send button with result display
- **Failure visibility:** `Device.isDevice` check surfaces "Not available on simulator" in Settings UI; token registration failures are caught and logged without breaking app startup; network errors from `registerPushToken()` throw `SemPKMError` with status code and detail
- **Redaction:** FCM/APNs tokens are never displayed in UI — only the registration success/failure status is shown
