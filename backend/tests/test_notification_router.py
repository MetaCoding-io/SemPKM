"""Tests for the notification API router — token registration, preference
CRUD, test-send endpoint, and auth enforcement.

Uses httpx AsyncClient with dependency overrides to mock auth and
NotificationService.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.context.notification_router import router


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="notif-test@example.com",
        role="owner",
    )


@pytest.fixture
def mock_service():
    """Mock NotificationService with sensible defaults."""
    svc = AsyncMock()
    svc.get_preferences.return_value = {
        "enabled": True,
        "quiet_hours_start": None,
        "quiet_hours_end": None,
        "suppress_when_busy": True,
        "enabled_types": ["overdue_tasks", "validation_warnings", "context_changes"],
    }
    svc.should_suppress.return_value = (False, None)
    svc.get_tokens_for_user.return_value = []
    svc.send_to_user.return_value = []
    return svc


@pytest.fixture
async def client(test_user, mock_service):
    """AsyncClient wired to the notification router with dependency overrides."""
    from fastapi import FastAPI

    app = FastAPI()
    app.state.notification_service = mock_service
    app.include_router(router)

    app.dependency_overrides[get_current_user_or_api] = lambda: test_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def noauth_client(mock_service):
    """AsyncClient WITHOUT auth override — endpoints should return 401."""
    from fastapi import FastAPI

    app = FastAPI()
    app.state.notification_service = mock_service
    app.include_router(router)
    # No dependency override for get_current_user_or_api

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Token Registration ───────────────────────────────────────────


class TestRegisterToken:
    @pytest.mark.asyncio
    async def test_register_success(self, client, mock_service, test_user):
        """POST /api/notifications/register returns 201 with token info."""
        token_row = MagicMock()
        token_row.id = uuid.uuid4()
        token_row.platform = "ios"
        token_row.device_name = "iPhone 15"
        token_row.created_at = datetime.now(timezone.utc)
        mock_service.register_token.return_value = token_row

        resp = await client.post(
            "/api/notifications/register",
            json={"token": "fcm-token-abc123", "platform": "ios", "device_name": "iPhone 15"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["platform"] == "ios"
        assert data["device_name"] == "iPhone 15"
        mock_service.register_token.assert_awaited_once_with(
            user_id=test_user.id,
            token="fcm-token-abc123",
            platform="ios",
            device_name="iPhone 15",
        )

    @pytest.mark.asyncio
    async def test_register_missing_platform(self, client):
        """POST without platform returns 422."""
        resp = await client.post(
            "/api/notifications/register",
            json={"token": "fcm-token-abc123"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_platform(self, client):
        """POST with invalid platform returns 422."""
        resp = await client.post(
            "/api/notifications/register",
            json={"token": "fcm-token-abc123", "platform": "windows"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_duplicate_token_upserts(self, client, mock_service, test_user):
        """Duplicate token registration is an upsert — still returns 201."""
        token_row = MagicMock()
        token_row.id = uuid.uuid4()
        token_row.platform = "android"
        token_row.device_name = None
        token_row.created_at = datetime.now(timezone.utc)
        mock_service.register_token.return_value = token_row

        resp = await client.post(
            "/api/notifications/register",
            json={"token": "same-token-twice", "platform": "android"},
        )
        assert resp.status_code == 201


# ── Preferences ──────────────────────────────────────────────────


class TestGetPreferences:
    @pytest.mark.asyncio
    async def test_get_default_preferences(self, client, mock_service, test_user):
        """GET /api/notifications/preferences returns defaults when no row."""
        resp = await client.get("/api/notifications/preferences")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["suppress_when_busy"] is True
        mock_service.get_preferences.assert_awaited_once_with(test_user.id)

    @pytest.mark.asyncio
    async def test_get_preferences_after_update(self, client, mock_service, test_user):
        """GET after update returns persisted values."""
        mock_service.get_preferences.return_value = {
            "enabled": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
            "suppress_when_busy": False,
            "enabled_types": ["overdue_tasks"],
        }
        resp = await client.get("/api/notifications/preferences")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["quiet_hours_start"] == "22:00"


class TestUpdatePreferences:
    @pytest.mark.asyncio
    async def test_partial_update(self, client, mock_service, test_user):
        """PUT with partial fields updates only those fields."""
        mock_service.update_preferences.return_value = {
            "enabled": False,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "suppress_when_busy": True,
            "enabled_types": ["overdue_tasks", "validation_warnings", "context_changes"],
        }
        resp = await client.put(
            "/api/notifications/preferences",
            json={"enabled": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        mock_service.update_preferences.assert_awaited_once_with(test_user.id, enabled=False)

    @pytest.mark.asyncio
    async def test_full_update(self, client, mock_service, test_user):
        """PUT with all fields updates everything."""
        mock_service.update_preferences.return_value = {
            "enabled": True,
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "06:00",
            "suppress_when_busy": False,
            "enabled_types": ["context_changes"],
        }
        resp = await client.put(
            "/api/notifications/preferences",
            json={
                "enabled": True,
                "quiet_hours_start": "23:00",
                "quiet_hours_end": "06:00",
                "suppress_when_busy": False,
                "enabled_types": ["context_changes"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["quiet_hours_start"] == "23:00"
        assert data["enabled_types"] == ["context_changes"]

    @pytest.mark.asyncio
    async def test_update_empty_body_returns_422(self, client):
        """PUT with no fields returns 422."""
        resp = await client.put(
            "/api/notifications/preferences",
            json={},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_quiet_hours_format(self, client):
        """PUT with badly formatted quiet hours returns 422."""
        resp = await client.put(
            "/api/notifications/preferences",
            json={"quiet_hours_start": "not-a-time"},
        )
        assert resp.status_code == 422


# ── Test Notification ────────────────────────────────────────────


class TestTestNotification:
    @pytest.mark.asyncio
    async def test_no_tokens(self, client, mock_service):
        """POST /api/notifications/test with no tokens returns sent_count=0."""
        mock_service.get_tokens_for_user.return_value = []
        resp = await client.post("/api/notifications/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent_count"] == 0
        assert data["reason"] == "no_devices"

    @pytest.mark.asyncio
    async def test_suppression_active(self, client, mock_service):
        """POST /api/notifications/test when suppressed returns reason."""
        mock_service.should_suppress.return_value = (True, "quiet_hours")
        resp = await client.post("/api/notifications/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["suppressed"] is True
        assert data["reason"] == "quiet_hours"

    @pytest.mark.asyncio
    async def test_with_tokens_sends(self, client, mock_service):
        """POST /api/notifications/test with tokens returns sent_count."""
        mock_token = MagicMock()
        mock_token.token = "some-fcm-token"
        mock_service.get_tokens_for_user.return_value = [mock_token]
        mock_service.send_to_user.return_value = ["msg-id-1"]

        resp = await client.post("/api/notifications/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent_count"] == 1
        assert data["suppressed"] is False


# ── Auth Enforcement ─────────────────────────────────────────────


class TestAuthEnforcement:
    @pytest.mark.asyncio
    async def test_register_requires_auth(self, noauth_client):
        """POST /api/notifications/register without auth returns 401."""
        resp = await noauth_client.post(
            "/api/notifications/register",
            json={"token": "t", "platform": "ios"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_preferences_requires_auth(self, noauth_client):
        """GET /api/notifications/preferences without auth returns 401."""
        resp = await noauth_client.get("/api/notifications/preferences")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_preferences_requires_auth(self, noauth_client):
        """PUT /api/notifications/preferences without auth returns 401."""
        resp = await noauth_client.put(
            "/api/notifications/preferences",
            json={"enabled": False},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_test_notification_requires_auth(self, noauth_client):
        """POST /api/notifications/test without auth returns 401."""
        resp = await noauth_client.post("/api/notifications/test")
        assert resp.status_code == 401
