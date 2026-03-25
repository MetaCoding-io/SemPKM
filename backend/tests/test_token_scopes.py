"""Tests for fine-grained API token scope enforcement (F-016).

Covers:
- scope_required() dependency: scoped token denied, wildcard passes, session bypasses
- SPARQL endpoint scope enforcement via Bearer token
- Commands endpoint scope enforcement (already wired, verify interaction)
- Token creation with scopes via JSON API
- Model-level scope property parsing
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.dependencies import get_current_user_or_api, scope_required
from app.auth.models import ApiToken, User, UserSession, VALID_SCOPES
from app.auth.service import AuthService
from app.config import settings
from app.db.base import Base
from app.db.session import get_db_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_engine():
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
async def owner_user(db_session: AsyncSession) -> User:
    user = User(id=uuid.uuid4(), email="owner@example.com", role="owner")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def member_user(db_session: AsyncSession) -> User:
    user = User(id=uuid.uuid4(), email="member@example.com", role="member")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def valid_session(db_session: AsyncSession, owner_user: User) -> UserSession:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
    session = UserSession(token=token, user_id=owner_user.id, expires_at=expires_at)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


def _create_api_token_row(
    db_session: AsyncSession,
    user: User,
    scope: str = "*",
    name: str = "test-token",
) -> tuple[str, ApiToken]:
    """Synchronous helper to build an ApiToken (must be committed by caller)."""
    plaintext = secrets.token_hex(32)
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    api_token = ApiToken(
        user_id=user.id, name=name, token_hash=token_hash, scope=scope,
    )
    db_session.add(api_token)
    return plaintext, api_token


@pytest.fixture
async def wildcard_token(db_session: AsyncSession, owner_user: User) -> str:
    """API token with wildcard scope (full access)."""
    plaintext, _ = _create_api_token_row(db_session, owner_user, scope="*")
    await db_session.commit()
    return plaintext


@pytest.fixture
async def sparql_read_token(db_session: AsyncSession, owner_user: User) -> str:
    """API token with only sparql:read scope."""
    plaintext, _ = _create_api_token_row(
        db_session, owner_user, scope="sparql:read", name="sparql-readonly",
    )
    await db_session.commit()
    return plaintext


@pytest.fixture
async def commands_only_token(db_session: AsyncSession, owner_user: User) -> str:
    """API token with only commands:execute scope."""
    plaintext, _ = _create_api_token_row(
        db_session, owner_user, scope="commands:execute", name="commands-only",
    )
    await db_session.commit()
    return plaintext


@pytest.fixture
async def multi_scope_token(db_session: AsyncSession, owner_user: User) -> str:
    """API token with multiple scopes."""
    plaintext, _ = _create_api_token_row(
        db_session, owner_user, scope="sparql:read,commands:execute", name="multi",
    )
    await db_session.commit()
    return plaintext


def _make_request(db_session_factory):
    """Build a mock Request with auth_service wired."""
    auth_service = AuthService(db_session_factory)
    app = FastAPI()
    app.state.auth_service = auth_service
    request = MagicMock()
    request.app = app
    request.state = MagicMock()
    request.url = MagicMock()
    request.url.path = "/api/test"
    return request


# ---------------------------------------------------------------------------
# ApiToken.scopes property tests
# ---------------------------------------------------------------------------


class TestApiTokenScopesProperty:
    """Test the scopes property on the ApiToken model."""

    def test_wildcard_scope(self):
        t = ApiToken(user_id=uuid.uuid4(), name="t", token_hash="x", scope="*")
        assert t.scopes == {"*"}

    def test_single_scope(self):
        t = ApiToken(user_id=uuid.uuid4(), name="t", token_hash="x", scope="sparql:read")
        assert t.scopes == {"sparql:read"}

    def test_multi_scope(self):
        t = ApiToken(
            user_id=uuid.uuid4(), name="t", token_hash="x",
            scope="sparql:read,commands:execute",
        )
        assert t.scopes == {"sparql:read", "commands:execute"}

    def test_scope_with_whitespace(self):
        t = ApiToken(
            user_id=uuid.uuid4(), name="t", token_hash="x",
            scope=" sparql:read , commands:execute ",
        )
        assert t.scopes == {"sparql:read", "commands:execute"}

    def test_none_scope_defaults_to_wildcard(self):
        t = ApiToken(user_id=uuid.uuid4(), name="t", token_hash="x", scope=None)
        assert t.scopes == {"*"}

    def test_empty_scope_defaults_to_wildcard(self):
        t = ApiToken(user_id=uuid.uuid4(), name="t", token_hash="x", scope="")
        assert t.scopes == {"*"}


class TestValidScopesConstant:
    """Test the VALID_SCOPES constant."""

    def test_contains_expected_scopes(self):
        expected = {
            "*", "sparql:read", "sparql:write", "objects:read", "objects:write",
            "models:admin", "users:admin", "commands:execute", "copilot:use",
        }
        assert expected == VALID_SCOPES

    def test_is_frozen(self):
        assert isinstance(VALID_SCOPES, frozenset)


# ---------------------------------------------------------------------------
# scope_required() dependency unit tests
# ---------------------------------------------------------------------------


class TestScopeRequiredDependency:
    """Direct unit tests for the scope_required() dependency factory."""

    async def test_session_auth_bypasses_scope_check(
        self, db_session, db_session_factory, owner_user, valid_session,
    ):
        """Session-authenticated requests bypass scope enforcement entirely."""
        request = _make_request(db_session_factory)

        # Resolve user via session cookie
        user = await get_current_user_or_api(
            request=request,
            sempkm_session=valid_session.token,
            authorization=None,
            db=db_session,
        )
        assert user.id == owner_user.id
        # auth_method should be "session"
        assert request.state.auth_method == "session"

    async def test_wildcard_token_passes_any_scope(
        self, db_session, db_session_factory, owner_user, wildcard_token,
    ):
        """A token with '*' scope passes any scope_required check."""
        request = _make_request(db_session_factory)

        user = await get_current_user_or_api(
            request=request,
            sempkm_session=None,
            authorization=f"Bearer {wildcard_token}",
            db=db_session,
        )
        assert user.id == owner_user.id
        assert request.state.auth_method == "bearer"
        assert "*" in request.state.api_token_scopes

    async def test_scoped_token_passes_matching_scope(
        self, db_session, db_session_factory, owner_user, sparql_read_token,
    ):
        """A token with sparql:read scope passes scope_required('sparql:read')."""
        request = _make_request(db_session_factory)

        user = await get_current_user_or_api(
            request=request,
            sempkm_session=None,
            authorization=f"Bearer {sparql_read_token}",
            db=db_session,
        )
        assert user.id == owner_user.id
        assert "sparql:read" in request.state.api_token_scopes

    async def test_scoped_token_denied_on_missing_scope(
        self, db_session, db_session_factory, owner_user, sparql_read_token,
    ):
        """A token with sparql:read scope gets 403 on commands:execute."""
        request = _make_request(db_session_factory)

        user = await get_current_user_or_api(
            request=request,
            sempkm_session=None,
            authorization=f"Bearer {sparql_read_token}",
            db=db_session,
        )
        # Now invoke the scope_required dependency manually
        checker = scope_required("commands:execute")
        with pytest.raises(HTTPException) as exc_info:
            await checker(request=request, user=user)
        assert exc_info.value.status_code == 403
        assert "Token lacks required scope" in exc_info.value.detail

    async def test_multi_scope_token_passes_either_scope(
        self, db_session, db_session_factory, owner_user, multi_scope_token,
    ):
        """A token with sparql:read,commands:execute passes either scope check."""
        request = _make_request(db_session_factory)

        user = await get_current_user_or_api(
            request=request,
            sempkm_session=None,
            authorization=f"Bearer {multi_scope_token}",
            db=db_session,
        )

        # Should pass sparql:read
        checker_sparql = scope_required("sparql:read")
        result = await checker_sparql(request=request, user=user)
        assert result.id == owner_user.id

        # Should pass commands:execute
        checker_cmd = scope_required("commands:execute")
        result = await checker_cmd(request=request, user=user)
        assert result.id == owner_user.id

    async def test_multi_scope_token_denied_on_unlisted_scope(
        self, db_session, db_session_factory, owner_user, multi_scope_token,
    ):
        """Multi-scope token gets 403 for a scope it doesn't have."""
        request = _make_request(db_session_factory)

        user = await get_current_user_or_api(
            request=request,
            sempkm_session=None,
            authorization=f"Bearer {multi_scope_token}",
            db=db_session,
        )

        checker = scope_required("copilot:use")
        with pytest.raises(HTTPException) as exc_info:
            await checker(request=request, user=user)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Token creation with scopes (JSON API)
# ---------------------------------------------------------------------------


class TestTokenCreationWithScopes:
    """Test that the /api/auth/tokens endpoint accepts and validates scopes."""

    def _build_auth_app(self, db_session_factory, db_session):
        from app.auth.router import router as auth_router

        test_app = FastAPI()
        auth_service = AuthService(db_session_factory)
        test_app.state.auth_service = auth_service
        test_app.include_router(auth_router)

        async def override_db():
            yield db_session

        test_app.dependency_overrides[get_db_session] = override_db
        return test_app

    async def test_create_token_with_explicit_scope(
        self, db_session, db_session_factory, owner_user, valid_session,
    ):
        """Create a token with specific scopes via JSON API."""
        app = self._build_auth_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/tokens",
                json={"name": "scoped-key", "scope": "sparql:read,objects:read"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "scoped-key"
        # Scopes are sorted on creation
        assert data["scope"] == "objects:read,sparql:read"

    async def test_create_token_default_wildcard(
        self, db_session, db_session_factory, owner_user, valid_session,
    ):
        """Token created without scope defaults to wildcard."""
        app = self._build_auth_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/tokens",
                json={"name": "full-access"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 201
        assert resp.json()["scope"] == "*"

    async def test_create_token_invalid_scope_rejected(
        self, db_session, db_session_factory, owner_user, valid_session,
    ):
        """Invalid scope values are rejected with 400."""
        app = self._build_auth_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/tokens",
                json={"name": "bad-scope", "scope": "sparql:read,nonexistent:scope"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 400
        assert "Invalid scope" in resp.json()["detail"]

    async def test_list_tokens_shows_scope(
        self, db_session, db_session_factory, owner_user, valid_session,
    ):
        """Token listing includes scope field."""
        app = self._build_auth_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create a scoped token first
            await client.post(
                "/api/auth/tokens",
                json={"name": "scoped", "scope": "sparql:read"},
                cookies={"sempkm_session": valid_session.token},
            )
            resp = await client.get(
                "/api/auth/tokens",
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200
        tokens = resp.json()
        assert len(tokens) >= 1
        scoped = next(t for t in tokens if t["name"] == "scoped")
        assert scoped["scope"] == "sparql:read"


# ---------------------------------------------------------------------------
# Integration: SPARQL endpoint scope enforcement
# ---------------------------------------------------------------------------


def _build_sparql_app(db_session_factory, db_session):
    """Build a FastAPI app with the SPARQL router for scope testing."""
    from app.sparql.router import router as sparql_router

    test_app = FastAPI()
    auth_service = AuthService(db_session_factory)
    test_app.state.auth_service = auth_service

    # Mock triplestore client that returns minimal valid SPARQL results
    mock_triplestore = AsyncMock()
    mock_triplestore.query = AsyncMock(return_value={
        "results": {"bindings": []},
        "head": {"vars": ["s"]},
    })

    test_app.include_router(sparql_router)

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db

    from app.dependencies import get_triplestore_client, get_label_service, get_prefix_registry, get_query_service, get_search_service
    test_app.dependency_overrides[get_triplestore_client] = lambda: mock_triplestore
    test_app.dependency_overrides[get_label_service] = lambda: AsyncMock()
    test_app.dependency_overrides[get_prefix_registry] = lambda: MagicMock()
    test_app.dependency_overrides[get_query_service] = lambda: AsyncMock()
    test_app.dependency_overrides[get_search_service] = lambda: AsyncMock()

    return test_app


class TestSparqlEndpointScopeEnforcement:
    """Integration tests: SPARQL endpoint with scoped tokens."""

    async def test_sparql_read_token_can_query(
        self, db_session, db_session_factory, owner_user, sparql_read_token,
    ):
        """Token with sparql:read can execute SPARQL GET."""
        app = _build_sparql_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/sparql",
                params={"query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"},
                headers={"Authorization": f"Bearer {sparql_read_token}"},
            )
        assert resp.status_code == 200

    async def test_commands_token_denied_on_sparql(
        self, db_session, db_session_factory, owner_user, commands_only_token,
    ):
        """Token with commands:execute but not sparql:read gets 403 on SPARQL."""
        app = _build_sparql_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/sparql",
                params={"query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"},
                headers={"Authorization": f"Bearer {commands_only_token}"},
            )
        assert resp.status_code == 403
        assert "Token lacks required scope" in resp.json()["detail"]

    async def test_wildcard_token_can_query_sparql(
        self, db_session, db_session_factory, owner_user, wildcard_token,
    ):
        """Wildcard token can access SPARQL endpoint."""
        app = _build_sparql_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/sparql",
                params={"query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"},
                headers={"Authorization": f"Bearer {wildcard_token}"},
            )
        assert resp.status_code == 200

    async def test_session_cookie_bypasses_sparql_scope(
        self, db_session, db_session_factory, owner_user, valid_session,
    ):
        """Session cookie auth bypasses scope check on SPARQL."""
        app = _build_sparql_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/sparql",
                params={"query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"},
                cookies={"sempkm_session": valid_session.token},
            )
        assert resp.status_code == 200

    async def test_no_auth_returns_401_on_sparql(
        self, db_session, db_session_factory,
    ):
        """No credentials on SPARQL endpoint returns 401."""
        app = _build_sparql_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/sparql",
                params={"query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Integration: Commands endpoint scope enforcement
# ---------------------------------------------------------------------------


def _build_commands_app(db_session_factory, db_session):
    """Build a FastAPI app with the commands router for scope testing."""
    from app.commands.router import router as commands_router

    test_app = FastAPI()
    auth_service = AuthService(db_session_factory)
    test_app.state.auth_service = auth_service
    test_app.state.triplestore_client = AsyncMock()
    test_app.state.validation_queue = AsyncMock()
    test_app.state.validation_queue.enqueue = AsyncMock()
    test_app.state.webhook_service = AsyncMock()
    test_app.state.webhook_service.dispatch = AsyncMock()

    test_app.include_router(commands_router)

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_db

    from app.dependencies import get_triplestore_client, get_validation_queue, get_webhook_service
    test_app.dependency_overrides[get_triplestore_client] = lambda: test_app.state.triplestore_client
    test_app.dependency_overrides[get_validation_queue] = lambda: test_app.state.validation_queue
    test_app.dependency_overrides[get_webhook_service] = lambda: test_app.state.webhook_service

    return test_app


class TestCommandsEndpointScopeEnforcement:
    """Integration tests: Commands endpoint with scoped tokens."""

    async def test_sparql_read_token_denied_on_commands(
        self, db_session, db_session_factory, owner_user, sparql_read_token,
    ):
        """Token with sparql:read but not commands:execute gets 403 on /api/commands."""
        app = _build_commands_app(db_session_factory, db_session)
        transport = ASGITransport(app=app)
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
                headers={"Authorization": f"Bearer {sparql_read_token}"},
            )
        assert resp.status_code == 403
        assert "Token lacks required scope" in resp.json()["detail"]

    async def test_commands_token_passes_commands_endpoint(
        self, db_session, db_session_factory, owner_user, commands_only_token,
    ):
        """Token with commands:execute scope can post to /api/commands."""
        from app.events.store import Operation

        app = _build_commands_app(db_session_factory, db_session)

        fake_op = Operation(
            operation_type="object.create",
            affected_iris=["urn:sempkm:obj:scope-test"],
            description="Created Note",
            data_triples=[],
            materialize_inserts=[],
            materialize_deletes=[],
        )

        with (
            patch("app.commands.router.dispatch", new_callable=AsyncMock) as mock_dispatch,
            patch("app.commands.router.EventStore") as MockEventStore,
        ):
            mock_dispatch.return_value = fake_op
            mock_store = AsyncMock()
            mock_store.commit = AsyncMock(return_value=MagicMock(
                event_iri="urn:sempkm:event:scope-test",
                timestamp="2025-01-01T00:00:00Z",
            ))
            MockEventStore.return_value = mock_store

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/commands",
                    json={
                        "command": "object.create",
                        "params": {
                            "type": "urn:sempkm:model:basic-pkm:Note",
                            "properties": {"dcterms:title": "Scoped creation"},
                        },
                    },
                    headers={"Authorization": f"Bearer {commands_only_token}"},
                )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Scope enforcement logging
# ---------------------------------------------------------------------------


class TestScopeEnforcementLogging:
    """Verify that scope denials are logged with token ID and endpoint."""

    async def test_scope_denial_logs_warning(
        self, db_session, db_session_factory, owner_user, sparql_read_token, caplog,
    ):
        """Scope denial should emit a WARNING log with token ID and endpoint."""
        import logging

        request = _make_request(db_session_factory)

        user = await get_current_user_or_api(
            request=request,
            sempkm_session=None,
            authorization=f"Bearer {sparql_read_token}",
            db=db_session,
        )

        checker = scope_required("commands:execute")
        with caplog.at_level(logging.WARNING, logger="app.auth.dependencies"):
            with pytest.raises(HTTPException):
                await checker(request=request, user=user)

        # Verify log content
        assert any("Scope enforcement denied" in r.message for r in caplog.records)
        assert any("commands:execute" in r.message for r in caplog.records)
        assert any("sparql:read" in r.message for r in caplog.records)
