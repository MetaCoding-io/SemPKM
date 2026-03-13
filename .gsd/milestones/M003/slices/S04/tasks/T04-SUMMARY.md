---
id: T04
parent: S04
milestone: M003
provides:
  - Playwright E2E tests for tag pills on seed objects
  - Playwright E2E tests for by-tag explorer mode (folders, expansion, object click-through)
  - Updated explorer-mode-switching tests expecting real tag content instead of placeholder
key_files:
  - e2e/tests/20-tags/tag-explorer.spec.ts
  - e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts
key_decisions:
  - Expand collapsed properties section before asserting tag pills (properties-collapsible starts collapsed by default)
patterns_established:
  - Tag explorer E2E follows VFS explorer pattern: expand folder → wait for children → click object leaf → verify tab opens
  - Properties toggle click required before inspecting read-view property values in E2E tests
observability_surfaces:
  - none (test-only task — failures produce Playwright traces and screenshots)
duration: 30m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T04: E2E test for tag pills and by-tag explorer mode

**Created 2 Playwright E2E tests verifying tag pill rendering and by-tag explorer functionality, and updated existing explorer-mode-switching tests to expect real tag content.**

## What Happened

Created `e2e/tests/20-tags/tag-explorer.spec.ts` with 2 tests:

1. **tag pills visible on object with tags** — Navigates to workspace, expands a type section in the by-type tree, opens a seed object, clicks the properties toggle to expand the collapsed properties section, then asserts `.tag-pill` elements are visible with `#` prefix and individual (non-comma-separated) values.

2. **by-tag explorer shows tag folders and expansion works** — Switches explorer dropdown to by-tag, asserts ≥3 tag folders with `[data-testid="tag-folder"]` are visible, verifies `#`-prefixed labels and count badges, clicks a tag folder to expand, waits for `[data-testid="tag-object"]` children, asserts ≥1 object leaf, clicks the object leaf, and verifies a dockview tab opens.

Updated `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts`:
- Changed the third test from expecting a `[data-testid="explorer-placeholder"]` with "Tag" text to expecting real `[data-testid="tag-folder"]` elements
- Round-trip verification now checks tag folders disappear when switching back to by-type (instead of checking placeholder disappears)

## Verification

- `cd e2e && npx playwright test tests/20-tags/ --reporter=list --project=chromium` — **2 passed**
- `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` — **5 passed**
- Must run separately due to auth rate limit (5 magic-link calls/minute); combined run (7 tests) exceeds limit
- Slice-level checks:
  - `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — 12 passed ✓
  - `cd backend && .venv/bin/pytest tests/test_tag_explorer.py -v` — 21 passed ✓
  - `docker compose exec api python -c "from app.commands.handlers.object_patch import split_tag_values; print(split_tag_values('a,b,c'))"` — `['a', 'b', 'c']` ✓

## Diagnostics

Test-only task. On failure: Playwright generates trace archives and screenshots in `e2e/test-results/`. Run `npx playwright show-trace <trace.zip>` to inspect failed test traces.

## Deviations

- **Properties toggle required**: The task plan assumed `.tag-pill` elements would be directly visible in the object read view. In reality, the properties section is collapsed by default (`.properties-collapsible` with `grid-template-rows: 0fr`). The test needed to click `.properties-toggle-badge` first to expand properties before asserting tag pills.
- **Fresh triplestore required**: Initial test run with stale data showed comma-separated tags. A `docker compose down -v` + rebuild was needed to re-load seed data with proper JSON-LD array tags. This is expected — the seed data fix from T01 only takes effect on fresh data loading.

## Known Issues

- Running `tests/20-tags/` and `tests/19-explorer-modes/` together in a single Playwright invocation (7 tests total) exceeds the 5 magic-link/minute rate limit. They must be run separately. This is a pre-existing constraint documented in other test specs.

## Files Created/Modified

- `e2e/tests/20-tags/tag-explorer.spec.ts` — New E2E test file with 2 tests for tag pills and by-tag explorer
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — Updated by-tag test to expect real tag folders instead of placeholder content
