---
phase: 58
slug: federation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 58 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright ^1.50.0 (E2E) + pytest (backend unit/integration) |
| **Config file** | `e2e/playwright.config.ts` (E2E), `backend/pyproject.toml` (pytest) |
| **Quick run command** | `cd backend && python -m pytest tests/ -x --tb=short` |
| **Full suite command** | `cd e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~30 seconds (unit), ~120 seconds (E2E) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x --tb=short`
- **After every plan wave:** Run `cd e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (unit), 120 seconds (E2E)

---

## Per-Task Verification Map

| Req ID | Requirement | Test Type | Automated Command | File Exists | Status |
|--------|-------------|-----------|-------------------|-------------|--------|
| FED-01 | Events serialize as RDF Patch | unit | `cd backend && python -m pytest tests/test_patch.py -x` | ❌ W0 | ⬜ pending |
| FED-02 | Export patches since timestamp | integration | `cd e2e && npx playwright test tests/18-federation/export-patches.spec.ts` | ❌ W0 | ⬜ pending |
| FED-03 | Register remote instance | E2E | `cd e2e && npx playwright test tests/18-federation/register-remote.spec.ts` | ❌ W0 | ⬜ pending |
| FED-04 | Pull + apply sync patches | integration | `cd backend && python -m pytest tests/test_sync.py -x` | ❌ W0 | ⬜ pending |
| FED-05 | Sync loop prevention | unit | `cd backend && python -m pytest tests/test_sync_source.py -x` | ❌ W0 | ⬜ pending |
| FED-06 | LDN inbox endpoint | integration | `cd e2e && npx playwright test tests/18-federation/ldn-inbox.spec.ts` | ❌ W0 | ⬜ pending |
| FED-07 | Send notification to remote | E2E | `cd e2e && npx playwright test tests/18-federation/send-notification.spec.ts` | ❌ W0 | ⬜ pending |
| FED-08 | View/act on notifications | E2E | `cd e2e && npx playwright test tests/18-federation/inbox-ui.spec.ts` | ❌ W0 | ⬜ pending |
| FED-09 | HTTP Signature authentication | unit | `cd backend && python -m pytest tests/test_signatures.py -x` | ❌ W0 | ⬜ pending |
| FED-10 | Collaboration UI | E2E | `cd e2e && npx playwright test tests/18-federation/collaboration-ui.spec.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_patch.py` — stubs for FED-01 (RDF Patch serialization/deserialization)
- [ ] `backend/tests/test_signatures.py` — stubs for FED-09 (HTTP Signature sign/verify)
- [ ] `backend/tests/test_sync_source.py` — stubs for FED-05 (loop prevention)
- [ ] `backend/tests/conftest.py` — shared test fixtures (mock triplestore, test keys)
- [ ] `e2e/tests/18-federation/` — directory for federation E2E tests
- [ ] Framework install: `pip install pytest pytest-asyncio` (already declared as dev deps)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Two-instance sync round-trip | FED-04, FED-05 | Requires two running SemPKM stacks | Deploy second stack, register instances bidirectionally, verify sync completes without loops |
| LDN notification delivery to external endpoint | FED-07 | Requires reachable remote instance | Use mock HTTP server or second stack, send notification, verify delivery |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (unit)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
