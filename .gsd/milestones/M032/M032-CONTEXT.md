# M032 — Block-Based Custom UI Builder (Research & Design)

## Goal

Design the architecture for a Notion-inspired block-based composition system that lets users build custom dashboards, views, and multi-object creation forms from reusable blocks/widgets. Produce a design document and proof-of-concept, not a full implementation.

## Background

SemPKM already has dashboards (grid layout + blocks) and views (table/card/graph/kanban). But:

- Dashboards have a fixed set of block types (`view-embed`, `markdown`, `object-embed`, `create-form`, `sparql-result`, `divider`) with a rigid grid layout
- Views are single-purpose (one renderer, one data scope)
- There's no way to create a custom multi-object form (e.g., "create a Project with 3 Tasks and a Note in one screen")

The vision is a unified block composition system — like Notion's block editor or Zabbix's dashboard builder — where the user drags and arranges blocks to compose:

1. **Custom dashboards** — mix stat cards, charts, views, markdown, and embedded objects in flexible layouts
2. **Custom views** — compose multiple view blocks side by side (e.g., a kanban next to a graph filtered by different queries)
3. **Custom forms** — multi-object creation forms built from SHACL-driven form blocks, allowing users to create multiple related objects in one workflow

## Research Questions

### RDF Data Model
- How do we store block layouts in RDF? Is this better as JSON-LD in a literal, or as a full RDF graph with block → slot → config triples?
- What's the right balance between RDF purity (everything is triples) and pragmatism (JSON blob in a literal, like the current `blocks_json` column)?
- How do custom forms reference SHACL shapes? Does a form block point to a shape IRI + override some field ordering/visibility?
- How do we version/snapshot block layouts?

### Widget Library
- What widget types are needed? Inventory from Notion (text, heading, list, toggle, callout, divider, table, image, embed) + Zabbix (graph, gauge, pie chart, stat card, clock, map) + SemPKM-specific (SHACL form, view embed, SPARQL result, object card, saved query scope)
- Which widgets need config panels vs. inline editing?
- How do widgets declare their data dependencies (e.g., "I need a type IRI" or "I need a SPARQL query")?

### Composition & Layout
- Notion uses a linear block list with nested blocks and column dividers. Zabbix uses a 2D grid with absolute positioning. Which model fits SemPKM?
- Can we unify the current dashboard grid layout with the block system, or do we need a migration?
- How do blocks communicate? (e.g., clicking a row in a table block could filter a graph block)

### Custom Multi-Object Forms
- How does a form block reference a SHACL shape for a specific type?
- How do we express "create a Project, then create 3 Tasks linked to it" in block form?
- What's the save/submit semantics? Single transaction across all blocks? Per-block?
- How do form blocks handle validation (SHACL constraints)?

## Deliverables

1. **Research document** (`M032-RESEARCH.md`) — survey of Notion block model, Zabbix dashboard widgets, and any RDF-native UI composition approaches
2. **Design document** — proposed RDF data model for block layouts, widget type registry, layout engine approach, and form block semantics
3. **Proof of concept** — minimal working prototype demonstrating:
   - A simple block editor (drag to reorder, add/remove blocks)
   - 2-3 widget types rendering real data
   - Block layout persisted and restored
4. **Widget inventory** — categorized list of planned widget types with config schemas

## Existing Code to Build On

| Component | Current State |
|-----------|---------------|
| Dashboard blocks | `dashboard/models.py` — `VALID_BLOCK_TYPES` set, `blocks_json` column (JSON text), grid layouts |
| Dashboard builder | `templates/browser/dashboard_builder.html` — block add/remove/configure UI |
| Dashboard service | `dashboard/service.py` — CRUD with block validation |
| SHACL forms | `templates/browser/shacl_form.html`, `form_renderer.py` — property-driven form generation |
| View registry | `views/registry.py` — discovers and registers model-declared view specs |
| Saved queries | `sparql/query_service.py` — full CRUD, sharing, promotion |

## Constraints

- Must be backwards-compatible with existing dashboards (migration path, not breaking change)
- SHACL shapes are the source of truth for form field definitions — block forms compose shapes, they don't replace them
- RDF storage preferred but pragmatic JSON-in-literal is acceptable if the alternative is over-engineering
- htmx for server-rendered block content; minimal client-side JS for drag-drop layout editing
- Cytoscape.js for any graph widgets
- No React/Vue/Angular — vanilla JS + htmx
