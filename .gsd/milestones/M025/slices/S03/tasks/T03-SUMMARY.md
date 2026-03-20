---
id: T03
parent: S03
milestone: M025
provides:
  - Dismissible CTA banner in workspace conditional on demo_mode
  - showDemoCta() / dismissDemoCta() functions with localStorage persistence
  - sempkm:demo-tour-done event listener auto-shows banner after tour completion
key_files:
  - backend/app/templates/browser/workspace.html
  - frontend/static/css/workspace.css
key_decisions:
  - Banner uses fixed bottom positioning with z-index 50 (below ninja-keys 100+, below Driver.js overlay)
  - Slide-up/slide-down CSS animation via @keyframes (no JS animation)
patterns_established:
  - CTA banner show/dismiss pattern: localStorage flag prevents re-showing; custom event triggers initial display
observability_surfaces:
  - "console.log('[SemPKM] CTA banner shown') when banner becomes visible"
  - "localStorage.sempkm_demo_cta_dismissed — '1' if dismissed, delete to re-show"
  - "document.getElementById('demo-cta-banner').style.display — '' visible, 'none' hidden"
duration: 10m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T03: Add dismissible CTA banner conditional on demo_mode

**Added dismissible "Try SemPKM" CTA banner with slide-up animation, GitHub install link, localStorage-backed dismiss, and automatic display after demo tour completion**

## What Happened

Added a fixed-bottom CTA banner to workspace.html inside the existing `{% if demo_mode %}` block. The banner contains a rocket icon, text encouraging Docker installation, a "Get Started" button linking to the GitHub repo, and an X dismiss button. It starts hidden (`display: none`) and is revealed via `showDemoCta()` either when the `sempkm:demo-tour-done` custom event fires (first-time visitor completing the tour) or on page load if `localStorage.sempkm_demo_tour_done` is already set (returning visitor). Dismissing sets `localStorage.sempkm_demo_cta_dismissed` to prevent re-showing.

CSS uses slide-up/slide-down `@keyframes` animations with `translateY`, and all Lucide icon SVGs follow CLAUDE.md rules: CSS-only sizing, `flex-shrink: 0`, `stroke: currentColor`.

## Verification

All 6 task-level verification checks pass:
1. CSS styles present for `.demo-cta-banner`
2. HTML `demo-cta-banner` div in workspace.html
3. `demo_cta_dismissed` localStorage logic in template
4. `z-index: 50` in CSS
5. `flex-shrink: 0` on all CTA SVG rules (5 occurrences in CTA section)
6. `sempkm:demo-tour-done` event listener wired in template

Slice-level checks:
- JS syntax valid (`node -c tutorials.js` passes)
- Zero conflict markers in frontend/backend/scripts
- CTA banner HTML is inside `{% if demo_mode %}` block (line 232)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep "demo-cta-banner" frontend/static/css/workspace.css` | 0 | ✅ pass | <1s |
| 2 | `grep "demo-cta-banner" backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 3 | `grep "demo_cta_dismissed" backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 4 | `grep "z-index: 50" frontend/static/css/workspace.css` | 0 | ✅ pass | <1s |
| 5 | `awk '/Demo CTA Banner/,0' workspace.css \| grep "flex-shrink: 0"` | 0 | ✅ pass | <1s |
| 6 | `grep "sempkm:demo-tour-done" workspace.html` | 0 | ✅ pass | <1s |
| 7 | `node -c frontend/static/js/tutorials.js` | 0 | ✅ pass | <1s |
| 8 | `grep -rn "^<<<<<<< " frontend/ backend/ scripts/` | 1 | ✅ pass (none found) | <1s |

## Diagnostics

- **Console signal:** `[SemPKM] CTA banner shown` logged when banner becomes visible
- **Dismiss state:** `localStorage.getItem('sempkm_demo_cta_dismissed')` — `'1'` means dismissed; `localStorage.removeItem('sempkm_demo_cta_dismissed')` to reset
- **DOM inspection:** `document.getElementById('demo-cta-banner').style.display` — empty string = visible, `'none'` = hidden
- **Banner not appearing?** Check: (1) `demo_mode` is true in template context, (2) `sempkm_demo_cta_dismissed` is not set in localStorage, (3) `sempkm:demo-tour-done` event was dispatched or `sempkm_demo_tour_done` is in localStorage

## Deviations

- Added `console.log('[SemPKM] CTA banner shown')` observability signal not in original plan — added per observability impact pre-flight fix requirement.

## Known Issues

- The slice plan's JS syntax check (`python3 -c "import ast; ast.parse(...)`) incorrectly uses Python's `ast` module on a JavaScript file. Used `node -c` instead for accurate validation. This is a pre-existing issue from the plan, not introduced by this task.

## Files Created/Modified

- `backend/app/templates/browser/workspace.html` — Added CTA banner HTML div and show/dismiss JavaScript inside `{% if demo_mode %}` block
- `frontend/static/css/workspace.css` — Added ~90 lines of `.demo-cta-banner` styles with animations, Lucide icon sizing, and z-index 50
- `.gsd/milestones/M025/slices/S03/tasks/T03-PLAN.md` — Added missing `## Observability Impact` section (pre-flight fix)
