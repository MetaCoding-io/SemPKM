"""SemPKM FastAPI application with lifespan management."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlencode as _urlencode

import httpx
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2_fragments.fastapi import Jinja2Blocks

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.browser.router import router as browser_router
from app.views.router import router as views_router
from app.debug.router import router as debug_router
from app.auth.service import AuthService
from app.auth.tokens import load_or_create_setup_token
from app.config import settings
from app.commands.router import router as commands_router
from app.db.engine import create_engine
from app.db.session import async_session_factory
from app.shell.router import router as shell_router
from app.events.store import EventStore
from app.health.router import router as health_router
from app.models.router import router as models_router
from app.services.labels import LabelService
from app.services.models import ModelService, model_shapes_loader, ensure_starter_model
from app.services.prefixes import PrefixRegistry
from app.services.shapes import ShapesService
from app.services.validation import ValidationService
from app.services.webhooks import WebhookService
from app.views.service import ViewSpecService
from app.sparql.router import router as sparql_router
from app.triplestore.client import TriplestoreClient
from app.triplestore.setup import ensure_repository
from app.monitoring.middleware import PostHogErrorMiddleware
from app.monitoring.posthog import init_posthog, shutdown_posthog
from app.monitoring.router import router as monitoring_router
from app.validation.queue import AsyncValidationQueue
from app.validation.router import router as validation_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle.

    Startup: Create triplestore client, ensure RDF4J repository exists.
    Shutdown: Close the triplestore client connection.
    """
    logger.info("Starting SemPKM API v%s", settings.app_version)

    # Initialize PostHog analytics/error monitoring
    init_posthog()

    # Create triplestore client and store on app state
    client = TriplestoreClient(
        base_url=settings.triplestore_url,
        repository_id=settings.repository_id,
    )
    app.state.triplestore_client = client

    # Ensure RDF4J repository exists with proper configuration
    async with httpx.AsyncClient(timeout=30.0) as setup_client:
        await ensure_repository(
            client=setup_client,
            base_url=settings.triplestore_url,
            repo_id=settings.repository_id,
        )

    # Create prefix registry and label service
    prefix_registry = PrefixRegistry()
    app.state.prefix_registry = prefix_registry

    label_service = LabelService(client, prefix_registry)
    app.state.label_service = label_service

    # Create event store and model service
    event_store = EventStore(client)
    app.state.event_store = event_store

    model_service = ModelService(client, event_store, prefix_registry)
    app.state.model_service = model_service

    # Auto-install starter model if no models are installed
    # models/ directory is mounted at /app/models in the container
    starter_model_path = Path("/app/models/basic-pkm")
    await ensure_starter_model(model_service, starter_model_path)

    # Create validation service with real shapes loader (replaces empty_shapes_loader)
    async def shapes_loader():
        return await model_shapes_loader(client)

    validation_service = ValidationService(client, shapes_loader)
    app.state.validation_service = validation_service

    # Create WebhookService for outbound event notifications
    # (must be created before validation_queue so it can be used in the callback)
    webhook_service = WebhookService(client)
    app.state.webhook_service = webhook_service

    # Define validation completion callback for webhook dispatch
    async def on_validation_complete(report_summary, event_iri, timestamp):
        await webhook_service.dispatch("validation.completed", {
            "event_iri": event_iri,
            "timestamp": timestamp,
            "conforms": report_summary.conforms,
            "violations": report_summary.violation_count,
            "warnings": report_summary.warning_count,
        })

    validation_queue = AsyncValidationQueue(
        validation_service, on_complete=on_validation_complete
    )
    app.state.validation_queue = validation_queue
    await validation_queue.start()

    # Create ShapesService for SHACL shape extraction (form generation)
    shapes_service = ShapesService(client)
    app.state.shapes_service = shapes_service

    # Create ViewSpecService for view spec loading and execution
    view_spec_service = ViewSpecService(client, label_service)
    app.state.view_spec_service = view_spec_service

    # --- SQL Database Initialization ---
    # Run Alembic migrations BEFORE creating the app engine.
    # Alembic's env.py creates its own async engine via asyncio.run(),
    # so we must not have a competing engine connection to the same
    # SQLite file (SQLite allows only one writer at a time).
    alembic_cfg = AlembicConfig("alembic.ini")

    def _run_migrations():
        """Run or stamp Alembic migrations.

        If the database already has tables (from the old create_all approach)
        but no alembic_version row, stamp it at head via direct SQL so Alembic
        treats the existing schema as current. Future migrations run normally.
        """
        import sqlite3
        from pathlib import Path as _Path

        db_url = settings.database_url
        db_path = db_url.split("///")[-1] if "///" in db_url else None
        if db_path and _Path(db_path).exists():
            conn = sqlite3.connect(db_path)
            try:
                tables = {r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()}
                has_version_row = False
                if "alembic_version" in tables:
                    row = conn.execute(
                        "SELECT version_num FROM alembic_version"
                    ).fetchone()
                    has_version_row = row is not None
                if "users" in tables and not has_version_row:
                    # Stamp directly via SQL — avoids asyncio.run() nesting issues
                    from alembic.script import ScriptDirectory
                    script = ScriptDirectory.from_config(alembic_cfg)
                    head = script.get_current_head()
                    if "alembic_version" not in tables:
                        conn.execute(
                            "CREATE TABLE alembic_version "
                            "(version_num VARCHAR(32) NOT NULL, "
                            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
                        )
                    conn.execute(
                        "INSERT INTO alembic_version (version_num) VALUES (?)",
                        (head,),
                    )
                    conn.commit()
                    logger.info("Existing database stamped at Alembic revision %s", head)
                    return
            finally:
                conn.close()
        alembic_command.upgrade(alembic_cfg, "head")

    await asyncio.to_thread(_run_migrations)
    logger.info("SQL database migrations applied")

    sql_engine = create_engine()

    # Store session factory on app state for dependencies
    app.state.async_session_factory = async_session_factory

    # Create AuthService and store on app state
    auth_service = AuthService(async_session_factory)
    app.state.auth_service = auth_service

    # Purge expired sessions on startup
    purged = await auth_service.cleanup_expired_sessions()
    if purged:
        logger.info("Purged %d expired sessions", purged)

    # --- Setup Mode Detection ---
    setup_complete = await auth_service.is_setup_complete()
    if not setup_complete:
        setup_token = load_or_create_setup_token()
        app.state.setup_mode = True
        app.state.setup_token = setup_token
        logger.info("")
        logger.info("=" * 60)
        logger.info("  FIRST-RUN SETUP")
        logger.info("  No owner found. Use this token to claim the instance:")
        logger.info("")
        logger.info("  Setup token: %s", setup_token)
        logger.info("")
        logger.info("  POST /api/auth/setup with {\"token\": \"<token>\"}")
        logger.info("=" * 60)
        logger.info("")
    else:
        app.state.setup_mode = False
        app.state.setup_token = None

    logger.info("SemPKM API started successfully")
    yield

    # Shutdown: stop validation queue, dispose SQL engine, close triplestore client,
    # flush PostHog events
    await validation_queue.stop()
    await sql_engine.dispose()
    await client.close()
    shutdown_posthog()
    logger.info("SemPKM API shut down")


app = FastAPI(
    title="SemPKM API",
    version=settings.app_version,
    lifespan=lifespan,
)

# Jinja2 template engine with block-level rendering for htmx partials
templates = Jinja2Blocks(directory=Path(__file__).parent / "templates")
app.state.templates = templates


def _dict_without(d: dict, key: str) -> dict:
    """Jinja2 filter: return a copy of dict d with the given key removed."""
    return {k: v for k, v in d.items() if k != key}


def _urlencode_filter(value) -> str:
    """Jinja2 filter: URL-encode a dict to query string or a scalar to percent-encoded string."""
    if isinstance(value, dict):
        return _urlencode(value)
    return quote(str(value), safe="")


def _compact_iri(iri: str) -> str:
    """Jinja2 filter: convert a full IRI to prefix:localname, or last segment as fallback."""
    from app.rdf.namespaces import COMMON_PREFIXES
    # Sort by namespace length descending so longer prefixes match first
    for prefix, namespace in sorted(COMMON_PREFIXES.items(), key=lambda x: len(x[1]), reverse=True):
        if iri.startswith(namespace):
            return f"{prefix}:{iri[len(namespace):]}"
    # Fallback: last '#', '/', or ':' segment
    for sep in ("#", "/", ":"):
        idx = iri.rfind(sep)
        if 0 <= idx < len(iri) - 1:
            return iri[idx + 1:]
    return iri


templates.env.filters["dict_without"] = _dict_without
# Register urlencode as dict-capable filter (Jinja2 built-in only handles scalars)
templates.env.filters["urlencode"] = _urlencode_filter
templates.env.filters["compact_iri"] = _compact_iri


def _is_html_route(path: str) -> bool:
    """Return True for HTML routes, False for API routes."""
    return not path.startswith("/api/")


@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    """Route auth errors to appropriate response format.

    - API routes (/api/*): always JSON (no interception)
    - HTML routes with 401:
        - HTMX partial requests: inline error fragment
        - Full page requests: 302 redirect to /login.html?next=...
    - HTML routes with 403:
        - HTMX partial requests: inline error fragment
        - Full page requests: styled 403.html template
    - All other status codes: JSON response
    """
    path = request.url.path
    is_htmx = request.headers.get("HX-Request") == "true"

    if _is_html_route(path):
        if exc.status_code == 401:
            if is_htmx:
                return HTMLResponse(
                    content='<div class="auth-error">Session expired. '
                    '<a href="/login.html">Log in again</a></div>',
                    status_code=401,
                )
            return RedirectResponse(
                url=f"/login.html?next={quote(str(request.url.path), safe='/')}",
                status_code=302,
            )
        if exc.status_code == 403:
            if is_htmx:
                return HTMLResponse(
                    content='<div class="auth-error">Access denied. '
                    "You do not have permission for this action.</div>",
                    status_code=403,
                )
            return templates.TemplateResponse(
                request,
                "errors/403.html",
                {"request": request},
                status_code=403,
            )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# PostHog error-capturing middleware (must be added before CORS so it wraps
# the full request lifecycle and catches unhandled exceptions)
app.add_middleware(PostHogErrorMiddleware)

# CORS: use specific origins with credentials when configured, wildcard without credentials otherwise
cors_origins_list = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers (API routers first, then UI routers, shell router last)
app.include_router(monitoring_router)
app.include_router(auth_router)
app.include_router(commands_router)
app.include_router(health_router)
app.include_router(models_router)
app.include_router(sparql_router)
app.include_router(validation_router)
app.include_router(admin_router)
app.include_router(views_router)
app.include_router(browser_router)
app.include_router(debug_router)
app.include_router(shell_router)

from fastapi.staticfiles import StaticFiles

# Serve user guide Markdown files as static content.
# In Docker: backend/ is the build context so main.py is at /app/app/main.py.
# The repo docs/ is mounted at /app/docs via docker-compose volume, giving
# /app/docs/guide/ = Path(__file__).parent.parent / "docs" / "guide".
# In local dev (running backend directly): main.py is at backend/app/main.py
# and docs/ is three levels up at repo root, so fall back to parent.parent.parent.
_docs_guide_path = Path(__file__).parent.parent / "docs" / "guide"
if not _docs_guide_path.is_dir():
    _docs_guide_path = Path(__file__).parent.parent.parent / "docs" / "guide"
if _docs_guide_path.is_dir():
    app.mount("/docs/guide", StaticFiles(directory=_docs_guide_path), name="docs_guide")
