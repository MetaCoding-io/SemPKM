# S03 Assessment — Roadmap Reassessment after S03

**Verdict: Roadmap unchanged.**

## What S03 Retired

- **innerHTML rebuild vs iframe persistence** — dual-layer rendering proven. Embed iframes survive `renderNodes()` rebuilds. Risk fully retired.
- **htmx navigation inside iframes** — `?embed=1` templates load in `base_embed.html` with no sidebar, no URL pushing. Risk fully retired.
- **CANVAS-03, CANVAS-04, CANVAS-05** all validated with 32 unit tests + browser verification.

## S04 Coverage

S04 (E2E Tests & User Guide) remains the only unchecked slice. All its dependencies are satisfied:

- S01 produced resize handles, variable-dimension CSS, extended node model — all working
- S02 produced `/api/canvas/properties` endpoint, flip button, property table — all working
- S03 produced embed templates, dual-layer rendering, toolbar picker, explorer drag-drop — all working

S04's scope is unchanged: Playwright E2E tests for resize, property flip, embed placement, save/load + User Guide Chapter 29.

## Success Criteria Mapping

All 7 success criteria map to S04 as the E2E proof owner. Features are built and browser-verified; S04 provides the automated regression coverage.

## Requirement Coverage

CANVAS-01 through CANVAS-05: all validated. No active requirements remain — S04 is quality/docs work, not feature work. No requirement changes needed.

## Boundary Map

S03 → S04 boundary accurate. S03 delivered everything the boundary map specified: `base_embed.html`, `?embed=1` endpoints, dual-layer rendering, embed node type with `embedConfig`, toolbar picker, explorer drag-drop, canvas document schema extensions, max-8 enforcement. S04 can consume all of these for test authoring.
