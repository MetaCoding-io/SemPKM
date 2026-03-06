---
phase: 41
slug: gap-closure-rules-flip-vfs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), Playwright (E2E) |
| **Config file** | `backend/pytest.ini`, `e2e/playwright.config.ts` |
| **Quick run command** | `docker compose exec api pytest tests/ -x -q` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~30 seconds (pytest), ~120 seconds (Playwright) |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec api pytest tests/ -x -q`
- **After every plan wave:** Run `cd e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 41-01-01 | 01 | 1 | INF-02 | integration | `docker compose exec api pytest tests/ -k rules` | ❌ W0 | ⬜ pending |
| 41-01-02 | 01 | 1 | LINT-02 | integration | `docker compose exec api pytest tests/ -k promote` | ❌ W0 | ⬜ pending |
| 41-02-01 | 02 | 1 | BUG-10 | E2E | `cd e2e && npx playwright test --grep flip` | ❌ W0 | ⬜ pending |
| 41-03-01 | 03 | 2 | VFS-01 | E2E | `cd e2e && npx playwright test --grep vfs-browser` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing test infrastructure covers all phase requirements.
- New E2E tests will be added as part of verification within each plan.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Flip card visual — no content bleed-through | BUG-10 | Visual rendering check | Open object, click Edit, verify only edit form is visible, no read-only properties showing through |
| VFS tree navigation | VFS-01 | UI interaction flow | Click VFS sidebar link, verify tree loads, expand model → type → see objects |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
