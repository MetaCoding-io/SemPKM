"""Regression tests for AppProxy query-parameter forwarding.

The proxy must append the incoming request's query string to the URL
sent to the app subprocess over UDS.  Prior to the fix, query params
were silently dropped — breaking OAuth callbacks and any endpoint that
relies on query parameters.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.apps.proxy import AppProxy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(path: str = "callback", query: str = "", method: str = "GET") -> MagicMock:
    """Build a minimal FastAPI Request mock with the given path and query."""
    req = MagicMock()
    req.method = method

    # Starlette's URL exposes .query as a string (without leading ?)
    url = MagicMock()
    url.query = query
    req.url = url

    req.headers = MagicMock()
    req.headers.__iter__ = lambda self: iter([])
    req.headers.items = lambda: []
    # dict(request.headers) needs to work
    req.headers.__class__ = dict
    # Simplify: just make dict() on it return an empty dict
    req.headers = {}

    req.body = AsyncMock(return_value=b"")
    return req


class CaptureClient:
    """Replaces httpx.AsyncClient to capture the URL passed to .request()."""

    def __init__(self) -> None:
        self.captured_url: str | None = None
        self.captured_method: str | None = None
        self.captured_kwargs: dict[str, Any] = {}

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        self.captured_method = method
        self.captured_url = url
        self.captured_kwargs = kwargs
        return httpx.Response(200, content=b"ok")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestProxyQueryParamForwarding:
    """Verify that query parameters are forwarded to the upstream app."""

    @pytest.fixture
    def proxy_and_capture(self, tmp_path: Path):
        """Set up an AppProxy with a fake socket and capture client."""
        manager = MagicMock()
        manager.get_token.return_value = "test-token"
        proxy = AppProxy(manager)

        # Create a fake socket file so the existence check passes
        sock = tmp_path / "sempkm-app-test.sock"
        sock.touch()

        capture = CaptureClient()
        # Pre-populate the client cache so _get_or_create_client is bypassed
        proxy._clients["test-app"] = capture

        return proxy, capture, sock

    @pytest.mark.asyncio
    async def test_query_params_forwarded(self, proxy_and_capture, tmp_path):
        """OAuth callback query string (code, state) must reach the upstream."""
        proxy, capture, sock = proxy_and_capture

        with patch("app.apps.proxy.Path") as MockPath:
            MockPath.return_value = sock

            req = _make_request(
                path="callback",
                query="code=auth_code_123&state=csrf_token",
            )
            await proxy.forward("test-app", "callback", req)

        assert capture.captured_url == "http://localhost/callback?code=auth_code_123&state=csrf_token"

    @pytest.mark.asyncio
    async def test_no_query_params_no_question_mark(self, proxy_and_capture, tmp_path):
        """When there's no query string, the URL should not end with '?'."""
        proxy, capture, sock = proxy_and_capture

        with patch("app.apps.proxy.Path") as MockPath:
            MockPath.return_value = sock

            req = _make_request(path="settings", query="")
            await proxy.forward("test-app", "settings", req)

        assert capture.captured_url == "http://localhost/settings"
        assert "?" not in capture.captured_url

    @pytest.mark.asyncio
    async def test_single_query_param(self, proxy_and_capture, tmp_path):
        """Single parameter is forwarded correctly."""
        proxy, capture, sock = proxy_and_capture

        with patch("app.apps.proxy.Path") as MockPath:
            MockPath.return_value = sock

            req = _make_request(path="search", query="q=hello+world")
            await proxy.forward("test-app", "search", req)

        assert capture.captured_url == "http://localhost/search?q=hello+world"

    @pytest.mark.asyncio
    async def test_post_with_query_params(self, proxy_and_capture, tmp_path):
        """POST requests also forward query parameters."""
        proxy, capture, sock = proxy_and_capture

        with patch("app.apps.proxy.Path") as MockPath:
            MockPath.return_value = sock

            req = _make_request(
                path="webhook",
                query="verify=true",
                method="POST",
            )
            await proxy.forward("test-app", "webhook", req)

        assert capture.captured_method == "POST"
        assert capture.captured_url == "http://localhost/webhook?verify=true"

    @pytest.mark.asyncio
    async def test_encoded_query_params_preserved(self, proxy_and_capture, tmp_path):
        """URL-encoded characters in query string pass through unchanged."""
        proxy, capture, sock = proxy_and_capture

        with patch("app.apps.proxy.Path") as MockPath:
            MockPath.return_value = sock

            req = _make_request(
                path="callback",
                query="redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcb&scope=read%2Cwrite",
            )
            await proxy.forward("test-app", "callback", req)

        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcb" in capture.captured_url
        assert "scope=read%2Cwrite" in capture.captured_url
