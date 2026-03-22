"""API tests for federation endpoint management routes.

Tests POST/DELETE/GET at /api/sparql/mirror/endpoints and validates
owner-only access, URL validation, and env-var protection.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.models import User
from app.sparql.federation_config import (
    FederationEndpoints,
    save_federation_endpoints,
)
from app.sparql.mirror_router import router as mirror_router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_owner_user():
    """Create a mock owner User."""
    import uuid
    return User(id=uuid.uuid4(), email="owner@test.com", role="owner")


def _make_member_user():
    """Create a mock member User."""
    import uuid
    return User(id=uuid.uuid4(), email="member@test.com", role="member")


@pytest.fixture
def federation_path(tmp_path):
    return tmp_path / ".federation-endpoints.json"


@pytest.fixture
def app(federation_path):
    """Create a minimal FastAPI app with the mirror router."""
    test_app = FastAPI()
    test_app.include_router(mirror_router)
    return test_app


@pytest.fixture
def owner_app(app):
    """App with owner-level auth override on all require_role deps."""
    from app.auth.dependencies import require_role, get_current_user
    owner = _make_owner_user()
    app.dependency_overrides[require_role("owner")] = lambda: owner
    app.dependency_overrides[get_current_user] = lambda: owner
    return app


@pytest.fixture
def member_app(app):
    """App with member-level auth override (should fail owner-only routes)."""
    from app.auth.dependencies import get_current_user
    member = _make_member_user()
    app.dependency_overrides[get_current_user] = lambda: member
    return app


# ---------------------------------------------------------------------------
# GET /api/sparql/mirror/endpoints
# ---------------------------------------------------------------------------


class TestGetEndpoints:
    @pytest.mark.anyio
    async def test_get_returns_merged_list(self, owner_app, federation_path):
        with patch(
            "app.sparql.mirror_router.get_merged_endpoints",
            return_value=[
                {"url": "https://env.org/sparql", "source": "env", "removable": False},
                {"url": "https://admin.org/sparql", "source": "admin", "removable": True},
            ],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=owner_app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/sparql/mirror/endpoints")
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["endpoints"]) == 2
                assert data["allowlist_configured"] is True

    @pytest.mark.anyio
    async def test_get_empty(self, owner_app):
        with patch(
            "app.sparql.mirror_router.get_merged_endpoints",
            return_value=[],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=owner_app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/sparql/mirror/endpoints")
                assert resp.status_code == 200
                data = resp.json()
                assert data["endpoints"] == []
                assert data["allowlist_configured"] is False


# ---------------------------------------------------------------------------
# POST /api/sparql/mirror/endpoints
# ---------------------------------------------------------------------------


class TestAddEndpoint:
    @pytest.mark.anyio
    async def test_add_valid_url(self, owner_app):
        with patch(
            "app.sparql.mirror_router.add_endpoint",
            return_value=[
                {"url": "https://dbpedia.org/sparql", "source": "admin", "removable": True},
            ],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=owner_app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/sparql/mirror/endpoints",
                    json={"url": "https://dbpedia.org/sparql"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["endpoints"]) == 1

    @pytest.mark.anyio
    async def test_add_invalid_url_rejected(self, owner_app):
        async with AsyncClient(
            transport=ASGITransport(app=owner_app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/sparql/mirror/endpoints",
                json={"url": "ftp://bad.org/sparql"},
            )
            assert resp.status_code == 400
            assert "http://" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE /api/sparql/mirror/endpoints/{encoded_url}
# ---------------------------------------------------------------------------


class TestRemoveEndpoint:
    @pytest.mark.anyio
    async def test_remove_admin_endpoint(self, owner_app):
        with patch(
            "app.sparql.mirror_router.remove_endpoint",
            return_value=[],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=owner_app),
                base_url="http://test",
            ) as client:
                resp = await client.delete(
                    "/api/sparql/mirror/endpoints/https%3A%2F%2Fadmin.org%2Fsparql"
                )
                assert resp.status_code == 200
                assert resp.json()["endpoints"] == []

    @pytest.mark.anyio
    async def test_remove_env_endpoint_returns_409(self, owner_app):
        with patch(
            "app.sparql.mirror_router.remove_endpoint",
            side_effect=ValueError("Cannot remove env-var endpoint: https://env.org/sparql"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=owner_app),
                base_url="http://test",
            ) as client:
                resp = await client.delete(
                    "/api/sparql/mirror/endpoints/https%3A%2F%2Fenv.org%2Fsparql"
                )
                assert resp.status_code == 409
                assert "Cannot remove" in resp.json()["detail"]
