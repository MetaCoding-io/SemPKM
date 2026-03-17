# S05: Cross-Model Verification, E2E Tests & User Guide — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

S05 is the integration and documentation capstone for M011. It has three deliverables: (1) a cross-model offline validation test proving all 4 models coexist without namespace conflicts, (2) E2E Playwright tests exercising the Docker install → object creation → form rendering → view rendering cycle per model, and (3) a user guide chapter (Chapter 29) documenting each model. All code patterns exist in the codebase — S05 applies them, it doesn't invent them.

**Critical prerequisite:** The CRM model files exist in the worktree (`.gsd/worktrees/M011/models/crm/`) but are untracked. They must be committed to the main working tree's `models/crm/` before Docker tests or offline cross-model tests can reference them. The other 3 models (basic-pkm v2, zettelkasten, research) are already committed and pass `validate_archive()` with 0 errors.

The work is straightforward — all E2E patterns are established (model lifecycle in `admin-model-lifecycle.spec.ts`, object creation in `create-object.spec.ts`, inference in `inference.spec.ts`, lint panel in `lint-panel.spec.ts`), the offline validation pipeline is proven in `test_basic_pkm_v2.py`, and the user guide follows a consistent chapter format with prev/next navigation links. No new platform code, no new libraries, no architectural decisions needed.

## Recommendation

**Approach:** Four tasks in order — (1) commit CRM model files from worktree to main, (2) write cross-model offline validation pytest, (3) write E2E Playwright test spec, (4) write user guide Chapter 29.

**Why this order:**
1. CRM file commit is a prerequisite for everything else — tests can't reference a model that doesn't exist on disk.
2. Offline validation proves model coexistence before Docker deployment — fast feedback loop.
3. E2E tests require a running Docker stack and are slower — do after offline passes.
4. User guide is pure documentation with no dependencies on test results.

Tasks 3 and 4 are independent of each other and could be parallelized.

## Implementation Landscape

### Key Files

**Files to create:**
- `models/crm/manifest.yaml` — Copy from `.gsd/worktrees/M011/models/crm/manifest.yaml` (already validated offline)
- `models/crm/ontology/crm.jsonld` — Copy from worktree
- `models/crm/shapes/crm.jsonld` — Copy from worktree
- `models/crm/views/crm.jsonld` — Copy from worktree
- `models/crm/rules/crm.ttl` — Copy from worktree
- `models/crm/seed/crm.jsonld` — Copy from worktree
- `backend/tests/test_cross_model_validation.py` — Cross-model offline validation test
- `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` — E2E tests for all 4 models
- `docs/guide/29-mental-model-catalog.md` — User guide chapter documenting all 4 new/upgraded models

**Files to modify:**
- `docs/guide/README.md` — Add Chapter 29 to TOC
- `docs/guide/28-dashboards-and-workflows.md` — Update "Next:" navigation link
- `docs/guide/appendix-d-glossary.md` — Add glossary entries for new model types

**Existing references (follow these patterns):**
- `backend/tests/test_basic_pkm_v2.py` — Offline validation test pattern (266 lines, 10 tests). Use as template for cross-model test.
- `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` — Model install/uninstall E2E pattern. Uses `ownerPage`, `ownerRequest`, `#model-path` input, and `waitForIdle`.
- `e2e/tests/01-objects/create-object.spec.ts` — Object creation via dockview `addPanel` with type IRI.
- `e2e/tests/09-inference/inference.spec.ts` — Inference run + inverse triple verification via API.
- `e2e/tests/04-validation/lint-panel.spec.ts` — Lint panel rendering and validation results via API.
- `e2e/fixtures/seed-data.ts` — Seed data constants (`SEED`, `TYPES`). Will need model-specific equivalents.
- `e2e/fixtures/auth.ts` — Auth fixtures: `ownerPage`, `ownerRequest`, `ownerSessionToken`, `BASE_URL`.
- `e2e/helpers/selectors.ts` — `SEL` object with CSS selectors for all test targets.
- `e2e/helpers/wait-for.ts` — `waitForIdle`, `waitForWorkspace`, `waitForElement`.
- `e2e/helpers/dockview.ts` — `openObjectTab` helper.
- `docs/guide/28-dashboards-and-workflows.md` — Most recent chapter, navigation chain target.

### Build Order

1. **Commit CRM model files** — Copy 6 files from worktree to `models/crm/`. Run `validate_archive()` to confirm. This unblocks everything.

2. **Cross-model offline validation test** (`backend/tests/test_cross_model_validation.py`) — Prove:
   - All 4 models parse, load, and validate with 0 errors independently
   - No namespace collisions across all 4 models (each uses distinct `urn:sempkm:model:{id}:`)
   - Combined graph merge doesn't produce RDF parse errors (simulates co-installation)
   - pyshacl fires correct validation warnings for each model's seed data
   Pattern: module-scoped fixtures for manifest/archive loading (same as `test_basic_pkm_v2.py`).

3. **E2E Playwright test** (`e2e/tests/26-mental-models/mental-model-expansion.spec.ts`) — Single `test.describe` with sequential tests (shared Docker state):
   - Install CRM, zettelkasten, research models (basic-pkm already installed by setup)
   - Refresh basic-pkm to v2.0 (tests upgrade path)
   - Create one object of each new type via API (faster than UI)
   - Verify SHACL forms render via UI (open object in edit mode, check form labels exist)
   - Run inference and verify it completes
   - Check lint API returns results for seed objects with trigger data
   - Cleanup: uninstall CRM, zettelkasten, research (leave basic-pkm)
   Model install path in Docker: `/app/models/{modelId}` (volume-mounted from `./models/`).

4. **User guide Chapter 29** (`docs/guide/29-mental-model-catalog.md`) — Document:
   - basic-pkm v2.0 (Task, Milestone types — what's new, field reference, queries)
   - Personal CRM (Contact, Company, Interaction, Deal — pipeline concept, relationship diagram)
   - Zettelkasten+ (5 note types — provenance chain, argumentation links)
   - Research Workflow (Paper, Claim, Evidence — confidence levels, evidence tracking)
   - Installation instructions per model
   - Recommended dashboard configurations (per D150 — can't bundle, document instead)
   Update README.md TOC, chapter navigation links, and glossary.

### Verification Approach

**Offline validation test:**
```bash
cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v
```
Must pass all tests with 0 errors. Key assertions: each model is_valid=True, no namespace collisions, pyshacl warnings fire for trigger data.

**E2E tests:**
```bash
cd e2e && npx playwright test tests/26-mental-models/ --project=chromium
```
Requires Docker test stack running: `docker compose -f docker-compose.test.yml up -d`

**User guide:**
- Chapter file exists at `docs/guide/29-mental-model-catalog.md`
- README.md TOC includes Chapter 29
- Navigation links: Ch. 28 → Ch. 29 → Appendix A
- Glossary updated with new type definitions

## Constraints

- **Docker test stack runs on port 3901** — uses `docker-compose.test.yml` with `./models:/app/models:ro` volume mount. All 4 model directories must exist and be populated before starting the stack.
- **E2E tests run sequentially with a single worker** — shared Docker state means tests must be ordered: install first, create objects, verify, then cleanup. Use a single `test.describe` with ordered `test()` calls.
- **Rate limit: 5 magic-link requests per minute** — use a single `ownerPage` fixture with one login. Keep all tests in one `test.describe` or use the existing auth fixture pattern.
- **Models are mounted read-only** — `./models:/app/models:ro` means the install endpoint reads from `/app/models/{id}` inside the container. Models must be on disk before `docker compose up`.
- **CRM model is untracked** — The 6 CRM files exist in `.gsd/worktrees/M011/models/crm/` but are not committed to the main branch. They must be copied to `models/crm/` and committed before Docker or offline tests can reference them.

## Common Pitfalls

- **E2E model install waits** — Model installation triggers triplestore writes + seed data loading which can take 3-10 seconds. Use `waitForTimeout(5000)` after install click, then `waitForIdle(ownerPage)` before proceeding, per the pattern in `admin-model-lifecycle.spec.ts`.
- **SHACL form detection** — After opening an object in edit mode, the form loads asynchronously inside a flip card. Use `waitForSelector('[data-testid="object-form"]', { state: 'attached' })` per the `create-object.spec.ts` pattern, not `{ state: 'visible' }`.
- **Type IRI encoding in URLs** — Type IRIs like `urn:sempkm:model:crm:Contact` must be `encodeURIComponent()`-encoded when passed as query params. The `create-object.spec.ts` already demonstrates this pattern.
- **Model uninstall requires no user data** — If any user-created objects of a model's types exist, the DELETE endpoint will fail. Clean up created test objects via SPARQL DELETE before uninstalling, per the `cleanupPpvInstances()` pattern in `admin-model-lifecycle.spec.ts`.
- **Cross-model offline test must handle CRM path** — If CRM files aren't committed yet, the test will fail with FileNotFoundError. Make CRM commit the first task.

## Open Risks

- **CRM model files are untracked** — This is the only real risk. If the worktree CRM files have issues that weren't caught by the S02 validation (unlikely given the S02 summary confirms all checks passed), they'll surface during the copy + offline validation step.
- **E2E test flakiness** — Model install involves triplestore writes that can vary in timing. The established pattern (generous `waitForTimeout` + `waitForIdle`) should handle this, but new models with more seed data may need longer waits.
