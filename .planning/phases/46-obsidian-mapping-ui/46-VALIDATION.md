---
phase: 46
slug: obsidian-mapping-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (e2e), pytest (backend unit) |
| **Config file** | `e2e/playwright.config.ts`, `backend/pyproject.toml` |
| **Quick run command** | `cd e2e && npx playwright test --project=chromium tests/14-obsidian-import/` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~30 seconds |

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
| 46-01-01 | 01 | 1 | OBSI-03 | e2e | `npx playwright test tests/14-obsidian-import/` | ❌ W0 | ⬜ pending |
| 46-01-02 | 01 | 1 | OBSI-04 | e2e | `npx playwright test tests/14-obsidian-import/` | ❌ W0 | ⬜ pending |
| 46-02-01 | 02 | 2 | OBSI-05 | e2e | `npx playwright test tests/14-obsidian-import/` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/14-obsidian-import/mapping-ui.spec.ts` — stubs for OBSI-03, OBSI-04, OBSI-05
- [ ] Test vault fixture with varied type groups and frontmatter keys

*Existing e2e infrastructure (Playwright, test fixtures) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag-drop visual feedback on type mapping | OBSI-03 | Visual styling verification | Upload vault, observe dropdown interactions, verify type mapping table renders correctly |
| Custom IRI input for property mapping | OBSI-04 | Complex input interaction | Map a frontmatter key to custom IRI, verify it persists |
| Preview sample objects render correctly | OBSI-05 | Visual content verification | Complete mapping, verify preview shows correct key-value pairs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
