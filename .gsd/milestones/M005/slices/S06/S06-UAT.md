# S06: PROV-O Alignment Design — UAT

**Milestone:** M005
**Written:** 2026-03-14

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S06 is a pure documentation slice — no code changes, no runtime components. The deliverable is a design doc file. Verification is structural (file exists, sections present, predicates covered) and content-quality (completeness, actionability).

## Preconditions

- Repository cloned locally (no running server needed)
- `.gsd/design/PROV-O-ALIGNMENT.md` file exists
- S06-RESEARCH.md available for cross-reference (`.gsd/milestones/M005/slices/S06/S06-RESEARCH.md`)

## Smoke Test

Open `.gsd/design/PROV-O-ALIGNMENT.md` and confirm it is a substantive document (not a stub) with a status header, multiple sections, and a predicate audit table.

## Test Cases

### 1. File Exists and Is Substantive

1. Run `test -f .gsd/design/PROV-O-ALIGNMENT.md`
2. Run `wc -l .gsd/design/PROV-O-ALIGNMENT.md`
3. **Expected:** File exists; line count is 100+ (actual: 360 lines)

### 2. All Required Sections Present

1. Run `grep "## .*Current State" .gsd/design/PROV-O-ALIGNMENT.md`
2. Run `grep "## .*Predicate Audit" .gsd/design/PROV-O-ALIGNMENT.md`
3. Run `grep "## .*Migration Plan" .gsd/design/PROV-O-ALIGNMENT.md`
4. Run `grep "## .*UI Exposure" .gsd/design/PROV-O-ALIGNMENT.md`
5. Run `grep "## .*Recommendations" .gsd/design/PROV-O-ALIGNMENT.md`
6. **Expected:** All 5 grep commands return matches

### 3. All 13 Predicates From Research Audit Covered

1. Open the Predicate Audit section
2. Verify each of these 13 predicates appears in the audit table:
   - `sempkm:Event` (type)
   - `sempkm:timestamp`
   - `sempkm:operationType`
   - `sempkm:affectedIRI`
   - `sempkm:description`
   - `sempkm:performedBy`
   - `sempkm:performedByRole`
   - `sempkm:syncSource`
   - `sempkm:graphTarget`
   - `sempkm:commentedBy`
   - `sempkm:commentedAt`
   - `sempkm:LintRun` (type)
   - `sempkm:triggerSource`
3. **Expected:** All 13 predicates present with PROV-O equivalent (or "keep custom"), migration risk, and recommendation

### 4. Four-Phase Migration Plan Complete

1. Read the Migration Plan section
2. Verify Phase 0 is marked complete (ops log already aligned)
3. Verify Phase 1 describes new-feature adoption scope
4. Verify Phase 2 describes dual-write compatibility layer for EventStore
5. Verify Phase 3 describes read-side migration with query patterns
6. **Expected:** All 4 phases described with clear scope boundaries between each

### 5. Immutability Constraint Documented

1. Search for "immutable" in the document
2. Verify the document explicitly states that existing event graphs retain `sempkm:` predicates forever
3. Verify the rationale references event-sourcing and federation sync
4. **Expected:** At least 3 mentions of immutability; explicit statement that no retroactive migration will occur

### 6. Dual-Predicate Query Patterns Actionable

1. Read the "Dual-Predicate Query Strategy" section
2. Verify Pattern 1 (COALESCE for timestamps) contains runnable SPARQL
3. Verify Pattern 2 (UNION for actors) contains runnable SPARQL
4. Verify Pattern 3 (cursor pagination) contains runnable SPARQL
5. Verify rationale for choosing COALESCE over VALUES is documented
6. **Expected:** Three concrete SPARQL query patterns with explanatory text; VALUES cross-product issue explained

### 7. UI Exposure Recommendation Has Clear Boundaries

1. Read the "UI Exposure Recommendation" section
2. Verify workspace user exposure is defined (creation time, author attribution)
3. Verify admin-only exposure is defined (event log, ops log, SPARQL console)
4. Verify explicit statement that no UI changes are recommended
5. **Expected:** Clear workspace vs. admin boundary with rationale

### 8. Starting Point Terms Recommendation

1. Read the Recommendations section
2. Verify explicit recommendation to use Starting Point terms only
3. Verify Qualified terms are rejected with rationale (blank nodes, complexity)
4. Verify Extended terms are rejected with rationale
5. **Expected:** Three-tier PROV-O ontology described with Starting Point recommended and other tiers rejected

## Edge Cases

### Cross-Reference with S02 Ops Log

1. Open `.gsd/design/PROV-O-ALIGNMENT.md`
2. Verify Phase 0 references the ops log service from S02
3. Verify the ops log's PROV-O terms (`prov:Activity`, `prov:startedAtTime`, etc.) are listed as already-aligned
4. **Expected:** S02 ops log explicitly cited as the reference implementation; its 5 PROV-O terms listed

### Query Execution History Partial Alignment Noted

1. Search for "Query Execution" or "executedBy" in the document
2. Verify the doc notes that query history already uses `prov:startedAtTime` but has a custom actor predicate
3. **Expected:** Partial alignment documented; migration to `prov:wasAssociatedWith` recommended in Phase 1

### Comments and Validation Deferred

1. Read the Recommendations section
2. Verify comments (`sempkm:commentedBy/At`) are listed as low-priority alignment targets
3. Verify validation reports (`sempkm:LintRun`, `sempkm:triggerSource`) are listed as low-priority
4. Verify explicit recommendation to defer these to their own milestones
5. **Expected:** Both subsystems acknowledged but explicitly deferred

## Failure Signals

- File missing or empty (< 50 lines)
- Any of the 5 required sections missing
- Fewer than 13 predicates in the audit table
- No concrete SPARQL query patterns (just prose without code)
- Missing immutability constraint statement
- Missing Phase 0 completion acknowledgment (S02 ops log)
- Recommendation to use Qualified or Extended PROV-O terms (contradicts D090)

## Requirements Proved By This UAT

- none — this is a design doc slice; implementation requirements will be proved when migration phases are executed

## Not Proven By This UAT

- The SPARQL query patterns actually work against RDF4J (would require running them against the triplestore)
- Phase 2 dual-write is implementable without performance regression
- The recommended UI exposure boundaries are correct from a UX perspective (requires human judgment)

## Notes for Tester

- This is a documentation review, not a runtime test. No server, Docker, or browser needed.
- The design doc follows the same format as `.gsd/design/VFS-V2-DESIGN.md` — compare structure if needed.
- Key quality signal: can you read the predicate audit table and determine, for any given predicate, whether to migrate it, when, and how? If yes, the doc serves its purpose.
