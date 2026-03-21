"""Tests for AI router: LLM streaming proxy and status endpoint.

Covers:
- GET /api/llm/status: returns available/unavailable, requires auth
- POST /api/llm/stream: SSE proxy, error when not configured, auth checks
- Both endpoints accept Bearer token and session cookie (dual-auth)
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.ai import ai_router
from app.auth.models import ApiToken, User, UserSession
from app.auth.service import AuthService
from app.db.base import Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def db_session(db_session_factory):
    async with db_session_factory() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(id=uuid.uuid4(), email="test@example.com", role="owner")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def valid_session(db_session: AsyncSession, test_user: User) -> UserSession:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
    session = UserSession(token=token, user_id=test_user.id, expires_at=expires_at)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture
async def valid_api_token(db_session: AsyncSession, test_user: User) -> str:
    plaintext = secrets.token_hex(32)
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    api_token = ApiToken(user_id=test_user.id, name="test-token", token_hash=token_hash)
    db_session.add(api_token)
    await db_session.commit()
    return plaintext


def _build_ai_app(db_session_factory) -> FastAPI:
    """Build a minimal FastAPI app with the AI router and auth service."""
    from app.db.session import get_db_session

    app = FastAPI()
    app.state.auth_service = AuthService(db_session_factory)
    app.include_router(ai_router)

    # Override the DB session dependency to use our test session factory
    async def _test_db_session():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _test_db_session
    return app


# ---------------------------------------------------------------------------
# GET /api/llm/status tests
# ---------------------------------------------------------------------------


class TestLLMStatusRequiresAuth:
    """GET /api/llm/status returns 401 without credentials."""

    async def test_llm_status_returns_401_without_auth(self, db_session_factory):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/llm/status")
        assert resp.status_code == 401


class TestLLMStatusUnavailable:
    """GET /api/llm/status returns unavailable when LLM not configured."""

    async def test_llm_status_returns_unavailable_when_not_configured(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)
        mock_config = {"api_base_url": "", "api_key_set": False, "default_model": ""}

        with patch(
            "app.api.ai.LLMConfigService.get_config",
            new_callable=AsyncMock,
            return_value=mock_config,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/llm/status",
                    headers={"Authorization": f"Bearer {valid_api_token}"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False
        assert data["provider"] is None


class TestLLMStatusAvailable:
    """GET /api/llm/status returns available with configured LLM."""

    async def test_llm_status_returns_available_with_config(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)
        mock_config = {
            "api_base_url": "https://api.openai.com",
            "api_key_set": True,
            "default_model": "gpt-4o",
        }

        with patch(
            "app.api.ai.LLMConfigService.get_config",
            new_callable=AsyncMock,
            return_value=mock_config,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/llm/status",
                    headers={"Authorization": f"Bearer {valid_api_token}"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["provider"] == "api.openai.com"


# ---------------------------------------------------------------------------
# POST /api/llm/stream tests
# ---------------------------------------------------------------------------


class TestLLMStreamRequiresAuth:
    """POST /api/llm/stream returns 401 without credentials."""

    async def test_llm_stream_returns_401_without_auth(self, db_session_factory):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/llm/stream",
                json={"messages": [{"role": "user", "content": "hi"}]},
            )
        assert resp.status_code == 401


class TestLLMStreamNotConfigured:
    """POST /api/llm/stream returns SSE error when LLM not configured."""

    async def test_llm_stream_returns_error_when_not_configured(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)
        mock_config = {"api_base_url": "", "api_key_set": False, "default_model": ""}

        with patch(
            "app.api.ai.LLMConfigService.get_config",
            new_callable=AsyncMock,
            return_value=mock_config,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/llm/stream",
                    json={"messages": [{"role": "user", "content": "hi"}]},
                    headers={"Authorization": f"Bearer {valid_api_token}"},
                )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers.get("x-accel-buffering") == "no"
        body = resp.text
        assert '"error": "LLM not configured"' in body
        assert "[DONE]" in body


class TestLLMStreamAcceptsBearerToken:
    """POST /api/llm/stream works with Bearer auth and proxies SSE data."""

    async def test_llm_stream_accepts_bearer_token(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)
        mock_config = {
            "api_base_url": "https://api.openai.com",
            "api_key_set": True,
            "default_model": "gpt-4o",
        }

        # Mock the httpx streaming response
        mock_response = AsyncMock()
        mock_response.aiter_lines = self._fake_sse_lines
        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = lambda *a, **kw: mock_stream_ctx
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "app.api.ai.LLMConfigService.get_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "app.api.ai.LLMConfigService.get_decrypted_api_key",
                new_callable=AsyncMock,
                return_value="sk-test-key",
            ),
            patch("app.api.ai.httpx.AsyncClient", return_value=mock_client_ctx),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/llm/stream",
                    json={"messages": [{"role": "user", "content": "hello"}]},
                    headers={"Authorization": f"Bearer {valid_api_token}"},
                )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers.get("x-accel-buffering") == "no"
        body = resp.text
        assert "test content" in body

    @staticmethod
    async def _fake_sse_lines():
        yield 'data: {"choices":[{"delta":{"content":"test content"}}]}'
        yield "data: [DONE]"


class TestLLMStreamAcceptsCookieAuth:
    """POST /api/llm/stream works with cookie auth."""

    async def test_llm_stream_accepts_cookie_auth(
        self, db_session_factory, test_user, valid_session
    ):
        app = _build_ai_app(db_session_factory)
        mock_config = {"api_base_url": "", "api_key_set": False, "default_model": ""}

        with patch(
            "app.api.ai.LLMConfigService.get_config",
            new_callable=AsyncMock,
            return_value=mock_config,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/llm/stream",
                    json={"messages": [{"role": "user", "content": "hi"}]},
                    cookies={"sempkm_session": valid_session.token},
                )

        # If auth works via cookie, we get the SSE error (not 401)
        assert resp.status_code == 200
        assert '"error": "LLM not configured"' in resp.text


class TestLLMStatusAcceptsCookieAuth:
    """GET /api/llm/status works with cookie auth."""

    async def test_llm_status_accepts_cookie_auth(
        self, db_session_factory, test_user, valid_session
    ):
        app = _build_ai_app(db_session_factory)
        mock_config = {"api_base_url": "", "api_key_set": False, "default_model": ""}

        with patch(
            "app.api.ai.LLMConfigService.get_config",
            new_callable=AsyncMock,
            return_value=mock_config,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/llm/status",
                    cookies={"sempkm_session": valid_session.token},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False
