---
phase: 53
slug: sparql-power-user
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 53 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright 1.50.0 |
| **Config file** | e2e/playwright.config.ts |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/05-admin/` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Manual smoke test in browser (execute query, check results)
- **After every plan wave:** Run `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 53-01-* | 01 | 1 | SPARQL-02 | integration | Manual: execute query, reload, check history | ❌ W0 | ⬜ pending |
| 53-01-* | 01 | 1 | SPARQL-03 | integration | Manual: save query, reload, check saved list | ❌ W0 | ⬜ pending |
| 53-02-* | 02 | 2 | SPARQL-05 | smoke | Manual: execute query with IRIs, verify pills | ❌ W0 | ⬜ pending |
| 53-02-* | 02 | 2 | SPARQL-06 | smoke | Manual: type in editor, verify suggestions | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- No existing SPARQL-specific E2E tests
- Framework already installed (`cd e2e && npx playwright test`)
- Backend API endpoints (history CRUD, vocabulary) could have pytest unit tests
- Manual testing is appropriate — SPARQL console is interactive/visual

*Existing infrastructure covers framework needs. Manual verification for interactive SPARQL features.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Query history persists server-side | SPARQL-02 | Requires browser session + reload | Execute query, reload page, verify history dropdown shows query |
| Save query with name/description | SPARQL-03 | Requires form interaction + persistence | Save query with name, reload, verify saved queries list |
| IRI cells display as labeled pills | SPARQL-05 | Visual rendering + click interaction | Execute query returning IRIs, verify pills with labels/icons, click to open tab |
| Ontology-aware autocomplete | SPARQL-06 | Editor interaction + suggestion popup | Type prefix/class/predicate in editor, verify suggestions from installed models |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
