---
id: S05
parent: M011
milestone: M011
provides:
  - Cross-model offline validation test proving all 4 M011 models coexist (10 pytest tests)
  - E2E Playwright test proving Docker install → create → form render → inference → lint cycle for all models
  - User guide Chapter 29 (Mental Model Catalog) with field references, relationships, saved queries, validation rules, and installation instructions
  - 15 glossary entries for new model types
  - CRM model files committed from worktree to main tree
requires:
  - slice: S01
    provides: basic-pkm v2.0 archive (6 types, Task/Milestone added)
  - slice: S02
    provides: CRM model archive (Contact/Company/Interaction/Deal)
  - slice: S03
    provides: Zettelkasten+ model archive (5 note types, provenance chain)
  - slice: S04
    provides: Research Workflow model archive (5 research types, evidence tracking)
affects: []
key_files:
  - models/crm/ (6 files — manifest, ontology, shapes, views, rules, seed)
  - backend/tests/test_cross_model_validation.py
  - e2e/tests/26-mental-models/mental-model-expansion.spec.ts
  - docs/guide/29-mental-model-catalog.md
  - docs/guide/README.md
  - docs/guide/28-dashboards-and-workflows.md
  - docs/guide/appendix-d-glossary.md
key_decisions:
  - Best-effort E2E cleanup instead of hard assertions — /api/sparql doesn't support SPARQL UPDATE/DELETE so seed data instances can't be removed via API
  - Docker test stack mounts from worktree path — model files must be copied to worktree for E2E tests to see them
patterns_established:
  - Cross-model validation pattern: module-scoped fixtures for manifests/archives dict, parametrized individual validation, helper function for pyshacl execution with expected warning/info counts
  - E2E model lifecycle pattern: UI form install, API object creation, tab open + editor area assertion, inference API, lint API verification
  - User guide model chapter format: type field tables, ASCII relationship diagrams, saved query tables, validation rule tables, installation instructions, recommended dashboard configs
observability_surfaces:
  - "cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v — 10 tests covering parse/validate, namespace, graph merge, pyshacl counts"
  - "cd e2e && npx playwright test tests/26-mental-models/ --project=chromium — 1 test with 7 steps covering full Docker lifecycle"
drill_down_paths:
  - .gsd/milestones/M011/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M011/slices/S05/tasks/T02-SUMMARY.md
  - .gsd/milestones/M011/slices/S05/tasks/T03-SUMMARY.md
duration: ~1h22m
verification_result: passed
completed_at: 2026-03-17
---

# S05: Cross-Model Verification, E2E Tests & User Guide

**All 4 M011 models verified coexisting without conflicts via 10 offline pytest tests and 1 E2E Playwright spec proving Docker install → create → form render → inference → lint; Chapter 29 user guide documents all models with field references and 15 glossary entries.**

## What Happened

Three tasks assembled the final integration layer for M011's 4 mental models:

**T01 — Cross-model offline validation** (12min): Copied 6 CRM model files from the S02 worktree into `models/crm/` (verified binary-identical). Wrote `test_cross_model_validation.py` with 10 tests: 4 parametrized parse+validate tests (one per model), namespace collision check, combined graph merge, and 4 pyshacl warning/info count tests. All 4 models validate independently with zero errors and coexist in a merged graph. pyshacl fires the expected diagnostics: basic-pkm 1W, CRM 2W, zettelkasten 2W+1I, research 2W+2I.

**T02 — E2E Playwright test** (45min): Created `mental-model-expansion.spec.ts` (~294 lines) as a single consolidated test with 7 sequential steps: install 3 new models via UI form, refresh basic-pkm to v2 via API, create 8 objects (one per new type), verify SHACL forms render for 4 objects, run inference via API, check lint API for 4 seed objects with trigger data, and attempt best-effort cleanup. Discovered two runtime constraints documented in KNOWLEDGE.md: the SPARQL API doesn't support UPDATE/DELETE operations, and the Docker test stack mounts volumes from its worktree path (not the main tree).

**T03 — User guide Chapter 29** (25min): Wrote 608-line chapter covering all 4 models with type field reference tables built from actual SHACL shapes, ASCII relationship diagrams, saved query tables, validation rule tables with severity/messages, installation instructions, and recommended dashboard configurations. Updated README.md TOC, Chapter 28 navigation link, and added 15 alphabetically-sorted glossary entries to Appendix D.

## Verification

All slice-level verification checks pass:

- `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v` — **10 passed** in 0.69s
- `test -f e2e/tests/26-mental-models/mental-model-expansion.spec.ts` — **exists** (294 lines)
- E2E test confirmed passing against Docker test stack — **1 passed** in 18.3s
- `test -f docs/guide/29-mental-model-catalog.md` — **exists** (608 lines)
- `grep "29-mental-model-catalog" docs/guide/README.md` — **listed in TOC**
- `grep "29-mental-model-catalog" docs/guide/28-dashboards-and-workflows.md` — **nav chain intact**
- `grep "appendix-a" docs/guide/29-mental-model-catalog.md` — **Ch. 29 → Appendix A link present**
- `grep -c "Chapter 29" docs/guide/appendix-d-glossary.md` — **15 glossary entries**
- All 4 model directories exist: `models/basic-pkm/`, `models/crm/`, `models/zettelkasten/`, `models/research/`

## Requirements Advanced

- MODEL-01 — basic-pkm v2.0 passes cross-model validation, E2E test confirms Docker install via refresh_artifacts + object creation + form rendering + inference + lint
- MODEL-02 — CRM passes cross-model validation, E2E test confirms Docker install + object creation + form rendering + inference + lint
- MODEL-03 — Zettelkasten+ passes cross-model validation, E2E test confirms Docker install + object creation + form rendering + inference + lint
- MODEL-04 — Research Workflow passes cross-model validation, E2E test confirms Docker install + object creation + form rendering + inference + lint

## Requirements Validated

- MODEL-01 — Offline validation (S01) + cross-model coexistence (S05) + E2E Docker lifecycle (S05) + user guide Chapter 29 (S05). All acceptance criteria proven.
- MODEL-02 — Offline validation (S02) + cross-model coexistence (S05) + E2E Docker lifecycle (S05) + user guide Chapter 29 (S05). All acceptance criteria proven.
- MODEL-03 — Offline validation (S03) + cross-model coexistence (S05) + E2E Docker lifecycle (S05) + user guide Chapter 29 (S05). All acceptance criteria proven.
- MODEL-04 — Offline validation (S04) + cross-model coexistence (S05) + E2E Docker lifecycle (S05) + user guide Chapter 29 (S05). All acceptance criteria proven.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **E2E cleanup is best-effort, not hard-asserted**: Plan called for strict cleanup (delete objects, uninstall models). The `/api/sparql` endpoint only supports read queries — SPARQL UPDATE/DELETE returns 400. Models with seed data can't be uninstalled via the API. Skip-if-already-installed logic enables idempotent reruns.
- **Model files copied to M007 worktree**: Docker test stack mounts from `.gsd/worktrees/M007/models/`. CRM, zettelkasten, research, and basic-pkm v2 files had to be copied there for E2E tests to see them.
- **Minor field value corrections in docs**: Chapter 29 used actual values from SHACL shapes (e.g., Milestone status `planned/active/completed/cancelled`) rather than plan-stated values (e.g., `planned/in-progress/completed/cancelled`).

## Known Limitations

- **No SPARQL UPDATE API**: E2E tests cannot clean up triplestore data. Model uninstall is blocked when seed data exists. A force-uninstall admin endpoint or SPARQL UPDATE API would fix this.
- **E2E test requires model dirs in Docker stack's mounted volume**: If the Docker test stack runs from a different worktree, model directories must be present in that worktree's `models/` directory.
- **Dashboard bundling not in model archives**: Per D150, DashboardSpec is SQLite JSON and can't be shipped in `.sempkm-model` archives. Recommended configurations documented in Chapter 29 instead.

## Follow-ups

- Add a SPARQL UPDATE endpoint or force-uninstall admin API to enable proper E2E cleanup
- Consider adding DashboardSpec-to-RDF migration (existing tech debt) to enable dashboard bundling in model archives

## Files Created/Modified

- `models/crm/manifest.yaml` — CRM manifest (copied from worktree)
- `models/crm/ontology/crm.jsonld` — CRM ontology (copied from worktree)
- `models/crm/shapes/crm.jsonld` — CRM shapes (copied from worktree)
- `models/crm/views/crm.jsonld` — CRM views (copied from worktree)
- `models/crm/rules/crm.ttl` — CRM rules (copied from worktree)
- `models/crm/seed/crm.jsonld` — CRM seed data (copied from worktree)
- `backend/tests/test_cross_model_validation.py` — 10-test cross-model validation suite
- `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` — E2E test for full model lifecycle (~294 lines)
- `docs/guide/29-mental-model-catalog.md` — Chapter 29 user guide (608 lines)
- `docs/guide/README.md` — Added Ch. 29 to TOC
- `docs/guide/28-dashboards-and-workflows.md` — Updated nav link to Ch. 29
- `docs/guide/appendix-d-glossary.md` — Added 15 glossary entries

## Forward Intelligence

### What the next slice should know
- M011 is complete. All 4 models are pure `.sempkm-model` archives requiring zero platform code changes (D149). The pipeline for shipping new mental models is fully proven: ontology + shapes + views + rules + seed data in JSON-LD/Turtle, validated offline with pyshacl, tested in Docker with E2E Playwright.
- The SPARQL date arithmetic workaround (Pattern #1 in KNOWLEDGE.md: `STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date)`) is essential for any future model with date-based validation rules.
- K001 (rdflib doesn't implement xsd:dayTimeDuration subtraction) means time-windowed checks must use `NOT EXISTS` in SHACL rules or direct date comparison in SavedQueries.

### What's fragile
- **Docker test stack volume mounts** — The M007 worktree's Docker stack is the only E2E test environment. Model files must be synced there. If a new worktree replaces M007 as the Docker host, all model dirs need copying again.
- **E2E test is skip-if-installed** — Repeated runs against the same Docker stack accumulate installed models that can't be fully cleaned up. A fresh Docker stack gives the cleanest test run.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v` — fastest way to verify all 4 models still coexist. Runs in <1s, no Docker needed.
- pyshacl warning/info counts in the test are the ground truth for SHACL-AF rule correctness. If a model's rules change, update the expected counts in the test.

### What assumptions changed
- **SPARQL API is read-only** — The plan assumed E2E tests could clean up via SPARQL DELETE. In reality, `/api/sparql` only supports SELECT/ASK/CONSTRUCT/DESCRIBE. Cleanup requires a dedicated admin API.
- **Docker stack mounts from worktree** — The plan assumed models in the main tree would be visible to Docker. They're not — Docker mounts from the worktree where `docker compose` was started.
