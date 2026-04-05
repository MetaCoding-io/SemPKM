---
id: S03
parent: M047
milestone: M047
provides:
  - 5 PPV dashboards (Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub) as TBox definitions
  - 5 PPV workflows (Daily Check-in, Weekly/Monthly/Quarterly/Yearly Review) as TBox definitions
  - dashboard_name→UUID resolution infrastructure in ModelService.install() and refresh_artifacts()
  - Seed.py trimmed to 1 generic workflow — PPV review workflows are now model-sourced
requires:
  - slice: S01
    provides: TBox install/uninstall lifecycle infrastructure with source_model column
  - slice: S02
    provides: PPV ontology with ViewSpec IRIs referenced by dashboard view-embed blocks
affects:
  - S04
key_files:
  - models/ppv/dashboards/ppv.json
  - models/ppv/workflows/ppv.json
  - models/ppv/manifest.yaml
  - backend/app/services/models.py
  - backend/app/dashboard/seed.py
  - backend/tests/test_tbox_loader.py
  - backend/tests/test_tbox_lifecycle.py
key_decisions:
  - D382: dashboard_name→dashboard_id resolution at install time via _resolve_dashboard_names() post-processing
patterns_established:
  - TBox dashboard JSON format: gridstack blocks with stat-card/view-embed/heading/sparql-result types, validated against BLOCK_REGISTRY
  - TBox workflow JSON format: steps with view/dashboard/form types, dashboard steps use dashboard_name for symbolic cross-reference
  - Install-time name resolution: ModelService builds name→UUID map from created dashboards, replaces dashboard_name with dashboard_id in workflow step configs before creating workflows
  - Same resolution applied in refresh_artifacts() for delete+recreate cycle
observability_surfaces:
  - _resolve_dashboard_names() logs warning for unresolved dashboard names (degraded mode)
drill_down_paths:
  - .gsd/milestones/M047/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M047/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M047/slices/S03/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T00:12:29.225Z
blocker_discovered: false
---

# S03: TBox Dashboards & Workflows — PPV Operating System

**PPV model ships 5 dashboards and 5 workflows as TBox definitions with install-time dashboard_name→UUID resolution; seed.py trimmed to 1 generic workflow.**

## What Happened

This slice delivered the full PPV operating system as model-sourced TBox surfaces — 5 dashboards covering the PPV workflow (Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub) and 5 workflows covering the review cadence (Daily Check-in, Weekly/Monthly/Quarterly/Yearly Review).

T01 replaced the single test dashboard placeholder with 5 production dashboards using gridstack layout. Each dashboard uses heading blocks, stat-cards with SPARQL count queries (ppv: prefix auto-injected at runtime), view-embed blocks referencing full ViewSpec IRIs from S02, and sparql-result blocks for diagnostic queries (orphan projects, goals without outcomes). All 25 blocks validated against BLOCK_REGISTRY.

T02 created the workflows JSON with 5 definitions using view/dashboard/form step types. Dashboard steps use `dashboard_name` string references that are resolved to `dashboard_id` UUIDs at install time. The `_resolve_dashboard_names()` helper in ModelService runs after dashboard creation during install and refresh, replacing name references with real UUIDs. Unresolved names log a warning but don't fail (degraded mode per D380). The manifest was updated with the `workflows` entrypoint.

T03 cleaned up seed.py by removing 4 PPV-specific workflows and the `_PPV` namespace constant, leaving only the generic "Create & Review" workflow. Added comprehensive test coverage: seed workflow count/content validation, real PPV workflow file loading, and an unresolved dashboard_name integration test that exercises the full install pipeline with a minimal v2 model archive.

## Verification

35 tests pass across test_tbox_loader.py (19) and test_tbox_lifecycle.py (16). JSON structure checks confirm 5 dashboards and 5 workflows. Manifest validation confirms workflows entrypoint. Seed workflow count confirms exactly 1 entry.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None. All three tasks completed as planned.

## Known Limitations

Dashboard SPARQL queries use ppv: prefix which requires the model's prefix registry to be loaded at runtime. If the prefix registry is stale or missing, stat-card queries will fail with SPARQL parse errors. The view-embed blocks reference ViewSpec IRIs that must exist in the triplestore — if S02 ontology changes ViewSpec IRIs, dashboards will show empty views.

## Follow-ups

S04 will add E2E verification for the full install → dashboard render → workflow launch → uninstall lifecycle. The Life Maintenance Checklist (deferred per D379) could be added as a workflow step with a create-form pre-fill once template infrastructure exists.

## Files Created/Modified

- `models/ppv/dashboards/ppv.json` — Replaced test dashboard with 5 production PPV dashboards (25 gridstack blocks total)
- `models/ppv/workflows/ppv.json` — New file: 5 PPV workflow definitions with view/dashboard/form step types
- `models/ppv/manifest.yaml` — Added workflows entrypoint: workflows/ppv.json
- `backend/app/services/models.py` — Added _resolve_dashboard_names() helper, wired into install() and refresh_artifacts()
- `backend/app/dashboard/seed.py` — Removed 4 PPV-specific workflows and _PPV constant, keeping 1 generic workflow
- `backend/tests/test_tbox_loader.py` — Added TestLoadTboxWorkflows, TestResolveDashboardNames, TestSeedWorkflows test classes + updated dashboard assertions
- `backend/tests/test_tbox_lifecycle.py` — Added unresolved dashboard_name integration test
