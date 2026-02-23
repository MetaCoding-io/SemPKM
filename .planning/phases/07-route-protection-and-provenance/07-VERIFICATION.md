---
phase: 07-route-protection-and-provenance
verified: 2026-02-22T05:30:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
---

# Phase 7: Route Protection and Provenance Verification Report

**Phase Goal:** All browser, views, and admin HTML routes enforce server-side authentication and authorization; browser-originated writes record user provenance in event metadata
**Verified:** 2026-02-22T05:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All 14 truths were derived directly from the `must_haves.truths` frontmatter of both plans (07-01 and 07-02).

#### Plan 01 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Unauthenticated full-page requests to HTML routes receive 302 redirect to /login.html with ?next= parameter | VERIFIED | `main.py` lines 198-200: `RedirectResponse(url=f"/login.html?next={quote(str(request.url.path), safe='/')}", status_code=302)` inside `auth_exception_handler` for 401 + `_is_html_route()` check |
| 2 | Authenticated users without required role see a styled 403 HTML page on HTML routes | VERIFIED | `main.py` lines 209-214: `templates.TemplateResponse(request, "errors/403.html", ...)` for 403 on non-HTMX HTML routes |
| 3 | HTMX partial requests that fail auth receive inline error fragments (not redirects) | VERIFIED | `main.py` lines 193-196 (401 HTMX): `HTMLResponse('<div class="auth-error">Session expired...')`, lines 205-208 (403 HTMX): `HTMLResponse('<div class="auth-error">Access denied...')` |
| 4 | API routes continue to receive JSON error responses for 401/403 (no regressions) | VERIFIED | `main.py` lines 216-219: `_is_html_route()` returns `False` for `/api/*` paths, falls through to `JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})` |
| 5 | EventStore.commit() accepts optional performed_by_role parameter | VERIFIED | `events/store.py` lines 74-79: `async def commit(self, operations, performed_by: URIRef \| None = None, performed_by_role: str \| None = None)`. Lines 149-152: builds `EVENT_PERFORMED_BY_ROLE` triple when non-None |
| 6 | After successful login, user is redirected back to the URL they originally requested via ?next= parameter | VERIFIED | `auth.js` line 43: `checkAuthStatus()` redirect with `encodeURIComponent`. Lines 169-171: `handleLoginForm()` auto-login path reads `params.get("next")`. Lines 236-238: `handleVerifyToken()`. Lines 310-312: `handleInviteAccept()` |

#### Plan 02 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 7 | All browser/* read endpoints require authentication via get_current_user dependency | VERIFIED | `browser/router.py`: `workspace()` (line 43), `tree_children()` (line 66), `get_object()` (line 113), `get_relations()` (line 228), `get_lint()` (line 332), `type_picker()` (line 409), `create_form()` (line 429), `search_references()` (line 682) — all carry `user: User = Depends(get_current_user)` |
| 8 | All browser/* write endpoints (POST create, POST save, POST body) require owner or member role and pass performed_by + performed_by_role to EventStore.commit() | VERIFIED | `save_body()` (line 189): `require_role("owner","member")`, commit at line 211. `create_object()` (line 465): `require_role("owner","member")`, commit at line 527. `save_object()` (line 584): `require_role("owner","member")`, commit at line 630. All three pass `performed_by=user_iri, performed_by_role=user.role` |
| 9 | All views/* read endpoints require authentication via get_current_user dependency | VERIFIED | `views/router.py`: `view_list()` (line 33), `table_view()` (line 82), `cards_view()` (line 175), `graph_data()` (line 248), `graph_expand()` (line 274), `graph_view()` (line 293), `views_explorer()` (line 358, bonus endpoint auto-fixed), `view_menu()` (line 397), `views_available()` (line 455) — all 9 carry `get_current_user` |
| 10 | All admin/* endpoints require owner role via require_role('owner') | VERIFIED | `admin/router.py`: 8 endpoints (`admin_index`, `admin_models`, `admin_models_install`, `admin_models_remove`, `admin_webhooks`, `admin_webhooks_create`, `admin_webhooks_delete`, `admin_webhooks_toggle`) all carry `user: User = Depends(require_role("owner"))`. Count confirmed at 8 matches |
| 11 | Shell routes (/, /health/) require authentication via get_current_user dependency | VERIFIED | `shell/router.py`: `dashboard()` (line 25) and `health_page()` (line 34) both carry `user: User = Depends(get_current_user)` |
| 12 | Debug routes (/sparql, /commands) require authentication via get_current_user dependency | VERIFIED | `debug/router.py`: `sparql_page()` (line 12) and `commands_page()` (line 21) both carry `user: User = Depends(get_current_user)` |
| 13 | Unauthenticated direct HTTP requests to any protected route receive 401/302 (not just a JS redirect) | VERIFIED | All 33 HTML endpoints now carry FastAPI `Depends(get_current_user)` or `Depends(require_role(...))`. The exception handler in `main.py` converts 401/403 to 302 for full-page requests. Server-side enforcement is independent of JS. |
| 14 | Browser-originated writes include sempkm:performedBy and sempkm:performedByRole triples in event metadata | VERIFIED | `events/models.py` lines 22-23: `EVENT_PERFORMED_BY = SEMPKM.performedBy`, `EVENT_PERFORMED_BY_ROLE = SEMPKM.performedByRole`. `events/store.py` lines 143-152: both are appended to `event_triples` when non-None. All 3 browser write endpoints supply both values. |

**Score:** 14/14 truths verified

---

### Required Artifacts

#### Plan 01 Artifacts

| Artifact | Provides | Exists | Substantive | Wired | Status |
|----------|----------|--------|-------------|-------|--------|
| `backend/app/main.py` | Custom HTTPException handler for HTML vs API auth error routing | Yes | Yes — `auth_exception_handler` at lines 174-219, `_is_html_route()` at lines 169-171 | Yes — registered via `@app.exception_handler(HTTPException)` | VERIFIED |
| `backend/app/templates/errors/403.html` | Styled Access Denied page matching app layout | Yes | Yes — 62 lines, standalone HTML with CSS, "403" code, "Access Denied" h1, explanation, `/browser/` link | Yes — referenced in `main.py` line 211 via `templates.TemplateResponse(...)` | VERIFIED |
| `backend/app/events/models.py` | EVENT_PERFORMED_BY_ROLE predicate and SYSTEM_ACTOR_IRI constant | Yes | Yes — lines 23 and 26 define both constants using `SEMPKM` namespace | Yes — imported into `events/store.py` line 27 | VERIFIED |
| `backend/app/events/store.py` | Extended commit() with performed_by_role parameter | Yes | Yes — `performed_by_role: str \| None = None` at line 78, used at lines 149-152 to build triple | Yes — called from all 3 browser write endpoints with both provenance args | VERIFIED |
| `frontend/static/js/auth.js` | Redirect-back flow using ?next= query parameter after login | Yes | Yes — 4 distinct usages of `?next=` pattern across `checkAuthStatus`, `handleLoginForm`, `handleVerifyToken`, `handleInviteAccept` | Yes — called from HTML auth pages during login flow | VERIFIED |

#### Plan 02 Artifacts

| Artifact | Provides | Exists | Substantive | Wired | Status |
|----------|----------|--------|-------------|-------|--------|
| `backend/app/browser/router.py` | Auth-protected browser endpoints with provenance on writes | Yes | Yes — 12 auth dependency usages (grep count confirmed); 3 `performed_by_role` usages | Yes — wired to `get_current_user` and `require_role` from `app.auth.dependencies` | VERIFIED |
| `backend/app/views/router.py` | Auth-protected views endpoints | Yes | Yes — 10 `get_current_user` usages covering all 9 endpoints | Yes — imported and applied | VERIFIED |
| `backend/app/admin/router.py` | Owner-only admin endpoints | Yes | Yes — 8 `require_role("owner")` usages covering all 8 endpoints | Yes — imported from `app.auth.dependencies` | VERIFIED |
| `backend/app/shell/router.py` | Auth-protected shell endpoints | Yes | Yes — `get_current_user` on both `dashboard()` and `health_page()` | Yes — imported and applied | VERIFIED |
| `backend/app/debug/router.py` | Auth-protected debug endpoints | Yes | Yes — `get_current_user` on both `sparql_page()` and `commands_page()` | Yes — imported and applied | VERIFIED |

---

### Key Link Verification

#### Plan 01 Key Links

| From | To | Via | Status | Detail |
|------|----|-----|--------|--------|
| `backend/app/main.py` | `backend/app/templates/errors/403.html` | Jinja2 TemplateResponse in exception handler | WIRED | Line 211: `templates.TemplateResponse(request, "errors/403.html", ...)` |
| `backend/app/main.py` | `/login.html` | RedirectResponse with ?next= in exception handler | WIRED | Line 199: `url=f"/login.html?next={quote(str(request.url.path), safe='/')}"` |
| `backend/app/events/store.py` | `backend/app/events/models.py` | Import EVENT_PERFORMED_BY_ROLE | WIRED | Line 27: `from app.events.models import ... EVENT_PERFORMED_BY_ROLE` |

#### Plan 02 Key Links

| From | To | Via | Status | Detail |
|------|----|-----|--------|--------|
| `backend/app/browser/router.py` | `backend/app/events/store.py` | performed_by and performed_by_role in EventStore.commit() | WIRED | Lines 211, 527, 630: `event_store.commit([operation], performed_by=user_iri, performed_by_role=user.role)` |
| `backend/app/browser/router.py` | `backend/app/auth/dependencies.py` | Depends(get_current_user) and Depends(require_role) | WIRED | Line 17: `from app.auth.dependencies import get_current_user, require_role`; 12 usages in endpoint signatures |
| `backend/app/admin/router.py` | `backend/app/auth/dependencies.py` | Depends(require_role('owner')) | WIRED | Line 14: `from app.auth.dependencies import require_role`; pattern `require_role("owner")` appears 8 times |

---

### Requirements Coverage

The INT-01, INT-02, INT-03 identifiers are **integration gap IDs** defined in `.planning/v1.0-MILESTONE-AUDIT.md`, not entries in `REQUIREMENTS.md`. This is by design — REQUIREMENTS.md covers functional requirements (CORE, SHCL, MODL, etc.), while the v1.0 audit identified cross-cutting integration gaps separately. No Phase 7 entries appear in the REQUIREMENTS.md Traceability table, which is consistent with this design.

| Gap ID | Source | Description | Status | Evidence |
|--------|--------|-------------|--------|----------|
| INT-01 | v1.0-MILESTONE-AUDIT.md | browser/* and views/* routers lack server-side auth dependency | SATISFIED | `browser/router.py` 12 auth dependencies; `views/router.py` 10 auth dependencies covering all 9 endpoints |
| INT-02 | v1.0-MILESTONE-AUDIT.md | admin/* router lacks server-side auth dependency | SATISFIED | `admin/router.py` 8 `require_role("owner")` dependencies on all 8 endpoints |
| INT-03 | v1.0-MILESTONE-AUDIT.md | browser/* write endpoints do not record user provenance | SATISFIED | All 3 write endpoints (`save_body`, `create_object`, `save_object`) pass `performed_by=user_iri, performed_by_role=user.role` to `EventStore.commit()` |

**REQUIREMENTS.md Orphan Check:** No requirement IDs in REQUIREMENTS.md Traceability table map to Phase 7. There are no orphaned requirements.

**Referenced v1 requirements from audit gap evidence (informational):**
- INT-01 references SHCL-03, SHCL-04, OBJ-01, OBJ-02, OBJ-03, VIEW-01-04 — all previously satisfied in Phases 2-5, now additionally protected by server-side auth.
- INT-02 references ADMN-02, ADMN-03 — both previously satisfied in Phase 4, now additionally protected.
- INT-03 references PROV-01, PROV-02 — these are v2 requirements not tracked in v1 REQUIREMENTS.md; the implementation satisfies the intent via `performed_by`/`performed_by_role` triples.

---

### Anti-Patterns Found

None. All 9 modified files scanned:
- `backend/app/main.py` — no TODOs, no placeholder returns, no empty handlers
- `backend/app/templates/errors/403.html` — no placeholder content; full styled error page
- `backend/app/events/models.py` — clean constant definitions only
- `backend/app/events/store.py` — no stubs; `performed_by_role` wired through full commit pipeline
- `backend/app/browser/router.py` — no stubs; all endpoints substantive; write endpoints commit with provenance
- `backend/app/views/router.py` — no stubs; all endpoints substantive
- `backend/app/admin/router.py` — no stubs; all endpoints substantive
- `backend/app/shell/router.py` — no stubs
- `backend/app/debug/router.py` — no stubs
- `frontend/static/js/auth.js` — no TODOs; ?next= flow implemented in all 4 locations

---

### Human Verification Required

The following items require manual testing and cannot be verified programmatically:

#### 1. Server-Side 302 Redirect Behavior (curl)

**Test:** `curl -s -o /dev/null -w "%{http_code}" -L0 http://localhost:8001/browser/`
**Expected:** Returns `302` (redirect to `/login.html?next=/browser/`)
**Why human:** Requires live Docker stack; curl behavior depends on runtime cookie state

#### 2. 403 Page Rendering for Wrong Role

**Test:** Log in as a `member` user, navigate directly to `http://localhost:8001/admin/`
**Expected:** Styled "Access Denied" page with error code 403 and "Back to Workspace" link
**Why human:** Requires two user accounts with different roles; visual verification of page styling

#### 3. HTMX Inline Error Fragment

**Test:** `curl -s -H "HX-Request: true" http://localhost:8001/browser/`
**Expected:** HTML fragment `<div class="auth-error">Session expired. <a href="/login.html">Log in again</a></div>` with 401 status (not 302 redirect)
**Why human:** Requires live stack; verifies header-based routing logic at runtime

#### 4. Redirect-Back Flow After Login

**Test:** Attempt to navigate to `/browser/` unauthenticated. Observe redirect to `/login.html?next=/browser/`. Complete login. Observe redirect back to `/browser/`.
**Expected:** After login, browser lands on `/browser/` not `/`
**Why human:** Full browser-based flow across multiple requests; cannot verify with static analysis

#### 5. Provenance in RDF Event Graph

**Test:** Log in as owner. Create an object via `/browser/objects`. Query the event graph: `SELECT ?performed_by ?role WHERE { GRAPH ?event { ?event <urn:sempkm:performedBy> ?performed_by ; <urn:sempkm:performedByRole> ?role } }` in the SPARQL console.
**Expected:** Results show the logged-in user's IRI (e.g. `urn:sempkm:user:{uuid}`) and their role (e.g. `"owner"`)
**Why human:** Requires live triplestore query; verifies RDF triple materialization end-to-end

---

### Commit Verification

All commits referenced in SUMMARY.md files were verified in git log:

| Commit | Description | Verified |
|--------|-------------|---------|
| `fd75e22` | feat(07-01): custom HTML auth exception handler, 403 template, and EventStore provenance extension | Yes |
| `8af1e65` | feat(07-01): frontend redirect-back flow via ?next= parameter | Yes |
| `42f29dc` | feat(explorer): VS Code-style collapsible sections with views tree (includes browser/views/admin auth) | Yes |
| `719f754` | feat(07-02): add auth dependencies to shell and debug routers | Yes |

---

### Overall Assessment

The phase goal is **fully achieved**. Every HTML route across all 5 routers (browser, views, admin, shell, debug) now enforces server-side authentication via FastAPI `Depends()`. The exception handler correctly differentiates between HTML routes and API routes, returning appropriate responses for each. Browser-originated writes (create_object, save_object, save_body) record `sempkm:performedBy` and `sempkm:performedByRole` triples in event metadata. The frontend ?next= redirect-back flow is implemented across all 4 login paths.

The implementation goes beyond the plan's 8 views endpoints to protect a 9th (`views_explorer`) discovered during execution — a correct security decision noted in the summary.

No artifacts are stubs. No key links are broken. No anti-patterns were found.

---

_Verified: 2026-02-22T05:30:00Z_
_Verifier: Claude (gsd-verifier)_
