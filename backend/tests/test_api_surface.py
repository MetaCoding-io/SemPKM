"""Tests for the API surface: dual-auth dependency and well-known endpoint.

Tests dual-auth resolution (session cookie, Bearer token, failure paths)
and the /.well-known/sempkm discovery endpoint response.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.dependencies import (
    _extract_bearer_token,
    get_current_user_or_api,
)
from app.auth.models import ApiToken, User, UserSession
from app.config import settings
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
    """Provide an async session factory."""
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def db_session(db_session_factory):
    """Provide a single async session for test use."""
    async with db_session_factory() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(id=uuid.uuid4(), email="test@example.com", role="owner")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def valid_session(db_session: AsyncSession, test_user: User) -> UserSession:
    """Create a valid (non-expired) session for the test user."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
    session = UserSession(token=token, user_id=test_user.id, expires_at=expires_at)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture
async def expired_session(db_session: AsyncSession, test_user: User) -> UserSession:
    """Create an expired session for the test user."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
    session = UserSession(token=token, user_id=test_user.id, expires_at=expires_at)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture
async def valid_api_token(db_session: AsyncSession, test_user: User) -> str:
    """Create a valid API token row and return the plaintext token."""
    plaintext = secrets.token_hex(32)
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    api_token = ApiToken(user_id=test_user.id, name="test-token", token_hash=token_hash)
    db_session.add(api_token)
    await db_session.commit()
    return plaintext


def _make_request_with_auth_service(db_session_factory):
    """Build a mock Request whose app.state.auth_service is a real AuthService."""
    from app.auth.service import AuthService

    auth_service = AuthService(db_session_factory)
    app = FastAPI()
    app.state.auth_service = auth_service
    request = MagicMock()
    request.app = app
    return request


# ---------------------------------------------------------------------------
# _extract_bearer_token tests
# ---------------------------------------------------------------------------


class TestExtractBearerToken:
    def test_valid_bearer(self):
        assert _extract_bearer_token("Bearer abc123") == "abc123"

    def test_bearer_case_insensitive(self):
        assert _extract_bearer_token("bearer abc123") == "abc123"
        assert _extract_bearer_token("BEARER abc123") == "abc123"

    def test_none_header(self):
        assert _extract_bearer_token(None) is None

    def test_empty_string(self):
        assert _extract_bearer_token("") is None

    def test_basic_scheme_rejected(self):
        assert _extract_bearer_token("Basic abc123") is None

    def test_no_space(self):
        assert _extract_bearer_token("Bearerabc123") is None

    def test_bearer_no_token(self):
        assert _extract_bearer_token("Bearer ") is None

    def test_bearer_with_spaces_in_token(self):
        # Only first space splits; rest is part of the token
        assert _extract_bearer_token("Bearer abc 123") == "abc 123"


# ---------------------------------------------------------------------------
# get_current_user_or_api tests
# ---------------------------------------------------------------------------


class TestDualAuthCookiePath:
    """Test that session cookie authentication works through dual-auth."""

    async def test_dual_auth_valid_cookie_returns_user(
        self, db_session, db_session_factory, test_user, valid_session
    ):
        """A valid session cookie should resolve to the correct user."""
        request = _make_request_with_auth_service(db_session_factory)
        user = await get_current_user_or_api(
            request=request,
            sempkm_session=valid_session.token,
            authorization=None,
            db=db_session,
        )
        assert user.id == test_user.id
        assert user.email == test_user.email

    async def test_dual_auth_expired_cookie_falls_through(
        self, db_session, db_session_factory, test_user, expired_session
    ):
        """An expired session cookie should not authenticate — raises 401."""
        request = _make_request_with_auth_service(db_session_factory)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_or_api(
                request=request,
                sempkm_session=expired_session.token,
                authorization=None,
                db=db_session,
            )
        assert exc_info.value.status_code == 401


class TestDualAuthBearerPath:
    """Test that Bearer token authentication works through dual-auth."""

    async def test_dual_auth_valid_bearer_returns_user(
        self, db_session, db_session_factory, test_user, valid_api_token
    ):
        """A valid Bearer token should resolve to the correct user."""
        request = _make_request_with_auth_service(db_session_factory)
        user = await get_current_user_or_api(
            request=request,
            sempkm_session=None,
            authorization=f"Bearer {valid_api_token}",
            db=db_session,
        )
        assert user.id == test_user.id
        assert user.email == test_user.email

    async def test_dual_auth_invalid_bearer_raises_401(
        self, db_session, db_session_factory
    ):
        """An invalid Bearer token should raise 401 with specific message."""
        request = _make_request_with_auth_service(db_session_factory)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_or_api(
                request=request,
                sempkm_session=None,
                authorization="Bearer invalid-token-value",
                db=db_session,
            )
        assert exc_info.value.status_code == 401
        assert "Invalid or expired API token" in exc_info.value.detail

    async def test_dual_auth_basic_scheme_rejected(
        self, db_session, db_session_factory
    ):
        """Basic auth scheme should not be accepted — raises 401."""
        request = _make_request_with_auth_service(db_session_factory)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_or_api(
                request=request,
                sempkm_session=None,
                authorization="Basic dXNlcjpwYXNz",
                db=db_session,
            )
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"


class TestDualAuthNoCredentials:
    """Test failure when neither cookie nor Bearer token is provided."""

    async def test_dual_auth_no_credentials_raises_401(
        self, db_session, db_session_factory
    ):
        """No cookie and no Authorization header should raise 401."""
        request = _make_request_with_auth_service(db_session_factory)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_or_api(
                request=request,
                sempkm_session=None,
                authorization=None,
                db=db_session,
            )
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"


class TestDualAuthPrecedence:
    """Test that cookie takes precedence over Bearer when both present."""

    async def test_cookie_preferred_over_bearer(
        self, db_session, db_session_factory, test_user, valid_session, valid_api_token
    ):
        """When both cookie and Bearer are present, cookie wins."""
        request = _make_request_with_auth_service(db_session_factory)
        user = await get_current_user_or_api(
            request=request,
            sempkm_session=valid_session.token,
            authorization=f"Bearer {valid_api_token}",
            db=db_session,
        )
        assert user.id == test_user.id


# ---------------------------------------------------------------------------
# Well-known endpoint tests (/.well-known/sempkm)
# ---------------------------------------------------------------------------


def _build_well_known_app(db_session_factory) -> FastAPI:
    """Build a minimal FastAPI app with the well-known router for testing.

    Uses the real well_known_router but overrides the DB session and
    auth service dependencies to use in-memory test fixtures.
    """
    from app.api.router import well_known_router
    from app.auth.service import AuthService
    from app.db.session import get_db_session

    test_app = FastAPI()
    auth_service = AuthService(db_session_factory)
    test_app.state.auth_service = auth_service

    test_app.include_router(well_known_router)

    return test_app


@pytest.fixture
def well_known_app(db_session_factory, db_session):
    """Provide a FastAPI test app with the well-known router and DB override."""
    from app.db.session import get_db_session

    test_app = _build_well_known_app(db_session_factory)

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db
    return test_app


class TestWellKnownEndpoint:
    """Test the /.well-known/sempkm discovery endpoint."""

    async def test_well_known_returns_json_with_correct_content_type(
        self, well_known_app, valid_session
    ):
        """Authenticated request returns application/json content-type."""
        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/.well-known/sempkm",
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]

    async def test_well_known_has_required_keys(
        self, well_known_app, valid_session
    ):
        """Response contains version, endpoints, auth, and capabilities keys."""
        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/.well-known/sempkm",
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "endpoints" in data
        assert "auth" in data
        assert "capabilities" in data

    async def test_well_known_returns_200_with_bearer_token(
        self, well_known_app, valid_api_token
    ):
        """Authenticated request via Bearer token returns the discovery document."""
        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/.well-known/sempkm",
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == settings.app_version

    async def test_well_known_rejects_unauthenticated(self, well_known_app):
        """Request without credentials returns 401."""
        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/.well-known/sempkm")
        assert resp.status_code == 401

    async def test_well_known_rejects_invalid_bearer(self, well_known_app):
        """Request with invalid Bearer token returns 401 with specific message."""
        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/.well-known/sempkm",
                headers={"Authorization": "Bearer invalid-token"},
            )
        assert resp.status_code == 401
        assert "Invalid or expired API token" in resp.json()["detail"]

    async def test_well_known_version_matches_config(
        self, well_known_app, valid_session
    ):
        """The returned version matches APP_VERSION from config."""
        from app.api.router import APP_VERSION

        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/.well-known/sempkm",
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        assert resp.json()["version"] == APP_VERSION

    async def test_well_known_endpoints_are_strings(
        self, well_known_app, valid_session
    ):
        """Each endpoint value should be a string URL path."""
        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/.well-known/sempkm",
                cookies={"sempkm_session": valid_session.token},
            )
        endpoints = resp.json()["endpoints"]
        for key, value in endpoints.items():
            assert isinstance(value, str), f"endpoints[{key!r}] is not a string"
            assert value.startswith("/"), f"endpoints[{key!r}] does not start with /"

    async def test_well_known_endpoints_structure(
        self, well_known_app, valid_session
    ):
        """The endpoints dict contains all required API paths."""
        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/.well-known/sempkm",
                cookies={"sempkm_session": valid_session.token},
            )
        endpoints = resp.json()["endpoints"]
        assert endpoints["types"] == "/api/types"
        assert endpoints["shapes"] == "/api/shapes/{type_iri}"
        assert endpoints["context_query"] == "/api/context-query"
        assert endpoints["sparql"] == "/api/sparql"
        assert endpoints["commands"] == "/api/commands"

    async def test_well_known_auth_methods(
        self, well_known_app, valid_session
    ):
        """The auth dict lists all supported authentication methods."""
        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/.well-known/sempkm",
                cookies={"sempkm_session": valid_session.token},
            )
        auth = resp.json()["auth"]
        assert auth["session"] is True
        assert auth["api_key"] is True
        assert auth["indieauth"] == "/auth/authorize"

    async def test_well_known_capabilities_list(
        self, well_known_app, valid_session
    ):
        """The capabilities list includes all expected capability names."""
        transport = ASGITransport(app=well_known_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/.well-known/sempkm",
                cookies={"sempkm_session": valid_session.token},
            )
        capabilities = resp.json()["capabilities"]
        expected = ["types", "shapes", "context-query", "sparql", "commands"]
        assert capabilities == expected


# ---------------------------------------------------------------------------
# /api/types endpoint tests
# ---------------------------------------------------------------------------

# Sample data for types endpoint tests
_SAMPLE_TYPES = [
    {"iri": "urn:sempkm:model:basic-pkm:Note", "label": "Note"},
    {"iri": "urn:sempkm:model:basic-pkm:Project", "label": "Project"},
    {"iri": "urn:sempkm:model:basic-pkm:Person", "label": "Person"},
]

_SAMPLE_ICON_MAP = {
    "urn:sempkm:model:basic-pkm:Note": {
        "icon": "file-text",
        "color": "#4a9eff",
        "size": 16,
    },
    "urn:sempkm:model:basic-pkm:Project": {
        "icon": "folder-kanban",
        "color": "#22c55e",
        "size": 16,
    },
}


@dataclass
class _FakeInstalledModel:
    model_id: str
    name: str


def _build_types_app(db_session_factory) -> FastAPI:
    """Build a minimal FastAPI app with the api_surface_router for testing.

    Mocks ShapesService, IconService, and ModelService on app.state.
    """
    from app.api.router import api_surface_router
    from app.auth.service import AuthService

    test_app = FastAPI()
    auth_service = AuthService(db_session_factory)
    test_app.state.auth_service = auth_service

    # Mock ShapesService
    mock_shapes = AsyncMock()
    mock_shapes.get_types = AsyncMock(return_value=list(_SAMPLE_TYPES))
    test_app.state.shapes_service = mock_shapes

    # Mock IconService
    mock_icons = MagicMock()
    mock_icons.get_icon_map = MagicMock(return_value=dict(_SAMPLE_ICON_MAP))
    test_app.state.icon_service = mock_icons

    # Mock ModelService
    mock_models = AsyncMock()
    mock_models.list_models = AsyncMock(
        return_value=[_FakeInstalledModel(model_id="basic-pkm", name="Basic PKM")]
    )
    test_app.state.model_service = mock_models

    test_app.include_router(api_surface_router)

    return test_app


@pytest.fixture
def types_app(db_session_factory, db_session):
    """Provide a FastAPI test app with the api_surface_router and mock services."""
    from app.db.session import get_db_session

    test_app = _build_types_app(db_session_factory)

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db
    return test_app


class TestTypesEndpoint:
    """Test the GET /api/types endpoint."""

    async def test_types_returns_list(self, types_app, valid_session):
        """Authenticated request returns a JSON object with a 'types' list."""
        transport = ASGITransport(app=types_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/types",
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "types" in data
        assert isinstance(data["types"], list)
        assert len(data["types"]) == 3

    async def test_types_entries_have_required_fields(self, types_app, valid_session):
        """Each type entry has iri and label fields."""
        transport = ASGITransport(app=types_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/types",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        for t in data["types"]:
            assert "iri" in t
            assert "label" in t
            assert isinstance(t["iri"], str)
            assert isinstance(t["label"], str)

    async def test_types_includes_icon_data(self, types_app, valid_session):
        """Types with icons in the icon map have icon and icon_color populated."""
        transport = ASGITransport(app=types_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/types",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        note = next(t for t in data["types"] if t["iri"].endswith(":Note"))
        assert note["icon"] == "file-text"
        assert note["icon_color"] == "#4a9eff"

    async def test_types_missing_icon_returns_none(self, types_app, valid_session):
        """Types without icons in the icon map have icon=None."""
        transport = ASGITransport(app=types_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/types",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        person = next(t for t in data["types"] if t["iri"].endswith(":Person"))
        assert person["icon"] is None
        assert person["icon_color"] is None

    async def test_types_includes_model_attribution(self, types_app, valid_session):
        """Types include model_id and model_name from IRI convention."""
        transport = ASGITransport(app=types_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/types",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        note = next(t for t in data["types"] if t["iri"].endswith(":Note"))
        assert note["model_id"] == "basic-pkm"
        assert note["model_name"] == "Basic PKM"

    async def test_types_requires_auth(self, types_app):
        """Request without credentials returns 401."""
        transport = ASGITransport(app=types_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/types")
        assert resp.status_code == 401

    async def test_types_works_with_bearer_token(
        self, types_app, valid_api_token
    ):
        """Authenticated request via Bearer token returns types."""
        transport = ASGITransport(app=types_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/types",
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )
        assert resp.status_code == 200
        assert len(resp.json()["types"]) == 3

    async def test_types_empty_when_no_models(self, db_session_factory, db_session, valid_session):
        """Returns empty types list (not error) when no models installed."""
        from app.api.router import api_surface_router
        from app.auth.service import AuthService
        from app.db.session import get_db_session

        test_app = FastAPI()
        test_app.state.auth_service = AuthService(db_session_factory)

        mock_shapes = AsyncMock()
        mock_shapes.get_types = AsyncMock(return_value=[])
        test_app.state.shapes_service = mock_shapes

        mock_icons = MagicMock()
        mock_icons.get_icon_map = MagicMock(return_value={})
        test_app.state.icon_service = mock_icons

        mock_models = AsyncMock()
        mock_models.list_models = AsyncMock(return_value=[])
        test_app.state.model_service = mock_models

        test_app.include_router(api_surface_router)

        async def override_db():
            yield db_session

        test_app.dependency_overrides[get_db_session] = override_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/types",
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        assert resp.json()["types"] == []
