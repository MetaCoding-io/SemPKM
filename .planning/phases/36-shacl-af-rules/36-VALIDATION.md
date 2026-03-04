---
phase: 36
slug: shacl-af-rules
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + Playwright (E2E) |
| **Config file** | backend/pyproject.toml (pytest section) |
| **Quick run command** | `docker compose exec api python -m pytest tests/ -x -q --tb=short -k shacl_rules` |
| **Full suite command** | `docker compose exec api python -m pytest tests/ -x -q --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command (SHACL rules tests)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 1 | INF-02 | unit | `pytest tests/ -k manifest_rules` | ❌ W0 | ⬜ pending |
| 36-01-02 | 01 | 1 | INF-02 | unit | `pytest tests/ -k load_rules_graph` | ❌ W0 | ⬜ pending |
| 36-01-03 | 01 | 1 | INF-02 | unit | `pytest tests/ -k shacl_rules_execution` | ❌ W0 | ⬜ pending |
| 36-02-01 | 02 | 2 | INF-02 | integration | `pytest tests/ -k shacl_rule_inference` | ❌ W0 | ⬜ pending |
| 36-02-02 | 02 | 2 | INF-02 | E2E | `npx playwright test -k shacl-rules` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test stubs for manifest rules entrypoint loading
- [ ] Test stubs for Turtle file parsing in loader
- [ ] Test stubs for shacl_rules() integration in inference pipeline
- [ ] Test stubs for sh:rule entailment type classification

*Existing pytest infrastructure covers framework/fixture needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rule-derived triples visible in object read view | INF-02 | Visual verification of inferred column rendering | Navigate to a Project that has Notes with relatedProject; verify hasRelatedNote appears in inferred properties |
| Admin entailment config shows SHACL rules toggle | INF-02 | Admin UI visual verification | Open Admin > Models > basic-pkm entailment config; verify shacl_rules toggle exists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
