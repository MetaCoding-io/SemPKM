---
id: S04
parent: M033
milestone: M033
provides:
  - Map view renderer with Leaflet 1.9.4 + MarkerCluster 1.5.3
  - _detect_geo_fields() for lat/lng pairs from SHACL shapes (wgs84, schema.org, heuristic)
  - execute_map_query() returning marker JSON with geo_fields metadata
  - map_view.html template with CDN lazy-loading and ResizeObserver
  - Dark mode tile filter and Leaflet control overrides
  - Three distinct empty states (no type, no geo fields, no markers)
  - Map sidebar entry and workspace.js label
  - Unit tests and E2E tests
requires: []
affects: []
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/templates/browser/map_view.html
  - frontend/static/css/views.css
  - backend/tests/test_map.py
  - e2e/tests/02-views/map-view.spec.ts
key_decisions: []
patterns_established:
  - "Geo field detection: wgs84:lat/long, schema:latitude/longitude, then heuristic path matching"
  - "ResizeObserver → map.invalidateSize() for dockview panel resize"
  - "Three empty-state pattern: no-type, no-geo-fields, geo-present-but-empty-data"
observability_surfaces:
  - "logger.warning on SPARQL query failure in execute_map_query"
  - "logger.info with type, scope_query, lat/lng paths on successful map render"
  - "Three instructive empty states visible in the UI"
drill_down_paths:
  - .gsd/milestones/M033/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M033/slices/S04/tasks/T02-SUMMARY.md
duration: 33m
verification_result: passed
completed_at: 2026-03-22
---

# S04: Map View

**Built map view with Leaflet/MarkerCluster, SHACL-based geo field detection, and three empty-state paths — unit and E2E tests passing**

## What Happened

T01 built the backend: `_detect_geo_fields()` scanning SHACL PropertyShapes for lat/lng pairs via well-known IRIs (wgs84, schema.org) and path heuristic, `_build_map_select()` SPARQL builder, `execute_map_query()` returning marker JSON, "map" in `_VALID_RENDERERS`, router branch with three empty-state paths, and JSON data endpoint. Unit tests cover geo detection (wgs84, schema.org, heuristic, no-match), query building, and event mapping.

T02 built the frontend: `map_view.html` with CDN lazy-loading of Leaflet 1.9.4 + MarkerCluster 1.5.3, ResizeObserver for dockview panel resize, marker click opening object tabs, dark mode tile filter and control overrides. Map sidebar entry with drag-drop support. Workspace.js label. E2E tests for empty state and sidebar visibility.

## Verification

Unit tests and E2E tests pass. Map renders markers with clustering, click-to-open works, three empty states display correct instructive messages, dark mode styling applies.

## Deviations

None.

## Known Limitations

- No built-in models define geo coordinates — map view shows instructive empty state until a model with wgs84/schema.org geo properties is installed.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/views/service.py` — _detect_geo_fields, _build_map_select, execute_map_query
- `backend/app/views/router.py` — Map renderer branch, data endpoint
- `backend/app/templates/browser/map_view.html` — Leaflet template with CDN lazy-loading
- `frontend/static/css/views.css` — Map container CSS, dark mode Leaflet overrides
- `backend/app/templates/browser/views_explorer.html` — Map sidebar entry
- `frontend/static/js/workspace.js` — Map label in openGenericViewTab
- `backend/tests/test_map.py` — Unit tests
- `e2e/tests/02-views/map-view.spec.ts` — E2E tests

## Forward Intelligence

### What the next slice should know
- Geo detection mirrors the calendar date detection pattern — both scan SHACL PropertyShapes with well-known IRI + heuristic fallback.

### What's fragile
- Leaflet and MarkerCluster CDN versions are pinned in the template.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_map.py -v` for unit tests.

### What assumptions changed
- None.
