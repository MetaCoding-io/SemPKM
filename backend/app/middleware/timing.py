"""Request timing middleware and admin report endpoint.

Measures request durations, logs slow requests, adds Server-Timing
headers, accumulates per-path timing statistics in memory, and exposes
a top-5 slowest endpoint report via an admin API.

Per-request SPARQL query timings are accumulated via a ContextVar and
serialized into the Server-Timing header as individual entries alongside
the total.

Delivers requirement PERF-08 (backend profiling).
"""

import logging
import time
from contextvars import ContextVar
from typing import Any

from fastapi import APIRouter, Depends, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.auth.dependencies import require_role

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory timing stats
# ---------------------------------------------------------------------------

_timing_stats: dict[str, list[float]] = {}
_MAX_SAMPLES_PER_PATH = 1000
_collection_start: float = time.monotonic()


def _record_timing(path: str, duration_ms: float) -> None:
    """Append a duration sample for *path*, trimming if over cap."""
    samples = _timing_stats.setdefault(path, [])
    samples.append(duration_ms)
    if len(samples) > _MAX_SAMPLES_PER_PATH:
        # Keep the most recent samples
        _timing_stats[path] = samples[-_MAX_SAMPLES_PER_PATH:]


def get_timing_report(top_n: int = 5) -> list[dict[str, Any]]:
    """Compute per-path timing stats sorted by avg_ms descending.

    Returns at most *top_n* entries, each containing:
      path, count, avg_ms, max_ms, min_ms, p50_ms, p95_ms, p99_ms, total_ms
    """
    report: list[dict[str, Any]] = []
    for path, durations in _timing_stats.items():
        if not durations:
            continue
        sorted_d = sorted(durations)
        count = len(sorted_d)
        total = sum(sorted_d)
        p50_idx = min(int(count * 0.50), count - 1)
        p95_idx = min(int(count * 0.95), count - 1)
        p99_idx = min(int(count * 0.99), count - 1)
        report.append(
            {
                "path": path,
                "count": count,
                "avg_ms": round(total / count, 2),
                "max_ms": round(sorted_d[-1], 2),
                "min_ms": round(sorted_d[0], 2),
                "p50_ms": round(sorted_d[p50_idx], 2),
                "p95_ms": round(sorted_d[p95_idx], 2),
                "p99_ms": round(sorted_d[p99_idx], 2),
                "total_ms": round(total, 2),
            }
        )
    report.sort(key=lambda r: r["avg_ms"], reverse=True)
    return report[:top_n]


def reset_timing_stats() -> None:
    """Clear all accumulated timing stats. Useful for test isolation."""
    global _collection_start
    _timing_stats.clear()
    _collection_start = time.monotonic()


# ---------------------------------------------------------------------------
# Per-request SPARQL timing accumulation (ContextVar)
# ---------------------------------------------------------------------------

_sparql_timings: ContextVar[list[tuple[str, float]] | None] = ContextVar(
    "_sparql_timings", default=None
)


def record_sparql_timing(name: str, duration_ms: float) -> None:
    """Record a SPARQL operation timing entry for the current request.

    No-op if the ContextVar has not been initialised for this request
    (i.e. the call originates outside an HTTP request context).
    """
    timings = _sparql_timings.get()
    if timings is not None:
        timings.append((name, duration_ms))


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

_SLOW_REQUEST_THRESHOLD_MS = 100.0


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware that times every request and adds Server-Timing header."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Initialise per-request SPARQL timing accumulator
        token = _sparql_timings.set([])
        try:
            start = time.monotonic()
            response = await call_next(request)
            duration_ms = (time.monotonic() - start) * 1000.0

            # Build Server-Timing header with per-query breakdown
            parts: list[str] = []
            sparql_entries = _sparql_timings.get() or []
            for idx, (name, dur) in enumerate(sparql_entries, start=1):
                parts.append(f"{name}.{idx};dur={dur:.2f}")
            parts.append(f"total;dur={duration_ms:.2f}")
            response.headers["Server-Timing"] = ", ".join(parts)

            path = request.url.path
            method = request.method
            status_code = response.status_code

            # Log request timing
            logger.debug(
                "%s %s %s %.1fms", method, path, status_code, duration_ms
            )
            if duration_ms > _SLOW_REQUEST_THRESHOLD_MS:
                logger.info(
                    "Slow request: %s %s %s %.1fms",
                    method,
                    path,
                    status_code,
                    duration_ms,
                )

            # Accumulate stats
            _record_timing(path, duration_ms)

            return response
        finally:
            _sparql_timings.reset(token)


# ---------------------------------------------------------------------------
# Admin API router
# ---------------------------------------------------------------------------

timing_router = APIRouter(prefix="/api/admin", tags=["admin"])


@timing_router.get(
    "/timing-report",
    dependencies=[Depends(require_role("owner"))],
)
async def timing_report() -> dict[str, Any]:
    """Return top-N slowest endpoint timing statistics.

    Requires owner role. Returns JSON with top_endpoints list,
    total_requests count, and approximate collection_period_seconds.
    """
    report = get_timing_report()
    total_requests = sum(len(v) for v in _timing_stats.values())
    collection_seconds = time.monotonic() - _collection_start

    return {
        "top_endpoints": report,
        "total_requests": total_requests,
        "collection_period_seconds": round(collection_seconds, 2),
    }
