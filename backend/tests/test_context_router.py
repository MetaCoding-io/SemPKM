"""Tests for the context API router — update, current, stream, and auth.

Tests use httpx AsyncClient with dependency overrides to mock auth,
ContextService, and ContextBroadcast.
"""

import asyncio
import dataclasses
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.context.broadcast import ContextBroadcast
from app.context.router import ContextUpdateRequest, router
from app.context.service import ContextData, ContextService
from app.dependencies import get_context_broadcast, get_context_service


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="ctx-test@example.com",
        role="owner",
    )


@pytest.fixture
def mock_service():
    return AsyncMock(spec=ContextService)


@pytest.fixture
def mock_broadcast():
    broadcast = AsyncMock(spec=ContextBroadcast)
    broadcast.client_count = 0
    return broadcast


@pytest.fixture
def sample_context_data(test_user):
    return ContextData(
        user_id=str(test_user.id),
        location_zone="office",
        activity="stationary",
        time_period="work_hours",
        is_stale=False,
        ttl_seconds=900,
        updated_at="2026-03-23T15:00:00",
        created_at="2026-03-23T14:00:00",
    )


@pytest.fixture
async def client(test_user, mock_service, mock_broadcast):
    """AsyncClient wired to the context router with dependency overrides."""
    from fastapi import FastAPI

    app = FastAPI()

    # The rate limiter needs app.state.limiter
    from app.auth.rate_limit import limiter

    app.state.limiter = limiter

    # Add slowapi middleware so the @limiter.limit decorator works
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Shutdown event needed by the stream endpoint
    app.state.shutdown_event = asyncio.Event()

    app.include_router(router)

    # Override dependencies
    app.dependency_overrides[get_current_user_or_api] = lambda: test_user
    app.dependency_overrides[get_context_service] = lambda: mock_service
    app.dependency_overrides[get_context_broadcast] = lambda: mock_broadcast

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── POST /api/context/update ─────────────────────────────────────


class TestUpdateContext:
    @pytest.mark.asyncio
    async def test_update_returns_context(
        self, client, mock_service, mock_broadcast, sample_context_data
    ):
        mock_service.update.return_value = sample_context_data

        resp = await client.post(
            "/api/context/update",
            json={"location_zone": "office", "activity": "stationary"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["location_zone"] == "office"
        assert data["is_stale"] is False

        # Verify service was called with correct kwargs
        mock_service.update.assert_awaited_once()
        call_kwargs = mock_service.update.call_args
        assert call_kwargs[1]["location_zone"] == "office"
        assert call_kwargs[1]["activity"] == "stationary"

    @pytest.mark.asyncio
    async def test_update_publishes_sse_event(
        self, client, mock_service, mock_broadcast, sample_context_data
    ):
        mock_service.update.return_value = sample_context_data

        await client.post(
            "/api/context/update",
            json={"location_zone": "office"},
        )

        mock_broadcast.publish.assert_awaited_once()
        event = mock_broadcast.publish.call_args[0][0]
        assert event.event == "context_update"
        assert event.data["location_zone"] == "office"

    @pytest.mark.asyncio
    async def test_update_empty_body_returns_422(self, client):
        resp = await client.post("/api/context/update", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_partial_fields(
        self, client, mock_service, sample_context_data
    ):
        """Only provided fields should be passed to service.update()."""
        mock_service.update.return_value = sample_context_data

        await client.post(
            "/api/context/update",
            json={"device_id": "phone-01"},
        )

        call_kwargs = mock_service.update.call_args[1]
        assert "device_id" in call_kwargs
        assert "location_zone" not in call_kwargs

    @pytest.mark.asyncio
    async def test_update_validates_field_length(self, client):
        """Fields exceeding max_length should fail validation."""
        resp = await client.post(
            "/api/context/update",
            json={"location_zone": "x" * 200},
        )
        assert resp.status_code == 422


# ── GET /api/context/current ─────────────────────────────────────


class TestGetCurrentContext:
    @pytest.mark.asyncio
    async def test_returns_context_when_exists(
        self, client, mock_service, sample_context_data
    ):
        mock_service.get_current.return_value = sample_context_data

        resp = await client.get("/api/context/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["context"]["location_zone"] == "office"
        assert data["context"]["is_stale"] is False

    @pytest.mark.asyncio
    async def test_returns_null_when_no_context(self, client, mock_service):
        mock_service.get_current.return_value = None

        resp = await client.get("/api/context/current")
        assert resp.status_code == 200
        assert resp.json() == {"context": None}

    @pytest.mark.asyncio
    async def test_returns_stale_context(self, client, mock_service, test_user):
        stale_ctx = ContextData(
            user_id=str(test_user.id),
            location_zone="office",
            is_stale=True,
            ttl_seconds=900,
            updated_at="2026-03-23T14:00:00",
            created_at="2026-03-23T13:00:00",
        )
        mock_service.get_current.return_value = stale_ctx

        resp = await client.get("/api/context/current")
        data = resp.json()
        assert data["context"]["is_stale"] is True


# ── Auth enforcement ─────────────────────────────────────────────


class TestAuthEnforcement:
    @pytest.mark.asyncio
    async def test_update_requires_auth(self, mock_service, mock_broadcast):
        """Without auth override, endpoints should require authentication."""
        from fastapi import FastAPI

        app = FastAPI()
        from app.auth.rate_limit import limiter

        app.state.limiter = limiter
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded

        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.state.shutdown_event = asyncio.Event()
        app.include_router(router)

        # Override service deps but NOT auth
        app.dependency_overrides[get_context_service] = lambda: mock_service
        app.dependency_overrides[get_context_broadcast] = lambda: mock_broadcast

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/context/update",
                json={"location_zone": "office"},
            )
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_current_requires_auth(self, mock_service, mock_broadcast):
        from fastapi import FastAPI

        app = FastAPI()
        app.state.shutdown_event = asyncio.Event()
        app.include_router(router)
        app.dependency_overrides[get_context_service] = lambda: mock_service
        app.dependency_overrides[get_context_broadcast] = lambda: mock_broadcast

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/context/current")
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_stream_requires_auth(self, mock_service, mock_broadcast):
        """GET /api/context/stream without auth returns 401."""
        from fastapi import FastAPI

        app = FastAPI()
        app.state.shutdown_event = asyncio.Event()
        app.include_router(router)
        app.dependency_overrides[get_context_service] = lambda: mock_service
        app.dependency_overrides[get_context_broadcast] = lambda: mock_broadcast

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/context/stream")
            assert resp.status_code == 401


# ── SSE stream content type ──────────────────────────────────────


class TestStreamEndpoint:
    @pytest.mark.asyncio
    async def test_stream_content_type(self, client, mock_broadcast):
        """GET /api/context/stream returns text/event-stream content type."""
        # Create a broadcast that will immediately provide a shutdown
        # so the stream terminates quickly
        from fastapi import FastAPI

        app = FastAPI()
        from app.auth.rate_limit import limiter

        app.state.limiter = limiter
        app.state.shutdown_event = asyncio.Event()
        app.state.shutdown_event.set()  # signal shutdown immediately
        app.include_router(router)

        test_user_obj = User(
            id=uuid.uuid4(), email="stream@test.com", role="owner"
        )
        real_broadcast = ContextBroadcast()

        app.dependency_overrides[get_current_user_or_api] = lambda: test_user_obj
        app.dependency_overrides[get_context_service] = lambda: AsyncMock(
            spec=ContextService
        )
        app.dependency_overrides[get_context_broadcast] = lambda: real_broadcast

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/context/stream")
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


# ── Pydantic model validation ───────────────────────────────────


class TestContextUpdateRequestModel:
    def test_all_fields_optional(self):
        """Empty dict should produce a valid model (all None)."""
        req = ContextUpdateRequest()
        assert req.location_zone is None
        assert req.calendar_busy is None

    def test_partial_fields(self):
        req = ContextUpdateRequest(location_zone="office")
        assert req.location_zone == "office"
        assert req.activity is None

    def test_model_dump_exclude_unset(self):
        req = ContextUpdateRequest(location_zone="office")
        dumped = req.model_dump(exclude_unset=True)
        assert "location_zone" in dumped
        assert "activity" not in dumped
