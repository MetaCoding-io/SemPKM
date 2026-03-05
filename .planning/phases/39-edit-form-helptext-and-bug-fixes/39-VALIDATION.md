---
phase: 39
slug: edit-form-helptext-and-bug-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (chromium project) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd e2e && npx playwright test --project=chromium -g "helptext"` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Manual browser verification (htmx hot-reload)
- **After every plan wave:** Run `cd e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 39-01-01 | 01 | 1 | HELP-01 | manual + e2e | Manual browser check; E2E deferred to Phase 40 | N/A | ⬜ pending |
| 39-01-02 | 01 | 1 | HELP-01 | manual | Manual browser check (shapes JSON-LD annotation) | N/A | ⬜ pending |
| 39-02-01 | 02 | 1 | BUG-04 | manual + e2e | Manual browser check; E2E deferred to Phase 40 | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. E2E tests for HELP-01 and BUG-04 are deferred to Phase 40 (TEST-05). Manual verification during implementation is sufficient. Existing tests should not regress.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Form-level helptext renders as collapsible markdown | HELP-01 | Visual rendering, markdown content | Open Note edit form, verify collapsed section above fields, expand and check markdown renders |
| Field-level helptext shows ? icon and expands inline | HELP-01 | Visual positioning, icon visibility | Open Note edit form, verify ? icons next to fields, click to expand, verify markdown |
| Tab accent bar uses type-specific color | BUG-04 | CSS visual verification | Open tabs for Note (teal), Project (indigo), Concept (amber), Person (rose), verify border color changes per active tab |
| Accent color works in dark mode | BUG-04 | Theme-specific visual check | Toggle dark mode, verify accent colors are visible and readable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
