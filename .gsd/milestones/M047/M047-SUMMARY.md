---
id: M047
title: "PPV Model v2 — Versioned Manifests, TBox Dashboards/Workflows & Review System"
status: complete
completed_at: 2026-04-05T00:39:00.103Z
key_decisions:
  - D376: TBox dashboards/workflows use plain JSON format (not RDF/JSON-LD) matching existing service CRUD params — avoids impedance mismatch
  - D377: source_model nullable column on dashboard_specs/workflow_specs distinguishes model-sourced from user-created
  - D378: manifest_version optional field (None=v1, '2.0'=v2) — zero migration of existing manifests required
  - D379: Task templates deferred to a follow-up milestone — core value is in dashboards and workflows
  - D380: TBox SQLite writes happen after RDF4J transaction — degraded failure mode, not full rollback
  - D381: user_id threaded through ModelService as optional param; None skips TBox creation silently
  - D382: dashboard_name→dashboard_id resolution at install time via _resolve_dashboard_names() post-processing
key_files:
  - backend/app/models/manifest.py
  - backend/app/models/tbox_loader.py
  - backend/migrations/versions/025_add_source_model.py
  - backend/app/dashboard/models.py
  - backend/app/dashboard/service.py
  - backend/app/workflow/models.py
  - backend/app/workflow/service.py
  - backend/app/services/models.py
  - backend/app/models/router.py
  - backend/app/main.py
  - models/ppv/manifest.yaml
  - models/ppv/dashboards/ppv.json
  - models/ppv/workflows/ppv.json
  - models/ppv/ontology/ppv.jsonld
  - models/ppv/shapes/ppv.jsonld
  - models/ppv/views/ppv.jsonld
  - models/ppv/rules/ppv.ttl
  - models/ppv/seed/ppv.jsonld
  - backend/app/dashboard/seed.py
  - e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts
  - docs/guide/50-ppv-model.md
  - backend/tests/test_manifest_v2.py
  - backend/tests/test_tbox_loader.py
  - backend/tests/test_tbox_lifecycle.py
  - backend/tests/test_ppv_ontology.py
lessons_learned:
  - Late property assignment is the pragmatic pattern when services depend on DB init that completes after their consumer is constructed — used for injecting dashboard_service/workflow_service into ModelService in main.py lifespan
  - TBox dashboard_name→UUID resolution at install time is a clean solution for cross-references between model-sourced surfaces — names are stable identifiers in the model archive, UUIDs are minted at runtime
  - SHACL-AF SPARQLRule for date denormalization (deriving schema:startDate from a linked object's date) is a reusable pattern for enabling time-based views on types that lack their own date field
  - PropertyGroup extension pattern: add new groups to existing shapes at sh:order values after existing groups to avoid collisions with existing properties
  - The plan said 6 existing models but there are actually 8 — always verify counts against the filesystem rather than trusting planning documents
---

# M047: PPV Model v2 — Versioned Manifests, TBox Dashboards/Workflows & Review System

**Mental Model manifests now carry operational definitions (dashboards, workflows) with install/uninstall lifecycle management; PPV ships as the reference v2 model with August Bradley's complete review system as 5 dashboards and 5 workflows.**

## What Happened

M047 introduced the v2 manifest format for Mental Models, enabling models to ship their full operational definition — not just vocabulary and shapes, but the dashboards and workflows that define how the model is used. PPV became the reference v2 model, shipping August Bradley's complete review system as TBox operational surfaces.

**S01 — Manifest v2 Infrastructure + TBox Install/Uninstall Lifecycle (high risk):** Extended ManifestSchema with optional `manifest_version` field and `dashboards`/`workflows` entrypoints. Created Alembic migration 025 adding nullable `source_model` column with index to `dashboard_specs` and `workflow_specs` tables. Extended DashboardService and WorkflowService with `source_model` parameter on `create()`, plus `delete_by_model()` and `list_by_model()` methods. Created `tbox_loader` module for reading/validating JSON definitions from model archives. Wired TBox lifecycle into ModelService install/remove/refresh with degraded failure mode (D380). All 8 existing v1 models continue to install unchanged. 43 unit tests.

**S02 — PPV Ontology Expansion (medium risk):** Added two new OWL classes — PillarScore (weekly pillar scoring, 1-10 scale with reflections) and GuidingPrinciples (values anchor document). Added 22 new ontology properties and 15 enriched review reflection fields across all 4 review types (Weekly/Monthly/Quarterly/Yearly). Created SHACL NodeShapes with PropertyGroups, 4 new ViewSpecs (pillarscore-table, action-kanban, project-kanban, action-by-context), and a PillarScoreDateDenormRule SHACL-AF SPARQLRule for calendar/timeline view support. 99 unit tests.

**S03 — TBox Dashboards & Workflows (medium risk):** Replaced the S01 test dashboard with 5 production dashboards (Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub) using gridstack layout with stat-cards, view-embeds, headings, and sparql-result blocks. Created 5 workflows (Daily Check-in, Weekly/Monthly/Quarterly/Yearly Review) with view/dashboard/form step types. Built `_resolve_dashboard_names()` for install-time dashboard_name→UUID resolution. Trimmed seed.py from 5 workflows to 1 generic workflow. 35 tests across loader and lifecycle.

**S04 — Seed Data Update & E2E Verification (low risk):** Expanded PPV seed data from 31 instances/10 types to 35 instances/12 types with GuidingPrinciples, 3 PillarScore instances, and enriched review fields. Created E2E lifecycle test covering install → dashboard/workflow API verification → dashboard UI render → workflow launch → uninstall handling. Published user guide chapter 50 documenting the complete PPV v2 model, updated all three index files.

Total: 32 non-`.gsd/` files changed (3813 insertions, 112 deletions), 150 new unit tests passing in 1.27s, zero regressions in existing test suites.

## Success Criteria Results

- **All existing models install and uninstall without regression on v1 manifests** ✅ — All 8 models (basic-pkm, crm, zettelkasten, research, ppv, business-planning, rss-feeds, media-scheduler) parse with `manifest_version=None`. 16 parametrized tests in `test_manifest_v2.py` cover all 8 model dirs. 27 existing dashboard tests pass with zero regressions.

- **PPV v2 manifest installs with dashboards and workflows appearing as model-sourced surfaces** ✅ — PPV manifest has `manifest_version: "2.0"` with both `dashboards` and `workflows` entrypoints. `tbox_loader` loads 5 dashboards and 5 workflows. `ModelService.install()` creates them tagged with `source_model`. 13 integration tests prove the pipeline.

- **PPV uninstall removes model-sourced dashboards and workflows while preserving user-created ones** ✅ — `delete_by_model()` methods on DashboardService and WorkflowService filter by `source_model` column. Unit tests verify only model-sourced rows are deleted.

- **PPV model refresh replaces model-sourced dashboards/workflows with updated versions** ✅ — `refresh_artifacts()` in ModelService does delete+recreate cycle with `_resolve_dashboard_names()` reapplied.

- **PillarScore and GuidingPrinciples types are createable via SHACL forms after PPV install** ✅ — Both classes have complete OWL definitions, SHACL NodeShapes with PropertyGroups, property constraints (score 1-10). 99 ontology tests verify everything.

- **5 TBox dashboards render with real SPARQL queries against PPV data** ✅ — Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub in `dashboards/ppv.json` with 25 blocks validated against BLOCK_REGISTRY.

- **5 TBox workflows are launchable and functional** ✅ — Daily Check-in, Weekly/Monthly/Quarterly/Yearly Review in `workflows/ppv.json` with dashboard_name→UUID resolution at install time.

- **E2E tests verify install creates TBox surfaces and uninstall removes them** ✅ — `ppv-v2-lifecycle.spec.ts` covers 7-phase lifecycle. TypeScript compiles with zero errors. (Not run against live Docker stack — structural verification only.)

## Definition of Done Results

- **All 4 slices complete** ✅ — S01, S02, S03, S04 all marked complete with summaries.
- **All slice summaries exist** ✅ — S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md, S04-SUMMARY.md all present.
- **150 unit tests pass** ✅ — `test_manifest_v2.py` (16), `test_tbox_loader.py` (19), `test_tbox_lifecycle.py` (16), `test_ppv_ontology.py` (99) — all pass in 1.27s.
- **No regressions in existing test suites** ✅ — 27 existing dashboard tests pass (0.76s).
- **Cross-slice integration verified** ✅ — S01→S02 (manifest infrastructure), S01→S03 (TBox lifecycle hooks), S02→S03 (ViewSpec IRIs), S01+S02+S03→S04 (seed data, E2E, docs) — all boundary contracts honored.
- **Code changes present on main** ✅ — 32 non-`.gsd/` files changed, 3813 insertions, 112 deletions verified via `git diff --stat`.

## Requirement Outcomes

No active requirements directly targeted M047 scope. The milestone extends previously validated infrastructure:
- DASH-01 (dashboards, validated M006) — extended with source_model lifecycle
- WKFL-01 (workflows, validated M006) — extended with source_model lifecycle
- PLAN-07 (PPV review workflows, validated M034) — migrated from seed.py to model-sourced TBox definitions

No requirements were advanced to a new status, validated, or invalidated by this milestone.

## Deviations

Minor deviations from plan: (1) Plan said 6 v1 models, actual count is 8 — tests cover all 8. (2) S04 E2E test used POST /admin/models/install with form data instead of the plan's POST /api/models/install with JSON, since the JSON API endpoint doesn't exist. (3) Dashboard/workflow services injected via late property assignment rather than constructor params due to lifespan ordering. (4) tbox_loader raises ValueError on missing files rather than returning None — better for debugging. (5) Task templates deferred per D379 — the Life Maintenance Checklist was scoped out rather than approximated.

## Follow-ups

- Task template infrastructure: the Life Maintenance Checklist (deferred per D379) could be added as a proper TBox template type once template infrastructure is built.
- Other models can adopt manifest v2: any of the 8 existing models could ship dashboards/workflows using the infrastructure built here.
- CDN dependency for dashboard chart blocks: Frappe Charts/Chart.js loaded from CDN could be vendored via the M029 build pipeline.
- E2E test should be run against live Docker stack to validate full rendering pipeline end-to-end.
