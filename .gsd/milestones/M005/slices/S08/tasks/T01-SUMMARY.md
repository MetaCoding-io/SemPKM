---
id: T01
parent: S08
milestone: M005
provides:
  - Revised VFS v2 design doc with concrete implementation guide
key_files:
  - .gsd/design/VFS-V2-DESIGN.md
key_decisions:
  - Direct SPARQL via SyncTriplestoreClient for saved query resolution (not async QueryService)
  - Adopt sempkm:scopeQuery predicate with full IRI (aligning VFS with Views Rethink D096)
  - Chain model (Option A) for composable strategies with max depth 3
  - type_filter AND saved_query_id compose via AND (both narrow result set)
  - Defer auto-refresh — use existing 30s TTLCache
patterns_established:
  - Design doc as self-contained implementation guide with code samples and migration paths
observability_surfaces:
  - none (design document, no runtime changes)
duration: 30m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Refine VFS v2 design doc against codebase state

**Rewrote VFS-V2-DESIGN.md from draft into concrete implementation guide: documented dead-wired `saved_query_id` gap with direct SPARQL fix, formalized path↔IRI contract, aligned query IRIs with Views Rethink `sempkm:scopeQuery`, answered all 4 open questions, added constraints/risks section.**

## What Happened

Revised `.gsd/design/VFS-V2-DESIGN.md` from a 120-line discussion draft to a 460-line implementation guide. Key changes:

1. **Saved Query Scope (§1):** Documented the exact gap — `build_scope_filter()` at `strategies.py:51` ignores `mount.saved_query_id`. Specified the fix: direct SPARQL SELECT against `urn:sempkm:queries` graph via `SyncTriplestoreClient` (not async `QueryService`). Included the exact query, revised function signature, and cache strategy using existing `TTLCache` (30s).

2. **Type Filter (§2):** Specified `sempkm:typeFilter` predicate with `VALUES` clause implementation. Documented AND composition with saved query scope.

3. **Composable Strategies (§3):** Confirmed chain model (Option A), max depth 3. Documented `parent_folder_value` generalization hook, provider path extension needs (5–6 segments), and per-level property configuration for strategy repeats.

4. **Bidirectional Path Contract (§4 — new):** Formalized forward mapping (`_slugify()` + sha256 dedup suffix), reverse mapping (`file_map` dict lookup), filename instability constraint, and persistent index recommendation for write-support milestone.

5. **Query IRI Alignment (§5 — new):** Recommended `sempkm:scopeQuery` with full IRI (matching Views Rethink D096), documented migration from bare UUID `savedQueryId`, noted model query IRI pattern compatibility.

6. **Preview Fix (§6):** Updated to note saved query resolution is now possible from RDF. Flagged the stale SQL comment at `mount_router.py:509`.

7. **Open Questions (all 4 resolved):** Strategy repeats (yes, different properties), type_filter+saved_query (AND), chain UI (+ button + predefined combos), auto-refresh (defer, use TTLCache).

8. **Constraints & Risks (§new):** Async/sync mismatch, cache invalidation timing, SPARQL injection safety via `check_member_query_safety()`, provider path depth limit, filename instability, SPARQL complexity at chain depth, query escape consistency.

9. **Priority Table:** Updated with LOC estimates against current codebase (items 1–4: ~140 LOC total, item 6: ~200 LOC, item 8: deferred).

Also applied pre-flight observability fixes to S08-PLAN.md and T01-PLAN.md.

## Verification

All slice-level verification checks pass:

- `wc -l` → 460 lines (threshold: >200) ✅
- `grep -c 'SyncTriplestoreClient\|build_scope_filter\|saved_query_id'` → 41 (threshold: ≥5) ✅
- `grep -c 'sempkm:scopeQuery\|urn:sempkm:query'` → 12 (threshold: ≥3) ✅
- `grep -c 'path.*IRI\|IRI.*path\|slugify\|file_map'` → 9 (threshold: ≥4) ✅
- `grep 'Open Questions'` → section exists with "(Resolved)" suffix ✅
- `grep -c 'TBD\|TODO\|FIXME'` → 0 (all questions answered) ✅

This is the only task in the slice — all slice-level checks pass.

## Diagnostics

None — this task produces a design document, not runtime code.

## Deviations

- Pre-flight required adding `## Observability / Diagnostics` to S08-PLAN.md, `## Observability Impact` to T01-PLAN.md, and a diagnostic verification step to S08-PLAN.md. Applied these before starting the main task.

## Known Issues

None.

## Files Created/Modified

- `.gsd/design/VFS-V2-DESIGN.md` — fully revised from 120-line draft to 460-line implementation guide
- `.gsd/milestones/M005/slices/S08/S08-PLAN.md` — added observability section, diagnostic verification, marked T01 done
- `.gsd/milestones/M005/slices/S08/tasks/T01-PLAN.md` — added Observability Impact section
