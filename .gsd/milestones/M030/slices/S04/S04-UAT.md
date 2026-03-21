# S04: E2E Tests & User Guide — UAT

**Milestone:** M030
**Written:** 2026-03-21

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for E2E tests)
- Why this mode is sufficient: E2E tests run against Docker test stack proving the full M030 pipeline. Docs are static content verifiable by inspection.

## Preconditions

- Docker test stack running (`docker compose -f docker-compose.test.yml up -d` from project root)
- API healthy (`curl http://localhost:3901/api/health` returns 200)
- basic-pkm model installed (seed data present)
- Alembic migration 015 applied (lint_suppressions, lint_dismissals, lint_presets tables exist)
- Node.js and Playwright installed in `e2e/` directory

## Smoke Test

Run `cd e2e && npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts --reporter=list --project=chromium` — all 7 tests should pass in under 30 seconds.

## Test Cases

### 1. E2E test suite passes

1. `cd e2e && npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts --reporter=list --project=chromium`
2. **Expected:** All 7 tests pass — setup, create+validate, suppress, dismiss, preset cycle, settings UI, cleanup.

### 2. Data quality rules fire after object creation

1. Create a Note with no body: `curl -X POST http://localhost:3901/api/commands -H "Cookie: sempkm_session=<token>" -H "Content-Type: application/json" -d '{"type":"object.create","params":{"type_iri":"urn:sempkm:model:basic-pkm:Note","properties":{"dcterms:title":"Test Note"}}}'`
2. Wait 15-20 seconds for validation to run.
3. `curl http://localhost:3901/api/lint/results -H "Cookie: sempkm_session=<token>"`
4. **Expected:** Results include at least one entry with `source_shape` containing "EmptyBody" for the created Note.

### 3. Suppress rule type hides results

1. Get the source_shape IRI of a rule from the lint results (e.g., the EmptyBody IRI).
2. `curl -X POST http://localhost:3901/api/lint/suppress -H "Cookie: sempkm_session=<token>" -H "Content-Type: application/json" -d '{"source_shape":"<the_iri>"}'`
3. `curl http://localhost:3901/api/lint/results -H "Cookie: sempkm_session=<token>"`
4. **Expected:** No results with the suppressed source_shape appear. Other rule results still visible.

### 4. Dismiss specific result hides only that (object, rule) pair

1. Find a lint result for a specific object+rule.
2. `curl -X POST http://localhost:3901/api/lint/dismiss -H "Cookie: sempkm_session=<token>" -H "Content-Type: application/json" -d '{"focus_node":"<object_iri>","source_shape":"<rule_iri>"}'`
3. `curl http://localhost:3901/api/lint/results -H "Cookie: sempkm_session=<token>"`
4. **Expected:** The dismissed (object, rule) pair is absent. Same rule on other objects still shows. Other rules on same object still show.

### 5. Preset save and apply cycle

1. Suppress a rule type (per test case 3).
2. `curl -X POST http://localhost:3901/api/lint/presets -H "Cookie: sempkm_session=<token>" -H "Content-Type: application/json" -d '{"name":"Test Preset"}'` — saves current suppressions.
3. `curl -X DELETE http://localhost:3901/api/lint/suppressions -H "Cookie: sempkm_session=<token>"` — clears all suppressions.
4. `curl http://localhost:3901/api/lint/results -H "Cookie: sempkm_session=<token>"` — previously suppressed results reappear.
5. Get preset ID from `curl http://localhost:3901/api/lint/presets -H "Cookie: sempkm_session=<token>"`.
6. `curl -X POST http://localhost:3901/api/lint/presets/<id>/apply -H "Cookie: sempkm_session=<token>"` — applies the saved preset.
7. `curl http://localhost:3901/api/lint/results -H "Cookie: sempkm_session=<token>"`
8. **Expected:** Suppressed results are hidden again after preset apply.

### 6. Lint settings management UI

1. Navigate to `http://localhost:3901/browser/` and log in.
2. Open the bottom panel and click the Lint tab.
3. Click "Manage Filters" (or equivalent settings link).
4. **Expected:** Settings section shows Suppressions, Dismissals, and Presets subsections with counts and individual items listed. Each item has a remove action.

### 7. Chapter 14 documentation content

1. Open `docs/guide/14-system-health-and-debugging.md`.
2. Search for the 5 section headings: "Data Quality Rules", "Suppressing Rule Types", "Dismissing Individual Results", "Filter Presets", "Lint Settings".
3. **Expected:** All 5 sections present with substantive content — rules table has 11 rows, each section has workflow description.

### 8. Glossary entries

1. Open `docs/guide/appendix-d-glossary.md`.
2. Search for "Data Quality Rules", "Lint Dismissal", "Lint Preset", "Lint Suppression".
3. **Expected:** All 4 entries present in alphabetical order with definitions. Existing "Lint Dashboard" entry updated to mention filtering.

## Edge Cases

### Stale filter state from prior run

1. Run the E2E test twice without manual cleanup.
2. **Expected:** Setup test (test 1) clears stale suppressions/dismissals/presets, so second run passes cleanly.

### Validation timing under load

1. Create 3+ objects rapidly via API.
2. Check lint results after 30 seconds.
3. **Expected:** All objects eventually produce validation results. Polling with source_shape match handles variable timing.

## Failure Signals

- E2E test fails at "create objects" step → validation pipeline not working (S01 regression)
- E2E test fails at "suppress" step → lint filter API not working (S03 regression)
- E2E test fails at "settings UI" → lint settings template or route broken
- Chapter 14 < 550 lines → documentation sections missing
- Glossary grep returns < 4 → glossary entries missing

## Requirements Proved By This UAT

- M030 acceptance criteria (pipeline fix, data quality rules, filter CRUD) proven end-to-end by E2E test
- User guide documentation complete for all M030 user-facing features

## Not Proven By This UAT

- Firefox browser compatibility (Chromium only in E2E)
- Performance under load (>1000 objects with all rules active)
- Triplestore cleanup of test objects (objects accumulate)

## Notes for Tester

- The Docker test stack must have migration 015 applied. If the image was built before S03, copy `backend/migrations/versions/015_lint_filters.py` into the container and run `alembic upgrade head`.
- E2E tests create Notes in the triplestore that are not cleaned up. This is harmless but adds clutter over many runs.
- The polling loop for validation results waits up to 30s — this is normal, not a hang. Validation runs sequentially after each object creation.
