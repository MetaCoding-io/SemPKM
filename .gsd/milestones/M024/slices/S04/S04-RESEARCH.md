# S04: E2E tests + user guide — Research

**Date:** 2026-03-20

## Summary

S04 is straightforward application of well-established patterns. All 7 prior sync apps (Linear, GitHub, Jira, etc.) follow the same E2E testing approach: a mock API server in `e2e/mock-{provider}-api/server.py`, a Playwright spec in `e2e/tests/{N}-{provider}-sync/{provider}-sync.spec.ts`, a Docker Compose service entry, a user guide chapter, and three file updates (README.md TOC, index.html sidebar, guide.html in-app page). The Monday.com variant adds one novel E2E phase — column mapping configuration — but otherwise clones the Jira pattern exactly.

The mock server is GraphQL-based like Linear's (substring matching against incoming query text), not REST-based like GitHub/Jira. The MondayClient already reads `MONDAY_API_URL` from environment (defaulting to `https://api.monday.com/v2`), so the Docker compose service just needs to set `MONDAY_API_URL: http://mock-monday:8080` and the mock server handles POST requests at `/` (Monday.com's single-endpoint pattern).

The E2E spec is longer than prior sync apps because Monday.com has an extra column-mapping configuration step between board selection and sync. The test must: install → connect (API token) → select board → configure columns (navigate to column mapping form, select dropdowns, save) → configure labels → sync now → verify tasks via SPARQL → verify admin → cleanup. This is ~14 phases vs. Jira's 12.

## Recommendation

Clone Jira's E2E pattern (the most recent and comprehensive) with these Monday.com-specific adaptations:

1. **Mock server**: GraphQL substring-matcher like Linear, but responding to Monday.com query shapes (`me`, `boards`, `boards(ids:`, `items_page`, `users`, `tags`, `change_multiple_column_values`, `create_item`). Must include `settings_str` JSON in column responses so the label mapping UI can parse labels. Selftest with ~12 checks.

2. **E2E spec**: Follow Jira's 12-phase structure plus 2 extra phases for column mapping + label mapping configuration. Use Monday.com-specific selectors (single token input `#monday-token`, board checkboxes `.board-checkbox-item`, column mapping buttons, SPARQL verification).

3. **User guide**: Clone Chapter 36 (Jira) structure but replace Jira-specific content with Monday.com column mapping walkthrough, custom label mapping explanation, and LoopGuard echo prevention documentation. ~350 lines.

4. **Three sync files**: README.md TOC, index.html sidebar, guide.html in-app page — all need Chapter 37 entry per KNOWLEDGE.md rule about three files staying in sync.

## Implementation Landscape

### Key Files

**Files to create:**
- `e2e/mock-monday-api/server.py` — Mock Monday.com GraphQL server (~350 lines). Canned responses for: `me` (user profile), `boards` (board list), `boards(ids:` with `columns` (column schema with `settings_str`), `boards(ids:` with `items_page` (items with column_values, group), `items(ids:` with `subitems`, `users(ids:` (user details), `tags(ids:` (tag names), `change_multiple_column_values` mutation, `create_item` mutation. Health check at GET `/health`. Selftest mode via `--selftest`.
- `e2e/tests/42-monday-sync/monday-sync.spec.ts` — Playwright E2E spec (~350 lines). 14 phases: cleanup → install basic-pkm → install monday-sync → open workspace → connect (API token) → select board → configure columns → configure labels → configure sync direction → sync now → verify SPARQL tasks → verify admin → cleanup.
- `docs/guide/37-monday-sync.md` — User guide Chapter 37 (~350 lines). Sections: intro, prerequisites, installation, connecting, board selection, column mapping walkthrough, status label mapping, priority label mapping, sync configuration, manual sync, field mapping table, LoopGuard echo prevention, groups/subitems/dependencies, troubleshooting.

**Files to modify:**
- `docker-compose.test.yml` — Add `MONDAY_API_URL: http://mock-monday:8080` to api environment, add `mock-monday` service (same pattern as mock-jira: python:3.12-slim image, volume mount, healthcheck), add `mock-monday` to api depends_on.
- `e2e/helpers/selectors.ts` — Add `mondaySync` selector block with: `tokenInput: '#monday-token'`, `connectBtn: '.credentials-form button[type="submit"]'`, `connectStatus: '.connection-status'`, `displayName: '.display-name'`, `boardCheckbox: '.board-checkbox-item input[type="checkbox"]'`, `saveBoardsBtn: '.boards-section button[type="submit"]'`, `configureColumnsBtn` (first `.board-mapping-row a.btn-sm`), `configureLabelsBtn`, `saveColumnMappingBtn`, `saveLabelMappingBtn`, `syncDirectionBidirectional`, `saveConfigBtn`, `syncNowBtn: '#sync-now-btn'`, `syncStats: '.sync-stats'`.
- `docs/guide/README.md` — Add `37. [Monday.com Sync](37-monday-sync.md)` after line 65 (Chapter 36).
- `docs/guide/index.html` — Add `<li><a href="#" data-file="37-monday-sync.md">37. Monday.com Sync</a></li>` after line 479 (Jira entry).
- `backend/app/templates/guide.html` — Add Chapter 37 button entry after the Jira Sync entry (~line 372).
- `docs/guide/appendix-a-environment-variables.md` — Add `MONDAY_API_URL` row.
- `docs/guide/appendix-d-glossary.md` — Add "Monday.com Sync", "Column Mapping", "LoopGuard" entries.

**Existing files to reference (read-only):**
- `e2e/mock-linear-api/server.py` — GraphQL substring-matching pattern (clone this approach, not REST).
- `e2e/mock-jira-api/server.py` — Selftest pattern with `_FakeRequestFile`/`_FakeWFile`/`_make_fake_handler` (clone this infrastructure).
- `e2e/tests/41-jira-sync/jira-sync.spec.ts` — Most comprehensive E2E spec (14 phases with SPARQL verification).
- `e2e/tests/31-linear-sync/linear-sync.spec.ts` — GraphQL-based sync E2E pattern.
- `docs/guide/36-jira-sync.md` — User guide structure to clone (383 lines, field mapping table, troubleshooting).
- `apps/monday-sync/services/monday_client.py` — Query shapes the mock must respond to; line 24 reads `MONDAY_API_URL` from env.
- `apps/monday-sync/frontend/templates/connect.html` — Selector `#monday-token` for E2E.
- `apps/monday-sync/frontend/templates/connect_status.html` — Selectors for board checkboxes, column mapping buttons, sync controls.
- `apps/monday-sync/frontend/templates/configure_columns.html` — Column mapping form selectors.
- `apps/monday-sync/frontend/templates/configure_labels.html` — Label mapping form selectors.

### Build Order

1. **T01 — Mock Monday.com GraphQL server + Docker integration** (~mock server + docker-compose + selftest). This unblocks the E2E test. The mock must handle all query shapes from `monday_client.py` and return canned data that exercises column mapping (status column with `settings_str` containing custom labels, priority column, date column, people column, tags column, dependency column). The items must include group metadata and realistic column_values. Selftest verifies all canned responses. Docker compose wires the mock as `mock-monday` service with `MONDAY_API_URL` env var.

2. **T02 — Playwright E2E spec + selectors** (~spec + selectors.ts). Depends on T01 mock server being defined. 14-phase test: Phase 0 cleanup → Phase 1 basic-pkm install → Phase 2 monday-sync install → Phase 3 open workspace, expand APPS, click Monday.com Sync → Phase 4 connect (fill `#monday-token`, click connect, verify Connected badge) → Phase 5 select board → Phase 6 configure columns (click Configure Columns button, select dropdowns for status/priority/date/assignee, save) → Phase 7 configure labels (click Configure Labels, map status/priority labels to bpkm values, save) → Phase 8 configure sync direction to bidirectional → Phase 9 Sync Now → Phase 10 verify tasks via SPARQL count → Phase 11 verify admin detail page → Phase 12 cleanup uninstall. Add `mondaySync` selectors to `selectors.ts`.

3. **T03 — User guide Chapter 37 + docs file updates** (~guide + README + index.html + guide.html + appendix-a + glossary). Clone Chapter 36 structure. Sections: intro (column mapping differentiator), prerequisites (basic-pkm, Monday.com account, API token from Administration → API), installation, connecting (single API token), board selection, column mapping walkthrough (type-filtered dropdowns with worked example), status label mapping (custom labels → bpkm:taskStatus), priority label mapping, sync configuration (direction, interval), manual sync, field mapping table (all 12 column types from RESEARCH.md), LoopGuard echo prevention explanation, groups as taskGroup, subitems as parentTask, dependencies as dependsOn, tags resolution, troubleshooting. Update all three navigation files (README.md TOC, index.html sidebar, guide.html). Add `MONDAY_API_URL` to appendix-a. Add 3 glossary entries.

### Verification Approach

- **Mock server selftest**: `python e2e/mock-monday-api/server.py --selftest` — all checks pass (target: 12+ checks).
- **E2E test** (requires Docker stack): `npx playwright test e2e/tests/42-monday-sync/monday-sync.spec.ts` against the test stack started with `docker compose -f docker-compose.test.yml up -d --build`.
- **All Monday.com unit tests still pass**: `cd backend && uv run python -m pytest tests/test_monday_*.py -v` — 607 tests in 7 files.
- **User guide files exist and are consistent**: `docs/guide/37-monday-sync.md` exists, README.md/index.html/guide.html all reference Chapter 37, appendix-a has `MONDAY_API_URL`, glossary has 3 new entries.
- **Docker compose syntax valid**: `docker compose -f docker-compose.test.yml config --quiet` passes.

## Constraints

- Monday.com GraphQL API uses a single POST endpoint (not separate paths per resource). The mock server must dispatch on query substring content, matching the Linear mock pattern.
- The `MondayClient._execute_query()` posts to `MONDAY_API_URL` with `{"query": "...", "variables": {...}}` JSON body and `Authorization: <token>` header (no Bearer prefix). The mock must accept this shape.
- Monday.com items use `items_page(limit: N, cursor: "...")` for pagination — the mock can return all items in a single page with `cursor: null`.
- Column `settings_str` must be valid JSON containing `{"labels": {"1": "Working on it", "2": "Done", "3": "Stuck"}}` for the label mapping UI to parse and render correctly.
- The `change_multiple_column_values` mutation query contains `column_values:` as a JSON-encoded string argument — the mock just needs to substring-match on `change_multiple_column_values` and return a success response.
- KNOWLEDGE.md rule: all three guide files (README.md, index.html, guide.html) must be updated together.
- KNOWLEDGE.md rule: htmx URLs in app templates already use `/app/monday-sync/` prefix.

## Common Pitfalls

- **Mock server must return `data` wrapper** — Monday.com GraphQL responses always have `{"data": {...}}` wrapping. Missing this causes MondayClient to return empty dicts from `body.get("data", {})`.
- **Column `settings_str` must be a JSON string, not a dict** — Monday.com returns `settings_str` as a string that needs `json.loads()`. The mock must return it as a JSON-encoded string value (double-encoded in the canned response).
- **E2E column mapping requires navigating away and back** — The "Configure Columns" button loads a new fragment via htmx replacing `#connect-content`. After saving, the connect_status fragment reloads. The E2E test must wait for htmx swaps between each configuration step.
- **Workspace APPS section starts collapsed** — Per KNOWLEDGE.md, the explorer sections need `.expanded` class. The E2E test must click the section header to expand before looking for the Monday.com Sync tree leaf.
- **E2E auth fixture runs from main tree** — Per KNOWLEDGE.md, Docker stack containers are addressed by the compose project name. The test must be run with proper compose file context.
