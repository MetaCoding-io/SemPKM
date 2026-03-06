---
phase: 42
slug: vfs-browser-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright E2E (existing) + manual browser verification |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `curl -s http://localhost:3901/browser/vfs -H 'Cookie: ...' -o /dev/null -w '%{http_code}'` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~5 seconds (curl check), ~120 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run curl check against VFS endpoints
- **After every plan wave:** Verify VFS tab opens and tree expands in browser
- **Before `/gsd:verify-work`:** Full E2E suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 42-01-01 | 01 | 1 | VFS-01 | integration | `curl /browser/vfs` returns 200 | N/A (endpoint test) | pending |
| 42-01-02 | 01 | 1 | VFS-01 | integration | `curl /browser/vfs/{id}/types` returns 200 | N/A | pending |
| 42-01-03 | 01 | 1 | VFS-01 | manual | VFS tree loads, expands, no infinite loop | N/A | pending |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — this is a bug fix phase on existing code.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VFS tree visual hierarchy | VFS-01 | CSS/UX rendering | Open VFS tab, verify model/type/object tree has clear indentation, icons, loading states |
| No infinite retry on error | VFS-01 | Network behavior | Open DevTools Network tab, verify no repeated failing requests |
| Click object opens tab | VFS-01 | Dockview integration | Click an object in VFS tree, verify it opens in workspace tab |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
