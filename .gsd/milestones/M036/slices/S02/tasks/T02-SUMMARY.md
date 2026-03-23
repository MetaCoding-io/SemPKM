---
id: T02
parent: S02
milestone: M036
provides:
  - bmc renderer registered in RENDERER_REGISTRY and _VALID_RENDERERS
  - elif branch for renderer=="bmc" in generic_view() with error handling
  - BMC data endpoint in generic_view_data() returning JSON
  - _detect_bmc_sections() service method finding 9-value sh:in properties
  - _build_bmc_select() SPARQL builder with OPTIONAL sectionContent/canvas
  - execute_bmc_query() grouping results into 9 section buckets
  - bmc_view.html Jinja2 template with CSS Grid container and lazy-load JS
key_files:
  - backend/app/views/registry.py
  - backend/app/views/router.py
  - backend/app/views/service.py
  - backend/app/templates/browser/bmc_view.html
key_decisions:
  - BMC section detection uses 9-value sh:in count (not hardcoded property IRI) — any type with exactly 9 enum values on a property will qualify, with preference for "sectiontype" in path name
  - Canvas property detection uses target_class containing "canvas" or "businessmodelcanvas" — general enough for model evolution
  - sectionContent IRI is hardcoded in SPARQL builder as urn:sempkm:model:business-planning:sectionContent — acceptable coupling since BMC is a specific model feature
patterns_established:
  - BMC backend follows exact quadrant wiring pattern — registry entry, _VALID_RENDERERS, elif branch in generic_view(), data endpoint in generic_view_data(), three service methods (detect, build, execute)
  - BMC_SECTION_TYPES class-level dict maps kebab-case to display names — used in both service grouping and template rendering
observability_surfaces:
  - logger.info("generic_view: renderer=bmc type=%s ...") in router on BMC view request
  - logger.info("execute_bmc_query: type=%s total=%d sections=%d") in service after query
  - /browser/views/generic/bmc/data?type=<iri> JSON endpoint for raw data inspection
  - Error template shown when type has no 9-value sh:in property
duration: 15min
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Wire BMC backend — service detection, SPARQL query, router branches, registry

**Wired `bmc` renderer through all three backend layers (registry, router, service) with section detection via 9-value sh:in, SPARQL grouping into 9 section buckets, and a Jinja2 template with lazy-load JS boot pattern.**

## What Happened

Followed the quadrant wiring pattern exactly across four files:

- **Registry** (`registry.py`): Added `"bmc"` entry with template `"browser/bmc_view.html"`.

- **Router** (`router.py`): Added `"bmc"` to `_VALID_RENDERERS` set. Added `elif renderer == "bmc":` branch in `generic_view()` before the `else: # kanban` fallback — handles no-type (error "Select a type to use Canvas View"), no-section-property detection failure, and happy path (calls service, renders template with data URL). Added `"bmc"` to `generic_view_data()` renderer tuple with JSON data endpoint returning sections/section_types/total.

- **Service** (`service.py`): Added three methods to `ViewSpecService`:
  - `_detect_bmc_sections(type_iri)`: Gets NodeShapeForm, finds property with exactly 9 `sh:in` values (prefers path containing "sectiontype"), also detects canvas link property by target_class containing "canvas"/"businessmodelcanvas". Returns `(section_prop, canvas_prop)`.
  - `_build_bmc_select(type_iri, section_path, canvas_path, scope_filter)`: Builds SPARQL SELECT with required sectionType, OPTIONAL label/sectionContent/canvas, and optional scope sub-select.
  - `execute_bmc_query(type_iri, section_prop, canvas_prop, scope_filter)`: Executes query, groups into 9 buckets keyed by sectionType value, returns `{"sections": [...], "section_types": {...}, "total": N}`.
  - `BMC_SECTION_TYPES` class-level dict mapping all 9 kebab-case values to display names.

- **Template** (`bmc_view.html`): `.view-flex-column` wrapper, type filter pills, view toolbar, CSS Grid container with 9 `div.bmc-section[data-section-type]` cells each containing header (name + count) and content area (textareas for items, empty hint if none). Uses `section['items']` bracket notation (Jinja2 dict key access). Lazy-load JS boot pattern for `/js/bmc.js`.

## Verification

All 5 task-level verification checks pass:

1. `from app.views.registry import RENDERER_REGISTRY; assert 'bmc' in RENDERER_REGISTRY` — ✅
2. `grep -c '"bmc"' backend/app/views/router.py` returns 7 (≥ 3) — ✅
3. `grep "section\['items'\]" backend/app/templates/browser/bmc_view.html` — matches 3 lines — ✅
4. `grep '/css/bmc.css' backend/app/templates/browser/bmc_view.html` — matches — ✅
5. `grep '/js/bmc.js' backend/app/templates/browser/bmc_view.html` — matches — ✅

Additional checks:
- All 3 Python files pass `ast.parse()` — syntax correct
- ViewSpecService has all 4 BMC attributes (_detect_bmc_sections, _build_bmc_select, execute_bmc_query, BMC_SECTION_TYPES)
- SPARQL builder produces valid queries with and without scope filter and canvas path
- All 5 model JSON-LD files still parse correctly

Slice-level checks applicable to T02:
- `bmc` present in `_VALID_RENDERERS` and `RENDERER_REGISTRY` — ✅
- All 5 JSON-LD model files parse — ✅
- `parse_manifest()` validates — ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.views.registry import RENDERER_REGISTRY; assert 'bmc' in RENDERER_REGISTRY; print('OK')"` | 0 | ✅ pass | 1.5s |
| 2 | `grep -c '"bmc"' backend/app/views/router.py` | 0 | ✅ pass (7) | 0.1s |
| 3 | `grep "section\['items'\]" backend/app/templates/browser/bmc_view.html` | 0 | ✅ pass (3 matches) | 0.1s |
| 4 | `grep '/css/bmc.css' backend/app/templates/browser/bmc_view.html` | 0 | ✅ pass | 0.1s |
| 5 | `grep '/js/bmc.js' backend/app/templates/browser/bmc_view.html` | 0 | ✅ pass | 0.1s |
| 6 | `ast.parse()` on registry.py, router.py, service.py | 0 | ✅ pass | 0.5s |
| 7 | `ViewSpecService` attribute existence check | 0 | ✅ pass | 1.5s |
| 8 | `_build_bmc_select()` produces valid SPARQL | 0 | ✅ pass | 1.5s |

## Diagnostics

- **Registry check:** `cd backend && python3 -c "from app.views.registry import RENDERER_REGISTRY; print(RENDERER_REGISTRY.keys())"`
- **Service methods check:** `cd backend && python3 -c "from app.views.service import ViewSpecService; print(ViewSpecService.BMC_SECTION_TYPES)"`
- **SPARQL preview:** `cd backend && python3 -c "from app.views.service import ViewSpecService; print(ViewSpecService._build_bmc_select('urn:sempkm:model:business-planning:BMCSection', 'urn:sempkm:model:business-planning:sectionType'))"`
- **Runtime data endpoint:** `GET /browser/views/generic/bmc/data?type=urn:sempkm:model:business-planning:BMCSection`

## Deviations

None — followed quadrant wiring pattern exactly.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/registry.py` — added `"bmc"` entry to RENDERER_REGISTRY
- `backend/app/views/router.py` — added `"bmc"` to _VALID_RENDERERS, elif branch in generic_view(), data endpoint in generic_view_data()
- `backend/app/views/service.py` — added BMC_SECTION_TYPES, _detect_bmc_sections(), _build_bmc_select(), execute_bmc_query()
- `backend/app/templates/browser/bmc_view.html` — Jinja2 template with CSS Grid container and lazy-load JS
- `.gsd/milestones/M036/slices/S02/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
