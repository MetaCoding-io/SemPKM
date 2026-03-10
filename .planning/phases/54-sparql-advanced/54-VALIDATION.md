---
phase: 54
slug: sparql-advanced
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 54 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright 1.50.0 |
| **Config file** | e2e/playwright.config.ts |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/07-multi-user/` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Manual smoke test in browser (share flow, promote flow, render check)
- **After every plan wave:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 54-01-* | 01 | 1 | SPARQL-04 | integration | Manual: share query, switch user, check Saved dropdown | ❌ W0 | ⬜ pending |
| 54-01-* | 01 | 1 | SPARQL-04 | smoke | Manual: fork shared query, verify in My Queries | ❌ W0 | ⬜ pending |
| 54-02-* | 02 | 2 | SPARQL-07 | integration | Manual: promote query, check My Views nav section | ❌ W0 | ⬜ pending |
| 54-02-* | 02 | 2 | SPARQL-07 | smoke | Manual: click promoted view, verify renderer | ❌ W0 | ⬜ pending |
| 54-02-* | 02 | 2 | SPARQL-07 | smoke | Manual: demote view, verify saved query intact | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- No existing sharing or promotion E2E tests
- Framework already installed (`cd e2e && npx playwright test`)
- Multi-user testing requires two browser sessions or two users in test database
- Manual testing is appropriate — these features involve multi-user flows and visual rendering

*Existing infrastructure covers framework needs. Manual verification for interactive multi-user features.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Share query with specific user | SPARQL-04 | Multi-user flow, browser session switching | As owner: save query, click share icon, select user. Switch to other user: open Saved dropdown, verify "Shared with Me" section shows query |
| Fork shared query | SPARQL-04 | Interactive editor + save flow | As recipient: load shared query, modify, click "Save as my own", verify new entry in My Queries |
| Live update badge on shared query | SPARQL-04 | Requires query modification + recipient re-check | As owner: update shared query text. As recipient: open Saved, verify "Updated" badge |
| Promote query to nav tree view | SPARQL-07 | Visual nav tree + dialog interaction | Save query, click promote icon, select renderer, verify "My Views" section appears in nav tree |
| Promoted view renders correctly | SPARQL-07 | Visual rendering verification | Click promoted view in nav tree, verify results render in selected format (table/cards/graph) |
| Demote view back to saved query | SPARQL-07 | Visual nav tree + data persistence check | Click remove on My Views entry, verify view disappears from nav, saved query still exists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
