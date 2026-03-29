"""SemPKM FastAPI application with lifespan management."""

import asyncio
import logging
import signal
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

from app.api.ai import ai_router
from app.api.copilot import copilot_router
from app.api.router import well_known_router, api_surface_router
from app.api.setup_routes import setup_router
from app.admin.router import router as admin_router
from app.apps.admin_router import app_admin_router
from app.apps.proxy import AppProxy
from app.apps.router import app_proxy_router
from app.auth.router import router as auth_router
from app.browser.apps import app_commands_router
from app.browser.router import router as browser_router
from app.inference.router import router as inference_router
from app.lint.broadcast import LintBroadcast, SSEEvent
from app.lint.router import router as lint_router
from app.lint.service import LintService
from app.canvas.router import router as canvas_router
from app.obsidian.router import router as obsidian_router
from app.notion.router import router as notion_router
from app.rdf_import.router import router as rdf_import_router
from app.views.router import router as views_router
from app.dashboard.router import browser_router as dashboard_browser_router, api_router as dashboard_api_router
from app.workflow.router import browser_router as workflow_browser_router, api_router as workflow_api_router
from app.task_templates.router import api_router as templates_api_router, browser_router as templates_browser_router
from app.persona.router import browser_router as persona_browser_router, api_router as persona_api_router
from app.context.router import router as context_router
from app.context.rules_router import router as context_rules_router
from app.context.zone_router import router as context_zones_router
from app.context.notification_router import router as notification_router
from app.debug.router import router as debug_router
from app.middleware.etag import ConditionalGetMiddleware
from app.middleware.timing import TimingMiddleware, timing_router
from app.auth.service import AuthService
from app.auth.tokens import load_or_create_setup_token
from app.config import settings, TIMEOUT_DEFAULT
from app.commands.router import router as commands_router
from app.db.engine import create_engine
from app.db.session import async_session_factory
from app.shell.router import router as shell_router
from app.events.store import EventStore
from app.health.router import router as health_router
from app.models.router import router as models_router
from app.ontology.service import OntologyService
from app.services.icons import load_user_type_icons
from app.services.labels import LabelService
from app.services.models import ModelService, model_shapes_loader, ensure_starter_model
from app.services.search import SearchService
from app.services.prefixes import PrefixRegistry
from app.services.shapes import ShapesService
from app.services.validation import ValidationService
from app.services.ops_log import OperationsLogService
from app.services.webhooks import WebhookService
from app.views.service import ViewSpecService
from app.sparql.mirror_router import router as mirror_router
from app.sparql.router import router as sparql_router
from app.triplestore.client import TriplestoreClient
from app.triplestore.setup import ensure_repository
from app.monitoring.middleware import PostHogErrorMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.auth.rate_limit import limiter
from app.monitoring.posthog import init_posthog, shutdown_posthog
from app.monitoring.router import router as monitoring_router
from app.validation.queue import AsyncValidationQueue
# Old validation router removed in 37-02 (replaced by /api/lint/*)
# from app.validation.router import router as validation_router
from wsgidav.wsgidav_app import WsgiDAVApp
from a2wsgi import WSGIMiddleware
from app.vfs.provider import SemPKMDAVProvider
from app.vfs.router import router as vfs_browser_router
from app.vfs.mount_router import router as vfs_mount_router
from app.federation.router import router as federation_router
from app.federation.webfinger import webfinger_router
from app.federation.inbox import inbox_router
from app.webid.router import router as webid_router, public_router as webid_public_router
from app.indieauth.router import router as indieauth_router, public_router as indieauth_public_router
from app.vfs.auth import SemPKMWsgiAuthenticator
from app.triplestore.sync_client import SyncTriplestoreClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle.

    Startup: Create triplestore client, ensure RDF4J repository exists.
    Shutdown: Close the triplestore client connection.
    """
    logger.info("Starting SemPKM API v%s", settings.app_version)

    # Create cooperative shutdown signal for SSE generators.
    # When uvicorn reloads, request.is_disconnected() does NOT fire for SSE
    # streams, so generators with `while True` loops hang forever.  This event
    # lets them exit within one iteration.
    #
    # IMPORTANT: uvicorn waits for all connections to close BEFORE calling the
    # lifespan __aexit__ (the code after `yield`).  So we cannot set the event
    # there — it would deadlock.  Instead we install a signal handler that
    # fires the event as soon as SIGTERM/SIGINT arrives (before uvicorn starts
    # waiting).  We chain to the previous handler so uvicorn's own shutdown
    # still proceeds normally.
    shutdown_event = asyncio.Event()
    app.state.shutdown_event = shutdown_event

    loop = asyncio.get_running_loop()

    def _on_shutdown_signal(sig, frame):
        """Set shutdown event on SIGTERM/SIGINT so SSE generators exit."""
        shutdown_event.set()

    # Install signal handlers — chain with existing ones so uvicorn still
    # receives the signal and initiates its own shutdown sequence.
    for sig in (signal.SIGTERM, signal.SIGINT):
        prev_handler = signal.getsignal(sig)
        def _chained(signum, frame, _prev=prev_handler):
            _on_shutdown_signal(signum, frame)
            if callable(_prev) and _prev not in (signal.SIG_DFL, signal.SIG_IGN):
                _prev(signum, frame)
        signal.signal(sig, _chained)

    # Initialize PostHog analytics/error monitoring
    init_posthog()

    # Create triplestore client and store on app state
    client = TriplestoreClient(
        base_url=settings.triplestore_url,
        repository_id=settings.repository_id,
    )
    app.state.triplestore_client = client

    # Ensure RDF4J repository exists with proper configuration
    async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as setup_client:
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

    # Create lint service for structured SHACL validation results
    lint_service = LintService(client, label_service)
    app.state.lint_service = lint_service

    # Create SSE broadcast manager for real-time lint event push
    lint_broadcast = LintBroadcast()
    app.state.lint_broadcast = lint_broadcast

    # Create search service for full-text keyword search (LuceneSail)
    search_service = SearchService(client)
    app.state.search_service = search_service

    # Create event store and model service
    event_store = EventStore(client)
    app.state.event_store = event_store

    # Wire event store into DAV provider for write path (PUT body.set)
    # The DAV provider is constructed at module load time; inject event_store here.
    _dav_provider.set_event_store(event_store)

    model_service = ModelService(client, event_store, prefix_registry)
    app.state.model_service = model_service

    # Auto-install starter model if no models are installed
    # models/ directory is mounted at /app/models in the container
    starter_model_path = Path("/app/models/basic-pkm")
    await ensure_starter_model(model_service, starter_model_path)

    # Load gist upper ontology into the triplestore (idempotent)
    ontology_service = OntologyService(client)
    app.state.ontology_service = ontology_service

    # Query service (RDF-backed saved queries, history, sharing, promotion)
    from app.sparql.query_service import QueryService
    query_service = QueryService(client)
    app.state.query_service = query_service

    # Operations log service (PROV-O activity logging)
    ops_log_service = OperationsLogService(client)
    app.state.ops_log_service = ops_log_service

    gist_path = Path("/app/ontologies/gist/gistCore14.0.0.ttl")
    gist_annotations_path = Path(
        "/app/ontologies/gist/gistRdfsAnnotations14.0.0.ttl"
    )
    try:
        await ontology_service.ensure_gist_loaded(
            gist_path, annotations_path=gist_annotations_path
        )
    except Exception:
        logger.error("gist ontology load failed — TBox queries will be incomplete", exc_info=True)

    # Load user-type icons from triplestore into app.state for IconService
    try:
        app.state.user_type_icons = await load_user_type_icons(client)
    except Exception:
        logger.warning("Failed to load user-type icons at startup")
        app.state.user_type_icons = {}

    # Create validation service with real shapes loader (replaces empty_shapes_loader)
    async def shapes_loader():
        return await model_shapes_loader(client)

    validation_service = ValidationService(client, shapes_loader)
    app.state.validation_service = validation_service

    # Create WebhookService for outbound event notifications
    # (must be created before validation_queue so it can be used in the callback)
    webhook_service = WebhookService(client)
    app.state.webhook_service = webhook_service

    # Define validation completion callback for webhook dispatch + SSE broadcast
    async def on_validation_complete(report_summary, event_iri, timestamp, trigger_source="user_edit"):
        # Dispatch webhook (existing behavior)
        await webhook_service.dispatch("validation.completed", {
            "event_iri": event_iri,
            "timestamp": timestamp,
            "conforms": report_summary.conforms,
            "violations": report_summary.violation_count,
            "warnings": report_summary.warning_count,
        })
        # Broadcast SSE event to all connected clients
        await lint_broadcast.publish(SSEEvent(
            event="validation_complete",
            data={
                "run_id": report_summary.report_iri or "",
                "conforms": report_summary.conforms,
                "violation_count": report_summary.violation_count,
                "warning_count": report_summary.warning_count,
                "info_count": report_summary.info_count,
                "timestamp": timestamp,
                "trigger_source": trigger_source,
            },
        ))

    validation_queue = AsyncValidationQueue(
        validation_service, on_complete=on_validation_complete,
        ops_log_service=ops_log_service,
    )
    app.state.validation_queue = validation_queue
    await validation_queue.start()

    # Create ShapesService for SHACL shape extraction (form generation)
    shapes_service = ShapesService(client)
    app.state.shapes_service = shapes_service

    # Create ViewSpecService for view spec loading and execution
    view_spec_service = ViewSpecService(client, label_service, query_service, shapes_service)
    app.state.view_spec_service = view_spec_service

    # Register generic views (table, card, graph) for dynamic SHACL-driven browsing
    view_spec_service.register_generic_views()

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

    # Create DashboardService and store on app state
    from app.dashboard.service import DashboardService
    app.state.dashboard_service = DashboardService(async_session_factory)

    # Create WorkflowService and store on app state
    from app.workflow.service import WorkflowService
    app.state.workflow_service = WorkflowService(async_session_factory)

    # Create TaskTemplateService and store on app state
    from app.task_templates.service import TaskTemplateService
    app.state.template_service = TaskTemplateService(client)

    # Create PersonaService and store on app state
    from app.persona.service import PersonaService
    app.state.persona_service = PersonaService(async_session_factory)

    # Create ContextService and ContextBroadcast for user context awareness
    from app.context.service import ContextService
    from app.context.broadcast import ContextBroadcast
    app.state.context_service = ContextService(async_session_factory)
    app.state.context_broadcast = ContextBroadcast()

    # Create RulesEngine for context-to-persona auto-switching
    from app.context.rules_engine import RulesEngine
    app.state.rules_engine = RulesEngine(async_session_factory)

    # Create ZoneService for geofence zone CRUD
    from app.context.zone_service import ZoneService
    app.state.zone_service = ZoneService(async_session_factory)

    # Create NotificationService for push notification dispatch
    import os
    from app.context.notification_service import NotificationService
    firebase_app = None
    creds_path = settings.firebase_credentials_path
    if creds_path and os.path.isfile(creds_path):
        try:
            import firebase_admin
            from firebase_admin import credentials as fb_credentials
            cred = fb_credentials.Certificate(creds_path)
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized from %s", creds_path)
        except Exception:
            logger.error("Failed to initialize Firebase Admin", exc_info=True)
    else:
        logger.info("notification.skipped reason=firebase_not_configured")
    app.state.notification_service = NotificationService(
        async_session_factory, app.state.context_service, firebase_app
    )

    # Create LintFilterService and store on app state
    from app.lint.filter_service import LintFilterService
    app.state.lint_filter_service = LintFilterService(async_session_factory)

    # Initialize App Platform manager
    from app.apps.manager import AppManager
    _platform_url = settings.app_base_url
    if not _platform_url:
        logger.warning(
            "APP_BASE_URL not set — app platform_url will default to "
            "http://localhost:4000. Set APP_BASE_URL for production."
        )
        _platform_url = "http://localhost:4000"
    app_manager = AppManager(
        session_factory=async_session_factory,
        triplestore_client=client,
        apps_dir=Path("/app/apps"),
        data_dir=Path("/app/data/apps"),
        platform_url=_platform_url,
    )
    app.state.app_manager = app_manager

    # Create AppProxy for forwarding HTTP to app subprocesses via UDS
    app_proxy = AppProxy(app_manager)
    app.state.app_proxy = app_proxy

    # Auto-start apps that were running before platform shutdown
    try:
        await app_manager.auto_start()
    except Exception:
        logger.error("Failed to auto-start apps", exc_info=True)

    # Create and start AppScheduler for periodic task execution
    from app.apps.scheduler import AppScheduler
    app_scheduler = AppScheduler(
        registry=app_manager.registry,
        app_manager=app_manager,
        app_proxy=app_proxy,
        async_sessionmaker=async_session_factory,
    )
    app.state.app_scheduler = app_scheduler
    await app_scheduler.start()

    # Purge expired sessions on startup
    purged = await auth_service.cleanup_expired_sessions()
    if purged:
        logger.info("Purged %d expired sessions", purged)

    # Purge expired used-magic-token records on startup
    purged_magic = await auth_service.cleanup_expired_magic_tokens()
    if purged_magic:
        logger.info("Purged %d expired magic token records", purged_magic)

    # --- Namespace Validation ---
    # Warn if base_namespace is still the dangerous default and no instance
    # config exists — means the user hasn't gone through the setup wizard.
    from app.instance_config import DEFAULT_CONFIG_PATH as _ic_path
    if settings.base_namespace == "https://example.org/data/" and not _ic_path.is_file():
        logger.warning(
            "BASE_NAMESPACE is set to the default 'https://example.org/data/'. "
            "This will cause IRI collisions with other SemPKM instances. "
            "Run the setup wizard or set BASE_NAMESPACE in your .env file."
        )

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

    # --- Seed sample data for first-time users ---
    if setup_complete:
        try:
            from app.dashboard.seed import seed_sample_data
            from sqlalchemy import select as sa_select
            from app.auth.models import User as UserModel

            async with async_session_factory() as session:
                result = await session.execute(sa_select(UserModel).limit(1))
                first_user = result.scalar_one_or_none()
            if first_user:
                seed_outcome = await seed_sample_data(
                    app.state.dashboard_service,
                    app.state.workflow_service,
                    first_user.id,
                )
                if seed_outcome.get("dashboard_created") or seed_outcome.get("workflow_created"):
                    logger.info("Seeded sample data: %s", seed_outcome)
        except Exception:
            logger.warning("Seed sample data failed (non-fatal)", exc_info=True)

    # --- Security Startup Warnings ---
    _WEAK_KEYS = {"changeme", "secret", "password", "admin"}
    if settings.secret_key in _WEAK_KEYS and not settings.demo_mode:
        logger.error(
            "SECRET_KEY is a known weak value ('%s'). "
            "Set a strong random SECRET_KEY before running in production.",
            settings.secret_key,
        )
        raise SystemExit(1)

    _is_localhost = (
        not settings.app_base_url
        or "localhost" in settings.app_base_url
        or "127.0.0.1" in settings.app_base_url
    )
    if settings.demo_mode and not _is_localhost:
        logger.warning(
            "demo_mode=True with non-localhost APP_BASE_URL (%s). "
            "Demo mode disables authentication — this is dangerous on a "
            "public-facing instance.",
            settings.app_base_url,
        )
    if not settings.cookie_secure and not _is_localhost:
        logger.warning(
            "cookie_secure=False with non-localhost APP_BASE_URL (%s). "
            "Session cookies will be sent over plain HTTP, making them "
            "vulnerable to interception.",
            settings.app_base_url,
        )
    if not settings.cookie_secure and settings.app_base_url.startswith("https://"):
        logger.warning(
            "cookie_secure=False but APP_BASE_URL uses HTTPS (%s). "
            "Set COOKIE_SECURE=true for HTTPS deployments.",
            settings.app_base_url,
        )

    logger.info("SemPKM API started successfully")

    # --- Periodic session/token cleanup (daily) ---
    async def _periodic_cleanup():
        """Run session and magic-token cleanup once every 24 hours."""
        while True:
            await asyncio.sleep(86400)  # 24 hours
            try:
                purged_sessions = await auth_service.cleanup_expired_sessions()
                purged_magic = await auth_service.cleanup_expired_magic_tokens()
                if purged_sessions or purged_magic:
                    logger.info(
                        "Periodic cleanup: %d expired sessions, %d expired magic tokens",
                        purged_sessions,
                        purged_magic,
                    )
            except Exception:
                logger.warning("Periodic session cleanup failed (non-fatal)", exc_info=True)

    _cleanup_task = asyncio.create_task(_periodic_cleanup())

    yield

    # Cancel periodic cleanup task
    _cleanup_task.cancel()
    try:
        await _cleanup_task
    except asyncio.CancelledError:
        pass

    # Shutdown: signal SSE generators first so they exit before we tear down
    # the services they depend on, then stop validation queue, dispose SQL
    # engine, close triplestore client, flush PostHog events.
    shutdown_event.set()
    await validation_queue.stop()

    # Stop AppScheduler before tearing down proxy and manager
    try:
        await app_scheduler.stop()
    except Exception:
        logger.error("Error stopping app scheduler", exc_info=True)

    # Close proxy connections before stopping app subprocesses
    try:
        await app_proxy.close_all()
    except Exception:
        logger.error("Error closing app proxy connections", exc_info=True)

    # Gracefully shut down all running app subprocesses
    try:
        await app_manager.shutdown_all()
    except Exception:
        logger.error("Error shutting down app processes", exc_info=True)

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

from app.template_helpers import init_template_helpers  # noqa: E402

init_template_helpers(app)


def _is_html_route(path: str) -> bool:
    """Return True for HTML routes, False for API routes."""
    return not (path.startswith("/api/") or path.startswith("/.well-known/"))


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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a generic 500 response.

    Logs the full traceback for debugging but returns only a generic
    message to the client to avoid leaking internal details (F-025).
    """
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# --- Rate limiting (slowapi) ---
# In-memory per-IP rate limiting for auth endpoints. The Limiter instance
# and decorators live in app.auth.rate_limit / app.auth.router; the
# middleware, state binding, and exception handler are registered here.
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


def _rate_limit_exceeded_handler_with_logging(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Log rate limit events at WARNING level and return 429 with Retry-After."""
    logger.warning(
        "rate_limit.exceeded source_ip=%s path=%s detail=%s",
        request.client.host if request.client else "unknown",
        request.url.path,
        exc.detail,
    )
    response = JSONResponse(
        {"error": f"Rate limit exceeded: {exc.detail}"},
        status_code=429,
    )
    response.headers["Retry-After"] = str(60)
    return response


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler_with_logging)

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


# Well-known discovery endpoint must always return Access-Control-Allow-Origin: *
# regardless of CORS_ORIGINS setting, because browser extensions on any origin
# need to reach it. This middleware overrides the CORSMiddleware header for that
# single path.
from starlette.middleware.base import BaseHTTPMiddleware

class _WellKnownCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path == "/.well-known/sempkm":
            response.headers["access-control-allow-origin"] = "*"
            # Remove credentials header if present — can't combine with wildcard origin
            if "access-control-allow-credentials" in response.headers:
                del response.headers["access-control-allow-credentials"]
        return response

app.add_middleware(_WellKnownCORSMiddleware)

# ETag conditional GET middleware — added before TimingMiddleware so timing
# wraps ETag processing and captures total time including 304 responses.
app.add_middleware(ConditionalGetMiddleware)

# Timing middleware — added last so it wraps all other middleware and
# captures the total request processing time (outermost layer).
app.add_middleware(TimingMiddleware)

# Include routers (API routers first, then UI routers, shell router last)
app.include_router(monitoring_router)
app.include_router(well_known_router)
app.include_router(api_surface_router)
app.include_router(ai_router)
app.include_router(copilot_router)
app.include_router(auth_router)
app.include_router(setup_router)
app.include_router(commands_router)
app.include_router(health_router)
app.include_router(models_router)
app.include_router(sparql_router)
app.include_router(mirror_router)
app.include_router(lint_router)
app.include_router(inference_router)
app.include_router(admin_router)
app.include_router(timing_router)
app.include_router(views_router)
app.include_router(dashboard_browser_router)
app.include_router(dashboard_api_router)
app.include_router(workflow_browser_router)
app.include_router(workflow_api_router)
app.include_router(templates_api_router)
app.include_router(templates_browser_router)
app.include_router(persona_browser_router)
app.include_router(persona_api_router)
app.include_router(context_router)
app.include_router(context_rules_router)
app.include_router(context_zones_router)
app.include_router(notification_router)
app.include_router(vfs_browser_router)
app.include_router(vfs_mount_router)
app.include_router(app_commands_router)
app.include_router(indieauth_router)
app.include_router(indieauth_public_router)
app.include_router(federation_router)
app.include_router(webfinger_router)
app.include_router(inbox_router)
app.include_router(webid_router)
app.include_router(webid_public_router)
app.include_router(app_admin_router)
app.include_router(app_proxy_router)
app.include_router(browser_router)
app.include_router(obsidian_router)
app.include_router(notion_router)
app.include_router(rdf_import_router)
app.include_router(canvas_router)
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

# --- WebDAV VFS Mount ---
# wsgidav runs in a WSGI thread pool via a2wsgi. SyncTriplestoreClient uses
# httpx.Client (sync) because wsgidav cannot use async clients.
# Mounted at /dav -- nginx proxies /dav/ to this app with Authorization passthrough.
_sync_ts_client = SyncTriplestoreClient(
    base_url=settings.triplestore_url,
    repository_id=settings.repository_id,
)
_dav_provider = SemPKMDAVProvider(sync_client=_sync_ts_client)

_dav_config = {
    "provider_mapping": {"/": _dav_provider},
    "http_authenticator": {
        "domain_controller": SemPKMWsgiAuthenticator,
        "accept_basic": True,
        "accept_digest": False,
        "default_to_digest": False,
    },
    "sempkm_db_url": settings.database_url,
    "verbose": 0,
    "logging": {"enable_loggers": []},
    # PUT is now allowed (write path via body.set event store).
    # DELETE/MOVE/COPY/MKCOL are blocked at the ResourceFile/Collection level (HTTP 403).
}

_wsgi_dav_app = WsgiDAVApp(_dav_config)
_asgi_dav_app = WSGIMiddleware(_wsgi_dav_app)
app.mount("/dav", _asgi_dav_app)
