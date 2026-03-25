---
id: S01
parent: M043
milestone: M043
provides:
  - Centralized SPARQLBuilder module (safe_iri, safe_literal, sparql_escape_string, values_clause, triple_pattern)
  - 18 exploit regression tests covering F-006 through F-010
  - Zero remaining local escape functions — all consolidated
requires:
  []
affects:
  - S05
key_files:
  - backend/app/sparql/builder.py
  - backend/tests/test_sparql_builder.py
  - backend/tests/test_sparql_injection_regression.py
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/browser/apps.py
  - backend/app/vfs/mount_service.py
  - backend/app/vfs/mount_router.py
  - backend/app/browser/events.py
  - backend/app/browser/favorites.py
  - backend/app/api/ai.py
  - backend/app/api/router.py
  - backend/app/browser/search.py
  - backend/app/browser/workspace.py
  - backend/app/federation/inbox.py
  - backend/app/federation/service.py
  - backend/app/services/webhooks.py
  - backend/app/task_templates/service.py
key_decisions:
  - D361: rdflib URIRef.n3() with pre-validation regex as SPARQL IRI safety layer — centralized in safe_iri()
  - D362: Validate IRIs early at HTTP boundary (router layer) with 400 + security logging, defense-in-depth safe_iri() also in service layer
patterns_established:
  - All SPARQL IRI interpolation goes through safe_iri() from app.sparql.builder — no local escape functions
  - All SPARQL string escaping goes through sparql_escape_string() from app.sparql.builder
  - Invalid IRI payloads return HTTP 400 with warning-level log for security monitoring
  - Exploit regression tests use exact audit payloads as frozen test cases
observability_surfaces:
  - Warning-level logs on invalid IRI payloads in views/router.py, browser/apps.py, browser/favorites.py, vfs/mount_router.py — includes source context for security monitoring
drill_down_paths:
  - .gsd/milestones/M043/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M043/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M043/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M043/slices/S01/tasks/T04-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T08:49:17.140Z
blocker_discovered: false
---

# S01: SPARQL Injection & Escape Consolidation

**Built centralized SPARQLBuilder module, migrated all 17 modules from 9 scattered escape functions to the single authoritative implementation, and added 18 exploit regression tests covering all 5 M042 audit findings (F-006 through F-010).**

## What Happened

T01 verified the SPARQLBuilder module (`backend/app/sparql/builder.py`) with 5 public APIs: `safe_iri()` using rdflib URIRef.n3() with pre-validation regex, `safe_literal()` via rdflib Literal.n3(), `sparql_escape_string()` as the consolidated escape function (covers \, ", ', \n, \r, \t — superset of all 9 scattered functions), `values_clause()` for safe VALUES block construction, and `triple_pattern()` for safe triple patterns. 66 unit tests cover valid IRIs, all injection payload types, literal escaping, edge cases.

T02 migrated the 5 confirmed-exploitable modules: views/service.py (~45 patterns → safe_iri()), views/router.py (IRI validation at router boundary), browser/apps.py (right_pane_sections returns 400 on invalid IRIs), vfs/mount_service.py (delegating wrapper → builder import), vfs/mount_router.py (safe_iri on all user-supplied fields including preview endpoint). Defense-in-depth: safe_iri() applied to both user-controlled AND system-derived IRIs.

T03 migrated the 6 likely-exploitable modules (events.py, favorites.py, api/ai.py, api/router.py) and 6 safe-but-inconsistent modules (search.py, workspace.py, federation/inbox.py, federation/service.py, webhooks.py, task_templates/service.py). Removed mount_service's thin wrapper from T02. Updated 3 test files. Final grep: zero local escape functions remain in the codebase.

T04 created 18 exploit regression tests using exact payloads from the M042 security audit. Discovered and fixed two early-validation gaps: views/router.py generic_view()/generic_view_data() returned 500 instead of 400 on invalid type IRIs (safe_iri ValueError uncaught at router boundary), and vfs/mount_router.py create_mount() had the same issue. Both now return 400 with warning-level security logging.

## Verification

1. `cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py -v` — 66 passed (builder primitives).
2. `cd backend && .venv/bin/python -m pytest tests/test_sparql_injection_regression.py -v` — 18 passed (all 5 audit findings blocked).
3. `rg 'def _sparql_escape|def _escape_sparql' app/ -g '*.py' | grep -v builder.py | wc -l` — returns 0 (zero legacy escape functions).
4. Full test suite (minus 3 pre-existing import failures): 5231 passed, 118 pre-existing failures (caldav, asana, github sync, jira, outlook, dashboard, rss — all unrelated to S01).
5. 349 tests across all S01-touched modules (sparql_builder, injection_regression, favorites, mount_explorer, vfs_path_contract, vfs_scope, event_log, event_suggestions, sparql_client, sparql_utils, federation_config, federation_discovery, federation_endpoints_api) — all passed.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

1. T02 kept mount_service._escape_sparql as a thin wrapper for backward compat; T03 removed it and migrated mount_router to import from builder directly.
2. T03 fixed 3 test files (test_tag_explorer, test_tag_suggestions, test_api_surface) that imported deleted local functions — not in plan.
3. T04 fixed early-validation gaps in views/router.py and vfs/mount_router.py to get 400 instead of 500 — necessary for regression tests to verify correct HTTP status.
4. pytest-timeout not installed — dropped --timeout=60 from verification commands.

## Known Limitations

118 pre-existing test failures across unrelated modules (caldav, sync engines, dashboard builder, etc.) — none introduced by S01. 3 test modules fail at collection due to missing icalendar dependency and stale notion ImportResult import.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/sparql/builder.py` — Centralized SPARQLBuilder with safe_iri(), safe_literal(), sparql_escape_string(), values_clause(), triple_pattern()
- `backend/tests/test_sparql_builder.py` — 66 unit tests for builder primitives including injection payloads
- `backend/tests/test_sparql_injection_regression.py` — 18 exploit regression tests for F-006 through F-010 audit findings
- `backend/app/views/service.py` — Replaced _validate_iri import with safe_iri; migrated ~45 raw IRI interpolation patterns
- `backend/app/views/router.py` — Added early safe_iri() validation on type_iri parameter; calendar_patch IRI validation
- `backend/app/browser/apps.py` — Added safe_iri() validation in right_pane_sections; returns 400 on invalid IRIs
- `backend/app/vfs/mount_service.py` — Removed local _escape_sparql; all calls use sparql_escape_string from builder
- `backend/app/vfs/mount_router.py` — safe_iri() on all user-supplied IRI fields; ValueError→400 with security logging
- `backend/app/browser/events.py` — Replaced bare replace('"', '\\"') with sparql_escape_string()
- `backend/app/browser/favorites.py` — Added safe_iri() validation on toggle_favorite; list_favorites uses values_clause()
- `backend/app/api/ai.py` — Replaced _sparql_escape_str with sparql_escape_string
- `backend/app/api/router.py` — Replaced _sparql_escape_str with sparql_escape_string
- `backend/app/browser/search.py` — Replaced _sparql_escape with sparql_escape_string
- `backend/app/browser/workspace.py` — Replaced _sparql_escape with sparql_escape_string (6 call sites)
- `backend/app/federation/inbox.py` — Replaced _escape_sparql_string with sparql_escape_string (7 call sites)
- `backend/app/federation/service.py` — Replaced _escape_sparql with sparql_escape_string (4 call sites)
- `backend/app/services/webhooks.py` — Replaced _escape_sparql with sparql_escape_string (6 call sites)
- `backend/app/task_templates/service.py` — Replaced _escape_sparql_string with sparql_escape_string (8 call sites)
- `backend/tests/test_tag_explorer.py` — Updated imports from deleted _sparql_escape to sparql_escape_string
- `backend/tests/test_tag_suggestions.py` — Updated imports from deleted _sparql_escape to sparql_escape_string
- `backend/tests/test_api_surface.py` — Updated TestSparqlEscapeStr to import from builder
