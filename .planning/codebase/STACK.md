# Technology Stack

**Analysis Date:** 2026-02-25

## Languages

**Primary:**
- Python 3.12 - Backend API (`backend/app/`)
- HTML/Jinja2 - Server-rendered templates (`backend/app/templates/`)
- Vanilla JavaScript (ES5/ES6) - Frontend interactivity (`frontend/static/js/`)
- CSS - Styling (`frontend/static/css/`)

**Secondary:**
- SPARQL - All triplestore queries and updates (`backend/app/sparql/`, `backend/app/services/`)
- Turtle (RDF) - Repository config, model ontologies, seed data (`config/`, `models/`)
- JSON-LD - Ontology, shapes, seed, and view spec format (`models/basic-pkm/`)
- YAML - Model manifests and view specs (`models/basic-pkm/manifest.yaml`)
- TypeScript - E2E test configuration (`e2e/`)

## Runtime

**Environment:**
- Python 3.12 (Docker container: `python:3.12-slim`)
- Node.js — used only in E2E test environment (`e2e/`)

**Package Manager:**
- Python: `pip` via `pyproject.toml` (no lockfile committed for dev; `uv.lock` present for uv users)
- Node: npm (lockfile not present in root; `e2e/package.json` managed separately)

## Frameworks

**Core Backend:**
- FastAPI (latest `standard` extra) - ASGI web framework (`backend/app/main.py`)
  - Uvicorn ASGI server (`CMD uvicorn app.main:app`)
  - Pydantic Settings for configuration (`backend/app/config.py`)
  - Jinja2 + jinja2-fragments for server-side template rendering with htmx partial support (`backend/app/main.py`)

**Frontend (CDN-loaded, no build step):**
- htmx 2.0.4 — Drives all AJAX/partial updates via HTML attributes (loaded from unpkg CDN)
- Cytoscape.js 3.33.1 — Graph visualization (`frontend/static/js/graph.js`)
  - cytoscape-fcose 2.2.0 — Force-directed layout
  - cytoscape-dagre 2.5.0 — Hierarchical layout
  - dagre 0.8.5 — Layout algorithm dependency
- Split.js 1.6.5 — Resizable panel layouts
- ninja-keys 1.2.2 — Command palette (`<ninja-keys>` web component)
- marked + marked-highlight — Markdown rendering (`frontend/static/js/markdown-render.js`)
- highlight.js 11.11.1 — Code block syntax highlighting
- DOMPurify — XSS sanitization for rendered Markdown
- Lucide 0.575.0 — SVG icon library
- Driver.js 1.4.0 — Guided tour overlays (`frontend/static/js/tutorials.js`)
- PostHog JS SDK — Analytics/error monitoring (dynamically loaded, `frontend/static/js/posthog.js`)

**Testing:**
- Playwright 1.50.0 — E2E browser testing (`e2e/`)
  - TypeScript 5.7.0 for test configuration (`e2e/playwright.config.ts`)
  - `@types/node` 25.3.0
- pytest + pytest-asyncio — Backend unit/integration tests (`backend/pyproject.toml` dev deps)
  - httpx used as test async client

**Build/Dev:**
- Docker Compose — Full-stack local development (`docker-compose.yml`, `docker-compose.test.yml`)
- nginx:stable-alpine — Frontend static file serving and reverse proxy (`frontend/Dockerfile`, `frontend/nginx.conf`)

## Key Dependencies

**Critical:**
- `rdflib>=7.5.0` — RDF graph manipulation, serialization/parsing, namespace management (`backend/app/rdf/`)
- `pyshacl>=0.31.0` — SHACL shapes validation (`backend/app/services/validation.py`)
- `httpx>=0.28` — Async HTTP client for triplestore communication and webhook dispatch (`backend/app/triplestore/client.py`)
- `sqlalchemy[asyncio]>=2.0.46` — Async ORM for SQL auth database (`backend/app/db/`)
- `aiosqlite>=0.22` — SQLite async driver (development/local)
- `asyncpg>=0.31` — PostgreSQL async driver (cloud/production)
- `alembic>=1.18` — SQL database migrations (`backend/migrations/`)

**Auth/Security:**
- `itsdangerous>=2.2` — Signed tokens for magic links and invitations (`backend/app/auth/tokens.py`)
- `cryptography>=43.0` — Cryptographic operations support

**Infrastructure:**
- `jinja2-fragments` — Block-level template rendering for htmx partial updates
- `pyyaml>=6.0` — YAML manifest parsing for model bundles
- `cachetools>=7.0` — In-memory caching
- `posthog>=3.7` — Analytics and error tracking SDK (`backend/app/monitoring/posthog.py`)
- `pydantic-settings` — Environment-variable-backed configuration

## Configuration

**Environment Variables (via `.env` and Docker Compose):**
- `TRIPLESTORE_URL` — RDF4J server URL (default: `http://triplestore:8080/rdf4j-server`)
- `REPOSITORY_ID` — RDF4J repository name (default: `sempkm`)
- `BASE_NAMESPACE` — IRI namespace for user data (default: `https://example.org/data/`)
- `DATABASE_URL` — SQLAlchemy URL; SQLite for local, PostgreSQL+asyncpg for cloud
- `SECRET_KEY` — HMAC key for signed tokens; auto-generated to `./data/.secret-key` if absent
- `SESSION_DURATION_DAYS` — Session expiry (default: 30)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` — Optional SMTP for email delivery
- `POSTHOG_ENABLED`, `POSTHOG_API_KEY`, `POSTHOG_HOST` — Optional analytics

**Configuration file:** `backend/app/config.py` — `Settings` class using `pydantic-settings` with `SettingsConfigDict(env_file=".env")`

**Build:**
- `backend/pyproject.toml` — Python project metadata and dependencies
- `backend/Dockerfile` — `python:3.12-slim`, installs via `pip install .`, runs uvicorn with hot-reload
- `frontend/nginx.conf` — nginx reverse proxy config (static files + API proxy)
- `docker-compose.yml` — Orchestrates triplestore, api, frontend services

## Platform Requirements

**Development:**
- Docker and Docker Compose
- Port 3000: frontend (nginx)
- Port 8001: API (FastAPI/uvicorn, mapped to 8000 inside container)
- No build step for frontend; all JS/CSS served as static files

**Production:**
- Deployment target: self-hosted Docker Compose (same configuration)
- Cloud deployment can substitute PostgreSQL via `DATABASE_URL`
- PostHog monitoring enabled via environment flags
- Frontend nginx serves static assets; proxies all other routes to FastAPI

---

*Stack analysis: 2026-02-25*
