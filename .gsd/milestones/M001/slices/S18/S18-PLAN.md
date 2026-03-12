# S18: Tutorials And Documentation

**Goal:** Integrate Driver.
**Demo:** Integrate Driver.

## Must-Haves


## Tasks

- [x] **T01: 18-tutorials-and-documentation 01**
  - Integrate Driver.js 1.4.0 CDN, create the Docs & Tutorials special tab (mirroring the existing special:settings pattern), implement the docs_page.html fragment, and add CSS theming for Driver.js popovers.

Purpose: This plan provides the infrastructure that Plan 02's tutorials depend on — the CDN library, the tab entry point, and the themed popover CSS. DOCS-01 (accessible docs page) and DOCS-02 (Driver.js integration) are both satisfied here.

Output: A working Docs & Tutorials tab in the workspace that loads a static hub page; Driver.js available globally for tutorials defined in Plan 02.
- [x] **T02: 18-tutorials-and-documentation 02**
  - Implement both Driver.js guided tours in a new `tutorials.js` file: the "Welcome to SemPKM" workspace orientation tour and the "Creating Your First Object" htmx-gated tutorial.

Purpose: DOCS-03 and DOCS-04 — the two tutorials that constitute the interactive onboarding experience. These are pure JS; no backend changes.

Output: `frontend/static/js/tutorials.js` with two exported global functions (`startWelcomeTour`, `startCreateObjectTour`) that are called by the buttons in `docs_page.html`.

## Files Likely Touched

- `backend/app/templates/base.html`
- `backend/app/templates/browser/docs_page.html`
- `backend/app/browser/router.py`
- `backend/app/templates/components/_sidebar.html`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/css/workspace.css`
- `backend/app/main.py`
- `docker-compose.yml`
- `frontend/static/js/tutorials.js`
