# Phase 49: IndieAuth Provider - Research

**Researched:** 2026-03-08
**Domain:** IndieAuth / OAuth2 Authorization Code Flow with PKCE
**Confidence:** HIGH

## Summary

IndieAuth is a decentralized identity protocol built on OAuth 2.0 that lets users authenticate with their own URL. SemPKM needs to become an IndieAuth **provider** (authorization server): exposing metadata discovery, an authorization endpoint with consent screen, a token endpoint for code exchange and refresh, and a token introspection endpoint. The spec is well-documented at indieauth.spec.indieweb.org and is a thin profile of OAuth 2.0 -- no exotic requirements.

The existing codebase has strong patterns to follow: router-per-domain organization, Alembic migrations, session-based auth with `get_current_user` dependency, opaque token generation via `secrets`, standalone HTML page template from WebID profile, and settings page section partials. The implementation is straightforward server-side OAuth2 with PKCE -- no third-party IndieAuth library is needed. The only new dependency is `mf2py` for parsing h-app microformats from client_id URLs to display friendly app names on the consent screen.

**Primary recommendation:** Implement as a new `backend/app/indieauth/` module with router, service, models, and schemas. Use opaque tokens (not JWT), store authorization codes and tokens in two new SQLite tables via Alembic migration 006. Reuse existing `_get_secret_key()` and `get_current_user` patterns. Add `mf2py` as the only new dependency.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Scope system:** Start with `profile` and `email` scopes only. `profile` returns display_name and profile URL. `email` is opt-in. Scope registry pattern (dict/enum) for future extensibility. No API access scopes.
- **Consent screen:** Standalone page, own template, SemPKM branding, light/dark theme. Shows app name + URL, requested scopes with descriptions, user identity, redirect destination. Fetch client_id URL to parse h-app microformat. If not logged in, redirect to login first then back to consent.
- **Token lifecycle:** Access tokens 1 hour TTL. Refresh tokens yes, 30-day TTL. Revocation UI in Settings as "Authorized Apps" section. Hard-delete on revoke.
- **Discovery & endpoints:** Canonical at `/api/indieauth/*` (authorize, token, introspect, metadata). `/.well-known/oauth-authorization-server` redirects to metadata. Discovery via both HTML `<link>` and HTTP `Link` header on profile responses. `rel="indieauth-metadata"` in WebID profile `<head>` and as Link header.
- **Storage:** Alembic migration 006 with `indieauth_codes` and `indieauth_tokens` tables. Foreign key to User. Clean separation from internal auth.

### Claude's Discretion
- Exact database column names and types
- PKCE implementation details (S256 only vs S256+plain)
- Authorization code TTL (typically 60 seconds)
- Token format (opaque vs JWT)
- h-app microformat parsing approach
- Consent page exact HTML/CSS layout
- Error response format details

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IAUTH-01 | Server exposes `rel="indieauth-metadata"` link for client discovery | Metadata endpoint JSON format documented; discovery via HTML `<link>` and HTTP `Link` header on profile responses; `/.well-known/oauth-authorization-server` redirect |
| IAUTH-02 | Authorization endpoint handles OAuth2 authorization code flow with mandatory PKCE | Full authorization request/response flow documented; PKCE S256 validation; `iss` parameter required in redirect; code_challenge storage and code_verifier verification |
| IAUTH-03 | Token endpoint issues access tokens after code exchange | Token exchange parameters documented; `application/x-www-form-urlencoded` request, JSON response; refresh token grant_type support |
| IAUTH-04 | Token endpoint supports token verification (introspection) | Introspection request/response format documented; active/inactive responses; required fields (me, client_id, scope, exp, iat) |
| IAUTH-05 | User sees consent screen showing requesting app and requested scopes | Consent screen elements documented; h-app microformat parsing via mf2py; scope descriptions; login redirect flow |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (existing) | HTTP endpoints, dependency injection | Already in stack |
| SQLAlchemy | (existing) | ORM for indieauth_codes and indieauth_tokens tables | Already in stack |
| Alembic | (existing) | Migration 006 for new tables | Already in stack |
| secrets | (stdlib) | Opaque token generation | Same pattern as existing session/API tokens |
| hashlib | (stdlib) | SHA-256 for PKCE code_challenge verification and token hashing | Standard, no deps |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mf2py | 2.x | Parse h-app microformat from client_id URL | Consent screen: fetch client_id, extract app name/logo |
| httpx | (existing) | Fetch client_id URL for h-app parsing | Already in stack, use async client |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mf2py | BeautifulSoup + manual parsing | mf2py is the canonical microformats parser; manual parsing would miss edge cases |
| Opaque tokens | JWT | Opaque tokens are simpler, consistent with existing patterns, no key management complexity; introspection endpoint handles validation |
| indieweb-utils | Custom implementation | indieweb-utils is Flask-oriented and bundles JWT-based tokens; our patterns use opaque tokens and FastAPI -- better to implement directly |

**Installation:**
```bash
pip install mf2py
```

Add to `backend/pyproject.toml` dependencies: `"mf2py>=2.0"`.
Note: This changes `pyproject.toml`, so Docker rebuild IS required.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/indieauth/
    __init__.py
    router.py          # FastAPI router with /api/indieauth/* endpoints
    service.py         # Business logic: code generation, token management, client fetch
    models.py          # SQLAlchemy models: IndieAuthCode, IndieAuthToken
    schemas.py         # Pydantic schemas for request/response validation
    scopes.py          # Scope registry (dict mapping scope name -> description)
backend/app/templates/indieauth/
    consent.html       # Standalone consent page (like profile.html)
backend/migrations/versions/
    006_indieauth_tables.py
```

### Pattern 1: Router Registration
**What:** New IndieAuth router follows the existing per-domain pattern.
**When to use:** All IndieAuth endpoints.
**Example:**
```python
# backend/app/indieauth/router.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/indieauth", tags=["indieauth"])

# In main.py:
from app.indieauth.router import router as indieauth_router
app.include_router(indieauth_router)
```

### Pattern 2: Standalone HTML Page (Consent Screen)
**What:** Copy the WebID profile.html pattern -- standalone HTML with inline CSS, light/dark theme via `prefers-color-scheme`, no base.html extension.
**When to use:** The consent screen.
**Example:**
```python
# Serve consent page as Jinja2 template
@router.get("/authorize")
async def authorize(request: Request, ...):
    # Validate params, fetch client info, render consent
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "indieauth/consent.html", {...})
```

### Pattern 3: Opaque Token with SHA-256 Hash Storage
**What:** Generate opaque token via `secrets.token_urlsafe()`, store SHA-256 hash in DB, return plaintext once.
**When to use:** Access tokens and refresh tokens.
**Example:**
```python
import hashlib, secrets

plaintext = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
# Store token_hash in DB, return plaintext to client
```

### Pattern 4: Authorization Code as Short-Lived DB Row
**What:** Auth code stored as a DB row with expiry, single-use enforced by deletion after exchange.
**When to use:** Authorization code generation and exchange.
**Example:**
```python
code = secrets.token_urlsafe(32)
# Store in indieauth_codes with: code_hash, user_id, client_id, redirect_uri,
# scope, code_challenge, code_challenge_method, expires_at
# On exchange: look up by hash, verify, delete row, issue token
```

### Pattern 5: Well-Known Redirect
**What:** `/.well-known/oauth-authorization-server` redirects to `/api/indieauth/metadata`.
**When to use:** OAuth2 generic client discovery.
**Example:**
```python
@router.get("/.well-known/oauth-authorization-server")
async def well_known_redirect():
    return RedirectResponse("/api/indieauth/metadata", status_code=307)
```
Note: This route is outside the `/api/indieauth` prefix, so it needs a separate router or direct registration. Use the `public_router` pattern from WebID.

### Anti-Patterns to Avoid
- **JWT for tokens:** Adds key management complexity and makes revocation harder. Opaque tokens with DB lookup are simpler and consistent with existing patterns.
- **Storing plaintext tokens:** Always store SHA-256 hash, return plaintext once.
- **Fetching localhost client_ids:** SSRF risk. IndieAuth spec says do NOT fetch `127.0.0.1` or `[::1]` client_id URLs.
- **Reusing session auth tables:** IndieAuth tokens are separate from internal sessions. Keep clean separation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Microformat parsing | Custom HTML scraper for h-app | `mf2py` library | Microformats have complex parsing rules (nested, implied properties, backcompat) |
| PKCE S256 verification | - | `hashlib.sha256` + `base64.urlsafe_b64encode` | Simple enough to implement directly, but get the base64url encoding right (no padding) |
| URL validation for client_id | Custom regex | `urllib.parse.urlparse` + validation rules | IndieAuth has specific URL requirements (scheme, path, no fragments, no userinfo) |

**Key insight:** IndieAuth is intentionally simple. The protocol is a thin OAuth2 profile. Most complexity is in getting the details right (PKCE base64url encoding, exact response formats, `iss` parameter) rather than in algorithmic difficulty.

## Common Pitfalls

### Pitfall 1: PKCE Base64URL Encoding Without Padding
**What goes wrong:** Standard `base64.b64encode` includes `+`, `/`, and `=` padding. PKCE requires base64url (RFC 4648 Section 5) with NO padding.
**Why it happens:** Python's `base64.urlsafe_b64encode` does use `-` and `_` but still includes `=` padding.
**How to avoid:** Strip padding: `base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')`
**Warning signs:** PKCE verification fails for legitimate clients.

### Pitfall 2: Content-Type Mismatch
**What goes wrong:** Token endpoint must accept `application/x-www-form-urlencoded` (NOT JSON) and return `application/json`. Many implementations accidentally expect JSON input.
**Why it happens:** FastAPI defaults to JSON body parsing.
**How to avoid:** Use `Form(...)` parameters in FastAPI, not `Body(...)` or Pydantic models for the token endpoint.
**Warning signs:** Clients get 422 Unprocessable Entity errors.

### Pitfall 3: Missing `iss` Parameter in Authorization Response
**What goes wrong:** IndieAuth spec REQUIRES `iss` parameter in the authorization redirect callback. Without it, spec-compliant clients reject the response.
**Why it happens:** Earlier IndieAuth versions didn't require it; copy-paste from old examples omits it.
**How to avoid:** Always include `iss` (the metadata endpoint URL or issuer URL) in redirect query params alongside `code` and `state`.
**Warning signs:** Clients report "issuer mismatch" errors.

### Pitfall 4: Authorization Code Replay
**What goes wrong:** If authorization codes aren't single-use, an attacker who intercepts a code can exchange it multiple times.
**Why it happens:** Not deleting the code row after successful exchange.
**How to avoid:** Delete the `indieauth_codes` row atomically during exchange. If the row doesn't exist, reject.
**Warning signs:** Security audit finding.

### Pitfall 5: SSRF via Client ID Fetch
**What goes wrong:** Server fetches arbitrary URLs when parsing client_id for h-app metadata. Attacker provides internal network URL as client_id.
**Why it happens:** No URL validation before fetch.
**How to avoid:** Validate client_id URL per spec rules. Reject loopback addresses for non-development. Set timeout and size limits on the fetch. Use `httpx` with timeout.
**Warning signs:** Internal service responses appearing in consent screen.

### Pitfall 6: nginx Not Forwarding .well-known Paths
**What goes wrong:** `/.well-known/oauth-authorization-server` hits nginx's catch-all `location /` but may not reach the API properly.
**Why it happens:** nginx config doesn't explicitly route `.well-known` paths.
**How to avoid:** The existing catch-all `location /` already proxies to the API. Verify it works -- no special nginx config needed since the catch-all proxies everything not matched by specific location blocks.
**Warning signs:** 404 on `.well-known` URL.

## Code Examples

### PKCE S256 Verification
```python
# Source: IndieAuth spec + RFC 7636
import hashlib
import base64

def verify_pkce_s256(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE S256 challenge against verifier."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return computed == code_challenge
```

### Metadata Endpoint Response
```python
# Source: IndieAuth spec Section 4.1
@router.get("/metadata")
async def metadata(request: Request):
    base_url = get_base_url(request)
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/api/indieauth/authorize",
        "token_endpoint": f"{base_url}/api/indieauth/token",
        "introspection_endpoint": f"{base_url}/api/indieauth/introspect",
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["profile", "email"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "introspection_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
        "authorization_response_iss_parameter_supported": True,
    }
```

### Token Endpoint (Form Parameters)
```python
# Source: IndieAuth spec + OAuth 2.0 RFC 6749
from fastapi import Form

@router.post("/token")
async def token_endpoint(
    grant_type: str = Form(...),
    code: str | None = Form(None),
    client_id: str | None = Form(None),
    redirect_uri: str | None = Form(None),
    code_verifier: str | None = Form(None),
    refresh_token: str | None = Form(None),
):
    if grant_type == "authorization_code":
        # Exchange code for token
        ...
    elif grant_type == "refresh_token":
        # Refresh existing token
        ...
```

### Client ID Validation
```python
# Source: IndieAuth spec Section 3.2
from urllib.parse import urlparse

def validate_client_id(client_id: str) -> bool:
    """Validate client_id URL per IndieAuth spec."""
    parsed = urlparse(client_id)
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.path or parsed.path == "":
        return False
    if parsed.fragment:
        return False
    if parsed.username or parsed.password:
        return False
    # Check for single/double dot path segments
    for segment in parsed.path.split("/"):
        if segment in (".", ".."):
            return False
    return True
```

### Fetching Client h-app Info
```python
# Source: IndieAuth spec + mf2py docs
import httpx
import mf2py

async def fetch_client_info(client_id: str) -> dict:
    """Fetch and parse h-app microformat from client_id URL.

    Returns dict with keys: name, url, logo (all optional).
    Falls back to page title or URL itself.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(client_id, follow_redirects=True)
            resp.raise_for_status()
    except Exception:
        return {"name": client_id, "url": client_id, "logo": None}

    parsed = mf2py.parse(doc=resp.text, url=client_id)

    # Look for h-app microformat
    for item in parsed.get("items", []):
        if "h-app" in item.get("type", []):
            props = item.get("properties", {})
            return {
                "name": props.get("name", [client_id])[0],
                "url": props.get("url", [client_id])[0],
                "logo": props.get("logo", [None])[0],
            }

    # Fallback: use page title
    # (mf2py doesn't extract <title>, parse it from HTML)
    from html.parser import HTMLParser
    title = client_id
    # Simple title extraction...

    return {"name": title, "url": client_id, "logo": None}
```

### Authorization Code DB Model
```python
# Source: Project patterns (auth/models.py)
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class IndieAuthCode(Base):
    __tablename__ = "indieauth_codes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    client_id: Mapped[str] = mapped_column(String(2048))
    redirect_uri: Mapped[str] = mapped_column(String(2048))
    scope: Mapped[str] = mapped_column(String(512))  # space-separated
    code_challenge: Mapped[str] = mapped_column(String(128))
    code_challenge_method: Mapped[str] = mapped_column(String(10), default="S256")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IndieAuthToken(Base):
    __tablename__ = "indieauth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    client_id: Mapped[str] = mapped_column(String(2048))
    scope: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refresh_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

### Scope Registry
```python
# Source: CONTEXT.md decision
SCOPE_REGISTRY: dict[str, dict[str, str]] = {
    "profile": {
        "description": "Access your basic profile information",
        "detail": "Your display name and profile URL",
    },
    "email": {
        "description": "Access your email address",
        "detail": "Your email address associated with this account",
    },
}

def validate_scopes(requested: str) -> list[str]:
    """Validate and return list of known scopes from space-separated string."""
    scopes = requested.split()
    return [s for s in scopes if s in SCOPE_REGISTRY]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| h-app microformat for client metadata | JSON client metadata document (OAuth Client ID Metadata) | IndieAuth spec update ~2023 | Servers should support both for backwards compat |
| No PKCE requirement | PKCE mandatory (S256) | IndieAuth spec update ~2023 | All authorization requests MUST include code_challenge |
| No `iss` parameter | `iss` parameter required in authorization response | IndieAuth spec update ~2023 | Prevents authorization server mix-up attacks |
| Token verification via GET to token endpoint | Dedicated introspection endpoint (RFC 7662) | IndieAuth spec update ~2023 | Separate endpoint, POST with token in body |

**Deprecated/outdated:**
- Token verification via GET to the token endpoint (old spec) -- use introspection endpoint instead
- Optional PKCE -- now mandatory
- Authorization response without `iss` -- now required

## Open Questions

1. **h-app fallback for pages without microformats**
   - What we know: Most client_id URLs won't have h-app markup
   - What's unclear: Best fallback -- `<title>` tag? OpenGraph `og:title`? Just the URL?
   - Recommendation: Try h-app first, then `<title>` tag, then URL hostname. Keep it simple.

2. **Rate limiting on authorization endpoint**
   - What we know: Public endpoint that triggers user-facing consent screen
   - What's unclear: Whether rate limiting is needed for this phase
   - Recommendation: Defer rate limiting. The consent screen requires an authenticated user session, limiting abuse surface.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (e2e) + pytest (unit, dev optional dep) |
| Config file | `e2e/playwright.config.ts` (e2e); no pytest config (backend unit) |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -g "indieauth"` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IAUTH-01 | Metadata endpoint returns valid JSON with required fields; `rel="indieauth-metadata"` appears on profile page | e2e | `npx playwright test --project=chromium -g "indieauth metadata"` | No -- Wave 0 |
| IAUTH-02 | Full authorization code flow with PKCE completes successfully | e2e | `npx playwright test --project=chromium -g "indieauth authorize"` | No -- Wave 0 |
| IAUTH-03 | Token endpoint issues access token after valid code exchange | e2e | `npx playwright test --project=chromium -g "indieauth token"` | No -- Wave 0 |
| IAUTH-04 | Introspection endpoint returns active=true for valid token, active=false for invalid | e2e | `npx playwright test --project=chromium -g "indieauth introspect"` | No -- Wave 0 |
| IAUTH-05 | Consent screen shows app name, scopes, user identity; user can approve/deny | e2e | `npx playwright test --project=chromium -g "indieauth consent"` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Quick run of indieauth-specific tests
- **Per wave merge:** Full e2e suite (`npx playwright test --project=chromium`)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `e2e/tests/16-indieauth/indieauth-flow.spec.ts` -- covers IAUTH-01 through IAUTH-05
- [ ] Test needs to simulate an IndieAuth client: generate PKCE verifier/challenge, hit authorize endpoint, submit consent, exchange code for token, introspect token
- [ ] Note: e2e tests cannot be modified per project rules, but new test files can be created

## Sources

### Primary (HIGH confidence)
- [IndieAuth Specification](https://indieauth.spec.indieweb.org/) - Full protocol details, endpoint requirements, PKCE, metadata, introspection
- Existing codebase: `backend/app/auth/` (session/token patterns), `backend/app/webid/` (profile/router patterns)

### Secondary (MEDIUM confidence)
- [indieweb-utils docs](https://indieweb-utils.readthedocs.io/en/latest/indieauth.html) - Server-side helper reference (not used as dependency, but validates approach)
- [IndieWeb consent_screen page](https://indieweb.org/consent_screen) - Best practices for consent UI
- [mf2py on GitHub](https://github.com/microformats/mf2py) - Microformats parser (v2.x, actively maintained)

### Tertiary (LOW confidence)
- [IndieAuth community implementations](https://indieweb.org/IndieAuth) - General ecosystem context

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Protocol is well-specified, existing codebase patterns are clear, only one new dep (mf2py)
- Architecture: HIGH - Follows established project patterns (router-per-domain, Alembic, opaque tokens)
- Pitfalls: HIGH - Spec explicitly documents requirements (PKCE format, iss param, content-type); common OAuth2 pitfalls well-known

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (IndieAuth spec is stable, infrequent changes)
