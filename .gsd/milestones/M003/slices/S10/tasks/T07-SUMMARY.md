---
id: T07
parent: S10
milestone: M003
provides:
  - e2e test for health check endpoint (GET /api/health) — response shape, no-auth access
  - e2e test for LLM config endpoints (PUT /browser/llm/config, POST /browser/llm/test, POST /browser/llm/models)
  - e2e test for object tooltip endpoint (GET /browser/tooltip/{iri}) — seed objects and missing IRI handling
  - e2e test for edge provenance endpoint (GET /browser/edge-provenance) — existing edge and missing edge handling
key_files:
  - e2e/tests/00-setup/health-check.spec.ts
  - e2e/tests/06-settings/llm-config.spec.ts
  - e2e/tests/01-objects/tooltip-and-provenance.spec.ts
key_decisions:
  - Health check test uses anonApi fixture (no magic link) since the endpoint is intentionally public — saves rate-limit budget
  - LLM config test saves field-by-field via {field, value} body matching the actual PUT /browser/llm/config API contract, not the incorrect {provider, api_key, model, base_url} body that was in the pre-existing stub
  - Edge provenance test uses correct query params (subject/predicate/target) matching the backend signature, not the incorrect (source/target/predicate) params from the pre-existing stub
patterns_established:
  - For health check e2e, use anonApi fixture to avoid consuming rate-limit budget — health endpoint requires no auth
  - LLM config endpoints accept {field, value} for per-field updates — tests verify save/test/models mechanics without a real LLM provider, then clean up by resetting fields to empty
observability_surfaces:
  - none — test-only task with no production code changes
duration: 25m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T07: LLM config, tooltip, edge provenance, health check tests

**Rewrote pre-existing broken test stubs into 4 working test functions (1 health + 1 LLM + 2 tooltip/provenance) covering all four endpoint categories — all passing.**

## What Happened

The three test files already existed but had multiple bugs preventing them from passing:

1. **health-check.spec.ts** — expected `status: "ok"` but backend returns `status: "healthy"`; had 4 test() functions consuming rate-limit budget needlessly for a public endpoint; last test tried to import from `@playwright/test` incorrectly.
2. **llm-config.spec.ts** — sent incorrect request body `{provider, api_key, model, base_url}` instead of the actual API contract `{field, value}`; had 3 separate test() functions hitting rate limit.
3. **tooltip-and-provenance.spec.ts** — edge provenance used wrong query params (`source/target/predicate` instead of `subject/predicate/target`); had 5 test() functions hitting rate limit.

Rewrote all three files:
- Consolidated to 4 total test() functions (1 + 1 + 2) to stay within the 5/minute magic-link rate limit
- Fixed health status assertion to match actual `"healthy"` response
- Fixed LLM config to use `{field, value}` per-field API contract
- Fixed edge provenance params to use `subject/predicate/target`
- Added cleanup step in LLM config test to reset config after testing
- Health check uses `anonApi` fixture (no magic link needed for public endpoint)

## Verification

```
cd e2e && npx playwright test tests/00-setup/health-check.spec.ts tests/01-objects/tooltip-and-provenance.spec.ts tests/06-settings/llm-config.spec.ts --project=chromium
# 4 passed (1.8s)
```

Slice-level checks (partial — T07 is not the final task):
- `rg "test.skip(" e2e/tests/ -c -g '*.ts'` — returns 17 (expected, remaining stubs belong to T08-T12)
- All 4 new test functions pass

## Diagnostics

None — test-only task with no production code changes.

## Deviations

Pre-existing test files had to be completely rewritten rather than just tweaked, due to incorrect API contracts (wrong param names, wrong request body shape, wrong expected values) and rate-limit-violating test structure (too many test() functions).

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/00-setup/health-check.spec.ts` — rewritten: consolidated 4 tests into 1, fixed status assertion, uses anonApi
- `e2e/tests/06-settings/llm-config.spec.ts` — rewritten: consolidated 3 tests into 1, fixed request body to match actual API
- `e2e/tests/01-objects/tooltip-and-provenance.spec.ts` — rewritten: consolidated 5 tests into 2, fixed edge-provenance query params
