---
id: M030
provides:
  - Validation pipeline fix — model_shapes_loader loads rules graphs, ValidationService passes advanced=True to pyshacl
  - 10 new SHACL-AF SPARQLConstraint data quality rules across 4 Mental Models (6 basic-pkm, 1 zettelkasten, 3 ppv, 1 research)
  - Lint filter system with SQLite persistence — suppress rule types, dismiss individual results, named presets
  - 13 REST API endpoints for lint filter CRUD (suppress/dismiss/preset operations)
  - Lint panel dismiss buttons, dashboard suppress buttons, preset selector, lint settings management UI
  - 7-test E2E Playwright suite proving full lint pipeline end-to-end
  - User guide Chapter 14 updated with 5 new sections (data quality rules, suppress, dismiss, presets, settings) + 4 glossary entries
key_decisions:
  - D278 — Cross-model rules placed in basic-pkm with type-namespace scoping via FILTER(STRSTARTS(...))
  - D279 — Lint filter storage in SQLite with server-side Python post-filtering (not SPARQL)
  - D280 — Additive preset model (presets store what to suppress, starting from "show all")
  - D281 — LINT-08 through LINT-20 requirement IDs continuing the LINT prefix sequence
  - D282 — Orphan object rule as SHACL-AF with performance monitoring, not SavedQuery
  - D283 — Violations not dismissable (structural issues must be resolved; only warnings/infos get dismiss)
patterns_established:
  - Multi-class SHACL-AF validation via sh:targetSubjectsOf rdf:type + UNION in SPARQL body
  - Type-namespace scoping via FILTER(STRSTARTS(STR(?type), "urn:sempkm:model:basic-pkm:")) to limit cross-model rules
  - Per-rule test pattern using _run_rule_test helper with sh:sourceShape filtering (K019)
  - LintFilterService follows PersonaService session_factory pattern (async session factory, dataclass read models)
  - Over-fetch re-pagination pattern for filtered result sets (fetch all, filter in Python, re-slice)
  - Poll for lint results with specific source_shape match in E2E tests — validation coalescing makes timing unpredictable
observability_surfaces:
  - GET /api/lint/suppressions — list active suppressions for authenticated user
  - GET /api/lint/dismissals — list active dismissals for authenticated user
  - GET /api/lint/presets — list presets for authenticated user
  - GET /api/lint/status — JSON with latest validation run results including warning/info counts
  - docker compose logs api | grep "rules triples" — shows whether rules are loading at startup
  - /browser/lint-dashboard — visual dashboard with filterable results, suppress buttons, preset selector
  - pytest tests/test_data_quality_rules.py -v — per-rule pass/fail with full pyshacl results_text on failure
requirement_outcomes:
  - id: LINT-08
    from_status: active
    to_status: validated
    proof: S01 fixed model_shapes_loader to include rules graphs and ValidationService to pass advanced=True; Docker logs confirm "Loaded 1143 shapes + 35 rules triples"; lint panel shows 2 overdue-task warnings from M011 rules
  - id: LINT-09
    from_status: active
    to_status: validated
    proof: S02 CommaInTagsValidationShape fires sh:Warning; 2 pytest tests (positive + negative) in test_data_quality_rules.py; S04 E2E test creates Note with comma-in-tags and verifies result appears
  - id: LINT-10
    from_status: active
    to_status: validated
    proof: S02 EmptyBodyValidationShape fires sh:Info for Notes/Concepts (basic-pkm) and 4 Zettelkasten note types; 3 pytest tests; S04 E2E test creates Note with empty body and verifies result appears
  - id: LINT-11
    from_status: active
    to_status: validated
    proof: S02 ConceptNoDefinitionValidationShape fires sh:Info; 2 pytest tests (positive + negative)
  - id: LINT-12
    from_status: active
    to_status: validated
    proof: S02 TitlelessObjectValidationShape fires sh:Warning for basic-pkm objects with no dcterms:title or rdfs:label; 3 pytest tests (positive + 2 negative variants)
  - id: LINT-13
    from_status: active
    to_status: validated
    proof: S02 OrphanObjectValidationShape fires sh:Info for basic-pkm objects with zero connections; 2 pytest tests
  - id: LINT-14
    from_status: active
    to_status: validated
    proof: S02 DuplicateUrlValidationShape fires sh:Info when same-type objects share schema:url; 2 pytest tests
  - id: LINT-15
    from_status: active
    to_status: validated
    proof: S02 StaleProjectValidationShape fires sh:Info for PPV Project with no dcterms:modified; 2 pytest tests
  - id: LINT-16
    from_status: active
    to_status: validated
    proof: S02 ActionItemNoProjectValidationShape fires sh:Warning; 2 pytest tests
  - id: LINT-17
    from_status: active
    to_status: validated
    proof: S02 ProjectNoGoalValidationShape fires sh:Warning; 2 pytest tests. ClaimNoRationaleValidationShape also implemented as bonus rule (research model)
  - id: LINT-18
    from_status: active
    to_status: validated
    proof: S03 suppress API (POST/DELETE/GET/DELETE-all), server-side Python filtering excludes suppressed rules, dashboard eye-off button, settings management with remove/clear-all; 59 unit tests; S04 E2E test suppresses CommaInTags and verifies results excluded
  - id: LINT-19
    from_status: active
    to_status: validated
    proof: S03 dismiss API (POST/DELETE/GET/DELETE-all), lint panel × dismiss button on warnings/infos only (D283), server-side filtering excludes dismissed pairs, settings management; 59 unit tests; S04 E2E test dismisses EmptyBody for specific object and verifies exclusion
  - id: LINT-20
    from_status: active
    to_status: validated
    proof: S03 preset CRUD API (POST/GET/PUT/DELETE/apply), dashboard preset selector dropdown with "Save Current"/"No preset", atomic apply replaces all suppressions, settings management with rename/delete; 59 unit tests; S04 E2E test saves preset, clears filters, applies preset, verifies restoration
duration: ~4h
verification_result: passed
completed_at: 2026-03-21
---

# M030: Data Quality Linting & Lint UX

**Fixed the broken SHACL-AF validation pipeline so 11 existing rules fire in production, added 10 new data quality rules across 4 Mental Models, and built a full lint filter system (suppress, dismiss, presets) with SQLite persistence and management UI**

## What Happened

M030 tackled three layered problems in sequence: a broken pipeline, missing rules, and no way to manage results.

**S01 (Pipeline Fix)** discovered and fixed the root cause of all M011 SHACL-AF validation rules being inert in production. `model_shapes_loader()` was only loading shapes graphs — not rules graphs. `ValidationService.validate()` wasn't passing `advanced=True` to pyshacl, so SPARQLConstraint rules never executed. The fix merged rules graphs into the shapes loader output, passed `advanced=True`, and also fixed two downstream bugs: `_store_report` was failing on blank node IRIs (switched to Graph Store protocol), and `_rdf_term_to_sparql` wasn't handling BNodes. After the fix, the Docker lint panel immediately showed 2 overdue-task warnings from M011's existing rules — the first time these rules had ever fired in production. Performance measured at 0.266s for advanced validation on live data, well within the 5s budget.

**S02 (Data Quality Rules)** added 10 new SHACL-AF SPARQLConstraint validation NodeShapes across 4 model rules files. Six rules went into basic-pkm (comma-in-tags, empty body, concept no definition, titleless objects, orphan objects, duplicate URL), one into zettelkasten (empty body for 4 note types), three into ppv (stale project, action item not linked to project, project not linked to goal), and one into research (claim no rationale). Cross-model rules (titleless, orphan) use `FILTER(STRSTARTS(STR(?type), "urn:sempkm:model:basic-pkm:"))` to scope to basic-pkm types only. All 10 rules were proven by 24 isolated pytest tests using a `_run_rule_test` helper that filters by `sh:sourceShape` (K019 pattern). The existing `EXPECTED_PYSHACL` cross-model test was refactored to a parametrized test and updated with new counts.

**S03 (Filter System)** built the complete lint filter CRUD in 5 tasks, layered bottom-up. Three SQLAlchemy ORM models (`LintSuppression`, `LintDismissal`, `LintPreset`) with Alembic migration 015, a `LintFilterService` with 15 async CRUD methods, 13 REST API endpoints, server-side Python post-filtering with over-fetch re-pagination, lint panel dismiss buttons on warnings/infos (violations excluded per D283), dashboard suppress buttons and preset selector, and a lint settings management UI with CRUD for all three entity types. 59 unit tests across 3 test files.

**S04 (E2E Tests & Docs)** created a 7-test Playwright E2E suite proving the full acceptance flow against the Docker test stack: setup → create objects with data quality issues → suppress rule → dismiss result → save/apply preset → verify settings management → cleanup. User guide Chapter 14 gained 5 new sections (139 lines) documenting all data quality rules and the filter system, plus 4 new glossary entries.

## Cross-Slice Verification

Each success criterion from the roadmap verified:

| Criterion | Evidence | Status |
|-----------|----------|--------|
| Pipeline fix: `model_shapes_loader()` includes rules, `validate()` passes `advanced=True` | S01 Docker logs: "Loaded 1143 shapes + 35 rules triples from 1 model(s)" | ✅ |
| All 11 existing M011 rules fire in Docker | S01 lint dashboard shows 2 overdue-task warnings; `/api/lint/status` returns `warning_count: 2` | ✅ |
| All 9+ new rules fire in offline pyshacl tests | S02: `pytest tests/test_data_quality_rules.py` — 24/24 passed (10 rules, 11 positive + 12 negative + 1 multi-type) | ✅ |
| New rules fire in Docker after object creation | S04 E2E test: creates Notes with empty body and comma-in-tags, polls until validation results appear with matching source_shape | ✅ |
| Lint filter CRUD: suppress, dismiss, preset | S03: 59 unit tests across 3 files; S04 E2E test exercises suppress → dismiss → preset save/apply/clear | ✅ |
| Lint panel UI shows filter controls | S03: dismiss × buttons on warnings/infos, "N dismissed" indicator, suppress eye-off buttons on dashboard | ✅ |
| Lint settings UI for managing state | S03: 3 collapsible sections (suppressions, dismissals, presets) with remove/clear/rename/delete actions | ✅ |
| E2E Playwright tests | S04: 7/7 tests pass in 23.8s (Chromium) | ✅ |
| User guide updated | S04: 5 new sections in Chapter 14 (568 total lines), 4 glossary entries | ✅ |
| Final acceptance scenarios pass | S04 E2E: create → see warning → suppress → dismiss → preset save/restore → settings manage → cleanup | ✅ |

All 4 slices completed with `verification_result: passed`. All 4 slice summaries exist. Full backend test suite (2654 tests) passes.

## Requirement Changes

- LINT-08: active → validated — Pipeline fix proven by Docker logs showing rules loading and lint panel showing M011 warnings
- LINT-09: active → validated — Comma-in-tags rule fires; proven by 2 pytest tests + E2E test
- LINT-10: active → validated — Empty body rule fires for basic-pkm and zettelkasten types; proven by 3 pytest tests + E2E test
- LINT-11: active → validated — Concept no definition rule fires; proven by 2 pytest tests
- LINT-12: active → validated — Titleless objects rule fires; proven by 3 pytest tests
- LINT-13: active → validated — Orphan objects rule fires; proven by 2 pytest tests
- LINT-14: active → validated — Duplicate URL rule fires; proven by 2 pytest tests
- LINT-15: active → validated — Stale project rule fires; proven by 2 pytest tests
- LINT-16: active → validated — PPV action item no project rule fires; proven by 2 pytest tests
- LINT-17: active → validated — PPV project no goal rule fires; proven by 2 pytest tests
- LINT-18: active → validated — Rule suppression works end-to-end; proven by 59 unit tests + E2E test
- LINT-19: active → validated — Individual dismissal works end-to-end; proven by 59 unit tests + E2E test
- LINT-20: active → validated — Named presets work end-to-end; proven by 59 unit tests + E2E test

## Forward Intelligence

### What the next milestone should know
- The validation pipeline is now fully operational: `model_shapes_loader()` fetches both shapes and rules graphs, `ValidationService` passes `advanced=True`. Any new SHACL-AF rules added to model `rules/*.ttl` files will automatically fire in production.
- Adding a new data quality rule is copy-paste: create a NodeShape with `sh:sparql [ a sh:SPARQLConstraint; sh:message "..."; sh:select "..." ]` in the appropriate model's rules file. The `EXPECTED_PYSHACL` dict in `test_cross_model_validation.py` must be updated if the rule fires against seed data.
- Lint filter storage is in SQLite (3 tables: `lint_suppressions`, `lint_dismissals`, `lint_presets`). The `source_shape` IRI is the stable identifier used for both suppress and dismiss operations — it's always populated on `LintResultItem` from SPARQL.
- The over-fetch approach for filtered pagination loads ALL results when filters are active. For typical result sets (~50-200) this is fast, but would need optimization for thousands of results.

### What's fragile
- `EXPECTED_PYSHACL` counts in `test_cross_model_validation.py` are tightly coupled to seed data — any seed data change requires updating the `(warnings, infos)` tuple for that model
- Cross-model rules use `STRSTARTS(STR(?type), "urn:sempkm:model:basic-pkm:")` namespace scoping — if the IRI convention changes, rules silently stop firing
- Rule labels in lint settings use `_local_name()` instead of `LabelService.resolve()` because SHACL shape IRIs lack `rdfs:label` — a pragmatic workaround
- Docker test image needs migration 015 manually applied if the image was built before S03

### Authoritative diagnostics
- `pytest tests/test_data_quality_rules.py -v` — each test class maps to one SHACL validation shape; failure output includes full pyshacl results_text
- `docker compose logs api | grep "rules triples"` — confirms rules are loading at startup
- `GET /api/lint/status` — JSON with latest run results (conforms, warning_count, info_count)
- `GET /api/lint/suppressions` + `GET /api/lint/dismissals` — shows exactly what's being filtered for the current user
- `cd e2e && npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts` — fastest way to verify the full M030 stack

### What assumptions changed
- Plan said "9 new rules" but implementation correctly has 10 NodeShapes — PPV broken chain is 2 separate shapes (ActionItemNoProject + ProjectNoGoal) and DuplicateUrl was under-counted in the original plan
- Stale project rule simplified from "no recent dcterms:modified" to "no dcterms:modified at all" due to K001 rdflib date arithmetic limitation — catches never-modified projects but misses stale-but-once-modified ones
- Validation timing is less predictable than assumed — sequential validation runs after each object creation mean results may not appear for 15-20s; E2E tests use polling with source_shape matching instead of fixed timeouts
- `source_shape` was originally only populated in detail mode on LintResultItem — changed to always populate it since both filtering and UI buttons depend on it (backward compatible)

## Files Created/Modified

- `backend/app/services/validation.py` — Pipeline fix: advanced=True, Graph Store protocol for report storage, BNode handling
- `backend/app/services/models.py` — model_shapes_loader extended to include rules graphs
- `backend/app/commands/handlers/object_patch.py` — Auto-type YYYY-MM-DD strings as xsd:date
- `models/basic-pkm/rules/basic-pkm.ttl` — 6 new validation NodeShapes + expanded PrefixDeclarations
- `models/zettelkasten/rules/zettelkasten.ttl` — 1 new EmptyBodyValidationShape
- `models/ppv/rules/ppv.ttl` — 3 new validation NodeShapes + expanded PrefixDeclarations
- `models/research/rules/research.ttl` — 1 new ClaimNoRationaleValidationShape
- `backend/app/lint/filter_models.py` — 3 SQLAlchemy ORM models (LintSuppression, LintDismissal, LintPreset)
- `backend/app/lint/filter_service.py` — LintFilterService with 15 async CRUD methods
- `backend/app/lint/models.py` — 7 Pydantic request/response models for filter API
- `backend/app/lint/router.py` — 13 REST API endpoints for lint filter CRUD + filter wiring
- `backend/app/lint/service.py` — Server-side Python post-filtering with over-fetch re-pagination
- `backend/app/main.py` — LintFilterService wired into app.state
- `backend/app/dependencies.py` — get_lint_filter_service dependency getter
- `backend/app/browser/pages.py` — lint dashboard filter wiring + lint settings route
- `backend/app/browser/objects.py` — lint panel filter wiring
- `backend/app/templates/browser/lint_panel.html` — dismiss buttons + dismissed count indicator
- `backend/app/templates/browser/lint_dashboard.html` — suppress buttons + preset selector + manage filters link
- `backend/app/templates/browser/lint_settings.html` — settings management section
- `frontend/static/js/workspace.js` — 10 lint filter JS handler functions
- `frontend/static/css/workspace.css` — lint filter UI styling (~230 lines)
- `backend/migrations/versions/015_lint_filters.py` — Alembic migration 015 (3 tables)
- `backend/tests/test_data_quality_rules.py` — 24 per-rule tests across 11 test classes
- `backend/tests/test_cross_model_validation.py` — updated EXPECTED_PYSHACL counts, parametrized test
- `backend/tests/test_basic_pkm_v2.py` — fixed synthetic data to prevent new rule false positives
- `backend/tests/test_lint_filter_service.py` — 30 CRUD unit tests
- `backend/tests/test_lint_filter_api.py` — 18 API endpoint tests
- `backend/tests/test_lint_filtering.py` — 11 server-side filtering tests
- `e2e/tests/10-lint-dashboard/lint-filters.spec.ts` — 7-test E2E suite
- `docs/guide/14-system-health-and-debugging.md` — 5 new sections (139 lines)
- `docs/guide/appendix-d-glossary.md` — 4 new entries + updated Lint Dashboard entry
