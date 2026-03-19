---
id: T01
parent: S03
milestone: M015
provides:
  - Context Overlay settings section in extension options page (3 controls)
  - EXT-14 through EXT-21 requirements registered in REQUIREMENTS.md
key_files:
  - extension/options/options.html
  - extension/options/options.js
  - .gsd/REQUIREMENTS.md
key_decisions: []
patterns_established:
  - Context overlay settings follow same DOM ref/load/save pattern as capture defaults
observability_surfaces:
  - "[SemPKM] Settings saved" console log confirms persist; TypeError on null access if DOM IDs mismatch
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Add Context Overlay settings section to options page and register requirements

**Added Context Overlay section with autoCheckContext toggle, contextCheckDelay input, and contextTimeout input to extension options page; registered EXT-14 through EXT-21 as active requirements.**

## What Happened

Added a "Context Overlay" `<section>` to `options.html` between Capture Defaults and the Save footer, containing three controls: a checkbox for autoCheckContext, and number inputs for contextCheckDelay (500–10000ms, step 500) and contextTimeout (1000–30000ms, step 1000). Wired three DOM refs (`$autoCheckCtx`, `$ctxCheckDelay`, `$ctxTimeout`) in `options.js`, updated `loadSettings()` to populate them from stored values with sensible defaults, and updated `saveCurrentSettings()` to persist them with `parseInt` parsing.

Registered EXT-14 through EXT-21 in `.gsd/REQUIREMENTS.md` — 7 requirements owned by M015/S01 (badge, sidebar, open, link, evidence, cache, cross-browser) and 1 by M015/S03 (auto-context toggle). Added corresponding traceability rows and updated the coverage summary (30 active requirements).

## Verification

- `node --check extension/options/options.js` — exit 0, no syntax errors
- `grep "auto-check-context" extension/options/options.html` — finds checkbox input
- `grep "contextCheckDelay" extension/options/options.js` — finds load and save wiring
- `grep "EXT-14" .gsd/REQUIREMENTS.md` — finds active requirement entry and traceability row
- `grep -c "EXT-1[4-9]\|EXT-2[0-1]" .gsd/REQUIREMENTS.md` — returns 16 (8 requirements × 2 sections)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/options/options.js` | 0 | ✅ pass | 8s |
| 2 | `grep "auto-check-context" extension/options/options.html` | 0 | ✅ pass | <1s |
| 3 | `grep "contextCheckDelay" extension/options/options.js` | 0 | ✅ pass | <1s |
| 4 | `grep "EXT-14" .gsd/REQUIREMENTS.md` | 0 | ✅ pass | <1s |
| 5 | `grep -c "EXT-1[4-9]\|EXT-2[0-1]" .gsd/REQUIREMENTS.md` → 16 | 0 | ✅ pass | <1s |

### Slice-level checks (partial — T01 is intermediate task)

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | `node --check extension/options/options.js` | ✅ pass | No syntax errors |
| 2 | E2E test (`extension-context-overlay.spec.ts`) | ⏳ pending | T02 creates the test file |
| 3 | Chapter 33 exists | ⏳ pending | T03 creates the docs |
| 4 | README TOC includes Chapter 33 | ⏳ pending | T03 |
| 5 | Glossary entries | ⏳ pending | T03 |

## Diagnostics

- **Options page load:** If any of the three new DOM IDs (`auto-check-context`, `context-check-delay`, `context-timeout`) are missing from HTML, `loadSettings()` will throw `TypeError: Cannot set properties of null` in extension devtools console on page load.
- **Storage inspection:** After saving, open devtools Application > Storage > chrome.storage.sync to verify `autoCheckContext`, `contextCheckDelay`, `contextTimeout` keys are present.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `extension/options/options.html` — Added Context Overlay section with checkbox and two number inputs
- `extension/options/options.js` — Added 3 DOM refs, wired loadSettings() and saveCurrentSettings() for context overlay keys
- `.gsd/REQUIREMENTS.md` — Registered EXT-14 through EXT-21 as active requirements with traceability rows; updated coverage summary
- `.gsd/milestones/M015/slices/S03/S03-PLAN.md` — Added Observability / Diagnostics section (pre-flight fix)
- `.gsd/milestones/M015/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
