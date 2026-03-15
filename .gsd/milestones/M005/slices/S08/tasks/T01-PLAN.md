---
estimated_steps: 9
estimated_files: 1
---

# T01: Refine VFS v2 design doc against codebase state

**Slice:** S08 — VFS v2 Design Refinement
**Milestone:** M005

## Description

Update `.gsd/design/VFS-V2-DESIGN.md` to reflect the current codebase state after S01 (queries in RDF) and S07 (Views Rethink). The draft has two critical gaps: `saved_query_id` is fully plumbed through CRUD but `build_scope_filter()` ignores it, and the path↔IRI contract is implicit. The draft also has 4 unanswered open questions and doesn't account for the `sempkm:scopeQuery` pattern from the Views Rethink. This task rewrites/extends the draft into a concrete implementation guide.

## Steps

1. Update the header metadata: change status from "Draft" to "Revised", add revision date, add "Depends on: S01 (Query SQL→RDF), S07 (Views Rethink)" note
2. Rewrite "Saved Query as Scope Source" section:
   - Document the gap: `build_scope_filter()` at `strategies.py:51` only reads `mount.sparql_scope`, completely ignores `mount.saved_query_id`
   - Specify fix approach: direct SPARQL SELECT against `urn:sempkm:queries` graph using `SyncTriplestoreClient` (already available in `build_scope_filter()`), NOT async `QueryService`
   - Include the exact SPARQL query: `SELECT ?text FROM <urn:sempkm:queries> WHERE { <urn:sempkm:query:{id}> <urn:sempkm:vocab:queryText> ?text }`
   - Note that preview endpoint comment at `mount_router.py:509` references SQL — now stale, preview can resolve saved queries from RDF
   - Document cache strategy: use TTLCache (30s) for query text resolution since `build_scope_filter()` is called on every collection init
3. Add new "Bidirectional Path Contract" section:
   - Forward: `_slugify(label)` + optional `--{sha256(iri)[:6]}` dedup suffix (from `_build_file_map_from_bindings()`)
   - Reverse: filename → `file_map` dict lookup (cached per folder in `MountRootCollection` and `StrategyFolderCollection`)
   - Key constraint: filenames are NOT stable if object labels change
   - Recommendation: persistent `filename→IRI` index needed for write-support milestone
4. Add new "Query IRI Alignment" subsection:
   - VFS should use `urn:sempkm:query:{uuid}` pattern (matching S01's `QueryService`)
   - Recommend switching from `sempkm:savedQueryId` (bare UUID) to `sempkm:scopeQuery` predicate (full IRI) — aligns with Views Rethink D096
   - Note model query IRIs use different pattern: `urn:sempkm:model:{id}:query:{name}` — `scopeQuery` should accept either pattern
   - Migration: existing mounts with `savedQueryId` values need IRI prefix prepended
5. Refine "Composable Strategy Chains" section:
   - Confirm chain model (Option A) over nested (Option B) — simpler to serialize and validate
   - Max depth 3 enforced — WebDAV clients struggle with deep paths
   - Note `parent_folder_value` in `StrategyFolderCollection` is the hook for generalization
   - Note provider path dispatch in `provider.py` handles max 4 segments (`len(parts)` 1-4) — chains deeper than 1 level need extension
   - UI recommendation: "+" button to add levels (max 3) plus predefined combos ("By Tag then By Date") for common patterns
6. Update "Type Filter" section:
   - Specify `sempkm:typeFilter` predicate on `MountSpec` — list of type IRIs
   - UI populated from `ShapesService` target class list (same data as Views Rethink type filter pills)
   - Composition: AND with saved query scope (both narrow the result set)
   - Implementation: `VALUES ?filterType { <t1> <t2> }` clause in `build_scope_filter()`
7. Update "Preview Improvements" section to note saved query resolution is now possible from RDF
8. Answer all 4 open questions:
   - Strategy chain repeats: Yes, allowed with different properties at each level (e.g., by-property/by-property with status then priority)
   - type_filter + saved_query_id: AND — both narrow the result set, compose naturally as additional WHERE clauses
   - Chain UI: "+" button to add levels (max 3) plus predefined combos for cognitive-load reduction
   - Auto-refresh: Defer — use existing TTL cache (30s from `cache.py`). Event-bus integration is a separate concern.
9. Add "Constraints & Risks" section consolidating: async/sync mismatch, cache invalidation timing, SPARQL injection safety (`check_member_query_safety()` guards), provider path depth limit, filename instability

## Must-Haves

- [ ] `saved_query_id` gap documented with concrete fix approach (direct SPARQL, not async bridge)
- [ ] Path↔IRI bidirectional contract formalized
- [ ] Query IRI alignment with Views Rethink `sempkm:scopeQuery` documented
- [ ] All 4 open questions answered with rationale
- [ ] Priority table updated with effort estimates against current codebase
- [ ] Constraints & risks section covers async/sync, caching, injection safety

## Verification

- `grep -c 'SyncTriplestoreClient\|build_scope_filter\|saved_query_id' .gsd/design/VFS-V2-DESIGN.md` — ≥5
- `grep -c 'sempkm:scopeQuery\|urn:sempkm:query' .gsd/design/VFS-V2-DESIGN.md` — ≥3
- `grep -c 'path.*IRI\|IRI.*path\|slugify\|file_map' .gsd/design/VFS-V2-DESIGN.md` — ≥4
- All 4 original open questions have answers (not "TBD")
- Document reads as a self-contained implementation guide

## Inputs

- `.gsd/design/VFS-V2-DESIGN.md` — existing draft with 6 features and 4 open questions
- `.gsd/milestones/M005/slices/S08/S08-RESEARCH.md` — codebase analysis, gap identification, approach recommendations
- `.gsd/milestones/M005/slices/S01/S01-SUMMARY.md` — S01 forward intelligence (query IRIs, `urn:sempkm:queries` graph, `_esc()` helpers)
- `.gsd/design/VIEWS-RETHINK.md` — `sempkm:scopeQuery` pattern (D096), type filter pills, SHACL column discovery
- `backend/app/vfs/strategies.py` — `build_scope_filter()` gap at line 51
- `backend/app/vfs/mount_service.py` — `MountDefinition` with `saved_query_id` field
- `backend/app/vfs/provider.py` — path segment limit (4 segments)
- `backend/app/vfs/mount_router.py` — preview endpoint stale SQL comment

## Observability Impact

This task produces a design document, not runtime code. No new runtime signals, logs, or endpoints are introduced. The document itself is the artifact — verified via `grep` count checks on key terms. Future tasks implementing this design will introduce the runtime observability (e.g., cache hit/miss logging for query text resolution, structured errors from `build_scope_filter()`).

## Expected Output

- `.gsd/design/VFS-V2-DESIGN.md` — fully revised design doc: status changed to "Revised", 3 new sections added (path contract, query alignment, constraints), all 4 open questions answered, priority table updated, coherent implementation guide for the next VFS milestone
