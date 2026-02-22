"""SemPKM FastAPI application with lifespan management."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from jinja2_fragments.fastapi import Jinja2Blocks

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.auth.service import AuthService
from app.auth.tokens import load_or_create_setup_token
from app.config import settings
from app.commands.router import router as commands_router
from app.db.base import Base
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
from app.sparql.router import router as sparql_router
from app.triplestore.client import TriplestoreClient
from app.triplestore.setup import ensure_repository
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

    validation_queue = AsyncValidationQueue(validation_service)
    app.state.validation_queue = validation_queue
    await validation_queue.start()

    # Create ShapesService for SHACL shape extraction (form generation)
    shapes_service = ShapesService(client)
    app.state.shapes_service = shapes_service

    # Create WebhookService for outbound event notifications
    webhook_service = WebhookService(client)
    app.state.webhook_service = webhook_service

    # --- SQL Database Initialization ---
    sql_engine = create_engine()

    # Create all tables (safe for existing tables -- uses IF NOT EXISTS)
    # Note: app.auth.models is already imported at module level via auth imports
    async with sql_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("SQL database tables created/verified")

    # Store session factory on app state for dependencies
    app.state.async_session_factory = async_session_factory

    # Create AuthService and store on app state
    auth_service = AuthService(async_session_factory)
    app.state.auth_service = auth_service

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

    # Shutdown: stop validation queue, dispose SQL engine, close triplestore client
    await validation_queue.stop()
    await sql_engine.dispose()
    await client.close()
    logger.info("SemPKM API shut down")


app = FastAPI(
    title="SemPKM API",
    version=settings.app_version,
    lifespan=lifespan,
)

# Jinja2 template engine with block-level rendering for htmx partials
templates = Jinja2Blocks(directory=Path(__file__).parent / "templates")
app.state.templates = templates

# CORS middleware for dev console access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (API routers first, admin before shell, shell router last)
app.include_router(auth_router)
app.include_router(commands_router)
app.include_router(health_router)
app.include_router(models_router)
app.include_router(sparql_router)
app.include_router(validation_router)
app.include_router(admin_router)
app.include_router(shell_router)
