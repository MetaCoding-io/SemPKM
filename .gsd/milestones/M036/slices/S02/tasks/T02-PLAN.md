---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T02: Wire BMC backend — service detection, SPARQL query, router branches, registry

**Slice:** S02 — Business Model Canvas — 9-Box Poster Renderer
**Milestone:** M036

## Description

Wire the `bmc` renderer through all three backend layers (registry, router, service) and create the Jinja2 template. Mirrors the quadrant wiring pattern exactly: registry entry, `_VALID_RENDERERS` set, elif branches in `generic_view()` and `generic_view_data()`, and three service methods for section detection, SPARQL query building, and result grouping.

## Steps

1. **Read** the existing quadrant wiring to understand the pattern: `backend/app/views/registry.py` (RENDERER_REGISTRY entry), `backend/app/views/router.py` (lines ~208 for `_VALID_RENDERERS`, ~751-848 for quadrant elif branch, ~956 for `generic_view_data` renderer check), `backend/app/views/service.py` (lines ~1984-2220 for quadrant methods). Also read `backend/app/templates/browser/quadrant_view.html` as the template pattern.
2. **Add registry + router wiring**: (a) In `registry.py`, add `"bmc": {"type": "bmc", "template": "browser/bmc_view.html"}` to `RENDERER_REGISTRY`. (b) In `router.py`, add `"bmc"` to the `_VALID_RENDERERS` set. (c) Add `"bmc"` to the tuple in `generic_view_data()` (line ~956: add to `("graph", "calendar", "map", "timeline", "quadrant")`). (d) Add an `elif renderer == "bmc":` branch in `generic_view()` BEFORE the `else: # kanban` fallback — handle no-type (error message "Select a type to use Canvas View"), no-section-property (error "This type has no BMC section type property"), and happy path (call service, render template). (e) Add BMC data endpoint logic in `generic_view_data()`.
3. **Add service methods** to `backend/app/views/service.py`: (a) `_detect_bmc_sections(self, type_iri: str)` — get NodeShapeForm, find a property whose `sh:in` has exactly 9 values (prefer path containing "sectiontype", case-insensitive), return `(section_prop, canvas_prop_or_None)` or `(None, None)`. Also look for an ObjectProperty pointing to `bp:BusinessModelCanvas` as the canvas link property. (b) `_build_bmc_select(self, type_iri, section_path, canvas_path, scope_filter)` — build SPARQL SELECT fetching `?s ?title ?sectionType ?sectionContent ?canvas` with OPTIONAL for `sectionContent` and `canvas`. (c) `execute_bmc_query(self, type_iri, section_prop, canvas_prop, scope_filter)` — execute query, group results into 9 buckets keyed by sectionType value. Return `{"sections": [...], "section_types": BMC_SECTION_TYPES, "total": N}` where each section has `type`, `label`, `items`. Add a `BMC_SECTION_TYPES` dict mapping kebab-case to display names (e.g. `"key-partners": "Key Partners"`).
4. **Create template** `backend/app/templates/browser/bmc_view.html`: Follow `quadrant_view.html` structure — `<link rel="stylesheet" href="/css/bmc.css">`, `.view-flex-column` wrapper, include `type_filter_pills.html` and `view_toolbar.html`, then the BMC grid. Each section is a `div.bmc-section[data-section-type="..."]` containing a `.bmc-section-header` with display name and a `.bmc-section-content` area. Content area renders items as textareas (one per BMCSection object) or a `.bmc-empty-hint` if no items. Use `section['items']` not `section.items` for dict key access. Add lazy-load JS boot pattern at bottom (create `<script>` element, set `src="/js/bmc.js"`, set `onload` to call `initBMC()`).

## Must-Haves

- [ ] `"bmc"` in `RENDERER_REGISTRY` with correct template path
- [ ] `"bmc"` in `_VALID_RENDERERS` set
- [ ] `"bmc"` in `generic_view_data()` renderer tuple
- [ ] elif branch for `renderer == "bmc"` in `generic_view()` — before `else: # kanban`
- [ ] `_detect_bmc_sections()` finds property with 9 `sh:in` values
- [ ] `_build_bmc_select()` builds SPARQL with OPTIONAL for sectionContent
- [ ] `execute_bmc_query()` groups results into 9 section buckets
- [ ] `bmc_view.html` uses `/css/bmc.css`, `/js/bmc.js` paths (not `/static/`)
- [ ] Template uses `section['items']` dict bracket notation

## Verification

- `cd backend && python3 -c "from app.views.registry import RENDERER_REGISTRY; assert 'bmc' in RENDERER_REGISTRY; print('OK')"` — passes
- `grep -c '"bmc"' backend/app/views/router.py` returns ≥ 3
- `grep "section\['items'\]" backend/app/templates/browser/bmc_view.html` — matches (not `section.items`)
- `grep '/css/bmc.css' backend/app/templates/browser/bmc_view.html` — matches
- `grep '/js/bmc.js' backend/app/templates/browser/bmc_view.html` — matches

## Inputs

- `backend/app/views/registry.py` — existing registry with quadrant entry to follow
- `backend/app/views/router.py` — existing router with quadrant elif to follow
- `backend/app/views/service.py` — existing service with quadrant methods to follow
- `backend/app/templates/browser/quadrant_view.html` — template pattern to follow
- `models/business-planning/ontology/business-planning.jsonld` — BMC classes added by T01
- `models/business-planning/shapes/business-planning.jsonld` — BMC shapes added by T01

## Expected Output

- `backend/app/views/registry.py` — `"bmc"` entry added to RENDERER_REGISTRY
- `backend/app/views/router.py` — `"bmc"` in `_VALID_RENDERERS`, elif branch in `generic_view()`, data endpoint in `generic_view_data()`
- `backend/app/views/service.py` — `_detect_bmc_sections()`, `_build_bmc_select()`, `execute_bmc_query()` methods added
- `backend/app/templates/browser/bmc_view.html` — Jinja2 template with CSS Grid container and lazy-load JS
