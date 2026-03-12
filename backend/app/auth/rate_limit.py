"""Rate limiting configuration for auth endpoints.

Uses slowapi with in-memory storage (no Redis) and per-IP keying
via X-Forwarded-For (nginx already forwards this header).

The Limiter instance is shared between router.py (decorators)
and main.py (middleware + state registration).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
