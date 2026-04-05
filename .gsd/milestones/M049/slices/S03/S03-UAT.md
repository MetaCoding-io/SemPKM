# S03: Server-Timing Headers & Admin Dashboard — UAT

**Milestone:** M049
**Written:** 2026-04-05T21:02:11.951Z

## UAT: S03 — Server-Timing Headers & Admin Dashboard

### Preconditions
- SemPKM running via Docker Compose with at least one Mental Model installed
- Logged in as owner
- Browser DevTools accessible

### Test 1: Server-Timing Header Per-Query Breakdown
1. Open browser DevTools → Network tab
2. Navigate to any object page (click an object in the explorer)
3. Find the HTML document request in the Network tab
4. Click it → Headers tab → scroll to Response Headers
5. **Expected:** `Server-Timing` header present containing `total;dur=X.XX` AND one or more `sparql.query.N;dur=Y.YY` entries (N is 1-indexed)
6. Open a different object
7. **Expected:** Server-Timing entries reflect fresh timings for this request, not accumulated from previous

### Test 2: Admin Performance Dashboard Access
1. Navigate to `/admin/`
2. **Expected:** A "Performance" card is visible among the admin dashboard cards
3. Click the Performance card
4. **Expected:** `/admin/performance` page loads with:
   - Stats cards row showing total requests, collection period, unique endpoints
   - A grouped bar chart (Chart.js) with colored bars for p50/p95/p99
   - A detail table below with columns: Endpoint, Count, Avg, p50, p95, p99, Max

### Test 3: Performance Dashboard Data
1. Navigate around the app (open 3-4 objects, visit admin pages) to generate timing data
2. Navigate to `/admin/performance`
3. **Expected:** Chart shows bars for the endpoints you visited. Table shows non-zero counts and timing values. p50 ≤ p95 ≤ p99 for each endpoint.

### Test 4: Performance Dashboard Auth
1. Log out or open an incognito window
2. Navigate to `/admin/performance`
3. **Expected:** Redirected to login page (not 200 OK)

### Test 5: Inbox Panel Lazy Loading
1. Open browser DevTools → Network tab → clear all requests
2. Navigate to `/browser/` (workspace)
3. **Expected:** No requests to the inbox endpoint visible in Network tab (the panel is collapsed/off-screen)
4. Scroll down or expand the inbox panel (right pane)
5. **Expected:** Network request to inbox endpoint fires when the panel enters the viewport
6. Wait 60+ seconds
7. **Expected:** Inbox endpoint is polled again (every 60s refresh continues after first reveal)

### Test 6: Collaboration Panel Lazy Loading
1. Open browser DevTools → Network tab → clear all requests
2. Navigate to `/browser/` (workspace)
3. **Expected:** No requests to the collaboration endpoint visible in Network tab
4. Scroll to or expand the collaboration panel
5. **Expected:** Network request fires only when the panel enters the viewport

### Edge Cases
- **Server restart:** After restarting the backend, `/admin/performance` should show empty state (zero requests, no chart data) — timing stats are in-memory only
- **CDN unavailable:** If cdn.jsdelivr.net is blocked, the performance dashboard loads but the chart area is blank (Chart.js fails to load). Stats cards and table still render.
- **No SPARQL queries:** For non-object routes (e.g., `/admin/`), Server-Timing header should contain `total;dur=X.XX` but no `sparql.*` entries
