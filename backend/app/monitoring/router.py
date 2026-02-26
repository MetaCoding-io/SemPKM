"""Public endpoint exposing PostHog configuration for the frontend.

Returns the PostHog enabled flag, project API key, and host so the
frontend JS can initialize the PostHog SDK without hard-coding values.
The project API key is safe to expose publicly — it is a write-only
ingestion key with no read access.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


class PostHogConfig(BaseModel):
    enabled: bool
    api_key: str
    host: str


@router.get("/config", response_model=PostHogConfig)
async def get_posthog_config() -> PostHogConfig:
    """Return PostHog configuration for frontend initialization."""
    return PostHogConfig(
        enabled=settings.posthog_enabled and bool(settings.posthog_api_key),
        api_key=settings.posthog_api_key if settings.posthog_enabled else "",
        host=settings.posthog_host,
    )
