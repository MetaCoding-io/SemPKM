# S04 Research: Map View

## Summary

Straightforward new view renderer following the exact pattern S03 (Calendar View) established. The work is: add `"map"` to `_VALID_RENDERERS`, create a Leaflet template, add geo field detection to ViewSpecService, wire up the data endpoint, and add the explorer sidebar entry. No models currently define geo coordinates, so the empty-state UX is the primary user-facing experience until a model adds `wgs84:lat`/`wgs84:long` properties.

## Recommendation

Follow the calendar view implementation line-for-line, substituting geo-specific concepts. The implementation decomposes into three clean tasks: (1) backend geo detection + data endpoint, (2) frontend template + CSS, (3) wiring (router, workspace.js labels, explorer sidebar, `_VALID_RENDERERS`).

## Requirements

| Req | Description | Risk | Notes |
|-----|------------|------|-------|
| MAP-01 | Map view renders objects with geo coordinates as clustered Leaflet markers | Low | Leaflet + MarkerCluster is proven; pattern mirrors calendar |
| MAP-02 | Clicking a marker opens the object tab | Low | Same `openTab(iri, title)` pattern as calendar event click |
| MAP-03 | Instructive empty state when no geo data exists | Low | Static HTML, no library dependency |

## Implementation Landscape

### Files to Create

| File | Purpose |
|------|---------|
| `backend/app/templates/browser/map_view.html` | Jinja2 template with lazy-loaded Leaflet + MarkerCluster, map container, empty-state |

### Files to Modify

| File | Change |
|------|--------|
| `backend/app/views/router.py` | Add `"map"` to `_VALID_RENDERERS`; add `elif renderer == "map":` branch in `generic_view()` (~60 lines mirroring calendar); add `elif renderer == "map":` branch in `generic_view_data()` (~15 lines); update the allowed-renderer check in `generic_view_data()` from `("graph", "calendar")` to `("graph", "calendar", "map")` |
| `backend/app/views/service.py` | Add `_detect_geo_fields()` method (~50 lines, mirrors `_detect_date_fields()`); add `_WELL_KNOWN_GEO_PATHS` and `_XSD_GEO_DATATYPES` constants; add `execute_map_query()` method (~60 lines); add `_build_map_select()` static method (~25 lines) |
| `frontend/static/js/workspace.js` | Add `map: 'Map View'` to labels dict at line 3478 |
| `frontend/static/css/views.css` | Add `.map-container` styles (~15 lines) + Leaflet dark mode overrides (~20 lines) |
| `backend/app/templates/browser/views_explorer.html` | Add Map View entry (mirrors calendar entry, ~5 lines) |

### Existing Patterns to Follow

**S03 Calendar View is the reference implementation.** Every aspect of the map view has a direct calendar analog:

| Calendar concept | Map analog |
|-----------------|------------|
| `_detect_date_fields()` | `_detect_geo_fields()` |
| `_XSD_DATE_TYPES` | `_XSD_DECIMAL_TYPES` (for `xsd:decimal`, `xsd:float`, `xsd:double`) |
| `_WELL_KNOWN_DATE_PATHS` | `_WELL_KNOWN_GEO_PATHS` (`lat`, `latitude`, `long`, `longitude`, `lng`) |
| `_START_DATE_PRIORITY` | Lat/lng pairing logic (find lat property, then find matching lng) |
| `execute_calendar_query()` → `{"events": [...]}` | `execute_map_query()` → `{"markers": [...]}` |
| `_build_calendar_select()` | `_build_map_select()` |
| `calendar_data_url` | `map_data_url` |
| FullCalendar CDN lazy-load | Leaflet + MarkerCluster CDN lazy-load |
| `calendar_view.html` | `map_view.html` |
| `calendar-container` CSS class | `map-container` CSS class |
| `date_fields` template variable | `geo_fields` template variable |

### Geo Field Detection Strategy

`_detect_geo_fields(type_iri)` scans SHACL PropertyShapes for a type and finds latitude/longitude pairs:

1. **By datatype:** `sh:datatype` is `xsd:decimal`, `xsd:float`, or `xsd:double`
2. **By path name:** local name of `sh:path` matches well-known geo IRIs:
   - WGS84: `http://www.w3.org/2003/01/geo/wgs84_pos#lat`, `wgs84_pos#long`
   - Schema.org: `http://schema.org/latitude`, `http://schema.org/longitude`
   - Local name heuristics: contains `lat`/`latitude`/`lng`/`long`/`longitude`

Returns `(lat_field: PropertyShape | None, lng_field: PropertyShape | None)`. Both must be found for the map to render; if either is `None`, show empty state.

**Pairing logic:** Find all properties that look like latitude candidates (path contains "lat"), then find all longitude candidates (path contains "lon" or "lng"). If both sets are non-empty, pick the first from each. If using well-known IRI matching (wgs84:lat + wgs84:long), pair them directly.

### Library CDN URLs

```
Leaflet 1.9.4:
  CSS: https://unpkg.com/leaflet@1.9.4/dist/leaflet.css
  JS:  https://unpkg.com/leaflet@1.9.4/dist/leaflet.js

MarkerCluster 1.5.3:
  CSS: https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css
  CSS: https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css
  JS:  https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js
```

Leaflet requires both CSS and JS (unlike FullCalendar which is JS-only). The CSS must load before the JS initializes. Lazy-loading order: CSS link elements first, then Leaflet JS, then MarkerCluster JS (depends on Leaflet).

### Leaflet Initialization Pattern

```javascript
var map = L.map('map-container').setView([20, 0], 2); // World-centered default
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

var markers = L.markerClusterGroup({ chunkedLoading: true });
data.markers.forEach(function(m) {
    var marker = L.marker([m.lat, m.lng]);
    marker.bindPopup('<strong>' + m.title + '</strong>');
    marker.on('click', function() {
        if (m.iri && typeof openTab === 'function') openTab(m.iri, m.title);
    });
    markers.addLayer(marker);
});
map.addLayer(markers);

// Fit bounds to markers if any exist
if (data.markers.length > 0) {
    map.fitBounds(markers.getBounds().pad(0.1));
}
```

### Map Data Endpoint Response Shape

```json
{
    "markers": [
        {
            "iri": "urn:sempkm:current:abc123",
            "title": "Some Place",
            "lat": 51.505,
            "lng": -0.09
        }
    ],
    "geo_fields": {
        "lat": { "path": "http://www.w3.org/2003/01/geo/wgs84_pos#lat", "name": "lat" },
        "lng": { "path": "http://www.w3.org/2003/01/geo/wgs84_pos#long", "name": "long" }
    }
}
```

### Empty State UX

Since no current Mental Models define geo coordinates, the empty state is what most users will see. It should be instructive, not just "no data":

```html
<div class="view-empty-state">
    <p><strong>Map View</strong></p>
    <p>This view displays objects with geographic coordinates on an interactive map.</p>
    <p>To use Map View, select a type that has latitude/longitude properties
       (e.g. <code>wgs84:lat</code> / <code>wgs84:long</code> or
        <code>schema:latitude</code> / <code>schema:longitude</code>).</p>
</div>
```

Three empty-state triggers (same as calendar pattern):
1. No type selected → "Select a type to use Map View"
2. Type selected but no geo properties → "This type has no geographic coordinate properties for Map display"
3. Type has geo properties but no objects with values → Map renders with no markers (world view)

### Dark Mode Leaflet Overrides

Leaflet tiles are OSM (light background). For dark mode, apply CSS filter to the tile layer:

```css
[data-theme="dark"] .leaflet-tile-pane {
    filter: brightness(0.6) invert(1) contrast(3) hue-rotate(200deg) saturate(0.3) brightness(0.7);
}
[data-theme="dark"] .leaflet-container {
    background: var(--color-bg);
}
```

Also override Leaflet's default control styles (zoom buttons, attribution) for dark theme.

### Dockview Integration

Map container needs `.view-flex-column` wrapper (same as graph/kanban) for full-height rendering. The Leaflet map's `height: 100%` requires its parent to have explicit height — the `flex: 1; min-height: 0;` pattern on `.map-container` handles this.

**Important:** Leaflet must call `map.invalidateSize()` when the container size changes (dockview panel resize). Use a `ResizeObserver` on the container, or listen for the dockview panel resize event. The calendar view doesn't need this (FullCalendar handles its own sizing), but Leaflet caches the container dimensions at init time.

### SPARQL Query Pattern

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?s ?label ?lat ?lng
WHERE {
  ?s rdf:type <{type_iri}> .
  ?s <{lat_path}> ?lat .
  ?s <{lng_path}> ?lng .
  {scope_clause}
  OPTIONAL { ?s rdfs:label|dcterms:title ?label }
}
```

Both lat and lng are required (non-OPTIONAL) — objects without both coordinates are excluded.

## Constraints

1. **No test data exists.** No model defines geo properties. Verification must either: (a) create temporary test triples via SPARQL INSERT through the triplestore client (not the API — see KNOWLEDGE.md), or (b) verify the empty-state UX and code path correctness through unit tests of `_detect_geo_fields()` and `_build_map_select()`.
2. **Leaflet requires CSS.** Unlike FullCalendar (JS-only CDN), Leaflet needs CSS loaded first. The lazy-load sequence must create `<link>` elements for CSS before `<script>` for JS.
3. **Leaflet `invalidateSize()`.** Must be called after container resize (dockview panel). A `ResizeObserver` on the map container is the cleanest approach.
4. **Tile loading in air-gapped environments.** Leaflet handles tile errors silently (grey tiles). No special handling needed, but the empty state should not be confused with a tile loading failure. The empty state is shown when _no geo properties exist_, not when tiles fail to load.

## Task Decomposition Guidance

**T01: Backend geo detection + data endpoint** (~100 lines in service.py, ~80 lines in router.py)
- Add `_WELL_KNOWN_GEO_PATHS`, `_XSD_DECIMAL_TYPES`, `_detect_geo_fields()`, `_build_map_select()`, `execute_map_query()` to ViewSpecService
- Add `"map"` to `_VALID_RENDERERS`
- Add `elif renderer == "map":` branch in `generic_view()` (mirrors calendar branch exactly)
- Add `elif renderer == "map":` branch in `generic_view_data()` + update allowed-renderers check
- Unit test `_detect_geo_fields()` and `_build_map_select()`

**T02: Frontend template + CSS + wiring** (~80 lines template, ~40 lines CSS, ~10 lines JS/HTML)
- Create `map_view.html` template with lazy-loaded Leaflet + MarkerCluster
- Add `.map-container` and dark mode Leaflet overrides to `views.css`
- Add `map: 'Map View'` to workspace.js labels dict
- Add Map View entry to `views_explorer.html`
- Verify in browser: map view opens, shows empty state, Leaflet loads when geo data exists

The wiring changes (workspace.js, views_explorer.html) are tiny and could go in either task. Putting them in T02 keeps T01 purely backend.
