"""Tests for the context zones API router — CRUD, auth, validation, and 404s.

Tests use httpx AsyncClient with dependency overrides to mock auth
and ZoneService. Follows the test_rules_router.py pattern.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.context.zone_models import ContextZone
from app.context.zone_router import router as zone_router
from app.dependencies import get_zone_service


# ── Helpers ──────────────────────────────────────────────────────


def _make_zone(
    user_id: uuid.UUID,
    name: str = "Home",
    latitude: float = 40.7128,
    longitude: float = -74.0060,
    radius_meters: float = 200.0,
    enabled: bool = True,
) -> ContextZone:
    """Build a ContextZone instance for test assertions."""
    zone = ContextZone(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        enabled=enabled,
    )
    zone.created_at = datetime.now(timezone.utc)
    zone.updated_at = datetime.now(timezone.utc)
    return zone


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="zone-test@example.com",
        role="owner",
    )


@pytest.fixture
def mock_zone_service():
    return AsyncMock()


@pytest.fixture
async def client(test_user, mock_zone_service):
    """AsyncClient wired to the zone router with dependency overrides."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(zone_router)

    app.dependency_overrides[get_current_user_or_api] = lambda: test_user
    app.dependency_overrides[get_zone_service] = lambda: mock_zone_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── POST /api/context/zones — create ────────────────────────────


class TestCreateZone:
    @pytest.mark.asyncio
    async def test_create_returns_201(self, client, mock_zone_service, test_user):
        zone = _make_zone(test_user.id, name="Office", latitude=51.5074, longitude=-0.1278)
        mock_zone_service.create.return_value = zone

        resp = await client.post(
            "/api/context/zones/",
            json={
                "name": "Office",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "radius_meters": 200.0,
                "enabled": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Office"
        assert data["latitude"] == 51.5074
        assert data["longitude"] == -0.1278
        mock_zone_service.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_uses_defaults(self, client, mock_zone_service, test_user):
        zone = _make_zone(test_user.id)
        mock_zone_service.create.return_value = zone

        resp = await client.post(
            "/api/context/zones/",
            json={
                "name": "Home",
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
        )
        assert resp.status_code == 201
        call_kwargs = mock_zone_service.create.call_args
        assert call_kwargs.kwargs["radius_meters"] == 200.0
        assert call_kwargs.kwargs["enabled"] is True

    @pytest.mark.asyncio
    async def test_create_missing_name_returns_422(self, client):
        resp = await client.post(
            "/api/context/zones/",
            json={"latitude": 40.0, "longitude": -74.0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_empty_name_returns_422(self, client):
        resp = await client.post(
            "/api/context/zones/",
            json={"name": "", "latitude": 40.0, "longitude": -74.0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_invalid_latitude_returns_422(self, client):
        resp = await client.post(
            "/api/context/zones/",
            json={"name": "Bad", "latitude": 91.0, "longitude": 0.0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_invalid_latitude_negative_returns_422(self, client):
        resp = await client.post(
            "/api/context/zones/",
            json={"name": "Bad", "latitude": -91.0, "longitude": 0.0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_invalid_longitude_returns_422(self, client):
        resp = await client.post(
            "/api/context/zones/",
            json={"name": "Bad", "latitude": 0.0, "longitude": 181.0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_invalid_longitude_negative_returns_422(self, client):
        resp = await client.post(
            "/api/context/zones/",
            json={"name": "Bad", "latitude": 0.0, "longitude": -181.0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_radius_too_small_returns_422(self, client):
        resp = await client.post(
            "/api/context/zones/",
            json={"name": "Tiny", "latitude": 0.0, "longitude": 0.0, "radius_meters": 10.0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_radius_too_large_returns_422(self, client):
        resp = await client.post(
            "/api/context/zones/",
            json={"name": "Huge", "latitude": 0.0, "longitude": 0.0, "radius_meters": 20000.0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_boundary_values_valid(self, client, mock_zone_service, test_user):
        """Edge values at boundaries should pass validation."""
        zone = _make_zone(test_user.id, latitude=90.0, longitude=180.0, radius_meters=50.0)
        mock_zone_service.create.return_value = zone

        resp = await client.post(
            "/api/context/zones/",
            json={"name": "Edge", "latitude": 90.0, "longitude": 180.0, "radius_meters": 50.0},
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_negative_boundary_values_valid(self, client, mock_zone_service, test_user):
        zone = _make_zone(test_user.id, latitude=-90.0, longitude=-180.0, radius_meters=10000.0)
        mock_zone_service.create.return_value = zone

        resp = await client.post(
            "/api/context/zones/",
            json={"name": "Edge", "latitude": -90.0, "longitude": -180.0, "radius_meters": 10000.0},
        )
        assert resp.status_code == 201


# ── GET /api/context/zones — list ────────────────────────────────


class TestListZones:
    @pytest.mark.asyncio
    async def test_list_empty(self, client, mock_zone_service):
        mock_zone_service.list_for_user.return_value = []
        resp = await client.get("/api/context/zones/")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_zones(self, client, mock_zone_service, test_user):
        zones = [
            _make_zone(test_user.id, name="Home"),
            _make_zone(test_user.id, name="Office"),
        ]
        mock_zone_service.list_for_user.return_value = zones

        resp = await client.get("/api/context/zones/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Home"
        assert data[1]["name"] == "Office"

    @pytest.mark.asyncio
    async def test_list_scoped_to_user(self, client, mock_zone_service, test_user):
        mock_zone_service.list_for_user.return_value = []
        await client.get("/api/context/zones/")
        mock_zone_service.list_for_user.assert_awaited_once_with(test_user.id)


# ── PUT /api/context/zones/{id} — update ─────────────────────────


class TestUpdateZone:
    @pytest.mark.asyncio
    async def test_update_returns_updated_zone(self, client, mock_zone_service, test_user):
        zone = _make_zone(test_user.id, name="Updated Home")
        mock_zone_service.update.return_value = zone

        zone_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/context/zones/{zone_id}",
            json={"name": "Updated Home"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Home"

    @pytest.mark.asyncio
    async def test_update_not_found_returns_404(self, client, mock_zone_service):
        mock_zone_service.update.return_value = None

        zone_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/context/zones/{zone_id}",
            json={"name": "New Name"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_empty_body_returns_422(self, client):
        zone_id = str(uuid.uuid4())
        resp = await client.put(f"/api/context/zones/{zone_id}", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_partial_fields(self, client, mock_zone_service, test_user):
        zone = _make_zone(test_user.id, radius_meters=500.0)
        mock_zone_service.update.return_value = zone

        zone_id = str(uuid.uuid4())
        await client.put(
            f"/api/context/zones/{zone_id}",
            json={"radius_meters": 500.0},
        )
        call_kwargs = mock_zone_service.update.call_args.kwargs
        assert "radius_meters" in call_kwargs
        assert "name" not in call_kwargs

    @pytest.mark.asyncio
    async def test_update_invalid_latitude_returns_422(self, client):
        zone_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/context/zones/{zone_id}",
            json={"latitude": 95.0},
        )
        assert resp.status_code == 422


# ── DELETE /api/context/zones/{id} ───────────────────────────────


class TestDeleteZone:
    @pytest.mark.asyncio
    async def test_delete_returns_204(self, client, mock_zone_service):
        mock_zone_service.delete.return_value = True

        zone_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/context/zones/{zone_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_404(self, client, mock_zone_service):
        mock_zone_service.delete.return_value = False

        zone_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/context/zones/{zone_id}")
        assert resp.status_code == 404


# ── Auth enforcement ─────────────────────────────────────────────


class TestAuthEnforcement:
    """Verify all endpoints require authentication."""

    @pytest.fixture
    async def unauthed_client(self, mock_zone_service):
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(zone_router)

        # Override service dep but NOT auth
        app.dependency_overrides[get_zone_service] = lambda: mock_zone_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, unauthed_client):
        resp = await unauthed_client.get("/api/context/zones/")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, unauthed_client):
        resp = await unauthed_client.post(
            "/api/context/zones/",
            json={"name": "Z", "latitude": 0.0, "longitude": 0.0},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, unauthed_client):
        zone_id = str(uuid.uuid4())
        resp = await unauthed_client.put(
            f"/api/context/zones/{zone_id}",
            json={"name": "New"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, unauthed_client):
        zone_id = str(uuid.uuid4())
        resp = await unauthed_client.delete(f"/api/context/zones/{zone_id}")
        assert resp.status_code == 401
