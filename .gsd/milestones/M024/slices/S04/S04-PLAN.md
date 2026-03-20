# S04: E2E tests + user guide

**Goal:** Mock Monday.com GraphQL server passes Docker selftest. Playwright E2E test exercises full install → auth → column mapping → sync → verify → push lifecycle. Chapter 37 user guide documents Monday.com setup with column mapping walkthrough. All three guide navigation files updated. All 607 Monday.com unit tests still pass.

**Demo:** `python e2e/mock-monday-api/server.py --selftest` passes 12+ checks. `docker compose -f docker-compose.test.yml config --quiet` validates. `docs/guide/37-monday-sync.md` exists with ~350 lines. README.md, index.html, and guide.html all reference Chapter 37.

## Must-Haves

- Mock Monday.com GraphQL server handles all 10 query shapes from `monday_client.py` with substring dispatch (Linear pattern)
- Mock returns `{"data": {...}}` wrapper on all responses (Monday.com GraphQL convention)
- Mock `settings_str` is a JSON string (double-encoded) containing `{"labels": {...}}` for label mapping UI
- Mock items include group metadata, realistic column_values, status/priority/date/people/tags/dependency columns
- Selftest verifies all canned responses (12+ checks)
- Docker compose has `mock-monday` service with healthcheck and `MONDAY_API_URL: http://mock-monday:8080` in api environment
- `mondaySync` selector block added to `e2e/helpers/selectors.ts`
- Playwright E2E spec covers: cleanup → install basic-pkm → install monday-sync → connect → select board → configure columns → configure labels → sync → verify SPARQL → admin → cleanup
- User guide Chapter 37 covers: installation, connecting, board selection, column mapping, label mapping, sync config, field mapping table, LoopGuard, groups/subitems/dependencies, troubleshooting
- README.md TOC, index.html sidebar, guide.html in-app page all updated with Chapter 37
- Appendix A has `MONDAY_API_URL` row
- Glossary has Monday.com Sync, Column Mapping, LoopGuard entries
- All 607 existing Monday.com unit tests still pass

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker stack for E2E)
- Human/UAT required: no

## Verification

- `python e2e/mock-monday-api/server.py --selftest` — all checks pass (12+)
- `docker compose -f docker-compose.test.yml config --quiet` — exits 0 (valid YAML)
- `cd backend && uv run python -m pytest tests/test_monday_*.py -v` — 607 tests pass (regression check)
- `test -f docs/guide/37-monday-sync.md` — file exists
- `grep -c "37-monday-sync" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — all 3 files contain reference
- `grep -c "MONDAY_API_URL" docs/guide/appendix-a-environment-variables.md` — at least 1 match
- `grep -c "LoopGuard\|Column Mapping\|Monday.com Sync" docs/guide/appendix-d-glossary.md` — at least 3 matches
- E2E test: `npx playwright test e2e/tests/42-monday-sync/monday-sync.spec.ts` (requires Docker stack)
- Mock fallback: `python -c "import e2e..." or selftest --selftest` verifies unrecognized queries return `{"data": {}}`
- Failure-path diagnostic: `python e2e/mock-monday-api/server.py --selftest 2>&1 | grep -c '✗'` — should be 0; any non-zero value pinpoints which canned response is broken

## Observability / Diagnostics

- **Mock Monday healthcheck**: `GET /health` on port 8080 returns `{"status": "ok"}` — used by Docker healthcheck and selftest
- **Selftest mode**: `python server.py --selftest` exercises all 10+ canned responses in-process, prints pass/fail per check with `✓`/`✗` prefix, exits 0/1 — no Docker required
- **Request logging**: All matched/unmatched queries logged to stderr with `[mock-monday]` prefix and matched query label for debugging dispatch misses
- **Unmatched query fallback**: Returns `{"data": {}}` and logs the first 120 chars of the unrecognized query — visible in `docker compose logs mock-monday`
- **Docker service health**: `docker compose -f docker-compose.test.yml ps mock-monday` shows health status
- **settings_str validation**: Selftest explicitly verifies `settings_str` is a JSON string that parses to a dict with `"labels"` key — catches double-encoding bugs

## Integration Closure

- Upstream surfaces consumed: All 6 Monday.com service modules (auth, client, field_mapper, person_matcher, sync_engine, loop_guard), app.py routes, 5 frontend templates, Docker compose test stack pattern
- New wiring introduced in this slice: `mock-monday` Docker service + `MONDAY_API_URL` env var in api service, `mondaySync` selector block in selectors.ts
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Mock Monday.com GraphQL server + Docker integration** `est:45m`
  - Why: The E2E test needs a mock API server to run against. The mock must handle all query shapes from `monday_client.py` and return canned data that exercises column mapping, groups, subitems, tags, and dependencies. Docker compose must wire it as a service.
  - Files: `e2e/mock-monday-api/server.py`, `docker-compose.test.yml`
  - Do: Create mock server following Linear's GraphQL substring-matching pattern and Jira's selftest infrastructure (`_FakeRequestFile`/`_FakeWFile`/`_make_fake_handler`). POST `/` dispatches on query substrings. Canned responses for: `me` (user profile), `boards(limit` (board list), `boards(ids:` with `columns` (column schema with `settings_str`), `boards(ids:` with `items_page` (items with column_values and group), `items(ids:` with `subitems`, `users(ids:` (user details), `tags(ids:` (tag names), `change_multiple_column_values` (mutation success), `create_item` (mutation success). GET `/health` returns OK. All responses wrapped in `{"data": {...}}`. Column `settings_str` must be a JSON string (double-encoded). Items must include status, priority, date, people, tags, and dependency column types. Add `mock-monday` service to docker-compose.test.yml with python:3.12-slim image, healthcheck, and `MONDAY_API_URL: http://mock-monday:8080` in api environment + depends_on.
  - Verify: `python e2e/mock-monday-api/server.py --selftest` — 12+ checks pass. `docker compose -f docker-compose.test.yml config --quiet` — exits 0.
  - Done when: Selftest passes all checks and docker-compose validates without error.

- [x] **T02: Playwright E2E spec + selectors** `est:40m`
  - Why: Proves the full Monday.com Sync lifecycle against Docker stack — the definitive integration test for M024. This is the only test that exercises the real app running in Docker with actual HTTP calls to the mock API.
  - Files: `e2e/tests/42-monday-sync/monday-sync.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Add `mondaySync` selector block to `selectors.ts` with selectors for: `tokenInput` (`#monday-token`), `connectBtn` (`.credentials-form button[type="submit"]`), `connectStatus` (`.connection-status`), `displayName` (`.display-name`), `boardCheckbox` (`.board-checkbox-item input[type="checkbox"]`), `saveBoardsBtn` (`.boards-section button[type="submit"]`), `configureColumnsBtn` (first `.board-mapping-row a`), `saveColumnMappingBtn`, `configureLabelsBtn`, `saveLabelMappingBtn`, `syncDirectionBidirectional` (`input[name="sync_direction"][value="bidirectional"]`), `saveConfigBtn` (`.sync-config-form button[type="submit"]`), `syncNowBtn` (`#sync-now-btn`), `syncStats` (`.sync-stats`). Create E2E spec following Jira's 12-phase structure with extra column/label mapping phases: Phase 0 cleanup → Phase 1 install basic-pkm → Phase 2 install monday-sync → Phase 3 open workspace + expand APPS + click Monday.com Sync → Phase 4 connect (fill token, verify Connected) → Phase 5 select board → Phase 6 configure columns (click Configure Columns, select dropdowns, save) → Phase 7 configure labels (click Configure Labels, map labels, save) → Phase 8 configure sync direction bidirectional → Phase 9 Sync Now → Phase 10 verify tasks via SPARQL count → Phase 11 admin detail → Phase 12 cleanup uninstall.
  - Verify: `npx playwright test e2e/tests/42-monday-sync/monday-sync.spec.ts` against Docker stack. Spec file passes TypeScript syntax check.
  - Done when: Spec file exists with all 12+ phases, selectors block added, TypeScript compiles without error.

- [x] **T03: User guide Chapter 37 + docs file updates** `est:35m`
  - Why: Completes MON-15 (user guide requirement). Users need documentation for Monday.com setup, the novel column mapping workflow, label mapping, and troubleshooting. Three navigation files must stay in sync per KNOWLEDGE.md rule.
  - Files: `docs/guide/37-monday-sync.md`, `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`, `docs/guide/appendix-a-environment-variables.md`, `docs/guide/appendix-d-glossary.md`
  - Do: Clone Chapter 36 (Jira) structure and adapt for Monday.com. Key sections: intro (column mapping differentiator), prerequisites (basic-pkm, Monday.com account, API token from Administration → Developers → API), installation, connecting (single API token — simpler than Jira's 3-field form), board selection, column mapping walkthrough (type-filtered dropdowns with worked example), status label mapping (Monday.com custom labels → bpkm:taskStatus), priority label mapping, sync configuration (direction + interval), manual sync, field mapping table (status, priority, date, people, text, long_text, numbers, tags, dropdown, dependency — all column types), LoopGuard echo prevention explanation, groups as taskGroup, subitems as parentTask, dependencies as dependsOn, troubleshooting. Update README.md TOC (add line 66: `37. [Monday.com Sync](37-monday-sync.md)`). Update index.html sidebar (add `<li>` after line 480). Update guide.html in-app page (add `<button>` entry after the Jira entry ~line 374). Add `MONDAY_API_URL` to appendix-a. Add 3 glossary entries: Monday.com Sync, Column Mapping, LoopGuard. Set navigation chain: Ch 36 → Ch 37 → Appendix A.
  - Verify: `test -f docs/guide/37-monday-sync.md && grep -c "37-monday-sync" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — all 3 match. `grep "MONDAY_API_URL" docs/guide/appendix-a-environment-variables.md` matches. `grep -c "LoopGuard" docs/guide/appendix-d-glossary.md` matches.
  - Done when: Chapter 37 exists with ~350 lines. All three navigation files reference it. Appendix has MONDAY_API_URL. Glossary has 3 new entries.

## Files Likely Touched

- `e2e/mock-monday-api/server.py` (new)
- `e2e/tests/42-monday-sync/monday-sync.spec.ts` (new)
- `e2e/helpers/selectors.ts`
- `docker-compose.test.yml`
- `docs/guide/37-monday-sync.md` (new)
- `docs/guide/README.md`
- `docs/guide/index.html`
- `backend/app/templates/guide.html`
- `docs/guide/appendix-a-environment-variables.md`
- `docs/guide/appendix-d-glossary.md`
