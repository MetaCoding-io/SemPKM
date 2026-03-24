# S03 UAT: Mobile App Foundation & API Connection

## Preconditions

- SemPKM backend running in Docker (`docker compose up -d`)
- Node.js 18+ available on host
- `cd mobile && npm install` completed
- A valid SemPKM user account exists with login credentials
- An API key has been generated (or will be generated via the Settings UI)
- iOS Simulator or Android Emulator available, OR physical device with Expo Go / dev build

## Test Environment Setup

1. Start the backend: `docker compose -f docker-compose.yml up -d`
2. Start Metro: `cd mobile && npx expo start`
3. Open the app on simulator/device via QR code or `i` (iOS) / `a` (Android)

---

## TC-01: Metro Bundler Starts

**Steps:**
1. `cd mobile && npx expo start`

**Expected:**
- Metro prints "Starting Metro Bundler" and "Waiting on http://localhost:8081"
- No errors in terminal output
- QR code displayed for device connection

---

## TC-02: TypeScript Compilation Clean

**Steps:**
1. `cd mobile && npx tsc --noEmit`

**Expected:**
- Exit code 0, no output (zero type errors)

---

## TC-03: Unauthenticated User Redirected to Sign-In

**Steps:**
1. Launch app on simulator/device (fresh install, no stored credentials)
2. Observe which screen appears

**Expected:**
- Sign-in screen shows with "Instance URL" and "API Key" fields
- "Connect" button visible
- No flash of the dashboard or tabs before redirect

---

## TC-04: Sign-In — Invalid URL Format

**Steps:**
1. On sign-in screen, enter "not-a-url" in Instance URL field
2. Enter any text in API Key field
3. Tap "Connect"

**Expected:**
- Error message: "URL must start with http:// or https://"
- No network request made
- Fields remain editable

---

## TC-05: Sign-In — Unreachable Server

**Steps:**
1. Enter "https://nonexistent.example.com" as Instance URL
2. Enter "test-key-123" as API Key
3. Tap "Connect"

**Expected:**
- ActivityIndicator appears on button during connection attempt
- After timeout, error message: "Could not reach server. Check the URL and your connection."
- Button returns to "Connect" state

---

## TC-06: Sign-In — Invalid API Key

**Steps:**
1. Enter the real SemPKM instance URL (e.g., "http://localhost:3901")
2. Enter "wrong-key-definitely-invalid" as API Key
3. Tap "Connect"

**Expected:**
- ActivityIndicator during connection
- Error message: "Invalid API key. Check your credentials."
- Fields remain editable

---

## TC-07: Sign-In — Successful Connection

**Steps:**
1. Enter the real SemPKM instance URL
2. Enter a valid API key
3. Tap "Connect"

**Expected:**
- ActivityIndicator during connection
- App navigates to Dashboard tab
- Three tabs visible at bottom: Dashboard, Zones, Settings
- No error messages

---

## TC-08: Dashboard — No Context Data

**Steps:**
1. Sign in successfully (TC-07)
2. Observe Dashboard screen (assuming no context has been posted)

**Expected:**
- "No context data yet" empty state message displayed
- No error indicators
- Pull-to-refresh gesture is available

---

## TC-09: Dashboard — Context Data Displayed

**Steps:**
1. Post context via API: `curl -X POST http://localhost:3901/api/context/update -H "Authorization: Bearer <api-key>" -H "Content-Type: application/json" -d '{"location_zone":"office","activity":"stationary","time_period":"work_hours","calendar_event":"Team standup"}'`
2. Open Dashboard tab (or pull to refresh)

**Expected:**
- Location field shows "office"
- Activity field shows "stationary"
- Time Period field shows "work_hours"
- Calendar field shows "Team standup"
- Green dot staleness indicator (context is fresh)
- Relative timestamp shown (e.g., "just now")

---

## TC-10: Dashboard — Stale Context Indicator

**Steps:**
1. Post context (TC-09)
2. Wait 16+ minutes (or temporarily reduce TTL to 1 minute for testing)
3. Pull to refresh on Dashboard

**Expected:**
- Red dot staleness indicator
- Context fields still show last known values
- `is_stale: true` reflected in the staleness display

---

## TC-11: Dashboard — Pull-to-Refresh

**Steps:**
1. Post context (TC-09)
2. Pull down on dashboard screen

**Expected:**
- Refresh indicator appears briefly
- Context data refreshes from API
- No full-screen loading spinner (only the pull-to-refresh control)

---

## TC-12: Dashboard — Network Error Recovery

**Steps:**
1. Sign in successfully
2. Stop the backend (`docker compose down`)
3. Pull to refresh on Dashboard

**Expected:**
- Error message displayed inline (not a crash)
- Message indicates network/connection error
4. Restart backend, pull to refresh again
5. Context data loads successfully

---

## TC-13: Zones Tab — Placeholder

**Steps:**
1. Tap the "Zones" tab

**Expected:**
- Placeholder screen with "Coming in a future update" or similar text
- Map-pin or location icon visible
- No crash, no blank screen

---

## TC-14: Settings — Instance URL Displayed

**Steps:**
1. Tap the "Settings" tab

**Expected:**
- Connected instance URL shown (matches what was entered at sign-in)
- App version displayed
- "Sign Out" button visible

---

## TC-15: Sign-Out — Confirmation Dialog

**Steps:**
1. On Settings screen, tap "Sign Out"

**Expected:**
- Confirmation dialog appears ("Are you sure?" or similar)
- Cancel button returns to Settings
- Confirm button proceeds to sign out

---

## TC-16: Sign-Out — Redirect to Sign-In

**Steps:**
1. Confirm sign-out (TC-15)

**Expected:**
- App navigates to sign-in screen
- All credential fields are empty
- Navigating back does NOT show Dashboard (credentials cleared)

---

## TC-17: Sign-Out and Re-Sign-In

**Steps:**
1. Sign out (TC-15 + TC-16)
2. Enter valid instance URL and API key
3. Tap "Connect"

**Expected:**
- Connection succeeds
- Dashboard loads with current context (if any posted)
- Full app navigation works again

---

## TC-18: API Key Not Exposed

**Steps:**
1. On sign-in screen, type API key into the field

**Expected:**
- Characters are masked (dots/bullets, not visible text)
- API key is never displayed in plain text anywhere in the app
- Settings screen does NOT show the API key

---

## Edge Cases

### EC-01: App Kill and Relaunch
1. Sign in successfully, close the app completely (swipe away)
2. Relaunch the app
3. **Expected:** App goes directly to Dashboard (credentials persisted in secure store), no sign-in screen

### EC-02: Empty API Key
1. Enter valid URL but leave API Key empty
2. Tap "Connect"
3. **Expected:** Error or disabled button — connection not attempted with empty key

### EC-03: URL with Trailing Slash
1. Enter "http://localhost:3901/" (with trailing slash)
2. Enter valid API key, tap "Connect"
3. **Expected:** Connection succeeds (trailing slash handled gracefully)
