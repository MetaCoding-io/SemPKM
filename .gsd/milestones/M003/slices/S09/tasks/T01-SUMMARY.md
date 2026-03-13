---
id: T01
parent: S09
milestone: M003
provides:
  - get_type_analytics() returns avg_connections, last_modified, growth_trend, link_distribution per type
  - Helper functions _extract_last_modified, _iso_week_key, _pad_weekly_trend, _bucket_link_counts
  - 32 unit tests covering all analytics parsing paths
key_files:
  - backend/app/services/models.py
  - backend/tests/test_model_analytics.py
key_decisions:
  - Growth trend for zero-instance types returns 8 padded zero-count weeks (not empty list) for consistent chart rendering
  - Link distribution query counts both outgoing and incoming non-rdf:type links per instance; zero-link instances inferred from count difference
  - Helper functions are module-level (not methods) for easy unit testing and reuse
patterns_established:
  - SPARQL cross-graph join pattern for correlating events with current-graph types (used in last_modified fallback and growth_trend)
  - _LINK_BUCKETS constant defines histogram bucket boundaries; _bucket_link_counts applies them
observability_surfaces:
  - WARNING-level logs per type IRI when avg_connections, last_modified, growth_trend, or link_distribution queries fail
  - Default values on failure: 0.0, None, padded-zeros list, empty list — template can render fallbacks
duration: 20m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Extend ModelService with SPARQL analytics queries

**Added four SPARQL aggregate queries to `get_type_analytics()` — avg connections, last modified, growth trend, link distribution — with 32 unit tests covering all parsing paths and graceful error defaults.**

## What Happened

Extended `get_type_analytics()` in `backend/app/services/models.py` with four new query sections:

1. **Avg connections** — Counts all non-`rdf:type` triples where subject or object is an instance of the type (UNION of outgoing and incoming), divides by instance count, rounds to 1 decimal. Defaults to 0.0.

2. **Last modified** — Primary query: `MAX(dcterms:modified)` on instances. Fallback: `MAX(sempkm:timestamp)` from event graphs where `operationType` contains "object" and `affectedIRI` is a current instance of the type. Returns ISO date string or None.

3. **Growth trend** — Queries `object.create` event timestamps from the last 8 weeks, groups by ISO week, pads missing weeks with zeros. Returns list of 8 `{week, count}` dicts oldest-first.

4. **Link distribution** — Counts incoming + outgoing non-rdf:type links per instance, infers zero-link instances from the count difference, buckets into (0, 1-2, 3-5, 6-10, 11+). Returns list of 5 `{bucket, count}` dicts.

Added four module-level helper functions: `_extract_last_modified`, `_iso_week_key`, `_pad_weekly_trend`, `_bucket_link_counts`.

Created `backend/tests/test_model_analytics.py` with 32 tests across 8 test classes covering helper function unit tests, mock-based integration tests for each stat, graceful default tests, and existing behavior preservation tests.

## Verification

- `cd backend && python -m pytest tests/test_model_analytics.py -v` — **32 passed**
- `cd backend && python -m pytest tests/ -v` — **335 passed**, 0 failures, no regressions
- Syntax check: `python3 -c "import ast; ast.parse(...)"` — OK

### Slice-level verification status (intermediate task):
- ✅ `python -m pytest tests/test_model_analytics.py -v` — all 32 tests pass
- ⏳ Docker Compose browser integration check — requires T02 (template changes)
- ⏳ `browser_assert` checks for removed placeholders — requires T02

## Diagnostics

- Read `get_type_analytics()` return dict — each type IRI maps to a dict with 6 keys: `count`, `top_nodes`, `avg_connections`, `last_modified`, `growth_trend`, `link_distribution`
- Query failures logged at WARNING level with the type IRI (e.g., `avg_connections query failed for type <...>`)
- Default values on failure: `avg_connections=0.0`, `last_modified=None`, `growth_trend=[8 zero-count weeks]`, `link_distribution=[]`
- Mock tests document expected shapes for all stats

## Deviations

- Growth trend for zero-instance types returns 8 padded zero-count weeks instead of empty list. The task plan said "Default to empty list on error" — error defaults still use padded zeros, but this is more useful for chart rendering (consistent x-axis).

## Known Issues

None.

## Files Created/Modified

- `backend/app/services/models.py` — Extended `get_type_analytics()` with 4 new SPARQL query sections and 4 helper functions
- `backend/tests/test_model_analytics.py` — New test file with 32 tests across 8 test classes
