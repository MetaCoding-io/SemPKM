# External Integrations

**Analysis Date:** 2026-02-25

## APIs & External Services

**Graph Database / Triplestore:**
- Eclipse RDF4J 5.0.1 — Core knowledge graph storage
  - Docker image: `eclipse/rdf4j-workbench:5.0.1`
  - Protocol: RDF4J REST API (SPARQL over HTTP)
  - Client: `backend/app/triplestore/client.py` (`TriplestoreClient` class using `httpx.AsyncClient`)
  - Auth: None (internal Docker network only)
  - Connection: `TRIPLESTORE_URL` env var (default `http://triplestore:8080/rdf4j-server`)
  - Repository config: `config/rdf4j/sempkm-repo.ttl` (NativeStore with spoc/posc/cspo indexes)
  - Operations: SPARQL SELECT/ASK/CONSTRUCT/UPDATE, transactional updates, repository provisioning

**Analytics & Error Monitoring:**
- PostHog — Analytics, error capture, session replay
  - Backend SDK: `posthog>=3.7` Python package
  - Frontend SDK: PostHog JS snippet (dynamically loaded via `frontend/static/js/posthog.js`)
  - Backend integration: `backend/app/monitoring/posthog.py`, `backend/app/monitoring/middleware.py`
  - Auth: `POSTHOG_API_KEY` env var
  - Host: `POSTHOG_HOST` env var (default `https://us.i.posthog.com`)
  - Toggle: `POSTHOG_ENABLED=true` env var (off by default for self-hosted)
  - Captures: unhandled exceptions via `PostHogErrorMiddleware`, backend events, frontend autocapture + session replay

**CDN-Loaded Frontend Libraries (external at runtime):**
- `unpkg.com` — htmx 2.0.4, cytoscape + layout plugins, split.js, ninja-keys, lucide
- `cdn.jsdelivr.net` — marked, marked-highlight, DOMPurify, driver.js
- `cdnjs.cloudflare.com` — highlight.js + theme CSS
- All loaded in `backend/app/templates/base.html` via `<script src="...">` tags
- No npm build step; CDN resources fetched by browser at page load

## Data Storage

**Databases:**

RDF Triplestore:
- Eclipse RDF4J NativeStore (runs as separate Docker service)
- Named graphs: `urn:sempkm:current` (materialized state), `urn:sempkm:events` (event log), `urn:sempkm:webhooks` (webhook configs), model-specific graphs
- Connection: `TRIPLESTORE_URL` env var
- Client: `backend/app/triplestore/client.py`

SQL Database (auth + metadata):
- SQLite (development): `sqlite+aiosqlite:///./data/sempkm.db` — file at `/app/data/sempkm.db` inside container
- PostgreSQL (cloud): `postgresql+asyncpg://...` — configured via `DATABASE_URL` env var
- ORM: SQLAlchemy 2.0 async (`backend/app/db/`)
- Migrations: Alembic (`backend/migrations/`, `backend/alembic.ini`)
- Tables: `users`, `sessions`, `invitations`, `instance_config` (see `backend/migrations/versions/001_initial_auth_tables.py`)

**File Storage:**
- Local filesystem only
- `/app/data/` volume: SQLite database, secret key file (`data/.secret-key`), setup token file (`data/.setup-token`)
- `/app/models/` volume (read-only): model bundle YAML/JSON-LD files
- `/app/config/` volume (read-only): RDF4J repository config
- `/app/docs/` volume (read-only): user guide Markdown files served as static

**Caching:**
- In-memory only via `cachetools>=7.0`
- No external cache (no Redis/Memcached)

## Authentication & Identity

**Auth Provider:**
- Custom (no OAuth/SAML/external IdP)
- Implementation: `backend/app/auth/` module
  - `service.py` — AuthService with session lifecycle, invitation flow
  - `tokens.py` — Token generation/verification via `itsdangerous.URLSafeTimedSerializer`
  - `router.py` — Auth endpoints at `/api/auth/`
  - `models.py` — SQLAlchemy User, UserSession, Invitation models
  - `dependencies.py` — FastAPI dependency injection for `get_current_user`, `require_role`

**Auth Flow:**
1. Magic link: `POST /api/auth/magic-link` → generates signed token → sent via SMTP or returned directly
2. Verify: `POST /api/auth/verify` → validates token → creates session → sets `sempkm_session` httpOnly cookie
3. Session: sliding-window expiry (30 days default), extended past 50% of lifetime
4. Cookie: `sempkm_session`, `httponly=True`, `samesite="lax"`, `secure=False` (TODO: configurable for prod)

**Roles:**
- `owner` — First user, created via one-time setup token flow (`POST /api/auth/setup`)
- `member` — Standard user, created via invitation or magic link
- `guest` — Limited access role (invitation-only)

## Email (SMTP)

**Provider:** Any SMTP server (configurable)
- Config: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` env vars
- Used for: Magic link emails, user invitations
- Fallback: When SMTP not configured, tokens returned directly in API response (browser-console delivery for local instances)
- Implementation: `backend/app/auth/router.py` — SMTP sending is a TODO stub; token generation is complete

## Monitoring & Observability

**Error Tracking:**
- PostHog (when `POSTHOG_ENABLED=true`)
  - Backend: `PostHogErrorMiddleware` wraps all requests, captures unhandled exceptions with traceback
  - Frontend: `posthog.js` captures JS errors, unhandled promise rejections, autocapture events

**Logs:**
- Python standard `logging` module, `basicConfig(level=INFO)`
- All significant lifecycle events logged: startup, triplestore connection, auth operations, webhook dispatch
- No structured logging / no external log aggregation

## CI/CD & Deployment

**Hosting:**
- Self-hosted Docker Compose (development and production)
- No cloud-native platform detected

**CI Pipeline:**
- None detected (no `.github/workflows/`, no CI config files)
- E2E tests run manually via Playwright from `e2e/` directory

## Webhooks & Callbacks

**Outgoing (internal webhook dispatch system):**
- Managed by `backend/app/services/webhooks.py` (`WebhookService`)
- Webhook configs stored as RDF triples in named graph `urn:sempkm:webhooks`
- Fire-and-forget HTTP POST to registered target URLs on matching events
- Events dispatched: `validation.completed`, `object.changed`, `edge.changed` (and others per config)
- Admin UI for webhook management: `backend/app/templates/admin/webhooks.html`
- API CRUD: `backend/app/admin/router.py`

**Incoming:**
- None (no incoming webhook endpoints)

## RDF Vocabularies / Ontologies Used

The application imports and uses these standard namespaces (defined in `backend/app/rdf/namespaces.py`):
- `rdf`, `rdfs`, `owl`, `xsd` — Core RDF/OWL
- `sh` — SHACL (shapes validation)
- `dcterms` — Dublin Core (note/project titles)
- `skos` — SKOS (concept labels)
- `foaf` — FOAF (person names)
- `schema` — Schema.org
- `prov` — PROV-O (provenance)
- `sempkm` — Internal SemPKM vocabulary (`urn:sempkm:`)

---

*Integration audit: 2026-02-25*
