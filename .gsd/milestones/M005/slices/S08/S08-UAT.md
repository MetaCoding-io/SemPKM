# S08: VFS v2 Design Refinement — UAT

**Milestone:** M005
**Written:** 2026-03-14

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This slice produces a design document, not runtime code. Verification is structural (content presence, completeness, internal consistency) rather than behavioral.

## Preconditions

- `.gsd/design/VFS-V2-DESIGN.md` exists and has been written by T01
- Access to the design doc file via filesystem

## Smoke Test

Run `wc -l .gsd/design/VFS-V2-DESIGN.md` — should show ≥200 lines (actual: 460). If the file is missing or trivially short, the slice did not execute.

## Test Cases

### 1. Document has substantive content

1. Run `wc -l .gsd/design/VFS-V2-DESIGN.md`
2. **Expected:** ≥200 lines

### 2. Core gap is thoroughly documented

1. Run `grep -c 'SyncTriplestoreClient\|build_scope_filter\|saved_query_id' .gsd/design/VFS-V2-DESIGN.md`
2. **Expected:** ≥5 references (confirms dead-wired gap, fix approach, and sync client recommendation are all present)

### 3. Query IRI alignment with Views Rethink

1. Run `grep -c 'sempkm:scopeQuery\|urn:sempkm:query' .gsd/design/VFS-V2-DESIGN.md`
2. **Expected:** ≥3 references (confirms alignment with D096 pattern)

### 4. Bidirectional path contract documented

1. Run `grep -c 'path.*IRI\|IRI.*path\|slugify\|file_map' .gsd/design/VFS-V2-DESIGN.md`
2. **Expected:** ≥4 references (confirms forward/reverse mapping documented)

### 5. All open questions resolved

1. Run `grep 'Open Questions' .gsd/design/VFS-V2-DESIGN.md`
2. **Expected:** Section header present with "(Resolved)" suffix
3. Read the Open Questions section
4. **Expected:** All 4 questions have concrete answers with rationale — none say "TBD"

### 6. No unresolved items remain

1. Run `grep -c 'TBD\|TODO\|FIXME' .gsd/design/VFS-V2-DESIGN.md`
2. **Expected:** 0

### 7. Saved query scope section includes exact SPARQL query

1. Search for "Saved Query" section in the document
2. **Expected:** Contains a SPARQL SELECT query against `urn:sempkm:queries` graph
3. **Expected:** Specifies `SyncTriplestoreClient` as the execution mechanism
4. **Expected:** Documents the exact gap at `strategies.py:51`

### 8. Type filter section specifies predicate and composition

1. Search for "Type Filter" section
2. **Expected:** Specifies `sempkm:typeFilter` predicate
3. **Expected:** Documents AND composition with saved query scope
4. **Expected:** References `ShapesService` for type list population

### 9. Composable strategies section has chain details

1. Search for "Composable" or "Strategy Chain" section
2. **Expected:** Recommends chain model (Option A)
3. **Expected:** Specifies max depth 3
4. **Expected:** Discusses `parent_folder_value` generalization
5. **Expected:** Notes provider path extension beyond 4 segments

### 10. Priority table has effort estimates

1. Search for priority table or implementation priorities
2. **Expected:** Table with items numbered and LOC estimates
3. **Expected:** Write support explicitly deferred with rationale

### 11. Constraints and risks section exists

1. Search for "Constraints" or "Risks" section
2. **Expected:** Documents async/sync mismatch
3. **Expected:** Documents cache invalidation (30s TTL)
4. **Expected:** Documents SPARQL injection safety (`check_member_query_safety()`)
5. **Expected:** Documents filename instability

## Edge Cases

### Stale SQL comment acknowledged

1. Search for "mount_router.py" or "SQL" in the document
2. **Expected:** Notes that the preview endpoint comment about SQL at `mount_router.py:509` is stale now that queries are in RDF

### Model query IRI pattern compatibility

1. Search for "model query" or "model.*IRI" in the document
2. **Expected:** Notes that model query IRIs use `urn:sempkm:model:{id}:query:{name}` — different from user query pattern `urn:sempkm:query:{uuid}`

### Write support deferral documented

1. Search for "write" or "Write Support" in the document
2. **Expected:** Explicitly states write support is deferred
3. **Expected:** Gives rationale (filename instability, persistent index needed)

## Failure Signals

- `wc -l` returns <200 — document is a stub, not a real design doc
- `grep -c 'TBD\|TODO\|FIXME'` returns >0 — unresolved items remain
- Open Questions section missing or still has "TBD" answers
- No mention of `SyncTriplestoreClient` — the sync/async constraint isn't addressed
- No mention of `sempkm:scopeQuery` — not aligned with Views Rethink
- No path contract section — bidirectional mapping not formalized

## Requirements Proved By This UAT

- VFS-01 (partial) — design doc refines VFS mount spec vocabulary, but implementation is deferred

## Not Proven By This UAT

- No runtime behavior verified (design doc only)
- No code correctness verified (implementation deferred)
- No integration with actual VFS provider code verified
- Priority estimates are unvalidated sizing

## Notes for Tester

- This is a design document review, not a functional test. The "tests" are structural checks that confirm the document covers all required topics.
- Read the document holistically for coherence — the grep checks confirm presence but not quality. A human reviewer should assess whether the implementation guidance is actually followable.
- Cross-reference the "Query IRI Alignment" section with `.gsd/design/VIEWS-RETHINK.md` to confirm `sempkm:scopeQuery` usage is consistent.
- The document should be understandable without reading the original VFS research doc — that's the self-containment test.
