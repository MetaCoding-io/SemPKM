"""Health check endpoint for SemPKM API.

Health endpoint is intentionally public (no auth required) -- used by
Docker healthchecks and load balancers that cannot provide credentials.
"""

from fastapi import APIRouter, Depends

from app.config import settings
from app.dependencies import get_triplestore_client
from app.triplestore.client import TriplestoreClient

router = APIRouter(prefix="/api")


@router.get("/health")
async def health_check(
    client: TriplestoreClient = Depends(get_triplestore_client),
) -> dict:
    """Check API and triplestore health status.

    Returns:
        Health status with service details and API version.
    """
    triplestore_ok = await client.is_healthy()
    return {
        "status": "healthy" if triplestore_ok else "degraded",
        "services": {
            "api": "up",
            "triplestore": "up" if triplestore_ok else "down",
        },
        "version": settings.app_version,
    }
