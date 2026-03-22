# S03 Research: Map View Renderer

## Summary

Map view follows the calendar renderer pattern established by S02 — registry entry, `_VALID_RENDERERS`, `generic_view()` branch, data endpoint, template, JS init, explorer sidebar entry. The technology stack is Leaflet 1.9.4 + Leaflet.markercluster 1.5.3 for map tiles and marker clustering. The main complication: **no model currently has geographic coordinate properties**. The slice must add `schema:latitude` and `schema:longitude` to the basic-pkm Event shape (or a new type) and populate seed data with real coordinates to be demoable.

## Calibration: Targeted Research

Known technology (Leaflet is well-documented, simple API), established codebase pattern (S02 proved the renderer registration end-to-end). Main risk is the geo data gap. The calendar implementation provides a nearly copy-and-adapt blueprint.

## Recommendation

Follow the S02 calendar pattern exactly, substituting Leaflet for FullCalendar and geo-field detection for date-field detection. Five tasks:

1. **Backend: geo detection + SPARQL query + data endpoint** — `_detect_geo_fields()`, `_build_map_select()`, `execute_map_query()`, extend `generic_view()` and `generic_graph_data()` with `"map"` branches
2. **Frontend: Leaflet template + JS + CSS** — `map_view.html`, `map.js`, Leaflet/markercluster CSS, dark mode
3. **Vendoring + build pipeline** — add `leaflet` + `leaflet.markercluster` to package.json, build.js sections, CDN fallback
4. **Model data: geo properties + seed** — add `schema:latitude`/`schema:longitude` to Event shape, add geo coordinates to seed events, add a few seed Place objects
5. **Tests** — unit tests for `_detect_geo_fields`, `_build_map_select`, `execute_map_query`

Tasks 1–3 could be collapsed into fewer tasks. The planner should decide based on task size limits.

## Implementation Landscape

### Files That Change

| File | Change | Pattern Source |
|---|---|---|
| `backend/app/views/registry.py` | Add `"map"` entry to `RENDERER_REGISTRY` | Calendar entry at line ~38 |
| `backend/app/views/router.py` | Add `"map"` to `_VALID_RENDERERS` set, add `elif renderer == "map"` branch in `generic_view()`, extend `generic_graph_data()` to accept `"map"` | Calendar branch at line 455 |
| `backend/app/views/service.py` | Add `_GEO_LAT_PATHS`, `_GEO_LNG_PATHS` constants, `_detect_geo_fields()`, `_build_map_select()`, `execute_map_query()` | Follows `_detect_date_fields()` at line 1345, `_build_calendar_select()` at line 1431, `execute_calendar_query()` at line 1491 |
| `backend/app/templates/browser/map_view.html` | New template — Leaflet container, type pills, toolbar, tryInit polling | Copy `calendar_view.html` structure |
| `frontend/static/js/map.js` | New IIFE — `initMap()` with Leaflet init, tile layer, marker clustering, popup, click-to-open | Copy `calendar.js` structure |
| `frontend/static/css/views.css` | Add `.map-container` styles, dark mode tile filter, Leaflet overrides | Copy `.calendar-container` block at line 1274 |
| `backend/app/templates/base.html` | Add `<script src="{{ 'map.js' | asset_url }}"></script>` after calendar.js line | Line 151 |
| `backend/app/templates/browser/views_explorer.html` | Add Map View `<a>` entry with `openGenericViewTab('map')` | Calendar entry at line 46-49 |
| `frontend/static/js/workspace.js` | Add `map: 'Map View'` to labels dict | Near calendar label |
| `frontend/package.json` | Add `"leaflet": "1.9.4"`, `"leaflet.markercluster": "^1.5.3"` | FullCalendar entry |
| `frontend/build.js` | Add Leaflet JS + CSS + markercluster build sections | FullCalendar section at line 226 |
| `models/basic-pkm/shapes/basic-pkm.jsonld` | Add `schema:latitude` (xsd:decimal) and `schema:longitude` (xsd:decimal) to EventShape | Existing properties pattern |
| `models/basic-pkm/ontology/basic-pkm.jsonld` | Declare latitude/longitude properties if needed (or use schema.org directly) | Existing property declarations |
| `models/basic-pkm/seed/basic-pkm.jsonld` | Add lat/lng values to existing events with physical locations | Existing event seed data |
| `backend/tests/test_map.py` | New — unit tests for geo detection, query building, response format | Copy `test_calendar.py` structure |

### Geo Field Detection Pattern

Follows `_detect_date_fields()` exactly:

```python
# Well-known geo property IRIs
_GEO_LAT_PATHS = [
    "https://schema.org/latitude",
    "http://schema.org/latitude",
]
_GEO_LNG_PATHS = [
    "https://schema.org/longitude",
    "http://schema.org/longitude",
]

async def _detect_geo_fields(self, type_iri: str) -> tuple[PropertyShape | None, PropertyShape | None]:
    """Find latitude and longitude properties from SHACL shapes."""
    # 1. Get form for type via shapes_service
    # 2. Match by exact path (schema:latitude, schema:longitude)
    # 3. Fallback: match by path containing "lat"/"lng"/"lon"/"latitude"/"longitude"
    # Returns (lat_prop, lng_prop) — either may be None
```

### Map SPARQL Query

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?s ?label ?lat ?lng ?type
WHERE {
  ?s rdf:type <TYPE_IRI> .
  ?s <LAT_PATH> ?lat .
  ?s <LNG_PATH> ?lng .
  OPTIONAL { ?s rdfs:label|dcterms:title ?label }
  OPTIONAL { ?s rdf:type ?type }
}
```

### Map Data JSON Response Format

```json
[
  {
    "id": "urn:...",
    "label": "Team Offsite",
    "lat": 37.3861,
    "lng": -122.0839,
    "type": "bpkm:Event",
    "properties": {
      "iri": "urn:...",
      "type": "bpkm:Event"
    }
  }
]
```

### Leaflet Initialization Pattern

```javascript
(function() {
    'use strict';

    function initMap(containerId, dataUrl, options) {
        var container = document.getElementById(containerId);
        if (!container) return;
        if (container._mapInstance) {
            container._mapInstance.remove();
        }

        var map = L.map(containerId).setView([20, 0], 2);
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        var markers = L.markerClusterGroup();

        fetch(dataUrl)
            .then(r => r.json())
            .then(data => {
                data.forEach(item => {
                    var marker = L.marker([item.lat, item.lng]);
                    marker.bindPopup(
                        '<strong>' + item.label + '</strong><br>' +
                        '<a href="#" onclick="openTab(\'' + item.id + '\', \'' + item.label + '\'); return false;">Open</a>'
                    );
                    markers.addLayer(marker);
                });
                map.addLayer(markers);
                if (data.length > 0) {
                    map.fitBounds(markers.getBounds().pad(0.1));
                }
            });

        container._mapInstance = map;
    }

    window.initMap = initMap;
})();
```

### Vendoring Pattern (build.js)

Leaflet needs both JS and CSS vendored. Markercluster also has its own CSS. The build.js section follows the FullCalendar pattern:

```javascript
// LEAFLET BUNDLE
const leafletJs = fs.readFileSync(
    path.join(NODE_MODULES, 'leaflet/dist/leaflet.js')
);
const leafletJsFile = writeHashed('leaflet', '.min.js', leafletJs);
manifest['leaflet.js'] = leafletJsFile;

const leafletCss = fs.readFileSync(
    path.join(NODE_MODULES, 'leaflet/dist/leaflet.css')
);
const leafletCssFile = writeHashed('leaflet', '.css', leafletCss);
manifest['leaflet.css'] = leafletCssFile;

// LEAFLET MARKERCLUSTER
const mcJs = fs.readFileSync(
    path.join(NODE_MODULES, 'leaflet.markercluster/dist/leaflet.markercluster.js')
);
const mcJsFile = writeHashed('leaflet-markercluster', '.min.js', mcJs);
manifest['leaflet-markercluster.js'] = mcJsFile;

const mcCss = fs.readFileSync(
    path.join(NODE_MODULES, 'leaflet.markercluster/dist/MarkerCluster.css')
);
const mcDefaultCss = fs.readFileSync(
    path.join(NODE_MODULES, 'leaflet.markercluster/dist/MarkerCluster.Default.css')
);
const mcCombined = Buffer.concat([mcCss, mcDefaultCss]);
const mcCssFile = writeHashed('leaflet-markercluster', '.css', mcCombined);
manifest['leaflet-markercluster.css'] = mcCssFile;
```

### Template Structure (map_view.html)

```html
<div class="view-flex-column">
{% if is_generic | default(false) %}
{% include "browser/type_filter_pills.html" %}
{% endif %}
{% include "browser/view_toolbar.html" %}

{% if selected_type and not lat_field and not lng_field %}
<div class="view-empty-state">
    <p>No geographic coordinate properties detected for this type. Map view requires latitude and longitude properties (e.g. schema:latitude, schema:longitude).</p>
</div>
{% else %}
<div id="map-container" class="map-container"></div>
{% endif %}
</div>

<link rel="stylesheet" href="{{ 'leaflet.css' | asset_url }}" />
<link rel="stylesheet" href="{{ 'leaflet-markercluster.css' | asset_url }}" />
<script src="{{ 'leaflet.js' | asset_url }}"></script>
<script src="{{ 'leaflet-markercluster.js' | asset_url }}"></script>
<!-- CDN fallbacks -->
<script>window.L || document.write('...')</script>

<script>
(function() {
    var dataUrl = {{ map_data_url | tojson }};
    function tryInit() {
        if (typeof window.initMap === 'function' && typeof L !== 'undefined') {
            var container = document.getElementById('map-container');
            if (container) {
                window.initMap('map-container', dataUrl, {});
            }
        } else {
            setTimeout(tryInit, 50);
        }
    }
    tryInit();
})();
</script>
```

### Seed Data Additions

Add `schema:latitude` and `schema:longitude` to the 2 events with physical locations:

| Event | Location | Lat | Lng |
|---|---|---|---|
| `bpkm:seed-event-offsite` | Mountain View Conference Center | 37.3861 | -122.0839 |
| `bpkm:seed-event-review-offsite` | Mountain View Conference Center, Room B | 37.3861 | -122.0839 |

Add 3-4 new seed events with diverse geo locations to make the map interesting:

| New Event | Location | Lat | Lng |
|---|---|---|---|
| `bpkm:seed-event-conference` | PyCon US, Pittsburgh | 40.4406 | -79.9959 |
| `bpkm:seed-event-meetup` | Tech Meetup, London | 51.5074 | -0.1278 |
| `bpkm:seed-event-workshop` | Design Workshop, Tokyo | 35.6762 | 139.6503 |

### Dark Mode Considerations

Leaflet tiles are raster images from OpenStreetMap — they don't respond to CSS variables. Two approaches:
1. **CSS filter** on `.leaflet-tile-pane`: `filter: invert(1) hue-rotate(180deg)` — quick, makes tiles dark, slightly distorts colors
2. **Dark tile provider**: Use CartoDB dark tiles (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`) when in dark mode

Recommend approach 1 for simplicity — it's a 3-line CSS rule. The calendar uses CSS variable overrides because FullCalendar is a DOM-based library. Map tiles are images, so CSS filter is the equivalent approach.

```css
.dark .map-container .leaflet-tile-pane {
    filter: invert(1) hue-rotate(180deg);
}
```

### Graceful Degradation (No Tiles)

If OpenStreetMap tiles fail to load (firewall, offline), markers still render but on a blank background. The map is still functional — you can click markers, see popups, the map pan/zoom works. Add a fallback message:

```javascript
tileLayer.on('tileerror', function() {
    if (!container._tileErrorShown) {
        container._tileErrorShown = true;
        console.warn('[map] Tile loading failed — map will show markers without background tiles');
    }
});
```

### Explorer Sidebar Entry

Add after the Calendar View entry in `views_explorer.html`:

```html
<a class="tree-leaf view-leaf" href="#"
   draggable="true"
   ondragstart="event.dataTransfer.setData('text/plain', 'Map View'); event.dataTransfer.effectAllowed = 'copy'; window.__canvasDragPayload = {type:'view', id:'generic-map', label:'Map View', url:'/browser/views/generic/map?embed=1'};"
   onclick="openGenericViewTab('map'); return false;">
    <span class="tree-leaf-icon">&#127759;</span>
    <span class="tree-leaf-label">Map View</span>
</a>
```

## Constraints

1. **No geo data exists yet** — shapes, ontology, and seed data all need updates before the map can render anything
2. **Leaflet CSS is required** — unlike FullCalendar which is a single JS file, Leaflet needs both JS and CSS. The CSS includes marker icons, popup styles, etc.
3. **Marker icon images** — Leaflet's default marker icons reference PNG images (`marker-icon.png`, `marker-shadow.png`) via CSS relative URLs. When vendored via build.js, these paths may break. Known fix: set `L.Icon.Default.imagePath` or use inline SVG markers via `L.divIcon`.
4. **Leaflet `invalidateSize()` in dockview** — Leaflet maps initialized in hidden or zero-size containers render incorrectly. When a map tab becomes visible in dockview, `map.invalidateSize()` must be called. The calendar has a similar issue — FullCalendar handles it internally. Leaflet needs an explicit call, likely triggered by dockview panel visibility or a `ResizeObserver`.
5. **Tile layer requires internet** — OpenStreetMap tiles are served from external CDN. Docker instances without internet access get blank map backgrounds. Markers still work.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Leaflet marker icon path breakage when vendored | Medium | Set `L.Icon.Default.imagePath` or use `L.divIcon` with inline SVG |
| Map renders blank when dockview panel resized/shown | Medium | Use `ResizeObserver` on container → `map.invalidateSize()` |
| No seed data with geo coordinates | Low | Adding lat/lng to shapes + seed is straightforward |
| Tile loading fails behind firewalls | Low | Graceful degradation — markers still visible, console warning |

## Patterns Established by S02 (to follow)

From S02 summary `patterns_established`:
- New renderer registration: registry entry → `_VALID_RENDERERS` → `generic_view` branch → data endpoint branch → template → JS init function → explorer sidebar entry → `workspace.js` label
- Field detection via SHACL PropertyShape scan with priority ranking
- Vendor library build pipeline: `build.js` section → content-hash → manifest → CDN fallback
- View template structure: `.view-flex-column` wrapper → type_filter_pills → view_toolbar → empty state or container

## Sources

- Leaflet 1.9.4 API: `L.map()`, `L.tileLayer()`, `L.marker()`, `L.markerClusterGroup()`
- Leaflet.markercluster 1.5.3: `maxClusterRadius`, `spiderfyOnMaxZoom`, `showCoverageOnHover`
- S02 implementation: calendar.js, calendar_view.html, views/service.py, views/router.py, views/registry.py, build.js, test_calendar.py
