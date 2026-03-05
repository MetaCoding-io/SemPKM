---
phase: 40-e2e-test-coverage-v24
verified: 2026-03-05T09:15:00Z
status: gaps_found
score: 3/4 success criteria verified
gaps:
  - truth: "E2E tests verify bidirectional links appear after creating a relationship (inference working)"
    status: partial
    reason: "Inference tests verify panel UI infrastructure and API endpoints (run, triples, config) but do NOT create an edge and verify the inverse triple appears. Documented deviation: seed data already has both inverse directions pre-populated, and a pre-existing bug in _store_inferred_triples prevents new inference from working with rdfs:domain/rdfs:range. Tests verify the machinery works but not the end-to-end user flow of 'create relationship -> run inference -> see bidirectional link'."
    artifacts:
      - path: "e2e/tests/09-inference/inference.spec.ts"
        issue: "No edge.create + inverse verification test. Tests cover panel loading, API response structure, filter controls, refresh button, and config endpoint -- all infrastructure, not the user-visible behavior described in the success criterion."
    missing:
      - "Test that creates a new edge (e.g., dcterms:contributor), triggers inference, and asserts the inverse triple appears in either the API response or the inference panel UI"
      - "Alternatively, fix the pre-existing _store_inferred_triples bug so inference actually produces new triples, then test the flow"
---

# Phase 40: E2E Test Coverage for v2.4 Verification Report

**Phase Goal:** Playwright tests cover all v2.4 user-visible features
**Verified:** 2026-03-05T09:15:00Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | E2E tests verify bidirectional links appear after creating a relationship (inference working) | PARTIAL | `inference.spec.ts` has 6 tests but all verify infrastructure (panel loads, API responds, filter controls exist). No test creates an edge and verifies the inverse appears. Deviation documented in SUMMARY -- seed data already has both directions, plus a pre-existing `_store_inferred_triples` bug blocks new inference. |
| 2 | E2E tests verify global lint dashboard loads, filters, and sorts results correctly | VERIFIED | `lint-dashboard.spec.ts` has 7 tests: dashboard loads via htmx revealed, creates invalid object to produce violations, severity filter narrows rows and validates class names, sort control accepts multiple options, search filter works, health badge attached, API returns HTML partial. |
| 3 | E2E tests verify edit form helptext renders and collapses | VERIFIED | `helptext.spec.ts` has 4 tests: toggle presence check (with graceful skip), form-level expand/collapse via details/summary, field-level toggle via button, markdown rendering verified by checking for HTML formatting elements. |
| 4 | E2E tests verify each bug fix (accent bar, card borders, Ctrl+K, tab bleed, dark chevrons, concept search) | VERIFIED | `bug-fixes.spec.ts` has 6 tests: BUG-04 (accent colors differ between Note and Person), BUG-05 (flip-card-front has border), BUG-06 (Ctrl+K opens ninja-keys), BUG-07 (inactive tabs lack active accent border), BUG-08 (chevron SVGs have non-zero dimensions), BUG-09 (concept search finds results in ninja-keys shadow DOM). |

**Score:** 3/4 truths verified (1 partial)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `e2e/tests/09-inference/inference.spec.ts` | Inference feature E2E tests, min 80 lines | VERIFIED | 190 lines, 6 tests, substantive infrastructure tests |
| `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` | Lint dashboard E2E tests, min 60 lines | VERIFIED | 257 lines, 7 tests, full filter/sort/search coverage |
| `e2e/tests/11-helptext/helptext.spec.ts` | Edit form helptext E2E tests, min 40 lines | VERIFIED | 143 lines, 4 tests with graceful skip pattern |
| `e2e/tests/12-bug-fixes/bug-fixes.spec.ts` | Bug fix regression E2E tests, min 80 lines | VERIFIED | 275 lines, 6 tests covering BUG-04 through BUG-09 |
| `e2e/tests/06-settings/vfs-settings.spec.ts` | VFS Settings UI tests (bonus) | VERIFIED | 144 lines, 6 tests covering token CRUD and endpoint display |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `inference.spec.ts` | `/api/inference/run` | API call to trigger inference | WIRED | 2 references: POST call in test + htmx attribute check |
| `inference.spec.ts` | `/api/commands` (edge.create) | Edge creation for test setup | NOT_WIRED | No edge.create call exists -- deviation from plan |
| `lint-dashboard.spec.ts` | `/browser/lint-dashboard` | Bottom panel tab loading dashboard | WIRED | 25 references throughout file |
| `helptext.spec.ts` | Edit form UI | Mode toggle to edit | WIRED | Opens in read mode, clicks `.mode-toggle`, waits for `.object-face-edit.face-visible` |
| `bug-fixes.spec.ts` | Dockview tab accent | `--tab-accent-color` CSS variable | WIRED | 2 references reading computed style from `.dv-active-group` |
| `bug-fixes.spec.ts` | ninja-keys command palette | Ctrl+K keyboard shortcut | WIRED | 7 references including attribute checks and shadow DOM search |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| TEST-05 | 40-01, 40-02 | Playwright E2E tests cover all v2.4 user-visible features | PARTIAL | 23 new tests across 4 spec files + 6 bonus VFS tests. Lint dashboard, helptext, and bug fix coverage is complete. Inference coverage tests infrastructure but not the specific bidirectional-link-after-edge-creation user flow. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No TODO/FIXME/placeholder patterns found in any test file |

### Human Verification Required

### 1. Inference Tests Actually Pass

**Test:** Run `cd e2e && npx playwright test tests/09-inference/ --project=chromium`
**Expected:** All 6 tests pass
**Why human:** Docker stack must be running; cannot verify test execution programmatically

### 2. Lint Dashboard Tests Actually Pass

**Test:** Run `cd e2e && npx playwright test tests/10-lint-dashboard/ --project=chromium`
**Expected:** All 7 tests pass
**Why human:** Requires live Docker stack with triplestore containing seed data

### 3. Helptext Tests Pass (or Skip Gracefully)

**Test:** Run `cd e2e && npx playwright test tests/11-helptext/ --project=chromium`
**Expected:** 4 tests pass or skip with informative message if no helptext configured
**Why human:** Depends on whether basic-pkm shapes have helptext annotations

### 4. Bug Fix Regression Tests Pass

**Test:** Run `cd e2e && npx playwright test tests/12-bug-fixes/ --project=chromium`
**Expected:** All 6 tests pass
**Why human:** Requires live browser environment for CSS computed style checks

### 5. Full Suite Regression Check

**Test:** Run `cd e2e && npx playwright test --project=chromium`
**Expected:** No regressions beyond pre-existing failures
**Why human:** Full suite takes several minutes and requires Docker stack

### Gaps Summary

One gap identified with the inference test coverage:

**Success Criterion 1 is partially met.** The inference spec tests infrastructure comprehensively (panel rendering, API endpoints, filter controls, htmx refresh, config endpoint) but does NOT test the specific user-visible behavior described in the success criterion: "create a relationship, run inference, see bidirectional links appear." This gap exists because:

1. The basic-pkm seed data already includes both sides of inverseOf relationships, so owl:inverseOf inference produces zero new triples
2. A pre-existing bug in `_store_inferred_triples` causes SPARQL 400 errors when rdfs:domain/rdfs:range inference produces triples with literal subjects
3. The SHACL-AF rules graph is not loaded during model install, making sh:rule inference non-functional

These are pre-existing issues (not caused by Phase 40), but they prevent the success criterion from being fully tested. To close this gap, either:
- Fix the pre-existing inference bugs first, then add the edge-create-and-verify test
- Or modify seed data to NOT include both inverse directions, allowing owl:inverseOf inference to produce verifiable new triples

**Bonus:** The VFS Settings UI tests (6 tests in `vfs-settings.spec.ts`) were added beyond the original scope, covering token generation, revocation, and endpoint display.

---

_Verified: 2026-03-05T09:15:00Z_
_Verifier: Claude (gsd-verifier)_
