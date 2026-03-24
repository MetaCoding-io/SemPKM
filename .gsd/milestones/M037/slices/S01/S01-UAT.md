# S01 UAT: Backend Context API & Workspace Indicator

## Preconditions

- Docker dev stack running (`docker compose up -d`)
- User logged in to workspace at `http://localhost:3901/browser/`
- Valid session cookie or API token available (get token from Settings > API Tokens)
- No prior context data for the test user (fresh state)

---

## TC-01: POST context update with full payload

**Steps:**
1. `curl -s -X POST http://localhost:3901/api/context/update -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"location_zone":"office","activity":"stationary","time_period":"work_hours","calendar_event":"Sprint Planning","calendar_busy":true,"device_id":"iphone-14"}'`
2. Inspect response JSON

**Expected:**
- HTTP 200
- Response contains `"context"` object with all 6 fields matching the input
- `"is_stale": false`
- `"updated_at"` is a recent ISO timestamp

---

## TC-02: GET current context after POST

**Steps:**
1. (After TC-01) `curl -s http://localhost:3901/api/context/current -H "Authorization: Bearer $TOKEN"`

**Expected:**
- HTTP 200
- Response contains `"context"` with `location_zone: "office"`, `activity: "stationary"`, etc.
- `"is_stale": false`
- `"ttl_seconds": 900`

---

## TC-03: Partial update preserves existing fields

**Steps:**
1. `curl -s -X POST http://localhost:3901/api/context/update -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"location_zone":"home"}'`
2. Inspect response

**Expected:**
- `location_zone` changed to `"home"`
- `activity` still `"stationary"` (preserved from TC-01)
- `time_period` still `"work_hours"` (preserved)
- `device_id` still `"iphone-14"` (preserved)

---

## TC-04: Auth enforcement — 401 without credentials

**Steps:**
1. `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3901/api/context/update -H "Content-Type: application/json" -d '{"location_zone":"office"}'`
2. `curl -s -o /dev/null -w "%{http_code}" http://localhost:3901/api/context/current`

**Expected:**
- Both return HTTP 401 or 302 (login redirect for non-API paths)

---

## TC-05: Empty POST body returns 422

**Steps:**
1. `curl -s -X POST http://localhost:3901/api/context/update -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'`

**Expected:**
- HTTP 422
- Error message indicates at least one field is required

---

## TC-06: Rate limiting — 429 on rapid POSTs

**Steps:**
1. Send 15 rapid POST requests in a loop:
   ```
   for i in $(seq 1 15); do
     curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:3901/api/context/update \
       -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
       -d "{\"location_zone\":\"zone-$i\"}"
   done
   ```

**Expected:**
- First 12 return 200
- At least one of the remaining returns 429
- 429 response includes `Retry-After` header

---

## TC-07: SSE stream delivers context_update events

**Steps:**
1. Open SSE connection: `curl -s -N http://localhost:3901/api/context/stream -H "Authorization: Bearer $TOKEN" &`
2. In another terminal: `curl -s -X POST http://localhost:3901/api/context/update -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"location_zone":"park","activity":"walking"}'`
3. Observe SSE output

**Expected:**
- SSE stream shows `event: context_update` followed by `data:` containing JSON with `location_zone: "park"` and `activity: "walking"`
- Keepalive comments (`: keepalive`) appear every ~30s if no updates sent

---

## TC-08: Stale context detection

**Steps:**
1. POST a context update (any field)
2. Wait 16 minutes (or temporarily set TTL to 5 seconds via code change for demo)
3. `curl -s http://localhost:3901/api/context/current -H "Authorization: Bearer $TOKEN"`

**Expected:**
- `"is_stale": true`
- All context field values still present (not cleared)

**Quick demo variant:** Set `DEFAULT_TTL_SECONDS = 5` in `service.py`, POST context, wait 6 seconds, GET current — `is_stale` should be `true`.

---

## TC-09: Workspace sidebar context indicator — initial load

**Steps:**
1. POST context: `{"location_zone":"office","activity":"stationary","time_period":"work_hours"}`
2. Open `http://localhost:3901/browser/` in browser
3. Look at the left sidebar, between the header and the explorer sections

**Expected:**
- Context indicator bar visible showing: 📍 office · 🪑 Stationary · 💼 Work Hours (icons + text)
- Indicator is not dimmed

---

## TC-10: Workspace sidebar context indicator — real-time SSE update

**Steps:**
1. With workspace open in browser (showing context from TC-09)
2. In terminal: `curl -s -X POST http://localhost:3901/api/context/update -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"location_zone":"home","activity":"walking","time_period":"evening"}'`
3. Watch the sidebar indicator

**Expected:**
- Indicator updates within 1-2 seconds to show: 📍 home · 🚶 Walking · 🌅 Evening
- No page refresh needed

---

## TC-11: Workspace sidebar — stale/unknown state

**Steps:**
1. Open workspace with no prior context data (new user or cleared state)
2. Observe indicator

**Expected:**
- Indicator shows "Context unknown" with dimmed/muted styling (opacity reduced)
- If SSE connection drops (stop the API container), indicator falls back to "Context unknown"

---

## TC-12: Field length validation

**Steps:**
1. `curl -s -X POST http://localhost:3901/api/context/update -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"location_zone":"'$(python3 -c "print('x'*300)")'"}' `

**Expected:**
- HTTP 422
- Validation error about field length exceeding limit

---

## Edge Cases

### EC-01: Context for user who has never posted

`GET /api/context/current` for a fresh user should return `{"context": null}` (not 500).

### EC-02: Multiple rapid context updates

The upsert pattern means only the latest value is stored. Rapid POSTs should not create duplicate rows — always one row per user.

### EC-03: Bearer token from mobile (simulated)

Using `Authorization: Bearer <api_token>` (same as the browser extension uses) should work identically to session cookie auth for all three endpoints.
