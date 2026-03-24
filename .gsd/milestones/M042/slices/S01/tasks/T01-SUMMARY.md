---
id: T01
parent: S01
milestone: M042
provides:
  - SPARQL injection triage classifying all 33 f-string SPARQL modules
  - Exploit scenarios for 5 confirmed-exploitable and 4 likely-exploitable paths
  - scope_to_current_graph and check_member_query_safety bypass analysis
  - Non-SPARQL injection assessment (Jinja2, SQLAlchemy, command injection)
key_files:
  - .gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md
key_decisions:
  - Classified 33 modules (not 29 as estimated — additional modules found via IRI interpolation pattern search)
patterns_established:
  - _validate_iri() is the critical defense for IRI-in-angle-bracket SPARQL; modules using it are safe, those without are exploitable
  - Three independent _sparql_escape functions with inconsistent coverage — need consolidation
observability_surfaces:
  - none (static analysis artifact, no runtime component)
duration: 45m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: SPARQL injection triage — classify all f-string SPARQL modules (A03)

**Classified 33 backend modules for SPARQL injection risk: 5 confirmed-exploitable, 4 likely-exploitable, 24 safe, plus non-SPARQL injection assessment.**

## What Happened

Systematically analyzed every backend module constructing SPARQL via Python f-strings. Enumerated 33 modules (vs. the 29 estimated — additional modules found via IRI interpolation pattern `f".*<\{"`). For each module:

1. Located all f-string SPARQL constructions
2. Traced interpolated variables back to HTTP input, service calls, or system values
3. Checked for `_validate_iri()` or `_sparql_escape()` sanitization
4. Classified as confirmed-exploitable / likely-exploitable / safe with reasoning

Key findings:
- **views/router.py + views/service.py**: The `type` query parameter reaches SPARQL `<{type_iri}>` without validation across ~10 endpoints — highest-risk vector
- **browser/apps.py**: `iri` query param injected directly without any validation or graph scoping
- **vfs/mount_router.py**: IRI fields from JSON body reach INSERT DATA without validation — **write injection** that can modify the knowledge graph
- **browser/favorites.py**: Stored injection — `object_iri` saved to SQL without validation, later used in SPARQL
- **scope_to_current_graph defense**: Sound against its design goal (keyword blocking + graph scoping), no practical bypass found
- **Non-SPARQL injection**: Jinja2 (autoescape=True, no |safe usage), SQLAlchemy (ORM only, no raw SQL), command injection (no shell=True, no eval/exec) — all safe

## Verification

- `test -f T01-SPARQL-TRIAGE.md` — PASS
- `grep -c "confirmed-exploitable|likely-exploitable|safe"` — 54 occurrences (well above 29 minimum)
- All 33 modules individually classified with reasoning in the classification table
- Exploit scenarios provided for all confirmed and likely-exploitable modules
- Defense analysis completed for `scope_to_current_graph` and `check_member_query_safety`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "confirmed-exploitable\|likely-exploitable\|safe" T01-SPARQL-TRIAGE.md` | 0 (54) | ✅ pass | <1s |

## Diagnostics

Static analysis artifact — no runtime diagnostics. Review `T01-SPARQL-TRIAGE.md` for the full classification table, exploit scenarios, and defense analysis. T02 will incorporate these findings into the final S01-FINDINGS.md.

## Deviations

- Found 33 modules instead of 29 — the additional 4 were discovered via the IRI interpolation pattern search (`f".*<\{`) which caught modules like `browser/favorites.py`, `browser/events.py`, `copilot/service.py`, and `federation/service.py` that the keyword-only search missed.
- Classified `browser/search.py` as safe (not exploitable) because `_validate_iri` is applied to the `type` parameter; only the `q` text parameter has incomplete escaping, which goes into a FILTER string literal (low risk).

## Known Issues

- The `_sparql_escape` function inconsistency (3 separate implementations with different coverage) should be consolidated in a future remediation task.

## Files Created/Modified

- `.gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md` — Complete SPARQL injection triage with 33-module classification table, 7 detailed findings with exploit scenarios, defense analysis, and non-SPARQL injection assessment
