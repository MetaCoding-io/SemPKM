# M030 — Research: Data Quality Linting & Lint UX

**Date:** 2026-03-20
**Status:** Complete

## Summary

M030 is a three-part milestone: (1) fix the production validation pipeline so existing SHACL-AF rules fire, (2) add 9 new data quality rules, and (3) build a lint filter/dismiss system with presets. Research confirms the pipeline fix is a surgical ~5-line change in `model_shapes_loader()` and `ValidationService.validate()`. The 9 new rules are standard SHACL-AF SPARQLConstraint patterns following the proven M011 approach. The lint filter system is a new SQLite-backed subsystem requiring Alembic migrations, API endpoints, and frontend UI changes.

The pipeline fix is the critical-path first slice — without it, no rules (existing or new) fire in production. The data quality rules are independent of each other and can be written in parallel or batched. The lint filter system is UI-heavy and depends on the lint panel already showing results (i.e., the pipeline fix).

## Recommendation

**Slice ordering: Pipeline fix → Data quality rules → Lint filter system → E2E/Docs**

1. **S01: Pipeline fix** — Modify `model_shapes_loader()` to include `:rules` graphs alongside `:shapes` graphs, and pass `advanced=True` to `pyshacl.validate()`. This is the highest-risk, lowest-effort slice. Prove it by creating a task with a past due date and verifying the overdue warning appears in the lint panel. Performance measurement required.

2. **S02: Data quality rules** — Write 9 new `.ttl` rule files across model `rules/` directories. Cross-model rules (comma-in-tags, titleless, orphan) need a placement decision. Offline pytest tests prove each rule fires correctly.

3. **S03: Lint filter system** — SQLite tables for suppressions, dismissals, and presets. API endpoints. Frontend UI for filter controls in lint panel + lint settings page. This is the largest slice.

4. **S04: E2E tests + User guide docs** — Playwright tests against Docker stack proving the full acceptance criteria. User guide chapter update.

## Implementation Landscape

### Key Files

- `backend/app/services/validation.py` — `ValidationService.validate()` calls `pyshacl.validate()` without `advanced=True`. **Must add `advanced=True` parameter.** Currently at line ~72: `pyshacl.validate(data_graph, shacl_graph=shapes_graph, allow_infos=True, allow_warnings=True)`.

- `backend/app/services/models.py` — `model_shapes_loader()` (line ~565) constructs FROM clauses for `:shapes` graphs only. **Must also include `:rules` graphs.** The function queries the model registry for installed model IDs, then builds `urn:sempkm:model:{model_id}:shapes` FROM clauses. Needs to add `urn:sempkm:model:{model_id}:rules` FROM clauses too.

- `backend/app/main.py` — Wires `shapes_loader` into `ValidationService`. The loader is passed as `shapes_loader=lambda: model_shapes_loader(triplestore_client)`. After the fix, the loader returns shapes+rules combined, and ValidationService passes `advanced=True` to pyshacl.

- `backend/app/validation/queue.py` — `AsyncValidationQueue` dispatches validation runs. No changes needed here — it delegates to `ValidationService.validate()`.

- `backend/app/validation/report.py` — `ValidationReport.from_pyshacl()` parses results. No changes needed — it already handles violations, warnings, and infos.

- `models/*/rules/*.ttl` — 5 existing rules files (basic-pkm, crm, ppv, research, zettelkasten). New data quality rules will be added here. Each file contains SHACL-AF SPARQLConstraint rules in Turtle format.

- `backend/app/lint/` — Lint panel and dashboard routes/templates. `service.py` queries lint results from triplestore. `router.py` serves lint panel and dashboard pages. `broadcast.py` handles SSE. `models.py` has Pydantic models. The filter system extends this module.

- `backend/app/lint/service.py` — `LintService` queries structured lint results from `urn:sempkm:lint-run:*` graphs. **Must be extended** to support filtering by rule type suppression and per-object dismissals.

- `backend/tests/test_cross_model_validation.py` — Reference for how pyshacl tests load shapes+rules with `advanced=True`. This is the pattern the production fix should match.

- `backend/tests/test_basic_pkm_v2.py` — Another reference for offline pyshacl testing pattern.

- `backend/app/templates/browser/lint/` — Lint panel templates. Need filter controls (rule type suppression toggles, dismiss buttons per result).

### Validation Pipeline Fix — Detailed Analysis

The fix has two parts:

**Part 1: `model_shapes_loader()` must include rules graphs.**

Current code (models.py ~line 575):
```python
for b in bindings:
    model_id = b["modelId"]["value"]
    shapes_iri = f"urn:sempkm:model:{model_id}:shapes"
    from_clauses.append(f"FROM <{shapes_iri}>")
```

Must become:
```python
for b in bindings:
    model_id = b["modelId"]["value"]
    shapes_iri = f"urn:sempkm:model:{model_id}:shapes"
    rules_iri = f"urn:sempkm:model:{model_id}:rules"
    from_clauses.append(f"FROM <{shapes_iri}>")
    from_clauses.append(f"FROM <{rules_iri}>")
```

**Part 2: `ValidationService.validate()` must pass `advanced=True`.**

Current code (validation.py ~line 72):
```python
conforms, results_graph, _results_text = await asyncio.to_thread(
    pyshacl.validate,
    data_graph,
    shacl_graph=shapes_graph,
    allow_infos=True,
    allow_warnings=True,
)
```

Must become:
```python
conforms, results_graph, _results_text = await asyncio.to_thread(
    pyshacl.validate,
    data_graph,
    shacl_graph=shapes_graph,
    advanced=True,
    allow_infos=True,
    allow_warnings=True,
)
```

**Note:** The function is named `model_shapes_loader` but after this change it loads both shapes AND rules. Consider renaming to `model_shapes_and_rules_loader` for clarity, but this touches the wiring in `main.py` and is cosmetic.

### Data Quality Rules — Approach

All 9 rules use the same SHACL-AF SPARQLConstraint pattern proven in M011. Each rule is a `sh:NodeShape` with `sh:sparql` containing a `sh:SPARQLConstraint` that defines `sh:select`, `sh:message`, and `sh:severity`.

**Cross-model rule placement decision needed:**

Rules 1 (comma-in-tags), 4 (titleless), and 5 (orphan) apply across all models. Three options:
- **Option A: Platform rules graph** — New `platform/rules/` directory loaded into `urn:sempkm:platform:rules`. Cleanest but requires loader changes.
- **Option B: Duplicate per model** — Same rule in each model's rules file. Simple but maintenance burden.
- **Option C: Attach to basic-pkm** — Since basic-pkm is always installed (starter model), put cross-model rules there with broad `sh:targetClass` patterns (e.g., `rdfs:Resource` or use `sh:targetSubjectsOf`).

**Recommendation: Option C** for v1. basic-pkm is auto-installed as the starter model. Rules can use `sh:targetSubjectsOf` or broad SPARQL patterns without needing a new graph loading mechanism. Migrate to Option A later if the system gets a dedicated platform rules graph.

**Rule-specific notes:**

1. **Comma-in-tags** — `FILTER(CONTAINS(?tagVal, ","))` on `bpkm:tags` and `schema:keywords`. Can target `rdfs:Resource` since only tagged objects have these predicates.

2. **Empty body** — `NOT EXISTS { ?this urn:sempkm:body ?body }` for types that typically have content. Target specific type IRIs across models.

3. **Duplicate URL** — `SELECT` counting objects sharing `schema:url` or `dcterms:source` with `HAVING(COUNT(DISTINCT ?s) > 1)`. Complex — may need to return both objects.

4. **Titleless objects** — `NOT EXISTS { ?this dcterms:title ?t } && NOT EXISTS { ?this skos:prefLabel ?l } && ...` for all label predicates.

5. **Orphan objects** — `NOT EXISTS { ?this ?p ?other . ?other a ?anyType }` and `NOT EXISTS { ?other2 ?p2 ?this . ?other2 a ?anyType2 }`. Performance concern — may be expensive on large graphs. Consider running only on-demand or with a simpler heuristic.

6. **Stale project/goal** — Uses K001 pattern: `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` for date comparison. Compare `dcterms:modified` < 30 days ago.

7. **PPV broken chain** — `NOT EXISTS` for ActionItem/Project missing link to GoalOutcome/Pillar. PPV-specific.

8. **Concept with no definition** — `NOT EXISTS { ?this skos:definition ?def }`.

9. **Research claim with no rationale** — `NOT EXISTS { ?this res:rationale ?rat }`.

### Lint Filter System — Architecture

**Storage (SQLite via Alembic):**

Three new tables:
- `lint_suppressions` — (id, user_id FK, rule_source_iri TEXT, created_at). Suppresses all results from a given SHACL source shape.
- `lint_dismissals` — (id, user_id FK, object_iri TEXT, rule_source_iri TEXT, created_at). Dismisses a specific object×rule combination.
- `lint_presets` — (id, user_id FK, name TEXT, suppressed_rules JSON, created_at, updated_at). Named filter preset storing a list of suppressed rule source IRIs.

**API endpoints (FastAPI):**

- `POST /lint/suppress` — Add rule type suppression
- `DELETE /lint/suppress/{id}` — Remove suppression
- `GET /lint/suppressions` — List active suppressions
- `POST /lint/dismiss` — Dismiss individual result
- `DELETE /lint/dismiss/{id}` — Un-dismiss
- `GET /lint/dismissals` — List active dismissals
- `POST /lint/presets` — Create preset
- `GET /lint/presets` — List presets
- `PUT /lint/presets/{id}` — Update preset
- `DELETE /lint/presets/{id}` — Delete preset
- `POST /lint/presets/{id}/apply` — Apply preset (set active suppressions to match preset)
- `DELETE /lint/suppressions/all` — Clear all suppressions
- `DELETE /lint/dismissals/all` — Clear all dismissals

**Frontend (htmx + vanilla JS):**

- Lint panel gets filter controls: dropdown/checkboxes for rule type suppression, "dismiss" button per result
- Lint settings page (new tab or section in admin) for managing suppressions, dismissals, presets
- Preset selector (dropdown) in lint panel header

**Filtering logic:**

The `LintService` result queries must be extended to exclude:
1. Results whose `sh:sourceShape` IRI is in the user's suppression list
2. Results whose (object IRI, source shape IRI) pair is in the user's dismissal list

This can be done either:
- **Server-side** — LintService accepts suppressed/dismissed lists and applies Python-side filtering after querying results from triplestore. Simpler, works with existing SPARQL.
- **Client-side** — Return all results, filter in JS. Simpler backend but wastes bandwidth.

**Recommendation: Server-side filtering** in Python after the SPARQL query returns. The SPARQL queries for lint results are already complex; adding SQL-sourced filter lists to SPARQL would require cross-database joins (impossible). Python post-filtering is clean and performant for typical result sets (~50-200 results).

### Build Order

1. **Pipeline fix first** — Unblocks everything. Without it, no rules fire. ~30 minutes of code changes + verification in Docker.

2. **Data quality rules second** — Can be developed and tested offline (pytest + pyshacl, no Docker). Each rule is independent. Cross-model placement decision must be made first.

3. **Lint filter system third** — Depends on lint panel showing real results (from steps 1+2) to be meaningful. Largest slice by effort.

4. **E2E + docs last** — Proves the full acceptance criteria end-to-end.

### Verification Approach

**Pipeline fix verification:**
1. Start Docker stack
2. Install basic-pkm (auto-installs)
3. Create a task with dueDate in the past and status "todo"
4. Trigger validation (happens automatically on object create)
5. Check lint panel — should show "overdue task" warning
6. This proves: rules graph loaded + advanced=True + SPARQLConstraint fires + result appears in UI

**Data quality rule verification:**
1. Offline pytest tests per rule — load model shapes+rules into pyshacl with test data graph
2. Each test creates minimal RDF with a violation, runs pyshacl, asserts warning/info result
3. Follow `test_basic_pkm_v2.py` and `test_cross_model_validation.py` patterns

**Lint filter verification:**
1. Backend unit tests for suppression/dismissal/preset CRUD
2. Browser-level testing: suppress a rule → results disappear; dismiss specific result → only that one disappears; save preset → switch away → switch back → same state

## Constraints

- pyshacl `advanced=True` is required for SPARQLConstraint rules — without it, sh:sparql blocks are silently ignored
- `model_shapes_loader()` currently returns only shapes graphs; rules graphs are stored separately at `urn:sempkm:model:{id}:rules`
- SPARQL date arithmetic limited by rdflib — K001 pattern (`STRDT(SUBSTR(...)...)`) required for date comparisons
- Lint filter storage must be in SQLite (not RDF) — user preferences, not knowledge graph data
- Frontend is htmx + vanilla JS — no React/Vue for filter UI
- Cross-model rules cannot easily target "all types" in SHACL without broad patterns like `rdfs:Resource` or `sh:targetSubjectsOf`

## Common Pitfalls

- **pyshacl `advanced=True` changes behavior** — With `advanced=True`, pyshacl also processes `sh:TripleRule` and `sh:SPARQLRule` for inference. The existing inference pipeline (`InferenceService`) runs pyshacl separately with `advanced=True` for inference. Running validation with `advanced=True` means inference rules in the shapes+rules graph will ALSO fire during validation. This is fine because inference rules produce new triples (which are discarded after validation) and validation rules produce violations/warnings. But verify that inference rules don't cause unexpected validation side effects.

- **Orphan detection performance** — A `NOT EXISTS` pattern scanning the full graph for objects with zero edges could be expensive on 1000+ objects. May need to be an on-demand SavedQuery rather than a SHACL rule that fires on every edit. Measure with Ideaverse-scale data (900 objects).

- **Mixed shapes+rules in one graph** — `model_shapes_loader()` will now return a merged graph of all shapes AND all rules. pyshacl handles this correctly — it separates `sh:NodeShape` with `sh:targetClass` (shapes) from those with `sh:sparql` (validation rules) and `sh:rule` (inference rules). But the function name `shapes_loader` becomes misleading.

- **Lint filter state vs. result identity** — Suppressions reference rule source shape IRIs (stable across validation runs). Dismissals reference (object IRI, rule source shape IRI) pairs. The source shape IRI is the `sh:sourceShape` value in the validation report. Verify that the lint service exposes this value to the frontend.

## Open Risks

- **Validation performance with rules enabled.** Adding `advanced=True` and loading rules alongside shapes may increase validation time. With ~1000 objects and 20+ rules, pyshacl could take 5-15 seconds. Need to measure during S01 and possibly add an async indicator or timeout.

- **Orphan object rule may be too expensive.** A `NOT EXISTS` pattern for "no edges" requires scanning the entire graph. Consider making it a SavedQuery (on-demand) rather than a validation rule (runs on every edit).

- **Cross-model rule placement.** Attaching cross-model rules to basic-pkm works only because basic-pkm is always installed. If a user removes basic-pkm (unlikely but possible since it's the starter model), cross-model rules disappear. A platform rules graph (Option A) is more robust but requires loader changes.

## Sources

- Existing codebase: `backend/app/services/validation.py`, `backend/app/services/models.py`, `backend/app/validation/`, `backend/app/lint/`
- Existing rules: `models/*/rules/*.ttl` (5 files with 11 SPARQLConstraint rules)
- Existing tests: `backend/tests/test_cross_model_validation.py`, `backend/tests/test_basic_pkm_v2.py`
- Project knowledge: K001 (rdflib date arithmetic limitation), D153 (separate validation-only NodeShapes)
- pyshacl documentation for `advanced=True` parameter behavior
