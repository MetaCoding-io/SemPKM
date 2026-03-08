# Firefox E2E Test Failure Analysis

**Date:** 2026-03-08
**Test command:** `npx playwright test --project=firefox` from `/home/james/Code/SemPKM/e2e/`

## Overview

| Metric | Value |
|--------|-------|
| Total tests | 223 |
| Passed | 211 |
| Failed | 12 |
| Failure rate | 5.4% |

All 12 failures fall into 3 root causes. The dominant issue (10 tests) is a selector mismatch between test expectations and the current crossfade implementation.

---

## Root Cause 1: `.object-face-edit.face-visible` Selector Timeout (10 tests)

### Symptoms

All 10 tests timeout at 10000ms waiting for the selector `.object-face-edit.face-visible` after clicking the read/edit mode toggle button.

### Root Cause

The object read/edit toggle was refactored from a CSS 3D flip to an **opacity crossfade** (see MEMORY.md "Object Read/Edit Toggle -- Crossfade"). The 3D flip implementation used `.face-visible` and `.face-hidden` CSS classes to control visibility. The crossfade implementation does NOT use these classes.

**Current crossfade mechanism** (`frontend/static/css/workspace.css` lines 1495-1532):
- `toggleObjectMode()` in `workspace.js` toggles `.flipped` on `.object-flip-inner`
- CSS rule `.object-flip-inner.flipped .object-face-edit` sets `opacity: 1; pointer-events: auto`
- No `.face-visible` class is ever added to `.object-face-edit`

**What the tests expect:**
- Tests wait for `.object-face-edit.face-visible` -- a class from the old 3D flip implementation
- This selector never matches because `.face-visible` is never applied in the crossfade flow

**Why this works in Chromium but fails in Firefox:**
This needs further investigation. It is possible that Chromium tests use a different wait strategy, or that the Chromium test project has been updated while Firefox tests were added later using stale selectors. The tests were added in quick task 28 (Firefox E2E extension) and may have copied selectors that happen to work differently across browser projects.

### Affected Tests

| # | File | Line | Test Name |
|---|------|------|-----------|
| 1 | `tests/01-objects/edit-object-ui.spec.ts` | 150 | Cancel button text when entering edit mode |
| 2 | `tests/01-objects/edit-object-ui.spec.ts` | 246 | multi-value reference field persist after save |
| 3 | `tests/01-objects/edit-object-ui.spec.ts` | 319 | title change updates tab bar label after save |
| 4 | `tests/01-objects/edit-object-ui.spec.ts` | 370 | title change updates object toolbar title after save |
| 5 | `tests/01-objects/object-view-redesign.spec.ts` | 221 | shared collapse state carries to edit mode |
| 6 | `tests/01-objects/object-view-redesign.spec.ts` | 274 | 3D flip to edit mode still works after redesign |
| 7 | `tests/11-helptext/helptext.spec.ts` | 52 | edit form has helptext toggle |
| 8 | `tests/11-helptext/helptext.spec.ts` | 68 | form-level helptext expands and collapses |
| 9 | `tests/11-helptext/helptext.spec.ts` | 94 | field-level helptext toggles |
| 10 | `tests/11-helptext/helptext.spec.ts` | 112 | helptext contains formatted markdown |

### Suggested Fix

**Option A (Application fix -- preferred):** Add `.face-visible` class toggling to `toggleObjectMode()` in `workspace.js` so that both the crossfade CSS and the legacy class names are applied. This maintains backward compatibility with any code that checks for `.face-visible`:

```javascript
// In toggleObjectMode(), when switching to edit:
editFace.classList.add('face-visible');
readFace.classList.add('face-hidden');

// When switching to read:
editFace.classList.remove('face-visible');
readFace.classList.remove('face-hidden');
```

**Option B (Test fix):** Change test selectors from `.object-face-edit.face-visible` to `.object-flip-inner.flipped .object-face-edit` to match the actual crossfade implementation. This is less desirable because the tests should verify user-visible behavior, not implementation details.

**Priority:** HIGH -- this single fix resolves 10 of 12 failures (83%).

---

## Root Cause 2: Strict Mode `.markdown-body` Resolves to Multiple Elements (1 test)

### Symptoms

Playwright strict mode error: `.markdown-body` resolves to 8 elements instead of 1.

### Root Cause

The test uses `page.locator('.markdown-body')` without scoping to a specific container. In the workspace layout, multiple object tabs or panel sections may each contain a `.markdown-body` element. With 8 matches, Playwright's strict mode (which requires exactly 1 match for actions/assertions) throws an error.

This likely passes in Chromium if the test runs with fewer tabs open at that point, or if the Chromium project test ordering differs.

### Affected Test

| # | File | Line | Test Name |
|---|------|------|-----------|
| 11 | `tests/01-objects/object-view-redesign.spec.ts` | 66 | Markdown body visible immediately, properties collapsed |

### Suggested Fix

Scope the selector to the active tab or the specific object face:

```typescript
// Instead of:
page.locator('.markdown-body')

// Use:
page.locator('.object-face-read .markdown-body').first()
// or scope to the active dockview panel:
page.locator('.dv-view-container:visible .markdown-body')
```

**Priority:** LOW -- 1 test, straightforward selector fix.

---

## Root Cause 3: Panel Tab Count Mismatch (1 test)

### Symptoms

Test expects exactly 2 panel tabs (EVENT LOG, AI COPILOT) in the bottom panel, but finds 4.

### Root Cause

The bottom panel may be initialized with duplicate tabs in Firefox. Possible causes:
1. **Dockview double-initialization:** The workspace layout JS may fire panel creation twice in Firefox due to different event timing (e.g., `DOMContentLoaded` vs `load` event ordering)
2. **Layout restore collision:** If `sempkm_layout_current` in localStorage contains stale panel state, Dockview may restore panels AND the initialization code may add them again
3. **Firefox htmx timing:** htmx `afterSettle` events may fire differently in Firefox, causing panel setup to run twice

### Affected Test

| # | File | Line | Test Name |
|---|------|------|-----------|
| 12 | `tests/03-navigation/workspace-layout.spec.ts` | 84 | bottom panel exists with EVENT LOG, AI COPILOT tabs |

### Suggested Fix

1. **Investigate:** Run the Firefox test with `--headed` and manually inspect the bottom panel to identify what the 4 tabs are (duplicates? or unexpected extra panels?)
2. **Guard against duplicates:** Add a check in the panel initialization code:
   ```javascript
   // Before adding a panel, check if it already exists
   if (!dockviewApi.getPanel('event-log')) {
       dockviewApi.addPanel({ id: 'event-log', ... });
   }
   ```
3. **Clear localStorage:** Ensure the test setup clears `sempkm_layout_current` before running

**Priority:** MEDIUM -- 1 test, but may indicate a real UI bug visible to Firefox users.

---

## Priority Summary

| Priority | Root Cause | Tests | Fix Effort | Impact |
|----------|-----------|-------|------------|--------|
| HIGH | 1: `.face-visible` selector mismatch | 10 | Small (add class toggle or update selectors) | 83% of failures |
| MEDIUM | 3: Panel tab duplication | 1 | Medium (debug + guard) | Possible real bug |
| LOW | 2: `.markdown-body` strict mode | 1 | Small (scope selector) | Test-only fix |

**Recommended approach:** Fix Root Cause 1 first (Option A -- add `.face-visible` class to crossfade toggle). This resolves 83% of Firefox failures with a single code change. Then address Root Causes 2 and 3 individually.

---

## Environment Notes

- Playwright version: per `e2e/package.json`
- Firefox project added in quick task 28 (commit `13512e7`)
- Tests are sequential (1 worker), test files should not be modified per project constraints
- Docker stack on port 3901
