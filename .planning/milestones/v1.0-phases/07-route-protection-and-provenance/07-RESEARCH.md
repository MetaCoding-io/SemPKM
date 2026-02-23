# Phase 7: Route Protection and Provenance - Research

**Researched:** 2026-02-22
**Domain:** FastAPI server-side authentication, authorization, and event provenance
**Confidence:** HIGH

## Summary

Phase 7 closes three integration gaps (INT-01, INT-02, INT-03) identified in the v1.0 milestone audit. The core problem is straightforward: the browser, views, and admin HTML routers were built before Phase 6 added authentication, so they lack `Depends(get_current_user)` and `Depends(require_role(...))` guards. Meanwhile, the API routes (`/api/commands`, `/api/sparql`, `/api/models`, `/api/validation`) are already correctly protected. The browser write endpoints also call `EventStore.commit()` without passing `performed_by`, so browser-originated writes lack user provenance in the event graph.

The implementation requires no new libraries, no schema changes, and no architectural shifts. The auth dependency system (`get_current_user`, `require_role`) is fully operational and battle-tested on the API routes. The `EventStore.commit()` already accepts `performed_by: URIRef | None`. The work is primarily mechanical: adding dependency injection parameters to existing router functions, handling HTML-appropriate error responses (302 redirects for 401, styled 403 pages for forbidden), and passing user IRI + role to EventStore from the browser write endpoints.

**Primary recommendation:** Add auth dependencies to every browser/views/admin endpoint, create HTML-aware auth error handling (redirect-to-login for 401, styled 403 page for role failures, inline HTMX fragments for partial requests), and wire `performed_by` + `performed_by_role` into browser write endpoints using the same pattern as `/api/commands`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Auth failure UX on HTML routes:** Unauthenticated users get 302 redirect to /login.html with ?next= parameter preserving the original URL. Authenticated users who lack required role see a styled 403 HTML page matching app styling ("Access Denied" heading, explanation, link back to workspace).
- **Role mapping to endpoints:** Browser READ endpoints require authentication only (get_current_user). Browser WRITE endpoints require owner or member role via require_role("owner", "member"). Views READ endpoints same as browser reads. Admin routes (all) strictly owner-only via require_role("owner"). Quick audit of API routes to verify consistent auth coverage.
- **Provenance detail level:** Browser writes pass performed_by (user IRI) to EventStore.commit(). Also record user's role at time of action via EVENT_PERFORMED_BY_ROLE predicate. EventStore.commit() signature adds explicit performed_by_role parameter. System operations get well-known system IRI (urn:sempkm:system) instead of remaining anonymous.
- **HTMX error handling:** When HTMX partial request gets 401 (session expired), swap inline error into target area: "Session expired" message with login link. When HTMX request gets 403, same pattern: inline "Access denied" message. Implemented as per-endpoint responses, not a global HTMX handler.

### Claude's Discretion
- Exact styling of the 403 error page
- HTMX error fragment HTML/CSS details
- How to handle the /login.html?next= redirect-back flow (may need frontend changes)
- Whether to use a shared auth dependency that returns HTML errors for HTMX vs JSON for API, or handle separately

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INT-01 | browser/* and views/* routers lack server-side auth dependency | Add `Depends(get_current_user)` to all read endpoints, `Depends(require_role("owner", "member"))` to write endpoints in browser/router.py and views/router.py. Pattern already proven in sparql/router.py, commands/router.py, models/router.py, validation/router.py |
| INT-02 | admin/* router lacks server-side auth dependency | Add `Depends(require_role("owner"))` to all admin/router.py endpoints. Pattern proven in models/router.py API routes |
| INT-03 | browser/* write endpoints do not record user provenance | Pass `performed_by=URIRef(f"urn:sempkm:user:{user.id}")` and `performed_by_role` to EventStore.commit() in save_body, create_object, save_object. Pattern proven in commands/router.py line 123-124 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (existing) | Dependency injection for auth guards | Already in use; Depends() is the standard pattern for route-level auth |
| rdflib | (existing) | URIRef construction for user IRI provenance | Already in use for EventStore |
| Jinja2Blocks | (existing) | Template rendering for 403 pages and error fragments | Already in use for all HTML route responses |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| No new libraries needed | - | - | All required functionality exists in current stack |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-endpoint auth deps | FastAPI middleware | Middleware can't easily distinguish HTML vs API routes, loses Depends() composability, harder to test. Per-endpoint is the established project pattern. |
| Per-endpoint HTMX error handling | Global htmx:responseError JS handler | User decision: per-endpoint responses, not global handler. Gives more control over error messages per context. |
| Custom HTML auth dependency | Reuse existing get_current_user + catch HTTPException | User's discretion area. A shared HTML-aware dependency avoids try/except boilerplate in every endpoint. |

## Architecture Patterns

### Current Endpoint Auth Patterns (already in codebase)

**Pattern A: Authentication-only read endpoint** (sparql/router.py, validation/router.py)
```python
@router.get("/endpoint")
async def my_endpoint(
    request: Request,
    user: User = Depends(get_current_user),
    # ... other deps
):
```

**Pattern B: Role-guarded write endpoint** (commands/router.py)
```python
@router.post("/commands")
async def execute_commands(
    request: Request,
    user: User = Depends(require_role("owner", "member")),
    # ... other deps
):
    # User object available for provenance
    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    event_result = await event_store.commit(operations, performed_by=user_iri)
```

**Pattern C: Owner-only API endpoint** (models/router.py)
```python
@router.post("/install")
async def install_model(
    body: InstallRequest,
    user: User = Depends(require_role("owner")),
    # ... other deps
):
```

### Recommended Pattern: HTML-Aware Auth Dependency

The existing `get_current_user` raises `HTTPException(401)` with a JSON detail. For HTML routes, we need 302 redirects instead. Two approaches:

**Approach 1: Wrapper dependencies (recommended)**

Create HTML-specific auth dependencies in a shared module that catch the 401/403 from the existing dependencies and convert them to HTML responses:

```python
# app/auth/html_dependencies.py

from urllib.parse import quote
from fastapi import Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.auth.dependencies import get_current_user as _get_current_user
from app.auth.models import User


def _is_htmx_request(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


async def require_login(request: Request) -> User:
    """Like get_current_user but returns 302 redirect for HTML routes,
    or inline error fragment for HTMX requests."""
    try:
        user = await _get_current_user(...)  # pass through deps
        return user
    except HTTPException as e:
        if e.status_code == 401:
            if _is_htmx_request(request):
                # Return inline error fragment for HTMX
                raise HTTPException(
                    status_code=401,
                    detail="Session expired",
                )
            # Redirect to login with ?next= for full page requests
            next_url = quote(str(request.url.path), safe="")
            raise HTTPException(
                status_code=302,
                headers={"Location": f"/login.html?next={next_url}"},
            )
        raise


def require_html_role(*roles: str):
    """Like require_role but returns styled 403 HTML for HTML routes."""
    async def _check(request: Request, user: User = Depends(require_login)):
        if user.role not in roles:
            if _is_htmx_request(request):
                # Inline "Access denied" fragment
                raise HTTPException(status_code=403)
            # Full 403 page
            raise HTTPException(status_code=403)
        return user
    return _check
```

**However**, FastAPI's `Depends()` chain makes this slightly tricky because `get_current_user` itself depends on `get_session_token` and `get_db_session`. The cleanest approach is actually to use FastAPI's exception handlers or custom dependencies that work at the right level.

**Approach 2: Custom dependencies that replicate the auth logic with HTML responses**

Create parallel dependencies that do the same DB lookup but return HTML-appropriate errors. This avoids the nested-exception problem.

```python
async def require_html_login(
    request: Request,
    sempkm_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Server-side auth for HTML routes. Returns 302 redirect or HTMX error fragment."""
    if sempkm_session is None:
        return _handle_unauthenticated(request)

    # ... same session lookup logic as get_current_user ...

    if user is None:
        return _handle_unauthenticated(request)
    return user
```

**Recommendation: Approach 2** -- Create clean HTML-specific dependencies that share the same session lookup logic but produce HTML-appropriate error responses. This avoids try/except around HTTPException (which FastAPI doesn't naturally support in dependency chains) and gives precise control over the redirect and HTMX error fragment behavior.

The implementation detail: FastAPI does not let you "catch" an HTTPException raised by a sub-dependency within another dependency. The exception propagates directly to the exception handler. So wrapping `get_current_user` in a try/except inside another dependency does NOT work as expected. You must either:
1. Create standalone dependencies that do their own session lookup (recommended)
2. Use a custom exception handler at the app level that checks if the route is HTML vs API

### Recommended Approach: Dual-purpose Exception Handler

Actually, the cleanest approach for this project is:

1. **Keep using the existing `get_current_user` and `require_role` dependencies as-is on the HTML routes** -- they raise HTTPException(401) and HTTPException(403)
2. **Add a custom exception handler** on the FastAPI app that intercepts 401/403 errors and checks if the route is an HTML route (by path prefix or Accept header), then returns the appropriate HTML response (302 redirect or 403 page)

```python
@app.exception_handler(HTTPException)
async def html_auth_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code in (401, 403):
        path = request.url.path
        is_html_route = (
            path.startswith("/browser") or
            path.startswith("/admin") or
            path.startswith("/health") or
            path == "/"
        )
        if is_html_route:
            if exc.status_code == 401:
                if request.headers.get("HX-Request") == "true":
                    return HTMLResponse(content="<error fragment>", status_code=401)
                next_url = quote(str(request.url.path))
                return RedirectResponse(f"/login.html?next={next_url}")
            elif exc.status_code == 403:
                if request.headers.get("HX-Request") == "true":
                    return HTMLResponse(content="<error fragment>", status_code=403)
                return HTMLResponse(content="<403 page>", status_code=403)
    # Default: let FastAPI handle it (JSON response)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
```

**This is the best pattern because:**
- Zero changes to existing API route behavior
- Zero changes to existing auth dependency code
- HTML routes just add `Depends(get_current_user)` or `Depends(require_role("owner"))` -- same as API routes
- All HTML-vs-JSON response logic is centralized in one handler
- HTMX detection is centralized
- Easy to test: one handler covers all routes

### Provenance Pattern

For EventStore provenance, extend the existing pattern from commands/router.py:

```python
# In browser write endpoints (create_object, save_object, save_body):
from app.auth.dependencies import require_role
from app.auth.models import User

@router.post("/objects")
async def create_object(
    request: Request,
    user: User = Depends(require_role("owner", "member")),
    # ... existing deps
):
    # Construct user IRI (same as commands/router.py)
    user_iri = URIRef(f"urn:sempkm:user:{user.id}")

    # ... existing command dispatch logic ...

    event_store = EventStore(client)
    event_result = await event_store.commit(
        [operation],
        performed_by=user_iri,
        performed_by_role=user.role,
    )
```

For the EventStore.commit() signature extension:
```python
async def commit(
    self,
    operations: list[Operation],
    performed_by: URIRef | None = None,
    performed_by_role: str | None = None,
) -> EventResult:
    # ... existing code ...

    if performed_by is not None:
        event_triples.append(
            (event_iri, EVENT_PERFORMED_BY, performed_by)
        )
    if performed_by_role is not None:
        event_triples.append(
            (event_iri, EVENT_PERFORMED_BY_ROLE, Literal(performed_by_role))
        )
```

### System IRI Pattern

For system operations (model auto-install, seed data), define:
```python
# In app/rdf/namespaces.py or app/events/models.py
SYSTEM_ACTOR_IRI = URIRef("urn:sempkm:system")
```

Then update the auto-install path in `main.py` / `ModelService` to pass `performed_by=SYSTEM_ACTOR_IRI`.

### Anti-Patterns to Avoid
- **Client-side only auth:** The current auth.js `checkAuthStatus()` provides UX-only protection. A curl request bypasses it entirely. Server-side deps are mandatory.
- **Separate auth logic for HTML vs API:** Do NOT duplicate session-lookup logic. Use the same `get_current_user`/`require_role` dependencies and handle response format in the exception handler.
- **Breaking existing API error responses:** The custom exception handler must fall through to default JSON behavior for `/api/*` routes.
- **Hardcoding user IRI format in multiple places:** The `urn:sempkm:user:{uuid}` pattern is currently in commands/router.py line 123. Browser write endpoints should use the same pattern. Consider extracting a helper `user_iri(user: User) -> URIRef`.

### Recommended Project Structure

No new directories needed. Changes touch existing files:

```
backend/app/
├── auth/
│   └── dependencies.py        # (unchanged -- reuse as-is)
├── events/
│   ├── models.py              # Add EVENT_PERFORMED_BY_ROLE predicate
│   └── store.py               # Add performed_by_role param to commit()
├── rdf/
│   └── namespaces.py          # (optional) Add SYSTEM_ACTOR_IRI constant
├── browser/
│   └── router.py              # Add auth deps to all endpoints, provenance to writes
├── views/
│   └── router.py              # Add auth deps to all endpoints
├── admin/
│   └── router.py              # Add require_role("owner") to all endpoints
├── shell/
│   └── router.py              # Add auth deps (dashboard, health page)
├── debug/
│   └── router.py              # Add auth deps (sparql, commands pages)
├── main.py                    # Add custom exception handler for HTML auth errors
└── templates/
    └── errors/
        └── 403.html           # New: styled "Access Denied" page
```

### Login Redirect-Back Flow

The ?next= parameter on /login.html requires a small frontend change:

1. After successful login verification in auth.js, check for `?next=` in the URL
2. If present, redirect to that URL instead of the default `/`

```javascript
// In auth.js handleLoginForm() and handleVerifyToken():
var nextUrl = new URLSearchParams(window.location.search).get("next");
window.location.href = nextUrl || "/";
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session validation | Custom cookie parsing | FastAPI's `Cookie()` + existing `get_current_user` | Already handles sliding window, expiry, DB lookup |
| Role checking | Manual if/else in each endpoint | `require_role("owner", "member")` dependency | Already validates against User model, raises proper HTTP errors |
| SPARQL escaping for provenance | String concatenation | `_serialize_rdf_term()` in EventStore | Already handles all RDF term types safely |
| User IRI format | Per-endpoint string formatting | Shared helper function | Ensures consistent `urn:sempkm:user:{uuid}` format across codebase |

**Key insight:** This phase is almost entirely about wiring existing components together. The auth dependencies exist, EventStore.commit() already accepts provenance, the templates engine is configured. The new work is the custom exception handler and the 403 template.

## Common Pitfalls

### Pitfall 1: FastAPI HTTPException in Dependency Chains
**What goes wrong:** Trying to catch `HTTPException` raised by a sub-dependency (e.g., wrapping `get_current_user` in try/except within another dependency) -- FastAPI propagates these directly to the exception handler, bypassing Python's try/except in the dependency.
**Why it happens:** FastAPI's dependency injection system treats HTTPException specially.
**How to avoid:** Use a custom exception handler on the app instead of wrapping dependencies. Let the existing dependencies raise 401/403 normally, intercept at the handler level.
**Warning signs:** Auth errors returning JSON on HTML routes despite wrapper dependencies.

### Pitfall 2: Breaking API Route Error Responses
**What goes wrong:** Custom exception handler converts ALL 401/403 to HTML, including API route errors that clients expect as JSON.
**Why it happens:** Exception handler doesn't check the route path.
**How to avoid:** In the custom handler, check `request.url.path.startswith("/api/")` and fall through to default JSON handling for API routes.
**Warning signs:** Frontend JavaScript getting HTML when expecting JSON error responses.

### Pitfall 3: HTMX Partial Requests Getting Full-Page Redirects
**What goes wrong:** An HTMX partial request (HX-Request: true) gets a 302 redirect, causing htmx to follow the redirect and swap the login page HTML into the target element.
**Why it happens:** Not checking for HTMX requests before issuing redirects.
**How to avoid:** Check `HX-Request` header first. For HTMX requests, return inline error fragments with appropriate status codes. For full-page requests, use 302 redirects.
**Warning signs:** Login page appearing inside the workspace editor area.

### Pitfall 4: Cookie Not Forwarded Through Nginx
**What goes wrong:** Auth cookies not reaching FastAPI backend, causing all HTML routes to return 401.
**Why it happens:** Nginx proxy not forwarding cookies.
**How to avoid:** Already handled -- nginx.conf includes `proxy_set_header Cookie $http_cookie` and `proxy_pass_header Set-Cookie`. No changes needed.
**Warning signs:** Auth works on direct API calls but fails on proxied HTML routes.

### Pitfall 5: Forgetting to URL-Encode the ?next= Parameter
**What goes wrong:** URLs with special characters (e.g., `/browser/object/http://example.com/thing`) break the redirect-back flow.
**Why it happens:** Not encoding the original URL before appending to the login redirect.
**How to avoid:** Use `urllib.parse.quote()` on the path when building the redirect URL.
**Warning signs:** Broken redirect-back for objects with special characters in their IRI.

### Pitfall 6: EventStore Signature Change Breaking Existing Callers
**What goes wrong:** Adding `performed_by_role` as a required parameter breaks all existing `EventStore.commit()` calls.
**Why it happens:** Changing the method signature without keeping it backward-compatible.
**How to avoid:** Use `performed_by_role: str | None = None` (optional, defaulting to None). All existing callers continue to work.
**Warning signs:** Import errors or test failures in unmodified code.

### Pitfall 7: Missing Auth on Debug Routes
**What goes wrong:** SPARQL console and Commands pages (/sparql, /commands) remain unprotected.
**Why it happens:** debug/router.py is easy to overlook since it's separate from the browser/admin routers.
**How to avoid:** Audit ALL routers: browser, views, admin, shell, debug. The audit scope includes "all browser, views, and admin HTML routes."
**Warning signs:** Unauthenticated access to debug tools.

## Code Examples

### Example 1: Adding Auth to a Browser Read Endpoint
```python
# browser/router.py -- BEFORE
@router.get("/")
async def workspace(
    request: Request,
    shapes_service: ShapesService = Depends(get_shapes_service),
):

# AFTER
from app.auth.dependencies import get_current_user
from app.auth.models import User

@router.get("/")
async def workspace(
    request: Request,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
```

### Example 2: Adding Auth + Provenance to a Browser Write Endpoint
```python
# browser/router.py -- save_body AFTER
from app.auth.dependencies import require_role
from rdflib import URIRef

@router.post("/objects/{object_iri:path}/body")
async def save_body(
    request: Request,
    object_iri: str,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
):
    # ... existing logic ...
    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    event_result = await event_store.commit(
        [operation],
        performed_by=user_iri,
        performed_by_role=user.role,
    )
```

### Example 3: Custom Exception Handler for HTML Auth Errors
```python
# main.py
from urllib.parse import quote
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

_HTML_ROUTE_PREFIXES = ("/browser", "/admin", "/health", "/sparql", "/commands", "/")

def _is_html_route(path: str) -> bool:
    """Check if a route serves HTML (not API JSON)."""
    if path.startswith("/api/"):
        return False
    return True  # All non-API routes are HTML

@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    if not _is_html_route(request.url.path):
        # API routes: default JSON response
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    is_htmx = request.headers.get("HX-Request") == "true"

    if exc.status_code == 401:
        if is_htmx:
            return HTMLResponse(
                content='<div class="auth-error">Session expired. <a href="/login.html">Log in again</a></div>',
                status_code=401,
            )
        next_url = quote(str(request.url.path), safe="/")
        return RedirectResponse(url=f"/login.html?next={next_url}", status_code=302)

    if exc.status_code == 403:
        if is_htmx:
            return HTMLResponse(
                content='<div class="auth-error">Access denied. You do not have permission.</div>',
                status_code=403,
            )
        # Render full 403 page
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request, "errors/403.html",
            {"request": request},
            status_code=403,
        )

    # All other HTTP exceptions: default behavior
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
```

### Example 4: Admin Router with Owner-Only Auth
```python
# admin/router.py -- AFTER
from app.auth.dependencies import require_role
from app.auth.models import User

@router.get("/")
async def admin_index(
    request: Request,
    user: User = Depends(require_role("owner")),
):
```

### Example 5: Login Redirect-Back (Frontend Change)
```javascript
// In auth.js -- update redirect after successful login:
// BEFORE:
window.location.href = "/";

// AFTER:
var params = new URLSearchParams(window.location.search);
var nextUrl = params.get("next");
window.location.href = nextUrl || "/";
```

### Example 6: EVENT_PERFORMED_BY_ROLE Predicate
```python
# events/models.py -- add new predicate
EVENT_PERFORMED_BY_ROLE = SEMPKM.performedByRole
```

### Example 7: System Actor IRI
```python
# events/models.py or rdf/namespaces.py
from rdflib import URIRef
SYSTEM_ACTOR_IRI = URIRef("urn:sempkm:system")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Client-side JS auth check only | Server-side FastAPI dependencies | Phase 6 (API routes) | API routes protected; HTML routes still JS-only |
| No performed_by on events | Optional performed_by on EventStore.commit() | Phase 6 (06-03) | API commands record provenance; browser writes don't |
| Anonymous system operations | No attribution | Current state | System IRI (urn:sempkm:system) will disambiguate |

**What Phase 7 changes:**
- HTML routes gain server-side auth (matching API routes)
- Browser writes gain provenance (matching API commands)
- System operations gain explicit attribution (urn:sempkm:system)

## Endpoint Audit

### Routes Requiring Auth Changes

**browser/router.py (prefix: /browser)**
| Endpoint | Method | Current Auth | Required Auth | Change |
|----------|--------|-------------|---------------|--------|
| `/` | GET | None | get_current_user | Add dependency |
| `/tree/{type_iri}` | GET | None | get_current_user | Add dependency |
| `/object/{object_iri}` | GET | None | get_current_user | Add dependency |
| `/objects/{object_iri}/body` | POST | None | require_role("owner","member") + provenance | Add dependency + performed_by |
| `/relations/{object_iri}` | GET | None | get_current_user | Add dependency |
| `/lint/{object_iri}` | GET | None | get_current_user | Add dependency |
| `/types` | GET | None | get_current_user | Add dependency |
| `/objects/new` | GET | None | get_current_user | Add dependency |
| `/objects` | POST | None | require_role("owner","member") + provenance | Add dependency + performed_by |
| `/objects/{object_iri}/save` | POST | None | require_role("owner","member") + provenance | Add dependency + performed_by |
| `/search` | GET | None | get_current_user | Add dependency |

**views/router.py (prefix: /browser/views)**
| Endpoint | Method | Current Auth | Required Auth | Change |
|----------|--------|-------------|---------------|--------|
| `/list/{type_iri}` | GET | None | get_current_user | Add dependency |
| `/table/{spec_iri}` | GET | None | get_current_user | Add dependency |
| `/card/{spec_iri}` | GET | None | get_current_user | Add dependency |
| `/graph/{spec_iri}/data` | GET | None | get_current_user | Add dependency |
| `/graph/expand/{node_iri}` | GET | None | get_current_user | Add dependency |
| `/graph/{spec_iri}` | GET | None | get_current_user | Add dependency |
| `/menu` | GET | None | get_current_user | Add dependency |
| `/available` | GET | None | get_current_user | Add dependency |

**admin/router.py (prefix: /admin)**
| Endpoint | Method | Current Auth | Required Auth | Change |
|----------|--------|-------------|---------------|--------|
| `/` | GET | None | require_role("owner") | Add dependency |
| `/models` | GET | None | require_role("owner") | Add dependency |
| `/models/install` | POST | None | require_role("owner") | Add dependency |
| `/models/{model_id}` | DELETE | None | require_role("owner") | Add dependency |
| `/webhooks` | GET | None | require_role("owner") | Add dependency |
| `/webhooks` | POST | None | require_role("owner") | Add dependency |
| `/webhooks/{webhook_id}` | DELETE | None | require_role("owner") | Add dependency |
| `/webhooks/{webhook_id}/toggle` | POST | None | require_role("owner") | Add dependency |

**shell/router.py (no prefix)**
| Endpoint | Method | Current Auth | Required Auth | Change |
|----------|--------|-------------|---------------|--------|
| `/` | GET | None | get_current_user | Add dependency |
| `/health/` | GET | None | get_current_user | Add dependency |

**debug/router.py (no prefix)**
| Endpoint | Method | Current Auth | Required Auth | Change |
|----------|--------|-------------|---------------|--------|
| `/sparql` | GET | None | get_current_user | Add dependency |
| `/commands` | GET | None | get_current_user | Add dependency |

### Routes Already Correctly Protected (No Changes Needed)
| Router | Prefix | Auth Pattern |
|--------|--------|-------------|
| auth/router.py | /api/auth | Mixed: public (status, setup, magic-link, verify) + protected (me, logout, invite) |
| commands/router.py | /api | require_role("owner", "member") + performed_by |
| sparql/router.py | /api | get_current_user |
| models/router.py | /api/models | require_role("owner") for writes, get_current_user for reads |
| validation/router.py | /api | get_current_user |
| health/router.py | /api | None (intentionally public for Docker healthcheck) |

## Open Questions

1. **Should the health page (/health/) require auth?**
   - What we know: The API health endpoint (/api/health) is intentionally public for Docker healthchecks. The health page is a human-readable dashboard page served by shell/router.py.
   - What's unclear: Should the HTML health page be public too, or only for authenticated users?
   - Recommendation: Require auth on the HTML health page (it shows config details like DB path, triplestore URL). The API endpoint stays public.

2. **Should system operations retroactively get urn:sempkm:system attribution?**
   - What we know: Existing events from model auto-install have no performed_by triple. New system operations will use SYSTEM_ACTOR_IRI.
   - What's unclear: Whether to backfill existing events.
   - Recommendation: Don't backfill -- immutable events should stay as-is. Future system operations use SYSTEM_ACTOR_IRI. The absence of performed_by on old events is informatively correct (they predate provenance tracking).

3. **Should debug routes (/sparql, /commands) require owner role?**
   - What we know: These are developer/debug tools. The SPARQL page can query any data. The Commands page can execute write operations.
   - What's unclear: Whether members should have access to debug tools.
   - Recommendation: Require auth (any authenticated user) for the HTML pages. The actual API endpoints they call already enforce their own auth (SPARQL requires get_current_user, Commands requires owner/member role).

## Sources

### Primary (HIGH confidence)
- **Codebase inspection** -- All findings based on direct reading of the current source code:
  - `backend/app/auth/dependencies.py` -- get_current_user, require_role, optional_current_user
  - `backend/app/browser/router.py` -- 11 endpoints, 0 auth deps, 3 write endpoints without provenance
  - `backend/app/views/router.py` -- 8 endpoints, 0 auth deps
  - `backend/app/admin/router.py` -- 8 endpoints, 0 auth deps
  - `backend/app/shell/router.py` -- 2 endpoints, 0 auth deps
  - `backend/app/debug/router.py` -- 2 endpoints, 0 auth deps
  - `backend/app/commands/router.py` -- Proven pattern: require_role + performed_by
  - `backend/app/sparql/router.py` -- Proven pattern: get_current_user
  - `backend/app/models/router.py` -- Proven pattern: require_role("owner")
  - `backend/app/events/store.py` -- EventStore.commit() with optional performed_by
  - `backend/app/events/models.py` -- EVENT_PERFORMED_BY predicate exists
  - `backend/app/main.py` -- Router registration order, lifespan setup
  - `frontend/nginx.conf` -- Cookie forwarding already configured
  - `frontend/static/js/auth.js` -- Client-side auth flow, needs ?next= support
  - `.planning/v1.0-MILESTONE-AUDIT.md` -- INT-01, INT-02, INT-03 definitions

### Secondary (MEDIUM confidence)
- **FastAPI exception handler pattern** -- Based on FastAPI documentation knowledge of custom exception handlers and HTTPException handling in dependency chains. The core claim (HTTPException in sub-dependencies cannot be caught by parent dependencies) is well-established FastAPI behavior.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new libraries needed; all patterns already proven in codebase
- Architecture: HIGH -- Exception handler approach is well-understood FastAPI pattern; endpoint audit is exhaustive from direct code reading
- Pitfalls: HIGH -- Identified from direct code analysis (FastAPI dependency chain behavior, HTMX request detection, nginx cookie forwarding)

**Research date:** 2026-02-22
**Valid until:** Indefinitely (all findings based on static codebase analysis, no external library version dependencies)
