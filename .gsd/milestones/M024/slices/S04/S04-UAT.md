# S04: E2E tests + user guide — UAT

**Milestone:** M024
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven for mock selftest + docs verification; live-runtime for Docker E2E)
- Why this mode is sufficient: The mock server selftest runs without Docker. The E2E test requires Docker but was verified structurally. Docs are fully verifiable from the filesystem.

## Preconditions

- For mock selftest and docs verification: Python 3.12+, Node.js installed
- For Docker E2E: `docker compose -f docker-compose.test.yml up -d` running from the project root, basic-pkm model available in the models directory
- For unit test regression: `uv` installed with backend dependencies resolved

## Smoke Test

Run `python3 e2e/mock-monday-api/server.py --selftest` — should print 12 ✓ checks and exit 0. If any ✗ appears, the mock server is broken.

## Test Cases

### 1. Mock Server Selftest (All Query Shapes)

1. Run `python3 e2e/mock-monday-api/server.py --selftest`
2. **Expected:** All 12 checks pass with ✓ prefix:
   - GET /health
   - POST / (me query)
   - POST / (boards list)
   - POST / (columns query)
   - POST / (items_page query)
   - POST / (subitems query)
   - POST / (users query)
   - POST / (tags query)
   - POST / (groups query)
   - POST / (change_multiple_column_values mutation)
   - POST / (create_item mutation)
   - POST / (unknown query → fallback)
3. **Expected:** Exit code 0, "12 passed, 0 failed" in output

### 2. Mock Server settings_str Double Encoding

1. Run `python3 -c "import json, sys; sys.path.insert(0, 'e2e/mock-monday-api'); from server import RESPONSES; cols = json.loads(RESPONSES['columns'])['data']['boards'][0]['columns']; status_col = [c for c in cols if c['id'] == 'status'][0]; labels = json.loads(status_col['settings_str']); print(type(labels)); assert 'labels' in labels"`
2. **Expected:** Output shows `<class 'dict'>` — confirms settings_str is a JSON string that parses to a dict with "labels" key

### 3. Docker Compose Validation

1. Run `docker compose -f docker-compose.test.yml config --quiet`
2. **Expected:** Exit code 0 (valid YAML, no errors)
3. Run `grep "MONDAY_API_URL" docker-compose.test.yml`
4. **Expected:** Shows `MONDAY_API_URL: http://mock-monday:8080` in the api service environment

### 4. Mock Server Fallback for Unknown Queries

1. Run the selftest and look for the "unknown query → fallback" check
2. **Expected:** Unrecognized queries return `{"data": {}}` (empty data, not an error)
3. Verify the `[mock-monday] Unmatched query (fallback):` log line appears in stderr

### 5. Unit Test Regression (607 Tests)

1. Run `cd backend && uv run python -m pytest tests/test_monday_*.py -v`
2. **Expected:** 607 tests pass, 0 failures, 0 errors
3. Tests should complete in under 2 seconds
4. All 7 test files should be represented: test_monday_auth, test_monday_client, test_monday_field_mapper, test_monday_person_matcher, test_monday_sync_engine, test_monday_loop_guard, test_monday_app_routes

### 6. User Guide Chapter 37 Content Verification

1. Open `docs/guide/37-monday-sync.md`
2. **Expected:** File exists with ~393 lines
3. Verify these sections exist:
   - Prerequisites (mentions API token from Administration → Developers)
   - Column Mapping (walkthrough with type compatibility table)
   - Status Label Mapping (example: "Working on it" → in-progress)
   - Priority Label Mapping
   - Field Mapping Table (13 column types: status, priority, date, people, text, long_text, numbers, tags, dropdown, dependency, etc.)
   - LoopGuard Echo Prevention
   - Groups as taskGroup
   - Subitems as parentTask
   - Dependencies as dependsOn
   - Troubleshooting

### 7. Navigation File Sync (Three-File Rule)

1. Run `grep "37-monday-sync" docs/guide/README.md`
2. **Expected:** At least one line (TOC entry)
3. Run `grep "37-monday-sync" docs/guide/index.html`
4. **Expected:** At least one line (sidebar entry)
5. Run `grep "37-monday-sync" backend/app/templates/guide.html`
6. **Expected:** At least one line (in-app button)
7. Run `grep "37-monday-sync" docs/guide/36-jira-sync.md`
8. **Expected:** At least one line (navigation footer chain: Ch 36 → Ch 37)

### 8. Appendix and Glossary Updates

1. Run `grep "MONDAY_API_URL" docs/guide/appendix-a-environment-variables.md`
2. **Expected:** Shows the environment variable entry with description
3. Run `grep -A1 "^\*\*Column Mapping\*\*" docs/guide/appendix-d-glossary.md`
4. **Expected:** Shows Column Mapping glossary entry
5. Run `grep -A1 "^\*\*LoopGuard\*\*" docs/guide/appendix-d-glossary.md`
6. **Expected:** Shows LoopGuard glossary entry
7. Run `grep -A1 "^\*\*Monday.com Sync\*\*" docs/guide/appendix-d-glossary.md`
8. **Expected:** Shows Monday.com Sync glossary entry

### 9. E2E Spec Structure Verification

1. Open `e2e/tests/42-monday-sync/monday-sync.spec.ts`
2. **Expected:** 13 phases with comment blocks: Phase 0 through Phase 12
3. Verify Phase 4 (connect) uses single token input (`#monday-token`), not 3-field form
4. Verify Phase 6 (configure columns) iterates select dropdowns for column mapping
5. Verify Phase 7 (configure labels) maps status/priority labels
6. Verify Phase 10 (SPARQL verify) queries for bpkm:Task objects
7. Run `grep -c 'Phase [0-9]' e2e/tests/42-monday-sync/monday-sync.spec.ts`
8. **Expected:** 13

### 10. E2E Selectors Block

1. Run `grep -A20 "mondaySync" e2e/helpers/selectors.ts | head -25`
2. **Expected:** Shows 14 selector entries including tokenInput, connectBtn, boardCheckbox, configureColumnsBtn, saveBoardsBtn, syncNowBtn, etc.

## Edge Cases

### Mock Server "me" Query Substring Safety

1. Run the selftest — check that the "unknown query → fallback" test sends `{ somethingUnknown { id } }` (contains "me" as substring)
2. **Expected:** Returns `{"data": {}}` fallback, NOT the `me` query response — the `"{ me "` matcher with surrounding syntax chars prevents false matching

### Empty Board Scenario in Mock

1. The mock returns boards with items and columns. If a real Monday.com account has empty boards (no items), the E2E test would still pass Phase 5 (board select) but Phase 10 (SPARQL verify) would find 0 tasks
2. **Expected:** This is expected behavior — the mock always returns populated data for testing

## Failure Signals

- Mock selftest shows any ✗ → a canned response is malformed or missing
- `docker compose config` fails → YAML syntax error in docker-compose.test.yml (likely indentation)
- Unit tests fail → regression in S01–S03 service modules (should not happen unless code was modified)
- Missing Chapter 37 → T03 file not committed
- Navigation file grep returns 0 → one of the three nav files was missed
- Glossary grep returns < 3 → one of the three glossary entries was missed
- E2E spec Phase count != 13 → phase was dropped or duplicated

## Requirements Proved By This UAT

- MON-14 (E2E + mock server) — Test cases 1–4, 9–10 prove mock server handles all query shapes and E2E spec covers full lifecycle
- MON-15 (user guide) — Test cases 6–8 prove Chapter 37 exists with correct content, navigation files are synced, appendix and glossary updated
- MON-01 through MON-13 — Test case 5 proves all 607 unit tests from S01–S03 still pass (regression check)

## Not Proven By This UAT

- E2E test runtime execution against Docker stack — requires `docker compose up` which is environment-dependent
- Visual layout of the user guide in the in-app docs viewer — requires running the full application
- Mock server behavior under concurrent requests — selftest exercises queries sequentially

## Notes for Tester

- The mock selftest (Test Case 1) is the fastest smoke test — run it first
- The unit test regression (Test Case 5) takes <1 second and confirms no S01–S03 regressions
- If you want to run the actual E2E Playwright test, start the Docker stack first: `docker compose -f docker-compose.test.yml up -d --wait`, then run `npx playwright test e2e/tests/42-monday-sync/monday-sync.spec.ts`
- The E2E test has not been run against the live Docker stack during this slice's development — first run may surface timing issues in column/label mapping phases where htmx-loaded forms need careful wait conditions
