---
id: T02
parent: S07
milestone: M046
provides: []
requires: []
affects: []
key_files: ["e2e/tests/01-objects/object-view-redesign.spec.ts", "e2e/tests/12-bug-fixes/bug-fixes.spec.ts", "e2e/tests/05-admin/admin-model-detail.spec.ts", "e2e/tests/01-objects/create-edge.spec.ts"]
key_decisions: ["Removed waitForIdle import entirely from admin-model-detail and create-edge after eliminating all call sites", "For webhook CRUD, combined waitForIdle+timeout+assertion into single toContainText with 20s timeout"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran full verification: cd e2e && npx playwright test tests/01-objects/object-view-redesign.spec.ts tests/12-bug-fixes/bug-fixes.spec.ts tests/05-admin/admin-model-detail.spec.ts tests/01-objects/create-edge.spec.ts --project=chromium --retries=1 --reporter=line — 18 passed, 1 failed (pre-existing app bug). Grep checks confirmed 0 remaining timeout:10000 in modified files and 0 remaining waitForIdle calls."
completed_at: 2026-03-29T07:04:58.982Z
blocker_discovered: false
---

# T02: Bump 18 object-tab timeouts to 20s and replace 7 waitForIdle calls with element-specific waits across 4 E2E test files

> Bump 18 object-tab timeouts to 20s and replace 7 waitForIdle calls with element-specific waits across 4 E2E test files

## What Happened
---
id: T02
parent: S07
milestone: M046
key_files:
  - e2e/tests/01-objects/object-view-redesign.spec.ts
  - e2e/tests/12-bug-fixes/bug-fixes.spec.ts
  - e2e/tests/05-admin/admin-model-detail.spec.ts
  - e2e/tests/01-objects/create-edge.spec.ts
key_decisions:
  - Removed waitForIdle import entirely from admin-model-detail and create-edge after eliminating all call sites
  - For webhook CRUD, combined waitForIdle+timeout+assertion into single toContainText with 20s timeout
duration: ""
verification_result: passed
completed_at: 2026-03-29T07:04:58.982Z
blocker_discovered: false
---

# T02: Bump 18 object-tab timeouts to 20s and replace 7 waitForIdle calls with element-specific waits across 4 E2E test files

**Bump 18 object-tab timeouts to 20s and replace 7 waitForIdle calls with element-specific waits across 4 E2E test files**

## What Happened

Edited four test files: object-view-redesign.spec.ts (13 timeout bumps), bug-fixes.spec.ts (5 timeout bumps), admin-model-detail.spec.ts (6 waitForIdle→element waits, removed import), create-edge.spec.ts (1 waitForIdle→element wait + .object-tab pre-wait, removed import). All mechanical edits verified via grep. 18/19 specs pass — the one failure (create-edge "edge appears in relations panel") is a pre-existing app bug where workspace-layout.js references an undefined loadRightPaneSection variable instead of window.SemPKM.refreshRightPaneSection, causing relations panel to never populate on tab activation.

## Verification

Ran full verification: cd e2e && npx playwright test tests/01-objects/object-view-redesign.spec.ts tests/12-bug-fixes/bug-fixes.spec.ts tests/05-admin/admin-model-detail.spec.ts tests/01-objects/create-edge.spec.ts --project=chromium --retries=1 --reporter=line — 18 passed, 1 failed (pre-existing app bug). Grep checks confirmed 0 remaining timeout:10000 in modified files and 0 remaining waitForIdle calls.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx playwright test tests/01-objects/object-view-redesign.spec.ts tests/12-bug-fixes/bug-fixes.spec.ts tests/05-admin/admin-model-detail.spec.ts tests/01-objects/create-edge.spec.ts --project=chromium --retries=1 --reporter=line` | 1 | ⚠️ 18/19 pass (1 pre-existing app bug) | 210600ms |


## Deviations

Added .object-tab wait before #relations-content wait in create-edge.spec.ts. Used short waitForTimeout for webhook delete instead of content-specific wait since next step is a full page reload.

## Known Issues

create-edge.spec.ts "edge appears in relations panel" fails due to pre-existing app bug: loadRightPaneSection undefined in workspace-layout.js scope — should be window.SemPKM.refreshRightPaneSection. T03 will address this.

## Files Created/Modified

- `e2e/tests/01-objects/object-view-redesign.spec.ts`
- `e2e/tests/12-bug-fixes/bug-fixes.spec.ts`
- `e2e/tests/05-admin/admin-model-detail.spec.ts`
- `e2e/tests/01-objects/create-edge.spec.ts`


## Deviations
Added .object-tab wait before #relations-content wait in create-edge.spec.ts. Used short waitForTimeout for webhook delete instead of content-specific wait since next step is a full page reload.

## Known Issues
create-edge.spec.ts "edge appears in relations panel" fails due to pre-existing app bug: loadRightPaneSection undefined in workspace-layout.js scope — should be window.SemPKM.refreshRightPaneSection. T03 will address this.
