# S05: Context-Driven Adaptation + Mobile — UAT Script

## Preconditions

- Docker dev stack running (`docker compose up -d`)
- Media scheduler app installed and running (verified via Admin > Applications)
- At least one podcast source subscribed with discovered episodes (S01)
- At least one schedule rule configured (S02) — e.g., "when commuting, play podcasts"
- Daily plan generated with entries visible in the Today view
- M037 context API operational (`GET /api/context/stream` returns SSE events)
- Mobile Expo app running on device/emulator with valid session

---

## Test 1: Context SSE Connection on App Startup

**Steps:**
1. Restart the media scheduler app (Admin > Applications > media-scheduler > Restart)
2. Check backend logs for `context_service` entries

**Expected:**
- Log entry: `context_service.sse_connected` appears within 5s of startup
- `get_context_subscription_status()` returns `connected: true`, `reconnect_count: 0`

---

## Test 2: Debounced Plan Re-evaluation on Activity Change

**Steps:**
1. Open the Media Scheduler app in the workspace
2. Navigate to the Today view and note the current plan entries
3. POST a context update to `/api/context` with `{"activity": "running"}` (non-location change)
4. Watch logs for 120 seconds

**Expected:**
- Log: `context_service.debounce_started` appears immediately after the context update
- Log: `context_service.debounce_fired` appears ~120s later
- Log: `context_service.plan_generation_completed` follows the debounce fire
- Today view entries may change if a rule matches the new activity

---

## Test 3: Immediate Re-evaluation on Location Zone Change

**Steps:**
1. POST a context update to `/api/context` with `{"location_zone": "office"}` 
2. Immediately check logs

**Expected:**
- Log: `context_service.debounce_cancelled` if a previous debounce was pending
- Log: `context_service.plan_generation_completed` appears within seconds (no 120s wait)
- Plan regenerates immediately — today view reflects updated rules matching "office"

---

## Test 4: Entry Status — Mark as Completed

**Steps:**
1. Open Today view in the Media Scheduler app
2. Locate any queued plan entry
3. Click the ✓ (Complete) button on the entry

**Expected:**
- Button area replaced by a green "completed" status badge
- Entry card gains `ms-entry-done` visual state (muted appearance)
- Action buttons (complete/skip/save) no longer visible on that entry
- Other queued entries remain interactive

---

## Test 5: Entry Status — Mark as Skipped

**Steps:**
1. Locate another queued plan entry in the Today view
2. Click the → (Skip) button

**Expected:**
- Status badge shows "skipped"
- Entry card gains done visual state
- Action buttons removed from the entry

---

## Test 6: Entry Status — Mark as Saved

**Steps:**
1. Locate another queued entry
2. Click the ♡ (Save) button

**Expected:**
- Status badge shows "saved" (blue badge per CSS)
- Entry card gains done visual state

---

## Test 7: JSON Suggestion Endpoint

**Steps:**
1. Open browser dev tools or curl: `GET /app/media-scheduler/_fragments/current-suggestion/json`

**Expected:**
- Response `Content-Type: application/json`
- JSON body contains: `title`, `slot_start`, `slot_end`, `status`, `source_type`, `source_title`, `enclosure_url`, `duration_seconds`
- `status` is one of: `queued`, `active`, `none`
- If no plan entries exist, `status` is `none` and other fields are absent

---

## Test 8: JSON Endpoint with No Active Plan

**Steps:**
1. Mark all today's entries as completed/skipped
2. GET the JSON suggestion endpoint again

**Expected:**
- Returns `{"status": "none"}` — no upcoming suggestion

---

## Test 9: Mobile Now Playing Card — Active Suggestion

**Steps:**
1. Open the SemPKM mobile app
2. Navigate to the dashboard (home tab)
3. Ensure the server has an active daily plan with queued entries

**Expected:**
- "Now Playing" card visible between the monitoring status row and "Server Context" section
- Card shows: source emoji (🎙️ / 🎬 / 🎵), source title, entry title, time slot, duration
- Status badge: "▶ Now playing" (green) for current slot, "⏭ Up next" (blue) for next queued
- "Play in [source]" button visible at the bottom of the card

---

## Test 10: Mobile Deep Link — Spotify

**Steps:**
1. On mobile, find a Spotify track suggestion in the Now Playing card
2. Tap the "Play in Spotify" button

**Expected:**
- Spotify app opens (or App Store if not installed) via `Linking.openURL(spotify:track:...)`
- If Spotify is installed, the track begins playing

---

## Test 11: Mobile Deep Link — YouTube

**Steps:**
1. Find a YouTube video suggestion in the Now Playing card
2. Tap the "Play in YouTube" button

**Expected:**
- YouTube app opens with the video URL
- If YouTube app not installed, opens in browser

---

## Test 12: Mobile Deep Link — Podcast

**Steps:**
1. Find a podcast episode suggestion
2. Tap the "Play in Podcast" button

**Expected:**
- Default podcast app or browser opens with the enclosure URL

---

## Test 13: Mobile Graceful Degradation — No Plan

**Steps:**
1. Stop the media scheduler app (Admin > Stop)
2. Open the mobile dashboard

**Expected:**
- Now Playing card does NOT appear (component returns null)
- No crash, no error UI — dashboard shows normally without the card
- Console.warn logged in Expo dev console: "Media suggestion fetch failed"

---

## Test 14: SSE Reconnect After Connection Drop

**Steps:**
1. Restart the backend API server (simulating SSE connection drop)
2. Wait 30 seconds
3. Check media scheduler logs

**Expected:**
- Log: `context_service.sse_connection_error` after connection drop
- Log: `context_service.sse_connected` after reconnect (within exponential backoff window)
- `get_context_subscription_status()` shows `reconnect_count: 1` (or higher)

---

## Test 15: Concurrent Plan Generation Protection

**Steps:**
1. Rapidly POST two context updates with `location_zone` changes within 1 second
2. Check logs for plan generation

**Expected:**
- First `plan_generation_completed` log appears
- Second request either waits for lock or logs `plan_lock_contention` warning
- No duplicate plan entries created — `asyncio.Lock` serializes generation

---

## Edge Cases

- **SSE stream sends malformed JSON:** Logged as warning, no crash, listener continues
- **Entry status with invalid value:** Returns 400 error, no state change
- **JSON endpoint with SPARQL failure:** Returns `{"status": "none", "error": "..."}` 
- **Mobile with expired session:** `getMediaSuggestion()` returns error, card renders null
- **Location zone unchanged:** If `_prev_context` has same `location_zone` as new event, treated as normal (debounced) change, not immediate
