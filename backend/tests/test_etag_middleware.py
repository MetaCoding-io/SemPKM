"""Tests for ConditionalGetMiddleware: ETag generation, 304 Not Modified
responses, path filtering, method filtering, streaming exclusion, large
response exclusion, and Cache-Control / Vary headers.
"""

import asyncio
import re
import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse

from app.middleware.etag import ConditionalGetMiddleware


# ---------------------------------------------------------------------------
# Test app factory
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with ConditionalGetMiddleware attached."""
    app = FastAPI()
    app.add_middleware(ConditionalGetMiddleware)

    @app.get("/api/test")
    async def api_test():
        return JSONResponse({"data": "hello"})

    @app.get("/api/test-dynamic")
    async def api_test_dynamic():
        return JSONResponse({"time": str(time.time())})

    @app.get("/browser/page")
    async def browser_page():
        return HTMLResponse("<html>page</html>")

    @app.post("/api/test")
    async def api_test_post():
        return JSONResponse({"created": True})

    @app.get("/api/stream")
    async def api_stream():
        async def generate():
            yield b'{"streaming": true}'

        return StreamingResponse(generate(), media_type="application/json")

    @app.get("/.well-known/sempkm")
    async def well_known():
        return JSONResponse({"version": "1.0"})

    return app


# ---------------------------------------------------------------------------
# ETag presence and format
# ---------------------------------------------------------------------------


class TestETagPresence:
    @pytest.mark.anyio
    async def test_etag_present_on_json_api_get(self):
        """GET /api/test should include an ETag header."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/test")
            assert resp.status_code == 200
            assert "etag" in resp.headers
            assert re.match(r'^W/"[0-9a-f]{16}"$', resp.headers["etag"])

    @pytest.mark.anyio
    async def test_etag_consistent_for_same_body(self):
        """Two identical GET requests produce the same ETag."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp1 = await client.get("/api/test")
            resp2 = await client.get("/api/test")
            assert resp1.headers["etag"] == resp2.headers["etag"]

    @pytest.mark.anyio
    async def test_etag_changes_when_body_changes(self):
        """Dynamic responses should produce different ETags."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp1 = await client.get("/api/test-dynamic")
            # Small delay to ensure time.time() changes
            await asyncio.sleep(0.01)
            resp2 = await client.get("/api/test-dynamic")
            assert resp1.headers["etag"] != resp2.headers["etag"]


# ---------------------------------------------------------------------------
# Conditional GET (304 Not Modified)
# ---------------------------------------------------------------------------


class TestConditionalGet:
    @pytest.mark.anyio
    async def test_304_on_matching_if_none_match(self):
        """If-None-Match with matching ETag returns 304."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp1 = await client.get("/api/test")
            etag = resp1.headers["etag"]

            resp2 = await client.get(
                "/api/test", headers={"If-None-Match": etag}
            )
            assert resp2.status_code == 304
            assert resp2.content == b""

    @pytest.mark.anyio
    async def test_200_on_mismatching_if_none_match(self):
        """If-None-Match with wrong ETag returns 200 with body."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/test", headers={"If-None-Match": 'W/"wrongwrongwrong0"'}
            )
            assert resp.status_code == 200
            assert resp.json() == {"data": "hello"}

    @pytest.mark.anyio
    async def test_304_on_if_none_match_wildcard(self):
        """If-None-Match: * returns 304 for any existing resource."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/test", headers={"If-None-Match": "*"}
            )
            assert resp.status_code == 304


# ---------------------------------------------------------------------------
# 304 response headers
# ---------------------------------------------------------------------------


class TestResponseHeaders:
    @pytest.mark.anyio
    async def test_304_has_etag_header(self):
        """304 response must include the ETag header."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp1 = await client.get("/api/test")
            etag = resp1.headers["etag"]

            resp2 = await client.get(
                "/api/test", headers={"If-None-Match": etag}
            )
            assert resp2.status_code == 304
            assert resp2.headers["etag"] == etag

    @pytest.mark.anyio
    async def test_304_has_cache_control(self):
        """304 response must include Cache-Control: no-cache."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp1 = await client.get("/api/test")
            etag = resp1.headers["etag"]

            resp2 = await client.get(
                "/api/test", headers={"If-None-Match": etag}
            )
            assert resp2.headers["cache-control"] == "no-cache"

    @pytest.mark.anyio
    async def test_304_has_vary_header(self):
        """304 response must include Vary: Accept, Authorization."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp1 = await client.get("/api/test")
            etag = resp1.headers["etag"]

            resp2 = await client.get(
                "/api/test", headers={"If-None-Match": etag}
            )
            assert resp2.headers["vary"] == "Accept, Authorization"

    @pytest.mark.anyio
    async def test_200_has_cache_control_no_cache(self):
        """200 response with ETag must have Cache-Control: no-cache."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/test")
            assert resp.headers["cache-control"] == "no-cache"

    @pytest.mark.anyio
    async def test_200_has_vary_header(self):
        """200 response with ETag must have Vary: Accept, Authorization."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/test")
            assert resp.headers["vary"] == "Accept, Authorization"


# ---------------------------------------------------------------------------
# Path and method exclusions
# ---------------------------------------------------------------------------


class TestExclusions:
    @pytest.mark.anyio
    async def test_non_api_path_excluded(self):
        """GET /browser/page (HTML) should not get an ETag."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/browser/page")
            assert resp.status_code == 200
            assert "etag" not in resp.headers

    @pytest.mark.anyio
    async def test_post_excluded(self):
        """POST /api/test should not get an ETag."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/test")
            assert resp.status_code == 200
            assert "etag" not in resp.headers

    @pytest.mark.anyio
    async def test_streaming_response_gets_etag_when_small(self):
        """GET /api/stream — BaseHTTPMiddleware buffers all responses, so
        even StreamingResponse gets an ETag if body is small enough.
        The isinstance(StreamingResponse) check is a safety net for
        non-BaseHTTPMiddleware usage; the 1MB body size limit is the
        real protection against unbounded streams."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/stream")
            assert resp.status_code == 200
            # Small streaming JSON gets an ETag because BaseHTTPMiddleware
            # buffers the body before our dispatch sees it.
            assert "etag" in resp.headers


# ---------------------------------------------------------------------------
# Well-known path inclusion
# ---------------------------------------------------------------------------


class TestWellKnownPath:
    @pytest.mark.anyio
    async def test_well_known_path_included(self):
        """GET /.well-known/sempkm should get an ETag."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/.well-known/sempkm")
            assert resp.status_code == 200
            assert "etag" in resp.headers
            assert re.match(r'^W/"[0-9a-f]{16}"$', resp.headers["etag"])

    @pytest.mark.anyio
    async def test_well_known_304_works(self):
        """Conditional GET on /.well-known/ path returns 304."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp1 = await client.get("/.well-known/sempkm")
            etag = resp1.headers["etag"]

            resp2 = await client.get(
                "/.well-known/sempkm", headers={"If-None-Match": etag}
            )
            assert resp2.status_code == 304
