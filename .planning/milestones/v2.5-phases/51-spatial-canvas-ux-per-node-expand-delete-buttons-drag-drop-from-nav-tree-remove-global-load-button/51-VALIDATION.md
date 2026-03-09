---
phase: 51
slug: spatial-canvas-ux
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 51 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (e2e) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd e2e && npx playwright test --project=chromium -g "canvas"` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick canvas tests
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 51-01-01 | 01 | 1 | Node controls | manual | Browser test | N/A | ⬜ pending |
| 51-01-02 | 01 | 1 | Drag-drop | manual | Browser test | N/A | ⬜ pending |
| 51-02-01 | 02 | 1 | Expand toggle | manual | Browser test | N/A | ⬜ pending |
| 51-02-02 | 02 | 1 | Sessions | manual | Browser test | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Canvas is a standalone page with client-side JS — visual behaviors require manual browser verification.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Node (+) expand loads neighbors | Expand behavior | Visual canvas interaction | Click (+) on a node, verify neighbor nodes appear in circle |
| Node (x) removes node | Delete behavior | Visual canvas interaction | Click (x) on a node, verify it disappears |
| Drag from nav tree creates node | Drag-drop | Cross-component drag interaction | Drag a nav tree leaf onto canvas, verify node appears at drop location |
| Expand toggle collapses neighbors | Scoped collapse | Stateful visual interaction | Expand a node, click (+) again, verify only its neighbors are removed |
| Named session save/load | Session management | User workflow | Save a session with a name, switch to another, switch back |
| Empty canvas hint | Bootstrap | Visual check | Open fresh canvas, verify hint text displayed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
