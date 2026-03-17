# S05: Cross-Model Verification, E2E Tests & User Guide — UAT

**Milestone:** M011
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for offline tests + docs, live-runtime for E2E)
- Why this mode is sufficient: Offline tests prove model coexistence without Docker. E2E tests prove Docker lifecycle. Documentation is artifact-verifiable. No human judgment needed beyond what automated tests cover.

## Preconditions

- Backend Python venv available at `backend/.venv/`
- All 4 model directories present: `models/basic-pkm/`, `models/crm/`, `models/zettelkasten/`, `models/research/`
- For E2E tests: Docker test stack running on port 3901 (started from appropriate worktree with model files copied)
- For docs verification: `docs/guide/` directory accessible

## Smoke Test

Run `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v` — all 10 tests pass in <2s. If this fails, stop — the models have a fundamental validation issue.

## Test Cases

### 1. All 4 models parse and validate independently

1. `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py::test_model_parses_and_validates -v`
2. **Expected:** 4 parametrized tests pass — basic-pkm, crm, zettelkasten, research all show `Valid=True Errors=0`

### 2. No namespace collisions across models

1. `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py::test_no_namespace_collisions -v`
2. **Expected:** Test passes — all 4 model namespaces (bpkm, crm, zk, rw) are distinct

### 3. Combined graph merge succeeds

1. `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py::test_combined_graph_merge -v`
2. **Expected:** Merged graph of all 4 models' ontology+shapes+seed has more triples than any individual model

### 4. pyshacl fires correct warnings per model

1. `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -k pyshacl -v`
2. **Expected:**
   - basic-pkm: 1 Warning, 0 Info (overdue task)
   - CRM: 2 Warnings, 0 Info (stale contacts)
   - zettelkasten: 2 Warnings, 1 Info (unprocessed notes + info-level)
   - research: 2 Warnings, 2 Info (unsupported/contested claims)

### 5. E2E model installation via UI

1. Start Docker test stack: `docker compose -f docker-compose.test.yml up -d`
2. `cd e2e && npx playwright test tests/26-mental-models/ --project=chromium`
3. **Expected:** Test passes in <30s. Steps verified:
   - CRM, Zettelkasten, Research models installed via admin UI form
   - basic-pkm refreshed to v2.0 via API
   - 8 objects created (Task, Milestone, Contact, Company, FleetingNote, PermanentNote, Paper, Claim)
   - SHACL forms render for 4 objects (editor area has content)
   - Inference API returns successful response with total_inferred and run_timestamp
   - Lint API returns results for 4 seed objects with trigger data

### 6. Chapter 29 exists with complete content

1. `wc -l docs/guide/29-mental-model-catalog.md`
2. **Expected:** 600+ lines
3. `grep -c "^## " docs/guide/29-mental-model-catalog.md`
4. **Expected:** At least 4 (one section per model)
5. Verify each model section has field reference tables: `grep -c "| Field" docs/guide/29-mental-model-catalog.md`
6. **Expected:** At least 4 tables

### 7. TOC and navigation chain

1. `grep "29-mental-model-catalog" docs/guide/README.md`
2. **Expected:** Chapter 29 listed in Part VIII of the TOC
3. `tail -3 docs/guide/28-dashboards-and-workflows.md`
4. **Expected:** "Next:" link points to Chapter 29
5. `head -5 docs/guide/29-mental-model-catalog.md` then check footer
6. **Expected:** "Previous:" link to Chapter 28, "Next:" link to Appendix A

### 8. Glossary entries

1. `grep "Chapter 29" docs/guide/appendix-d-glossary.md | wc -l`
2. **Expected:** At least 12 entries (Task, Milestone, Contact, Company, Interaction, Deal, FleetingNote, PermanentNote, StructureNote, Paper, Claim, Evidence)

## Edge Cases

### CRM model files match worktree originals

1. `diff -r models/crm/ .gsd/worktrees/M011/models/crm/`
2. **Expected:** No differences — files are binary-identical copies

### E2E test is idempotent

1. Run the E2E test twice against the same Docker stack without resetting
2. **Expected:** Second run succeeds — skip-if-already-installed logic prevents duplicate install errors. Cleanup messages may appear about seed data blocking removal.

### Offline tests work without Docker

1. Stop Docker stack entirely
2. `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v`
3. **Expected:** All 10 tests pass — offline validation uses only rdflib and pyshacl, no triplestore connection

## Failure Signals

- `test_model_parses_and_validates` fails → model archive has structural error (missing file, bad manifest, invalid JSON-LD/Turtle)
- `test_no_namespace_collisions` fails → two models accidentally share a namespace prefix
- `test_pyshacl_*_warnings` fails with wrong count → SHACL-AF rule changed or seed data changed; full `results_text` printed on failure shows focus nodes and messages
- E2E test fails at install step → model files not present in Docker container's mounted volume
- E2E test fails at form render step → SHACL shapes don't generate form fields for the type
- E2E test fails at inference step → inference API endpoint changed or times out
- Chapter 29 missing → docs/guide/29-mental-model-catalog.md not created
- Navigation chain broken → Chapter 28 footer still points to Appendix A instead of Chapter 29

## Requirements Proved By This UAT

- MODEL-01 — basic-pkm v2.0 upgrade via refresh_artifacts works in Docker, forms render, inference fires, validation warnings appear
- MODEL-02 — CRM model installs from scratch, forms render for Contact/Company types, inference fires, stale-contact warnings from lint API
- MODEL-03 — Zettelkasten+ model installs, forms render for FleetingNote/PermanentNote types, inference fires, unprocessed-note warnings from lint API
- MODEL-04 — Research Workflow model installs, forms render for Paper/Claim types, inference fires, unsupported-claim warnings from lint API

## Not Proven By This UAT

- ViewSpec rendering (Table/Cards/Graph views with seed data) — E2E test creates objects and checks forms but doesn't navigate to view tabs
- Saved query execution — queries are defined in model views but not exercised in E2E test
- owl:inverseOf inference materialization verification — inference runs but specific inverse triple creation isn't asserted in E2E
- Dashboard configuration after model install — only documented as recommended configs in Chapter 29
- Multi-model concurrent inference correctness — inference runs once covering all models but individual rule firing not verified in E2E

## Notes for Tester

- The E2E test is a single consolidated test (not multiple independent tests) to stay within the magic-link rate limit for authentication. If you need to debug a specific step, look at the step-by-step output with `--reporter=list`.
- Model cleanup at the end is best-effort. If you see "Could not remove CRM (seed data exists)" in console output, that's expected — the API doesn't support SPARQL UPDATE to delete seed instances.
- The offline pytest tests are the fastest verification path (<1s). Run those first before spinning up Docker for E2E.
- pyshacl warning counts are sensitive to seed data changes. If a model's seed data is modified in a future slice, the expected counts in `test_cross_model_validation.py` may need updating.
