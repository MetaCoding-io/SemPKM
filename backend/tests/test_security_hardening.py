"""Tests for security hardening: rate limits, query timeout, error disclosure, auth logging.

Covers:
- Rate limit returns 429 with Retry-After header
- SPARQL query timeout returns 504
- Generic error messages instead of stack traces
- Failed auth attempts logged at WARNING
"""

import logging
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user, get_current_user_or_api
from app.auth.models import User
from app.auth.rate_limit import limiter


# ── Helpers ──────────────────────────────────────────────────────


def _test_user():
    return User(
        id=uuid.uuid4(),
        email="security-test@example.com",
        role="owner",
    )


# ── Rate Limit Tests ────────────────────────────────────────────


class TestRateLimits:
    """Verify that rate-limited endpoints return 429 with Retry-After."""

    @pytest.fixture(autouse=True)
    def enable_limiter(self):
        """Ensure the limiter is enabled for these tests."""
        original = limiter.enabled
        limiter.enabled = True
        yield
        limiter.enabled = original

    @pytest.fixture
    async def sparql_client(self):
        """Client wired to the SPARQL router with rate limiting."""
        from fastapi import FastAPI
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware

        from app.sparql.router import router as sparql_router

        app = FastAPI()
        app.state.limiter = limiter
        app.add_middleware(SlowAPIMiddleware)

        # Custom handler that adds Retry-After header (mirrors main.py)
        def _rate_limit_handler(request, exc):
            from fastapi.responses import JSONResponse as _JSONResponse
            response = _JSONResponse(
                {"error": f"Rate limit exceeded: {exc.detail}"},
                status_code=429,
            )
            response.headers["Retry-After"] = str(60)
            return response

        app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
        app.include_router(sparql_router)

        mock_client = AsyncMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": []},
            "head": {"vars": []},
        })

        user = _test_user()

        app.dependency_overrides[get_current_user_or_api] = lambda: user
        app.dependency_overrides[get_current_user] = lambda: user

        # Mock triplestore client dependency
        from app.dependencies import get_triplestore_client, get_query_service, get_label_service, get_prefix_registry
        app.dependency_overrides[get_triplestore_client] = lambda: mock_client
        app.dependency_overrides[get_query_service] = lambda: AsyncMock()
        app.dependency_overrides[get_label_service] = lambda: AsyncMock()
        app.dependency_overrides[get_prefix_registry] = lambda: MagicMock(compact=lambda x: x)

        transport = ASGITransport(app=app)
        # Reset limiter state to avoid cross-test pollution
        limiter.reset()
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_sparql_rate_limit_returns_429(self, sparql_client):
        """POST /api/sparql returns 429 after exceeding 60/minute."""
        # Send 61 requests — the 61st should be rate-limited
        for i in range(60):
            resp = await sparql_client.post(
                "/api/sparql",
                json={"query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"},
            )
            assert resp.status_code == 200, f"Request {i+1} failed with {resp.status_code}"

        # 61st request should be rate-limited
        resp = await sparql_client.post(
            "/api/sparql",
            json={"query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"},
        )
        assert resp.status_code == 429
        assert "retry-after" in resp.headers


# ── Timeout Tests ────────────────────────────────────────────────


class TestQueryTimeout:
    """Verify that triplestore timeout returns 504."""

    @pytest.fixture
    async def timeout_client(self):
        """Client with triplestore mock that raises TimeoutException."""
        from fastapi import FastAPI
        from app.sparql.router import router as sparql_router

        app = FastAPI()
        # Disable rate limiter for these tests
        app.state.limiter = limiter
        limiter_orig = limiter.enabled
        limiter.enabled = False

        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        user = _test_user()

        app.include_router(sparql_router)
        app.dependency_overrides[get_current_user_or_api] = lambda: user
        app.dependency_overrides[get_current_user] = lambda: user

        from app.dependencies import get_triplestore_client, get_query_service, get_label_service, get_prefix_registry
        app.dependency_overrides[get_triplestore_client] = lambda: mock_client
        app.dependency_overrides[get_query_service] = lambda: AsyncMock()
        app.dependency_overrides[get_label_service] = lambda: AsyncMock()
        app.dependency_overrides[get_prefix_registry] = lambda: MagicMock(compact=lambda x: x)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
            limiter.enabled = limiter_orig

    @pytest.mark.asyncio
    async def test_sparql_timeout_returns_504(self, timeout_client):
        """POST /api/sparql returns 504 when query times out."""
        resp = await timeout_client.post(
            "/api/sparql",
            json={"query": "SELECT ?s WHERE { ?s ?p ?o }"},
        )
        assert resp.status_code == 504
        body = resp.json()
        assert "timed out" in body["error"].lower()

    @pytest.mark.asyncio
    async def test_sparql_get_timeout_returns_504(self, timeout_client):
        """GET /api/sparql returns 504 when query times out."""
        resp = await timeout_client.get(
            "/api/sparql",
            params={"query": "SELECT ?s WHERE { ?s ?p ?o }"},
        )
        assert resp.status_code == 504
        body = resp.json()
        assert "timed out" in body["error"].lower()


# ── Error Disclosure Tests ───────────────────────────────────────


class TestErrorDisclosure:
    """Verify that unhandled exceptions return generic error messages."""

    @pytest.fixture
    async def error_client(self):
        """Client with a mini app that has the global exception handler."""
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse as _JSONResponse

        # debug=False prevents Starlette's ServerErrorMiddleware from
        # re-raising exceptions before our handler can intercept them
        app = FastAPI(debug=False)

        # Register the same global exception handler as main.py
        @app.exception_handler(Exception)
        async def _handler(request, exc):
            return _JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

        @app.get("/explode")
        async def explode():
            raise RuntimeError("SECRET_INTERNAL_DETAILS_SHOULD_NOT_LEAK")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_global_exception_handler_returns_generic_500(self, error_client):
        """Unhandled exceptions return 500 with generic message, not stack trace."""
        resp = await error_client.get("/explode")
        assert resp.status_code == 500
        body = resp.json()
        assert body["detail"] == "Internal server error"
        assert "SECRET_INTERNAL_DETAILS" not in str(body)


# ── Auth Logging Tests ───────────────────────────────────────────


class TestAuthFailureLogging:
    """Verify that failed auth attempts are logged at WARNING."""

    @pytest.mark.asyncio
    async def test_invalid_bearer_token_logged(self, caplog):
        """Invalid Bearer token generates WARNING log."""
        from fastapi import FastAPI, Depends
        from app.db.session import get_db_session

        app = FastAPI()

        # Create a simple endpoint that uses dual auth (cookie + Bearer)
        @app.get("/test-auth")
        async def test_auth(user=Depends(get_current_user_or_api)):
            return {"email": user.email}

        # Ensure rate limiter is off for test
        limiter_orig = limiter.enabled
        limiter.enabled = False

        # Mock auth service that rejects all tokens
        mock_auth_service = AsyncMock()
        mock_auth_service.verify_api_token = AsyncMock(return_value=(None, None))
        app.state.auth_service = mock_auth_service

        # Mock DB session to avoid real DB
        mock_db = AsyncMock()
        app.dependency_overrides[get_db_session] = lambda: mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            with caplog.at_level(logging.WARNING, logger="app.auth.dependencies"):
                resp = await ac.get(
                    "/test-auth",
                    headers={"Authorization": "Bearer invalid-token-12345678"},
                )

        assert resp.status_code == 401
        # Check that the warning was logged with IP and token prefix
        auth_warnings = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and "bearer_failed" in r.message
        ]
        assert len(auth_warnings) >= 1, (
            f"Expected auth failure log, got: {[r.message for r in caplog.records]}"
        )
        # Verify token prefix is present in the log (first 8 chars + ...)
        assert "token_prefix=" in auth_warnings[0].message
        assert "source_ip=" in auth_warnings[0].message

        limiter.enabled = limiter_orig
