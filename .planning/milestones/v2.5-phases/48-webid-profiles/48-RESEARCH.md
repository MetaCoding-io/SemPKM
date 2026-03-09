# Phase 48: WebID Profiles - Research

**Researched:** 2026-03-08
**Domain:** WebID / Linked Data Identity / Content Negotiation / Ed25519 Cryptography
**Confidence:** HIGH

## Summary

Phase 48 adds dereferenceable WebID URIs to SemPKM. Each user gets a URI of the form `{app_base_url}/users/{username}#me` that resolves to an RDF profile document (Turtle, JSON-LD, or HTML via content negotiation). The profile publishes the user's Ed25519 public key using the W3C Security Vocabulary and includes `rel="me"` links for fediverse (Mastodon) verification.

The implementation is self-contained: a new `webid` domain module with router, service, schemas, and templates. The User model gains five new columns (username, public_key_pem, private_key_encrypted, webid_links, webid_published) via Alembic migration 005. Ed25519 key generation uses the existing `cryptography` library (already a dependency). Private keys are Fernet-encrypted at rest using the same PBKDF2 pattern as LLM API key encryption. The profile document is constructed with rdflib (already a dependency) and serialized to Turtle/JSON-LD. The HTML page is a standalone Jinja2 template.

**Primary recommendation:** Build as a new `backend/app/webid/` domain module following the existing router-per-domain pattern, reusing established Fernet encryption, rdflib serialization, and Jinja2 templating infrastructure.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- WebID URI format: `{app_base_url}/users/{username}#me`
- Profile document URL: `{app_base_url}/users/{username}`
- Username is user-chosen, immutable after creation
- Username validation: lowercase, alphanumeric + hyphens, unique
- User picks username on first visit to WebID settings (not auto-derived)
- Reuse existing `app_base_url` config -- no separate WebID base URL config
- Profiles are public but opt-in -- returns 404 until user explicitly publishes
- Publishing toggle in Settings alongside username setup
- Essential identity only: `foaf:name`, WebID URI, public key, `foaf:account` for rel="me" links
- Document typed as `foaf:PersonalProfileDocument` with `foaf:primaryTopic <#me>`
- No rich profile fields (bio, avatar, email hash) -- keep minimal
- Styled standalone page -- own template, not extending base.html with sidebar
- SemPKM logo/branding, light/dark mode (respects `prefers-color-scheme`)
- Shows: name, WebID URI, public key fingerprint with "Copy PEM" action, verified profile links
- Includes alternate format links ("View as Turtle | JSON-LD") for developer discovery
- `<link rel="me" ...>` tags in `<head>` for fediverse verification
- Accept header determines format: `text/turtle` -> Turtle, `application/ld+json` -> JSON-LD, `text/html` (or default) -> HTML
- Links stored as JSON array in a Text column on User table (SQL, not triplestore)
- Validated as http/https URLs before saving
- No limit on number of links
- Add/remove UI with [+ Add link] and [x] remove buttons
- Ed25519 key pair generated when user chooses username (single setup action)
- Private key encrypted with Fernet (same PBKDF2 pattern as LLM API key encryption)
- Public key stored as PEM in User table
- Public key published using W3C Security Vocabulary (`sec:publicKeyPem`, `sec:Ed25519VerificationKey2020`)
- Users can regenerate key pair via "Regenerate Key" button with confirmation dialog
- Old key discarded on regeneration -- no key history
- Managed in a "WebID Profile" section within the existing Settings page

### Claude's Discretion
- Database migration structure (column names, types)
- Router/service module organization
- Exact HTML template styling and layout details
- Content negotiation parsing approach
- Key fingerprint display format

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WBID-01 | Each user has a WebID URI (e.g. `https://instance/users/alice#me`) | URI construction from `app_base_url` + username; Architecture Pattern 1 |
| WBID-02 | Dereferencing the WebID URI returns an RDF profile document (FOAF/schema.org properties) | rdflib Graph construction with FOAF vocabulary; Code Example 1 |
| WBID-03 | Content negotiation serves Turtle, JSON-LD, or HTML based on Accept header | Accept header parsing pattern; Architecture Pattern 2 |
| WBID-04 | Profile page includes `rel="me"` links for fediverse verification | Mastodon verification protocol; Code Example 3 |
| WBID-05 | Server generates Ed25519 key pair per user, stores encrypted | `cryptography` library Ed25519 API + Fernet encryption; Code Example 2 |
| WBID-06 | Public key is published in the WebID profile document | W3C Security Vocabulary `sec:publicKeyPem`; Code Example 1 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rdflib | >=7.5.0 | RDF graph construction + Turtle/JSON-LD serialization | Already in project; handles all RDF formats |
| cryptography | >=43.0 | Ed25519 key generation + Fernet encryption | Already in project; `Ed25519PrivateKey.generate()` is the standard API |
| FastAPI | (current) | HTTP routing + content negotiation | Already in project; `Request.headers` for Accept parsing |
| Jinja2 | (current) | HTML profile page template | Already in project via `jinja2-fragments` |
| SQLAlchemy | >=2.0.46 | User model columns + Alembic migration | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | (current) | Request/response schemas for username setup, link management | Validation of username format, URL format |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sec:publicKeyPem` | `sec:publicKeyMultibase` | W3C prefers multibase for new deployments, but user locked PEM. PEM is simpler and more widely understood. Fine for WebID profiles. |
| rdflib JSON-LD serializer | Manual JSON construction | rdflib handles edge cases (blank nodes, datatypes). Use rdflib. |

**Installation:**
No new dependencies required -- all libraries are already in `backend/pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/webid/
    __init__.py
    router.py          # Public profile endpoint + settings API endpoints
    service.py          # Key generation, profile RDF construction, username management
    schemas.py          # Pydantic models for username setup, link management

backend/app/templates/
    webid/
        profile.html    # Standalone public profile page (no base.html extension)
    browser/
        _webid_settings.html  # Settings panel partial (included in settings_page.html)

backend/migrations/versions/
    005_webid_columns.py  # Add username, keys, links, published flag to users table
```

### Pattern 1: WebID URI Construction
**What:** Construct the WebID URI from `app_base_url` and username
**When to use:** Anywhere a WebID URI is needed (profile document, RDF serialization, template rendering)
**Example:**
```python
from app.config import settings

def build_webid_uri(username: str) -> str:
    """Build the WebID URI for a user."""
    base = settings.app_base_url.rstrip("/")
    return f"{base}/users/{username}#me"

def build_profile_url(username: str) -> str:
    """Build the profile document URL (without fragment)."""
    base = settings.app_base_url.rstrip("/")
    return f"{base}/users/{username}"
```

### Pattern 2: Content Negotiation
**What:** Route same URL to different response formats based on Accept header
**When to use:** The `/users/{username}` endpoint
**Example:**
```python
from fastapi import Request
from fastapi.responses import Response, HTMLResponse

@router.get("/users/{username}")
async def get_profile(username: str, request: Request):
    accept = request.headers.get("accept", "text/html")

    if "text/turtle" in accept:
        turtle_bytes = graph.serialize(format="turtle")
        return Response(content=turtle_bytes, media_type="text/turtle")
    elif "application/ld+json" in accept:
        jsonld = graph_to_jsonld(graph)
        return JSONResponse(content=jsonld, media_type="application/ld+json")
    else:
        # Default: HTML
        return templates.TemplateResponse(request, "webid/profile.html", context)
```

### Pattern 3: Fernet Encryption for Private Keys (Reuse Existing)
**What:** Encrypt Ed25519 private key PEM using same pattern as LLM API key encryption
**When to use:** When storing/retrieving private keys
**Reference:** `backend/app/services/llm.py` -- `_get_fernet()`, `encrypt_api_key()`, `decrypt_api_key()`
**Note:** Use a different KDF salt (e.g., `b"sempkm-webid-keys-v1"`) to derive a different Fernet key from the same `secret_key`. This is cryptographically sound -- same master key, different derived keys per domain.

### Anti-Patterns to Avoid
- **Storing private key unencrypted:** Always Fernet-encrypt before writing to DB
- **Using triplestore for profile data:** User decided SQL columns on User table, not triplestore. RDF is generated on-the-fly from SQL data.
- **Extending base.html for profile page:** User decided standalone template. The profile page is public and should not include workspace sidebar/navigation.
- **Auto-generating username from email:** User decided username is explicitly chosen by user, not derived.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 key generation | Custom crypto | `cryptography.hazmat.primitives.asymmetric.ed25519` | Standard, audited implementation |
| RDF serialization | String concatenation for Turtle/JSON-LD | `rdflib.Graph.serialize()` | Handles escaping, prefixes, blank nodes correctly |
| Fernet encryption | Custom symmetric cipher | `cryptography.fernet.Fernet` via PBKDF2 | Existing pattern in codebase, proven |
| Accept header parsing | Simple string split | Check for media type containment (see pattern) | Good enough for 3 known types; no need for full conneg library |
| URL validation | Regex | `pydantic.HttpUrl` or `urllib.parse.urlparse` | Pydantic already validates in schemas |
| Key fingerprint | Manual hash formatting | `hashlib.sha256(public_key_der).hexdigest()` | Standard fingerprint approach |

**Key insight:** Every component of this phase has existing infrastructure in the codebase or standard library. No new dependencies needed.

## Common Pitfalls

### Pitfall 1: app_base_url Not Set
**What goes wrong:** WebID URIs contain empty base URL, producing invalid URIs like `/users/alice#me`
**Why it happens:** `app_base_url` defaults to empty string in config.py (derived from request headers)
**How to avoid:** When constructing WebID URIs, if `app_base_url` is empty, derive from the current request's `Host` header and scheme. The profile endpoint always has access to the Request object.
**Warning signs:** WebID URIs without scheme/host in Turtle output

### Pitfall 2: Fragment Identifier in Content Negotiation
**What goes wrong:** Browser requests `#me` fragment, but HTTP fragments are never sent to the server
**Why it happens:** `#me` is a fragment identifier, stripped by the browser before making the HTTP request
**How to avoid:** This is actually the correct behavior. The server receives `/users/{username}`, serves the profile document, and the `#me` fragment identifies the person within that document. No special handling needed -- just document it correctly in the RDF (`<> foaf:primaryTopic <#me>`).
**Warning signs:** None -- this is how WebID is designed

### Pitfall 3: Mastodon rel="me" Verification Requires Bidirectional Links
**What goes wrong:** User adds Mastodon URL to profile links but verification fails
**Why it happens:** Mastodon checks that the external page links BACK to the Mastodon profile. The SemPKM profile must contain `<a href="https://mastodon.social/@user" rel="me">` AND the Mastodon profile metadata must link to the SemPKM profile URL.
**How to avoid:** Document this in the UI -- show instructions explaining bidirectional linking. The `<link rel="me">` tags in `<head>` satisfy the technical requirement.
**Warning signs:** Links shown without verification checkmarks on Mastodon

### Pitfall 4: Username Uniqueness Race Condition
**What goes wrong:** Two users try to claim the same username simultaneously
**Why it happens:** Check-then-insert without database constraint
**How to avoid:** Add `UNIQUE` constraint on the username column in the migration. Let the database enforce uniqueness. Catch `IntegrityError` and return a user-friendly error message.
**Warning signs:** Duplicate usernames in database

### Pitfall 5: JSON-LD Serialization Missing FOAF/Security Context
**What goes wrong:** JSON-LD output uses full IRIs instead of compact prefixes; consumers may not understand the vocabulary
**Why it happens:** The existing `SEMPKM_CONTEXT` in `jsonld.py` doesn't include FOAF or Security Vocabulary prefixes
**How to avoid:** Build a WebID-specific JSON-LD context that includes `foaf`, `sec` (W3C Security Vocabulary) prefixes. Don't modify the shared SEMPKM context.

### Pitfall 6: PEM Key Format Mismatch
**What goes wrong:** Published PEM doesn't match what consumers expect
**Why it happens:** `cryptography` library can output PEM in PKCS8 or raw format
**How to avoid:** Use `SubjectPublicKeyInfo` format for public key PEM -- this is the standard X.509 format that external consumers expect. Use `PKCS8` format for private key PEM.

## Code Examples

Verified patterns from official sources and existing codebase:

### Example 1: RDF Profile Document Construction
```python
# Source: rdflib docs + W3C WebID spec + FOAF vocabulary
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, FOAF, XSD

SEC = Namespace("https://w3id.org/security#")

def build_profile_graph(
    profile_url: str,
    webid_uri: str,
    display_name: str,
    public_key_pem: str,
    rel_me_links: list[str],
) -> Graph:
    g = Graph()
    g.bind("foaf", FOAF)
    g.bind("sec", SEC)

    doc = URIRef(profile_url)
    me = URIRef(webid_uri)
    key_node = URIRef(f"{webid_uri}-key")

    # Profile document metadata
    g.add((doc, RDF.type, FOAF.PersonalProfileDocument))
    g.add((doc, FOAF.maker, me))
    g.add((doc, FOAF.primaryTopic, me))

    # Person
    g.add((me, RDF.type, FOAF.Person))
    g.add((me, FOAF.name, Literal(display_name)))

    # Public key
    g.add((me, SEC.verificationMethod, key_node))
    g.add((key_node, RDF.type, SEC.Ed25519VerificationKey2020))
    g.add((key_node, SEC.controller, me))
    g.add((key_node, SEC.publicKeyPem, Literal(public_key_pem)))

    # rel="me" links as foaf:account
    for link_url in rel_me_links:
        g.add((me, FOAF.account, URIRef(link_url)))

    return g
```

### Example 2: Ed25519 Key Generation + Fernet Encryption
```python
# Source: cryptography library docs (https://cryptography.io/en/latest/)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def generate_ed25519_keypair() -> tuple[str, str]:
    """Generate Ed25519 key pair. Returns (public_pem, private_pem)."""
    private_key = Ed25519PrivateKey.generate()

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    return public_pem, private_pem


# Encryption at rest -- reuse pattern from app/services/llm.py
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_WEBID_KDF_SALT = b"sempkm-webid-keys-v1"

def _get_webid_fernet(secret_key: str) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_WEBID_KDF_SALT,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return Fernet(key)

def encrypt_private_key(private_pem: str, secret_key: str) -> str:
    return _get_webid_fernet(secret_key).encrypt(private_pem.encode()).decode()

def decrypt_private_key(ciphertext: str, secret_key: str) -> str | None:
    from cryptography.fernet import InvalidToken
    try:
        return _get_webid_fernet(secret_key).decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        return None
```

### Example 3: HTML Profile with rel="me" Tags
```html
<!-- Standalone template -- does NOT extend base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ display_name }} - WebID Profile</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {% for link_url in rel_me_links %}
  <link rel="me" href="{{ link_url }}">
  {% endfor %}
  <link rel="alternate" type="text/turtle" href="{{ profile_url }}">
  <link rel="alternate" type="application/ld+json" href="{{ profile_url }}">
  <style>
    /* Inline styles for standalone page -- prefers-color-scheme for light/dark */
    @media (prefers-color-scheme: dark) { /* dark theme vars */ }
  </style>
</head>
<body>
  <!-- SemPKM branding, name, WebID URI, key fingerprint, links -->
</body>
</html>
```

### Example 4: Key Fingerprint Display
```python
import hashlib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_public_key

def key_fingerprint(public_key_pem: str) -> str:
    """SHA-256 fingerprint of the public key DER bytes, colon-separated hex."""
    pub_key = load_pem_public_key(public_key_pem.encode())
    der_bytes = pub_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashlib.sha256(der_bytes).hexdigest()
    # Format as colon-separated pairs: "ab:cd:ef:..."
    return ":".join(digest[i:i+2] for i in range(0, len(digest), 2))
```

### Example 5: Alembic Migration Pattern
```python
# Migration 005: Add WebID columns to users table
# Source: existing migration pattern in backend/migrations/versions/003_api_tokens.py

def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(63), nullable=True))
    op.add_column("users", sa.Column("public_key_pem", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("private_key_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("webid_links", sa.Text(), nullable=True))  # JSON array
    op.add_column("users", sa.Column("webid_published", sa.Boolean(), nullable=True, server_default=sa.false()))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| RSA keys for WebID-TLS | Ed25519 keys for signing | ~2020 | Smaller keys (32 bytes), faster, Ed25519VerificationKey2020 spec |
| `cert:RSAPublicKey` | `sec:Ed25519VerificationKey2020` | ~2020 | Different namespace (w3id.org/security vs w3.org/ns/auth/cert) |
| `sec:publicKeyBase58` | `sec:publicKeyMultibase` (preferred) | ~2022 | User chose PEM format, which predates both -- acceptable for WebID |
| WebID-TLS client certs | WebID + IndieAuth | ~2019 | Client certs are dead in browsers; IndieAuth is Phase 49 |

**Deprecated/outdated:**
- WebID-TLS: Browsers removed client certificate support; do not implement
- `cert:RSAPublicKey`: Old WebID 1.0 approach with RSA; use Ed25519 instead
- `publicKeyBase58`: Deprecated in favor of `publicKeyMultibase`, but user chose PEM which is different from both

## Open Questions

1. **app_base_url fallback behavior**
   - What we know: `app_base_url` defaults to empty string; the setting says "derive from request headers"
   - What's unclear: Whether there's existing utility code for this derivation
   - Recommendation: In the profile endpoint, if `settings.app_base_url` is empty, construct from `request.base_url`. For the settings UI, show a warning that WebID URIs require a stable `app_base_url`.

2. **W3C Security Vocabulary namespace stability**
   - What we know: User locked `sec:publicKeyPem` + `sec:Ed25519VerificationKey2020`. The current W3C spec at `https://w3id.org/security#` prefers `publicKeyMultibase`.
   - What's unclear: Whether consumers will understand PEM-encoded keys in this vocabulary
   - Recommendation: Follow user decision. PEM is widely understood. The Phase 49 IndieAuth implementation can use the private key regardless of how the public key is published.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (e2e) -- no backend unit test framework configured |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -g "webid"` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WBID-01 | WebID URI exists per user | e2e | `npx playwright test --project=chromium 15-webid` | No -- Wave 0 |
| WBID-02 | Profile returns RDF | e2e + manual curl | `npx playwright test --project=chromium 15-webid` | No -- Wave 0 |
| WBID-03 | Content negotiation (Turtle/JSON-LD/HTML) | e2e + manual curl | `npx playwright test --project=chromium 15-webid` | No -- Wave 0 |
| WBID-04 | HTML contains rel="me" links | e2e | `npx playwright test --project=chromium 15-webid` | No -- Wave 0 |
| WBID-05 | Ed25519 key pair generated + stored encrypted | e2e (setup flow) | `npx playwright test --project=chromium 15-webid` | No -- Wave 0 |
| WBID-06 | Public key in profile document | e2e + manual curl | `npx playwright test --project=chromium 15-webid` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Manual curl verification of content negotiation
- **Per wave merge:** Full e2e suite
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `e2e/tests/15-webid/webid-profiles.spec.ts` -- covers WBID-01 through WBID-06
- [ ] Content negotiation requires API-level testing (curl/httpx), not just browser testing

## Sources

### Primary (HIGH confidence)
- `backend/app/services/llm.py` -- Fernet encryption pattern (codebase)
- `backend/app/auth/models.py` -- User model structure (codebase)
- `backend/app/rdf/namespaces.py` -- FOAF namespace already defined (codebase)
- `backend/app/rdf/jsonld.py` -- JSON-LD serialization pattern (codebase)
- [cryptography Ed25519 docs](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/) -- key generation API
- [WebID 1.0 Spec](https://w3c.github.io/WebID/spec/identity/index.html) -- profile document structure
- [FOAF Vocabulary](https://xmlns.com/foaf/spec/) -- PersonalProfileDocument, primaryTopic, Person

### Secondary (MEDIUM confidence)
- [W3C Security Vocabulary](https://w3c-ccg.github.io/security-vocab/) -- Ed25519VerificationKey2020, publicKeyPem properties
- [Mastodon verification docs](https://docs.joinmastodon.org/user/profile/) -- rel="me" bidirectional linking
- [Solid WebID Profiles](https://solid.github.io/webid-profile/) -- modern WebID profile patterns

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, APIs verified
- Architecture: HIGH -- follows established domain module pattern in codebase
- Pitfalls: HIGH -- based on protocol specifications and codebase analysis
- Cryptography: HIGH -- `cryptography` library Ed25519 API is stable and well-documented

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain, specs don't change frequently)
