# M047 Research: PPV Model v2 — Versioned Manifests, TBox Dashboards/Workflows & Review System

## Executive Summary

This milestone extends the Mental Model manifest format to carry operational surfaces (dashboards, workflows, templates) as TBox definitions, then applies it to the PPV model with August Bradley's complete review system. The codebase is well-structured for this — the dashboard/workflow services use clean CRUD patterns, the model installer pipeline is transactional, and the block registry is extensible. The primary risk is manifest v2 backward compatibility and the install/uninstall lifecycle for model-sourced operational surfaces.

## Codebase Findings

### Model Installer Pipeline

**Location:** `backend/app/services/models.py` → `ModelService.install()`

The install pipeline is a well-structured 12-step sequence:
1. Parse manifest (`manifest.py` → `ManifestSchema` Pydantic model)
2. Check duplicates (triplestore ASK)
3. Load archive (`loader.py` → `ModelArchive` dataclass with rdflib Graphs)
4. Validate archive (`validator.py` → IRI namespacing + cross-file ref integrity)
5-9. Write named graphs in RDF4J transaction (ontology, shapes, views, rules, registry)
10. Materialize seed data via EventStore (outside transaction — degraded failure mode)
11. Register model prefixes
12. Return result

**Key constraint:** The manifest schema (`ManifestSchema`) is a Pydantic model with strict validation. Adding new entrypoint fields requires extending `ManifestEntrypoints` with optional fields that default to `None`. v1 manifests omit these fields → they stay `None` → loader skips them. This is the natural backward-compat path.

**`load_archive()`** loads each entrypoint into an rdflib Graph. New entrypoints (dashboards, workflows, templates) are NOT RDF — they're JSON specifications for the dashboard/workflow services. The loader needs a parallel path that loads these as raw JSON dicts instead of Graph objects.

### Manifest Schema (v1)

**Location:** `backend/app/models/manifest.py`

```python
class ManifestEntrypoints(BaseModel):
    ontology: str = "ontology/{modelId}.jsonld"
    shapes: str = "shapes/{modelId}.jsonld"
    views: str = "views/{modelId}.jsonld"
    seed: str | None = "seed/{modelId}.jsonld"
    rules: str | None = None
```

No `manifest_version` field exists. Adding it as an optional field with default `"1.0"` (inferred when absent) is the clean approach. The presence/absence of `manifest_version` distinguishes v1 from v2.

### Dashboard/Workflow Storage

**Location:** `backend/app/dashboard/models.py`, `backend/app/workflow/models.py`

Both use SQLite tables with JSON blob columns:
- `DashboardSpec`: id (UUID), user_id (FK), name, description, layout, blocks_json, timestamps
- `WorkflowSpec`: id (UUID), user_id (FK), name, description, steps_json, timestamps

**Critical finding:** Neither table has a `source_model` column. Adding this column is required for the TBox lifecycle:
- `source_model = NULL` → user-created (never touched by install/uninstall)
- `source_model = "ppv"` → model-sourced (created on install, removed on uninstall, replaced on refresh)

This requires an Alembic migration. The migration system is working (`backend/migrations/versions/` has 24 migrations through `024_add_security_audit_log.py`).

### Dashboard Block Types

**Location:** `backend/app/dashboard/registry.py`

10 block types registered in `BLOCK_REGISTRY`:
- **Data:** `view-embed`, `create-form`, `object-embed`, `sparql-result`, `stat-card`, `chart`, `form-group`
- **Content:** `markdown`, `heading`
- **Layout:** `divider`

All block types needed for the PPV dashboards already exist:
- `stat-card`: SPARQL COUNT query → single number display (with icon, label, color)
- `chart`: SPARQL query → Chart.js visualization (bar, line, pie)
- `view-embed`: embeds an existing ViewSpec (table, card, graph, kanban)
- `create-form`: SHACL form for a target class
- `form-group`: multi-slot form creation (for pillar scoring)
- `object-embed`: renders an object inline (for Guiding Principles)
- `markdown`: rendered markdown content
- `heading`: section headings with subtitles

The stat-card renders via htmx load → `data-sparql-query` attribute → client-side JS execution. Charts use Chart.js CDN lazy-load. Both patterns are established and working.

### Workflow Step Types

**Location:** `backend/app/workflow/models.py`, `backend/app/workflow/router.py`

Three step types: `view`, `dashboard`, `form`
- `view`: loads a ViewSpec via htmx
- `dashboard`: loads a dashboard by UUID via htmx
- `form`: renders SHACL form for a target class

The `dashboard` step type is key — workflows can embed dashboards as steps, enabling the "guided review" pattern where each step of a weekly review is a purpose-built dashboard.

### Seed Data Flow

**Location:** `backend/app/dashboard/seed.py`, `backend/app/main.py:479`

Current flow: On startup, if setup is complete, `seed_sample_data()` runs for the first user. It creates a "Getting Started" dashboard and 5 workflows (Create & Review, Weekly/Monthly/Quarterly/Yearly Review). Seeding is idempotent — per-name checks prevent duplicates.

**The 5 seed workflows are PPV-specific** (they reference `ppv:` namespace IRIs). These are exactly what should migrate from seed.py to the model's TBox manifest. The "Getting Started" dashboard is model-agnostic and should stay in seed.py.

### PPV Ontology (Current State)

**Location:** `models/ppv/` — 406 lines ontology, 1059 lines shapes, 207 lines views

**10 classes:** PillarGroup, Pillar, ValueGoal, GoalOutcome, Project, ActionItem, WeeklyReview, MonthlyReview, QuarterlyReview, YearlyReview

**~40 properties** covering status, priority, dates, hierarchy links, review fields (cycle, focusObjective, gratitude, learnedThisMonth)

**Missing from ontology (needed for M047):**
- `PillarScore` class — core weekly review mechanic (score + reflection per pillar per week)
- `GuidingPrinciples` class — singleton values anchor
- Enriched review properties (wins, challenges, supportingPriorities, biggestWins, etc.)
- New ViewSpecs: pillar score table, action kanban, project kanban, action by context

**19 existing ViewSpecs** covering table/card/graph renderers for all 10 types.

### View Renderers Available

**Location:** `backend/app/views/registry.py`

Registered renderers: `table`, `card`, `graph`, `kanban`, `calendar`, `timeline`, `map`, `decision-matrix`, `bmc`, `okr`, `quadrant`

Kanban is available and working — detected automatically via SHACL `sh:in` constraints on status-like fields. ActionItem already has `ppv:status` with `sh:in` values, so `kanban` should work out of the box for actions and projects.

### Archive Validation

**Location:** `backend/app/models/validator.py`

Validates IRI namespacing and cross-file references (shapes→ontology, views→ontology, seed→ontology). New entrypoints (dashboards.jsonld, workflows.jsonld, templates.jsonld) need their own validation — checking that referenced ViewSpec IRIs exist in the views file, that target classes exist in the ontology, etc.

### Refresh/Update Lifecycle

**Location:** `ModelService.refresh_artifacts()`

Exists and clears+reloads the 4 artifact graphs (ontology, shapes, views, rules) in a transaction. Seed and registry are untouched. This method needs extension to also refresh TBox dashboards/workflows — clear model-sourced rows from SQLite, recreate from manifest.

## Architecture Decisions

### D1: Dashboard/Workflow JSON Format (Not RDF)

The context document proposes using JSON format that maps directly to `DashboardService.create()` and `WorkflowService.create()` parameter shapes. This is correct — dashboards and workflows are UI constructs stored in SQLite, not RDF concepts. Using RDF here would create an impedance mismatch (serialize to RDF in manifest → parse to JSON → store in SQLite).

The format should be a JSON file with arrays of dashboard/workflow definitions, each containing the same fields as the service `create()` methods:
```json
{
  "dashboards": [
    { "name": "...", "layout": "gridstack", "description": "...", "blocks": [...] }
  ],
  "workflows": [
    { "name": "...", "description": "...", "steps": [...] }
  ]
}
```

### D2: source_model Column + Alembic Migration

Add `source_model: str | None` to both `DashboardSpec` and `WorkflowSpec`. Nullable, default NULL. This is a simple ALTER TABLE ADD COLUMN migration — SQLite supports this cleanly. The column enables:
- Install: create with `source_model = model_id`
- Uninstall: `DELETE WHERE source_model = model_id`
- Refresh: delete model-sourced + recreate from manifest
- User customization: user edits a model dashboard → set `source_model = NULL` (detach from model)

### D3: manifest_version Field

Add `manifest_version: str | None` to `ManifestSchema` with default None. When None, treat as v1. When "2.0", process new entrypoints. This is the minimum-change approach for backward compatibility.

### D4: Templates as a Separate Entrypoint

The context document proposes `templates/ppv.jsonld` for task templates (Life Maintenance Checklist). There is NO existing template infrastructure in the codebase — no `TemplateSpec` model, no service, no UI. Building this from scratch adds significant scope.

**Recommendation:** Defer templates to a follow-up milestone. The Life Maintenance Checklist can be approximated as a workflow step with a `create-form` step pre-filled with defaults. The core PPV value is in dashboards and workflows, not templates.

## Risk Analysis

### High Risk: Manifest v2 Backward Compatibility

The manifest schema is validated via Pydantic, which rejects unknown fields by default. Adding new fields must use `Optional` with defaults, and the `ManifestEntrypoints` model must not break when v1 manifests lack the new fields. All 6 existing models must continue installing unmodified.

**Mitigation:** Write the schema changes first with comprehensive unit tests covering all 6 existing manifests.

### Medium Risk: Install/Uninstall Lifecycle for SQLite-stored TBox

The model installer currently writes to RDF4J triplestore only. Dashboard/workflow TBox must write to SQLite via service methods. This crosses a storage boundary — triplestore writes are transactional (RDF4J transactions), SQLite writes are separate transactions. If the triplestore commit succeeds but SQLite creation fails (or vice versa), the system is in an inconsistent state.

**Mitigation:** Write SQLite TBox after triplestore transaction commits (same pattern as seed data — degraded failure mode, not full failure). Log warnings for partial failures.

### Medium Risk: Dashboard SPARQL Queries Must Be Model-Portable

Dashboard stat-cards and charts contain embedded SPARQL queries. These queries reference model-specific IRIs (e.g., `ppv:ActionItem`, `ppv:status`). The queries must be correct for the PPV ontology — tested against actual seed data.

**Mitigation:** Test each dashboard SPARQL query against the PPV triplestore data before committing. E2E tests that install the model and verify dashboard content renders.

### Low Risk: Ontology Expansion

Adding PillarScore and GuidingPrinciples classes follows established patterns. The PPV ontology already has 10 classes and ~40 properties. The shapes, views, and rules extensions are mechanical. Risk is low because the ontology authoring pattern is proven across 6 models.

## Existing Patterns to Reuse

1. **ManifestEntrypoints optional fields:** `seed` and `rules` are already `str | None = None`. New entrypoints follow the same pattern.
2. **Seed data pattern:** `seed_sample_data()` in `seed.py` demonstrates per-name idempotent creation. TBox creation follows the same pattern but triggered by model install instead of startup.
3. **Block rendering:** All 10 block types are implemented in `dashboard/router.py:render_block()`. No new block types needed.
4. **Kanban detection:** `_detect_status_field()` in `ViewSpecService` auto-detects `sh:in` enum fields. PPV's `ppv:status` already has `sh:in` constraints — kanban should just work.
5. **Alembic migration pattern:** 24 existing migrations demonstrate the standard pattern.
6. **Model detail admin page:** `ModelService.get_model_detail()` queries all model artifacts. Can be extended to show TBox dashboard/workflow counts.

## Boundary Contracts

### Manifest ↔ Installer
- `ManifestSchema` (Pydantic) is the contract between on-disk YAML and the installer
- New entrypoints are optional strings defaulting to None
- `ModelArchive` dataclass needs new fields for dashboard/workflow JSON dicts

### Installer ↔ Dashboard/Workflow Services
- Installer calls `DashboardService.create()` and `WorkflowService.create()` with `source_model` parameter
- New method: `DashboardService.delete_by_model(model_id)` for uninstall
- New method: `WorkflowService.delete_by_model(model_id)` for uninstall

### Dashboard JSON ↔ Block Registry
- Dashboard blocks in the manifest must use valid block types from `BLOCK_REGISTRY`
- SPARQL queries in stat-card/chart blocks are model-specific and not validated at manifest parse time

## Slice Ordering Recommendation

**S01: Manifest v2 Schema + source_model Migration** `risk:high`
- This is the foundational infrastructure. Everything else depends on it.
- Prove backward compat first: all 6 existing models must install/uninstall unchanged.
- Alembic migration adds `source_model` column to both tables.
- ManifestSchema v2 with optional new entrypoints.
- ModelArchive extended with dashboard/workflow JSON loading.
- Install/uninstall lifecycle wired: create/delete model-sourced dashboards+workflows.

**S02: PPV Ontology Expansion** `risk:medium` `depends:[S01]`
- PillarScore and GuidingPrinciples classes.
- Enriched review properties.
- New SHACL shapes for new types.
- New ViewSpecs (pillar scores table, action kanban, project kanban).
- SHACL-AF rules for PillarScore denormalization.
- This can be validated independently by installing the updated PPV model.

**S03: TBox Dashboards & Workflows** `risk:medium` `depends:[S01, S02]`
- Create dashboards/ppv.jsonld (5 dashboards) and workflows/ppv.jsonld (5 workflows).
- Update PPV manifest to v2.
- Remove PPV-specific workflows from seed.py (keep "Getting Started" dashboard).
- Verify install creates dashboards/workflows, uninstall removes them.

**S04: Seed Data & E2E** `risk:low` `depends:[S03]`
- Update james-life.jsonld with GuidingPrinciples instance and sample PillarScores.
- E2E tests: install creates TBox surfaces, uninstall removes them, user guide.

This ordering retires the highest risk (backward compat) first. S02 can technically proceed in parallel with S01 since it's purely ontology work, but depends on S01 for the manifest v2 format to wire everything together.

## Candidate Requirements

The following should be considered for explicit requirements tracking:

1. **v1 manifest backward compatibility:** All 6 existing models must install/uninstall without changes. (Table stakes — non-negotiable.)
2. **Model-sourced dashboard/workflow lifecycle:** Install creates, uninstall removes, refresh replaces. User-customized surfaces (detached from model) must survive refresh.
3. **PPV review system completeness:** Daily through yearly review workflows operational. Pillar scoring functional.
4. **Template system:** NOT recommended for this milestone — defer to follow-up. The core value is dashboards + workflows.

## Templates Deferral Rationale

The context document includes a `templates` entrypoint for task templates (Life Maintenance Checklist). This requires:
- New `TemplateSpec` SQLAlchemy model
- New `TemplateService` with CRUD
- New admin/browser UI for template management
- Template instantiation logic (create N objects from a template definition)
- Alembic migration for templates table

This is a complete new subsystem (~300-500 lines of backend + frontend). The Life Maintenance Checklist is a nice-to-have that can be approximated using a workflow step with a pre-filled create-form and default values. Deferring templates keeps M047 focused on the high-value deliverables (manifest v2 + review system).

## Dashboard Step Type for Workflows

Workflows already support `dashboard` step type. This means the review workflows can embed purpose-built dashboards as steps. The pattern:
1. Create a dashboard with specific blocks (e.g., "Pillar Scoring" dashboard with active pillars + form-group for PillarScore)
2. Create a workflow step: `{"type": "dashboard", "label": "Score Pillars", "config": {"dashboard_id": "..."}}`

**Challenge:** Dashboard IDs are UUIDs assigned at creation time. TBox workflows that reference TBox dashboards need a stable identifier scheme. Options:
- Use dashboard name for lookup at workflow step render time (fragile — name changes break it)
- Store a model-scoped ID in the manifest and resolve to UUID at install time (robust)
- Reference dashboards by model-scoped slug, resolve lazily at render time

**Recommendation:** Assign model-scoped IDs in the manifest (e.g., `"ppv:dashboard-action-items"`) and store a `model_ref` field alongside the UUID on the dashboard row. Workflow steps reference the model_ref, resolved to UUID at install time when both dashboards and workflows are created in the same transaction.

## Skill Discovery

No additional professional skills are needed for this work. The core technologies (Python/FastAPI, Pydantic, SQLAlchemy/Alembic, rdflib, SPARQL) are well-established in the codebase with extensive patterns to follow. No new external libraries or frameworks are introduced.
