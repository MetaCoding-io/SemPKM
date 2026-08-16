# repolens → SemPKM

*Research for turning repolens from a standalone page into a Mental Model.*

## The finding

Almost all of it already exists, and the parts that exist are more general than
what we built. repolens is a single-purpose reader over a fixed JSON file;
SemPKM is a general reader over RDF with the same interaction model — an
explorer of nodes, a relationship browser, per-type views, custom renderers and
custom graph layouts, all declared rather than coded.

The honest summary: **we rebuilt the browser, badly, for one dataset.** What we
gained that is worth keeping is not the UI. It is the extraction pipeline, the
vocabulary it implies, and two or three drawing behaviours SemPKM's graph view
does not have.

## Feature by feature

| repolens | SemPKM equivalent | Verdict |
|---|---|---|
| Parts panel — filtered, grouped node list | Explorer sidebar, configured by `ExplorerConfigSpec` (`group_by: type\|tag`, `sort_by`, `sort_order`), stored per user in SQLite with built-in presets | **Exists, more general.** Ours groups by one hardcoded field. |
| Connections panel — edges grouped by source | First-class edges (`sempkm:Edge` via `edge.create`), plus the relationship browser (ch. 6) and explorer sections | **Exists, more general.** A SemPKM edge is a resource with its own IRI and annotations; ours is a JSON object. |
| Collapsible rail panels | Explorer sidebar sections with expand/collapse chevrons and drag-to-reorder | **Exists.** |
| Node inspector — three tabs of prose and metrics | Object view: markdown body plus the SHACL-derived property table, flipped by the same card-flip we documented in CLAUDE.md | **Exists.** |
| Findings list ranked by severity | A `ViewSpec` with `rendererType: table` and `sortDefault`, or the existing validation report UI | **Is a ViewSpec.** |
| Decisions list + fuzzy search | A `ViewSpec` table plus keyword search (FTS, ch. 22) | **Is a ViewSpec.** |
| A topbar number that opens the list behind it | Dashboards (ch. 28) — saved views, counts, embeds | **Exists.** |
| Link picker over parts, files and symbols | Reference properties with `sh:class`: search-as-you-type over every instance of the target type, writing a real edge | **Exists, more general.** Ours searched three hardcoded kinds. |
| `links.yml` + `repolens serve` to persist an edit | Every mutation is an event; `POST /api/commands` → `event.commit` → immutable named graph | **Strictly better.** Ours has no history, no actor, no undo. |
| Layout registry (`survey`, `stack`, `lowy`, `rings`) | Graph view layouts: `fcose`, `dagre`, `concentric`, **`isometric`** — plus `get_model_layouts()`, which reads `sempkm:layoutAlgorithm` / `layoutName` / `layoutConfig` from an installed model's views graph | **Exists, and is already pluggable per model.** |
| Custom renderers | `RENDERER_REGISTRY` with `register_renderer()`; models declare `sempkm:customRenderer` with a template path. Eight ship: table, card, graph, kanban, quadrant, bmc, okr, decision-matrix | **Exists, and is already pluggable per model.** |
| Colour by group | `type_colors`, plus per-type `icon`/`color` in the model manifest, for tree, tab and graph separately | **Exists, more general.** |
| Drill: system → part → file | Spatial canvas: drag in a node, expand 1-hop neighbourhoods, arrange by hand, save named sessions | **Exists differently.** Theirs is freeform and saved; ours is a fixed three-level zoom. |
| `.repolens.yml` | Model manifest + ontology + shapes + views | **Exists.** |
| `facts.json` / `model.json` | A named graph | **Replaced.** |

## What genuinely has no equivalent

Five things, in descending order of whether they matter:

1. **Height encodes a measure.** Boxes whose elevation is lines of code or file
   count. SemPKM's graph nodes have no size-by-property channel.
2. **True axonometric drawing.** SemPKM's "Isometric 2.5D" is a CSS 3D
   transform applied to a flat cytoscape graph. Ours projects real boxes with
   a painter's-algorithm depth sort, so occlusion is correct and the pitch dial
   goes all the way to a plan view.
3. **Pitch and turn dials.** No equivalent; the isometric layout is one fixed
   angle.
4. **Edge bundling with thickness by count**, and hovering a bundle to list
   what shares the route.
5. **Packets animating along edges.** Conceded as no great loss.

Items 1–4 are all properties of *one renderer*. That is the shape of the work:
a `repolens` custom renderer registered by the model, not a new application.

## What the data model has to carry

Everything in `facts.json` and `model.json` that is not a drawing instruction.
This is the input to the ontology:

**Structural** — `Repository`, `Part` (a node set member), `File`, `Symbol`
(function, class, method), and the containment between them.

**Relational** — `imports` (file→file, part→part), `calls` (symbol→symbol),
`dataFlow` (the authored edges, carrying a flow layer and a payload example).

**Measured** — lines, file counts, out-degree, call-site hits with path and
line, route counts, test counts. Every one of these is a measurement with a
provenance, which is the thing to get right in the vocabulary.

**Judgemental** — `Finding` with a severity, `Check` with a pass/fail and an
expected value, `Claim` (an authored number that a build compares against the
tree). These are the three that no code-analysis ontology in the wild models
well, because they are about the *assessment* of code rather than the code.

**Conventions (gsd)** — `Decision` and `Rule`, with scope, rationale and the
milestone that produced them, and the link from a decision to the part it is
about. This is the plugin boundary: nothing here is about code, and a
repository without gsd should not load any of it.

**Provenance** — the three-way distinction the whole tool is built on:
`measured` (read from the tree), `authored` (a person said so), `computed`
(re-derived by a failing check). This maps onto PROV-O rather than needing new
terms, and it is the single most valuable thing repolens has to contribute,
because it survives the move to RDF unchanged.

## Consequences for what to build

- **The ontology (task 2)** covers the four groups above, split into a core
  module and a `gsd` module.
- **The Mental Model (task 3)** is mostly declarative: ontology, shapes, view
  specs for the lists we built, `sempkm:layoutAlgorithm` entries for the four
  layouts, and one `sempkm:customRenderer` for the axonometric drawing. The
  explorer, the link picker, the edit history and the search all come free.
- **The exporter (task 4)** is the existing pipeline with a different `emit`
  stage: the same stages produce the same facts, and a serialiser writes
  Turtle instead of JSON.
- **The existing page** stays useful as the zero-install view — point it at a
  repo, get a file. It stops being the place where editing happens.

## Where this got to

Built and verified:

- `models/repolens` and `models/repolens-gsd` — ontology, SHACL shapes, and
  sixteen view specs between them, plus four `sempkm:LayoutAlgorithm` entries.
  Both load through SemPKM's own `load_archive()`, remote-context check
  included.
- `tools/repolens/rdf/` and the `graph` stage — 35,871 triples from this
  repository, 128 from a two-file synthetic one with no `.gsd`.
- `tools/repolens/verify_graph.py` — every predicate emitted is declared in the
  ontology, and all sixteen views return rows against the real graph.

Not done, and honestly so:

- **The model has never been installed into a running SemPKM.** There is no
  Docker daemon in this environment, so the archives were validated with the
  loader rather than by starting the stack. Restarting the API is the next
  step, and the first thing likely to need a fix.
- **No custom renderer.** The four layouts are declared as data; the
  axonometric renderer — height as a measure, real occlusion, pitch and turn —
  is not written. Declaring a `sempkm:customRenderer` pointing at a template
  that does not exist would have made the model look finished and load broken,
  so it was left out.
- **Nothing imports the graph automatically.** The `.ttl` goes through the
  normal RDF import screen today.
