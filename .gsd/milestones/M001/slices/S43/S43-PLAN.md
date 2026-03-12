# S43: Inference E2e Test Gap

**Goal:** Fix the `_store_inferred_triples` Literal bug and add an E2E test covering the full inference user story: create a one-sided relationship, run inference, verify the inverse triple appears.
**Demo:** Fix the `_store_inferred_triples` Literal bug and add an E2E test covering the full inference user story: create a one-sided relationship, run inference, verify the inverse triple appears.

## Must-Haves


## Tasks

- [x] **T01: 43-inference-e2e-test-gap 01** `est:3min`
  - Fix the `_store_inferred_triples` Literal bug and add an E2E test covering the full inference user story: create a one-sided relationship, run inference, verify the inverse triple appears.

Purpose: Close the TEST-05 gap identified in the v2.4 milestone audit. The existing inference E2E tests only verify panel UI infrastructure, not the actual data flow.
Output: Bug-fixed inference service + Playwright test proving inference works end-to-end.

## Files Likely Touched

- `backend/app/inference/service.py`
- `e2e/tests/09-inference/inference.spec.ts`
