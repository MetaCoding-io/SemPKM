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
    from unittest.mock import patch
    from app.db.session import get_db_session

    test_app = _build_types_app(db_session_factory)

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db

    # Patch IconService so it returns the test icon map without needing /app/models
    mock_icon_svc = MagicMock()
    mock_icon_svc.get_icon_map = MagicMock(return_value=dict(_SAMPLE_ICON_MAP))
    mock_icon_svc.set_user_type_icons = MagicMock()

    patcher = patch("app.api.router.IconService", return_value=mock_icon_svc)
    patcher.start()

    yield test_app

    patcher.stop()


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
        """Each type entry has iri, label, icon, and model_id fields."""
        transport = ASGITransport(app=types_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/types",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        required_keys = {"iri", "label", "icon", "icon_color", "model_id", "model_name"}
        for t in data["types"]:
            missing = required_keys - set(t.keys())
            assert not missing, f"Type {t.get('iri', '?')} missing keys: {missing}"
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
        from unittest.mock import patch
        from app.api.router import api_surface_router
        from app.auth.service import AuthService
        from app.db.session import get_db_session

        test_app = FastAPI()
        test_app.state.auth_service = AuthService(db_session_factory)

        mock_shapes = AsyncMock()
        mock_shapes.get_types = AsyncMock(return_value=[])
        test_app.state.shapes_service = mock_shapes

        mock_models = AsyncMock()
        mock_models.list_models = AsyncMock(return_value=[])
        test_app.state.model_service = mock_models

        test_app.include_router(api_surface_router)

        async def override_db():
            yield db_session

        # Patch IconService to return empty icon map
        mock_icon_svc = MagicMock()
        mock_icon_svc.get_icon_map = MagicMock(return_value={})
        mock_icon_svc.set_user_type_icons = MagicMock()

        with patch("app.api.router.IconService", return_value=mock_icon_svc):
            test_app.dependency_overrides[get_db_session] = override_db

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/types",
                    cookies={"sempkm_session": valid_session.token},
                )
            assert resp.status_code == 200
            assert resp.json()["types"] == []


# ---------------------------------------------------------------------------
# /api/shapes/{type_iri} endpoint tests
# ---------------------------------------------------------------------------

# Sample data for shapes endpoint tests — mirrors real SHACL shapes structure.
# Uses the actual dataclasses from shapes.py so conversions are tested end-to-end.

from app.services.shapes import NodeShapeForm, PropertyGroup, PropertyShape

_SAMPLE_NOTE_SHAPE = NodeShapeForm(
    shape_iri="urn:sempkm:model:basic-pkm:shapes:NoteShape",
    target_class="urn:sempkm:model:basic-pkm:Note",
    label="Note",
    groups=[
        PropertyGroup(
            iri="urn:sempkm:model:basic-pkm:shapes:CoreGroup",
            label="Core",
            order=1.0,
        ),
        PropertyGroup(
            iri="urn:sempkm:model:basic-pkm:shapes:MetadataGroup",
            label="Metadata",
            order=2.0,
        ),
    ],
    properties=[
        PropertyShape(
            path="http://purl.org/dc/terms/title",
            name="Title",
            datatype="http://www.w3.org/2001/XMLSchema#string",
            order=1.0,
            group="urn:sempkm:model:basic-pkm:shapes:CoreGroup",
            min_count=1,
            max_count=1,
            description="The display name for this note.",
        ),
        PropertyShape(
            path="http://www.w3.org/2000/01/rdf-schema#comment",
            name="Body",
            datatype="http://www.w3.org/2001/XMLSchema#string",
            order=2.0,
            group="urn:sempkm:model:basic-pkm:shapes:CoreGroup",
            min_count=0,
            max_count=1,
        ),
        PropertyShape(
            path="urn:sempkm:model:basic-pkm:noteStatus",
            name="Status",
            datatype="http://www.w3.org/2001/XMLSchema#string",
            order=3.0,
            group="urn:sempkm:model:basic-pkm:shapes:MetadataGroup",
            min_count=0,
            max_count=1,
            in_values=["draft", "active", "archived"],
            default_value="draft",
            helptext="Current lifecycle status of the note.",
        ),
        PropertyShape(
            path="urn:sempkm:model:basic-pkm:relatedTo",
            name="Related To",
            target_class="urn:sempkm:model:basic-pkm:Note",
            order=4.0,
            min_count=0,
            max_count=None,
            description="Other notes related to this one.",
        ),
    ],
    helptext="A free-form note for capturing ideas and information.",
)


def _build_shapes_app(db_session_factory, mock_form_return=None) -> FastAPI:
    """Build a minimal FastAPI app with the shapes endpoint for testing.

    Mocks ShapesService.get_form_for_type() to return the provided form
    (or None if not specified). Also includes types endpoint mocks so
    the router doesn't fail on missing app.state attributes.
    """
    from app.api.router import api_surface_router
    from app.auth.service import AuthService

    test_app = FastAPI()
    auth_service = AuthService(db_session_factory)
    test_app.state.auth_service = auth_service

    # Mock ShapesService with get_form_for_type
    mock_shapes = AsyncMock()
    mock_shapes.get_form_for_type = AsyncMock(return_value=mock_form_return)
    # Also need get_types for the types endpoint (router includes both)
    mock_shapes.get_types = AsyncMock(return_value=[])
    test_app.state.shapes_service = mock_shapes

    # Mock ModelService (required by types endpoint on same router)
    mock_models = AsyncMock()
    mock_models.list_models = AsyncMock(return_value=[])
    test_app.state.model_service = mock_models

    test_app.include_router(api_surface_router)

    return test_app


@pytest.fixture
def shapes_app(db_session_factory, db_session):
    """Provide a FastAPI test app with a mock shape for the Note type."""
    from app.db.session import get_db_session

    test_app = _build_shapes_app(db_session_factory, mock_form_return=_SAMPLE_NOTE_SHAPE)

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db
    return test_app


@pytest.fixture
def shapes_app_404(db_session_factory, db_session):
    """Provide a FastAPI test app where get_form_for_type returns None (404)."""
    from app.db.session import get_db_session

    test_app = _build_shapes_app(db_session_factory, mock_form_return=None)

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db
    return test_app


class TestShapesEndpoint:
    """Test the GET /api/shapes/{type_iri} endpoint."""

    async def test_shapes_returns_valid_json(self, shapes_app, valid_session):
        """Known type returns 200 with JSON containing shape fields."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:sempkm:model:basic-pkm:Note",
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "shape_iri" in data
        assert "target_class" in data
        assert "label" in data
        assert "groups" in data
        assert "properties" in data

    async def test_shapes_has_correct_top_level_fields(self, shapes_app, valid_session):
        """Response top-level fields match the source NodeShapeForm."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:sempkm:model:basic-pkm:Note",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        assert data["shape_iri"] == "urn:sempkm:model:basic-pkm:shapes:NoteShape"
        assert data["target_class"] == "urn:sempkm:model:basic-pkm:Note"
        assert data["label"] == "Note"
        assert data["helptext"] == "A free-form note for capturing ideas and information."

    async def test_shapes_has_properties(self, shapes_app, valid_session):
        """Response has non-empty properties list."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:sempkm:model:basic-pkm:Note",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        assert len(data["properties"]) == 4

    async def test_shapes_property_fields(self, shapes_app, valid_session):
        """Each property has path, name, order, datatype, min_count, max_count."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:sempkm:model:basic-pkm:Note",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        required_keys = {"path", "name", "order", "datatype", "min_count", "max_count"}
        for prop in data["properties"]:
            missing = required_keys - set(prop.keys())
            assert not missing, f"Property {prop.get('name', '?')} missing keys: {missing}"
            assert isinstance(prop["path"], str)
            assert isinstance(prop["name"], str)
            assert isinstance(prop["order"], (int, float))
            assert isinstance(prop["min_count"], int)
            assert prop["max_count"] is None or isinstance(prop["max_count"], int)

    async def test_shapes_preserves_constraints(self, shapes_app, valid_session):
        """in_values, min_count, max_count round-trip correctly."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:sempkm:model:basic-pkm:Note",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        # Title: min_count=1, max_count=1
        title = next(p for p in data["properties"] if p["name"] == "Title")
        assert title["min_count"] == 1
        assert title["max_count"] == 1

        # Status: in_values=["draft", "active", "archived"], default_value="draft"
        status = next(p for p in data["properties"] if p["name"] == "Status")
        assert status["in_values"] == ["draft", "active", "archived"]
        assert status["default_value"] == "draft"

        # Related To: max_count=None (unbounded)
        related = next(p for p in data["properties"] if p["name"] == "Related To")
        assert related["max_count"] is None
        assert related["min_count"] == 0

    async def test_shapes_preserves_target_class_on_property(self, shapes_app, valid_session):
        """Object reference properties have target_class set."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:sempkm:model:basic-pkm:Note",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        related = next(p for p in data["properties"] if p["name"] == "Related To")
        assert related["target_class"] == "urn:sempkm:model:basic-pkm:Note"
        # Literal properties should have target_class=None
        title = next(p for p in data["properties"] if p["name"] == "Title")
        assert title["target_class"] is None

    async def test_shapes_groups_with_correct_ordering(self, shapes_app, valid_session):
        """Groups are returned with correct iri, label, and order."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:sempkm:model:basic-pkm:Note",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        groups = data["groups"]
        assert len(groups) == 2
        assert groups[0]["label"] == "Core"
        assert groups[0]["order"] == 1.0
        assert groups[1]["label"] == "Metadata"
        assert groups[1]["order"] == 2.0
        # Each group has iri
        assert groups[0]["iri"].endswith(":CoreGroup")
        assert groups[1]["iri"].endswith(":MetadataGroup")

    async def test_shapes_unknown_type_returns_404(self, shapes_app_404, valid_session):
        """Unknown type IRI returns 404 with structured error detail."""
        transport = ASGITransport(app=shapes_app_404)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:nonexistent:Type",
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "No shape found for type: urn:nonexistent:Type"

    async def test_shapes_requires_auth(self, shapes_app):
        """Request without credentials returns 401."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/shapes/urn:sempkm:model:basic-pkm:Note")
        assert resp.status_code == 401

    async def test_shapes_works_with_bearer_token(self, shapes_app, valid_api_token):
        """Authenticated request via Bearer token returns shape."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:sempkm:model:basic-pkm:Note",
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )
        assert resp.status_code == 200
        assert len(resp.json()["properties"]) == 4

    async def test_shapes_helptext_on_properties(self, shapes_app, valid_session):
        """Property-level helptext is serialized correctly."""
        transport = ASGITransport(app=shapes_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/shapes/urn:sempkm:model:basic-pkm:Note",
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        status = next(p for p in data["properties"] if p["name"] == "Status")
        assert status["helptext"] == "Current lifecycle status of the note."
        # Properties without helptext return None
        body = next(p for p in data["properties"] if p["name"] == "Body")
        assert body["helptext"] is None


# ---------------------------------------------------------------------------
# POST /api/context-query endpoint tests
# ---------------------------------------------------------------------------

from app.services.search import SearchResult


def _build_context_query_app(
    db_session_factory,
    triplestore_query_results: dict | None = None,
    search_results: list | None = None,
    label_results: dict | None = None,
) -> FastAPI:
    """Build a minimal FastAPI app with the context-query endpoint for testing.

    Mocks TriplestoreClient, SearchService, and LabelService on app.state.
    Also includes types endpoint mocks so the router doesn't fail on
    missing app.state attributes.
    """
    from app.api.router import api_surface_router
    from app.auth.service import AuthService

    test_app = FastAPI()
    auth_service = AuthService(db_session_factory)
    test_app.state.auth_service = auth_service

    # Mock TriplestoreClient — returns configurable SPARQL results
    mock_triplestore = AsyncMock()

    # Build side_effect that returns different results based on query content
    _triplestore_results = triplestore_query_results or {}

    async def _mock_query(sparql: str) -> dict:
        """Route SPARQL queries to their mock results."""
        # URL matching query contains FILTER(STR(?val)
        if "FILTER(STR(?val)" in sparql:
            return _triplestore_results.get(
                "url_match",
                {"results": {"bindings": []}},
            )
        # Type resolution query contains "?s a ?type"
        if "?s a ?type" in sparql:
            return _triplestore_results.get(
                "type_resolve",
                {"results": {"bindings": []}},
            )
        return {"results": {"bindings": []}}

    mock_triplestore.query = AsyncMock(side_effect=_mock_query)
    test_app.state.triplestore_client = mock_triplestore

    # Mock SearchService
    mock_search = AsyncMock()
    mock_search.search = AsyncMock(return_value=search_results or [])
    test_app.state.search_service = mock_search

    # Mock LabelService
    mock_labels = AsyncMock()
    _label_map = label_results or {}

    async def _mock_resolve_batch(iris: list[str]) -> dict[str, str]:
        return {iri: _label_map.get(iri, iri) for iri in iris}

    mock_labels.resolve_batch = AsyncMock(side_effect=_mock_resolve_batch)
    test_app.state.label_service = mock_labels

    # Mock ShapesService + ModelService (required by types endpoint on same router)
    mock_shapes = AsyncMock()
    mock_shapes.get_types = AsyncMock(return_value=[])
    mock_shapes.get_form_for_type = AsyncMock(return_value=None)
    test_app.state.shapes_service = mock_shapes

    mock_models = AsyncMock()
    mock_models.list_models = AsyncMock(return_value=[])
    test_app.state.model_service = mock_models

    test_app.include_router(api_surface_router)

    return test_app


# --- Sample data for context-query tests ---

_URL_MATCH_BINDINGS = {
    "url_match": {
        "results": {
            "bindings": [
                {"s": {"value": "urn:sempkm:obj:note-1"}},
                {"s": {"value": "urn:sempkm:obj:note-2"}},
            ]
        }
    },
    "type_resolve": {
        "results": {
            "bindings": [
                {
                    "s": {"value": "urn:sempkm:obj:note-1"},
                    "type": {"value": "urn:sempkm:model:basic-pkm:Note"},
                },
                {
                    "s": {"value": "urn:sempkm:obj:note-2"},
                    "type": {"value": "urn:sempkm:model:basic-pkm:Note"},
                },
            ]
        }
    },
}

_KEYWORD_SEARCH_RESULTS = [
    SearchResult(
        iri="urn:sempkm:obj:project-1",
        type="urn:sempkm:model:basic-pkm:Project",
        label="My Project",
        snippet="A project about <b>knowledge</b> management",
        score=0.95,
    ),
]

_DEDUP_SEARCH_RESULTS = [
    SearchResult(
        iri="urn:sempkm:obj:note-1",  # Same as URL match
        type="urn:sempkm:model:basic-pkm:Note",
        label="Note One",
        snippet="Overlapping result from FTS",
        score=0.8,
    ),
    SearchResult(
        iri="urn:sempkm:obj:project-1",
        type="urn:sempkm:model:basic-pkm:Project",
        label="My Project",
        snippet="A unique FTS result",
        score=0.7,
    ),
]

_LABEL_MAP = {
    "urn:sempkm:obj:note-1": "Note One",
    "urn:sempkm:obj:note-2": "Note Two",
    "urn:sempkm:obj:project-1": "My Project",
    "urn:sempkm:model:basic-pkm:Note": "Note",
    "urn:sempkm:model:basic-pkm:Project": "Project",
}


@pytest.fixture
def context_query_url_app(db_session_factory, db_session):
    """App that returns URL match results."""
    from app.db.session import get_db_session

    test_app = _build_context_query_app(
        db_session_factory,
        triplestore_query_results=_URL_MATCH_BINDINGS,
        label_results=_LABEL_MAP,
    )

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db
    return test_app


@pytest.fixture
def context_query_keyword_app(db_session_factory, db_session):
    """App that returns keyword search results."""
    from app.db.session import get_db_session

    type_bindings = {
        "type_resolve": {
            "results": {
                "bindings": [
                    {
                        "s": {"value": "urn:sempkm:obj:project-1"},
                        "type": {"value": "urn:sempkm:model:basic-pkm:Project"},
                    },
                ]
            }
        },
    }

    test_app = _build_context_query_app(
        db_session_factory,
        triplestore_query_results=type_bindings,
        search_results=_KEYWORD_SEARCH_RESULTS,
        label_results=_LABEL_MAP,
    )

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db
    return test_app


@pytest.fixture
def context_query_empty_app(db_session_factory, db_session):
    """App that returns no results for any query."""
    from app.db.session import get_db_session

    test_app = _build_context_query_app(db_session_factory)

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db
    return test_app


@pytest.fixture
def context_query_dedup_app(db_session_factory, db_session):
    """App with overlapping URL + keyword results (tests deduplication)."""
    from app.db.session import get_db_session

    test_app = _build_context_query_app(
        db_session_factory,
        triplestore_query_results=_URL_MATCH_BINDINGS,
        search_results=_DEDUP_SEARCH_RESULTS,
        label_results=_LABEL_MAP,
    )

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db
    return test_app


class TestContextQueryEndpoint:
    """Test the POST /api/context-query endpoint."""

    async def test_context_query_url_match(self, context_query_url_app, valid_session):
        """URL matching returns results with match_type 'url'."""
        transport = ASGITransport(app=context_query_url_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"url": "https://example.com/page"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["results"]) == 2
        # All results should have match_type 'url'
        for r in data["results"]:
            assert r["match_type"] == "url"
            assert r["iri"].startswith("urn:sempkm:obj:")
            assert r["label"]  # non-empty label

    async def test_context_query_keyword_match(self, context_query_keyword_app, valid_session):
        """Keyword matching returns results with match_type 'keyword'."""
        transport = ASGITransport(app=context_query_keyword_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"keywords": "knowledge management"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        result = data["results"][0]
        assert result["match_type"] == "keyword"
        assert result["iri"] == "urn:sempkm:obj:project-1"
        assert result["snippet"] is not None

    async def test_context_query_title_match(self, context_query_keyword_app, valid_session):
        """Title-only matching returns results with match_type 'title'."""
        transport = ASGITransport(app=context_query_keyword_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"title": "Knowledge Management Overview"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for r in data["results"]:
            assert r["match_type"] == "title"

    async def test_context_query_empty_results(self, context_query_empty_app, valid_session):
        """No matches returns 200 with empty array (not 404 or error)."""
        transport = ASGITransport(app=context_query_empty_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"url": "https://nonexistent.example.com"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["total"] == 0

    async def test_context_query_requires_field(self, context_query_empty_app, valid_session):
        """Empty request body returns 400 with validation message."""
        transport = ASGITransport(app=context_query_empty_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 400
        assert "at least one" in resp.json()["detail"].lower()

    async def test_context_query_requires_auth(self, context_query_empty_app):
        """Request without credentials returns 401."""
        transport = ASGITransport(app=context_query_empty_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"keywords": "test"},
            )
        assert resp.status_code == 401

    async def test_context_query_deduplicates(self, context_query_dedup_app, valid_session):
        """Same IRI from URL + keyword match appears only once (URL wins)."""
        transport = ASGITransport(app=context_query_dedup_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"url": "https://example.com/page", "keywords": "notes"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        iris = [r["iri"] for r in data["results"]]
        # Should be deduplicated — no duplicate IRIs
        assert len(iris) == len(set(iris))
        # note-1 appears in both URL and keyword results but should be 'url' (first match wins)
        note1 = next(r for r in data["results"] if r["iri"] == "urn:sempkm:obj:note-1")
        assert note1["match_type"] == "url"
        # project-1 is keyword-only
        proj = next(r for r in data["results"] if r["iri"] == "urn:sempkm:obj:project-1")
        assert proj["match_type"] == "keyword"
        # Total should be 3: note-1, note-2 (from URL), project-1 (from keyword)
        assert data["total"] == 3

    async def test_context_query_includes_type_info(self, context_query_url_app, valid_session):
        """Results include type_iri and type_label from SPARQL type resolution."""
        transport = ASGITransport(app=context_query_url_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"url": "https://example.com/page"},
                cookies={"sempkm_session": valid_session.token},
            )
        data = resp.json()
        for r in data["results"]:
            assert r["type_iri"] == "urn:sempkm:model:basic-pkm:Note"
            assert r["type_label"] == "Note"

    async def test_context_query_works_with_bearer_token(
        self, context_query_keyword_app, valid_api_token
    ):
        """Authenticated request via Bearer token works."""
        transport = ASGITransport(app=context_query_keyword_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"keywords": "knowledge"},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_context_query_url_sparql_failure_degrades(
        self, db_session_factory, db_session, valid_session
    ):
        """SPARQL URL matching failure doesn't block keyword results (graceful degradation)."""
        from app.db.session import get_db_session

        test_app = _build_context_query_app(
            db_session_factory,
            search_results=_KEYWORD_SEARCH_RESULTS,
            label_results=_LABEL_MAP,
        )
        # Override triplestore to raise on URL match query
        async def _failing_query(sparql: str) -> dict:
            if "FILTER(STR(?val)" in sparql:
                raise ConnectionError("Triplestore unavailable")
            return {"results": {"bindings": []}}

        test_app.state.triplestore_client.query = AsyncMock(side_effect=_failing_query)

        async def override_db():
            yield db_session
        test_app.dependency_overrides[get_db_session] = override_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"url": "https://example.com", "keywords": "knowledge"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        # Keyword results still returned despite SPARQL failure
        assert data["total"] >= 1
        assert data["results"][0]["match_type"] == "keyword"

    async def test_context_query_fts_failure_degrades(
        self, db_session_factory, db_session, valid_session
    ):
        """FTS search failure doesn't block URL match results (graceful degradation)."""
        from app.db.session import get_db_session

        test_app = _build_context_query_app(
            db_session_factory,
            triplestore_query_results=_URL_MATCH_BINDINGS,
            label_results=_LABEL_MAP,
        )
        # Override search to raise
        test_app.state.search_service.search = AsyncMock(
            side_effect=RuntimeError("FTS index corrupted")
        )

        async def override_db():
            yield db_session
        test_app.dependency_overrides[get_db_session] = override_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"url": "https://example.com", "keywords": "knowledge"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        # URL results still returned despite FTS failure
        assert data["total"] == 2
        for r in data["results"]:
            assert r["match_type"] == "url"

    async def test_context_query_label_resolution_failure_degrades(
        self, db_session_factory, db_session, valid_session
    ):
        """Label resolution failure falls back to IRI as label."""
        from app.db.session import get_db_session

        test_app = _build_context_query_app(
            db_session_factory,
            triplestore_query_results=_URL_MATCH_BINDINGS,
        )
        # Override label service to raise
        test_app.state.label_service.resolve_batch = AsyncMock(
            side_effect=RuntimeError("Label service down")
        )

        async def override_db():
            yield db_session
        test_app.dependency_overrides[get_db_session] = override_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"url": "https://example.com/page"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        # Labels fall back to IRI when label service fails
        for r in data["results"]:
            assert r["label"] == r["iri"]

    async def test_context_query_type_resolution_failure_degrades(
        self, db_session_factory, db_session, valid_session
    ):
        """Type resolution failure returns results with type_iri=None."""
        from app.db.session import get_db_session

        # Only URL match returns data; type query raises
        url_only_bindings = {
            "url_match": _URL_MATCH_BINDINGS["url_match"],
        }
        test_app = _build_context_query_app(
            db_session_factory,
            triplestore_query_results=url_only_bindings,
            label_results=_LABEL_MAP,
        )
        # Override triplestore to fail on type resolution but succeed on URL match
        original_query = test_app.state.triplestore_client.query.side_effect

        async def _type_failing_query(sparql: str) -> dict:
            if "?s a ?type" in sparql:
                raise ConnectionError("Type resolution failed")
            return await original_query(sparql)

        test_app.state.triplestore_client.query = AsyncMock(side_effect=_type_failing_query)

        async def override_db():
            yield db_session
        test_app.dependency_overrides[get_db_session] = override_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/context-query",
                json={"url": "https://example.com/page"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        # Type info missing due to failure — both should be None
        for r in data["results"]:
            assert r["type_iri"] is None
            assert r["type_label"] is None


class TestSparqlEscapeStr:
    """Test the sparql_escape_string helper used in context-query SPARQL building."""

    def test_plain_string(self):
        from app.sparql.builder import sparql_escape_string
        assert sparql_escape_string("hello") == "hello"

    def test_escapes_double_quotes(self):
        from app.sparql.builder import sparql_escape_string
        assert sparql_escape_string('say "hi"') == 'say \\"hi\\"'

    def test_escapes_backslash(self):
        from app.sparql.builder import sparql_escape_string
        assert sparql_escape_string("path\\to") == "path\\\\to"

    def test_escapes_newline(self):
        from app.sparql.builder import sparql_escape_string
        assert sparql_escape_string("line\nbreak") == "line\\nbreak"

    def test_combined_special_chars(self):
        from app.sparql.builder import sparql_escape_string
        result = sparql_escape_string('a\\b"c\nd')
        assert result == 'a\\\\b\\"c\\nd'
