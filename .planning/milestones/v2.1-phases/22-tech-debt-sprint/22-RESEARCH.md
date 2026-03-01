# Phase 22: Tech Debt Sprint - Research

**Researched:** 2026-02-28
**Domain:** Python backend infrastructure (SQLAlchemy migrations, SMTP email, session lifecycle, SPARQL caching)
**Confidence:** HIGH

## Summary

Phase 22 addresses four independent medium-priority tech debt items in the SemPKM backend. All four are well-scoped changes touching existing, well-understood code paths. The codebase already has strong foundations for each: Alembic is already a dependency with `alembic.ini`, `env.py`, and two migration files in place; SMTP settings are already defined in `config.py` with a clear TODO stub in `auth/router.py`; session expiry filtering is already implemented in `auth/dependencies.py`; and `cachetools.TTLCache` is already used by `LabelService` with the exact same pattern needed for `ViewSpecService`.

The four items share no code dependencies and can be implemented in any order or in parallel. Each item is a 1-2 file change with well-defined success criteria. The primary risk is the Alembic startup runner pitfall (logging configuration causing process hangs), which has a documented one-line fix.

**Primary recommendation:** Implement all four items as independent tasks, each touching at most 2-3 files. Use the existing `LabelService` TTLCache pattern as the template for `ViewSpecService` caching. Use `aiosmtplib` for async SMTP delivery. Replace `create_all` with `alembic command.upgrade` in the lifespan function. Add a `cleanup_expired_sessions` method to `AuthService` and call it during startup.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TECH-01 | Alembic migration runner at startup -- replaces `create_all`, proper schema migration support for both SQLite and PostgreSQL | Alembic is already installed and configured; `env.py` uses async engine; `command.upgrade(Config("alembic.ini"), "head")` replaces `Base.metadata.create_all` in lifespan; `fileConfig` pitfall documented |
| TECH-02 | SMTP email delivery -- magic links sent via real email (configurable SMTP settings), not logged to console | `aiosmtplib` provides async SMTP; auth/router.py has a clear TODO stub at line 132; SMTP settings already in config.py; `email.message.EmailMessage` from stdlib for message construction |
| TECH-03 | Session cleanup job -- expired sessions purged on startup or via scheduled task | `AuthService` already has `revoke_session`/`revoke_all_sessions` patterns; add `DELETE FROM sessions WHERE expires_at < now()` method; call from lifespan after engine init |
| TECH-04 | ViewSpecService TTL cache -- reduce SPARQL queries per view spec lookup (currently 2 queries per lookup) | `cachetools.TTLCache` already a dependency and used by `LabelService`; same pattern applies to `ViewSpecService.get_all_view_specs()` results |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| alembic | >=1.18 (already in pyproject.toml) | Schema migration runner | Only mature SQLAlchemy migration tool; already configured in project |
| aiosmtplib | 5.1.0 | Async SMTP client | Standard async SMTP lib for Python; clean asyncio integration |
| cachetools | >=7.0 (already in pyproject.toml) | TTL-based in-memory cache | Already used by LabelService; lightweight, proven |
| sqlalchemy[asyncio] | >=2.0.46 (already in pyproject.toml) | Async ORM for session cleanup query | Already in use throughout auth layer |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| email.message (stdlib) | Python 3.12+ | Email message construction | Always -- no external dependency needed for message building |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiosmtplib | smtplib (sync stdlib) | Would block event loop; aiosmtplib is async-native |
| aiosmtplib | fastapi-mail | Heavy dependency with Jinja2 template engine; overkill for single-template magic links |
| cachetools TTLCache | functools.lru_cache | No TTL support; stale data persists until eviction |
| Startup cleanup | APScheduler / BackgroundTasks | Overengineered for a once-per-startup purge |

**Installation:**
```bash
pip install aiosmtplib
```
Only `aiosmtplib` is new. All other libraries are already dependencies.

## Architecture Patterns

### Recommended File Changes
```
backend/
├── app/
│   ├── main.py              # TECH-01: Replace create_all with alembic upgrade
│   │                        # TECH-03: Add session cleanup call in lifespan
│   ├── auth/
│   │   ├── service.py       # TECH-03: Add cleanup_expired_sessions method
│   │   └── router.py        # TECH-02: Replace TODO with send_magic_link_email call
│   ├── services/
│   │   └── email.py         # TECH-02: NEW file -- EmailService with async SMTP
│   └── views/
│       └── service.py       # TECH-04: Add TTLCache to ViewSpecService
├── migrations/
│   └── env.py               # TECH-01: Add disable_existing_loggers=False
└── pyproject.toml            # TECH-02: Add aiosmtplib dependency
```

### Pattern 1: Programmatic Alembic Upgrade at Startup (TECH-01)
**What:** Replace `Base.metadata.create_all` in lifespan with `alembic.command.upgrade`
**When to use:** Application startup, before any database access
**Example:**
```python
# Source: https://github.com/sqlalchemy/alembic/issues/1606
# In main.py lifespan(), replace the create_all block:

import asyncio
from alembic import command
from alembic.config import Config

# --- SQL Database Initialization ---
# Run Alembic migrations instead of create_all
alembic_cfg = Config("alembic.ini")
await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
logger.info("SQL database migrations applied")
```

**Key detail:** `asyncio.to_thread()` is required because `command.upgrade()` internally uses `asyncio.run()` in `env.py`, and you cannot nest `asyncio.run()` inside a running event loop. `asyncio.to_thread()` runs the blocking call in a separate thread where a fresh event loop can be created.

### Pattern 2: Async Email Service (TECH-02)
**What:** Encapsulate SMTP delivery in a service module with fallback to console logging
**When to use:** Magic link and invitation email delivery
**Example:**
```python
# Source: https://aiosmtplib.readthedocs.io/en/latest/usage.html
# New file: backend/app/services/email.py

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


async def send_magic_link_email(email: str, token: str, base_url: str) -> bool:
    """Send a magic link login email via SMTP.

    Returns True if sent successfully, False on error (logged, not raised).
    """
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message["Subject"] = "SemPKM Login Link"

    verify_url = f"{base_url}/login.html?token={token}"
    message.set_content(
        f"Click the link below to log in to SemPKM:\n\n{verify_url}\n\n"
        "This link expires in 10 minutes."
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )
        logger.info("Magic link email sent to %s", email)
        return True
    except aiosmtplib.SMTPException:
        logger.error("Failed to send magic link email to %s", email, exc_info=True)
        return False
```

### Pattern 3: Session Cleanup at Startup (TECH-03)
**What:** Delete expired sessions from the database during application startup
**When to use:** Once during lifespan startup, after database is initialized
**Example:**
```python
# In auth/service.py -- add method to AuthService:

async def cleanup_expired_sessions(self) -> int:
    """Delete all expired sessions. Returns count deleted."""
    now = _utcnow()
    async with self._session_factory() as session:
        result = await session.execute(
            delete(UserSession).where(UserSession.expires_at <= now)
        )
        await session.commit()
        return result.rowcount
```

### Pattern 4: TTLCache for ViewSpecService (TECH-04)
**What:** Cache `get_all_view_specs()` results using TTLCache, same pattern as LabelService
**When to use:** All view spec lookups (get_all, get_by_type, get_by_iri) go through cached get_all
**Example:**
```python
# Source: Existing LabelService pattern in backend/app/services/labels.py
# In views/service.py -- add to ViewSpecService.__init__:

from cachetools import TTLCache

class ViewSpecService:
    def __init__(self, client, label_service, ttl=300, maxsize=64):
        self._client = client
        self._label_service = label_service
        self._specs_cache: TTLCache[str, list[ViewSpec]] = TTLCache(
            maxsize=maxsize, ttl=ttl
        )

    async def get_all_view_specs(self) -> list[ViewSpec]:
        cache_key = "all_specs"
        if cache_key in self._specs_cache:
            logger.debug("ViewSpec cache hit")
            return self._specs_cache[cache_key]

        # ... existing SPARQL query logic ...
        specs = [...]  # result of current logic

        self._specs_cache[cache_key] = specs
        logger.info("ViewSpec cache miss -- loaded %d specs, cached for %ds",
                     len(specs), self._specs_cache.ttl)
        return specs

    def invalidate_cache(self) -> None:
        """Clear cached view specs after model install/uninstall."""
        self._specs_cache.clear()
```

### Anti-Patterns to Avoid
- **Running `create_all` alongside Alembic:** Once Alembic manages migrations, remove `Base.metadata.create_all` entirely. Running both causes confusion about which is the source of truth for the schema.
- **Sending email synchronously:** Never use `smtplib` in an async FastAPI handler -- it blocks the event loop. Use `aiosmtplib`.
- **Scheduled session cleanup with APScheduler:** Overkill for this use case. Expired sessions are already filtered out at query time by `auth/dependencies.py`. Startup cleanup is sufficient to prevent unbounded table growth.
- **Per-request ViewSpec caching:** Don't cache at the HTTP layer (e.g., `Cache-Control` headers). The cache belongs in the service layer because multiple endpoints call the same `get_all_view_specs()` method.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema migrations | Custom DDL scripts or create_all | Alembic `command.upgrade` | Handles migration ordering, rollback, autogenerate; project already has it configured |
| Async SMTP | Raw socket/ssl code | aiosmtplib | STARTTLS negotiation, auth, error handling, timeouts are deceptively complex |
| TTL cache | dict + timestamps | cachetools.TTLCache | Thread-safe, handles expiry, eviction; already a dependency |
| Email message construction | String concatenation | email.message.EmailMessage (stdlib) | Handles MIME encoding, headers, multipart correctly |

**Key insight:** All four items have well-proven, minimal-dependency solutions. The project already uses 3 of the 4 required libraries.

## Common Pitfalls

### Pitfall 1: Alembic fileConfig Disabling Application Loggers
**What goes wrong:** After `command.upgrade()` runs, all application loggers stop working (appear to hang)
**Why it happens:** `fileConfig()` in `env.py` defaults `disable_existing_loggers=True`, which kills all loggers created before migration runs
**How to avoid:** Add `disable_existing_loggers=False` to the `fileConfig()` call in `migrations/env.py`:
```python
fileConfig(config.config_file_name, disable_existing_loggers=False)
```
**Warning signs:** Application appears to hang after "SQL database migrations applied" log message; no further log output
**Source:** [alembic/alembic#1483](https://github.com/sqlalchemy/alembic/discussions/1483)

### Pitfall 2: Nested asyncio.run() in Alembic env.py
**What goes wrong:** `RuntimeError: This event loop is already running` when calling `command.upgrade()` from FastAPI lifespan
**Why it happens:** `env.py` uses `asyncio.run()` internally, which cannot be nested inside an already-running event loop
**How to avoid:** Use `asyncio.to_thread(command.upgrade, cfg, "head")` to run in a separate thread where `asyncio.run()` can create a fresh loop
**Warning signs:** RuntimeError immediately on startup
**Source:** [alembic/alembic#1606](https://github.com/sqlalchemy/alembic/issues/1606)

### Pitfall 3: SMTP Credentials in Source Control
**What goes wrong:** SMTP password committed to docker-compose.yml or .env
**Why it happens:** Developer adds credentials for testing and forgets to remove them
**How to avoid:** SMTP settings are already in docker-compose.yml as commented-out env vars. Keep them commented; real deployments use `.env` file (which is in `.gitignore`)
**Warning signs:** `SMTP_PASSWORD` value visible in git history

### Pitfall 4: SQLite Batch Mode for ALTER TABLE
**What goes wrong:** `ALTER TABLE` fails on SQLite when adding columns or constraints
**Why it happens:** SQLite has limited ALTER TABLE support
**How to avoid:** Already handled -- `env.py` uses `render_as_batch=True` in both offline and online modes. This makes Alembic recreate tables instead of using ALTER TABLE.
**Warning signs:** Migration failure with SQLite-specific error about unsupported ALTER TABLE operation

### Pitfall 5: ViewSpec Cache Invalidation on Model Install/Uninstall
**What goes wrong:** After installing a new Mental Model, old cached view specs are served for up to TTL seconds
**Why it happens:** Cache doesn't know about model changes
**How to avoid:** Add an `invalidate_cache()` method to ViewSpecService and call it from the model install/uninstall endpoints. The TTL (300s = 5 min) also provides natural expiry.
**Warning signs:** Newly installed model's views don't appear for several minutes

### Pitfall 6: Magic Link URL Construction
**What goes wrong:** Magic link URL points to wrong host/port when behind nginx reverse proxy
**Why it happens:** `request.url` may reflect the internal container URL, not the public-facing URL
**How to avoid:** Use `request.base_url` or construct from a configurable `APP_BASE_URL` setting. In Docker, the frontend nginx is the public entry point at port 3000, while the API is internal at port 8000.
**Warning signs:** Magic link in email points to `http://api:8000/...` instead of `http://localhost:3000/...`

## Code Examples

### TECH-01: Lifespan Migration Runner
```python
# backend/app/main.py -- replace create_all block (lines 132-139)
# Source: alembic docs + GitHub issues #1606, #1483

import asyncio
from alembic import command
from alembic.config import Config

# In lifespan(), replace:
#   sql_engine = create_engine()
#   async with sql_engine.begin() as conn:
#       await conn.run_sync(Base.metadata.create_all)
#   logger.info("SQL database tables created/verified")
# With:
sql_engine = create_engine()
alembic_cfg = Config("alembic.ini")
await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
logger.info("SQL database migrations applied")
```

### TECH-02: Email Service Integration Point
```python
# backend/app/auth/router.py -- replace TODO at line 131-135
# After creating the token:

if smtp_configured:
    from app.services.email import send_magic_link_email
    base_url = str(request.base_url).rstrip("/")
    await send_magic_link_email(body.email, token, base_url)
    return MagicLinkResponse(
        message="If this email is registered, a login link has been sent."
    )
```

### TECH-03: Session Cleanup in Lifespan
```python
# backend/app/main.py -- add after AuthService creation (after line 145)

# Purge expired sessions on startup
purged = await auth_service.cleanup_expired_sessions()
if purged:
    logger.info("Purged %d expired sessions", purged)
```

### TECH-04: ViewSpecService with Cache
```python
# backend/app/views/service.py -- add to __init__ and modify get_all_view_specs
# Source: existing LabelService pattern (backend/app/services/labels.py)

from cachetools import TTLCache

# In __init__:
self._specs_cache: TTLCache[str, list[ViewSpec]] = TTLCache(maxsize=64, ttl=300)

# In get_all_view_specs, at top:
cache_key = "all_specs"
if cache_key in self._specs_cache:
    return self._specs_cache[cache_key]

# At end, before return:
self._specs_cache[cache_key] = specs
return specs
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Base.metadata.create_all()` | `alembic command.upgrade(cfg, "head")` | Alembic standard since SQLAlchemy 1.x | Enables schema evolution without DB drops |
| `smtplib` (sync) | `aiosmtplib` (async) | aiosmtplib 1.0 (2019), v5.1.0 current | Non-blocking email delivery in async apps |
| Manual cache dict + timestamps | `cachetools.TTLCache` | cachetools 1.0 (2014), v7.0 current | Thread-safe, per-item TTL, LRU eviction |

**Deprecated/outdated:**
- `@app.on_event("startup")`: Replaced by `lifespan` context manager in FastAPI 0.93+. This project already uses `lifespan`.
- `smtplib.SMTP_SSL` for async apps: Blocks the event loop. Use `aiosmtplib` instead.

## Open Questions

1. **Magic link email base URL**
   - What we know: The frontend runs at `localhost:3000` (nginx), the API at `localhost:8000` (uvicorn). `request.base_url` in the API context returns the internal URL.
   - What's unclear: Whether a configurable `APP_BASE_URL` setting is needed or if `request.headers.get("X-Forwarded-Host")` from nginx is sufficient.
   - Recommendation: Add an `app_base_url` setting to `config.py` with a sensible default (empty = derive from request). This is simpler and more reliable than parsing forwarded headers. The nginx config can be updated later to forward proper headers if needed.

2. **ViewSpec cache invalidation trigger**
   - What we know: Model install/uninstall goes through `ModelService` methods. `ViewSpecService` doesn't currently have a reference to `ModelService` or vice versa.
   - What's unclear: The cleanest way to wire invalidation. Options: (a) call `view_spec_service.invalidate_cache()` from model install endpoint, (b) event-based coupling, (c) rely on TTL alone.
   - Recommendation: Option (a) -- direct call from the model install/uninstall router handlers, since they already have access to `app.state.view_spec_service`. TTL provides the safety net.

3. **Alembic working directory in Docker**
   - What we know: The Dockerfile's WORKDIR is `/app`. The `alembic.ini` sets `script_location = migrations`. Docker-compose mounts `./backend/app:/app/app` but not `./backend/migrations`.
   - What's unclear: Whether `alembic.ini` and `migrations/` are included in the Docker image via `COPY` (yes -- `COPY pyproject.toml .` and `COPY app/ app/` don't include them).
   - Recommendation: Add `COPY alembic.ini .` and `COPY migrations/ migrations/` to the Dockerfile. Without this, programmatic migration won't find the migration scripts in the container.

## Sources

### Primary (HIGH confidence)
- `backend/app/main.py` lines 132-139 -- current `create_all` block to be replaced
- `backend/app/auth/router.py` lines 131-135 -- current SMTP TODO stub
- `backend/app/services/labels.py` lines 28-37 -- existing TTLCache pattern
- `backend/app/views/service.py` -- ViewSpecService without caching
- `backend/migrations/env.py` -- existing async Alembic env configuration
- `backend/migrations/versions/` -- two existing migration files (001, 002)
- `backend/alembic.ini` -- existing Alembic configuration
- `backend/app/config.py` -- SMTP settings already defined
- [aiosmtplib 5.1.0 docs](https://aiosmtplib.readthedocs.io/en/latest/usage.html) -- async SMTP usage patterns
- [aiosmtplib API reference](https://aiosmtplib.readthedocs.io/en/latest/reference.html) -- exception hierarchy

### Secondary (MEDIUM confidence)
- [Alembic issue #1606](https://github.com/sqlalchemy/alembic/issues/1606) -- async startup migration pattern with `asyncio.to_thread`
- [Alembic discussion #1483](https://github.com/sqlalchemy/alembic/discussions/1483) -- `fileConfig` logger disabling pitfall and fix
- [cachetools 7.0 docs](https://cachetools.readthedocs.io/) -- TTLCache API reference

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are either already in the project or well-established (aiosmtplib 5.1.0)
- Architecture: HIGH -- all four patterns follow existing codebase conventions; LabelService provides exact template for TECH-04
- Pitfalls: HIGH -- Alembic pitfalls verified via official GitHub issues; others derived from direct codebase inspection

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable domain, no fast-moving dependencies)
