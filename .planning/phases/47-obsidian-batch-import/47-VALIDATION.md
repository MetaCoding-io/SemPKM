---
phase: 47
slug: obsidian-batch-import
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 47 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (e2e) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/14-obsidian-import/` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Manual verification via UI (upload vault, run import, check objects)
- **After every plan wave:** `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/14-obsidian-import/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 47-01-01 | 01 | 1 | OBSI-06 | e2e | `npx playwright test --project=chromium tests/14-obsidian-import/batch-import.spec.ts` | No - W0 | pending |
| 47-01-02 | 01 | 1 | OBSI-07 | e2e | `npx playwright test --project=chromium tests/14-obsidian-import/batch-import.spec.ts` | No - W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/14-obsidian-import/batch-import.spec.ts` -- stubs for OBSI-06, OBSI-07
- [ ] Test vault ZIP with known wiki-links and tags for deterministic assertions

*Existing infrastructure covers test framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE progress bar updates in real-time | OBSI-06 | Visual timing behavior | Upload vault, start import, observe progress bar fills smoothly |
| Post-import summary layout | OBSI-06 | Visual design check | Verify summary shows stats with correct counts |
| "Browse Imported Objects" navigates to results | OBSI-06 | UI navigation flow | Click browse button, verify objects appear in workspace |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
