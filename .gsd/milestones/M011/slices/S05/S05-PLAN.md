# S05: Cross-Model Verification, E2E Tests & User Guide

**Goal:** Prove all 4 M011 models (basic-pkm v2, CRM, Zettelkasten+, Research Workflow) coexist without conflicts, pass E2E Playwright tests covering install → create → view cycles, and document all models in user guide Chapter 29.

**Demo:** `pytest tests/test_cross_model_validation.py -v` passes (all 4 models validate, no namespace collisions, pyshacl rules fire), `npx playwright test tests/26-mental-models/` passes against Docker stack (model install + object creation + form rendering + inference + validation), Chapter 29 appears in the guide TOC with navigation links.

## Must-Haves

- CRM model files (6 files) committed from worktree to `models/crm/`
- Cross-model offline validation pytest proves all 4 models parse, load, validate independently + coexist
- Namespace collision test confirms no IRI prefix overlaps across models
- pyshacl fires correct validation warnings for each model's trigger data
- E2E Playwright spec covers: install 3 new models, refresh basic-pkm v2, create objects via API, verify forms render, run inference, check lint API, cleanup
- User guide Chapter 29 documents all 4 models with type descriptions, installation, and field reference
- README.md TOC updated, navigation chain intact (Ch. 28 → Ch. 29 → Appendix A), glossary updated

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker for E2E)
- Human/UAT required: no (E2E tests substitute)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v` — all tests pass, 0 errors
- `cd e2e && npx playwright test tests/26-mental-models/ --project=chromium` — all tests pass (requires Docker test stack on port 3901)
- `test -f docs/guide/29-mental-model-catalog.md` — chapter file exists
- `grep "29-mental-model-catalog" docs/guide/README.md` — listed in TOC
- `tail -1 docs/guide/28-dashboards-and-workflows.md` contains `29-mental-model-catalog` — navigation chain intact

## Observability / Diagnostics

- Runtime signals: pytest test output (pass/fail per model), Playwright test reporter (pass/fail per step)
- Inspection surfaces: `backend/tests/test_cross_model_validation.py` for offline, `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` for Docker
- Failure visibility: pytest prints pyshacl violation details (focus node, severity, message); Playwright captures screenshots on failure
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `models/basic-pkm/` (S01), `models/crm/` (S02, files from worktree), `models/zettelkasten/` (S03), `models/research/` (S04), manifest/loader/validator pipeline (`app.models.*`), E2E auth fixtures, wait helpers, selectors
- New wiring introduced in this slice: none — pure testing and documentation
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [ ] **T01: Commit CRM model files and write cross-model offline validation test** `est:45m`
  - Why: CRM model files exist only in the worktree — they must be committed to the main tree for Docker and offline tests to reference them. The cross-model test proves all 4 models coexist without namespace conflicts and validates each model's SHACL-AF rules fire correctly.
  - Files: `models/crm/manifest.yaml`, `models/crm/ontology/crm.jsonld`, `models/crm/shapes/crm.jsonld`, `models/crm/views/crm.jsonld`, `models/crm/rules/crm.ttl`, `models/crm/seed/crm.jsonld`, `backend/tests/test_cross_model_validation.py`
  - Do: Copy 6 CRM files from `.gsd/worktrees/M011/models/crm/` to `models/crm/`. Write pytest module with module-scoped fixtures for all 4 models. Test cases: each model parses/loads/validates independently; no namespace prefix collisions; combined graph merge doesn't error; pyshacl fires correct warnings per model (basic-pkm: 1 Warning, CRM: 2 Warnings, zettelkasten: 2 Warning + 1 Info, research: 2 Warning + 2 Info).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v`
  - Done when: All cross-model validation tests pass with 0 errors

- [ ] **T02: Write E2E Playwright test for mental model expansion** `est:1h`
  - Why: Proves the full Docker lifecycle — model install, object creation via API, SHACL form rendering in UI, inference, and validation — for all 4 M011 models. This is the integration verification that retires MODEL-01 through MODEL-04.
  - Files: `e2e/tests/26-mental-models/mental-model-expansion.spec.ts`
  - Do: Create single `test.describe` with sequential ordered tests sharing Docker state. Steps: (1) install CRM, zettelkasten, research models via UI form, (2) refresh basic-pkm via API, (3) create one object per new type via Command API, (4) open objects in edit mode and verify form labels render, (5) run inference via API and verify completion, (6) check lint API returns results for objects with trigger data, (7) cleanup — delete created objects and uninstall CRM/zettelkasten/research. Follow patterns from `admin-model-lifecycle.spec.ts` (install), `inference.spec.ts` (API run), `lint-panel.spec.ts` (lint API).
  - Verify: `cd e2e && npx playwright test tests/26-mental-models/ --project=chromium` (requires Docker test stack)
  - Done when: All E2E tests pass against running Docker test stack

- [ ] **T03: Write user guide Chapter 29 (Mental Model Catalog) and update navigation** `est:45m`
  - Why: Documents all 4 new/upgraded models for end users — type descriptions, field reference, installation, recommended dashboard configurations. Completes the milestone's documentation requirement.
  - Files: `docs/guide/29-mental-model-catalog.md`, `docs/guide/README.md`, `docs/guide/28-dashboards-and-workflows.md`, `docs/guide/appendix-d-glossary.md`
  - Do: Write Chapter 29 with 4 sections (basic-pkm v2, CRM, Zettelkasten+, Research Workflow), each covering types/fields, relationships, installation, saved queries, and recommended dashboards. Update README TOC to add Ch. 29. Update Ch. 28 nav link to point to Ch. 29. Update Appendix D with glossary entries for new types (Task, Milestone, Contact, Company, Interaction, Deal, FleetingNote, PermanentNote, StructureNote, Paper, Claim, Evidence).
  - Verify: `test -f docs/guide/29-mental-model-catalog.md && grep "29-mental-model-catalog" docs/guide/README.md && grep "29-mental-model-catalog" docs/guide/28-dashboards-and-workflows.md`
  - Done when: Chapter exists, TOC updated, navigation chain Ch. 28 → Ch. 29 → Appendix A, glossary has new entries

## Files Likely Touched

- `models/crm/manifest.yaml` (copy from worktree)
- `models/crm/ontology/crm.jsonld` (copy from worktree)
- `models/crm/shapes/crm.jsonld` (copy from worktree)
- `models/crm/views/crm.jsonld` (copy from worktree)
- `models/crm/rules/crm.ttl` (copy from worktree)
- `models/crm/seed/crm.jsonld` (copy from worktree)
- `backend/tests/test_cross_model_validation.py` (new)
- `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` (new)
- `docs/guide/29-mental-model-catalog.md` (new)
- `docs/guide/README.md` (update TOC)
- `docs/guide/28-dashboards-and-workflows.md` (update nav link)
- `docs/guide/appendix-d-glossary.md` (add entries)
