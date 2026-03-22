---
estimated_steps: 8
estimated_files: 7
skills_used: []
---

# T02: Frontend map.js, Leaflet vendoring, explorer entry, dark mode CSS

**Slice:** S03 — Map View Renderer
**Milestone:** M033

## Description

Build the frontend rendering layer for the map view. This includes vendoring Leaflet and Leaflet.markercluster via `build.js`, creating `map.js` with the `initMap()` function, adding the explorer sidebar entry, registering the workspace label, loading the script in `base.html`, and adding dark mode + layout CSS.

S02's calendar frontend is the pattern: `calendar.js` is an IIFE with `initCalendar()`, loaded in `base.html`, vendored via `build.js` content-hash pipeline. The map follows this exactly with Leaflet instead of FullCalendar, plus markercluster as a second vendored library.

Key Leaflet complication: marker icon images. Leaflet's default markers reference PNG files via CSS relative URLs that break when vendored. Use `L.divIcon` with CSS-styled markers (a colored circle) to avoid the icon path issue entirely.

Key dockview complication: Leaflet maps initialized in zero-size panels render wrong. Use `ResizeObserver` on the map container to call `map.invalidateSize()` when the panel is resized or shown.

## Steps

1. **Package dependencies:** Add `"leaflet": "1.9.4"` and `"leaflet.markercluster": "^1.5.3"` to `frontend/package.json` devDependencies. Run `npm install` from `frontend/`.

2. **Build pipeline:** In `frontend/build.js`, add sections (after the FullCalendar section) for:
   - Leaflet JS: read `node_modules/leaflet/dist/leaflet.js`, write content-hashed `leaflet-{hash}.min.js`, add `manifest['leaflet.js']`
   - Leaflet CSS: read `node_modules/leaflet/dist/leaflet.css`, write content-hashed `leaflet-{hash}.css`, add `manifest['leaflet.css']`
   - Markercluster JS: read `node_modules/leaflet.markercluster/dist/leaflet.markercluster.js`, write content-hashed, add `manifest['leaflet-markercluster.js']`
   - Markercluster CSS: read and concatenate `MarkerCluster.css` + `MarkerCluster.Default.css`, write content-hashed, add `manifest['leaflet-markercluster.css']`
   Follow the exact `writeHashed()` pattern used for FullCalendar.

3. **map.js IIFE:** Create `frontend/static/js/map.js` with:
   ```javascript
   (function() {
       'use strict';
       function initMap(containerId, dataUrl, options) {
           var container = document.getElementById(containerId);
           if (!container) { console.warn('[map] Container not found:', containerId); return; }
           // Clean up existing instance
           if (container._mapInstance) { container._mapInstance.remove(); container._mapInstance = null; }

           var map = L.map(containerId).setView([20, 0], 2);
           L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
               maxZoom: 19,
               attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
           }).addTo(map);

           // Tile error handler
           map.eachLayer(function(layer) {
               if (layer.on) layer.on('tileerror', function() {
                   if (!container._tileErrorShown) {
                       container._tileErrorShown = true;
                       console.warn('[map] Tile loading failed');
                   }
               });
           });

           var markers = L.markerClusterGroup();

           fetch(dataUrl)
               .then(function(r) { return r.json(); })
               .then(function(data) {
                   data.forEach(function(item) {
                       var marker = L.marker([item.lat, item.lng]);
                       var popupHtml = '<strong>' + (item.label || 'Unnamed') + '</strong>';
                       if (item.type) popupHtml += '<br><em>' + item.type + '</em>';
                       popupHtml += '<br><a href="#" onclick="openTab(\'' + item.id + '\', \'' + (item.label || '').replace(/'/g, "\\'") + '\'); return false;">Open</a>';
                       marker.bindPopup(popupHtml);
                       markers.addLayer(marker);
                   });
                   map.addLayer(markers);
                   if (data.length > 0) {
                       map.fitBounds(markers.getBounds().pad(0.1));
                   }
               })
               .catch(function(err) { console.error('[map] Failed to load markers:', err); });

           // ResizeObserver for dockview panel resize
           if (typeof ResizeObserver !== 'undefined') {
               var ro = new ResizeObserver(function() { map.invalidateSize(); });
               ro.observe(container);
           }

           container._mapInstance = map;
       }
       window.initMap = initMap;
   })();
   ```
   Adjust as needed — this is the target structure, not an exact copy-paste. Handle `L.divIcon` for custom markers if default icon paths break.

4. **base.html script tag:** Add `<script src="{{ 'map.js' | asset_url }}"></script>` after the `calendar.js` script tag in `backend/app/templates/base.html`.

5. **Explorer sidebar entry:** Add Map View `<a>` entry in `backend/app/templates/browser/views_explorer.html` after the Calendar View entry:
   ```html
   <a class="tree-leaf view-leaf" href="#"
      draggable="true"
      ondragstart="event.dataTransfer.setData('text/plain', 'Map View'); event.dataTransfer.effectAllowed = 'copy'; window.__canvasDragPayload = {type:'view', id:'generic-map', label:'Map View', url:'/browser/views/generic/map?embed=1'};"
      onclick="openGenericViewTab('map'); return false;">
       <span class="tree-leaf-icon">&#127759;</span>
       <span class="tree-leaf-label">Map View</span>
   </a>
   ```

6. **Workspace label:** In `frontend/static/js/workspace.js`, find the labels dict (line ~3234) and add `map: 'Map View'` after the calendar entry.

7. **CSS:** In `frontend/static/css/views.css`, add:
   - `.map-container` block: `flex: 1; min-height: 0; width: 100%; position: relative;` (matches `.calendar-container` pattern)
   - Dark mode tile inversion: `.dark .map-container .leaflet-tile-pane { filter: invert(1) hue-rotate(180deg); }`
   - Popup styling overrides if needed for dark mode
   - Leaflet z-index fix if needed for dockview stacking

8. **Run build:** Execute `cd frontend && npm run build` to verify vendoring works and manifest entries are created.

## Must-Haves

- [ ] Leaflet and markercluster in `package.json` devDependencies
- [ ] `build.js` vendors Leaflet JS, CSS, markercluster JS, CSS with content-hash + manifest
- [ ] `map.js` IIFE exports `window.initMap`
- [ ] `initMap` creates L.map, tile layer, markerClusterGroup, fetches data, creates markers with popups
- [ ] Click-to-open via `openTab()` in popup
- [ ] `ResizeObserver` calls `map.invalidateSize()` on container resize
- [ ] `map.js` loaded in `base.html`
- [ ] Explorer sidebar has Map View entry with canvas drag
- [ ] `workspace.js` labels dict includes `map: 'Map View'`
- [ ] Dark mode CSS inverts tiles
- [ ] `npm run build` succeeds with leaflet manifest entries

## Verification

- `rg 'initMap' frontend/static/js/map.js` — init function exists
- `rg 'leaflet' frontend/build.js` — build sections exist
- `rg 'leaflet.js' frontend/dist/manifest.json 2>/dev/null || rg 'leaflet' frontend/build.js` — manifest entry created
- `rg "map.*Map View" backend/app/templates/browser/views_explorer.html` — explorer entry
- `rg "map:" frontend/static/js/workspace.js` — label registered
- `rg "map.js" backend/app/templates/base.html` — script loaded
- `rg "map-container" frontend/static/css/views.css` — CSS present
- `rg "invalidateSize" frontend/static/js/map.js` — resize handling

## Inputs

- `backend/app/views/registry.py` — T01 registered map renderer
- `backend/app/views/router.py` — T01 added map branches serving map_view.html
- `backend/app/templates/browser/map_view.html` — T01 created template referencing initMap, leaflet.js/css via asset_url
- `backend/app/templates/browser/calendar_view.html` — pattern reference for template structure
- `frontend/static/js/calendar.js` — pattern reference for JS IIFE structure
- `frontend/build.js` — existing FullCalendar build section to follow
- `frontend/package.json` — existing devDependencies
- `backend/app/templates/base.html` — existing script tags to extend
- `backend/app/templates/browser/views_explorer.html` — existing explorer entries
- `frontend/static/js/workspace.js` — existing labels dict
- `frontend/static/css/views.css` — existing view CSS

## Expected Output

- `frontend/static/js/map.js` — new IIFE with initMap
- `frontend/build.js` — modified with Leaflet + markercluster sections
- `frontend/package.json` — modified with leaflet dependencies
- `frontend/static/css/views.css` — modified with map container + dark mode CSS
- `backend/app/templates/browser/views_explorer.html` — modified with Map View entry
- `frontend/static/js/workspace.js` — modified with map label
- `backend/app/templates/base.html` — modified with map.js script tag

## Observability Impact

- **Browser console**: `[map] Container not found` (warn), `[map] Failed to load markers` (error), `[map] Tile loading failed` (warn) — surface rendering failures without backend involvement
- **Inspection**: `initMap` on `window` — callable from DevTools to re-render map. Container stores `_mapInstance` for direct Leaflet API access
- **Build verification**: `frontend/dist/manifest.json` contains `leaflet.js`, `leaflet.css`, `leaflet-markercluster.js`, `leaflet-markercluster.css` entries — confirms vendoring pipeline succeeded
- **Failure visibility**: Missing Leaflet falls through to CDN fallback scripts in `map_view.html`; if both fail, `tryInit` polls indefinitely (visible in DevTools as repeated setTimeout calls)
