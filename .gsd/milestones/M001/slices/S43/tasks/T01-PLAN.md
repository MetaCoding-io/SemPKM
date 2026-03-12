# T01: 43-inference-e2e-test-gap 01

**Slice:** S43 — **Milestone:** M001

## Description

Fix the `_store_inferred_triples` Literal bug and add an E2E test covering the full inference user story: create a one-sided relationship, run inference, verify the inverse triple appears.

Purpose: Close the TEST-05 gap identified in the v2.4 milestone audit. The existing inference E2E tests only verify panel UI infrastructure, not the actual data flow.
Output: Bug-fixed inference service + Playwright test proving inference works end-to-end.

## Must-Haves

- [ ] "_store_inferred_triples does not produce SPARQL 400 errors when owlrl generates Literal-subject triples"
- [ ] "E2E test creates a one-sided hasParticipant relationship and inference materializes the participatesIn inverse"
- [ ] "Inference run returns total_inferred > 0 after adding a fresh one-sided relationship"

## Files

- `backend/app/inference/service.py`
- `e2e/tests/09-inference/inference.spec.ts`
