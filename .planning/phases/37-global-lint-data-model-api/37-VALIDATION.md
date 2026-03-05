---
phase: 37
slug: global-lint-data-model-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (e2e) + pytest (unit) |
| **Config file** | `e2e/playwright.config.ts`, `backend/pyproject.toml` |
| **Quick run command** | `cd e2e && npx playwright test tests/04-validation/ --project=chromium` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd e2e && npx playwright test tests/04-validation/ --project=chromium`
- **After every plan wave:** Run `cd e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 37-01-01 | 01 | 1 | LINT-01 | integration | `cd e2e && npx playwright test tests/04-validation/` | Partial (lint-panel.spec.ts exists but tests old endpoints) | ⬜ pending |
| 37-01-02 | 01 | 1 | LINT-01 | integration | `cd e2e && npx playwright test tests/04-validation/` | ❌ W0 | ⬜ pending |
| 37-02-01 | 02 | 2 | LINT-02 | integration | `cd e2e && npx playwright test tests/04-validation/` | ❌ W0 | ⬜ pending |
| 37-02-02 | 02 | 2 | LINT-01, LINT-02 | integration | `cd e2e && npx playwright test tests/04-validation/` | Partial | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Update `e2e/tests/04-validation/lint-panel.spec.ts` — adapt tests for new `/api/lint/*` endpoints and SSE behavior
- [ ] Add API integration test for `/api/lint/results` pagination and filtering
- [ ] Add API integration test for `/api/lint/status` endpoint
- [ ] Add API integration test for `/api/lint/diff` endpoint

*Existing infrastructure partially covers phase requirements — lint-panel tests exist but need migration.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE reconnection after network drop | LINT-02 | Requires network simulation | 1. Open lint panel 2. Restart Docker backend 3. Verify SSE reconnects and panel refreshes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
