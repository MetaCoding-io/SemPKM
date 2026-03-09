---
phase: 52
slug: bug-fixes-security
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 52 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (E2E), pytest + pytest-asyncio (backend unit) |
| **Config file** | `e2e/playwright.config.ts`, `backend/pyproject.toml` |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/05-admin/ tests/06-settings/ tests/10-lint-dashboard/` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/05-admin/ tests/06-settings/ tests/10-lint-dashboard/`
- **After every plan wave:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 52-01-01 | 01 | 1 | SPARQL-01 | E2E | `npx playwright test tests/05-admin/sparql-console.spec.ts` | Exists, needs role-gating cases | ⬜ pending |
| 52-01-02 | 01 | 1 | SPARQL-01 | E2E | `npx playwright test tests/05-admin/sparql-console.spec.ts` | Needs new test case | ⬜ pending |
| 52-02-01 | 02 | 1 | FIX-01 | E2E | `npx playwright test tests/06-settings/event-log.spec.ts` | Exists, needs compound case | ⬜ pending |
| 52-02-02 | 02 | 1 | FIX-01 | E2E | `npx playwright test tests/06-settings/event-log.spec.ts` | Needs new test case | ⬜ pending |
| 52-03-01 | 03 | 1 | FIX-02 | E2E/manual | `npx playwright test tests/10-lint-dashboard/lint-dashboard.spec.ts` | Exists, may need resize test | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/05-admin/sparql-console.spec.ts` — needs role-gating test cases (guest 403, member restrictions)
- [ ] `e2e/tests/06-settings/event-log.spec.ts` — needs compound event display test + undo test
- [ ] `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` — needs narrow viewport resize test for FIX-02

*Existing infrastructure covers framework needs. Only new test cases required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Lint filter wraps gracefully on narrow viewport | FIX-02 | Visual layout verification | 1. Open workspace, 2. Open lint panel, 3. Resize browser to <800px, 4. Verify filter controls wrap without overflow |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
