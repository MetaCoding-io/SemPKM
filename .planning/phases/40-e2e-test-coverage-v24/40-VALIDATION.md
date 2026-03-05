---
phase: 40
slug: e2e-test-coverage-v24
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright ^1.50.0 |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd e2e && npx playwright test --project=chromium --grep "PATTERN"` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd e2e && npx playwright test --project=chromium --grep "PATTERN"` (target spec file)
- **After every plan wave:** Run `cd e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 40-01-01 | 01 | 1 | TEST-05a | e2e | `cd e2e && npx playwright test tests/09-inference/ -x` | ❌ W0 | ⬜ pending |
| 40-01-02 | 01 | 1 | TEST-05b | e2e | `cd e2e && npx playwright test tests/10-lint-dashboard/ -x` | ❌ W0 | ⬜ pending |
| 40-02-01 | 02 | 1 | TEST-05c | e2e | `cd e2e && npx playwright test tests/11-helptext/ -x` | ❌ W0 | ⬜ pending |
| 40-02-02 | 02 | 1 | TEST-05d | e2e | `cd e2e && npx playwright test tests/12-bug-fixes/ -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/09-inference/inference.spec.ts` — stubs for TEST-05a
- [ ] `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` — stubs for TEST-05b
- [ ] `e2e/tests/11-helptext/helptext.spec.ts` — stubs for TEST-05c
- [ ] `e2e/tests/12-bug-fixes/bug-fixes.spec.ts` — stubs for TEST-05d

*All test files are new — Wave 0 creates them.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
