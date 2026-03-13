---
id: T03
parent: S07
milestone: M003
provides:
  - ABox Browser with type counts and instance drill-down
  - RBox Legend with object/datatype property tables
  - Three-tab ontology viewer page (/browser/ontology)
  - openOntologyTab() workspace integration with command palette entry
key_files:
  - backend/app/ontology/service.py
  - backend/app/ontology/router.py
  - backend/app/templates/browser/ontology/ontology_page.html
  - backend/app/templates/browser/ontology/abox_browser.html
  - backend/app/templates/browser/ontology/abox_instances.html
  - backend/app/templates/browser/ontology/rbox_legend.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
key_decisions:
  - ABox instance counts use UNION of current+inferred graphs rather than FROM clause aggregation, because FROM aggregation merges differently for data graphs vs ontology graphs
  - RBox label resolution uses same COALESCE(skos:prefLabel, rdfs:label, local-name) pattern as TBox for consistency
  - Ontology tab switching uses inline JS function rather than htmx tab component, keeping it lightweight and consistent with existing panel patterns
patterns_established:
  - special-panel component pattern extended for ontology viewer (specialType='ontology' → GET /browser/ontology)
  - ABox drill-down pattern: type list with hx-trigger="click once" expands instance list inline
  - Ontology viewer tabs: pure JS tab switching with htmx lazy-loading per pane
observability_surfaces:
  - logger.debug("ABox: %d types with instances (%.2fs)") with count and timing
  - logger.debug("ABox instances of %s: %d results (%.2fs)") per type drill-down
  - logger.debug("RBox: %d object properties, %d datatype properties (%.2fs)") with counts and timing
  - Error states rendered as visible messages in each tab section rather than blank content
duration: 35min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Build ABox Browser and RBox Legend with ontology viewer panel

**Added ABox Browser (type counts + instance drill-down), RBox Legend (property reference tables), three-tab ontology viewer page, and workspace integration via openOntologyTab() + command palette.**

## What Happened

1. Extended `OntologyService` with ABox methods (`get_type_counts`, `get_instances`) and RBox method (`get_properties`). ABox queries all owl:Class IRIs from ontology graphs, then counts instances across current+inferred graphs using UNION. RBox queries owl:ObjectProperty and owl:DatatypeProperty across all ontology graphs with domain/range label resolution.

2. Extended `ontology_router` with main page route (`GET /browser/ontology`), ABox routes (`GET /browser/ontology/abox`, `GET /browser/ontology/abox/instances?class=`), and RBox route (`GET /browser/ontology/rbox`).

3. Created four new templates: `ontology_page.html` (three-tab container with lazy loading), `abox_browser.html` (type list with count badges and source badges), `abox_instances.html` (clickable instance list using openTab()), `rbox_legend.html` (two-section property table with domain/range columns).

4. Added `openOntologyTab()` to workspace.js following the special-panel pattern, plus `_addOntologyPaletteEntry()` for command palette integration under "Views" section.

5. Added CSS styles for the ontology viewer: tabs, ABox type rows with count badges, instance list, RBox tables.

## Verification

- **Command palette:** Opened via F1 → typed "ontology" → "Open: Ontology Viewer" visible under Views → clicked → ontology viewer tab opened
- **TBox tab:** Loaded immediately with gist class hierarchy (Account, Agreement, Aspect, etc.) with source badges; expanded Content → showed Address, Content Expression, Contingent Event subclasses
- **ABox tab:** Clicked → loaded with 4 types: Concept (363), Note (540), Person (23), Project (14) — all with basic-pkm badges; clicked Person → 23 instances shown with labels (Arnold Schwarzenegger, Carl Sagan, etc.)
- **Instance click:** Clicked a Person instance → new workspace tab opened with "Edit Person" form
- **RBox tab:** Clicked → loaded with Object Properties (71) and Datatype Properties (55) tables with domain/range columns showing real data (Has Note: Project→Note, latitude: Geographic Point→XMLSchema#double)
- **Existing tests:** 16/16 passed (`uv run python -m pytest tests/test_ontology_service.py -v`)
- **API endpoints:** All returning 200 (verified via docker compose logs)
- **Browser assertions:** 7/7 PASS for viewer structure, tabs, and content visibility

## Diagnostics

- **Check ABox types:** `curl http://localhost:3000/browser/ontology/abox` (requires auth session)
- **Check ABox instances:** `curl http://localhost:3000/browser/ontology/abox/instances?class=<url-encoded-iri>`
- **Check RBox:** `curl http://localhost:3000/browser/ontology/rbox`
- **Check main page:** `curl http://localhost:3000/browser/ontology`
- **Debug SPARQL:** set `LOG_LEVEL=DEBUG` → ABox/RBox queries log counts and timing
- **Failure mode:** SPARQL errors → logged with traceback, each tab section shows error message rather than blank content

## Deviations

None.

## Known Issues

- Some ABox Person instances show UUIDs instead of labels — these are instances that lack dcterms:title/rdfs:label/skos:prefLabel/foaf:name properties in the current graph (label resolution works correctly for instances that have labels)

## Files Created/Modified

- `backend/app/ontology/service.py` — extended with get_type_counts(), get_instances(), get_properties() methods
- `backend/app/ontology/router.py` — extended with ontology_page, abox_browser, abox_instances, rbox_legend routes
- `backend/app/templates/browser/ontology/ontology_page.html` — new three-tab layout container
- `backend/app/templates/browser/ontology/abox_browser.html` — new type counts view with drill-down
- `backend/app/templates/browser/ontology/abox_instances.html` — new instance list with click-to-open
- `backend/app/templates/browser/ontology/rbox_legend.html` — new property reference table
- `frontend/static/js/workspace.js` — added openOntologyTab() and command palette entry
- `frontend/static/css/workspace.css` — added ontology viewer styles (tabs, ABox, RBox)
