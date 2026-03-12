# T01: 18-tutorials-and-documentation 01

**Slice:** S18 — **Milestone:** M001

## Description

Integrate Driver.js 1.4.0 CDN, create the Docs & Tutorials special tab (mirroring the existing special:settings pattern), implement the docs_page.html fragment, and add CSS theming for Driver.js popovers.

Purpose: This plan provides the infrastructure that Plan 02's tutorials depend on — the CDN library, the tab entry point, and the themed popover CSS. DOCS-01 (accessible docs page) and DOCS-02 (Driver.js integration) are both satisfied here.

Output: A working Docs & Tutorials tab in the workspace that loads a static hub page; Driver.js available globally for tutorials defined in Plan 02.

## Must-Haves

- [ ] "Clicking 'Docs & Tutorials' in the Meta sidebar section opens a Docs tab in the editor area (not a navigation away)"
- [ ] "Driver.js 1.4.0 IIFE script and CSS load from jsDelivr CDN in every workspace page"
- [ ] "The Docs tab displays a page listing tutorial launch buttons and documentation links"
- [ ] "The Docs tab does not trigger relations/lint right-pane loading (isSpecial guard)"
- [ ] "Driver.js popovers use project CSS token colors and match the current dark/light theme"

## Files

- `backend/app/templates/base.html`
- `backend/app/templates/browser/docs_page.html`
- `backend/app/browser/router.py`
- `backend/app/templates/components/_sidebar.html`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/css/workspace.css`
- `backend/app/main.py`
- `docker-compose.yml`
