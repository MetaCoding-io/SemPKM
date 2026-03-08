---
phase: 45
slug: obsidian-vault-scanner
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (e2e), pytest (backend unit) |
| **Config file** | `e2e/playwright.config.ts`, `backend/pytest.ini` |
| **Quick run command** | `cd e2e && npx playwright test --project=chromium tests/14-obsidian-import/` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~30 seconds (import tests only) |

---

## Sampling Rate

- **After every task commit:** Run `cd e2e && npx playwright test --project=chromium tests/14-obsidian-import/`
- **After every plan wave:** Run `cd e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 45-01-01 | 01 | 1 | OBSI-01 | e2e | `npx playwright test tests/14-obsidian-import/vault-upload.spec.ts` | ❌ W0 | ⬜ pending |
| 45-01-02 | 01 | 1 | OBSI-02 | e2e | `npx playwright test tests/14-obsidian-import/scan-results.spec.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/14-obsidian-import/vault-upload.spec.ts` — stubs for OBSI-01
- [ ] `e2e/tests/14-obsidian-import/scan-results.spec.ts` — stubs for OBSI-02

*Existing infrastructure covers test framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE progress bar animation | OBSI-02 | Visual timing | Upload large vault, verify progress bar updates smoothly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
