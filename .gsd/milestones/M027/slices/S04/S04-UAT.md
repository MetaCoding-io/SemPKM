# S04: E2E Tests + User Guide — UAT

**Milestone:** M027
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for E2E test)
- Why this mode is sufficient: The E2E Playwright test exercises the full wizard flow against the real Docker stack (live-runtime). Documentation is verifiable by artifact inspection (file existence, content, navigation links).

## Preconditions

- Docker test stack running: `cd /home/james/Code/SemPKM && docker compose -f docker-compose.test.yml up -d`
- Stack healthy: `curl -sf http://localhost:3901/api/health` returns 200
- Playwright installed: `cd e2e && npm install`

## Smoke Test

Run `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium` — all 3 tests pass in <30s.

## Test Cases

### 1. Full wizard E2E flow

1. Navigate to `http://localhost:3901/admin/import/notion` (or Admin > Import > Notion)
2. Upload `e2e/fixtures/notion-export.zip` via the file input
3. Click through scan results — should show 2 databases (Tasks, Projects), 1 standalone page (Meeting Notes), and detected cross-DB relations
4. In type mapping, map Tasks → a type, Projects → a type, standalone pages → Note
5. In property mapping, verify CSV columns are listed with mapping dropdowns
6. In relation mapping, verify the Project→Tasks cross-DB relation is detected
7. In preview, verify sample objects are shown with their mapped properties
8. Click Import and wait for SSE progress to complete
9. **Expected:** Import summary shows 4 stat cards (Created, Edges, Skipped, Duration). Created count > 0. Browse button appears.

### 2. Imported objects visible in workspace

1. After test 1, click Browse (or navigate to `/browser/`)
2. Expand the nav tree
3. **Expected:** Imported objects from Tasks and Projects databases appear in the nav tree with correct type labels

### 3. Import cleanup via Discard

1. After test 2, navigate back to `/admin/import/notion`
2. Click Discard
3. Navigate to `/browser/`
4. **Expected:** Imported objects are no longer visible in the nav tree

### 4. User guide chapter exists and is complete

1. Open `docs/guide/39-notion-import.md`
2. **Expected:** Contains sections for Prerequisites, Upload, Scan Results, Type Mapping, Property Mapping, Relation Mapping, Preview, Import, After Import, Concept Mapping table, Troubleshooting (5 items), and See Also

### 5. Navigation chain is connected

1. Open `docs/guide/38-hosted-demo.md`, scroll to bottom
2. **Expected:** "Next" link points to Chapter 39
3. Open `docs/guide/39-notion-import.md`, scroll to bottom
4. **Expected:** "Next" link points to Appendix A
5. Check `docs/guide/README.md`
6. **Expected:** Chapter 39 entry exists in TOC
7. Check `docs/guide/index.html`
8. **Expected:** Chapter 39 entry exists in sidebar
9. Check `backend/app/templates/guide.html`
10. **Expected:** Chapter 39 button exists in in-app guide

### 6. Glossary entry

1. Open `docs/guide/appendix-d-glossary.md`
2. Search for "Notion Import"
3. **Expected:** Entry exists, placed alphabetically between "Monday.com Sync" and "Named Graph"

### 7. Backend unit test regression check

1. Run `cd backend && .venv/bin/python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py tests/test_notion_executor.py -v`
2. **Expected:** 69/69 tests pass with zero failures

## Edge Cases

### Fixture ZIP integrity

1. Run `unzip -l e2e/fixtures/notion-export.zip`
2. Verify all filenames contain exactly 32 hex character Notion IDs
3. **Expected:** 10 entries, all with 32-char hex IDs matching `[0-9a-f]{32}` pattern

### E2E test with stack down

1. Stop Docker test stack
2. Run the Playwright test
3. **Expected:** Test fails with clear network/connection error (not a cryptic hang)

## Failure Signals

- E2E test fails at upload step → fixture ZIP is corrupt or file upload selector changed
- E2E test fails at scan step → scanner module broken or SSE broadcast not working
- E2E test fails at mapping steps → template CSS classes changed, selectors stale
- E2E test fails at import step → executor module broken or SSE completion event not firing
- Stat card count = 0 → objects created but not displayed, or executor silently failing
- Navigation grep checks fail → one of the three navigation files was not updated
- Unit test count < 69 → test files moved or deleted

## Requirements Proved By This UAT

- NOTION-01 — Full wizard flow from ZIP upload through import with object persistence verified

## Not Proven By This UAT

- Performance under 500+ page Notion exports (fixture has ~5 pages — large-scale performance tested by unit tests with mocked data in S03)
- Notion API integration (explicitly out of scope)
- Firefox E2E coverage (Chromium only, consistent with all other wizard tests)

## Notes for Tester

- The E2E test is the primary proof artifact — if it passes, the entire wizard flow works
- The 120s timeout on the full flow test is generous; typical runs complete in ~10s
- Playwright traces are captured on failure in `e2e/test-results/` — use `npx playwright show-trace <trace.zip>` to debug
- The fixture ZIP is intentionally small (5 pages) to keep test runs fast while still exercising cross-DB relations
