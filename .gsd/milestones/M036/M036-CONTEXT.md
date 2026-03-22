---
depends_on: [M033]
---

# M036: Business Planning Mental Models & Custom Renderers

**Gathered:** 2026-03-22
**Status:** Queued — pending auto-mode execution

## Project Description

A comprehensive library of business planning and strategic decision-making frameworks as Mental Models with custom visual renderers. Each framework is stored as typed RDF — not just a diagram but structured data an AI copilot can query, reason over, and synthesize across frameworks. The custom renderers provide the visual layouts users expect (2×2 matrices, 9-box canvases, progress dashboards, weighted tables) while the underlying data model enables cross-framework analysis impossible in traditional diagramming tools.

## Why This Milestone

SemPKM's Mental Model system has proven it can deliver instant PKM experiences for note-taking (basic-pkm), CRM, research, and Zettelkasten workflows. But business planning — the daily work of prioritization, strategy, and decision-making — has no structured support. Users doing strategic planning in SemPKM are reduced to untyped Notes.

The key differentiator: unlike Miro, Lucidchart, or Notion templates, these frameworks store data as typed RDF triples. An Eisenhower matrix item knows it's urgent AND important — it's not a sticky note on a 2D canvas. The AI copilot (M035) can query "show me all urgent-important items across all my Eisenhower matrices" or "which OKR key results are behind target" and get structured answers, not image recognition.

The renderer registry (proven in M033 with calendar/map/isometric) supports Mental Model-declared custom renderers — each framework registers its own visual layout.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install the business-planning Mental Model and immediately see new types in the object browser
- Create an Eisenhower Matrix and see items in a 2×2 quadrant view, drag items between quadrants
- Create a Business Model Canvas and fill in the 9 standard sections in a poster-style layout
- Create a SWOT Analysis with 4-quadrant visual layout
- Set OKR Objectives with Key Results showing progress bars (current vs target)
- Build a Decision Matrix with weighted criteria and see computed rankings
- Create a Porter's Five Forces analysis, Value Chain diagram, Lean Canvas, BCG Matrix, and other standard business frameworks
- See all strategic frameworks queryable via SPARQL — an AI copilot can synthesize across them
- Link framework items to existing objects (e.g., Eisenhower item → bpkm:Task, OKR → ppv:GoalOutcome)

### Entry point / environment

- Entry point: Admin > Mental Models > Install, then workspace for object creation and custom renderers
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: RDF4J triplestore

## Completion Class

- Contract complete means: all framework archives pass manifest validation, install cleanly, generate correct SHACL forms, custom renderers display correctly, seed data creates valid objects
- Integration complete means: custom renderers load via register_renderer(), cross-model edges work (Eisenhower item → Task), SPARQL queries return structured framework data
- Operational complete means: models survive Docker restart, refresh_artifacts works, custom renderers survive theme toggle

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User installs business-planning model, creates an Eisenhower Matrix, sees items in 2×2 quadrant view
- Dragging an item from "Urgent/Important" to "Not Urgent/Important" updates the RDF properties
- User creates a Business Model Canvas and fills sections in the 9-box layout
- OKR view shows objectives with progress bars computed from key result current/target values
- SPARQL query "all urgent-important items" returns structured results across multiple matrices
- Cross-model edge: Eisenhower item linked to a bpkm:Task appears in both views

## Risks and Unknowns

- **Custom renderer count** — Each framework with a unique visual layout needs its own renderer template + CSS + JS. With 10+ frameworks, this is significant frontend work. Prioritize the 5 most visually distinctive, use table/kanban fallback for the rest.
- **Drag interactions in custom renderers** — Eisenhower drag-to-reclassify and BMC card dragging need the same stopPropagation pattern used in kanban (M031) and canvas (M008) to avoid dockview interference.
- **BMC 9-box layout** — The standard Business Model Canvas poster layout is a non-trivial CSS Grid with varying column/row spans. Needs careful responsive design.
- **Computed values in Decision Matrix** — Weighted score computation (Σ weight × score) should happen server-side in the data endpoint, not client-side, for SPARQL queryability.
- **Framework library scope** — "Big library" means potentially 15-20+ frameworks. The model design should be composable (shared base types, per-framework shapes) not monolithic.

## Existing Codebase / Prior Art

- `backend/app/views/registry.py` — `register_renderer()` for custom renderer types. Proven with calendar, map, isometric in M033. Mental Models declare custom renderers via `sempkm:customRenderer` in views JSON-LD. Verified on main.
- `models/basic-pkm/` — Reference for Mental Model archive structure (manifest.yaml, ontology/, shapes/, views/, rules/, seed/). Verified 6-file pattern.
- `models/ppv/` — Reference for complex model with 11 types, review hierarchy, and cross-type relationships. OKR framework complements PPV's GoalOutcome pattern.
- `frontend/static/js/kanban.js` — Drag-drop with stopPropagation for dockview isolation. Reference for Eisenhower/BMC drag patterns. Verified on main.
- `backend/app/dashboard/registry.py` — BlockRegistry pattern for typed component registration. Reference for framework renderer registration.
- `backend/app/views/router.py` — Generic view endpoint with renderer branching (table/cards/graph/kanban/calendar/map). Custom renderers branch into this same pattern.
- M011 pattern — Pure Mental Model archives requiring zero platform code changes. The model types and shapes are the deliverable; custom renderers extend the view system.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New requirements to be created: BIZ-01 through BIZ-10+ covering each framework type, custom renderers, cross-model linking, AI queryability
- Existing pattern advanced: M011 proved pure Mental Model delivery; this extends with model-declared custom renderers

## Scope

### In Scope

**Core Frameworks (with custom renderers):**
- Eisenhower Matrix — 2×2 quadrant renderer with drag-to-reclassify
- Business Model Canvas — 9-box poster layout with inline editing
- SWOT Analysis — 2×2 quadrant renderer (variant of Eisenhower layout)
- OKR Framework — Objective + Key Results with progress bar renderer
- Decision Matrix / Weighted Scoring — weighted-score table with computed rankings

**Extended Framework Library (table/kanban/graph views):**
- Porter's Five Forces — 5 force types with competitive analysis properties
- Value Chain Analysis — primary and support activity types
- Lean Canvas — simplified BMC variant (shares renderer with BMC)
- BCG Matrix — 2×2 (market growth × market share) variant of quadrant renderer
- Ansoff Matrix — 2×2 (market × product) growth strategy
- PESTLE Analysis — 6-category environmental scan
- Balanced Scorecard — 4-perspective strategic management
- RACI Matrix — responsibility assignment type
- Stakeholder Map — power/interest 2×2 (reuses quadrant renderer)
- Risk Matrix — likelihood/impact 2×2 (reuses quadrant renderer)
- Kanban Board — already exists (M031), model provides typed columns
- Gantt Chart — timeline renderer from M034

**Model Architecture:**
- Single `business-planning` model archive (or split into `business-frameworks` + `strategy-tools` if too large)
- Shared base types (QuadrantItem, MatrixEntry, FrameworkSection) for renderer reuse
- Per-framework SHACL shapes with PropertyGroups
- ViewSpecs with custom renderer declarations
- Seed data with example frameworks filled in
- Cross-model edges: EisenhowerItem → bpkm:Task, OKR Objective → ppv:GoalOutcome, SWOT → bpkm:Project

**Custom Renderer Infrastructure:**
- Renderers registered via existing register_renderer() pattern
- Each renderer: Jinja2 template + CSS + optional JS for interactivity
- 2×2 Quadrant renderer (reused by Eisenhower, SWOT, BCG, Ansoff, Stakeholder, Risk)
- 9-box Canvas renderer (reused by BMC, Lean Canvas)
- Progress renderer (OKR)
- Weighted table renderer (Decision Matrix)
- Dark mode support via CSS variables

### Out of Scope / Non-Goals

- Real-time collaborative editing of frameworks
- Export to PowerPoint/PDF (separate feature)
- Import from existing Miro/Lucidchart boards
- AI auto-population of frameworks (M035 scope — the AI reads the data, doesn't write it in this milestone)
- Custom user-created framework types (users can create types via M004, but custom renderers require code)

## Technical Constraints

- Mental Models are .sempkm-model archives with standard 6-file structure
- Custom renderers use register_renderer() from views/registry.py
- Frontend: htmx + vanilla JS. Renderer templates are Jinja2 with htmx for interactivity.
- Drag interactions must use stopPropagation() to prevent dockview interference
- All framework data stored as typed RDF triples — not JSON blobs or SVG diagrams
- SHACL shapes drive form generation for framework data entry

## Integration Points

- **ViewSpecService / registry.py** — custom renderer registration and dispatch
- **ShapesService** — SHACL forms for framework data entry
- **M035 AI Copilot** — AI queries structured framework data via SPARQL
- **M034 Timeline** — Gantt chart renderer for project-type frameworks
- **PPV model** — OKR objectives link to ppv:GoalOutcome
- **basic-pkm model** — Eisenhower items link to bpkm:Task
- **Dashboard system (M032)** — framework visualizations embeddable as dashboard blocks

## Open Questions

- **Model packaging** — Single model or split? One `business-planning` model with all 15+ types, or split into `strategic-frameworks` (high-level: SWOT, Porter, PESTLE) and `operational-tools` (Eisenhower, OKR, Decision Matrix, RACI)? Single model is simpler to install; split allows selective installation.
- **Quadrant renderer reuse** — The 2×2 quadrant layout is used by 6+ frameworks. Should it be a generic "quadrant renderer" parameterized by axis labels, or should each framework register its own renderer variant? Generic is cleaner but needs configuration per framework.
- **Computed fields** — Decision Matrix weighted scores and OKR progress percentages should be computed how? Options: (a) SHACL-AF inference rules computing derived triples, (b) server-side computation in the renderer endpoint, (c) client-side JS. SHACL-AF is most aligned with the RDF-native philosophy but adds rule complexity.
