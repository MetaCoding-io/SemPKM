"""FastAPI dependency injection for shared services."""

from fastapi import Request

from app.triplestore.client import TriplestoreClient


async def get_triplestore_client(request: Request) -> TriplestoreClient:
    """Get the TriplestoreClient instance from app state.

    The client is created during app lifespan startup and stored on
    app.state.triplestore_client.
    """
    return request.app.state.triplestore_client
