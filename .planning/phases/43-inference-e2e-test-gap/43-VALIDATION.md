---
phase: 43
slug: inference-e2e-test-gap
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright E2E (existing) + pytest (existing) |
| **Config file** | `e2e/playwright.config.ts`, `backend/pyproject.toml` |
| **Quick run command** | `cd e2e && npx playwright test tests/09-inference/ --project=chromium` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~30 seconds (inference tests), ~120 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run inference test subset
- **After every plan wave:** Run full E2E suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 43-01-01 | 01 | 1 | TEST-05 | unit | `python -c "from app.inference.service import ..."` | N/A | pending |
| 43-01-02 | 01 | 1 | TEST-05 | e2e | `npx playwright test tests/09-inference/` | exists | pending |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — tests extend existing E2E suite.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Inverse triple visible in inference panel | TEST-05 | Visual rendering | Create one-sided relationship, run inference, check panel shows inverse |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
