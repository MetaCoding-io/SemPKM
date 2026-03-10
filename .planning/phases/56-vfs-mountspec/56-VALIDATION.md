---
phase: 56
slug: vfs-mountspec
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (E2E) + pytest (if backend unit tests exist) |
| **Config file** | `e2e/playwright.config.ts` |
| **Quick run command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test tests/vfs-webdav.spec.ts --project=chromium` |
| **Full suite command** | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd e2e && npx playwright test tests/vfs-webdav.spec.ts --project=chromium`
- **After every plan wave:** Run `cd e2e && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 56-01-01 | 01 | 1 | VFS-01 | integration | `cd e2e && npx playwright test tests/vfs-webdav.spec.ts -g "mount definition" --project=chromium` | ❌ W0 | ⬜ pending |
| 56-02-01 | 02 | 1 | VFS-02 | integration | `cd e2e && npx playwright test tests/vfs-webdav.spec.ts -g "mount strategy" --project=chromium` | ❌ W0 | ⬜ pending |
| 56-02-02 | 02 | 1 | VFS-03 | integration | `cd e2e && npx playwright test tests/vfs-webdav.spec.ts -g "mount dispatch" --project=chromium` | ❌ W0 | ⬜ pending |
| 56-03-01 | 03 | 2 | VFS-04 | integration | `cd e2e && npx playwright test tests/vfs-webdav.spec.ts -g "frontmatter write" --project=chromium` | ❌ W0 | ⬜ pending |
| 56-04-01 | 04 | 2 | VFS-05 | e2e | `cd e2e && npx playwright test tests/06-settings/vfs-mounts.spec.ts --project=chromium` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `e2e/tests/vfs-webdav.spec.ts` — extend with mount strategy tests (VFS-01, VFS-02, VFS-03, VFS-04)
- [ ] `e2e/tests/06-settings/vfs-mounts.spec.ts` — settings UI mount management tests (VFS-05)
- [ ] No backend unit test framework exists — E2E tests via Playwright API requests cover the integration layer

*Existing infrastructure covers Playwright framework; test files need stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live preview of directory structure in mount form | VFS-05 | Visual layout verification | 1. Open Settings > VFS > Add Mount 2. Select "by-tag" strategy 3. Verify preview shows tag-based folder structure |
| Multi-folder object editing consistency | VFS-02 | Concurrency edge case | 1. Create mount with by-tag strategy 2. Edit object appearing in multiple tag folders 3. Verify both copies update 4. Edit stale copy, verify 412 response |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
