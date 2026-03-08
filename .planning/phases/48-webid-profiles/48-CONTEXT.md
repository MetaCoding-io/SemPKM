# Phase 48: WebID Profiles - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Each SemPKM user gets a dereferenceable WebID URI (`/users/{username}#me`) that resolves to an RDF profile document. Content negotiation serves Turtle, JSON-LD, or a styled HTML page. The profile publishes an Ed25519 public key and `rel="me"` links for fediverse verification. IndieAuth (authorization/token endpoints) is Phase 49.

</domain>

<decisions>
## Implementation Decisions

### Profile URL structure
- WebID URI format: `{app_base_url}/users/{username}#me`
- Profile document URL: `{app_base_url}/users/{username}`
- Username is user-chosen, immutable after creation
- Username validation: lowercase, alphanumeric + hyphens, unique
- User picks username on first visit to WebID settings (not auto-derived)
- Reuse existing `app_base_url` config — no separate WebID base URL config

### Profile visibility
- Profiles are public but opt-in — returns 404 until user explicitly publishes
- Publishing toggle in Settings alongside username setup

### Profile content (RDF)
- Essential identity only: `foaf:name`, WebID URI, public key, `foaf:account` for rel="me" links
- Document typed as `foaf:PersonalProfileDocument` with `foaf:primaryTopic <#me>`
- No rich profile fields (bio, avatar, email hash) — keep minimal

### Profile content (HTML)
- Styled standalone page — own template, not extending base.html with sidebar
- SemPKM logo/branding, light/dark mode (respects `prefers-color-scheme`)
- Shows: name, WebID URI, public key fingerprint with "Copy PEM" action, verified profile links
- Includes alternate format links ("View as Turtle | JSON-LD") for developer discovery
- `<link rel="me" ...>` tags in `<head>` for fediverse verification

### Content negotiation
- Accept header determines response format:
  - `text/turtle` → Turtle
  - `application/ld+json` → JSON-LD
  - `text/html` (or default) → HTML profile page

### rel="me" link management
- Managed in a "WebID Profile" section within the existing Settings page
- Links stored as JSON array in a Text column on User table (SQL, not triplestore)
- Validated as http/https URLs before saving
- No limit on number of links
- Add/remove UI with [+ Add link] and [×] remove buttons

### Key lifecycle
- Ed25519 key pair generated when user chooses username (single setup action)
- Private key encrypted with Fernet (same PBKDF2 pattern as LLM API key encryption)
- Public key stored as PEM in User table
- Public key published using W3C Security Vocabulary (`sec:publicKeyPem`, `sec:Ed25519VerificationKey2020`)
- Users can regenerate key pair via "Regenerate Key" button with confirmation dialog
- Old key discarded on regeneration — no key history

### Claude's Discretion
- Database migration structure (column names, types)
- Router/service module organization
- Exact HTML template styling and layout details
- Content negotiation parsing approach
- Key fingerprint display format

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/llm.py`: Fernet encryption pattern (`_get_fernet`, `encrypt_api_key`, `decrypt_api_key`) — reuse for Ed25519 private key encryption
- `backend/app/rdf/jsonld.py`: `graph_to_jsonld()` for JSON-LD serialization with SemPKM context
- `backend/app/rdf/namespaces.py`: FOAF, SCHEMA, SEMPKM namespaces already defined
- `backend/app/triplestore/client.py`: `construct()` method returns Turtle bytes — pattern for RDF serialization
- Jinja2 template engine with `jinja2-fragments` for block-based rendering

### Established Patterns
- Router per domain: `backend/app/{domain}/router.py`, registered in `main.py`
- Auth dependencies: `get_current_user`, `require_role()` for protected endpoints
- Pydantic schemas in `{domain}/schemas.py` for request/response validation
- Alembic migrations in `backend/migrations/versions/` (currently at 004)
- Instance config via `InstanceConfig` key-value table
- User settings via `user_settings` table (key-value per user)

### Integration Points
- User model: `backend/app/auth/models.py` — needs new columns (username, public_key, private_key_encrypted, webid_links, webid_published)
- Settings page: needs new "WebID Profile" section
- `app_base_url` in `backend/app/config.py` — used to construct WebID URIs
- Router registration in `backend/app/main.py`

</code_context>

<specifics>
## Specific Ideas

- Profile page mockup: SemPKM branding at top, user name, WebID URI, public key fingerprint with copy button, list of verified profile links, and format links at bottom
- Fediverse verification flow: HTML page has `<link rel="me" href="...">` in `<head>`, Mastodon checks that the linked profile links back

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 48-webid-profiles*
*Context gathered: 2026-03-08*
