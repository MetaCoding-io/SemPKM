"""Rate limiting configuration for auth endpoints.

Uses slowapi with in-memory storage (no Redis) and per-IP keying
via X-Forwarded-For (nginx already forwards this header).

The Limiter instance is shared between router.py (decorators)
and main.py (middleware + state registration).

Set RATE_LIMIT_ENABLED=false to disable rate limiting entirely
(useful for E2E test environments where auth fixtures rapidly
create sessions).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
)
