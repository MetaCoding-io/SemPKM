# Chapter 48: Mobile App & Context

The SemPKM **mobile app** turns your phone into a context provider for your
knowledge workspace. It is not a full SemPKM client — you don't browse or
edit objects from it. Instead, it continuously reports your real-world context
(location zone, activity, time period, calendar event) to the server, which
uses that context to switch personas, trigger notifications, and surface
relevant information in the workspace sidebar.

Key capabilities:

- **Geofence zones** — define named locations (Home, Office, Library) on a
  map; the app detects when you enter or leave each zone
- **Calendar integration** — reads your device calendar to report the current
  event title and busy/free status
- **Activity detection** — uses device motion APIs to report whether you are
  stationary, walking, driving, or cycling
- **Time period classification** — labels the current time as morning,
  afternoon, evening, or night based on configurable boundaries
- **Push notifications** — receives persona-switch alerts, rule-triggered
  notifications, and reminders from the server
- **Context dashboard** — shows both server-reported and device-detected
  context values with staleness indicators

The workspace sidebar displays a **context indicator chip** that updates in
real time via SSE, showing your current zone, activity, time period, and
calendar event at a glance.

---

## Prerequisites

Before installing the mobile app, ensure:

1. Your SemPKM instance is running and reachable over the network (not just
   `localhost` — your phone must be able to reach the server's IP or domain).
2. You have generated an **API key** in **Settings → API Keys** on the
   SemPKM web interface.
3. Your instance has the context system enabled (it is enabled by default in
   SemPKM 1.x).

---

## Installation

### Development Build (Expo)

For local development or testing, run the app via Expo:

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with **Expo Go** on your device, or press `i` / `a` to open
in the iOS Simulator or Android Emulator.

> **Note:** Geofencing requires a physical device. The iOS Simulator and
> Android Emulator do not trigger real geofence enter/exit events.

### Production Build

For production builds distributed via TestFlight (iOS) or Play Store (Android):

```bash
npx expo prebuild
npx expo run:ios   # or npx expo run:android
```

The app's bundle identifiers are `app.sempkm.mobile` (iOS) and
`app.sempkm.mobile` (Android), configured in `mobile/app.json`.

---

## Onboarding

When you launch the app for the first time, you see the **Sign In** screen.

1. Enter your **Instance URL** — the full URL of your SemPKM server, e.g.
   `https://sempkm.example.com` or `http://192.168.1.50:8080`.
2. Enter your **API Key** — the key you generated in the web interface.
3. Tap **Connect**.

The app tests the connection by calling `GET /.well-known/sempkm` on your
server. If the connection succeeds, you are taken to the main dashboard. If
it fails, an error message tells you what went wrong:

| Error                          | Cause                                      |
|--------------------------------|--------------------------------------------|
| *URL must start with http(s)://* | The URL format is invalid.                |
| *Could not reach server*       | Network issue — phone can't reach the URL. |
| *Server error: 401*            | The API key is invalid or expired.         |
| *Server error: 5xx*            | The server is having issues.               |

Credentials are stored securely in the device's keychain via `expo-secure-store`
and persist across app restarts.

---

## The Dashboard Tab

The main screen shows a **Context Dashboard** with two sections:

### Server-Reported Context

These values come from the SemPKM server (via `GET /api/context/current`) and
reflect the last context update the server received from any device:

| Field           | Example Value     | Description                            |
|-----------------|-------------------|----------------------------------------|
| **Location**    | Office            | Name of the zone you're in             |
| **Activity**    | stationary        | Detected physical activity             |
| **Time Period** | morning           | Current time-of-day classification     |
| **Calendar**    | Sprint Planning   | Current calendar event title           |
| **Busy**        | Yes / No          | Whether the current event is busy      |

### Device-Detected Context

Below the server section, the dashboard shows what your device is currently
detecting locally — before it has been sent to the server. This is useful for
verifying that sensors are working:

| Field           | Source                    |
|-----------------|---------------------------|
| **Calendar**    | Device calendar via expo-calendar |
| **Activity**    | Motion sensors via expo-activity  |
| **Time Period** | Local clock + configured boundaries |

### Staleness Indicator

Each server-reported field shows a relative timestamp ("2m ago", "1h ago").
If the context is older than the configured TTL (default: 5 minutes), the
field appears with a warning style indicating stale data.

### Pull to Refresh

Pull down on the dashboard to re-fetch the latest context from the server.
The refresh also triggers a new context push from the device, ensuring both
local and server values are up to date.

---

## The Zones Tab

The **Zones** tab provides a map interface for managing geofence zones. Zones
are named geographic regions that the app monitors in the background. When you
enter or leave a zone, the app sends a context update to the server.

### Viewing Zones

The top half of the screen shows a **MapView** with:

- Your current location (blue dot, requires location permission)
- Colored circles for each configured zone
- A marker at the center of each zone showing its name

The bottom half lists all zones with their name, radius, and an enable/disable
toggle.

### Adding a Zone

1. **Long-press** on the map at the desired location. A pin appears and the
   **Zone Editor** modal opens.
2. Enter a **name** for the zone (e.g. "Office", "Gym", "Coffee Shop").
3. Set the **radius** in meters (default: 200m). Smaller radii require more
   precise GPS and may not trigger reliably.
4. Tap **Save**. The zone appears on the map and in the list below.

### Editing a Zone

Tap a zone in the list to re-open the Zone Editor. You can change the name,
radius, or delete the zone entirely.

### Enable / Disable

Each zone has a toggle switch. Disabled zones remain saved but are not
registered as geofences — the app won't monitor them until re-enabled.

### iOS Geofence Limit

iOS imposes a hard limit of **20 monitored regions** per app. When you
approach 15 zones, the app shows a warning. At 20 zones, you cannot add more
without disabling or deleting existing ones.

Android does not have a practical limit for typical usage.

### Permissions

On first access, the Zones tab requests location permissions:

- **iOS:** "Allow While Using App" is sufficient for map display. "Always
  Allow" is required for background geofencing.
- **Android:** "Allow all the time" is required for background geofencing.

If you deny permissions, the map still displays but zone monitoring will not
work. You can re-enable permissions in your device's Settings app.

---

## Auto-Persona Rules

Auto-persona rules let SemPKM automatically switch your workspace persona
based on context conditions. Rules are configured in the **web interface**,
not in the mobile app.

### Creating a Rule

1. Navigate to **Settings → Context Rules** in the SemPKM web interface.
2. Click **New Rule**.
3. Define **conditions** — each condition matches a context field:
   - **Location equals** "Office"
   - **Time period equals** "morning"
   - **Activity equals** "stationary"
   - **Calendar busy** is true
4. Select the **target persona** to activate when all conditions match.
5. Set a **priority** (lower number = higher priority). When multiple rules
   match, the highest-priority rule wins.
6. Save the rule.

### How Rules Evaluate

When the mobile app sends a context update, the server:

1. Persists the new context values.
2. Evaluates all enabled rules against the updated context.
3. If a rule matches and its target persona differs from the current persona,
   switches the persona automatically.
4. Sends a push notification to the device (if enabled) confirming the switch.

Rules use AND logic — all conditions must match for the rule to fire. If no
rules match, the current persona remains unchanged.

### Testing a Rule

Use the **Test Rule** button on any rule in the web interface. This evaluates
the rule against the current context snapshot and shows whether it would fire,
without actually switching the persona. The test endpoint is
`POST /api/context/rules/test`.

---

## Push Notifications

The mobile app can receive push notifications from the SemPKM server for
persona switches, rule-triggered events, and custom reminders.

### Enabling Notifications

1. Open the **Settings** tab in the mobile app.
2. Under **Notifications**, tap **Enable Notifications**.
3. The app requests OS-level notification permission. Accept the prompt.
4. Once granted, the app registers its push token with the server.

The current permission status is displayed on the Settings screen:
`granted`, `denied`, or `undetermined`.

### Notification Preferences

Toggle **Notifications Enabled** on or off to control whether the server
sends push notifications to this device. Disabling notifications does not
revoke the OS permission — it tells the server to skip this device when
dispatching.

Additional preferences (configured in the web interface at
**Settings → Notifications**):

| Setting              | Default | Description                              |
|----------------------|---------|------------------------------------------|
| **Quiet Hours**      | Off     | Suppress notifications between set times |
| **Suppress When Busy** | Off   | Skip notifications during busy calendar events |

### Test Send

On the Settings tab, tap **Send Test Notification** to trigger a test push
from the server via `POST /api/notifications/test`. A notification should
arrive within a few seconds. If it doesn't:

- Check that the OS permission is `granted`.
- Verify the device is a physical device (push tokens are not available on
  simulators/emulators).
- Check that **Notifications Enabled** is toggled on.
- Verify your server can reach the Expo push notification service
  (`https://exp.host/--/api/v2/push/send`).

---

## Workspace Context Indicator

The SemPKM workspace sidebar displays a **context indicator chip** that shows
your current context at a glance. This indicator updates in real time via
Server-Sent Events (SSE).

### What It Shows

The chip displays compact tokens for each context dimension:

| Token           | Example       | Source                    |
|-----------------|---------------|---------------------------|
| **Location**    | 📍 Office     | Last zone enter event     |
| **Activity**    | 🚶 walking    | Device motion detection   |
| **Time Period** | 🌅 morning    | Server clock classification |
| **Calendar**    | 📅 Sprint Planning | Device calendar sync  |

### Real-Time Updates

The indicator subscribes to SSE events from the server. When the mobile app
sends a context update, the workspace reflects the change within seconds —
no page refresh needed.

### Stale State

If the server has not received a context update within the configured TTL
(default: 5 minutes), the indicator chip switches to a **stale** appearance
(muted colors, "stale" label). This tells you the context data may be
outdated — the mobile app might be offline, in airplane mode, or the
background task was killed by the OS.

The indicator is implemented in `frontend/static/js/context-indicator.js`
and styled in `frontend/static/css/context-indicator.css`.

---

## Troubleshooting

### Context shows as stale

The server hasn't received an update recently.

- **Check device connectivity.** The phone must be able to reach the server.
- **Check TTL settings.** The default TTL is 5 minutes. If the mobile app
  sends updates less frequently (e.g. only on zone transitions), staleness
  is expected between events.
- **Check background app restrictions.** Both iOS and Android can kill
  background tasks. Ensure SemPKM is not battery-optimized (Android) or
  that Background App Refresh is enabled (iOS).

### Geofence not triggering

Zone enter/exit events are not being reported.

- **Check location permissions.** Background geofencing requires "Always
  Allow" (iOS) or "Allow all the time" (Android).
- **Check zone radius.** Very small radii (under 100m) may not trigger
  reliably, especially on iOS where the OS batches location updates.
- **Check iOS region limit.** If you have more than 20 zones enabled,
  only the first 20 are registered. Disable unused zones.
- **Restart the app.** If the background task was killed, reopening the
  app re-registers all geofences.

### Notifications not arriving

Push notifications are not being received.

- **Verify OS permission.** Check the Settings tab — permission status must
  be `granted`.
- **Physical device required.** Push tokens are not available on
  simulators or emulators.
- **Check server connectivity.** The server must be able to reach
  `https://exp.host/--/api/v2/push/send` (Expo push service).
- **Check Notifications Enabled toggle.** If disabled on the Settings tab,
  the server skips this device.
- **Send a test notification.** Use the "Send Test Notification" button on
  the Settings tab to isolate whether the issue is server-side or device-side.

### Permission revoked after initial grant

If you revoke location or notification permissions in your device's Settings
app, the mobile app detects this on next launch and shows a prompt to re-enable.
You cannot re-grant permissions from within the app — you must navigate to:

- **iOS:** Settings → SemPKM → Location / Notifications
- **Android:** Settings → Apps → SemPKM → Permissions

### Updates lost when offline

The mobile app does not currently queue context updates for offline delivery.
If the device cannot reach the server, the update is silently dropped. When
connectivity returns, the next scheduled update (zone transition, calendar
change, or periodic refresh) will bring the server up to date.

A future version may add offline queuing with automatic replay on reconnect.

---

**Previous:** [Chapter 47: Asana Sync](47-asana-sync.md) | **Next:** [Appendices](appendix-a-environment-variables.md)
