---
phase: 38
slug: global-lint-dashboard-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (chromium project) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/04-validation/` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/04-validation/`
- **After every plan wave:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 1 | LINT-03, LINT-04 | e2e | `npx playwright test tests/04-validation/lint-dashboard.spec.ts` | ❌ W0 | ⬜ pending |
| 38-01-02 | 01 | 1 | LINT-05, LINT-06, LINT-07 | e2e | `npx playwright test tests/04-validation/lint-dashboard.spec.ts` | ❌ W0 | ⬜ pending |
| 38-02-01 | 02 | 2 | LINT-03 | e2e | `npx playwright test tests/04-validation/lint-dashboard.spec.ts` | ❌ W0 | ⬜ pending |
| 38-02-02 | 02 | 2 | LINT-04, LINT-05 | e2e | `npx playwright test tests/04-validation/lint-dashboard.spec.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/04-validation/lint-dashboard.spec.ts` — new file covering LINT-03 through LINT-07

*Existing test infrastructure (Playwright, config, helpers) already in place. Only the test file is needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Health badge visibility without opening panel | LINT-03 | Visual judgment on badge placement | 1. Load workspace 2. Verify lint health indicator visible without opening bottom panel |
| Large result set scroll performance | LINT-04 | Performance threshold | 1. Load dataset with 100+ violations 2. Scroll/paginate through results 3. Verify no lag |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
