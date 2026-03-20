---
verdict: pass
remediation_round: 0
---

# Milestone Validation: M019

## Success Criteria Checklist

- [x] **User installs Todoist Sync app, enters API token, connects successfully** — S01 delivers manifest.yaml, auth.py (store/verify/status/disconnect), connect.html PAT form, connect_status.html with project count. 25 auth unit tests. Route handlers wired in app.py.
- [x] **User selects projects, triggers sync, sees tasks as bpkm:Task objects with correct fields** — S01 delivers pull_sync() with two-phase bulk create, project selection UI with checkboxes, field_mapper with bidirectional priority inversion (1→low, 2→medium, 3→high, 4→critical), due date extraction (None/date-only/datetime), labels passthrough, external ID/URL. 65 field mapper + 38 sync engine tests.
- [x] **User completes a task in SemPKM, Todoist task closed via close endpoint** — S02 delivers push_sync() with close_task() call via `POST /rest/v2/tasks/{id}/close` (returns 204). Status change detection in _find_changed_tasks() SPARQL. 71 push-specific unit tests.
- [x] **User reopens a task in SemPKM, Todoist task reopened** — S02 delivers reopen_task() via `POST /rest/v2/tasks/{id}/reopen`. Same push_sync() branching logic. Unit tests cover reopen path.
- [x] **Settings UI: project selection, sync direction toggle, poll interval, Sync Now** — S02 delivers sync-config POST route, direction radios, poll interval dropdown, bidirectional sync_now (push after pull). 25 route/handler/template tests.
- [x] **150+ unit tests** — 239 tests across 6 test files (auth 25, client 22, field_mapper 65, person_matcher 18, sync_engine 38, push_sync 71). 4,253 lines of test code. Exceeds target by 59%.
- [x] **Mock Todoist API server passes selftest** — server.py with 10 endpoints, selftest verified live: 10/10 passed (health, projects, tasks, labels, 401 auth, close 204, reopen 204, update, create, project IDs).
- [x] **E2E Playwright test structurally complete** — todoist-sync.spec.ts (311 lines, 11 phases). todoistSync selector block (11 selectors) in selectors.ts. Pre-existing subprocess issue documented in comments. `npx playwright test --list` confirms 2 tests listed (chromium + firefox).
- [x] **Chapter 37 user guide** — 37-todoist-sync.md (358 lines) with field mapping tables, priority inversion, close/reopen pattern, troubleshooting. README TOC entry, glossary entry, appendix A env var row, Ch 36→37 navigation chain.

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | Auth + Client + Pull Sync (100+ tests) | PAT auth, TodoistClient (all CRUD), bidirectional field mapper, PersonMatcher, pull_sync with two-phase bulk, route handlers, templates. **168 tests** in 0.18s. | pass |
| S02 | Push Sync + Settings UI (50+ tests) | push_sync() with close/reopen branching, _find_changed_tasks() SPARQL, loop prevention, sync-config route, direction/interval settings, bidirectional sync_now. **71 push-specific tests**, 239 total. | pass |
| S03 | E2E Tests + User Guide | Mock server (10 endpoints, 10 selftest), TODOIST_API_URL env var override, Docker service wired, 11-phase E2E test, Chapter 37 (358 lines), README/glossary/appendix/navigation updates. | pass |

## Cross-Slice Integration

**S01 → S02 boundary:** S01 produced auth, client (with close/reopen methods already wired), field_mapper (with bidirectional mappings), person_matcher, pull_sync, route handlers, and templates. S02 consumed all of these and added push_sync, settings routes, and enriched templates. Boundary map matches actual delivery.

**S02 → S03 boundary:** S03 consumed the complete app (all S01 + S02 outputs) for mock server design, E2E test, and documentation. No mismatches.

**Deviation noted:** S01 pre-built close_task/reopen_task/create_task/update_task on the client beyond its plan scope. This was beneficial — S02 consumed these directly without needing to add them. S02 used `externalId` instead of `externalUuid` (deviating from github-sync pattern) — correct for Todoist since pull_sync only populates externalId.

## Requirement Coverage

The roadmap specified informal TD-01 through TD-08 requirements. These were never registered in REQUIREMENTS.md (consistent with the S03 summary noting "TD requirements were not in REQUIREMENTS.md"). Coverage assessment against the informal definitions:

| Ref | Description | Evidence | Status |
|-----|-------------|----------|--------|
| TD-01 | PAT auth | S01: 25 auth tests, store/verify/status/disconnect/mask | covered |
| TD-02 | Pull sync | S01: 38 sync engine tests, two-phase bulk create | covered |
| TD-03 | Push sync | S02: 71 push tests, close/reopen/update pipeline | covered |
| TD-04 | Project selection | S01: project selection UI + routes, S02: settings integration | covered |
| TD-05 | Priority mapping | S01: 65 field mapper tests, all 4 levels bidirectional | covered |
| TD-06 | Label→tag mapping | S01: labels passthrough in field_mapper, unit tests | covered |
| TD-07 | Settings UI | S02: direction radios, poll interval, push stats, Sync Now | covered |
| TD-08 | E2E + user guide | S03: mock server, E2E test, Chapter 37 | covered |

No gaps. All 8 informal requirements have implementation + test evidence.

## Verification Summary

| Check | Result |
|-------|--------|
| All key files exist on disk | ✅ All 11 checked (manifest, app, 5 services, mock server, E2E spec, user guide) |
| Mock selftest passes | ✅ 10/10 live verification |
| htmx URLs all prefixed with /app/todoist-sync/ | ✅ grep returns empty (no unprefixed URLs) |
| TODOIST_API_URL env var in both client and auth | ✅ Confirmed in both files + docker-compose.test.yml |
| User guide linked in README, glossary, appendix, navigation | ✅ All 4 confirmed via grep |
| E2E test listed by Playwright | ✅ 2 tests (chromium + firefox) |
| Test file volume matches claimed counts | ✅ 6 files, 4,253 total lines |

## Verdict Rationale

All 9 success criteria met. All 3 slices delivered their claimed outputs with evidence exceeding targets (239 tests vs. 150+ planned). Cross-slice boundaries aligned. All 8 informal requirements covered. No regressions introduced. The only known limitation — the pre-existing subprocess startup issue blocking full E2E runtime — is explicitly scoped as not Todoist-specific (documented across M016–M018) and the roadmap anticipated it ("structurally complete — may hit pre-existing subprocess issue").

The milestone delivered a clean fourth sync app following established patterns with the novel close/reopen endpoint pattern proven by dedicated unit tests.

## Remediation Plan

None required.
