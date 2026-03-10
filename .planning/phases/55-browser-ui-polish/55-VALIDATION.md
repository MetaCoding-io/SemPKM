---
phase: 55
slug: browser-ui-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (Chromium project) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium --grep "PATTERN" -x` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Interactive verification via playwright-cli (open browser, navigate, test interactions)
- **After every plan wave:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 55-01-01 | 01 | 1 | OBUI-01 | manual-only | Visual verification via playwright-cli | N/A | ⬜ pending |
| 55-01-02 | 01 | 1 | OBUI-02 | manual-only | Visual verification via playwright-cli | N/A | ⬜ pending |
| 55-02-01 | 02 | 2 | OBUI-03 | manual-only | Visual verification via playwright-cli | N/A | ⬜ pending |
| 55-02-02 | 02 | 2 | OBUI-04 | smoke | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium --grep "delete" -x` | ❌ W0 | ⬜ pending |
| 55-03-01 | 03 | 1 | OBUI-05 | manual-only | Visual verification via playwright-cli | N/A | ⬜ pending |
| 55-04-01 | 04 | 1 | VFSX-01 | manual-only | Visual verification via playwright-cli | N/A | ⬜ pending |
| 55-04-02 | 04 | 1 | VFSX-02 | manual-only | Visual verification via playwright-cli | N/A | ⬜ pending |
| 55-04-03 | 04 | 1 | VFSX-03 | manual-only | Visual verification via playwright-cli | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* This phase is UI polish with primarily manual/interactive verification. The existing e2e test suite covers the base functionality (nav tree navigation, object creation, etc.) that this phase extends. Regression testing via the full suite is the primary safety net.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Nav tree refresh button reloads objects | OBUI-01 | UI interaction polish | Click refresh icon in OBJECTS header, verify tree reloads and collapses |
| Plus button opens command palette with Create entries | OBUI-02 | Command palette integration | Click plus icon, verify command palette opens; type "create", verify per-type entries |
| Shift-click selects range in nav tree | OBUI-03 | Complex JS interaction | Click first item, shift-click third item, verify range highlights |
| Edge inspector expands with provenance | OBUI-05 | UI layout verification | Click a relation item, verify inline expansion with predicate QName, timestamp, author, source |
| VFS side-by-side preview | VFSX-01 | Layout verification | Open VFS file, toggle preview, verify horizontal split with rendered markdown |
| VFS consistent icons and loading states | VFSX-02 | Visual polish | Verify Lucide icons for edit/read toggle, spinner during loads, error toasts on failure |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
