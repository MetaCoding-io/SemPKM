# S03 UAT: Map View Renderer

## Preconditions

1. Docker stack running (`docker compose up -d`)
2. basic-pkm Mental Model installed (includes 4 geo-located seed events)
3. User logged in to workspace at `/browser/`
4. Browser has internet access (OpenStreetMap tiles load from tile.openstreetmap.org)

---

## Test Cases

### TC-01: Map View opens from Explorer sidebar

**Steps:**
1. In the workspace sidebar, expand the VIEWS section
2. Locate the "Map View" entry (should show 🌍 globe emoji)
3. Click "Map View"

**Expected:**
- A new dockview tab opens with label "Map View"
- The tab contains a Leaflet map showing OpenStreetMap tiles
- Map has zoom controls (+ / - buttons in top-left)
- Attribution text "© OpenStreetMap contributors" visible in bottom-right

### TC-02: Seed events display as markers

**Steps:**
1. Open Map View (TC-01)
2. Select type filter pill for "Event" (bpkm:Event type) if type pills are visible
3. Wait for markers to load

**Expected:**
- 4 markers visible (Mountain View, Pittsburgh, London, Tokyo)
- Markers are styled circles (not default blue Leaflet pin icons)
- Map auto-fits bounds to show all markers
- At world zoom level, some markers may be clustered — zoom in to see individual markers

### TC-03: Marker clustering

**Steps:**
1. Zoom out to a level where markers overlap (e.g., both US markers visible close together)
2. Observe cluster behavior

**Expected:**
- Overlapping markers merge into a cluster icon showing count (e.g., "2")
- Clicking a cluster zooms in to reveal individual markers
- Single markers remain as individual circles

### TC-04: Marker popup shows object info

**Steps:**
1. Open Map View with Event markers visible
2. Click on any individual marker (e.g., Tokyo marker)

**Expected:**
- Popup appears near the marker
- Popup shows the event label (e.g., "Workshop on Knowledge Graphs" or similar)
- Popup shows the event type
- Popup contains a clickable "Open" link/button

### TC-05: Click-to-open from popup

**Steps:**
1. Open a marker popup (TC-04)
2. Click the "Open" link in the popup

**Expected:**
- A new object tab opens in the workspace with the event's details
- The SHACL form shows the event's properties including schema:latitude and schema:longitude fields

### TC-06: Type filter pills

**Steps:**
1. Open Map View (generic, not type-specific)
2. Observe type filter pills at the top of the view
3. Click the "Event" type pill

**Expected:**
- Only Event objects with geo coordinates display as markers
- Active pill is visually highlighted
- If no objects of a selected type have geo coordinates, an appropriate empty state message appears

### TC-07: Dark mode tile rendering

**Steps:**
1. Toggle dark mode in the workspace (theme toggle)
2. Open or observe an already-open Map View

**Expected:**
- Map tiles invert colors (dark background with light roads/labels)
- Popup backgrounds adjust to dark theme (not white popup on dark map)
- Marker circles remain visible and readable

### TC-08: Panel resize handling

**Steps:**
1. Open Map View in a dockview panel
2. Drag the panel border to resize the panel (make it wider/narrower)

**Expected:**
- Map fills the new panel dimensions without blank areas or overlapping tiles
- No need to manually refresh the map — ResizeObserver triggers `invalidateSize()` automatically

### TC-09: Map data JSON endpoint

**Steps:**
1. Open browser DevTools Network tab
2. Open Map View with Event type selected
3. Find the XHR request to `/browser/views/generic/map/data?type=...`

**Expected:**
- Response is a JSON array of marker objects
- Each marker has: `id` (IRI string), `label` (string), `lat` (number), `lng` (number), `type` (string)
- Coordinates are numeric floats, not strings
- At least 4 markers for seed events

### TC-10: Graceful degradation — type without geo properties

**Steps:**
1. Open Map View
2. Select a type pill for a type that has no geo properties (e.g., "Project" or "Concept")

**Expected:**
- Empty state message appears (not a broken map or JS error)
- Message indicates the selected type doesn't have geographic properties
- Map container remains stable (no console errors)

### TC-11: Canvas drag support

**Steps:**
1. In the workspace, locate the Map View entry in the VIEWS explorer section
2. Drag the Map View entry onto the canvas area

**Expected:**
- Drag initiates with correct payload (type: 'view', id: 'generic-map')
- Map view opens in the dropped panel location

### TC-12: CDN fallback (manual test)

**Steps:**
1. In browser DevTools, block requests to vendored Leaflet files (e.g., `leaflet-*.min.js`)
2. Reload the Map View

**Expected:**
- Leaflet loads from CDN fallback (unpkg.com/leaflet@1.9.4)
- MarkerCluster loads from CDN fallback
- Map still renders and functions correctly

---

## Edge Cases

### EC-01: Empty triplestore (no events)
- Open Map View with no objects in the triplestore
- Expected: Empty state message, no JS errors

### EC-02: Object with invalid coordinates
- If an object has non-numeric latitude/longitude values
- Expected: Backend skips invalid coordinates (tested in unit tests). No markers for invalid data. No server error.

### EC-03: Multiple map tabs
- Open Map View twice (different type selections)
- Expected: Each tab has its own independent map instance. Resizing one doesn't affect the other.

### EC-04: Very rapid type switching
- Click through type pills quickly
- Expected: Map updates to show markers for the final selected type. No race conditions or stale markers.
