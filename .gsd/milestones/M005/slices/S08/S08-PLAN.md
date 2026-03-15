# S08: VFS v2 Design Refinement

**Goal:** `.gsd/design/VFS-V2-DESIGN.md` refined against current codebase state with scope/strategy/prefix model, bidirectional path contract, query IRI alignment with Views Rethink, and implementation priorities with realistic effort estimates.

**Demo:** The updated design doc resolves all 4 open questions from the draft, documents the dead-wired `saved_query_id` gap with a concrete fix approach, formalizes the path↔IRI contract, and aligns VFS scope queries with the `sempkm:scopeQuery` pattern from the Views Rethink.

## Must-Haves

- Saved query scope section updated: documents the `build_scope_filter()` gap, specifies direct SPARQL resolution via `SyncTriplestoreClient` (not async `QueryService`), and shows the exact query to retrieve query text from `urn:sempkm:queries`
- Type filter section updated with `sempkm:typeFilter` predicate and `ShapesService` reuse for UI population
- Bidirectional path↔IRI contract documented: forward (IRI→path via slugify+dedup), reverse (path→IRI via file_map), filename instability acknowledged with persistent index recommendation for write-support milestone
- Query IRI alignment: VFS `saved_query_id` aligned with Views Rethink `sempkm:scopeQuery` — same `urn:sempkm:query:{uuid}` pattern, recommendation on full IRI vs bare UUID storage
- Composable strategies section refined with chain model, max depth 3, `parent_folder_value` generalization, and provider path extension note
- All 4 open questions from draft answered with rationale
- Preview section updated to note that saved query resolution is now possible (queries in RDF, not SQL)
- Priority table updated with realistic effort estimates reflecting current codebase state
- Write support confirmed deferred with rationale

## Verification

- `cat .gsd/design/VFS-V2-DESIGN.md | wc -l` — document exists and has substantive content (>200 lines)
- `grep -c 'SyncTriplestoreClient\|build_scope_filter\|saved_query_id' .gsd/design/VFS-V2-DESIGN.md` — ≥5 references to the core gap
- `grep -c 'sempkm:scopeQuery\|urn:sempkm:query' .gsd/design/VFS-V2-DESIGN.md` — ≥3 references to query IRI alignment
- `grep -c 'path.*IRI\|IRI.*path\|slugify\|file_map' .gsd/design/VFS-V2-DESIGN.md` — ≥4 references to path contract
- `grep 'Open Questions' .gsd/design/VFS-V2-DESIGN.md` — section exists with resolved answers
- All 4 original open questions have answers (not "TBD")

- `grep -c 'TBD\|TODO\|FIXME' .gsd/design/VFS-V2-DESIGN.md` — should return 0 (no unresolved items)

## Tasks

- [x] **T01: Refine VFS v2 design doc against codebase state** `est:1h`
  - Why: The existing draft identifies 6 features but has two critical gaps (dead-wired `saved_query_id`, implicit path contract) and 4 unanswered open questions. S01 changed the landscape (queries now in RDF) and S07's Views Rethink introduced `sempkm:scopeQuery`. The doc needs to reflect these.
  - Files: `.gsd/design/VFS-V2-DESIGN.md`
  - Do:
    1. Rewrite "Saved Query as Scope Source" section: document the `build_scope_filter()` gap (line 51 of `strategies.py` ignores `saved_query_id`), specify the direct SPARQL approach using `SyncTriplestoreClient` (not async `QueryService`), show the exact query against `urn:sempkm:queries`, address `type_filter` + `saved_query_id` composition (AND, not exclusive), note that preview endpoint comment at `mount_router.py:509` about SQL is now stale
    2. Add "Bidirectional Path Contract" section: document forward mapping (IRI→path via `_slugify()` + sha256 dedup), reverse mapping (path→IRI via `file_map` dict), filename instability on label change, and recommendation for persistent filename index in write-support milestone
    3. Align query IRI pattern: document that VFS should use `urn:sempkm:query:{uuid}` (matching S01 pattern), recommend `sempkm:scopeQuery` predicate (matching Views Rethink D096) instead of `sempkm:savedQueryId` storing bare UUIDs, note that model query IRIs use a different pattern (`urn:sempkm:model:{id}:query:{name}`)
    4. Refine "Composable Strategy Chains" section: recommend chain (Option A) with max depth 3, note `parent_folder_value` generalization in `StrategyFolderCollection`, document that provider path dispatch (`provider.py`) needs extension beyond 4 segments, suggest predefined combos + "+" button for UI
    5. Update "Type Filter" section: specify `sempkm:typeFilter` predicate, note `ShapesService` reuse for type list population, confirm AND composition with saved query scope
    6. Update "Preview Improvements" section: note that saved query resolution is now possible (queries in RDF post-S01), update the stale SQL comment
    7. Answer all 4 open questions with rationale: strategy chain repeats (yes, different properties), type_filter + saved_query_id composition (AND), chain UI ("+" button + predefined combos), auto-refresh (defer, use TTL cache)
    8. Update priority table with refined effort estimates and add a "Sync/Async Constraint" note explaining why `QueryService` can't be used from WebDAV context
    9. Add "Constraints & Risks" section: async/sync mismatch, cache invalidation (30s TTL), SPARQL injection safety (apply `check_member_query_safety()`), filename instability
  - Verify: All verification commands from the plan pass; all 4 open questions answered; doc reads as a coherent implementation guide
  - Done when: Design doc is a self-contained guide that an implementer could follow without reading the research doc

## Observability / Diagnostics

This slice produces a design document, not runtime code. No new runtime signals are introduced.

- **Inspection surface:** The design doc itself (`.gsd/design/VFS-V2-DESIGN.md`) serves as the authoritative reference. `grep` patterns in Verification section confirm key content is present.
- **Failure visibility:** If the design doc has unresolved questions or missing sections, the verification `grep` counts will fail their thresholds. No runtime failure paths are introduced.
- **Diagnostic command:** `grep -c 'TBD\|TODO\|FIXME' .gsd/design/VFS-V2-DESIGN.md` — should return 0 for a fully resolved doc.

## Files Likely Touched

- `.gsd/design/VFS-V2-DESIGN.md`
