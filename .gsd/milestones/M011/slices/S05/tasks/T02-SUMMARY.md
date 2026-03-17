---
id: T02
parent: S05
milestone: M011
provides:
  - E2E Playwright test covering full model lifecycle for all 4 M011 models
key_files:
  - e2e/tests/26-mental-models/mental-model-expansion.spec.ts
key_decisions:
  - Best-effort cleanup instead of hard assertions on model uninstall — /api/sparql does not support SPARQL UPDATE/DELETE so seed data instances cannot be removed via the E2E API
  - Single consolidated test() following admin-model-lifecycle pattern to stay within magic-link rate limit
  - Skip-if-already-installed logic for idempotent repeated runs against same Docker stack
patterns_established:
  - Model install via UI form: fill #model-path, click Install, waitForTimeout(5000) + waitForIdle
  - Object creation via POST /api/commands with type IRI and dcterms:title property
  - SHACL form verification: openTab(iri) then assert editorArea not empty
  - Lint API verification: GET /browser/lint/{encodedIri} with HX-Request header
observability_surfaces:
  - Playwright test reporter with step-by-step output and failure screenshots
  - Trace zips in test-results/ for detailed debugging
  - Console.log for cleanup status messages
duration: ~45min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Write E2E Playwright test for mental model expansion

**Created comprehensive E2E test exercising install → create → form render → inference → lint for all 4 M011 models against Docker test stack.**

## What Happened

Wrote `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` (~280 lines) as a single consolidated test covering 7 steps:

1. **Install** CRM, Zettelkasten, Research models via UI form (with pre-clean and skip-if-installed logic)
2. **Refresh** basic-pkm to v2.0 via refresh-artifacts API
3. **Create** 8 objects (one per new type: Task, Milestone, Contact, Company, FleetingNote, PermanentNote, Paper, Claim)
4. **Verify SHACL forms** render for 4 objects (one per model) by opening tabs and asserting editor area has content
5. **Run inference** via API and verify response structure (total_inferred, run_timestamp)
6. **Lint API** verification for 4 seed objects with trigger data (one per model)
7. **Best-effort cleanup** — attempt model removal (logs when blocked by seed data)

Key debugging discovery: The test Docker stack (m007) mounts models from `.gsd/worktrees/M007/models/`, not the main tree. Had to copy CRM/zettelkasten/research/basic-pkm v2 model dirs to the worktree for tests to see them. Also discovered that `/api/sparql` only supports read queries (SELECT/ASK/CONSTRUCT), not SPARQL UPDATE/DELETE, making instance cleanup impossible via the API.

## Verification

- `cd e2e && npx playwright test tests/26-mental-models/ --project=chromium` — **1 passed (18.3s)**
- File exists: `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` ✅
- No TypeScript errors in the file (verified via `npx tsc --noEmit` — 0 errors for this file) ✅
- Steps 1-6 all assert successfully; Step 7 cleanup is best-effort with console logging

## Diagnostics

- Run `cd e2e && npx playwright test tests/26-mental-models/ --project=chromium --reporter=list` for step-by-step output
- On failure: screenshots in `e2e/test-results/26-mental-models-*/test-failed-*.png`
- Trace replay: `npx playwright show-trace e2e/test-results/*/trace.zip`
- Cleanup messages: `Cleanup: Could not remove <model> (seed data exists)` in console output — this is expected when seed data instances block removal

## Deviations

- **Cleanup is best-effort, not hard-asserted**: The plan called for strict cleanup verification (delete objects, uninstall models, verify table). The `/api/sparql` endpoint doesn't support SPARQL UPDATE/DELETE, so seed data instances in `urn:sempkm:current` cannot be removed via the E2E API. Cleanup attempts model removal but doesn't assert success. Added skip-if-already-installed logic so the test is idempotent across repeated runs.
- **Model files copied to M007 worktree**: The Docker test stack mounts from `.gsd/worktrees/M007/models/`. Had to copy CRM, zettelkasten, research, and basic-pkm v2 files there for the test to pass.

## Known Issues

- Model cleanup blocked by seed data: Models with seed objects (all 3 new models) cannot be uninstalled via the API because there's no SPARQL UPDATE endpoint to delete instances from `urn:sempkm:current`. A future task could add a SPARQL UPDATE API or a force-uninstall admin endpoint.
- Test requires model dirs in the Docker stack's mounted volume. If running from a different worktree, model dirs must be present.

## Files Created/Modified

- `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` — E2E test spec covering full model lifecycle for all 4 M011 models (~280 lines)
- `.gsd/milestones/M011/slices/S05/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
