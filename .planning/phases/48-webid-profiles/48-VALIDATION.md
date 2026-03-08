---
phase: 48
slug: webid-profiles
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 48 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (e2e) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -g "webid"` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -g "webid"`
- **After every plan wave:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 48-01-01 | 01 | 1 | WBID-01 | e2e | `npx playwright test --project=chromium -g "webid"` | ❌ W0 | ⬜ pending |
| 48-01-02 | 01 | 1 | WBID-05 | e2e | `npx playwright test --project=chromium -g "webid"` | ❌ W0 | ⬜ pending |
| 48-02-01 | 02 | 2 | WBID-02 | e2e + curl | `npx playwright test --project=chromium -g "webid"` | ❌ W0 | ⬜ pending |
| 48-02-02 | 02 | 2 | WBID-03 | e2e + curl | `npx playwright test --project=chromium -g "webid"` | ❌ W0 | ⬜ pending |
| 48-02-03 | 02 | 2 | WBID-04 | e2e | `npx playwright test --project=chromium -g "webid"` | ❌ W0 | ⬜ pending |
| 48-02-04 | 02 | 2 | WBID-06 | e2e + curl | `npx playwright test --project=chromium -g "webid"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/15-webid/webid-profiles.spec.ts` — stubs for WBID-01 through WBID-06
- [ ] Content negotiation testing via Playwright API requests (not just browser navigation)

*Existing infrastructure covers Playwright setup and Docker stack.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mastodon rel="me" verification | WBID-04 | Requires external Mastodon instance | Add SemPKM WebID URL to Mastodon profile, verify green checkmark |
| Content negotiation with curl | WBID-03 | Browser always sends text/html Accept | `curl -H "Accept: text/turtle" http://localhost:3000/users/{username}` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
