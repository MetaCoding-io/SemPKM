"""Tests for Server-Timing header with per-query SPARQL breakdown.

Validates:
- Server-Timing header always contains total;dur=
- Per-query sparql.*.N entries appear when record_sparql_timing is called
- ContextVar is properly reset between requests (no cross-request leaking)
- record_sparql_timing is a no-op outside request context
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.middleware.timing import (
    TimingMiddleware,
    _sparql_timings,
    record_sparql_timing,
    reset_timing_stats,
)


# ---------------------------------------------------------------------------
# Test app factory
# ---------------------------------------------------------------------------


def _make_app(handler=None):
    """Create a minimal Starlette app with TimingMiddleware."""

    async def default_handler(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(
        routes=[
            Route("/", handler or default_handler),
            Route("/other", handler or default_handler),
        ],
    )
    app.add_middleware(TimingMiddleware)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_timing_has_total():
    """Baseline: Server-Timing header always contains total;dur=."""
    app = _make_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    st = resp.headers.get("server-timing", "")
    assert "total;dur=" in st


@pytest.mark.asyncio
async def test_server_timing_includes_sparql_entries():
    """When SPARQL timings are recorded, they appear as numbered entries."""

    async def handler_with_sparql(request: Request) -> PlainTextResponse:
        record_sparql_timing("sparql.query", 12.34)
        record_sparql_timing("sparql.construct", 5.67)
        return PlainTextResponse("ok")

    app = _make_app(handler_with_sparql)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")

    st = resp.headers["server-timing"]
    # Should contain two sparql entries plus total
    assert "sparql.query.1;dur=12.34" in st
    assert "sparql.construct.2;dur=5.67" in st
    assert "total;dur=" in st


@pytest.mark.asyncio
async def test_sparql_timing_entries_are_ordered():
    """Entries use 1-based incrementing index matching call order."""

    async def handler(request: Request) -> PlainTextResponse:
        record_sparql_timing("sparql.query", 1.0)
        record_sparql_timing("sparql.query", 2.0)
        record_sparql_timing("sparql.update", 3.0)
        return PlainTextResponse("ok")

    app = _make_app(handler)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")

    st = resp.headers["server-timing"]
    assert "sparql.query.1;dur=1.00" in st
    assert "sparql.query.2;dur=2.00" in st
    assert "sparql.update.3;dur=3.00" in st


@pytest.mark.asyncio
async def test_contextvar_no_leaking_between_requests():
    """ContextVar is reset per-request; timings from request 1 don't appear in request 2."""
    call_count = 0

    async def handler(request: Request) -> PlainTextResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            record_sparql_timing("sparql.query", 99.99)
        # Second request records nothing
        return PlainTextResponse("ok")

    app = _make_app(handler)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp1 = await client.get("/")
        resp2 = await client.get("/")

    # First request should have the entry
    st1 = resp1.headers["server-timing"]
    assert "sparql.query.1;dur=99.99" in st1

    # Second request should NOT have any sparql entries
    st2 = resp2.headers["server-timing"]
    assert "sparql.query" not in st2
    assert "total;dur=" in st2


@pytest.mark.asyncio
async def test_contextvar_reset_on_exception():
    """ContextVar is reset even if the handler raises an exception."""

    async def bad_handler(request: Request) -> PlainTextResponse:
        record_sparql_timing("sparql.query", 10.0)
        raise RuntimeError("boom")

    app = _make_app(bad_handler)
    # The middleware will let the exception propagate, but the finally
    # block should still reset the ContextVar.
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        resp = await client.get("/")

    # After the erroring request, the ContextVar should be None
    assert _sparql_timings.get() is None


def test_record_sparql_timing_noop_outside_request():
    """record_sparql_timing is a no-op when ContextVar is not set (None default)."""
    # Ensure the ContextVar is at its default (None)
    assert _sparql_timings.get() is None
    # Should not raise
    record_sparql_timing("sparql.query", 42.0)
    # Still None — nothing was accumulated
    assert _sparql_timings.get() is None


@pytest.mark.asyncio
async def test_no_sparql_entries_when_none_recorded():
    """When no SPARQL timings are recorded, only total appears."""
    app = _make_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")

    st = resp.headers["server-timing"]
    # Only total, no sparql entries
    assert st.startswith("total;dur=")
    assert "sparql" not in st


@pytest.fixture(autouse=True)
def _reset_stats():
    """Reset timing stats before each test."""
    reset_timing_stats()
    yield
    reset_timing_stats()
