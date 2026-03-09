---
phase: 50
slug: user-guide-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 50 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (via existing e2e/ infrastructure) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `npx playwright test tests/screenshots/guide-capture.spec.ts --project=screenshots` |
| **Full suite command** | N/A (docs phase — validation is content review + grep checks) |
| **Estimated runtime** | ~30 seconds (screenshot capture only) |

---

## Sampling Rate

- **After every task commit:** Verify changed markdown files render correctly (syntax, image paths, nav links)
- **After every plan wave:** Review updated chapters for consistency and cross-references
- **Before `/gsd:verify-work`:** Full guide walkthrough, grep for stale terms, verify all navigation links
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 50-01-01 | 01 | 1 | DOCS-03 | grep | `grep -r "Split.js\|flip card\|3D flip" docs/guide/` | ✅ | ⬜ pending |
| 50-01-02 | 01 | 1 | DOCS-01 | manual-only | N/A — content completeness review | N/A | ⬜ pending |
| 50-02-01 | 02 | 1 | DOCS-02 | grep | `ls docs/guide/25-*.md docs/guide/26-*.md 2>/dev/null` | ❌ W0 | ⬜ pending |
| 50-02-02 | 02 | 1 | DOCS-01 | manual-only | N/A — verify feature coverage | N/A | ⬜ pending |
| 50-03-01 | 03 | 2 | DOCS-02 | file-check | `test -d docs/screenshots && ls docs/screenshots/guide-*.png` | ❌ W0 | ⬜ pending |
| 50-04-01 | 04 | 2 | DOCS-01 | grep | `grep -c "WebID\|IndieAuth\|inference\|lint dashboard" docs/guide/*.md` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/screenshots/guide-capture.spec.ts` — screenshot capture spec for guide images (extends existing capture.spec.ts pattern)
- [ ] `docs/screenshots/` directory — verify exists, clean up if needed

*Existing infrastructure covers markdown authoring. Screenshot capture needs new spec file.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All v2.0+ features covered | DOCS-01 | Content completeness cannot be auto-tested | Review TOC against feature list from REQUIREMENTS.md |
| Each feature has dedicated section | DOCS-02 | Page quality/depth requires human review | Spot-check 3-4 feature sections for task-oriented structure |
| No stale references | DOCS-03 | Partial automation via grep, but context matters | Run `grep -r "Split.js\|flip card\|3D flip\|bottom panel.*AI Copilot" docs/guide/` — should return 0 results |
| Navigation links work | DOCS-03 | Cross-reference integrity | Check prev/next footers in all modified chapters |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
