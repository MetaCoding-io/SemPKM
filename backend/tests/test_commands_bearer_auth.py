"""Tests for require_role_or_api factory and commands endpoint Bearer auth.

Covers:
- require_role_or_api factory: bearer acceptance, cookie acceptance,
  wrong role rejection, no-credentials rejection, invalid bearer rejection
- POST /api/commands integration: Bearer token creates object, guest role 403
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.dependencies import require_role_or_api, get_current_user_or_api
from app.auth.models import ApiToken, User, UserSession
from app.config import settings
from app.db.base import Base


# ---------------------------------------------------------------------------
# Fixtures (same patterns as test_api_surface.py)
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
    """Create a test user with owner role."""
    user = User(id=uuid.uuid4(), email="test@example.com", role="owner")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def guest_user(db_session: AsyncSession) -> User:
    """Create a test user with guest role (insufficient for commands)."""
    user = User(id=uuid.uuid4(), email="guest@example.com", role="guest")
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
async def valid_api_token(db_session: AsyncSession, test_user: User) -> str:
    """Create a valid API token row and return the plaintext token."""
    plaintext = secrets.token_hex(32)
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    api_token = ApiToken(user_id=test_user.id, name="test-token", token_hash=token_hash)
    db_session.add(api_token)
    await db_session.commit()
    return plaintext


@pytest.fixture
async def guest_api_token(db_session: AsyncSession, guest_user: User) -> str:
    """Create a valid API token for the guest user."""
    plaintext = secrets.token_hex(32)
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    api_token = ApiToken(user_id=guest_user.id, name="guest-token", token_hash=token_hash)
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
# require_role_or_api factory unit tests
# ---------------------------------------------------------------------------


class TestRequireRoleOrApiAcceptsBearerToken:
    """Verify the factory resolves a user from Bearer token."""

    async def test_require_role_or_api_accepts_bearer_token(
        self, db_session, db_session_factory, test_user, valid_api_token
    ):
        """A valid Bearer token should authenticate and pass role check."""
        request = _make_request_with_auth_service(db_session_factory)
        # Resolve user via dual-auth
        user = await get_current_user_or_api(
            request=request,
            sempkm_session=None,
            authorization=f"Bearer {valid_api_token}",
            db=db_session,
        )
        assert user.id == test_user.id
        assert user.role == "owner"
        # Now verify role check passes
        assert user.role in ("owner", "member")


class TestRequireRoleOrApiAcceptsCookie:
    """Verify cookie auth still works through the factory."""

    async def test_require_role_or_api_accepts_cookie(
        self, db_session, db_session_factory, test_user, valid_session
    ):
        """A valid session cookie should authenticate and pass role check."""
        request = _make_request_with_auth_service(db_session_factory)
        user = await get_current_user_or_api(
            request=request,
            sempkm_session=valid_session.token,
            authorization=None,
            db=db_session,
        )
        assert user.id == test_user.id
        assert user.role == "owner"


class TestRequireRoleOrApiRejectsWrongRole:
    """Verify 403 for insufficient role."""

    async def test_require_role_or_api_rejects_wrong_role(
        self, db_session, db_session_factory, guest_user, guest_api_token
    ):
        """A user with guest role should be authenticated but get 403 from role check."""
        request = _make_request_with_auth_service(db_session_factory)
        user = await get_current_user_or_api(
            request=request,
            sempkm_session=None,
            authorization=f"Bearer {guest_api_token}",
            db=db_session,
        )
        assert user.id == guest_user.id
        assert user.role == "guest"
        # Role check should reject
        assert user.role not in ("owner", "member")


class TestRequireRoleOrApiRejectsNoCredentials:
    """Verify 401 with no auth."""

    async def test_require_role_or_api_rejects_no_credentials(
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


class TestRequireRoleOrApiRejectsInvalidBearer:
    """Verify 401 with bad token."""

    async def test_require_role_or_api_rejects_invalid_bearer(
        self, db_session, db_session_factory
    ):
        """An invalid Bearer token should raise 401 with specific message."""
        request = _make_request_with_auth_service(db_session_factory)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_or_api(
                request=request,
                sempkm_session=None,
                authorization="Bearer totally-invalid-token",
                db=db_session,
            )
        assert exc_info.value.status_code == 401
        assert "Invalid or expired API token" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Integration tests: POST /api/commands with Bearer auth
# ---------------------------------------------------------------------------


@dataclass
class _FakeEventResult:
    """Minimal event result for mocking EventStore.commit()."""

    event_iri: str = "urn:sempkm:event:test-event-1"
    timestamp: str = "2025-01-01T00:00:00Z"


def _build_commands_app(db_session_factory) -> FastAPI:
    """Build a FastAPI app with the commands router and mocked services."""
    from app.commands.router import router as commands_router
    from app.auth.service import AuthService
    from app.events.store import Operation

    test_app = FastAPI()
    auth_service = AuthService(db_session_factory)
    test_app.state.auth_service = auth_service

    # Mock triplestore client
    mock_triplestore = AsyncMock()
    test_app.state.triplestore_client = mock_triplestore

    # Mock validation queue
    mock_validation_queue = AsyncMock()
    mock_validation_queue.enqueue = AsyncMock()
    test_app.state.validation_queue = mock_validation_queue

    # Mock webhook service
    mock_webhook_service = AsyncMock()
    mock_webhook_service.dispatch = AsyncMock()
    test_app.state.webhook_service = mock_webhook_service

    test_app.include_router(commands_router)

    return test_app


@pytest.fixture
def commands_app(db_session_factory, db_session):
    """Provide a FastAPI test app with commands router and mocked services."""
    from app.db.session import get_db_session
    from app.dependencies import get_triplestore_client, get_validation_queue, get_webhook_service

    test_app = _build_commands_app(db_session_factory)

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db
    test_app.dependency_overrides[get_triplestore_client] = lambda: test_app.state.triplestore_client
    test_app.dependency_overrides[get_validation_queue] = lambda: test_app.state.validation_queue
    test_app.dependency_overrides[get_webhook_service] = lambda: test_app.state.webhook_service

    return test_app


class TestCommandsEndpointAcceptsBearer:
    """Integration test: POST /api/commands with Bearer token creates an object."""

    async def test_commands_endpoint_accepts_bearer(
        self, commands_app, valid_api_token
    ):
        """Bearer token auth should be accepted and create an object."""
        from app.events.store import Operation

        fake_operation = Operation(
            operation_type="object.create",
            affected_iris=["urn:sempkm:obj:test-obj-1"],
            description="Created Note",
            data_triples=[],
            materialize_inserts=[],
            materialize_deletes=[],
        )

        with (
            patch("app.commands.router.dispatch", new_callable=AsyncMock) as mock_dispatch,
            patch("app.commands.router.EventStore") as MockEventStore,
        ):
            mock_dispatch.return_value = fake_operation
            mock_store_instance = AsyncMock()
            mock_store_instance.commit = AsyncMock(return_value=_FakeEventResult())
            MockEventStore.return_value = mock_store_instance

            transport = ASGITransport(app=commands_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/commands",
                    json={
                        "command": "object.create",
                        "params": {
                            "type": "urn:sempkm:model:basic-pkm:Note",
                            "properties": {
                                "dcterms:title": "Test from extension",
                            },
                        },
                    },
                    headers={"Authorization": f"Bearer {valid_api_token}"},
                )

            assert resp.status_code == 200
            data = resp.json()
            assert data["results"][0]["iri"] == "urn:sempkm:obj:test-obj-1"
            assert data["results"][0]["command"] == "object.create"
            assert data["event_iri"] == "urn:sempkm:event:test-event-1"
            mock_dispatch.assert_called_once()

    async def test_commands_endpoint_accepts_cookie(
        self, commands_app, valid_session
    ):
        """Cookie auth should still work for the commands endpoint."""
        from app.events.store import Operation

        fake_operation = Operation(
            operation_type="object.create",
            affected_iris=["urn:sempkm:obj:test-obj-2"],
            description="Created Note",
            data_triples=[],
            materialize_inserts=[],
            materialize_deletes=[],
        )

        with (
            patch("app.commands.router.dispatch", new_callable=AsyncMock) as mock_dispatch,
            patch("app.commands.router.EventStore") as MockEventStore,
        ):
            mock_dispatch.return_value = fake_operation
            mock_store_instance = AsyncMock()
            mock_store_instance.commit = AsyncMock(return_value=_FakeEventResult())
            MockEventStore.return_value = mock_store_instance

            transport = ASGITransport(app=commands_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/commands",
                    json={
                        "command": "object.create",
                        "params": {
                            "type": "urn:sempkm:model:basic-pkm:Note",
                            "properties": {
                                "dcterms:title": "Test via cookie",
                            },
                        },
                    },
                    cookies={"sempkm_session": valid_session.token},
                )

            assert resp.status_code == 200
            data = resp.json()
            assert data["results"][0]["iri"] == "urn:sempkm:obj:test-obj-2"


class TestCommandsEndpointRejectsGuestBearer:
    """Integration test: guest role gets 403."""

    async def test_commands_endpoint_rejects_guest_bearer(
        self, commands_app, guest_api_token
    ):
        """Guest role should be authenticated but rejected with 403."""
        transport = ASGITransport(app=commands_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/commands",
                json={
                    "command": "object.create",
                    "params": {
                        "type": "urn:sempkm:model:basic-pkm:Note",
                        "properties": {
                            "dcterms:title": "Should fail",
                        },
                    },
                },
                headers={"Authorization": f"Bearer {guest_api_token}"},
            )
        assert resp.status_code == 403
        assert "Requires role" in resp.json()["detail"]


class TestCommandsEndpointRejectsNoAuth:
    """Integration test: no credentials returns 401."""

    async def test_commands_endpoint_rejects_no_auth(self, commands_app):
        """No credentials should return 401."""
        transport = ASGITransport(app=commands_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/commands",
                json={
                    "command": "object.create",
                    "params": {
                        "type": "urn:sempkm:model:basic-pkm:Note",
                        "properties": {"dcterms:title": "Should fail"},
                    },
                },
            )
        assert resp.status_code == 401

    async def test_commands_endpoint_rejects_invalid_bearer(self, commands_app):
        """Invalid Bearer token should return 401 with specific message."""
        transport = ASGITransport(app=commands_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/commands",
                json={
                    "command": "object.create",
                    "params": {
                        "type": "urn:sempkm:model:basic-pkm:Note",
                        "properties": {"dcterms:title": "Should fail"},
                    },
                },
                headers={"Authorization": "Bearer totally-invalid-token"},
            )
        assert resp.status_code == 401
        assert "Invalid or expired API token" in resp.json()["detail"]
