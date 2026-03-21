"""Tests for AppProxy — HTTP forwarding to app subprocesses over UDS.

Covers:
- ``forward()`` preserves query strings in the target URL
- ``forward()`` works without query strings (baseline)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.apps.proxy import AppProxy


# ── Helpers ──


def _make_mock_request(
    method: str = "GET",
    headers: dict | None = None,
    body: bytes = b"",
    query: str = "",
    path: str = "test-app/_fragments/article-list",
) -> MagicMock:
    """Build a mock Starlette Request with URL query support."""
    req = MagicMock()
    req.method = method
    req.headers = headers or {"host": "localhost", "accept": "text/html"}
    req.body = AsyncMock(return_value=body)

    # Starlette URL object
    url = MagicMock()
    url.query = query
    req.url = url

    return req


def _make_upstream_response(
    status_code: int = 200,
    content: bytes = b"<div>OK</div>",
    headers: dict | None = None,
) -> httpx.Response:
    """Build a real httpx.Response for the mock client to return."""
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=headers or {"content-type": "text/html"},
    )


# ── Tests ──


@pytest.mark.asyncio
async def test_forward_preserves_query_string(tmp_path):
    """Query params like ?feed_iri=... must survive proxy forwarding."""
    # Arrange
    socket_path = tmp_path / "sempkm-app-test.sock"
    socket_path.touch()  # Must exist for the check

    manager = MagicMock()
    manager.get_token.return_value = "fake-jwt"

    proxy = AppProxy(manager)

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(
        return_value=_make_upstream_response()
    )
    proxy._clients["test-app"] = mock_client

    request = _make_mock_request(query="feed_iri=urn%3Afeed%3A1&page=2")

    # Act
    with patch.object(Path, "exists", return_value=True):
        await proxy.forward(
            app_id="test-app",
            path="_fragments/article-list",
            request=request,
        )

    # Assert — the URL passed to httpx must include the query string
    call_kwargs = mock_client.request.call_args
    actual_url = call_kwargs.kwargs.get("url") or call_kwargs[1].get("url")
    assert "?" in actual_url, f"Query string missing from URL: {actual_url}"
    assert "feed_iri=urn%3Afeed%3A1" in actual_url
    assert "page=2" in actual_url


@pytest.mark.asyncio
async def test_forward_no_query_string(tmp_path):
    """Baseline: requests without query params should not get a trailing '?'."""
    socket_path = tmp_path / "sempkm-app-test.sock"
    socket_path.touch()

    manager = MagicMock()
    manager.get_token.return_value = "fake-jwt"

    proxy = AppProxy(manager)

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(
        return_value=_make_upstream_response()
    )
    proxy._clients["test-app"] = mock_client

    request = _make_mock_request(query="")

    with patch.object(Path, "exists", return_value=True):
        await proxy.forward(
            app_id="test-app",
            path="_fragments/feed-sidebar",
            request=request,
        )

    call_kwargs = mock_client.request.call_args
    actual_url = call_kwargs.kwargs.get("url") or call_kwargs[1].get("url")
    assert "?" not in actual_url, f"Unexpected query string in URL: {actual_url}"
    assert actual_url == "http://localhost/_fragments/feed-sidebar"


@pytest.mark.asyncio
async def test_forward_injects_app_token(tmp_path):
    """App token should be injected as x-sempkm-app-token header."""
    socket_path = tmp_path / "sempkm-app-test.sock"
    socket_path.touch()

    manager = MagicMock()
    manager.get_token.return_value = "test-token-123"

    proxy = AppProxy(manager)

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(
        return_value=_make_upstream_response()
    )
    proxy._clients["myapp"] = mock_client

    request = _make_mock_request(query="")

    with patch.object(Path, "exists", return_value=True):
        await proxy.forward(
            app_id="myapp",
            path="some/path",
            request=request,
        )

    call_kwargs = mock_client.request.call_args
    actual_headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
    assert actual_headers["x-sempkm-app-token"] == "test-token-123"
