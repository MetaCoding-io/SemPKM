---
phase: 57
slug: spatial-canvas
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright 1.50+ (E2E) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium --grep "canvas"` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~30 seconds (canvas tests only) |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium --grep "canvas"`
- **After every plan wave:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 57-01-01 | 01 | 1 | CANV-01 | E2E | `npx playwright test tests/17-spatial-canvas/snap-to-grid.spec.ts -x` | ❌ W0 | ⬜ pending |
| 57-01-02 | 01 | 1 | CANV-02 | E2E | `npx playwright test tests/17-spatial-canvas/edge-labels.spec.ts -x` | ❌ W0 | ⬜ pending |
| 57-01-03 | 01 | 1 | CANV-03 | E2E | `npx playwright test tests/17-spatial-canvas/keyboard-nav.spec.ts -x` | ❌ W0 | ⬜ pending |
| 57-02-01 | 02 | 1 | CANV-04 | E2E | `npx playwright test tests/17-spatial-canvas/bulk-drop.spec.ts -x` | ❌ W0 | ⬜ pending |
| 57-02-02 | 02 | 1 | CANV-05 | E2E | `npx playwright test tests/17-spatial-canvas/wiki-link-edges.spec.ts -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/17-spatial-canvas/` directory — create for all canvas tests
- [ ] `e2e/tests/17-spatial-canvas/snap-to-grid.spec.ts` — stub for CANV-01
- [ ] `e2e/tests/17-spatial-canvas/edge-labels.spec.ts` — stub for CANV-02
- [ ] `e2e/tests/17-spatial-canvas/keyboard-nav.spec.ts` — stub for CANV-03
- [ ] `e2e/tests/17-spatial-canvas/bulk-drop.spec.ts` — stub for CANV-04
- [ ] `e2e/tests/17-spatial-canvas/wiki-link-edges.spec.ts` — stub for CANV-05
- [ ] Test data: objects with `[[wiki-link]]` syntax in body text for CANV-05 testing

*Existing infrastructure covers framework install — Playwright already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ghost node visual appearance | CANV-05 | Semi-transparent styling hard to assert reliably | Verify ghost nodes appear smaller/transparent, click resolves to full node |
| Focus ring visibility | CANV-03 | Visual styling assertion fragile | Tab through nodes, verify visible focus ring on selected node |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
