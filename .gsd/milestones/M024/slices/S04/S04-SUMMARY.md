---
id: S04
parent: M024
milestone: M024
provides:
  - Mock Monday.com GraphQL server with 10 query shapes and 12-check selftest
  - Docker compose mock-monday service with MONDAY_API_URL env var wiring
  - Playwright E2E spec (13 phases) exercising full Monday.com Sync lifecycle
  - mondaySync selector block (14 selectors) in shared selectors.ts
  - User guide Chapter 37 (393 lines) covering Monday.com setup, column mapping, label mapping, LoopGuard
  - Three-file navigation sync (README.md, index.html, guide.html) with Chapter 37
  - Appendix A MONDAY_API_URL entry and 3 glossary entries (Column Mapping, LoopGuard, Monday.com Sync)
requires:
  - slice: S01
    provides: Auth module, MondayClient with all query shapes, field mapper, person matcher, app scaffold
  - slice: S02
    provides: Column mapping UI, pull sync engine, connect_status template with board/column/label config
  - slice: S03
    provides: Push sync, LoopGuard, dependency edges, tag mapping, complete bidirectional sync pipeline
affects: []
key_files:
  - e2e/mock-monday-api/server.py
  - e2e/tests/42-monday-sync/monday-sync.spec.ts
  - e2e/helpers/selectors.ts
  - docker-compose.test.yml
  - docs/guide/37-monday-sync.md
  - docs/guide/README.md
  - docs/guide/index.html
  - backend/app/templates/guide.html
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/36-jira-sync.md
key_decisions:
  - Used "{ me " (with space) as substring matcher in mock server to avoid false-matching queries containing "me" as substring
  - Used hx-post attribute selectors for E2E column/label mapping form buttons since templates use bare forms without CSS class names
  - Used columns-3 Lucide icon for Monday.com guide.html button (represents board/column nature)
patterns_established:
  - Monday.com mock uses POST / (root path) unlike Linear's POST /graphql — matches Monday.com's single-endpoint GraphQL API
  - Monday.com E2E test adds two extra phases (column mapping + label mapping) beyond the Jira 12-phase pattern
  - Glossary entries for sync apps follow pattern: bold term, one-sentence summary, feature highlights, "See Chapter N" link
observability_surfaces:
  - python e2e/mock-monday-api/server.py --selftest — 12 checks, exits 0/1
  - GET /health on mock-monday:8080 — Docker healthcheck
  - [mock-monday] prefixed stderr logs for query dispatch visibility
  - Each E2E phase has named comment block for Playwright failure diagnosis
drill_down_paths:
  - .gsd/milestones/M024/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M024/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M024/slices/S04/tasks/T03-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-20
---

# S04: E2E tests + user guide

**Mock Monday.com GraphQL server with 12-check selftest, 13-phase Playwright E2E spec covering full install→auth→column mapping→sync→push lifecycle, and Chapter 37 user guide documenting Monday.com setup with column mapping walkthrough — completing the M024 Monday.com Sync App milestone.**

## What Happened

Three tasks delivered the final-assembly layer for the Monday.com Sync App:

**T01 — Mock Monday.com GraphQL server + Docker integration.** Built `e2e/mock-monday-api/server.py` (697 lines) following the Linear mock's substring-dispatch pattern and Jira mock's selftest infrastructure. The mock handles all 10 query shapes from `monday_client.py`: `me`, `boards(limit`, `boards(ids:` with `columns`, `boards(ids:` with `items_page`, `boards(ids:` with `groups`, `items(ids:` with `subitems`, `users(ids:`, `tags(ids:`, `change_multiple_column_values` mutation, and `create_item` mutation. All responses wrapped in `{"data": {...}}`. Column `settings_str` values are double-encoded JSON strings containing label mappings. Items include realistic column_values covering status, priority, date, people, tags, dependency, and numbers types. The `mock-monday` Docker service was wired into `docker-compose.test.yml` with healthcheck and `MONDAY_API_URL: http://mock-monday:8080` in the api environment.

**T02 — Playwright E2E spec + selectors.** Created the `mondaySync` selector block (14 selectors) in `e2e/helpers/selectors.ts` and a 372-line Playwright E2E spec with 13 phases: cleanup → install basic-pkm → install monday-sync → workspace open → connect (single API token) → board select → configure columns (type-filtered dropdown iteration) → configure labels (status/priority label mapping) → sync direction bidirectional → sync now → SPARQL verify tasks created → admin detail verify → cleanup uninstall. The column and label mapping phases are unique to Monday.com — they iterate select dropdowns and pick first non-empty options, matching the novel multi-step configuration UI built in S02.

**T03 — User guide Chapter 37 + docs file updates.** Wrote the complete Monday.com Sync user guide (393 lines) covering: prerequisites, API token generation, installation, connecting, board selection, column mapping walkthrough with worked example and type compatibility table, status/priority label mapping with example tables, sync configuration, manual sync, field mapping table (13 column types), LoopGuard echo prevention, groups/subitems/dependencies, and troubleshooting. Updated all six supporting files: README.md TOC, index.html sidebar, guide.html in-app page (columns-3 icon), appendix-a (MONDAY_API_URL), glossary (3 entries), and Ch 36 navigation footer to chain to Ch 37.

## Verification

All slice-level verification checks passed:

| # | Check | Result |
|---|-------|--------|
| 1 | `python3 e2e/mock-monday-api/server.py --selftest` | ✅ 12 passed, 0 failed |
| 2 | `docker compose -f docker-compose.test.yml config --quiet` | ✅ exits 0 |
| 3 | `cd backend && uv run python -m pytest tests/test_monday_*.py -v` | ✅ 607 passed in 0.52s |
| 4 | `test -f docs/guide/37-monday-sync.md` | ✅ exists (393 lines) |
| 5 | `grep -c "37-monday-sync" README.md index.html guide.html` | ✅ all 3 files match |
| 6 | `grep -c "MONDAY_API_URL" appendix-a-environment-variables.md` | ✅ 1 match |
| 7 | `grep -c "LoopGuard\|Column Mapping\|Monday.com Sync" appendix-d-glossary.md` | ✅ 6 matches (3 entries) |
| 8 | `test -f e2e/tests/42-monday-sync/monday-sync.spec.ts` | ✅ exists (372 lines) |
| 9 | `grep -c "mondaySync" e2e/helpers/selectors.ts` | ✅ 1 match |
| 10 | `selftest 2>&1 \| grep -c '✗'` | ✅ 0 failures |

## Requirements Advanced

- MON-14 (E2E + mock server) — Mock server with 12-check selftest passes. E2E spec covers full lifecycle (requires Docker stack to run)
- MON-15 (user guide) — Chapter 37 documents Monday.com setup, column mapping walkthrough, label mapping, LoopGuard, troubleshooting

## Requirements Validated

- MON-14 — Mock Monday.com GraphQL server passes selftest (12 checks, all query shapes), Docker compose validates, E2E spec exists with 13 phases
- MON-15 — Chapter 37 exists (393 lines), all 3 navigation files updated, appendix has MONDAY_API_URL, glossary has 3 new entries
- MON-01 through MON-13 — All validated by 607 passing unit tests from S01–S03 (regression confirmed in this slice)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- E2E selectors for column/label mapping submit buttons use `form[hx-post*="save-column-mapping"]` attribute selectors instead of the planned CSS class selectors, because the actual templates use bare `<form>` elements with htmx attributes — no dedicated CSS classes exist
- Configure Labels button selector uses `.filter({ hasText: /Configure Labels/i })` instead of `a.btn-configure-labels` because the template uses generic `a.btn.btn-sm` without a distinguishing class

## Known Limitations

- E2E test requires full Docker stack running (`docker compose -f docker-compose.test.yml up`) to execute — cannot be verified in the worktree alone
- E2E test has not been run against the live Docker stack in this slice (TypeScript compiles clean, structure verified, but runtime execution depends on Docker environment)
- Mock server returns static canned data — does not exercise dynamic state changes or error conditions (e.g., rate limiting, complexity throttling)

## Follow-ups

- none — this is the final slice of M024

## Files Created/Modified

- `e2e/mock-monday-api/server.py` — New: Mock Monday.com GraphQL server (697 lines) with 10 query shape handlers and 12-check selftest
- `e2e/tests/42-monday-sync/monday-sync.spec.ts` — New: 13-phase Playwright E2E spec (372 lines)
- `e2e/helpers/selectors.ts` — Added mondaySync selector block (14 selectors)
- `docker-compose.test.yml` — Added mock-monday service, MONDAY_API_URL env var, depends_on entry
- `docs/guide/37-monday-sync.md` — New: Complete Monday.com Sync user guide (393 lines)
- `docs/guide/README.md` — Added Chapter 37 to TOC
- `docs/guide/index.html` — Added Chapter 37 to sidebar navigation
- `backend/app/templates/guide.html` — Added Chapter 37 button with columns-3 Lucide icon
- `docs/guide/appendix-a-environment-variables.md` — Added MONDAY_API_URL row
- `docs/guide/appendix-d-glossary.md` — Added 3 entries (Column Mapping, LoopGuard, Monday.com Sync)
- `docs/guide/36-jira-sync.md` — Updated navigation footer to chain Ch 36 → Ch 37

## Forward Intelligence

### What the next slice should know
- M024 is complete — all 4 slices delivered. The Monday.com Sync App is the 8th task provider integration (after Linear, GitHub, Google Calendar, Todoist, Outlook Calendar, CalDAV, Asana, Jira). The column mapping pattern (D228, first implemented in Asana M022, refined in M024) is now the established approach for providers with custom fields.

### What's fragile
- The E2E test has not been run against the live Docker stack — it compiles and structurally matches the templates, but runtime issues (timing, selector mismatches against real htmx-loaded content) could surface when first executed
- Mock server's `settings_str` double-encoding must exactly match Monday.com's API format — if the mock drifts from reality, the column mapping UI may parse labels incorrectly

### Authoritative diagnostics
- `python3 e2e/mock-monday-api/server.py --selftest` — instant verification of all 10 query shape handlers, no Docker needed
- `cd backend && uv run python -m pytest tests/test_monday_*.py -v` — 607 tests in <1s covering all 6 service modules

### What assumptions changed
- No assumptions changed — this slice delivered exactly to plan as the low-risk final-assembly slice
