---
phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness
verified: 2026-02-22T14:00:00Z
status: human_needed
score: 7/7 success criteria verified
re_verification: true
previous_status: gaps_found
previous_score: 6/7
gaps_closed:
  - "Owner can invite members and guests via POST /api/auth/invite endpoint — endpoint now exists in backend/app/auth/router.py (lines 199-215), InviteRequest/InviteResponse imported and used, require_role('owner') enforced, auth_service.create_invitation() wired"
gaps_remaining: []
regressions: []
human_verification:
  - test: "First-run setup flow in browser"
    expected: "Navigate to http://localhost:3000/setup.html, see the setup wizard, enter the terminal setup token, click Claim Instance, receive a session cookie, and be redirected to the main dashboard"
    why_human: "Requires running docker-compose, inspecting terminal logs, and verifying browser cookie issuance with DevTools"
  - test: "Auth redirect behavior on dashboard"
    expected: "When not authenticated, navigating to the main dashboard (/) redirects to /login.html. After login, navigating to / shows the dashboard."
    why_human: "Requires browser interaction and cookie manipulation"
  - test: "Logout clears session"
    expected: "After clicking logout, the sempkm_session cookie is cleared and the user is redirected to /login.html"
    why_human: "Cookie removal and redirect requires browser verification"
---

# Phase 6: User and Team Management Verification Report

**Phase Goal:** Users can authenticate, manage roles (owner/member/guest), and control access so SemPKM supports multiple users per instance with passwordless login, session-based auth, and event provenance tracking
**Verified:** 2026-02-22T14:00:00Z
**Status:** human_needed (all automated checks pass; 3 items require browser verification)
**Re-verification:** Yes — after gap closure (previous status: gaps_found, previous score: 6/7)

---

## Re-Verification Summary

The single gap from the initial verification has been closed.

**Gap closed:** POST /api/auth/invite endpoint now exists at `backend/app/auth/router.py` lines 199-215:
- `InviteRequest` and `InviteResponse` are imported (lines 19-20) and used (lines 201, 212)
- `require_role("owner")` is enforced via `Depends(require_role("owner"))` (line 203)
- `auth_service.create_invitation(email=body.email, role=body.role, invited_by=current_user.id)` is called (lines 207-211)
- `InviteResponse(message=..., invitation_id=str(invitation.id))` is returned (lines 212-215)

**Regressions:** None detected. All previously-passing checks still pass (auth dependencies on all routers, provenance wiring, docker-compose port isolation, frontend pages).

---

## Goal Achievement

### Success Criteria from ROADMAP.md

| # | Success Criterion | Status | Evidence |
|---|------------------|--------|----------|
| 1 | User can claim a local instance via setup wizard (enter terminal token, become owner) with zero-friction first-run | VERIFIED | `main.py` lifespan displays setup token; `router.py` POST /auth/setup verified; `setup.html` + `auth.js` handle form submission; `nginx.conf` serves the page |
| 2 | System authenticates users via passwordless magic links (cloud) or setup token (local) with session-based cookies | VERIFIED | `tokens.py` creates/verifies signed magic link tokens; `router.py` POST /auth/verify creates session; httpOnly `sempkm_session` cookie set via `_set_session_cookie()`; POST /auth/magic-link generates token (SMTP deferred, as designed) |
| 3 | Owner can invite members and guests, each with appropriate access level | VERIFIED | POST /api/auth/invite now exists (lines 199-215 of router.py); requires `owner` role; delegates to `auth_service.create_invitation()`; `InviteRequest` validates role is `member` or `guest` only; `invite.html` acceptance page works via `/api/auth/verify` |
| 4 | All write endpoints require owner or member role; all read endpoints require authentication; health stays public | VERIFIED | `commands/router.py` has `Depends(require_role("owner", "member"))`; `sparql/router.py` has `Depends(get_current_user)` on both GET and POST; `models/router.py` has `require_role("owner")` on install/remove and `get_current_user` on list; `validation/router.py` has `Depends(get_current_user)`; `health/router.py` has no auth dependency (intentionally public) |
| 5 | Every user-initiated write event records which user performed the action (sempkm:performedBy provenance) | VERIFIED | `events/models.py` defines `EVENT_PERFORMED_BY = SEMPKM.performedBy`; `events/store.py` commit() accepts `performed_by: URIRef | None` and appends `(event_iri, EVENT_PERFORMED_BY, performed_by)` when provided; `commands/router.py` constructs `URIRef(f"urn:sempkm:user:{user.id}")` and passes it to `event_store.commit()` |
| 6 | SQL database (SQLite local, PostgreSQL cloud) stores user accounts, sessions, invitations, and instance config | VERIFIED | `db/engine.py` dual-database factory; `auth/models.py` User, UserSession, Invitation, InstanceConfig ORM models; `migrations/versions/001_initial_auth_tables.py` creates all 4 tables; `pyproject.toml` includes sqlalchemy, aiosqlite, asyncpg |
| 7 | RDF4J triplestore port is not exposed to host; data volume persists across restarts | VERIFIED | `docker-compose.yml` triplestore service has no `ports:` mapping; `sempkm_data` volume mounted at `/app/data` in api service; only ports exposed are `8001:8000` (api dev) and `3000:80` (nginx) |

**Score:** 7/7 success criteria verified

---

## Observable Truths from Plan must_haves

### Plan 01 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SQLAlchemy async engine connects to SQLite database in data volume | VERIFIED | `db/engine.py` creates async engine from `settings.database_url`; default URL is `sqlite+aiosqlite:///./data/sempkm.db` |
| 2 | Alembic migrations create users, sessions, invitations, and instance_config tables | VERIFIED | `migrations/versions/001_initial_auth_tables.py` creates all 4 tables with indexes; `migrations/env.py` has `render_as_batch=True` in both offline and online modes |
| 3 | ORM models support both SQLite and PostgreSQL via same schema | VERIFIED | String(20) for role fields (no native Enum); `db/engine.py` adds SQLite-specific `check_same_thread=False` connect arg conditionally |
| 4 | RDF4J triplestore port is no longer exposed to the host | VERIFIED | `docker-compose.yml` triplestore service has no `ports:` section; confirmed via grep |
| 5 | SQLite database file persists across container restarts via data volume | VERIFIED | `sempkm_data:/app/data` volume mount in docker-compose.yml |
| 6 | SECRET_KEY is auto-generated on first run and persisted to data volume | VERIFIED | `tokens.py` `_get_secret_key()` reads from `settings.secret_key_path` (./data/.secret-key), auto-generates if missing |

### Plan 02 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | On first startup with no users, setup token is displayed in terminal and persisted to disk | VERIFIED | `main.py` lifespan: if not setup_complete, calls `load_or_create_setup_token()`, logs "FIRST-RUN SETUP" with token |
| 2 | Owner can claim instance by entering setup token, creating owner user and session | VERIFIED | `router.py` POST /auth/setup: verifies `setup_mode`, matches token, calls `auth_service.create_owner()`, `auth_service.create_session()`, sets httpOnly cookie |
| 3 | Authenticated users receive httpOnly session cookie (sempkm_session) | VERIFIED | `_set_session_cookie()` in router.py: `httponly=True`, `samesite="lax"`, key="sempkm_session" |
| 4 | get_current_user dependency extracts session cookie and returns User or 401 | VERIFIED | `dependencies.py` `get_current_user`: extracts `sempkm_session` cookie via `Depends(get_session_token)`, queries DB for non-expired session, returns User or raises HTTP 401 |
| 5 | require_role dependency checks user role and returns 403 if insufficient | VERIFIED | `dependencies.py` `require_role(*roles)`: factory function returns dependency that raises HTTP 403 if `user.role not in roles` |
| 6 | Magic link token generation and verification work with time-limited signatures | VERIFIED | `tokens.py`: `create_magic_link_token()` uses itsdangerous URLSafeTimedSerializer with salt="magic-link"; `verify_magic_link_token()` catches SignatureExpired, returns None |
| 7 | Sessions auto-extend when past 50% lifetime (sliding window) | VERIFIED | `dependencies.py` `get_current_user()`: computes `midpoint = user_session.expires_at - (total_duration / 2)`, extends if `now > midpoint` |

### Plan 03 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/commands requires authentication with owner or member role | VERIFIED | `commands/router.py`: `user: User = Depends(require_role("owner", "member"))` on `execute_commands` |
| 2 | GET/POST /api/sparql requires authentication (any role can query) | VERIFIED | `sparql/router.py`: `user: User = Depends(get_current_user)` on both `sparql_get` and `sparql_post` |
| 3 | POST /api/models/install and DELETE /api/models/{id} require owner role | VERIFIED | `models/router.py`: `user: User = Depends(require_role("owner"))` on both `install_model` and `remove_model` |
| 4 | GET /api/models requires authentication (any role) | VERIFIED | `models/router.py`: `user: User = Depends(get_current_user)` on `list_models` |
| 5 | Events created through commands include sempkm:performedBy with user IRI | VERIFIED | `commands/router.py`: `user_iri = URIRef(f"urn:sempkm:user:{user.id}")`, `event_store.commit(operations, performed_by=user_iri)` |
| 6 | Pre-Phase-6 events without performedBy are handled gracefully | VERIFIED | `events/store.py`: `if performed_by is not None:` guard — system operations that omit performed_by produce no performedBy triple |
| 7 | GET /api/health remains public (no auth required) | VERIFIED | `health/router.py`: no auth dependency on `health_check`; docstring explicitly states "intentionally public" |
| 8 | Validation endpoints require authentication (any role) | VERIFIED | `validation/router.py`: `user: User = Depends(get_current_user)` on both `/validation/latest` and `/validation/{event_id}` |

### Plan 04 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User sees a setup wizard page on first visit to an unclaimed instance | VERIFIED | `frontend/static/setup.html` exists; `auth.js` `checkAuthStatus()` redirects to /setup.html when `data.setup_mode` is true |
| 2 | User can enter setup token and claim instance as owner | VERIFIED | `setup.html` has form with token + optional email inputs; `auth.js` `handleSetupForm()` POSTs to `/api/auth/setup` |
| 3 | User sees a login page when not authenticated | VERIFIED | `frontend/static/login.html` exists; `checkAuthStatus()` redirects to /login.html on 401 from /auth/me |
| 4 | User can request a magic link email via the login page | VERIFIED | `login.html` has email form; `auth.js` `handleLoginForm()` POSTs to `/api/auth/magic-link` |
| 5 | Owner can invite a user, and invitee can accept via a link that creates their account | VERIFIED | POST /api/auth/invite (lines 199-215) creates invitation via `auth_service.create_invitation()`; `invite.html` exists and `handleInviteAccept()` POSTs to `/api/auth/verify` with URL token for acceptance |
| 6 | Nginx routes auth pages and proxies cookies correctly | VERIFIED | `nginx.conf` has explicit `location = /setup.html`, `/login.html`, `/invite.html` blocks; `/api/` proxy has `proxy_set_header Cookie $http_cookie; proxy_pass_header Set-Cookie;` |

---

## Required Artifacts

| Artifact | Exists | Substantive | Wired | Status |
|----------|--------|-------------|-------|--------|
| `backend/app/db/engine.py` | Yes | Yes (dual-DB factory, conditional connect_args) | Yes (imported in session.py and main.py) | VERIFIED |
| `backend/app/db/session.py` | Yes | Yes (async_sessionmaker, get_db_session dependency) | Yes (used in auth/dependencies.py) | VERIFIED |
| `backend/app/db/base.py` | Yes | Yes (DeclarativeBase) | Yes (imported in auth/models.py, migrations/env.py) | VERIFIED |
| `backend/app/auth/models.py` | Yes | Yes (4 ORM models: User, UserSession, Invitation, InstanceConfig) | Yes (imported across auth subsystem) | VERIFIED |
| `backend/migrations/env.py` | Yes | Yes (render_as_batch=True in both offline/online modes, imports all models) | Yes (Alembic configuration wired to app settings) | VERIFIED |
| `backend/app/config.py` | Yes | Yes (database_url, secret_key, secret_key_path, setup_token_path, session_duration_days, SMTP fields) | Yes (imported everywhere via settings) | VERIFIED |
| `backend/app/auth/tokens.py` | Yes | Yes (create_magic_link_token, verify_magic_link_token, create_invitation_token, verify_invitation_token, setup token functions) | Yes (imported in router.py, service.py) | VERIFIED |
| `backend/app/auth/service.py` | Yes | Yes (AuthService with all CRUD, session lifecycle, invitation flow, sliding window) | Yes (instantiated in main.py, stored on app.state.auth_service) | VERIFIED |
| `backend/app/auth/dependencies.py` | Yes | Yes (get_current_user with sliding window, require_role factory, optional_current_user, get_session_token) | Yes (imported in all protected routers) | VERIFIED |
| `backend/app/auth/schemas.py` | Yes | Yes (SetupRequest, MagicLinkRequest, VerifyTokenRequest, AuthResponse, InviteRequest, InviteResponse, StatusResponse) | Yes (InviteRequest/InviteResponse now imported and used in router.py lines 19-20, 201, 212) | VERIFIED |
| `backend/app/auth/router.py` | Yes | Yes (setup, magic-link, verify, logout, me, status, invite endpoints) | Yes (registered in main.py as auth_router) | VERIFIED |
| `backend/app/main.py` | Yes | Yes (SQL init, AuthService setup, setup mode detection, auth_router registered) | Yes (runs on startup) | VERIFIED |
| `backend/migrations/versions/001_initial_auth_tables.py` | Yes | Yes (creates all 4 tables with proper indexes and FKs) | Yes (Alembic migration infrastructure configured) | VERIFIED |
| `backend/app/events/models.py` | Yes | Yes (EVENT_PERFORMED_BY = SEMPKM.performedBy added) | Yes (imported in events/store.py) | VERIFIED |
| `backend/app/events/store.py` | Yes | Yes (commit() accepts optional performed_by URIRef, appends to event triples when provided) | Yes (called in commands/router.py with performed_by=user_iri) | VERIFIED |
| `backend/app/commands/router.py` | Yes | Yes (require_role("owner", "member"), user_iri construction, performed_by passed to commit()) | Yes (user dependency fully wired) | VERIFIED |
| `backend/app/sparql/router.py` | Yes | Yes (get_current_user on both GET and POST handlers) | Yes (auth dependency injected) | VERIFIED |
| `backend/app/models/router.py` | Yes | Yes (require_role("owner") on install/remove, get_current_user on list) | Yes (auth dependencies injected) | VERIFIED |
| `backend/app/validation/router.py` | Yes | Yes (get_current_user on both validation endpoints) | Yes (auth dependency injected) | VERIFIED |
| `backend/app/health/router.py` | Yes | Yes (no auth dependency, public endpoint documented) | Yes (intentionally unwired from auth) | VERIFIED |
| `frontend/static/setup.html` | Yes | Yes (token input, optional email, "Claim Instance" button, links auth.js) | Yes (form calls handleSetupForm() to POST /api/auth/setup) | VERIFIED |
| `frontend/static/login.html` | Yes | Yes (email input, "Send Magic Link" button, token verification on URL param) | Yes (calls handleLoginForm() and handleVerifyToken()) | VERIFIED |
| `frontend/static/invite.html` | Yes | Yes (auto-reads ?token from URL, shows verification status) | Yes (calls handleInviteAccept() which POSTs to /api/auth/verify) | VERIFIED |
| `frontend/static/js/auth.js` | Yes | Yes (checkAuthStatus, handleSetupForm, handleLoginForm, handleVerifyToken, handleLogout, handleInviteAccept) | Yes (included in all three auth pages) | VERIFIED |
| `frontend/nginx.conf` | Yes | Yes (auth page locations, API proxy with cookie forwarding: proxy_pass_header Set-Cookie, proxy_set_header Cookie) | Yes (serves auth pages as static, proxies API) | VERIFIED |
| `docker-compose.yml` | Yes | Yes (no RDF4J ports, sempkm_data volume, DATABASE_URL/SECRET_KEY env vars) | Yes (used by all services) | VERIFIED |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Evidence |
|------|-----|-----|--------|---------|
| `backend/app/db/engine.py` | `backend/app/config.py` | `settings.database_url` drives engine creation | WIRED | `create_async_engine(settings.database_url, ...)` |
| `backend/app/auth/models.py` | `backend/app/db/base.py` | ORM models inherit from Base | WIRED | Line 15: `from app.db.base import Base`; each model class inherits Base |
| `backend/migrations/env.py` | `backend/app/auth/models.py` | Alembic imports all models for autogenerate | WIRED | Line 18: `from app.auth.models import InstanceConfig, Invitation, User, UserSession` |

### Plan 02 Key Links

| From | To | Via | Status | Evidence |
|------|-----|-----|--------|---------|
| `backend/app/auth/dependencies.py` | `backend/app/auth/models.py` | Session lookup queries UserSession model | WIRED | `select(UserSession).where(UserSession.token == token, UserSession.expires_at > now)` |
| `backend/app/auth/service.py` | `backend/app/db/session.py` | Uses AsyncSession for DB operations | WIRED | Constructor takes `async_sessionmaker[AsyncSession]`; used throughout with `async with self._session_factory() as session:` |
| `backend/app/auth/tokens.py` | `backend/app/config.py` | Uses settings.secret_key for token signing | WIRED | `_get_secret_key()`: checks `settings.secret_key`, falls back to `settings.secret_key_path` |
| `backend/app/auth/router.py` | `backend/app/auth/service.py` | Endpoints delegate to AuthService | WIRED | `_get_auth_service(request)` returns `request.app.state.auth_service`; used in setup, verify, logout, magic-link, and invite endpoints |
| `backend/app/main.py` | `backend/app/db/engine.py` | Lifespan creates SQL engine | WIRED | `sql_engine = create_engine()`, `async with sql_engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)` |

### Plan 03 Key Links

| From | To | Via | Status | Evidence |
|------|-----|-----|--------|---------|
| `backend/app/commands/router.py` | `backend/app/auth/dependencies.py` | `Depends(require_role('owner', 'member'))` | WIRED | Line 85: `user: User = Depends(require_role("owner", "member"))` |
| `backend/app/commands/router.py` | `backend/app/events/store.py` | Passes user_iri to event_store.commit() | WIRED | `user_iri = URIRef(f"urn:sempkm:user:{user.id}")`, `event_result = await event_store.commit(operations, performed_by=user_iri)` |
| `backend/app/sparql/router.py` | `backend/app/auth/dependencies.py` | `Depends(get_current_user)` | WIRED | `user: User = Depends(get_current_user)` on both GET and POST handlers |
| `backend/app/models/router.py` | `backend/app/auth/dependencies.py` | `Depends(require_role('owner'))` for install/remove | WIRED | `user: User = Depends(require_role("owner"))` on both install and remove |

### Plan 04 Key Links

| From | To | Via | Status | Evidence |
|------|-----|-----|--------|---------|
| `frontend/static/setup.html` | `/api/auth/setup` | JS fetch POST with setup token | WIRED | `auth.js` handleSetupForm(): `fetch("/api/auth/setup", {method: "POST", ...})` |
| `frontend/static/login.html` | `/api/auth/magic-link` | JS fetch POST with email | WIRED | `auth.js` handleLoginForm(): `fetch("/api/auth/magic-link", {method: "POST", ...})` |
| `frontend/static/js/auth.js` | `/api/auth/status` | Check auth status to redirect appropriately | WIRED | `checkAuthStatus()`: `fetch("/api/auth/status")` then redirects based on `setup_mode` and authentication state |
| `frontend/nginx.conf` | `api:8000` | Proxy with cookie forwarding | WIRED | `/api/` location: `proxy_pass http://api:8000/api/`; `proxy_pass_header Set-Cookie;` and `proxy_set_header Cookie $http_cookie;` |
| `backend/app/auth/router.py` POST /invite | `backend/app/auth/service.py` create_invitation | `auth_service.create_invitation(email, role, invited_by)` | WIRED | Lines 207-211: `invitation = await auth_service.create_invitation(email=body.email, role=body.role, invited_by=current_user.id)` |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| AUTH-01 | 06-01 | SQL data layer: users, sessions, invitations, instance_config tables with Alembic migrations | SATISFIED | All 4 ORM models defined, 001_initial_auth_tables.py migration verified, Alembic configured |
| AUTH-02 | 06-02, 06-04 | Passwordless session-based authentication (setup token + magic link) with httpOnly cookie | SATISFIED | Setup flow works, magic link token generation/verification implemented, httpOnly cookie set |
| AUTH-03 | 06-02, 06-04 | First-run setup wizard: terminal token, browser claim page, zero-friction local setup | SATISFIED | setup.html, auth.js handleSetupForm(), POST /auth/setup endpoint all verified |
| AUTH-04 | 06-02 | Session management: create, verify, sliding window extension, revoke | SATISFIED | AuthService.create_session(), verify_session() (50% sliding window), revoke_session() all implemented |
| RBAC-01 | 06-02, 06-03 | get_current_user dependency injects authenticated User or 401 | SATISFIED | dependencies.py get_current_user() verified with DB session lookup and 401 on failure |
| RBAC-02 | 06-02, 06-03 | require_role(*roles) dependency checks role and returns 403 if insufficient | SATISFIED | dependencies.py require_role() factory verified; applied on commands, models/install, models/remove, auth/invite |
| RBAC-03 | 06-02, 06-03 | Role hierarchy enforced: owner (full), member (read+write), guest (read-only) | SATISFIED | commands requires owner/member; models install/remove requires owner; auth/invite requires owner; all read endpoints require any auth |
| PROV-01 | 06-03 | EVENT_PERFORMED_BY constant defined in event vocabulary | SATISFIED | events/models.py: `EVENT_PERFORMED_BY = SEMPKM.performedBy` |
| PROV-02 | 06-03 | EventStore.commit() records user IRI in event metadata when provided | SATISFIED | events/store.py: `if performed_by is not None: event_triples.append((event_iri, EVENT_PERFORMED_BY, performed_by))` |
| INFRA-01 | 06-01 | Docker infrastructure: no RDF4J port exposure, persistent data volume | SATISFIED | docker-compose.yml: no `8080:8080` mapping; `sempkm_data:/app/data` volume mount; only exposed ports are `8001:8000` (api dev) and `3000:80` (nginx) |
| INVITE-01 | 06-04 | Owner can invite members and guests via invitation flow | SATISFIED | POST /api/auth/invite (router.py lines 199-215) requires owner role, delegates to create_invitation(), returns InviteResponse with invitation_id; InviteRequest validates role is member or guest; invite.html handles acceptance via /api/auth/verify |

**All 11 requirements satisfied.**

Note: These requirement IDs (AUTH-01 through INVITE-01) are phase-06-specific requirements defined in ROADMAP.md and CONTEXT.md, not in the v1 REQUIREMENTS.md file. This is expected.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/auth/router.py` | 47 | `secure=False  # TODO: make configurable for production` | Warning | Cookie `secure=False` means session cookie sent over HTTP; appropriate for local development but a production concern; not a functional blocker |
| `backend/app/auth/router.py` | 127 | `# TODO: If SMTP is configured, send the email with the token` | Info | Acknowledged as deferred — magic link works without SMTP (logs token in debug mode); not a blocker |
| `backend/app/commands/router.py` | 146 | `# TODO: Wire validation.completed webhook via validation queue callback` | Info | Pre-existing deferred item from Phase 4; not related to Phase 6 |

No blocker anti-patterns found. The previously-flagged blocker (InviteRequest/InviteResponse defined but unused) has been resolved.

---

## Human Verification Required

### 1. First-Run Setup Flow

**Test:** Run `docker compose up --build -d`, wait for healthy, check `docker compose logs api` for the FIRST-RUN SETUP block with token. Open http://localhost:3000/setup.html in browser. Verify setup wizard form renders. Enter the terminal token, click "Claim Instance". Verify success message and redirect to /.
**Expected:** Setup wizard displays, token is accepted, user is redirected to main dashboard, `sempkm_session` httpOnly cookie appears in DevTools > Application > Cookies.
**Why human:** Cookie issuance, browser redirect, and httpOnly flag visibility require browser interaction.

### 2. Auth Redirect Behavior

**Test:** Without a session cookie, navigate to http://localhost:3000/ (or any dashboard page). Observe where you end up.
**Expected:** Unauthenticated users are redirected to /login.html (via checkAuthStatus() in auth.js).
**Why human:** Redirect behavior requires browser session state that cannot be tested with grep.

### 3. Logout Clears Session

**Test:** After setup, open browser console and run: `fetch('/api/auth/logout', {method: 'POST'}).then(r => r.json()).then(console.log)`. Then check Cookies in DevTools.
**Expected:** Response is `{"message": "Logged out successfully"}`, the `sempkm_session` cookie disappears, and refreshing the page redirects to /login.html.
**Why human:** Cookie deletion and redirect after logout require browser verification.

---

_Verified: 2026-02-22T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
