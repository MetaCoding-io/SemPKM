# Phase 6: User and Team Management for Multi-Tenant Cloud Readiness - Research

**Researched:** 2026-02-22
**Domain:** Authentication, authorization, SQL data layer, event provenance, multi-tenant architecture
**Confidence:** MEDIUM-HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **One instance = one project = one triplestore** -- no multi-project abstraction within an instance
- No "project" entity -- the instance itself is the unit of organization
- All users in an instance share the same knowledge data (no object-level privacy)
- Cloud service orchestrates many isolated instances, each with its own RDF4J repository
- Cloud uses shared API tier routing to per-customer RDF4J stores (not fully isolated containers)
- One shared PostgreSQL for all cloud user accounts, instance metadata, and membership
- **Passwordless only** -- no passwords stored in SQL database (security by design if DB is leaked)
- **Local first-run**: Setup wizard in browser, one-time setup token shown in terminal. Owner enters token to claim the instance. Long-lived session after that. No SMTP needed for initial setup.
- **SMTP setup deferred**: Only required when owner wants to invite other users. Not part of initial install.
- **Cloud**: Magic link emails from day one (cloud service handles email delivery)
- **User-first onboarding** (cloud): User signs up with email first, then creates an instance
- **Sessions**: Configurable duration, default 30 days
- **API access**: Session-based only -- no separate API tokens/keys
- **DNS verification** required for custom domains (both local self-hosted and cloud)
- **Owner** (exactly one per instance): Full control -- manage users, install/remove Mental Models, configure instance, billing, transfer ownership
- **Member**: Read/write knowledge data (create, edit, query objects). Soft-delete only (archive). Cannot install/remove models or manage users.
- **Guest**: Read-only access to all data and instance info. Can run SPARQL SELECT queries. Cannot create, edit, or delete anything.
- One user identity across many instances (like GitHub orgs)
- Users added via email invitation (owner sends invite)
- **Writes always go through command API** -- role enforcement happens here
- **SPARQL endpoint**: Authenticated access only. All roles (including guest) can query. No write access via SPARQL.
- **RDF4J port not exposed** to host in Docker -- only backend container talks to triplestore
- Members can soft-delete (archive) objects; only owner can permanently delete or restore
- Mental Model management (install/remove) is owner-only
- **Events track user identity** -- each event records which user performed the action
- Objects show "created by" and "last modified by"
- This requires retroactively enriching the event model from Phase 1
- **SQLite for local installs, PostgreSQL for cloud** -- identical schema, same ORM/data layer, two connection strings
- Database holds: user accounts, sessions, instance config, membership/roles, invitation state
- No knowledge data in SQL -- that stays in the triplestore
- **Rework required**: Event store (add user provenance), Command API (add auth middleware), SPARQL endpoint (add authentication)

### Claude's Discretion
- ORM/library choice for SQLite+PostgreSQL dual backend
- Session token implementation (JWT vs opaque tokens vs signed cookies)
- Magic link token expiration and security details
- Setup wizard UI design and flow
- Database migration tooling choice
- How to handle the owner's long-lived local session (refresh strategy)

### Deferred Ideas (OUT OF SCOPE)
- None -- discussion stayed within phase scope
</user_constraints>

## Summary

Phase 6 transforms SemPKM from a single-user, unauthenticated system into one that supports user identity, role-based access, and session management -- all without passwords. The core technical challenge is threefold: (1) adding a SQL data layer alongside the existing RDF triplestore for user/session data, (2) retrofitting authentication and authorization into the existing FastAPI API surface, and (3) enriching the event model with user provenance.

The recommended stack is SQLAlchemy 2.0 (async ORM) with Alembic (migrations using batch mode for SQLite compatibility), opaque session tokens stored in the SQL database, and `itsdangerous` for signing magic link and setup tokens. The existing FastAPI dependency injection system maps cleanly to auth -- a `get_current_user` dependency chains into `require_role("owner")` dependencies for protected routes. The PROV-O namespace already exists in the codebase (`prov:` prefix defined in `namespaces.py`) and can be used to add `sempkm:performedBy` predicates to events.

**Primary recommendation:** Use SQLAlchemy 2.0 async with `aiosqlite`/`asyncpg` drivers, Alembic with `render_as_batch=True`, opaque session tokens via `secrets.token_urlsafe()`, and FastAPI's `Depends()` for layered auth enforcement. Do not use JWT for sessions (opaque tokens give server-side revocation which matches the single-API-tier architecture).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | >=2.0.46 | Async ORM for user/session/role data | Industry standard Python ORM; async support since 2.0; supports both SQLite and PostgreSQL with same model definitions |
| Alembic | >=1.18.4 | Database schema migrations | Official SQLAlchemy migration tool; batch mode handles SQLite's ALTER limitations transparently |
| aiosqlite | >=0.22.1 | Async SQLite driver | Required by SQLAlchemy async for `sqlite+aiosqlite://` URLs |
| asyncpg | >=0.31.0 | Async PostgreSQL driver | Required by SQLAlchemy async for `postgresql+asyncpg://` URLs; highest-performance Python PG driver |
| itsdangerous | >=2.2 | Token signing for magic links and setup tokens | Pallets project (Flask ecosystem); time-limited signed tokens without database storage; already a transitive dependency of many Python web frameworks |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi-mail / aiosmtplib | >=1.4 / >=3.0 | Async email sending for magic links and invitations | When SMTP is configured (deferred -- not needed for local first-run) |
| python-multipart | (already in fastapi[standard]) | Form data parsing for setup wizard | Already included via FastAPI standard extras |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLAlchemy | SQLModel | SQLModel wraps SQLAlchemy+Pydantic but adds coupling between API models and DB models; for a small user schema, raw SQLAlchemy is simpler and more explicit |
| SQLAlchemy | Tortoise ORM | Django-inspired async ORM, but smaller ecosystem, less mature migration story, fewer SQLite edge-case solutions |
| Opaque tokens | JWT | JWT enables stateless verification but prevents server-side revocation; for a single-API-tier architecture where every request hits the same backend, opaque tokens with DB lookup are simpler and more secure (instant revocation, no refresh token complexity) |
| itsdangerous | PyJWT | PyJWT is heavier and designed for bearer auth; itsdangerous is purpose-built for short-lived signed URLs |

### Installation
```bash
pip install "sqlalchemy>=2.0.46" "alembic>=1.18" "aiosqlite>=0.22" "asyncpg>=0.31" "itsdangerous>=2.2"
```

Add to `backend/pyproject.toml` dependencies:
```toml
"sqlalchemy[asyncio]>=2.0.46",
"alembic>=1.18",
"aiosqlite>=0.22",
"asyncpg>=0.31",
"itsdangerous>=2.2",
```

Note: `asyncpg` is only needed for cloud deployment. For local-only installs, only `aiosqlite` is required. Both should be listed as dependencies for the single codebase.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── auth/                    # NEW: Authentication & authorization
│   ├── __init__.py
│   ├── models.py            # SQLAlchemy ORM models (User, Session, Invitation, InstanceConfig)
│   ├── schemas.py           # Pydantic request/response models
│   ├── service.py           # Auth business logic (create session, verify token, etc.)
│   ├── dependencies.py      # FastAPI Depends: get_current_user, require_role()
│   ├── router.py            # Auth endpoints (/auth/setup, /auth/magic-link, /auth/verify, /auth/logout)
│   └── tokens.py            # Token generation/verification (setup token, magic link, session)
├── db/                      # NEW: SQL database layer
│   ├── __init__.py
│   ├── engine.py            # create_async_engine factory (SQLite or PostgreSQL based on config)
│   ├── session.py           # AsyncSession factory and dependency
│   └── base.py              # DeclarativeBase for all ORM models
├── migrations/              # NEW: Alembic migration directory
│   ├── env.py               # Async Alembic env with render_as_batch=True
│   ├── script.py.mako
│   └── versions/
├── config.py                # MODIFIED: Add DATABASE_URL, SESSION_DURATION, SMTP settings
├── dependencies.py          # MODIFIED: Add get_db_session, get_current_user
├── events/
│   ├── models.py            # MODIFIED: Add EVENT_PERFORMED_BY predicate
│   └── store.py             # MODIFIED: Accept user_iri parameter in commit()
├── commands/
│   ├── router.py            # MODIFIED: Inject current_user, enforce roles
│   └── dispatcher.py        # MODIFIED: Pass user context to handlers
├── sparql/
│   └── router.py            # MODIFIED: Require authentication
└── models/
    └── router.py            # MODIFIED: Require owner role
```

### Pattern 1: Dual-Database Engine Factory
**What:** A single factory function that returns the correct async engine based on the DATABASE_URL scheme.
**When to use:** Application startup, creating the engine in lifespan.
**Example:**
```python
# backend/app/db/engine.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from app.config import settings

def create_engine() -> AsyncEngine:
    """Create async engine for SQLite (local) or PostgreSQL (cloud).

    SQLite URL: sqlite+aiosqlite:///./data/sempkm.db
    PostgreSQL URL: postgresql+asyncpg://user:pass@host/dbname
    """
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        # SQLite needs check_same_thread=False for async
        connect_args = {"check_same_thread": False}

    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args=connect_args,
    )
```

### Pattern 2: Layered Auth Dependencies
**What:** Chain of FastAPI dependencies that extract session token, look up user, then check role.
**When to use:** Every protected endpoint.
**Example:**
```python
# backend/app/auth/dependencies.py
from fastapi import Depends, Cookie, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.auth.models import User, Session as UserSession

async def get_session_token(
    session_token: str | None = Cookie(None, alias="sempkm_session"),
) -> str:
    """Extract session token from cookie."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return session_token

async def get_current_user(
    token: str = Depends(get_session_token),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Look up session in DB, return user or 401."""
    session = await db.execute(
        select(UserSession).where(
            UserSession.token == token,
            UserSession.expires_at > func.now(),
        )
    )
    session_row = session.scalar_one_or_none()
    if not session_row:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session_row.user

def require_role(*roles: str):
    """Factory for role-checking dependencies."""
    async def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_role
```

Usage in routers:
```python
# Owner-only endpoint
@router.post("/install")
async def install_model(
    body: InstallRequest,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
):
    ...

# Any authenticated user (guest can query)
@router.get("/sparql")
async def sparql_get(
    user: User = Depends(get_current_user),  # Just auth, no role check
    ...
):
    ...

# Write operations require member or owner
@router.post("/commands")
async def execute_commands(
    user: User = Depends(require_role("owner", "member")),
    ...
):
    ...
```

### Pattern 3: Setup Token Flow (Local First-Run)
**What:** On first startup with no users, generate a one-time setup token, display it in the terminal, serve a setup page that accepts it.
**When to use:** Local instance initial setup.
**Example:**
```python
# Lifespan startup
async def lifespan(app: FastAPI):
    ...
    # Check if any users exist
    async with async_session() as db:
        result = await db.execute(select(func.count(User.id)))
        user_count = result.scalar()

    if user_count == 0:
        setup_token = secrets.token_urlsafe(32)
        app.state.setup_token = setup_token
        app.state.setup_mode = True
        logger.info("=" * 60)
        logger.info("FIRST-RUN SETUP")
        logger.info("Open your browser and enter this token:")
        logger.info("  %s", setup_token)
        logger.info("=" * 60)
    else:
        app.state.setup_mode = False
    ...
```

### Pattern 4: Event Provenance Enrichment
**What:** Add user identity to every event committed through EventStore.
**When to use:** Every EventStore.commit() call.
**Example:**
```python
# Modified EventStore.commit signature
async def commit(
    self,
    operations: list[Operation],
    performed_by: URIRef | None = None,  # NEW: user IRI
) -> EventResult:
    ...
    # Add user provenance to event metadata
    if performed_by:
        event_triples.append(
            (event_iri, SEMPKM.performedBy, performed_by)
        )
    ...
```

The `performed_by` IRI should follow the pattern `urn:sempkm:user:{user_id}` (UUID-based, not email) to decouple identity from contact info.

### Pattern 5: SQLAlchemy ORM Models
**What:** SQL schema for users, sessions, invitations, and instance config.
**When to use:** Database initialization.
**Example:**
```python
# backend/app/auth/models.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        Enum("owner", "member", "guest", name="user_role"),
        default="member",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")

class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="sessions")

class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(Enum("member", "guest", name="invite_role"))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class InstanceConfig(Base):
    __tablename__ = "instance_config"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(String(4096))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### Anti-Patterns to Avoid
- **Storing passwords "just in case":** The decision is passwordless-only. Do not add a password column. If the DB leaks, it should contain nothing exploitable beyond email addresses.
- **Using JWT for sessions:** With a single API tier (no microservices), JWT adds complexity (refresh tokens, revocation lists) for no benefit. Opaque tokens with DB lookup are simpler and revocable.
- **Putting user data in the triplestore:** User accounts, sessions, and roles belong in SQL. The triplestore holds knowledge data only. User IRIs in RDF events are references, not the source of truth.
- **Global middleware for auth:** Use FastAPI `Depends()` on individual routers/routes, not ASGI middleware. This gives per-route control (e.g., health endpoint stays public, setup endpoint only works in setup mode).
- **Skipping batch mode in Alembic:** Without `render_as_batch=True`, any migration that ALTERs a column will fail on SQLite.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL ORM | Custom SQL query builder | SQLAlchemy 2.0 async | Connection pooling, async session management, dialect-specific SQL generation, type-safe queries |
| Schema migrations | Manual CREATE/ALTER TABLE scripts | Alembic with batch mode | Auto-detection of model changes, reversible migrations, SQLite batch mode handles ALTER limitations |
| Token signing | Custom HMAC implementation | itsdangerous `URLSafeTimedSerializer` | Time-limited signatures, constant-time comparison, URL-safe encoding, battle-tested by Flask/Pallets |
| Session token generation | Custom random string | `secrets.token_urlsafe(32)` | Cryptographically secure, URL-safe, correct entropy (256 bits) |
| Async email | Synchronous smtplib in thread | aiosmtplib or fastapi-mail | Non-blocking email delivery, proper async/await integration |
| Password hashing | N/A | N/A | No passwords in this system -- passwordless by design |

**Key insight:** The SQL layer in this phase is small (4-5 tables) but must work identically across two database engines. SQLAlchemy + Alembic is the only Python stack with a proven track record for this exact dual-engine pattern. Hand-rolling the database layer would be fragile and untestable.

## Common Pitfalls

### Pitfall 1: SQLite Enum Type Handling
**What goes wrong:** SQLAlchemy `Enum` type creates a PostgreSQL ENUM type but maps to VARCHAR on SQLite. If you use `Enum(..., create_constraint=True)`, Alembic generates CHECK constraints that differ between backends.
**Why it happens:** SQLite doesn't support native ENUM types.
**How to avoid:** Use `Enum(..., native_enum=False)` to store as VARCHAR on both backends, or use `String` with application-level validation.
**Warning signs:** Migration works on PostgreSQL but fails on SQLite, or vice versa.

### Pitfall 2: SQLite DateTime Handling
**What goes wrong:** SQLite stores datetimes as strings (ISO format) while PostgreSQL has native TIMESTAMP. Timezone-aware datetimes behave differently.
**Why it happens:** SQLite has no native datetime type.
**How to avoid:** Always use `DateTime(timezone=True)` and ensure all Python datetime objects are timezone-aware (UTC). Test both backends.
**Warning signs:** Session expiry comparisons fail on one backend but work on the other.

### Pitfall 3: Alembic Migrations Without Batch Mode
**What goes wrong:** Migrations that use `op.alter_column()` or `op.drop_column()` fail on SQLite with "near ALTER: syntax error".
**Why it happens:** SQLite barely supports ALTER TABLE. Alembic's batch mode does a copy-rename workaround.
**How to avoid:** Set `render_as_batch=True` in `env.py`. On PostgreSQL, this is a no-op (regular ALTER runs). On SQLite, it transparently uses the move-and-copy workflow.
**Warning signs:** CI passes on PostgreSQL but migration commands fail locally.

### Pitfall 4: Session Cookie Security Flags
**What goes wrong:** Session cookies are accessible to JavaScript (XSS) or sent over HTTP (MITM).
**Why it happens:** Default cookie settings are permissive.
**How to avoid:** Set `httponly=True` (no JS access), `secure=True` in production (HTTPS only), `samesite="lax"` (CSRF protection). For local development over HTTP, allow `secure=False` with a config flag.
**Warning signs:** Sessions work in development but not in production behind HTTPS proxy.

### Pitfall 5: Setup Token Persistence Across Restarts
**What goes wrong:** The setup token is generated in-memory on startup; if the container restarts before the owner claims it, a new token is generated and the old one (possibly written down) is invalid.
**Why it happens:** In-memory-only token storage.
**How to avoid:** Write the setup token to a file in the data volume (e.g., `/app/data/.setup-token`). On startup, read existing token if file exists and no owner has been created yet. Delete the file after setup completes.
**Warning signs:** "Token invalid" errors after container restarts during first-run.

### Pitfall 6: Event Store Backward Compatibility
**What goes wrong:** Adding `sempkm:performedBy` to new events breaks code that assumes a fixed set of event predicates, or old events without the predicate cause errors in new UI code.
**Why it happens:** Schema evolution in an append-only event store.
**How to avoid:** Make `performed_by` optional (None for pre-migration events). Treat absence as "system/unknown". Never require the predicate in queries -- use OPTIONAL in SPARQL. Display "System" for events without user provenance.
**Warning signs:** Errors when displaying event history that includes pre-Phase-6 events.

### Pitfall 7: asyncpg Version Compatibility
**What goes wrong:** Certain versions of asyncpg (notably >=0.29.0 per some reports) can have issues with SQLAlchemy's `create_async_engine`.
**Why it happens:** asyncpg API changes that SQLAlchemy hasn't fully adapted to.
**How to avoid:** Pin asyncpg to `>=0.31.0` (current stable, confirmed compatible). Test the exact version combination in CI.
**Warning signs:** Connection errors or type serialization failures only on PostgreSQL.

## Code Examples

### Alembic Async env.py with Batch Mode
```python
# backend/migrations/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
from app.db.base import Base
from app.auth.models import User, UserSession, Invitation, InstanceConfig  # noqa

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,  # Critical for SQLite compatibility
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # Critical for SQLite compatibility
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Magic Link Token Generation and Verification
```python
# backend/app/auth/tokens.py
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key)

def create_magic_link_token(email: str) -> str:
    """Create a time-limited token for magic link authentication.

    Token embeds the email and is signed with the app secret.
    """
    return _serializer.dumps(email, salt="magic-link")

def verify_magic_link_token(token: str, max_age_seconds: int = 600) -> str | None:
    """Verify a magic link token and return the email.

    Returns None if token is expired (default 10 minutes) or invalid.
    """
    try:
        return _serializer.loads(token, salt="magic-link", max_age=max_age_seconds)
    except (SignatureExpired, BadSignature):
        return None

def create_invitation_token(email: str, role: str) -> str:
    """Create a token for user invitation."""
    return _serializer.dumps({"email": email, "role": role}, salt="invitation")

def verify_invitation_token(token: str, max_age_seconds: int = 7 * 86400) -> dict | None:
    """Verify an invitation token (default 7-day expiry)."""
    try:
        return _serializer.loads(token, salt="invitation", max_age=max_age_seconds)
    except (SignatureExpired, BadSignature):
        return None
```

### AsyncSession Dependency for FastAPI
```python
# backend/app/db/session.py
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.db.engine import create_engine

engine = create_engine()
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session.

    Session is committed on success, rolled back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Event Store Integration with User Identity
```python
# Modified command router to pass user context
@router.post("/commands")
async def execute_commands(
    request: Request,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
) -> CommandResponse:
    ...
    # Pass user identity to event store
    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    event_result = await event_store.commit(operations, performed_by=user_iri)
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x sync sessions | SQLAlchemy 2.0 async with `AsyncSession` | 2023 (SQLAlchemy 2.0 release) | Native async; no need for `run_in_executor` |
| Alembic sync-only migrations | Alembic async template with `async_engine_from_config` | Alembic 1.8+ (2022) | Migrations work with async engines natively |
| JWT for everything | Opaque tokens for server-rendered / single-API apps | Ongoing shift | JWT still dominant for microservices; opaque tokens preferred for monoliths |
| Password + MFA | Passwordless (magic links, passkeys) | 2023-2025 trend | Eliminates credential stuffing; simpler for users |

**Deprecated/outdated:**
- `sqlalchemy.orm.Session` (sync) with FastAPI: Use `AsyncSession` instead
- `databases` package (encode/databases): Superseded by SQLAlchemy 2.0 native async
- `flask-login` patterns in FastAPI: Use FastAPI's native `Depends` system

## Rework Analysis

This section analyzes the existing codebase files that need modification and the scope of changes.

### Event Store (`backend/app/events/store.py`)
**Current state:** `EventStore.commit(operations)` accepts only operations, no user context. Event metadata includes type, timestamp, operation, affected IRIs, description.
**Required change:** Add optional `performed_by: URIRef | None = None` parameter. Add `sempkm:performedBy` triple to event metadata when provided.
**Impact:** LOW -- additive change, backward compatible. Callers that don't pass `performed_by` (like model install during startup) produce events with no user attribution.

### Event Models (`backend/app/events/models.py`)
**Current state:** Defines EVENT_TYPE, EVENT_TIMESTAMP, EVENT_OPERATION, EVENT_AFFECTED, EVENT_DESCRIPTION.
**Required change:** Add `EVENT_PERFORMED_BY = SEMPKM.performedBy`.
**Impact:** LOW -- adding one constant.

### Command Router (`backend/app/commands/router.py`)
**Current state:** No authentication. Creates EventStore inline. No user context.
**Required change:** Add `Depends(require_role("owner", "member"))` to `execute_commands`. Pass `user_iri` to `event_store.commit()`. Use app-state EventStore instead of creating new one.
**Impact:** MEDIUM -- signature changes, dependency additions.

### SPARQL Router (`backend/app/sparql/router.py`)
**Current state:** No authentication. Supports GET and POST.
**Required change:** Add `Depends(get_current_user)` to both endpoints (all roles can query).
**Impact:** LOW -- add one dependency parameter.

### Models Router (`backend/app/models/router.py`)
**Current state:** No authentication. Install, remove, list endpoints.
**Required change:** Add `Depends(require_role("owner"))` to install and remove. List can be any authenticated user.
**Impact:** LOW -- add dependency parameters.

### Config (`backend/app/config.py`)
**Current state:** Triplestore URL, repository ID, base namespace, app version.
**Required change:** Add DATABASE_URL, SECRET_KEY, SESSION_DURATION_DAYS, SMTP_* settings (optional), SETUP_MODE flag.
**Impact:** LOW -- additive.

### Main App (`backend/app/main.py`)
**Current state:** Lifespan creates triplestore client and services. No SQL database.
**Required change:** Initialize SQL engine, run Alembic migrations on startup (or verify schema), check for setup mode, create/display setup token if needed.
**Impact:** MEDIUM -- significant additions to lifespan.

### Docker Compose (`docker-compose.yml`)
**Current state:** Three services: triplestore, api, frontend. No persistent data volume for api.
**Required change:** Add a data volume for SQLite database. Add environment variables for SECRET_KEY, DATABASE_URL. Ensure RDF4J port is NOT exposed to host (currently exposed on 8080 -- this needs to change per the locked decision).
**Impact:** MEDIUM -- note that port 8080 is currently exposed, violating the "RDF4J port not exposed" decision. This must be fixed.

### Nginx Config (`frontend/nginx.conf`)
**Current state:** Proxies /api/ to backend. No auth headers.
**Required change:** May need to forward auth cookies. Add setup wizard HTML page. Potentially add auth-related static pages (login, invitation accept).
**Impact:** MEDIUM -- new pages and routes.

## Open Questions

1. **Secret key management for local installs**
   - What we know: `itsdangerous` and session tokens need a SECRET_KEY. For cloud, this comes from environment/secrets manager.
   - What's unclear: For local Docker Compose, should the secret be auto-generated on first run and persisted to the data volume, or should users set it in `.env`?
   - Recommendation: Auto-generate on first run, write to `/app/data/.secret-key`. Read from file if exists, generate if not. This gives zero-config local setup.

2. **Soft-delete vs hard-delete mechanics**
   - What we know: Members can soft-delete (archive), only owner can permanently delete or restore.
   - What's unclear: How does soft-delete map to the event-sourced RDF model? Is it a new command type (`object.archive`) that removes from current graph but preserves in event history? Or a metadata flag?
   - Recommendation: New `object.archive` command that removes from current graph and adds `sempkm:archivedAt` + `sempkm:archivedBy` metadata. Owner can `object.restore` to re-materialize. This fits the event sourcing model naturally.

3. **Cloud multi-instance routing**
   - What we know: Shared API tier routes to per-customer RDF4J stores. Shared PostgreSQL for user data.
   - What's unclear: How does the shared API tier determine which RDF4J instance to route to? Is this phase's responsibility or infrastructure-level?
   - Recommendation: This phase should design the SQL schema to include instance membership (user_id + instance_id), but the actual routing infrastructure is a separate concern. Include `instance_id` in the User/Membership schema so cloud deployment can query it.

4. **RDF4J port exposure**
   - What we know: The locked decision says "RDF4J port not exposed to host." Current docker-compose.yml exposes 8080.
   - What's unclear: Should this be fixed in this phase or earlier?
   - Recommendation: Fix it in this phase as part of security hardening. Remove `ports: - "8080:8080"` from the triplestore service. The API container can still reach it via the Docker network.

5. **Session refresh for long-lived local sessions**
   - What we know: Default 30-day sessions. Local owner should have near-zero friction.
   - What's unclear: Should sessions auto-extend on activity (sliding window) or have a fixed expiry?
   - Recommendation: Sliding window -- on each authenticated request, if the session is past 50% of its lifetime, extend it by the full duration. This gives the local owner an effectively permanent session as long as they use the system regularly.

## Sources

### Primary (HIGH confidence)
- [Alembic batch mode documentation](https://alembic.sqlalchemy.org/en/latest/batch.html) -- SQLite batch migration workflow, `render_as_batch=True`
- [Alembic async template](https://github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py) -- Official async env.py pattern
- [SQLAlchemy 2.0 asyncio documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) -- AsyncSession, expire_on_commit=False
- [FastAPI security documentation](https://fastapi.tiangolo.com/tutorial/security/) -- OAuth2, dependency injection for auth
- [FastAPI dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies/) -- Depends chain pattern
- [itsdangerous documentation](http://pythonhosted.org/itsdangerous/) -- URLSafeTimedSerializer for token signing

### Secondary (MEDIUM confidence)
- [Alembic GitHub Discussion #1009](https://github.com/sqlalchemy/alembic/discussions/1009) -- Alembic maintainer confirms SQLite+PostgreSQL dual-backend is "very common" pattern
- [Scalekit FastAPI Passwordless Guide](https://www.scalekit.com/blog/fastapi-passwordless-magic-link-otp-implementation) -- Magic link implementation patterns for FastAPI
- [Stytch: JWTs vs Sessions](https://stytch.com/blog/jwts-vs-sessions-which-is-right-for-you/) -- Comparison confirming opaque tokens better for single-tier architectures
- [FastAPI RBAC Tutorial (Permit.io)](https://www.permit.io/blog/fastapi-rbac-full-implementation-tutorial) -- Role-based dependency injection patterns

### Tertiary (LOW confidence)
- [Medium: FastAPI async SQLAlchemy 2.0 setup](https://medium.com/@tclaitken/setting-up-a-fastapi-app-with-async-sqlalchemy-2-0-pydantic-v2-e6c540be4308) -- Community guide, patterns verified against official docs
- asyncpg version compatibility note -- based on WebSearch findings about >=0.29.0 issues; current 0.31.0 appears stable but should be verified in CI

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- SQLAlchemy 2.0 + Alembic + aiosqlite/asyncpg is the dominant async Python ORM stack, confirmed by official docs
- Architecture: MEDIUM-HIGH -- auth dependency injection pattern is well-documented in FastAPI ecosystem; dual-database pattern confirmed by Alembic maintainer
- Pitfalls: MEDIUM -- SQLite/PostgreSQL dialect differences and Alembic batch mode are well-documented; session security patterns are standard web security
- Event provenance: MEDIUM -- PROV namespace already in codebase; adding `performedBy` to events is straightforward but the backward compatibility handling needs careful testing

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable technologies, 30-day window)
