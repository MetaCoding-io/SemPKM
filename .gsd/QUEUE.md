# GSD Queue

Append-only log of queued future milestones and ideas.

---

## Workspace UX Enhancements

**Queued:** 2026-03-12  
**Status:** Idea collection  

### Ideas

1. **Object Hierarchy via `dcterms:isPartOf`** — Let users organize objects in the explorer by parent/child relationships, not just by type. Objects would be nestable (e.g., a Project containing Action Items). Explore whether this connects to the VFS spec or is a parallel navigation axis.

2. **Tag Explorer** — Dedicated view/panel for browsing and navigating by `schema:keywords` tags. Show tag counts, click to filter, possibly tag hierarchy.

3. **Object Comments via `rdfs:comment`** — Users can add comments/annotations to any object. Threaded or flat discussion on objects.

4. **Favorites & Favorites View** — Users can star/favorite objects. Dedicated favorites view for quick access to frequently used items.

5. **Hierarchical Tag Tree** — Tags using `/` as delimiter (e.g. `garden/cultivate`, `output/newsletter`) should nest in the By Tag explorer mode. Group by prefix so `#garden` becomes a parent folder containing `cultivate`, `plant`, `question`, etc. Currently renders as a flat list. Affects: `_handle_by_tag()` in workspace.py, `tag_tree.html` template.

6. **Tag Autocomplete in Edit Form** — Tag fields (`bpkm:tags`, `schema:keywords`) render as plain text inputs in edit mode. Should have autocomplete that suggests existing tag values from the graph. Read mode already shows tag pills correctly. Affects: `forms/_field.html` template, needs new endpoint or reuse of tag-children query.

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

## VFS Mount Spec v2

**Queued:** 2026-03-13  
**Status:** Designed  

Next-generation mount capabilities: saved query scoping, composable strategy chains (multi-level folders), type filters without SPARQL, preview improvements, filename templates. Write support deferred to its own milestone.

**Design:** `.gsd/design/VFS-V2-DESIGN.md`

---

## Ontology Viewer & Gist Upper Ontology

**Queued:** 2026-03-12  
**Status:** Researched  

Integrated ontology visualization with TBox/ABox/RBox separation. Three purpose-built views: TBox Explorer (class hierarchy across mental models), ABox Browser (instances by type), RBox Legend (property reference). Gist 14.0.0 as upper ontology foundation, with mental model classes aligned to gist hierarchy.

**Research:** `.planning/ontology-viewer-research.md`
