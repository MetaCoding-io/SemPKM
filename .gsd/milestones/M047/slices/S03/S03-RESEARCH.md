# S03 Research: TBox Dashboards & Workflows — PPV Operating System

## Summary

This slice creates the 5 PPV dashboards and 5 PPV workflows as TBox definitions (JSON files in the model archive), adds a `workflows` entrypoint to the manifest, and migrates the 5 seed.py PPV workflows to model-sourced TBox. The infrastructure is fully built (S01), the ontology/ViewSpecs are complete (S02), and the block registry has every block type needed. The work is primarily authoring JSON content files and wiring the manifest — no new Python code beyond removing seed workflows and adding minor workflow routing enhancements.

## Recommendation

**Targeted research.** The infrastructure and block types are established. The main design challenge is the dashboard-step-in-workflow UUID problem, which has a clean solution (name-based lookup). The rest is content authoring against known schemas.

---

## Implementation Landscape

### What Exists

**Dashboard JSON format** (`models/ppv/dashboards/ppv.json`): Top-level `{"dashboards": [...]}` array. Each dashboard: `{name, description, layout, blocks}`. Blocks: `{type, config, x, y, w, h}` (GridStack positions). Currently holds 1 test dashboard (markdown block from S01).

**Workflow JSON format** — needs to be created at `models/ppv/workflows/ppv.json`. Format: `{"workflows": [...]}`. Each workflow: `{name, description, steps}`. Each step: `{type, label, config}`. Step types: `view`, `dashboard`, `form`.

**tbox_loader** (`backend/app/models/tbox_loader.py`): `load_tbox_dashboards()` and `load_tbox_workflows()` — reads JSON, validates name/steps presence, returns list of dicts. No schema-level validation beyond structure.

**ModelService install** (`backend/app/services/models.py:468-510`): After seed materialization, calls tbox_loader, iterates results, calls `DashboardService.create(source_model=model_id)` / `WorkflowService.create(source_model=model_id)`. On remove: `delete_by_model(model_id)`.

**DashboardService.create()** signature: `(user_id, name, layout="single", blocks=[], description="", source_model=None)`.

**WorkflowService.create()** signature: `(user_id, name, steps=[], description="", source_model=None)`.

**Block types available** (all needed by PPV dashboards):
- `stat-card`: `{query (SPARQL), label, icon (lucide), color}` → executes SPARQL via `/api/sparql`, displays first binding value
- `chart`: `{query (SPARQL), chart_type (bar/line/pie), label}` → SPARQL results must return `?label` and `?value` bindings
- `view-embed`: `{spec_iri, renderer_type, height, emits_context, listens_to_context}` → loads ViewSpec inline
- `create-form`: `{target_class, defaults}` → renders SHACL form
- `form-group`: `{slots, edges}` → multi-slot form creation
- `object-embed`: `{object_iri, mode}` → renders object inline (but object_iri must be known at install time — problematic for GuidingPrinciples singleton)
- `markdown`: `{content}` → rendered markdown
- `heading`: `{text, level, subtitle, align}` → section heading
- `sparql-result`: `{query, label}` → SPARQL → table display
- `divider`: `{}` → `<hr>`

**Valid layouts:** `single`, `sidebar-main`, `grid-2x2`, `grid-3`, `top-bottom`, `gridstack`. All dashboards auto-migrate to `gridstack` on first render, so `gridstack` is the correct layout to declare.

**SPARQL scoping:** All queries through `/api/sparql` are scoped to `urn:sempkm:current` via `scope_to_current_graph()`. Queries can use PPV namespace prefixes (auto-injected from model prefix registry).

**Seed workflows** (`backend/app/dashboard/seed.py`): 5 workflows defined in `SEED_WORKFLOWS` list:
1. "Create & Review" (generic, empty spec_iri — model-agnostic)
2. "Weekly Review" (PPV: weekly-table → action-table → WeeklyReview form → review-graph)
3. "Monthly Review" (PPV: monthly-table → weekly-table → MonthlyReview form → goaloutcome-table)
4. "Quarterly Review" (PPV: quarterly-table → QuarterlyReview form → valuegoal-table)
5. "Yearly Review" (PPV: yearly-table → YearlyReview form → hierarchy-graph)

**PPV ViewSpec IRIs** (23 total, from S02):
- Tables: `ppv:view-pillar-table`, `ppv:view-pillargroup-table`, `ppv:view-valuegoal-table`, `ppv:view-goaloutcome-table`, `ppv:view-project-table`, `ppv:view-action-table`, `ppv:view-weekly-table`, `ppv:view-monthly-table`, `ppv:view-quarterly-table`, `ppv:view-yearly-table`, `ppv:view-pillarscore-table`, `ppv:view-action-by-context`
- Cards: `ppv:view-pillar-card`, `ppv:view-valuegoal-card`, `ppv:view-goaloutcome-card`, `ppv:view-project-card`, `ppv:view-action-card`
- Graphs: `ppv:view-pillar-graph`, `ppv:view-project-graph`, `ppv:view-review-graph`, `ppv:view-hierarchy-graph`
- Kanban: `ppv:view-action-kanban`, `ppv:view-project-kanban`

**PPV property values for SPARQL filters:**
- `ppv:status` (ActionItem): Active, Waiting, Paused, Next Up, Future 1/2/3
- `ppv:priority` (ActionItem): Immediate, Quick, Scheduled, 1st–5th Priority, Errand, Remember
- `ppv:context` (ActionItem): home, office, errands, calls, computer, anywhere
- `ppv:done` (ActionItem): DatatypeProperty (boolean/string)
- `ppv:status` (Project): Active, On Hold, Next Up, Future, Someday/Maybe, Completed

### Key Design Challenge: Dashboard References in Workflow Steps

**Problem:** The `dashboard` step type in workflows references dashboards by UUID (`config.dashboard_id`). TBox dashboards get new UUIDs at install time. A TBox workflow JSON can't hardcode UUIDs because they don't exist until the model is installed.

**Solution — Name-based resolution at install time:** The ModelService install sequence creates dashboards first, then workflows. Add a post-processing step: after creating dashboards, build a `name → UUID` map from the created dashboards. When creating workflows, resolve any `dashboard_name` references in step configs to the corresponding dashboard UUID.

**Implementation approach:**
1. In the workflow JSON, use `"dashboard_name": "Action Items"` instead of `"dashboard_id": "..."` in step configs
2. In `ModelService.install()` (or a helper), after creating TBox dashboards, collect `{name: id}` mapping from the created `DashboardData` objects
3. Before passing workflow defs to `WorkflowService.create()`, iterate steps and replace `dashboard_name` → `dashboard_id` using the mapping
4. If a referenced dashboard name isn't found, log a warning (degraded mode consistent with D380)

This approach requires ~15 lines of post-processing code in `ModelService.install()`. No changes to the workflow router or database schema needed.

**Alternative (rejected): name-based lookup in workflow router.** Would require changes to the router, DashboardService, and doesn't work for user-created workflows referencing user-created dashboards. The install-time resolution is simpler and more contained.

### object-embed Limitation for GuidingPrinciples

The `object-embed` block type requires a specific `object_iri`. GuidingPrinciples is a singleton, but the IRI depends on what the user creates. Two options:

1. **Use sparql-result instead** — query for the singleton and display its properties as a table. Simpler, works regardless of IRI.
2. **Use markdown with a prompt** — instruction text like "Create your Guiding Principles from the sidebar, then pin it here." More honest about the limitation.

**Recommendation:** Use `sparql-result` with a SPARQL query that selects the GuidingPrinciples instance. If none exists, it shows "No results" — which is informative. Future enhancement could add a "dynamic object-embed" block type that resolves by class, but that's out of scope.

### Seed.py Migration Strategy

The 5 PPV workflows in `SEED_WORKFLOWS` need to move from seed.py to the model archive. The "Create & Review" workflow is generic (empty IRIs, no PPV references) and should stay in seed.py. The "Getting Started" dashboard is also generic and stays.

After migration:
- `seed.py` keeps: "Getting Started" dashboard + "Create & Review" workflow
- PPV model ships: 5 dashboards + 5 workflows via TBox

**Conflict prevention:** When PPV is installed, the model-sourced workflows have `source_model="ppv"`. The seed workflows have `source_model=None`. Both will exist simultaneously for existing users. New installs get both — the seed runs first (main.py startup), then model install creates TBox surfaces. Existing users who already have the seed workflows keep them. The TBox workflows are richer (dashboard steps, more steps) so users will naturally prefer them. No need to delete seed workflows — they're harmless.

### Templates Entrypoint — Defer

The M047 CONTEXT mentions a `templates` entrypoint for the Life Maintenance Checklist. The manifest schema doesn't have a `templates` field yet, and there's no template service in the codebase. This is out of scope for S03 — the context itself marks it as aspirational. The Life Maintenance Checklist can be represented as a workflow with a `form` step that creates an ActionItem (the checklist concept maps to creating action items with default properties).

---

## File Inventory

### Files to Create

| File | Purpose |
|------|---------|
| `models/ppv/workflows/ppv.json` | 5 workflow definitions (TBox): Daily Check-in, Weekly Review, Monthly Review, Quarterly Review, Yearly Review |

### Files to Modify

| File | Change |
|------|--------|
| `models/ppv/dashboards/ppv.json` | Replace test dashboard with 5 real dashboards: Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub |
| `models/ppv/manifest.yaml` | Add `workflows: "workflows/ppv.json"` entrypoint |
| `backend/app/services/models.py` | Add dashboard name→UUID resolution for workflow `dashboard_name` references during install |
| `backend/app/dashboard/seed.py` | Remove 4 PPV-specific workflows from SEED_WORKFLOWS (keep "Create & Review") |

### Files to Verify (No Changes Expected)

| File | Why |
|------|-----|
| `backend/app/models/tbox_loader.py` | Already handles workflows JSON loading |
| `backend/app/dashboard/registry.py` | All needed block types already registered |
| `backend/app/workflow/router.py` | `dashboard` step type already works with `dashboard_id` |

---

## SPARQL Query Inventory

Stat-card and chart blocks need SPARQL queries. These execute via `/api/sparql` which auto-injects prefixes and scopes to `urn:sempkm:current`. Prefix `ppv:` is registered via the model prefix registry.

### Stat-Card Queries

**Active Actions Count:**
```sparql
SELECT (COUNT(?s) AS ?count) WHERE { ?s a ppv:ActionItem ; ppv:status "Active" }
```

**Immediate Priority Count:**
```sparql
SELECT (COUNT(?s) AS ?count) WHERE { ?s a ppv:ActionItem ; ppv:status "Active" ; ppv:priority "Immediate" }
```

**Active Projects Count:**
```sparql
SELECT (COUNT(?s) AS ?count) WHERE { ?s a ppv:Project ; ppv:status "Active" }
```

**Active Value Goals Count:**
```sparql
SELECT (COUNT(?s) AS ?count) WHERE { ?s a ppv:ValueGoal ; ppv:status "Underway" }
```

### Chart Queries

**Pillar Score Trend** (line chart — requires `?label` and `?value` bindings):
```sparql
SELECT ?label ?value WHERE {
  ?s a ppv:PillarScore ; ppv:score ?value ; ppv:pillar ?p .
  ?p dcterms:title ?label .
} ORDER BY ?label
```
Note: Chart.js doesn't natively support multi-series from flat SPARQL results. A single-pillar view or grouped bar chart is more practical. The chart block maps `?label` → x-axis labels and `?value` → y-axis values.

### SPARQL Result Queries

**Orphan Projects (no goal link):**
```sparql
SELECT ?project ?title WHERE {
  ?project a ppv:Project ; dcterms:title ?title .
  FILTER NOT EXISTS { ?project ppv:goalOutcome ?go }
}
```

**Value Goals without Active Outcomes:**
```sparql
SELECT ?goal ?title WHERE {
  ?goal a ppv:ValueGoal ; dcterms:title ?title .
  FILTER NOT EXISTS {
    ?outcome a ppv:GoalOutcome ; ppv:valueGoal ?goal ; ppv:status "Active"
  }
}
```

---

## Task Decomposition Guidance

### T01: PPV Dashboards JSON (models/ppv/dashboards/ppv.json)

Replace the test dashboard with 5 real dashboards using gridstack layout and the block types documented above. Each dashboard has heading blocks, stat-cards with SPARQL queries, and view-embed blocks referencing PPV ViewSpec IRIs.

**Key constraint:** All positions must be valid GridStack (x: 0-11, y: ≥0, w: 1-12, h: ≥1, x+w ≤ 12). Stat-cards are typically 3w×2h, view-embeds are 6w×4h or 12w×6h, headings are 12w×1h.

**Verification:** `python3 -c "import json; d=json.load(open('models/ppv/dashboards/ppv.json')); print(len(d['dashboards']), 'dashboards')"` → 5. Every block type is in `VALID_BLOCK_TYPES`. Every `spec_iri` in view-embed blocks matches a ViewSpec from the views file. Every SPARQL query in stat-cards/charts is syntactically valid.

### T02: PPV Workflows JSON + Manifest Update + dashboard_name Resolution

Create `models/ppv/workflows/ppv.json` with 5 workflows. Add `workflows` entrypoint to manifest. Add ~15 lines of name→UUID resolution code in `ModelService.install()`.

**Workflow steps use three patterns:**
1. `{type: "view", config: {spec_iri, renderer_type}}` — loads a ViewSpec
2. `{type: "dashboard", config: {dashboard_name: "..."}}` — loads a TBox dashboard (resolved to UUID at install time)
3. `{type: "form", config: {target_class}}` — renders SHACL creation form

**Key constraint for dashboard_name resolution:** The install sequence in `ModelService.install()` already creates dashboards before workflows (lines 468-510). After the dashboard creation loop, collect `{name: dashboard_data.id}` into a dict. Before creating each workflow, iterate its steps and replace `dashboard_name` → `dashboard_id`. This is the natural seam — no reordering needed.

**Verification:** JSON validation. Manifest YAML validation. Unit test: mock ModelService install with v2 manifest → verify workflows are created with resolved dashboard_id (not dashboard_name) in step configs.

### T03: Seed.py Migration + Tests

Remove the 4 PPV workflows from `SEED_WORKFLOWS` in seed.py. Keep "Create & Review" (generic). Add/update tests covering: (1) TBox dashboards/workflows JSON loads correctly, (2) seed.py only creates 1 workflow (down from 5), (3) dashboard_name resolution works in ModelService install integration test.

**Verification:** `cd backend && .venv/bin/python -m pytest tests/test_tbox_loader.py tests/test_tbox_lifecycle.py tests/test_data_widgets.py -v` — all pass with zero regressions. Seed.py only has 1 workflow in SEED_WORKFLOWS.

---

## Constraints & Risks

1. **GridStack position collisions:** If two blocks overlap (same x,y range), GridStack auto-adjusts at runtime, but the definition looks messy. The planner should lay out blocks carefully in a 12-column grid.

2. **SPARQL prefix availability:** Stat-card queries use `ppv:` prefix. This is auto-injected by the SPARQL router from the model prefix registry, which is populated during model install. Queries will work when the model is installed.

3. **Chart data shape:** The chart block expects exactly `?label` and `?value` bindings. Multi-series charts (e.g., pillar scores over time with one line per pillar) aren't supported by the current chart block implementation. Use single-series or pivot the query to produce label/value pairs.

4. **object-embed for GuidingPrinciples:** Cannot use because the IRI isn't known at manifest authoring time. Use `sparql-result` with a query that selects the GuidingPrinciples properties, or `markdown` with instructional text.

5. **Dashboard names must be unique within the model:** The name→UUID resolution depends on unique names. All 5 proposed dashboards have distinct names.
