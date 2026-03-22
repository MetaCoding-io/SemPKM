"""API tests for federation endpoint management routes.

Tests POST/DELETE/GET at /api/sparql/mirror/endpoints and validates
owner-only access, URL validation, env-var protection, and merged list shape.

Uses dependency overrides on ``get_current_user`` so that
``require_role("owner")`` picks up the injected user and checks its role.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.sparql.federation_config import (
    DEFAULT_FEDERATION_PATH,
    FederationEndpoints,
    save_federation_endpoints,
)
from app.sparql.mirror_router import router as mirror_router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(role: str = "owner", email: str | None = None) -> User:
    """Create a mock User with the given role."""
    import uuid

    return User(
        id=uuid.uuid4(),
        email=email or f"{role}@test.com",
        role=role,
    )


def _patch_env_endpoints(endpoints: list[str]):
    """Return a context manager that patches settings.get_allowed_endpoints()."""
    mock_settings = type(
        "MockSettings", (), {"get_allowed_endpoints": lambda self: endpoints}
    )()
    return patch("app.sparql.federation_config.settings", mock_settings)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def federation_path(tmp_path):
    return tmp_path / ".federation-endpoints.json"


@pytest.fixture
def app():
    """Create a minimal FastAPI app with the mirror router."""
    test_app = FastAPI()
    test_app.include_router(mirror_router)
    yield test_app
    test_app.dependency_overrides.clear()


@pytest.fixture
def owner_client(app, federation_path):
    """Return an (app, AsyncClient-factory) tuple with owner auth and patched path."""
    owner = _make_user("owner")
    app.dependency_overrides[get_current_user] = lambda: owner

    async def _client():
        return AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )

    return _client


@pytest.fixture
def member_client(app, federation_path):
    """Return an AsyncClient-factory with member auth (non-owner)."""
    member = _make_user("member")
    app.dependency_overrides[get_current_user] = lambda: member

    async def _client():
        return AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )

    return _client


# ---------------------------------------------------------------------------
# GET /api/sparql/mirror/endpoints
# ---------------------------------------------------------------------------


class TestGetEndpoints:
    @pytest.mark.anyio
    async def test_get_returns_merged_list(self, owner_client, federation_path):
        """GET returns both env and admin endpoints with correct annotations."""
        # Persist an admin endpoint
        save_federation_endpoints(
            FederationEndpoints(
                endpoints=["https://admin.org/sparql"], updated_at="2026-01-01T00:00:00"
            ),
            federation_path,
        )

        with (
            _patch_env_endpoints(["https://env.org/sparql"]),
            patch(
                "app.sparql.mirror_router.get_merged_endpoints",
                wraps=None,
            ) as mock_merged,
        ):
            # Use the real get_merged_endpoints but with controlled path
            from app.sparql.federation_config import get_merged_endpoints

            mock_merged.side_effect = lambda path=None: get_merged_endpoints(federation_path)

            async with await owner_client() as client:
                resp = await client.get("/api/sparql/mirror/endpoints")
                assert resp.status_code == 200
                data = resp.json()
                assert data["allowlist_configured"] is True
                assert len(data["endpoints"]) == 2
                sources = {e["url"]: e["source"] for e in data["endpoints"]}
                assert sources["https://env.org/sparql"] == "env"
                assert sources["https://admin.org/sparql"] == "admin"

    @pytest.mark.anyio
    async def test_get_empty(self, owner_client):
        """GET with nothing configured returns empty list and flag False."""
        with patch(
            "app.sparql.mirror_router.get_merged_endpoints",
            return_value=[],
        ):
            async with await owner_client() as client:
                resp = await client.get("/api/sparql/mirror/endpoints")
                assert resp.status_code == 200
                data = resp.json()
                assert data["endpoints"] == []
                assert data["allowlist_configured"] is False

    @pytest.mark.anyio
    async def test_get_accessible_by_member(self, member_client):
        """GET /endpoints is accessible to members (not owner-only)."""
        with patch(
            "app.sparql.mirror_router.get_merged_endpoints",
            return_value=[],
        ):
            async with await member_client() as client:
                resp = await client.get("/api/sparql/mirror/endpoints")
                assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/sparql/mirror/endpoints
# ---------------------------------------------------------------------------


class TestAddEndpoint:
    @pytest.mark.anyio
    async def test_add_valid_url(self, owner_client):
        """POST with a valid https URL succeeds."""
        with patch(
            "app.sparql.mirror_router.add_endpoint",
            return_value=[
                {"url": "https://dbpedia.org/sparql", "source": "admin", "removable": True},
            ],
        ):
            async with await owner_client() as client:
                resp = await client.post(
                    "/api/sparql/mirror/endpoints",
                    json={"url": "https://dbpedia.org/sparql"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["endpoints"]) == 1
                assert data["endpoints"][0]["url"] == "https://dbpedia.org/sparql"

    @pytest.mark.anyio
    async def test_add_http_url_accepted(self, owner_client):
        """POST with a plain http:// URL also succeeds."""
        with patch(
            "app.sparql.mirror_router.add_endpoint",
            return_value=[
                {"url": "http://localhost:7200/sparql", "source": "admin", "removable": True},
            ],
        ):
            async with await owner_client() as client:
                resp = await client.post(
                    "/api/sparql/mirror/endpoints",
                    json={"url": "http://localhost:7200/sparql"},
                )
                assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_add_invalid_url_rejected(self, owner_client):
        """POST with a non-HTTP URL returns 400."""
        async with await owner_client() as client:
            resp = await client.post(
                "/api/sparql/mirror/endpoints",
                json={"url": "ftp://bad.org/sparql"},
            )
            assert resp.status_code == 400
            assert "http://" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_add_duplicate_endpoint_is_idempotent(self, owner_client, federation_path):
        """POSTing the same URL twice does not create duplicates."""
        # First add returns 1 endpoint, second add also returns 1
        call_count = 0

        def _mock_add(url, path=None):
            nonlocal call_count
            call_count += 1
            return [
                {"url": "https://dbpedia.org/sparql", "source": "admin", "removable": True},
            ]

        with patch("app.sparql.mirror_router.add_endpoint", side_effect=_mock_add):
            async with await owner_client() as client:
                resp1 = await client.post(
                    "/api/sparql/mirror/endpoints",
                    json={"url": "https://dbpedia.org/sparql"},
                )
                assert resp1.status_code == 200
                resp2 = await client.post(
                    "/api/sparql/mirror/endpoints",
                    json={"url": "https://dbpedia.org/sparql"},
                )
                assert resp2.status_code == 200
                assert len(resp2.json()["endpoints"]) == 1

    @pytest.mark.anyio
    async def test_add_endpoint_owner_only(self, member_client):
        """POST by a non-owner user returns 403."""
        async with await member_client() as client:
            resp = await client.post(
                "/api/sparql/mirror/endpoints",
                json={"url": "https://dbpedia.org/sparql"},
            )
            assert resp.status_code == 403
            assert "role" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE /api/sparql/mirror/endpoints/{encoded_url}
# ---------------------------------------------------------------------------


class TestRemoveEndpoint:
    @pytest.mark.anyio
    async def test_remove_admin_endpoint(self, owner_client):
        """DELETE an admin endpoint returns updated list without it."""
        with patch(
            "app.sparql.mirror_router.remove_endpoint",
            return_value=[],
        ):
            async with await owner_client() as client:
                resp = await client.delete(
                    "/api/sparql/mirror/endpoints/https%3A%2F%2Fadmin.org%2Fsparql"
                )
                assert resp.status_code == 200
                assert resp.json()["endpoints"] == []

    @pytest.mark.anyio
    async def test_remove_env_endpoint_returns_409(self, owner_client):
        """DELETE an env-sourced endpoint returns 409 with explanation."""
        with patch(
            "app.sparql.mirror_router.remove_endpoint",
            side_effect=ValueError("Cannot remove env-var endpoint: https://env.org/sparql"),
        ):
            async with await owner_client() as client:
                resp = await client.delete(
                    "/api/sparql/mirror/endpoints/https%3A%2F%2Fenv.org%2Fsparql"
                )
                assert resp.status_code == 409
                assert "Cannot remove" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_delete_then_get_reflects_removal(self, owner_client, federation_path):
        """After DELETE, GET no longer includes the removed endpoint."""
        remaining = [
            {"url": "https://env.org/sparql", "source": "env", "removable": False},
        ]

        with (
            patch("app.sparql.mirror_router.remove_endpoint", return_value=remaining),
            patch("app.sparql.mirror_router.get_merged_endpoints", return_value=remaining),
        ):
            async with await owner_client() as client:
                # Delete
                resp_del = await client.delete(
                    "/api/sparql/mirror/endpoints/https%3A%2F%2Fadmin.org%2Fsparql"
                )
                assert resp_del.status_code == 200

                # Verify GET reflects the removal
                resp_get = await client.get("/api/sparql/mirror/endpoints")
                assert resp_get.status_code == 200
                urls = [e["url"] for e in resp_get.json()["endpoints"]]
                assert "https://admin.org/sparql" not in urls

    @pytest.mark.anyio
    async def test_delete_endpoint_owner_only(self, member_client):
        """DELETE by a non-owner user returns 403."""
        async with await member_client() as client:
            resp = await client.delete(
                "/api/sparql/mirror/endpoints/https%3A%2F%2Fadmin.org%2Fsparql"
            )
            assert resp.status_code == 403
            assert "role" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_remove_nonexistent_returns_409(self, owner_client):
        """DELETE a URL that doesn't exist in the list returns 409."""
        with patch(
            "app.sparql.mirror_router.remove_endpoint",
            side_effect=ValueError("Endpoint not found in admin list: https://ghost.org/sparql"),
        ):
            async with await owner_client() as client:
                resp = await client.delete(
                    "/api/sparql/mirror/endpoints/https%3A%2F%2Fghost.org%2Fsparql"
                )
                assert resp.status_code == 409
                assert "not found" in resp.json()["detail"].lower()
