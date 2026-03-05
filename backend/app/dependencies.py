"""FastAPI dependency injection for shared services."""

from fastapi import Request

from app.auth.service import AuthService
from app.events.store import EventStore
from app.lint.broadcast import LintBroadcast
from app.lint.service import LintService
from app.services.labels import LabelService
from app.services.models import ModelService
from app.services.prefixes import PrefixRegistry
from app.services.search import SearchService
from app.services.shapes import ShapesService
from app.services.validation import ValidationService
from app.services.webhooks import WebhookService
from app.triplestore.client import TriplestoreClient
from app.validation.queue import AsyncValidationQueue
from app.views.service import ViewSpecService


async def get_triplestore_client(request: Request) -> TriplestoreClient:
    """Get the TriplestoreClient instance from app state.

    The client is created during app lifespan startup and stored on
    app.state.triplestore_client.
    """
    return request.app.state.triplestore_client


async def get_prefix_registry(request: Request) -> PrefixRegistry:
    """Get the PrefixRegistry instance from app state.

    The registry is created during app lifespan startup and stored on
    app.state.prefix_registry.
    """
    return request.app.state.prefix_registry


async def get_label_service(request: Request) -> LabelService:
    """Get the LabelService instance from app state.

    The service is created during app lifespan startup and stored on
    app.state.label_service.
    """
    return request.app.state.label_service


async def get_validation_queue(request: Request) -> AsyncValidationQueue:
    """Get the AsyncValidationQueue instance from app state.

    The queue is created during app lifespan startup and stored on
    app.state.validation_queue.
    """
    return request.app.state.validation_queue


async def get_validation_service(request: Request) -> ValidationService:
    """Get the ValidationService instance from app state.

    The service is created during app lifespan startup and stored on
    app.state.validation_service.
    """
    return request.app.state.validation_service


async def get_model_service(request: Request) -> ModelService:
    """Get the ModelService instance from app state.

    The service is created during app lifespan startup and stored on
    app.state.model_service.
    """
    return request.app.state.model_service


async def get_shapes_service(request: Request) -> ShapesService:
    """Get the ShapesService instance from app state.

    The service is created during app lifespan startup and stored on
    app.state.shapes_service.
    """
    return request.app.state.shapes_service


async def get_webhook_service(request: Request) -> WebhookService:
    """Get the WebhookService instance from app state.

    The service is created during app lifespan startup and stored on
    app.state.webhook_service.
    """
    return request.app.state.webhook_service


async def get_auth_service(request: Request) -> AuthService:
    """Get the AuthService instance from app state.

    The service is created during app lifespan startup and stored on
    app.state.auth_service.
    """
    return request.app.state.auth_service


async def get_view_spec_service(request: Request) -> ViewSpecService:
    """Get the ViewSpecService instance from app state.

    The service is created during app lifespan startup and stored on
    app.state.view_spec_service.
    """
    return request.app.state.view_spec_service


async def get_event_store(request: Request) -> EventStore:
    """Get the EventStore instance from app state.

    The store is created during app lifespan startup and stored on
    app.state.event_store.
    """
    return request.app.state.event_store


async def get_search_service(request: Request) -> SearchService:
    """Get the SearchService instance from app state.

    The service is created during app lifespan startup and stored on
    app.state.search_service.
    """
    return request.app.state.search_service


async def get_lint_service(request: Request) -> LintService:
    """Get the LintService instance from app state.

    The service is created during app lifespan startup and stored on
    app.state.lint_service.
    """
    return request.app.state.lint_service


async def get_lint_broadcast(request: Request) -> LintBroadcast:
    """Get the LintBroadcast instance from app state.

    The broadcast manager is created during app lifespan startup and
    stored on app.state.lint_broadcast.
    """
    return request.app.state.lint_broadcast
