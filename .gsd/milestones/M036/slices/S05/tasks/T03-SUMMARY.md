---
id: T03
parent: S05
milestone: M036
provides:
  - Section "5. Business Planning" in user guide chapter 39 documenting all 15 business planning frameworks (32 types)
  - Type reference tables with field/type/required/description for every concrete type
  - Custom renderer descriptions (quadrant, bmc, okr, decision-matrix)
  - Cross-model edges documentation (bp:relatedTask, bp:relatedGoalOutcome, bp:relatedProject)
  - 3 SPARQL query examples (Eisenhower Do-First, OKR progress, Decision Matrix weighted totals)
  - Updated Model Comparison table with Business Planning row
key_files:
  - docs/guide/39-mental-model-catalog.md
key_decisions: []
patterns_established: []
observability_surfaces:
  - none (static documentation only)
duration: 15m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: User guide documentation for all business planning frameworks

**Added comprehensive "5. Business Planning" section to chapter 39 documenting all 15 frameworks with 32 types, custom renderers, cross-model edges, and SPARQL examples**

## What Happened

Added ~490 lines of documentation to `docs/guide/39-mental-model-catalog.md` as section "## 5. Business Planning" between the existing Research Workflow section and the Model Comparison table. Documented all 15 frameworks grouped into 5 categories (Prioritization & Decision-Making, Strategy Analysis, Business Design, Goal Tracking, Resource Management). Each framework includes the container type and item type with full field reference tables sourced from the ontology and SHACL shapes files. Added custom renderers section describing all 4 view types, cross-model edges table, 3 SPARQL query examples, relationships diagram, installation instructions, and recommended dashboard configuration. Updated the Model Comparison table with the Business Planning row (32 types, 0 validation rules, 0 saved queries). Also added `## Observability Impact` to the T03 plan as required by the pre-flight check.

## Verification

- Section heading found: `rg "^## 5\. Business Planning"` returns match
- Line count: 1101 lines (target ≥ 900, was 608 before)
- Business Planning mentions: 6 (target ≥ 5)
- Framework mentions: 91 lines matching framework names (target ≥ 15)
- Cross-model edges: 7 mentions of relatedTask/relatedGoalOutcome/relatedProject (target ≥ 3)
- All slice-level checks pass: rdflib assertion OK, shapes grep OK, E2E spec exists, tsc errors are pre-existing in unrelated files only

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `wc -l docs/guide/39-mental-model-catalog.md` | 0 | ✅ pass (1101 ≥ 900) | <1s |
| 2 | `rg "^## 5\. Business Planning" docs/guide/39-mental-model-catalog.md` | 0 | ✅ pass | <1s |
| 3 | `rg "Business Planning" docs/guide/39-mental-model-catalog.md \| wc -l` | 0 | ✅ pass (6 ≥ 5) | <1s |
| 4 | `rg "Eisenhower\|SWOT\|..." \| wc -l` | 0 | ✅ pass (91 ≥ 15) | <1s |
| 5 | `rg "relatedTask\|relatedGoalOutcome\|relatedProject" docs/guide/... \| wc -l` | 0 | ✅ pass (7 ≥ 3) | <1s |
| 6 | Slice: `python3 -c "...cross-model properties assertion..."` | 0 | ✅ pass | <1s |
| 7 | Slice: `rg ... models/business-planning/shapes/...` | 0 | ✅ pass | <1s |
| 8 | Slice: `test -f e2e/tests/36-business-planning/business-planning.spec.ts` | 0 | ✅ pass | <1s |
| 9 | Slice: `cd e2e && npx tsc --noEmit` | 2 | ⚠️ pre-existing errors in 06-settings + 07-multi-user (not our files) | 3s |

## Diagnostics

- `rg "^## 5\. Business Planning" docs/guide/39-mental-model-catalog.md` — confirms section exists
- `wc -l docs/guide/39-mental-model-catalog.md` — confirms sufficient content
- `rg "relatedTask|relatedGoalOutcome|relatedProject" docs/guide/39-mental-model-catalog.md` — confirms cross-model edges documented

## Deviations

- The task plan says "16 frameworks" but the ontology has 15 distinct frameworks (Eisenhower, Decision Matrix, SWOT, Porter, PESTLE, BCG, Ansoff, BMC, Lean Canvas, Value Chain, OKR, Balanced Scorecard, RACI, Stakeholder Map, Risk Matrix). The count depends on whether you count abstract base classes — documented all 15 concrete frameworks with 32 types as specified in the ontology.

## Known Issues

- The `cd e2e && npx tsc --noEmit` check fails with pre-existing type errors in `tests/06-settings/llm-config.spec.ts` and `tests/07-multi-user/invite-flow.spec.ts`. These are unrelated to the business-planning model work. The business-planning spec (`tests/36-business-planning/`) produces no type errors.

## Files Created/Modified

- `docs/guide/39-mental-model-catalog.md` — Added section "5. Business Planning" (~490 lines) and updated Model Comparison table
- `.gsd/milestones/M036/slices/S05/tasks/T03-PLAN.md` — Added Observability Impact section per pre-flight requirement
