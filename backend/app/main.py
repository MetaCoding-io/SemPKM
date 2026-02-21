"""SemPKM FastAPI application with lifespan management."""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.commands.router import router as commands_router
from app.health.router import router as health_router
from app.services.labels import LabelService
from app.services.prefixes import PrefixRegistry
from app.services.validation import ValidationService, empty_shapes_loader
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

    # Create validation service and async queue
    validation_service = ValidationService(client, empty_shapes_loader)
    app.state.validation_service = validation_service

    validation_queue = AsyncValidationQueue(validation_service)
    app.state.validation_queue = validation_queue
    await validation_queue.start()

    logger.info("SemPKM API started successfully")
    yield

    # Shutdown: stop validation queue, then close the triplestore client
    await validation_queue.stop()
    await client.close()
    logger.info("SemPKM API shut down")


app = FastAPI(
    title="SemPKM API",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware for dev console access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(commands_router)
app.include_router(health_router)
app.include_router(sparql_router)
app.include_router(validation_router)
