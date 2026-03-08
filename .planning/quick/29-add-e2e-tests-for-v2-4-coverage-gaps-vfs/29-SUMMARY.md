---
phase: quick-29
plan: 01
subsystem: e2e-tests
tags: [e2e, testing, v2.4, coverage]
dependency_graph:
  requires: [basic-pkm-model, vfs-browser, entailment-config, inference-engine, crossfade-toggle]
  provides: [v24-e2e-coverage]
  affects: [e2e/tests/13-v24-coverage/]
tech_stack:
  added: []
  patterns: [playwright-e2e, htmx-wait-patterns, dockview-openTab]
key_files:
  created:
    - e2e/tests/13-v24-coverage/vfs-browser.spec.ts
    - e2e/tests/13-v24-coverage/admin-entailment.spec.ts
    - e2e/tests/13-v24-coverage/crossfade-and-misc.spec.ts
  modified: []
decisions:
  - Used .object-flip-inner.flipped selector for crossfade tests (not face-visible/face-hidden which are stale plan references)
  - Used model ID "basic-pkm" in VFS tree assertion (lowercase model ID, not display name)
  - Inferred badge test creates fresh objects via API to ensure one-sided relationship triggers inference
metrics:
  duration: 8 min
  completed: "2026-03-08T00:34:10Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 0
---

# Quick Task 29: Add E2E Tests for v2.4 Coverage Gaps (VFS)

15 new e2e tests across 3 files covering VFS browser, admin entailment config, crossfade toggle, inferred badge display, and clear-reload button.

## Commits

| # | Hash | Description |
|---|------|-------------|
| 1 | 745b400 | VFS browser + admin entailment config tests (10 tests) |
| 2 | 4fb9c0f | Crossfade toggle, inferred badge, clear-reload tests (5 tests) |

## Task Details

### Task 1: VFS Browser and Admin Entailment Config Tests

**VFS browser (5 tests):**
- Page loads from direct URL `/browser/vfs`
- Sidebar navigation to VFS works
- Tree shows model nodes ("basic-pkm") after async fetch
- Model auto-expands showing type folders (Note, Concept, Person, Project)
- Clicking a type node reveals object files (seed note titles)

**Admin entailment config (5 tests):**
- Page loads at `/admin/models/basic-pkm/entailment` with h1 "Inference Settings"
- Entailment toggles render with checkboxes (at least 2)
- Type labels include `owl:inverseOf` and `sh:rule`
- inverseOf toggle shows ontology examples
- Save Configuration button is present

### Task 2: Crossfade, Inferred Badge, and Clear & Reload Tests

**Crossfade toggle (3 tests):**
- Toggle switches to edit mode (`.flipped` class, Cancel button, form present)
- Toggle returns to read mode (`.flipped` removed, Edit button, markdown body visible)
- Crossfade uses opacity transition, NOT 3D `preserve-3d` transform

**Inferred badge (1 test):**
- Creates project + person via API, adds one-sided hasParticipant relationship
- Runs inference, verifies `total_inferred > 0`
- Opens person in workspace, checks `.inferred-badge` visible in relations panel

**Clear & Reload button (1 test):**
- Button with "Clear" and "Reload" text exists in `#user-popover` DOM

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed VFS tree model text assertion**
- **Found during:** Task 1
- **Issue:** Plan specified "Basic PKM" but VFS tree renders the model ID "basic-pkm" (lowercase)
- **Fix:** Changed assertion to match `basic-pkm`
- **Files modified:** `e2e/tests/13-v24-coverage/vfs-browser.spec.ts`
- **Commit:** 745b400

**2. [Rule 1 - Bug] Fixed crossfade toggle selectors**
- **Found during:** Task 2
- **Issue:** Plan specified `.object-face-edit.face-visible` and `.face-hidden` selectors which don't exist; actual crossfade uses `.object-flip-inner.flipped` class toggle with CSS opacity transitions
- **Fix:** Updated all crossfade test selectors to use `.object-flip-inner.flipped`
- **Files modified:** `e2e/tests/13-v24-coverage/crossfade-and-misc.spec.ts`
- **Commit:** 4fb9c0f
