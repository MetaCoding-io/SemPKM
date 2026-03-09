---
phase: 49
slug: indieauth-provider
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (e2e) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -g "indieauth"` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~30 seconds (indieauth tests) |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -g "indieauth"`
- **After every plan wave:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 1 | IAUTH-01 | e2e | `npx playwright test --project=chromium -g "indieauth metadata"` | ❌ W0 | ⬜ pending |
| 49-01-02 | 01 | 1 | IAUTH-02 | e2e | `npx playwright test --project=chromium -g "indieauth authorize"` | ❌ W0 | ⬜ pending |
| 49-02-01 | 02 | 1 | IAUTH-03 | e2e | `npx playwright test --project=chromium -g "indieauth token"` | ❌ W0 | ⬜ pending |
| 49-02-02 | 02 | 1 | IAUTH-04 | e2e | `npx playwright test --project=chromium -g "indieauth introspect"` | ❌ W0 | ⬜ pending |
| 49-03-01 | 03 | 1 | IAUTH-05 | e2e | `npx playwright test --project=chromium -g "indieauth consent"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/16-indieauth/indieauth-flow.spec.ts` — e2e tests covering IAUTH-01 through IAUTH-05
- [ ] Test simulates IndieAuth client: generate PKCE verifier/challenge, hit authorize endpoint, submit consent, exchange code for token, introspect token

*Note: New test files can be created per project rules.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Consent screen visual appearance | IAUTH-05 | CSS/styling not testable via e2e assertions | Visually verify consent page matches SemPKM branding, light/dark theme |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
