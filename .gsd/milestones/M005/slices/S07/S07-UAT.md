# S07: Views Rethink Design — UAT

**Milestone:** M005
**Written:** 2026-03-14

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S07 produces only a design document — no runtime code changes, no new endpoints, no UI changes. Verification is entirely about document existence, structure, and content quality.

## Preconditions

- Repository cloned with `.gsd/design/VIEWS-RETHINK.md` present
- `rg` (ripgrep) available for codebase reference validation

## Smoke Test

Run `test -f .gsd/design/VIEWS-RETHINK.md && echo "Design doc exists"` — should print "Design doc exists".

## Test Cases

### 1. Design document exists and is well-formed

1. Run `test -f .gsd/design/VIEWS-RETHINK.md`
2. Run `grep -c "^##" .gsd/design/VIEWS-RETHINK.md`
3. **Expected:** File exists; H2 section count is ≥ 6

### 2. Document covers all required sections

1. Run `grep "^## " .gsd/design/VIEWS-RETHINK.md`
2. Verify the following sections exist:
   - Summary (or equivalent overview)
   - Current State
   - Proposed Data Model
   - Explorer Tree Redesign
   - Migration Plan
   - UI Exposure
   - Open Questions / Deferred Scope
   - Recommendations
3. **Expected:** All listed sections present in document

### 3. Document references real code paths (not hypothetical)

1. Run `grep -c "ViewSpecService" .gsd/design/VIEWS-RETHINK.md`
2. Run `grep -c "ShapesService" .gsd/design/VIEWS-RETHINK.md`
3. Run `grep -c "carousel_tab_bar" .gsd/design/VIEWS-RETHINK.md`
4. Run `grep -c "QueryService" .gsd/design/VIEWS-RETHINK.md`
5. **Expected:** Each term appears ≥ 1 time in the document

### 4. Referenced code paths exist in the codebase

1. Run `rg -l "ViewSpecService" backend/ frontend/` — should find ≥ 1 file
2. Run `rg -l "ShapesService" backend/ frontend/` — should find ≥ 1 file
3. Run `rg -l "carousel_tab_bar" backend/ frontend/` — should find ≥ 1 file
4. Run `rg -l "QueryService" backend/ frontend/` — should find ≥ 1 file
5. **Expected:** All 4 terms found in at least 1 file in the codebase, confirming the design doc references real code, not hypothetical abstractions

### 5. Current state audit includes concrete scaling numbers

1. Open `.gsd/design/VIEWS-RETHINK.md` and find the "Current State" section
2. Look for a table or list showing ViewSpec counts per model
3. **Expected:** Document shows specific numbers (12 basic-pkm + 19 ppv = 31 total), not vague "many entries"

### 6. Proposed data model includes RDF vocabulary examples

1. Search for Turtle syntax in the document: `grep -c "@prefix\|sempkm:isGeneric\|sempkm:scopeQuery" .gsd/design/VIEWS-RETHINK.md`
2. **Expected:** Count ≥ 3, confirming concrete RDF vocabulary is proposed with Turtle examples

### 7. Explorer tree redesign shows before/after comparison

1. Find "Explorer Tree Redesign" section
2. Verify it contains both a "Before" (current 31+ entries) and "After" (proposed ~7 entries) structure
3. **Expected:** Both before and after tree structures are shown with specific entry counts

### 8. Migration plan is phased and backward-compatible

1. Find "Migration Plan" section
2. Verify Phase 1 is described as additive (no removal of existing entries)
3. Verify Phase 2 restructures navigation without removing ViewSpec data
4. Verify backward compatibility is explicitly addressed
5. **Expected:** 3 phases described; Phase 1 is strictly additive; backward compatibility section present

### 9. Query scope binding uses distinct predicate from provenance

1. Search for `sempkm:scopeQuery` in the document
2. Search for `sempkm:fromQuery` in the document
3. **Expected:** Both predicates appear; document explains that `scopeQuery` is runtime filtering while `fromQuery` is provenance

### 10. Open questions are explicitly listed

1. Find "Open Questions" section
2. **Expected:** At least 3 concrete open questions listed (not generic placeholders), covering topics like graph view performance, sparse SHACL fallback, and scope binding UX

## Edge Cases

### Design doc references stale code after future refactoring

1. Run `for term in ViewSpecService ShapesService carousel_tab_bar QueryService; do echo "$term: $(rg -l "$term" backend/ frontend/ | wc -l) files"; done`
2. **Expected:** All terms found in ≥ 1 file. If any return 0, the design doc has stale references that need updating after a refactor.

### Document internal consistency

1. Verify that the Recommendations section references Phase 1 as the milestone deliverable (consistent with Migration Plan)
2. Verify that template and router change tables are consistent with the proposed data model
3. **Expected:** No contradictions between sections

## Failure Signals

- `.gsd/design/VIEWS-RETHINK.md` does not exist
- Document has fewer than 6 H2 sections
- Document references code paths that don't exist in the codebase (hypothetical abstractions)
- No Turtle/RDF vocabulary examples (too abstract, not implementable)
- Migration plan missing or described as a single-phase big-bang switchover
- No open questions section (suggests over-confidence or incomplete analysis)

## Requirements Proved By This UAT

- VIEW-01 (views rethink — design only) — design doc exists with concrete data model, UI flow, and migration path

## Not Proven By This UAT

- Runtime correctness of the proposed design (no code implemented)
- Performance of generic views with large datasets
- UX quality of type filter pills vs. alternatives
- SHACL column discovery working end-to-end with real shapes

## Notes for Tester

- This is a design document review, not a live system test. All verification is file-based.
- The design doc is meant to be implementable in one future milestone (Phase 1). Phases 2-3 are subsequent milestones.
- The document intentionally leaves some questions open — this is a feature, not a bug. Open questions are explicitly scoped for resolution during implementation planning.
- If reviewing content quality, focus on whether the proposals reference existing extension points (`ViewSpecService`, `ShapesService`, etc.) rather than inventing new abstractions.
