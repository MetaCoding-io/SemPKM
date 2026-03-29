---
id: S04
parent: M046
milestone: M046
provides:
  - Ontology viewer E2E tests no longer hit strict mode 'resolved to 2 elements' errors — selectors are now unique
requires:
  []
affects:
  - S06
key_files:
  - backend/app/templates/browser/ontology/ontology_page.html
key_decisions:
  - Placed ABox tab between RBox and Create Class buttons to match E2E selector expectations
patterns_established:
  - (none)
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M046/slices/S04/tasks/T01-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-29T02:36:15.279Z
blocker_discovered: false
---

# S04: Ontology Viewer — Locator Scoping for Dockview Panels

**Eliminated all 'resolved to 2 elements' Playwright strict mode errors in ontology E2E tests by removing a duplicate ontology-tab-content block, fixing an unclosed div, and adding the missing ABox tab.**

## What Happened

The ontology_page.html template contained two `<div class="ontology-tab-content">` blocks — the first was the active implementation with htmx-powered lazy loading, and the second was a stale duplicate with simpler markup. Both blocks defined the same element IDs (`ontology-tbox`, `ontology-rbox`, `ontology-abox`) and data-testid attributes (`tbox-tree`, `rbox-legend`, `abox-browser`), causing Playwright strict mode to fail with 'resolved to 2 elements' on every locator targeting these selectors.

T01 made three surgical changes to the single file `ontology_page.html`:
1. **Removed the entire stale duplicate `ontology-tab-content` block** (~50 lines of dead markup).
2. **Fixed the unclosed RBox pane `</div>`** in the first (active) block — missing closing tag caused DOM nesting corruption.
3. **Added the ABox tab button and pane** — the tab bar was missing the ABox button between RBox and Create Class. The new button has `data-tab="abox"`, htmx lazy-loading via `hx-get="/browser/ontology/abox"`, and matching pane div with `id="ontology-abox"` and `data-testid="abox-browser"`.

After the fix, all 7 element IDs/data-testids appear exactly once. TBox and ABox ontology-viewer E2E tests pass cleanly with zero strict mode errors. Two pre-existing failures remain (RBox data-testid naming mismatch, class creation success-message selector) — these are unrelated to the duplicate element issue and are tracked for S06.

## Verification

Duplicate check: all 7 data-testid attributes (tbox-tree, rbox-legend, abox-browser, ontology-tab-abox) and element IDs (ontology-tbox, ontology-rbox, ontology-abox) appear exactly 1 time each. Single ontology-tab-content block confirmed (grep count = 1). E2E tests `tests/22-ontology/` pass for TBox and ABox specs with zero 'resolved to 2 elements' or 'strict mode' errors in output.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None. Single task, single file change as planned.

## Known Limitations

RBox E2E test fails due to pre-existing data-testid naming mismatch (template appends source suffix to testid). Class creation test fails waiting for .success-message element (pre-existing UI issue). Both are tracked for S06.

## Follow-ups

S06 should address the RBox data-testid naming mismatch and class creation success-message selector as part of the miscellaneous failures sweep.

## Files Created/Modified

- `backend/app/templates/browser/ontology/ontology_page.html` — Removed duplicate ontology-tab-content block (~50 lines), fixed unclosed RBox div, added ABox tab button with htmx lazy-loading and ABox pane div
