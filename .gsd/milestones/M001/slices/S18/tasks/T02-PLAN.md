# T02: 18-tutorials-and-documentation 02

**Slice:** S18 — **Milestone:** M001

## Description

Implement both Driver.js guided tours in a new `tutorials.js` file: the "Welcome to SemPKM" workspace orientation tour and the "Creating Your First Object" htmx-gated tutorial.

Purpose: DOCS-03 and DOCS-04 — the two tutorials that constitute the interactive onboarding experience. These are pure JS; no backend changes.

Output: `frontend/static/js/tutorials.js` with two exported global functions (`startWelcomeTour`, `startCreateObjectTour`) that are called by the buttons in `docs_page.html`.

## Must-Haves

- [ ] "Clicking 'Start Tour' on the Welcome tutorial card launches a Driver.js overlay that steps through the workspace in 10 steps: sidebar, explorer, object types, opening an object, editor area, read/edit toggle, context panel, command palette, saving (Ctrl+S), and closing card"
- [ ] "Clicking 'Start Tour' on the Creating Your First Object card launches a tour where the type picker htmx step waits for DOM load before advancing"
- [ ] "All tour steps use lazy element resolution (function form) for htmx-rendered or conditionally-present content (read/edit toggle, ninja-keys); always-present elements like sidebar and panes use string selectors"
- [ ] "The htmx:afterSwap handler in the create-object tour checks the target element identity to prevent spurious advances from unrelated htmx swaps"
- [ ] "Both tours handle Driver.js not yet loaded gracefully (guard check before calling driver())"

## Files

- `frontend/static/js/tutorials.js`
