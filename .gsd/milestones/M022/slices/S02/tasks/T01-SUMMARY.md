---
id: T01
parent: S02
milestone: M022
provides:
  - Pure field mapper with configurable 3-mode status extraction for Asana tasks
  - Person matcher with SPARQL email lookup, create-on-miss, LRU cache
  - 92 field mapper tests + 18 person matcher tests (110 total)
key_files:
  - apps/asana-sync/services/field_mapper.py
  - apps/asana-sync/services/person_matcher.py
  - backend/tests/test_asana_field_mapper.py
  - backend/tests/test_asana_person_matcher.py
key_decisions:
  - Used tuple return (type_iri, properties) from build_task_properties instead of embedding type in the dict — cleaner separation for sync engine consumption
  - Slug format is `asana-{gid}` (no hashing) — GIDs are already unique stable identifiers
patterns_established:
  - Configurable field extraction via field_config dict pattern — status_source selects extraction mode, *_field_gid keys select custom fields by GID, *_mapping dicts provide value translation
observability_surfaces:
  - none (pure functions — observability lives in the sync engine layer)
duration: 25min
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build field mapper and person matcher with tests

**Built Asana field mapper with 3-mode configurable status extraction and person matcher cloned from Linear, with 110 passing tests.**

## What Happened

Created `field_mapper.py` (~350 lines) with all Asana→bpkm:Task field extraction functions. The core novelty is `extract_status()` which reads `field_config["status_source"]` to select between three modes: `completed_only` (boolean map), `custom_field` (enum field matched by GID), and `section` (section name lookup). Each mode falls back to the completed boolean when no match is found. Priority and story points similarly extract from custom fields by GID with configurable mappings.

HTML→Markdown conversion uses conditional markdownify import with `strip_html_tags` regex fallback, matching the pattern from outlook-calendar.

`person_matcher.py` (~130 lines) is a direct clone of the Linear version with only the logger name changed to `asana.sync.person_matcher`. Same SPARQL email lookup, same create-on-miss via command API, same case-insensitive LRU cache.

## Verification

- `pytest backend/tests/test_asana_field_mapper.py -v --noconftest` — 92 tests pass
- `pytest backend/tests/test_asana_person_matcher.py -v --noconftest` — 18 tests pass
- Syntax verification via `ast.parse()` — both files clean

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `backend/.venv/bin/pytest backend/tests/test_asana_field_mapper.py -v --noconftest` | 0 | ✅ pass | 2.2s |
| 2 | `backend/.venv/bin/pytest backend/tests/test_asana_person_matcher.py -v --noconftest` | 0 | ✅ pass | 2.2s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/person_matcher.py').read())"` | 0 | ✅ pass | <1s |

### Slice-level verification (partial — T01 is first of 2 tasks)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | field_mapper tests (50+) | ✅ 92 pass | Exceeds target |
| 2 | person_matcher tests (10+) | ✅ 18 pass | Exceeds target |
| 3 | sync_engine tests (40+) | ⏳ T02 | Not yet built |
| 4 | field_mapper.py syntax | ✅ | Clean |
| 5 | person_matcher.py syntax | ✅ | Clean |
| 6 | sync_engine.py syntax | ⏳ T02 | Not yet built |
| 7 | Diagnostic surface test | ⏳ T02 | last_pull_result assertion is in sync engine tests |

## Diagnostics

Both modules are pure / injected-dependency — no runtime state to inspect. To verify correctness, run the test suites. Person matcher emits `asana.sync.person_matcher` DEBUG logs for cache hits and person creation events.

## Deviations

- Person matcher tests initially used `asyncio.get_event_loop().run_until_complete()` which is removed in Python 3.14. Fixed to use `asyncio.run()` instead.
- Test count exceeds plan targets: 92 field mapper tests (plan: 50+), 18 person matcher tests (plan: 10+). More edge cases covered than originally scoped.

## Known Issues

None.

## Files Created/Modified

- `apps/asana-sync/services/field_mapper.py` — New. Pure field mapping functions for all Asana→bpkm:Task property extraction with configurable status/priority via field_config dict.
- `apps/asana-sync/services/person_matcher.py` — New. SPARQL email lookup + create-on-miss + LRU cache, cloned from Linear person matcher.
- `backend/tests/test_asana_field_mapper.py` — New. 92 tests covering all extraction paths: 3 status modes, priority mapping, story points, tags, followers, assignee, section name, milestone detection, HTML→Markdown, date truncation, slug computation, build_task_properties integration.
- `backend/tests/test_asana_person_matcher.py` — New. 18 tests covering email found, create-on-miss, cache hit, None/empty email, slug from display name vs email local part, case-insensitive cache, multiple emails.
- `.gsd/milestones/M022/slices/S02/tasks/T01-PLAN.md` — Modified. Added Observability Impact section.
