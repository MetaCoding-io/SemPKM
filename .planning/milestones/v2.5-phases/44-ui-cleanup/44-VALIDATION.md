---
phase: 44
slug: ui-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright 1.x |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/13-v24-coverage -x` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Manual visual verification in browser (CSS/UI changes)
- **After every plan wave:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -x`
- **Before `/gsd:verify-work`:** Full suite must be green + manual visual UAT
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 1 | UICL-01 | visual | Manual: verify VFS markdown font size matches app | N/A | ⬜ pending |
| 44-01-02 | 01 | 1 | UICL-02 | visual | Manual: verify no spurious underlines in VFS content | N/A | ⬜ pending |
| 44-02-01 | 02 | 1 | UICL-03 | mixed | Manual: per-sub-item visual checks | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. This is a CSS/JS fix phase — existing e2e tests cover workspace navigation, tab management, and object editing. New e2e tests for specific visual rendering details would be brittle and low-value. Manual visual verification is appropriate for CSS fixes.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VFS markdown renders at correct font size | UICL-01 | Visual CSS rendering, pixel-level check would be brittle | Open VFS browser, navigate to markdown file, compare font size to rest of app |
| VFS content has no spurious underlines | UICL-02 | Visual CSS rendering, underline detection fragile across browsers | Open VFS browser, view non-link text, verify no underline styling |
| UI polish sub-items | UICL-03 | Mixed visual/interaction fixes, each sub-item needs individual visual check | Per sub-item: verify visual appearance and interaction behavior |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
