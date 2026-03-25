# S01: SPARQL Injection & Escape Consolidation — UAT

**Milestone:** M043
**Written:** 2026-03-25T08:49:17.140Z

## Preconditions
- Backend running with `cd backend && .venv/bin/python -m uvicorn app.main:app`
- Authenticated session available (cookie or API token)
- basic-pkm model installed with at least one type (e.g., bpkm:Task)

## Test Cases

### TC-01: F-006 — Views type parameter injection blocked
1. Open browser to `/browser/views/generic/table?type=x>%20.%20?s%20?p%20?o%20}%20%23`
2. **Expected:** HTTP 400 response (not a data leak, not 500)
3. Try the same with `/browser/views/generic/cards?type=x>%20.%20?s%20?p%20?o%20}%20%23`
4. **Expected:** HTTP 400 response

### TC-02: F-006 — Valid type IRI still works
1. Open browser to `/browser/views/generic/table?type=urn:sempkm:model:basic-pkm:Task`
2. **Expected:** Normal table view renders (200), no regression

### TC-03: F-007 — Apps IRI parameter injection blocked
1. Send GET `/browser/apps/right-pane-sections?iri=x>%20.%20?s%20?p%20?o%20}%20%23`
2. **Expected:** HTTP 400 response with error message about invalid IRI

### TC-04: F-008 — VFS mount creation injection blocked
1. Send POST `/browser/vfs/mounts` with JSON body containing `group_by_property: "x> . ?s ?p ?o } #"`
2. **Expected:** HTTP 400 response — injected SPARQL not executed

### TC-05: F-009 — Favorites injection blocked
1. Send POST `/browser/favorites` with `object_iri: "x> . ?s ?p ?o } #"`
2. **Expected:** HTTP 400 response — malicious IRI rejected before SQL storage

### TC-06: F-010 — Events search escape breakout blocked
1. Search events with term containing `\" )) . ?s ?p ?o } #`
2. **Expected:** Empty results or safe search — no SPARQL breakout, no data leak

### TC-07: No local escape functions remain
1. Run: `cd backend && rg 'def _sparql_escape|def _escape_sparql' app/ -g '*.py' | grep -v builder.py`
2. **Expected:** Zero results — all local escape functions have been deleted

### TC-08: Builder test suite passes
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py -v`
2. **Expected:** 66 tests pass

### TC-09: Regression test suite passes
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_sparql_injection_regression.py -v`
2. **Expected:** 18 tests pass, covering all 5 audit findings

### TC-10: No new test failures introduced
1. Run full test suite: `cd backend && .venv/bin/python -m pytest tests/ --ignore=tests/test_caldav_field_mapper.py --ignore=tests/test_caldav_sync_engine.py --ignore=tests/test_notion_executor.py`
2. **Expected:** 5231+ pass, 118 pre-existing failures (all in unrelated modules). No new failures.
