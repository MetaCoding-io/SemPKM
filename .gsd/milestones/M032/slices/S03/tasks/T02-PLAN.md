---
estimated_steps: 4
estimated_files: 1
skills_used: []
---

# T02: Update user guide chapter 28 with new block types and GridStack builder

**Slice:** S03 — E2E Tests and User Guide
**Milestone:** M032

## Description

Update the existing user guide chapter 28 ("Dashboards and Workflows") to document all 10 dashboard block types, the GridStack drag-drop builder, and the new form-group multi-object creation workflow. The chapter currently documents 6 block types and describes the old CSS Grid layout template system. Four new block types (stat-card, chart, heading, form-group), improved markdown (full marked.js rendering), and improved sparql-result (now executes queries live) need documentation.

Since chapter 28 already exists in all three guide index files (`docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`), only the content file needs updating — no index changes required.

## Steps

1. **Rewrite the Block Types table** in `docs/guide/28-dashboards-and-workflows.md`.
   Replace the current 6-type table with a 10-type table covering all registered block types from `BLOCK_REGISTRY`:
   | Block Type | Description |
   |------------|-------------|
   | **view-embed** | (keep existing description) |
   | **markdown** | Update: "Renders full Markdown content using marked.js — headings, lists, code blocks, links, and inline formatting. Content is sanitized via DOMPurify." |
   | **object-embed** | (keep existing description) |
   | **create-form** | (keep existing description) |
   | **sparql-result** | Update: "Executes a SPARQL SELECT query and displays results in an interactive table. The query runs live against your knowledge base on load." |
   | **divider** | (keep existing description) |
   | **stat-card** | NEW: "Displays a single numeric value from a SPARQL query — ideal for counts, totals, and KPIs. Configure a SPARQL query that returns one value, a label, a Lucide icon, and an optional accent color." |
   | **chart** | NEW: "Renders a Chart.js visualization (bar, line, or pie chart) from SPARQL query results. The query must return `?label` and `?value` columns. Chart.js is loaded on demand only when a chart block is present." |
   | **heading** | NEW: "Displays a configurable title and optional subtitle at heading levels h1–h4 with text alignment. Use for section dividers and dashboard headers." |
   | **form-group** | NEW: "Creates multiple linked objects in one submission. Contains two or more SHACL sub-forms (slots), with edges automatically created between the resulting objects." |

2. **Replace the Layout Templates section with GridStack builder description.**
   The old section describes 5 CSS Grid templates (single, sidebar-main, grid-2x2, grid-3, top-bottom). Replace with:
   - Describe the GridStack drag-drop layout: blocks are placed freely on a 12-column responsive grid
   - Blocks can be dragged to reposition, resized by dragging corners/edges
   - Each block type has default dimensions that can be adjusted
   - Note that legacy CSS Grid layouts (created before this update) continue to work
   Update the "Creating a Dashboard" section to describe: (1) click + in DASHBOARDS section, (2) name the dashboard, (3) drag blocks from the palette or click to add, (4) configure each block's type-specific settings, (5) save

3. **Add a "Data Widgets" subsection.**
   After the Block Types table, add a subsection explaining how to configure data-driven blocks:
   - **Stat Card:** Write a SPARQL query returning one row with one value (typically a COUNT). Set a descriptive label, pick a Lucide icon name, optionally set an accent color. Example query: `SELECT (COUNT(*) AS ?count) WHERE { ?s a bpkm:Project }`
   - **Chart:** Write a SPARQL query returning `?label` and `?value` columns. Choose bar, line, or pie chart type. Example: `SELECT ?label (COUNT(*) AS ?value) WHERE { ?s a ?type . BIND(STRAFTER(STR(?type), "#") AS ?label) } GROUP BY ?type`
   - **SPARQL Result Table:** Write any SELECT query — results display in a sortable table with column headers from query variables

4. **Add a "Form Groups" subsection.**
   After Data Widgets, add a subsection explaining multi-object creation:
   - Concept: a form group contains multiple "slots," each rendering a SHACL creation form for a target class
   - Edges: configure edges between slots (source slot → target slot + predicate IRI) to automatically create relationships
   - Submission: all objects are created in a single batch via the Command API with slot-based IRI resolution
   - Example: a "Note + Task" form group with slots for Note and Task, and an edge linking the Note to the Task via a "relatedTo" predicate
   - Update the Dashboard vs. Workflow comparison table to reflect 10 block types instead of 6

## Must-Haves

- [ ] Block Types table lists all 10 types with accurate descriptions
- [ ] Layout section describes GridStack drag-drop (not CSS Grid templates)
- [ ] Data Widgets subsection with stat-card, chart, and sparql-result configuration examples
- [ ] Form Groups subsection explaining slots, edges, and batch creation
- [ ] Markdown and sparql-result descriptions updated to reflect improvements
- [ ] Navigation links preserved (Previous/Next chapter links at bottom)

## Verification

- `test -f docs/guide/28-dashboards-and-workflows.md`
- `grep -q 'stat-card' docs/guide/28-dashboards-and-workflows.md`
- `grep -q 'form-group' docs/guide/28-dashboards-and-workflows.md`
- `grep -q 'chart' docs/guide/28-dashboards-and-workflows.md`
- `grep -q 'heading' docs/guide/28-dashboards-and-workflows.md`
- `grep -q 'GridStack' docs/guide/28-dashboards-and-workflows.md`
- `grep -c '^|' docs/guide/28-dashboards-and-workflows.md` returns ≥ 12 (10-row block table + headers)

## Inputs

- `docs/guide/28-dashboards-and-workflows.md` — existing chapter to update (210 lines)
- `backend/app/dashboard/registry.py` — all 10 block types and their config schemas (reference)

## Expected Output

- `docs/guide/28-dashboards-and-workflows.md` — updated chapter with all 10 block types, GridStack builder, data widgets, and form groups
