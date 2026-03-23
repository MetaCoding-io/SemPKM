---
id: T02
parent: S01
milestone: M036
provides:
  - quadrant renderer type in _VALID_RENDERERS and RENDERER_REGISTRY
  - _detect_quadrant_axes() method on ViewSpecService (finds two sh:in properties with 2 values each)
  - execute_quadrant_query() method on ViewSpecService (groups items into quadrant buckets by axis values)
  - quadrant branch in generic_view() and generic_view_data() router endpoints
  - quadrant_view.html Jinja2 template with view-flex-column wrapper, type_filter_pills, view_toolbar, 2×2 grid
key_files:
  - backend/app/views/router.py
  - backend/app/views/service.py
  - backend/app/views/registry.py
  - backend/app/templates/browser/quadrant_view.html
key_decisions:
  - _detect_quadrant_axes finds properties with exactly 2 sh:in values (general), not hardcoded to "high"/"low"
  - Eisenhower-specific quadrant labels ("Do First", "Schedule", "Delegate", "Eliminate") in a lookup dict with generic fallback
  - Template uses lazy-load pattern for quadrant.js (consistent with calendar/map CDN loading pattern)
patterns_established:
  - Quadrant axis detection follows _detect_status_field pattern — prefers keyword in path ("urgency"/"importance") with fallback to first 2 candidates
  - _build_quadrant_select uses non-OPTIONAL axis bindings (items missing either axis are excluded), matching _build_map_select pattern
  - Quadrant data endpoint at /browser/views/generic/quadrant/data returns JSON with quadrants array, axes object, and total count
observability_surfaces:
  - logger.info("generic_view: renderer=quadrant type=%s ...") in router on each view request
  - logger.info("execute_quadrant_query: type=%s total=%d quadrants=%d") in service after query execution
  - /browser/views/generic/quadrant/data?type=<iri> JSON endpoint for debugging quadrant data
  - Error template shows descriptive message when type has no quadrant-axis properties
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Wire quadrant renderer into view router + backend data endpoint

**Added quadrant renderer to the view system with axis detection from SHACL sh:in constraints, SPARQL-based quadrant grouping, JSON data endpoint, and server-rendered Jinja2 template.**

## What Happened

Wired the quadrant renderer into all three layers of the view system:

1. **Registry & valid renderers**: Added `"quadrant"` to both `_VALID_RENDERERS` set in router.py and `RENDERER_REGISTRY` dict in registry.py.

2. **ViewSpecService** (service.py): Added three methods following existing kanban/map patterns:
   - `_detect_quadrant_axes()` — finds two SHACL properties with exactly 2 `sh:in` values. Prefers paths containing "urgency" for x-axis and "importance" for y-axis (case-insensitive). Falls back to first two candidates. Returns `(x_axis, y_axis, x_values, y_values)` or `(None, None, [], [])`.
   - `_build_quadrant_select()` — builds a SELECT query with non-OPTIONAL axis bindings (items missing either axis are excluded). Supports scope filter injection.
   - `execute_quadrant_query()` — executes the SPARQL query, groups items into (x_value, y_value) buckets, assigns Eisenhower-specific labels ("Do First", "Schedule", "Delegate", "Eliminate") with generic fallback. Handles unclassified items.

3. **Router** (router.py): Added `elif renderer == "quadrant"` branch in `generic_view()` following the exact pattern of map/timeline/kanban branches. Added quadrant branch in `generic_view_data()` for JSON endpoint. Both handle no-type-selected and no-axes-found error cases with descriptive messages.

4. **Template** (quadrant_view.html): Uses `view-flex-column` wrapper, includes `type_filter_pills.html` and `view_toolbar.html`. Renders a `.quadrant-board` container with `.quadrant-grid` containing 4 `.quadrant-cell` divs (server-rendered via Jinja2 loop). Each cell has header (label + count) and body with draggable `.quadrant-card` items. Unclassified items render in a separate section below the grid. Uses lazy-load pattern for `quadrant.js` (T03 will create the JS file).

## Verification

1. `"quadrant"` in `_VALID_RENDERERS` — confirmed via Python import
2. `"quadrant"` in `RENDERER_REGISTRY` — confirmed with correct template path
3. All four ViewSpecService methods exist and are callable
4. `_build_quadrant_select()` generates correct SPARQL with xValue/yValue bindings
5. `_quadrant_label()` returns Eisenhower-specific labels and generic fallback
6. Template file exists at expected path
7. Router module imports cleanly
8. 34 references to "quadrant" in router.py (well above the >5 threshold)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.views.router import _VALID_RENDERERS; assert 'quadrant' in _VALID_RENDERERS; print('OK')"` | 0 | ✅ pass | 1.5s |
| 2 | `cd backend && .venv/bin/python -c "from app.views.registry import RENDERER_REGISTRY; assert 'quadrant' in RENDERER_REGISTRY; print('OK')"` | 0 | ✅ pass | 1.5s |
| 3 | `cd backend && .venv/bin/python -c "from app.views.service import ViewSpecService; assert hasattr(ViewSpecService, '_detect_quadrant_axes'); assert hasattr(ViewSpecService, 'execute_quadrant_query'); print('OK')"` | 0 | ✅ pass | 1.5s |
| 4 | `cd backend && .venv/bin/python -c "...build_quadrant_select test..."` | 0 | ✅ pass | 1.5s |
| 5 | `cd backend && .venv/bin/python -c "..._quadrant_label test..."` | 0 | ✅ pass | 1.5s |
| 6 | `test -f backend/app/templates/browser/quadrant_view.html && echo OK` | 0 | ✅ pass | 0.1s |
| 7 | `rg 'quadrant' backend/app/views/router.py \| wc -l` → 34 | 0 | ✅ pass | 0.2s |

## Diagnostics

- **Check quadrant in valid renderers:** `cd backend && .venv/bin/python -c "from app.views.router import _VALID_RENDERERS; print('quadrant' in _VALID_RENDERERS)"`
- **Check quadrant in registry:** `cd backend && .venv/bin/python -c "from app.views.registry import RENDERER_REGISTRY; print(RENDERER_REGISTRY.get('quadrant'))"`
- **Test axis detection (requires running triplestore with model installed):** `curl -s http://localhost:3901/browser/views/generic/quadrant/data?type=urn:sempkm:model:business-planning:EisenhowerItem | python3 -m json.tool`
- **Verify SPARQL query shape:** `cd backend && .venv/bin/python -c "from app.views.service import ViewSpecService; print(ViewSpecService._build_quadrant_select('urn:test:Type', 'urn:test:x', 'urn:test:y'))"`
- **Runtime logs:** `docker compose logs api | grep 'quadrant'` shows axis detection and query execution

## Deviations

- Pre-flight requested adding observability impact to T02-PLAN.md — addressed in this summary's observability_surfaces field instead of modifying the plan mid-execution.
- Pre-flight requested adding a diagnostic verification step to S01-PLAN.md — added the curl-based data endpoint check to the Verification section.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/registry.py` — Added `"quadrant"` entry to RENDERER_REGISTRY
- `backend/app/views/router.py` — Added `"quadrant"` to _VALID_RENDERERS, added quadrant branch to generic_view() and generic_view_data()
- `backend/app/views/service.py` — Added _detect_quadrant_axes(), _build_quadrant_select(), _quadrant_label(), execute_quadrant_query() methods to ViewSpecService
- `backend/app/templates/browser/quadrant_view.html` — New Jinja2 template for quadrant grid view
- `.gsd/milestones/M036/slices/S01/S01-PLAN.md` — Added diagnostic verification step per pre-flight requirement
