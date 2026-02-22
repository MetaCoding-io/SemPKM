---
phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness
plan: 04
subsystem: frontend
tags: [auth-ui, setup-wizard, login, invitation, nginx, vanilla-js, sidebar-refactor, debug-router, health-page, auto-login]

# Dependency graph
requires:
  - phase: 06-02
    provides: "Auth endpoints (setup, magic-link, verify, logout, me, status)"
provides:
  - "Setup wizard page for first-run instance claiming"
  - "Login page with magic link form and auto-login without SMTP"
  - "Invitation acceptance page"
  - "Auth redirect on all dashboard pages (unauthenticated -> login)"
  - "Shared sidebar partial (components/_sidebar.html) with active_page variable"
  - "Debug router serving SPARQL and Commands as Jinja2 templates"
  - "Health page with 3-card grid (Service Status, Data Stores, Email/SMTP)"
  - "API Docs (ReDoc + Swagger) loaded inline via iframe"
  - "Instance reset script (scripts/reset-instance.sh)"
  - "POST /api/auth/invite endpoint for owner invitations"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [auth-redirect-check, sidebar-partial, debug-router, iframe-docs, auto-login-no-smtp]

key-files:
  created:
    - frontend/static/setup.html
    - frontend/static/login.html
    - frontend/static/invite.html
    - frontend/static/js/auth.js
    - backend/app/templates/components/_sidebar.html
    - backend/app/templates/debug/sparql.html
    - backend/app/templates/debug/commands.html
    - backend/app/debug/__init__.py
    - backend/app/debug/router.py
    - scripts/reset-instance.sh
    - scripts/README.md
  modified:
    - frontend/static/css/style.css
    - frontend/nginx.conf
    - backend/app/templates/base.html
    - backend/app/templates/health.html
    - backend/app/templates/browser/workspace.html
    - backend/app/shell/router.py
    - backend/app/auth/router.py
    - backend/app/auth/schemas.py
    - backend/app/main.py
    - docker-compose.yml
  deleted:
    - frontend/static/sparql.html
    - frontend/static/commands.html

key-decisions:
  - "Auth pages served as static HTML by nginx; dashboard pages served by FastAPI Jinja2 templates"
  - "checkAuthStatus() checks /api/auth/me and redirects to login on 401"
  - "Browser assets (workspace.css, split.js, ninja-keys) loaded in base template for htmx compatibility"
  - "Sidebar extracted into Jinja2 partial with active_page variable for DRY navigation"
  - "SPARQL and Commands converted from static HTML to Jinja2 templates via debug router"
  - "MagicLinkRequest relaxed from EmailStr to plain str with @ check for owner@local support"
  - "Auto-login when SMTP not configured: API returns token directly, frontend JS auto-verifies"
  - "Health page redesigned with 3-card grid: Service Status, Data Stores, Email (SMTP)"
  - "API Docs loaded in iframe within content area instead of navigating to new page"
  - "main:not(.content-area) CSS selector to avoid 960px width cap on dashboard"

patterns-established:
  - "Auth redirect pattern: checkAuthStatus() in auth.js checks status + auth/me, redirects unauthenticated users"
  - "Sidebar partial pattern: components/_sidebar.html with active_page Jinja2 variable"
  - "Debug router pattern: FastAPI router for dev tools at /sparql and /commands"
  - "Auto-login pattern: API returns token when SMTP not configured, JS auto-verifies"

requirements-completed: [AUTH-02, AUTH-03, INVITE-01]

# Metrics
duration: 60min (including extensive post-plan iterative UI/UX refinement)
completed: 2026-02-22
---

# Phase 6 Plan 04: Frontend Auth Pages Summary

**Setup wizard, login, and invitation pages with auth redirect, sidebar refactoring, debug tools, health page redesign, and auto-login flow**

## Performance

- **Duration:** ~60 min (30 min plan execution + 30 min post-plan iterative refinement)
- **Completed:** 2026-02-22
- **Tasks:** 2 planned + extensive post-plan work
- **Files created:** 11
- **Files modified:** 10
- **Files deleted:** 2

## Accomplishments

### Plan Execution (Tasks 1-2)
- Three auth pages (setup, login, invite) with vanilla JS form handling
- Auth redirect logic added to all dashboard pages via base.html
- Debug Tools sidebar section with SPARQL and Commands links
- Nginx configured to serve auth pages with cookie forwarding
- Browser workspace assets moved to base template for htmx navigation

### Post-Plan Refinement
- **Sidebar refactor**: Extracted sidebar into `components/_sidebar.html` Jinja2 partial with `active_page` variable controlling active link highlighting across all pages
- **Debug router**: Converted SPARQL and Commands from static HTML to Jinja2 templates served by `backend/app/debug/router.py`, deleted old static files, removed nginx static rules
- **Auto-login flow**: When SMTP is not configured, magic-link endpoint returns token directly in response; frontend JS auto-verifies it for seamless local login without email
- **MagicLinkRequest fix**: Relaxed from `EmailStr` to plain `str` with `@` validation so `owner@local` works; changed login.html input from `type="email"` to `type="text"`
- **Health page redesign**: Redesigned with 3-card grid showing Service Status, Data Stores (SQLite engine/path + RDF4J URL/repository/namespace), and Email (SMTP) configuration
- **API Docs integration**: Added ReDoc and Swagger links in sidebar Debug Tools section; docs load in iframe within content area instead of navigating away
- **Width fix**: Changed `main` CSS to `main:not(.content-area)` to prevent 960px max-width cap on dashboard; changed `#app-content` max-width to 100%
- **Instance reset script**: Created `scripts/reset-instance.sh` for wiping auth DB and tokens
- **Invite endpoint**: Added missing `POST /api/auth/invite` endpoint to close INVITE-01 requirement gap
- **SMTP documentation**: Added commented-out SMTP env vars to docker-compose.yml with setup instructions

## Task Commits

1. **Task 1: Auth pages, JS, nginx** - `27b303b` (feat)
2. **Task 2: Human verification** - approved after iterative fixes:
   - `750d9d7` - Auth redirect to dashboard pages via base template
   - `86a9f93` - Serve sparql/commands pages via nginx
   - `87b247d` - Restyle debug tools to dashboard layout
   - `2151c54` - Add Home link to sidebar
   - `c1a613d` - Load browser assets in base template for htmx
3. **Post-plan commits:**
   - Sidebar refactor into Jinja2 partial with active_page variable
   - Debug router (SPARQL/Commands as Jinja2 templates, static files deleted)
   - Auto-login flow (token returned when no SMTP, JS auto-verify)
   - Health page 3-card redesign (Service Status, Data Stores, Email)
   - API Docs iframe integration
   - Width fixes (main:not(.content-area), #app-content 100%)
   - Instance reset script and scripts/README.md
   - POST /api/auth/invite endpoint
   - SMTP env vars documentation in docker-compose.yml

## Files Created/Modified

### Created
- `frontend/static/setup.html` - Setup wizard page for first-run instance claiming
- `frontend/static/login.html` - Login page with magic link form (type="text" for owner@local)
- `frontend/static/invite.html` - Invitation acceptance page
- `frontend/static/js/auth.js` - Auth status check, setup/login/logout/invite handlers, auto-login
- `backend/app/templates/components/_sidebar.html` - Shared sidebar partial with active_page variable
- `backend/app/templates/debug/sparql.html` - SPARQL console as Jinja2 template
- `backend/app/templates/debug/commands.html` - Commands console as Jinja2 template
- `backend/app/debug/__init__.py` - Debug module init
- `backend/app/debug/router.py` - FastAPI router for /sparql and /commands
- `scripts/reset-instance.sh` - Instance reset (wipe DB, tokens, restart API)
- `scripts/README.md` - Scripts documentation

### Modified
- `frontend/static/css/style.css` - Auth styles, sidebar sections, health grid, config tables, width fixes, docs iframe
- `frontend/nginx.conf` - Auth page locations, cookie forwarding, removed static sparql/commands rules
- `backend/app/templates/base.html` - auth.js, browser assets, sidebar include, loadDocsIframe(), updateActiveNav()
- `backend/app/templates/health.html` - 3-card grid: Service Status, Data Stores, Email (SMTP)
- `backend/app/templates/browser/workspace.html` - Removed duplicate asset blocks (now in base)
- `backend/app/shell/router.py` - active_page context, SMTP/db/triplestore config for health page
- `backend/app/auth/router.py` - POST /api/auth/invite endpoint, token return when no SMTP
- `backend/app/auth/schemas.py` - MagicLinkResponse.token field, MagicLinkRequest str validation
- `backend/app/main.py` - Registered debug_router
- `docker-compose.yml` - Commented SMTP env vars documentation

### Deleted
- `frontend/static/sparql.html` - Replaced by Jinja2 template
- `frontend/static/commands.html` - Replaced by Jinja2 template

## Deviations from Plan

- **Sidebar refactor**: Plan only created auth pages; post-plan work extracted sidebar into shared partial for DRY navigation across all pages
- **Debug router**: Replaced nginx-served static HTML debug tools with FastAPI-served Jinja2 templates for consistent layout
- **Auto-login flow**: Added local development auth flow that works without SMTP (token returned in API response, auto-verified by JS)
- **Health page redesign**: Expanded from simple status display to 3-card layout showing database, triplestore, and SMTP configuration
- **API Docs integration**: Added inline iframe loading for ReDoc and Swagger within dashboard layout
- **Width fixes**: Two rounds of CSS fixes to remove 960px cap on content area
- **Instance reset tooling**: Created scripts/reset-instance.sh for development workflow
- **Invite endpoint**: Discovered and filled INVITE-01 gap (schemas existed but no router endpoint)
- **Email validation relaxation**: Changed from EmailStr to plain str to support owner@local pattern

## Issues Encountered

- Database already claimed from Plan 06-02 testing -- had to reset SQLite DB for fresh setup flow
- Auth redirect wasn't working because dashboard is served by Jinja2 templates, not static HTML -- added auth.js to base.html
- Browser page broke on htmx navigation due to missing CSS/JS assets -- moved all to base template
- Frontend container served cached files -- required `docker compose build --no-cache frontend`
- owner@local rejected by Pydantic EmailStr validator -- relaxed to plain str
- Logout locked user out when no SMTP configured -- added auto-login token return flow
- Bare `main` CSS selector matched `.content-area` causing 960px width cap

## Self-Check: PASSED

All auth pages verified in browser. Setup flow, auth redirect, sidebar navigation, auto-login, health page, debug tools, API docs all working.

---
*Phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness*
*Completed: 2026-02-22*
