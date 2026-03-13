---
id: T01
parent: S10
milestone: M003
provides:
  - e2e tests for object deletion (single + bulk)
  - e2e test for edge deletion via API
  - e2e test for edge.patch command via API
key_files:
  - e2e/tests/01-objects/delete-object.spec.ts
  - e2e/tests/01-objects/delete-edge.spec.ts
  - e2e/tests/01-objects/edge-patch.spec.ts
key_decisions:
  - Edge deletion test verifies first-class edge resources (sempkm:Edge with sempkm:source/target/predicate) rather than direct triples, matching the actual edge.create handler behavior
patterns_established:
  - API-only e2e test pattern for CRUD operations — create via /api/commands, verify via SPARQL ASK, mutate via endpoint, verify again via SPARQL ASK
observability_surfaces:
  - none (test-only, no production code)
duration: 20m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Object & edge deletion tests

**Added e2e tests for single/bulk object deletion, edge deletion, and edge.patch command — all passing via API-only verification.**

## What Happened

The three test files already existed with implementations from a prior session. Running them revealed one bug in `delete-edge.spec.ts`: the test was verifying edge existence using a direct triple pattern `<source> <predicate> <target>`, but `edge.create` produces a first-class edge resource with structural triples (`sempkm:source`, `sempkm:target`, `sempkm:predicate`). The delete endpoint also expects `subject`/`predicate`/`target` params, not `source`/`target`/`predicate`.

Fixed the delete-edge test to:
1. Capture the edge IRI from the `edge.create` response
2. Verify edge existence via the edge resource's structural triples
3. Send the correct params (`subject` not `source`) to the delete endpoint
4. Verify deletion by checking the edge resource IRI has no remaining triples

The delete-object and edge-patch tests were already correct and passed on first run.

## Verification

```
cd e2e && npx playwright test tests/01-objects/delete-object.spec.ts tests/01-objects/delete-edge.spec.ts tests/01-objects/edge-patch.spec.ts --project=chromium
# 4 passed (2.5s)
```

Slice-level checks (partial — T01 is the first task):
- `rg "test.skip(" e2e/tests/ -c -g '*.ts'` → 17 remaining stubs (expected, other tasks will address these)
- Full suite not run yet (other tasks will add remaining tests)

## Diagnostics

None — test-only task with no production code changes.

## Deviations

Rewrote `delete-edge.spec.ts` to align with actual edge.create/edge.delete semantics. The original version assumed edges are stored as direct triples, but they are first-class resources with their own IRIs.

## Known Issues

Rate limiting can cause auth fixture failures when tests are run in rapid succession (magic-link requests get throttled). An API restart clears the rate limiter state. This is a known test infrastructure issue, not a test bug.

## Files Created/Modified

- `e2e/tests/01-objects/delete-edge.spec.ts` — rewrote to verify edge resources instead of direct triples, fixed delete endpoint param names
- `e2e/tests/01-objects/delete-object.spec.ts` — no changes (already passing)
- `e2e/tests/01-objects/edge-patch.spec.ts` — no changes (already passing)
