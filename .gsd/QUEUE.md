# GSD Queue

Append-only log of queued future milestones and ideas.

---

## Rethink Views: Generic Views with Query Binding

**Queued:** 2026-03-14  
**Status:** Idea  

The current VIEWS section is cluttered with per-type duplicates (e.g., "Concept Graph", "Concept Card", "Note Card", "Project Card"). These should be **generic view types** — Graph View, Card View, Table View — that work across all objects by default and can optionally be scoped via saved queries or type filters.

**Problems with current approach:**
- VIEWS section is crowded with near-duplicates (one per type × view mode)
- Adding a new type multiplies the view count
- Users see "Concept Card" and "Note Card" as separate things when they're the same view with a type filter

**Proposed model:**
- **Generic views**: Graph, Card, Table (and future: Timeline, Kanban, etc.) — each is a single entry
- **Default scope**: All objects (no type filter)
- **Optional binding**: Connect a view to a saved SPARQL query for custom scoping
- **In-view filtering**: Type filter dropdown/pills within the view itself (like faceted search)
- **Saved view instances**: Users can save a configured view (e.g., "My Project Cards" = Card view + Project type filter + sort by modified) as a named entry under MY VIEWS

This connects to the VFS v2 saved query scoping work — views and VFS mounts could share the same query binding mechanism.

---

## Workspace UX Enhancements

**Queued:** 2026-03-12  
**Status:** Partially done (M003 shipped hierarchy, tags, comments, favorites)  

### Remaining Ideas

1. **Hierarchical Tag Tree** — Tags using `/` as delimiter (e.g. `garden/cultivate`, `output/newsletter`) should nest in the By Tag explorer mode. Group by prefix so `#garden` becomes a parent folder containing `cultivate`, `plant`, `question`, etc. Currently renders as a flat list. Affects: `_handle_by_tag()` in workspace.py, `tag_tree.html` template.

2. **Tag Autocomplete in Edit Form** — Tag fields (`bpkm:tags`, `schema:keywords`) render as plain text inputs in edit mode. Should have autocomplete that suggests existing tag values from the graph. Read mode already shows tag pills correctly. Affects: `forms/_field.html` template, needs new endpoint or reuse of tag-children query.

---

## MCP Server for AI Agent Access

**Queued:** 2026-03-10  
**Status:** Idea — deferred from M002  

MCP server exposing object browse/search, SPARQL query, graph traversal, and write operations to AI agents via the Model Context Protocol. Enables Claude, GPT, etc. to interact with the knowledge base directly.

**Research:** `.planning/todos/pending/2026-03-10-build-mcp-server-for-ai-agent-access-to-sempkm.md`

---

## Notion Import Wizard

**Queued:** 2026-03-12  
**Status:** Researched  

Interactive import flow for Notion workspace exports (ZIP first, API later), mirroring the Obsidian import wizard pattern. Covers databases → types, rows → objects, relations → edges, with dashboard/rollup/formula metadata preservation.

**Research:** `.planning/notion-import-research.md`

---

## Data Quality & Backend Error Fixes

**Queued:** 2026-03-13  
**Status:** Documented  

Two known backend error classes found during M003 testing: (1) malformed `xsd:dateTime` literals from Obsidian import containing text after the date portion (rdflib warnings, non-fatal), and (2) validation report store returning HTTP 415 from RDF4J (validation works but report not persisted). Neither blocks normal usage.

**Details:** `.gsd/design/KNOWN-BACKEND-ERRORS.md`

---

## VFS Mount Spec v2

**Queued:** 2026-03-13  
**Status:** Designed  

Next-generation mount capabilities: saved query scoping, composable strategy chains (multi-level folders), type filters without SPARQL, preview improvements, filename templates. Write support deferred to its own milestone.

**Design:** `.gsd/design/VFS-V2-DESIGN.md`

---

## In-App Relationship (Property) Creation

**Queued:** 2026-03-13  
**Status:** Idea  

Users can create OWL Object Properties and Datatype Properties from the RBox tab, mirroring the "+ Create Class" flow on TBox. A "+ Create Property" button on the RBox tab opens a modal with: property name, domain class (source), range class or datatype (target), description (`rdfs:comment`), and property characteristics (functional, symmetric, etc.). Stored in `urn:sempkm:user-types` graph alongside user-created classes.

**Context:** Currently only classes can be created in-app. Relationships between classes must be hand-written in model ontology files. This would let users define connections like "authored by" (Person → Research Paper) directly from the Ontology Viewer.

---

## Full CRUD for Custom Types & Relationships

**Queued:** 2026-03-13  
**Status:** Idea  

Complete lifecycle management for user-created classes and properties in `urn:sempkm:user-types`. Currently only Create exists (via the Ontology Viewer modal). Needs:

- **Edit**: Rename class/property, change description/example, update icon/color, reparent in hierarchy, add/remove/reorder SHACL properties on a class shape.
- **Delete**: Remove class and its SHACL shape (endpoint exists but no UI). Warn if instances exist. Cascade option for orphaned instances.
- **View/Manage**: Dedicated "Custom" section on the Mental Models admin page showing all user-created types and relationships with edit/delete actions — parallel to the "Installed Models" table but for the `urn:sempkm:user-types` graph.

The Mental Models page would gain three sections: Upper Ontology (gist, read-only), Installed Models (basic-pkm etc., install/remove), Custom (user types/properties, full CRUD).

---

## "Create New Object" Opens in New Tab

**Queued:** 2026-03-13  
**Status:** Bug  

Creating a new object overwrites the content of the currently active dockview tab instead of opening a fresh tab. Expected behavior: "Create New" should always open a new tab (like clicking an object in the explorer does), preserving whatever the user was looking at. Likely the create action targets the active panel's content area rather than calling `openTab()` to create a new panel.

---

## Ontology Viewer & Gist Upper Ontology

**Queued:** 2026-03-12  
**Status:** ✅ Done (M003) — TBox/RBox viewer, gist 14.0.0, class creation all shipped
