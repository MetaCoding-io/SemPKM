---
id: S08
parent: M005
milestone: M005
provides:
  - Revised VFS v2 design doc as self-contained implementation guide
requires:
  - slice: S01
    provides: Queries stored as RDF in urn:sempkm:queries (enabler for saved query resolution)
  - slice: S07
    provides: Views Rethink design with sempkm:scopeQuery pattern (alignment target)
affects:
  - Future VFS v2 implementation milestone
key_files:
  - .gsd/design/VFS-V2-DESIGN.md
key_decisions:
  - D098 — Direct SPARQL via SyncTriplestoreClient for saved query resolution (not async QueryService)
  - D099 — Adopt sempkm:scopeQuery predicate with full IRI (aligning VFS with Views Rethink D096)
  - D100 — Chain model (Option A) for composable strategies with max depth 3
  - D101 — type_filter AND saved_query_id compose via AND (both narrow result set)
  - D102 — Defer auto-refresh — use existing 30s TTLCache
patterns_established:
  - Design doc as self-contained implementation guide with code samples, LOC estimates, and migration paths
observability_surfaces:
  - none (design document, no runtime changes)
drill_down_paths:
  - .gsd/milestones/M005/slices/S08/tasks/T01-SUMMARY.md
duration: 30m
verification_result: passed
completed_at: 2026-03-14
---

# S08: VFS v2 Design Refinement

**Revised VFS-V2-DESIGN.md from 120-line discussion draft to 460-line implementation guide: documented dead-wired `saved_query_id` gap with direct SPARQL fix, formalized path↔IRI contract, aligned query IRIs with Views Rethink `sempkm:scopeQuery`, answered all 4 open questions, added constraints/risks section.**

## What Happened

The existing VFS v2 draft identified 6 desired features but had two critical gaps (dead-wired `saved_query_id`, implicit path contract) and 4 unanswered open questions. S01's query SQL→RDF migration and S07's Views Rethink changed the landscape — queries are now in RDF and `sempkm:scopeQuery` is the established scope-binding pattern. The design doc needed to reflect these.

T01 rewrote the doc into a concrete implementation guide covering:

1. **Saved Query Scope** — Documented the exact gap (`build_scope_filter()` at `strategies.py:51` ignores `mount.saved_query_id`). Specified fix: direct SPARQL SELECT against `urn:sempkm:queries` graph via `SyncTriplestoreClient`. Included exact query, revised function signature, and TTLCache strategy.

2. **Type Filter** — Specified `sempkm:typeFilter` predicate with `VALUES` clause implementation and AND composition with saved query scope.

3. **Composable Strategies** — Confirmed chain model (Option A), max depth 3. Documented `parent_folder_value` generalization, provider path extension needs (5–6 segments), and per-level property configuration.

4. **Bidirectional Path Contract** — Formalized forward mapping (`_slugify()` + sha256 dedup suffix), reverse mapping (`file_map` dict lookup), filename instability constraint, and persistent index recommendation for write-support.

5. **Query IRI Alignment** — Recommended `sempkm:scopeQuery` with full IRI matching Views Rethink D096. Documented migration from bare UUID `savedQueryId` and model query IRI pattern compatibility.

6. **All 4 Open Questions Resolved** — Strategy repeats (yes, different properties), type_filter+saved_query (AND), chain UI (+ button + predefined combos), auto-refresh (defer, use TTLCache).

7. **Constraints & Risks** — Async/sync mismatch, cache invalidation, SPARQL injection safety, filename instability, provider path depth limit.

8. **Priority Table** — Updated with LOC estimates against current codebase.

## Verification

All slice-level checks pass:

- `wc -l` → 460 lines (threshold: >200) ✅
- Core gap references (`SyncTriplestoreClient|build_scope_filter|saved_query_id`) → 41 (threshold: ≥5) ✅
- Query IRI alignment (`sempkm:scopeQuery|urn:sempkm:query`) → 12 (threshold: ≥3) ✅
- Path contract (`path.*IRI|IRI.*path|slugify|file_map`) → 9 (threshold: ≥4) ✅
- Open Questions section exists with "(Resolved)" suffix ✅
- `TBD|TODO|FIXME` count → 0 (all resolved) ✅

## Requirements Advanced

- VFS-01 — Design doc refines the VFS mount spec vocabulary and strategy composition model for v2

## Requirements Validated

- None newly validated (design doc, not implementation)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

Pre-flight required adding `## Observability / Diagnostics` to S08-PLAN.md and `## Observability Impact` to T01-PLAN.md. Applied before starting the main task.

## Known Limitations

- Design doc only — no runtime code changes. Implementation deferred to a future VFS v2 milestone.
- Priority estimates are LOC-based rough sizing, not time-boxed commitments.

## Follow-ups

- Implement saved query scope resolution (item 1 in priority table, ~40 LOC)
- Implement type filter (item 2, ~30 LOC)
- Migrate `sempkm:savedQueryId` → `sempkm:scopeQuery` predicate (SPARQL UPDATE)
- Extend provider path dispatch beyond 4 segments for strategy chains
- Add persistent filename index when write-support milestone begins

## Files Created/Modified

- `.gsd/design/VFS-V2-DESIGN.md` — fully revised from 120-line draft to 460-line implementation guide
- `.gsd/milestones/M005/slices/S08/S08-PLAN.md` — added observability section, diagnostic verification, marked T01 done
- `.gsd/milestones/M005/slices/S08/tasks/T01-PLAN.md` — added Observability Impact section

## Forward Intelligence

### What the next slice should know
- VFS v2 design is now a concrete implementation guide with code samples and LOC estimates. Implementers can follow it directly without reading the original research doc.
- The `sempkm:scopeQuery` pattern is shared between Views (D096) and VFS (D099) — any change to one affects the other.

### What's fragile
- The `build_scope_filter()` gap is real production debt — saved queries silently don't filter VFS content. Users who set a saved query on a mount get unfiltered results with no error.

### Authoritative diagnostics
- `grep -c 'TBD\|TODO\|FIXME' .gsd/design/VFS-V2-DESIGN.md` — must return 0 for a fully resolved doc.

### What assumptions changed
- Original assumption: saved query resolution requires async `QueryService`. Actual: `SyncTriplestoreClient` is already available in VFS context and can query `urn:sempkm:queries` directly.
- Original assumption: path↔IRI mapping was an implementation detail. Actual: it's a critical contract that needs documentation for write-support planning.
