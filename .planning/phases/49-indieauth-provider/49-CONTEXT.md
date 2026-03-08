# Phase 49: IndieAuth Provider - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

SemPKM becomes an IndieAuth provider: users can sign into IndieWeb-compatible services using their SemPKM profile URL as their identity. This phase implements the OAuth2 authorization code flow with PKCE, consent screen, token management, and metadata discovery. The WebID profile (Phase 48) provides the identity URL that IndieAuth references.

</domain>

<decisions>
## Implementation Decisions

### Scope system
- Start with two scopes: `profile` (identity/sign-in) and `email` (optional, returns user email)
- `profile` returns: display_name and profile URL only — minimal, privacy-respecting
- `email` is opt-in: clients can request it, user sees it on consent screen
- Scope registry pattern: scopes defined in a dict/enum that future phases can extend without changing IndieAuth code
- No API access scopes (create/read/update/delete) in this phase — defer to future collaboration phases

### Consent screen
- Standalone page — own template, SemPKM branding, light/dark theme (consistent with WebID profile page)
- Shows all four pieces of info: app name + URL, requested scopes with human-readable descriptions, user's identity (WebID/profile URL), redirect destination
- Fetch client_id URL to parse h-app microformat or page title for friendlier app name/logo display
- If user is not logged into SemPKM: redirect to login (magic link) first, then back to consent screen

### Token lifecycle
- Access tokens: 1 hour TTL
- Refresh tokens: yes, 30-day TTL — clients can silently renew without re-authorization
- Revocation UI: "Authorized Apps" section in Settings showing active tokens with app name, granted scopes, and Revoke button
- Tokens revoked via hard-delete (consistent with existing API token revocation pattern)

### Discovery & endpoints
- Canonical endpoints at `/api/indieauth/*`:
  - `/api/indieauth/authorize` — authorization endpoint
  - `/api/indieauth/token` — token endpoint (issue, refresh)
  - `/api/indieauth/introspect` — token introspection
  - `/api/indieauth/metadata` — server metadata JSON
- `/.well-known/oauth-authorization-server` redirects to `/api/indieauth/metadata`
- Discovery via both HTML `<link>` tag and HTTP `Link` header on profile responses — maximum compatibility
- `rel="indieauth-metadata"` added to WebID profile.html `<head>` AND as Link header on all profile response formats
- Metadata endpoint advertises: authorization_endpoint, token_endpoint, introspection_endpoint, supported scopes, PKCE methods

### Storage
- New Alembic migration (006) with dedicated IndieAuth tables:
  - `indieauth_codes` — authorization codes (short-lived, single-use)
  - `indieauth_tokens` — access tokens and refresh tokens
- Foreign key to User table
- Clean separation from internal session auth

### Claude's Discretion
- Exact database column names and types
- PKCE implementation details (S256 only vs S256+plain)
- Authorization code TTL (typically 60 seconds)
- Token format (opaque vs JWT)
- h-app microformat parsing approach
- Consent page exact HTML/CSS layout
- Error response format details

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/webid/router.py`: public_router pattern (no auth) — reuse for consent page and well-known redirect
- `backend/app/webid/service.py`: `get_base_url()`, `build_profile_url()`, `build_webid_uri()` — needed for constructing identity URLs
- `backend/app/auth/service.py`: `AuthService` — session management, user lookup patterns
- `backend/app/auth/dependencies.py`: `get_current_user` — needed for consent screen (user must be logged in)
- `backend/app/auth/tokens.py`: `_get_secret_key()` — Fernet key derivation pattern, reuse for token signing
- `backend/app/templates/webid/profile.html`: standalone page template with light/dark theme — copy pattern for consent page

### Established Patterns
- Router per domain: `backend/app/{domain}/router.py`, registered in `main.py`
- Alembic migrations: `backend/migrations/versions/` (currently at 005)
- Settings page sections: `backend/app/templates/browser/_webid_settings.html` — pattern for "Authorized Apps" section
- Session cookies: `sempkm_session`, httponly, samesite=lax
- Hard-delete for token revocation (existing API tokens pattern)

### Integration Points
- WebID profile template: add `<link rel="indieauth-metadata">` to `<head>`
- WebID profile router: add `Link` header to all response formats
- Settings page: add "Authorized Apps" section
- Router registration in `backend/app/main.py`
- nginx: may need to pass through `/.well-known/` paths to API

</code_context>

<specifics>
## Specific Ideas

- Consent page should feel like the WebID profile page — clean, branded, standalone
- Well-known URLs redirect to canonical /api/indieauth/ endpoints for discoverability by generic OAuth2 clients
- Scope registry is a simple extensibility point — future phases add scopes without touching IndieAuth flow code

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 49-indieauth-provider*
*Context gathered: 2026-03-08*
