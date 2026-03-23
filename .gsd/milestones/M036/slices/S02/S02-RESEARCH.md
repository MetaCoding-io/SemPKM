# S02 Research: Business Model Canvas — 9-Box Poster Renderer

**Researched:** 2026-03-23
**Depth:** Light — straightforward replication of S01 quadrant pattern with different layout and data model

## Summary

S02 adds BMC types to the existing `business-planning` model and wires a new `bmc` renderer following the exact pattern S01 established for `quadrant`. The work decomposes into four clean tasks: (1) extend model archive with BMC ontology + shapes + views + seed, (2) wire backend service + router, (3) build frontend CSS Grid + inline-editing JS, (4) unit tests. No novel architecture — every integration point was proven in S01.

## Recommendation

Follow S01's pattern exactly. Four tasks, same decomposition as S01.

## Implementation Landscape

### Data Model Design

**Two new OWL classes** extend the existing ontology:

- `bp:BusinessModelCanvas` — container (subClassOf `gist:Collection`, like EisenhowerMatrix)
- `bp:BMCSection` — content item (subClassOf `bp:FrameworkItem`)

**Key properties on BMCSection:**

| Property | Type | Constraint | Purpose |
|---|---|---|---|
| `bp:sectionType` | xsd:string | `sh:in` 9 values | Which of the 9 BMC boxes |
| `bp:sectionContent` | xsd:string | Optional, multi-line | Free-text content for the section |
| `bp:belongsToCanvas` | ObjectProperty → bp:BusinessModelCanvas | maxCount 1 | Links section to its canvas |
| `dcterms:title` | xsd:string | minCount 1 | Display label |

The 9 standard `sh:in` values for `bp:sectionType`:
1. `key-partners`
2. `key-activities`
3. `key-resources`
4. `value-propositions`
5. `customer-relationships`
6. `channels`
7. `customer-segments`
8. `cost-structure`
9. `revenue-streams`

Using kebab-case strings (not display names) so the CSS Grid can use `data-section-type` attributes for positioning and color coding. Display names are a lookup dict in the service layer.

### Standard BMC Grid Layout

The canonical BMC poster is a 10-column × 3-row CSS Grid:

```
┌──────────┬──────────┬──────────────────────┬──────────┬──────────┐
│          │  Key     │                      │ Customer │          │
│   Key    │Activities│   Value              │Relations │ Customer │
│ Partners │──────────│   Propositions       │──────────│ Segments │
│          │  Key     │                      │          │          │
│          │Resources │                      │ Channels │          │
├──────────┴──────────┼──────────────────────┼──────────┴──────────┤
│   Cost Structure    │                      │  Revenue Streams    │
└─────────────────────┴──────────────────────┘─────────────────────┘
```

CSS Grid spec:
- `grid-template-columns: repeat(10, 1fr)` — 10 equal columns
- `grid-template-rows: 1fr 1fr 0.6fr` — 3 rows, bottom row shorter
- Key Partners: col 1-2, row 1-2
- Key Activities: col 3-4, row 1
- Key Resources: col 3-4, row 2
- Value Propositions: col 5-6, row 1-2
- Customer Relationships: col 7-8, row 1
- Channels: col 7-8, row 2
- Customer Segments: col 9-10, row 1-2
- Cost Structure: col 1-5, row 3
- Revenue Streams: col 6-10, row 3

### Backend Pattern (mirrors quadrant exactly)

**Registry** (`registry.py`): Add `"bmc"` entry with `template: "browser/bmc_view.html"`.

**Valid renderers** (`router.py`): Add `"bmc"` to `_VALID_RENDERERS` set.

**Service** (`service.py`): Three new methods:

1. `_detect_bmc_sections(type_iri)` — finds a SHACL property with 9 `sh:in` values (or checks `bp:sectionType` path keyword). Returns the property + section type list, or None.
2. `_build_bmc_select(type_iri, section_path, canvas_path, scope_filter)` — builds SPARQL SELECT fetching sections with their sectionType, sectionContent, title, and parent canvas IRI.
3. `execute_bmc_query(type_iri, section_prop, scope_filter)` — executes query, groups results into 9 buckets keyed by sectionType, returns `{"sections": [...], "section_types": [...], "total": N}`.

**Router elif branch**: Same pattern as quadrant — handle no-type, no-section-property, and happy path. Pass `sections` and `section_meta` to template.

**Data endpoint**: Add `"bmc"` to the `generic_view_data` renderer check. Return sections JSON.

### Frontend Pattern

**Template** (`bmc_view.html`): Same structure as `quadrant_view.html` — `<link>` to CSS, `.view-flex-column` wrapper, `type_filter_pills`, `view_toolbar`, then the BMC grid. Each section is a `div.bmc-section[data-section-type]` containing a header with section name and a content area. Content area uses a `<textarea>` (or `<div contenteditable>`) for inline editing.

**CSS** (`bmc.css`): CSS Grid with the 10-column layout above. Section-specific color coding (each section gets a distinct soft tint, like quadrant cells). Dark mode via `html[data-theme="dark"]` overrides. Full-height via `.view-flex-column` pattern.

**JS** (`bmc.js`): IIFE following `quadrant.js` structure:
- `initBMC(boardEl)` — attaches event listeners
- Inline editing: blur/focusout on textarea → `object.patch` with `bp:sectionContent` update
- Optional drag between sections: same `stopPropagation()` pattern if we allow moving items between BMC sections (lower priority — inline text editing is the primary interaction)
- Scope sync: listen for `sempkm:scope-changed`, re-fetch via htmx

### Files to Create/Modify

**Create:**
- `backend/app/templates/browser/bmc_view.html` (~100 lines)
- `frontend/static/js/bmc.js` (~120 lines)
- `frontend/static/css/bmc.css` (~280 lines)
- `backend/tests/test_bmc.py` (~25 tests)

**Modify:**
- `models/business-planning/ontology/business-planning.jsonld` — add BMCCanvas + BMCSection classes + properties
- `models/business-planning/shapes/business-planning.jsonld` — add NodeShapes for BMCCanvas + BMCSection
- `models/business-planning/views/business-planning.jsonld` — add ViewSpecs (table + bmc renderer)
- `models/business-planning/seed/business-planning.jsonld` — add 1 canvas + 9 section seed items
- `models/business-planning/manifest.yaml` — add icon definitions for BMC types, update description
- `backend/app/views/registry.py` — add `"bmc"` entry
- `backend/app/views/router.py` — add `"bmc"` to `_VALID_RENDERERS`, elif branches in `generic_view()` + `generic_view_data()`
- `backend/app/views/service.py` — add `_detect_bmc_sections()`, `_build_bmc_select()`, `execute_bmc_query()`

### Constraints and Gotchas

1. **Jinja2 dict key access**: Use `section['items']` not `section.items` — same bug as quadrant (KNOWLEDGE entry from kanban M031).
2. **nginx serves `/js/` and `/css/` not `/static/`**: Template must reference `/css/bmc.css` and `/js/bmc.js`.
3. **htmx script race**: Use the lazy-load `<script>` boot pattern from `quadrant_view.html` (create `<script>` element, set `onload`).
4. **Dockview stacking**: If adding drag-between-sections, `stopPropagation()` on all drag events.
5. **CSS Grid `data-section-type` selectors**: Position each section via `[data-section-type="key-partners"] { grid-column: 1/3; grid-row: 1/3; }` etc.
6. **Inline editing save**: `object.patch` with `bp:sectionContent` property. Debounce saves on textarea input (300-500ms) to avoid excessive API calls during typing.
7. **Empty sections**: Seed data should provide all 9 sections even if content is empty — the grid should always show all 9 boxes. Query must use OPTIONAL for sectionContent.

### Verification Strategy

- **Unit tests**: `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v` — section detection, SPARQL building, result grouping
- **JSON-LD parse**: All modified model files load via rdflib without error
- **Manifest validates**: `parse_manifest()` still works with added BMC types
- **Frontend files**: bmc.js has `stopPropagation` calls (if drag enabled), CSS Grid layout correct, dark mode rules present
- **Browser verification**: BMC view renders 9-box grid in dockview tab, inline edit saves content, dark mode readable

### Seed Data Design

One BMC instance with realistic content:

- **Canvas**: "SemPKM Business Model" — a self-referential BMC for the product itself
- **9 Sections**: Each with 2-4 bullet points of realistic content
  - Key Partners: "Open-source community, RDF4J/Apache Jena, Cloud hosting providers"
  - Key Activities: "Knowledge graph R&D, Mental Model development, Community engagement"
  - etc.

### Task Decomposition (for planner)

| Task | Scope | Est | Risk |
|---|---|---|---|
| T01 | Model archive: ontology + shapes + views + seed for BMC types | 25min | low — follows S01 pattern exactly |
| T02 | Backend: service methods + router wiring + registry | 25min | low — mirrors quadrant wiring |
| T03 | Frontend: template + CSS Grid + JS inline editing | 30min | medium — CSS Grid layout needs care |
| T04 | Unit tests for BMC pipeline | 20min | low — follows test_quadrant.py structure |

T01 → T02 → T03 → T04 (sequential — each depends on prior)

### What the Planner Must Know

- The `business-planning` model namespace is `urn:sempkm:model:business-planning:` with prefix `bp:`. All new types use this namespace.
- S01 added `bp:FrameworkItem` as the abstract base — `bp:BMCSection` should subclass it.
- S01 added `bp:EisenhowerMatrix` subclassing `gist:Collection` — `bp:BusinessModelCanvas` follows the same pattern.
- The router has an `else: # kanban` fallback at the end of the elif chain — new `bmc` elif must go before it.
- The `generic_view_data` function checks `renderer not in ("graph", "calendar", "map", "timeline", "quadrant")` — add `"bmc"` to this tuple.
- The seed file already has 9 Eisenhower items — adding 10 more BMC items (1 canvas + 9 sections) is fine.
- `PropertyShape` has `.in_values` list and `.path` string — the BMC detection method needs to find a property with 9 in_values.
