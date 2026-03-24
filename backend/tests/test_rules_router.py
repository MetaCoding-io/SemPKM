"""Tests for the context rules API router — CRUD, test endpoint, integration hook, and auth.

Tests use httpx AsyncClient with dependency overrides to mock auth,
RulesEngine, ContextService, and ContextBroadcast. The integration
test verifies that context updates trigger rule evaluation and emit
persona_switched SSE events.
"""

import asyncio
import dataclasses
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.context.broadcast import ContextBroadcast
from app.context.rules_engine import RulesEngine
from app.context.rules_models import ContextRule
from app.context.rules_router import router as rules_router
from app.context.router import router as context_router
from app.context.service import ContextData, ContextService
from app.dependencies import (
    get_context_broadcast,
    get_context_service,
    get_rules_engine,
)


# ── Helpers ──────────────────────────────────────────────────────


def _make_rule(
    user_id: uuid.UUID,
    name: str = "Test Rule",
    conditions: dict | None = None,
    persona_id: str | None = None,
    priority: int = 0,
    enabled: bool = True,
) -> ContextRule:
    """Build a ContextRule instance for test assertions."""
    rule = ContextRule(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        conditions=conditions or {"location_zone": "office"},
        persona_id=persona_id or str(uuid.uuid4()),
        priority=priority,
        enabled=enabled,
    )
    rule.created_at = datetime.now(timezone.utc)
    rule.updated_at = datetime.now(timezone.utc)
    return rule


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="rules-test@example.com",
        role="owner",
    )


@pytest.fixture
def mock_engine():
    return AsyncMock(spec=RulesEngine)


@pytest.fixture
def mock_service():
    return AsyncMock(spec=ContextService)


@pytest.fixture
def mock_broadcast():
    broadcast = AsyncMock(spec=ContextBroadcast)
    broadcast.client_count = 0
    return broadcast


@pytest.fixture
async def client(test_user, mock_engine, mock_service, mock_broadcast):
    """AsyncClient wired to the rules router with dependency overrides."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(rules_router)

    app.dependency_overrides[get_current_user_or_api] = lambda: test_user
    app.dependency_overrides[get_rules_engine] = lambda: mock_engine
    app.dependency_overrides[get_context_service] = lambda: mock_service
    app.dependency_overrides[get_context_broadcast] = lambda: mock_broadcast

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── POST /api/context/rules — create ────────────────────────────


class TestCreateRule:
    @pytest.mark.asyncio
    async def test_create_returns_201(self, client, mock_engine, test_user):
        persona_id = str(uuid.uuid4())
        rule = _make_rule(test_user.id, name="Office Work", persona_id=persona_id)
        mock_engine.create_rule.return_value = rule

        resp = await client.post(
            "/api/context/rules/",
            json={
                "name": "Office Work",
                "conditions": {"location_zone": "office"},
                "persona_id": persona_id,
                "priority": 10,
                "enabled": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Office Work"
        assert data["persona_id"] == persona_id
        mock_engine.create_rule.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_uses_defaults(self, client, mock_engine, test_user):
        """Priority defaults to 0, enabled defaults to True."""
        rule = _make_rule(test_user.id)
        mock_engine.create_rule.return_value = rule

        resp = await client.post(
            "/api/context/rules/",
            json={
                "name": "Default Rule",
                "conditions": {},
                "persona_id": "some-id",
            },
        )
        assert resp.status_code == 201
        call_kwargs = mock_engine.create_rule.call_args
        assert call_kwargs.kwargs["priority"] == 0
        assert call_kwargs.kwargs["enabled"] is True

    @pytest.mark.asyncio
    async def test_create_missing_name_returns_422(self, client):
        resp = await client.post(
            "/api/context/rules/",
            json={"conditions": {}, "persona_id": "abc"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_empty_name_returns_422(self, client):
        resp = await client.post(
            "/api/context/rules/",
            json={"name": "", "conditions": {}, "persona_id": "abc"},
        )
        assert resp.status_code == 422


# ── GET /api/context/rules — list ────────────────────────────────


class TestListRules:
    @pytest.mark.asyncio
    async def test_list_empty(self, client, mock_engine):
        mock_engine.list_rules.return_value = []
        resp = await client.get("/api/context/rules/")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_rules(self, client, mock_engine, test_user):
        rules = [
            _make_rule(test_user.id, name="Rule A", priority=10),
            _make_rule(test_user.id, name="Rule B", priority=5),
        ]
        mock_engine.list_rules.return_value = rules

        resp = await client.get("/api/context/rules/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Rule A"
        assert data[1]["name"] == "Rule B"

    @pytest.mark.asyncio
    async def test_list_scoped_to_user(self, client, mock_engine, test_user):
        """Verify list_rules is called with the authenticated user's ID."""
        mock_engine.list_rules.return_value = []
        await client.get("/api/context/rules/")
        mock_engine.list_rules.assert_awaited_once_with(test_user.id)


# ── PUT /api/context/rules/{id} — update ────────────────────────


class TestUpdateRule:
    @pytest.mark.asyncio
    async def test_update_returns_updated_rule(
        self, client, mock_engine, test_user
    ):
        rule = _make_rule(test_user.id, name="Updated Name")
        mock_engine.update_rule.return_value = rule

        rule_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/context/rules/{rule_id}",
            json={"name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_not_found_returns_404(self, client, mock_engine):
        mock_engine.update_rule.return_value = None

        rule_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/context/rules/{rule_id}",
            json={"name": "New Name"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_empty_body_returns_422(self, client):
        rule_id = str(uuid.uuid4())
        resp = await client.put(f"/api/context/rules/{rule_id}", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_partial_fields(self, client, mock_engine, test_user):
        """Only explicitly provided fields are passed to engine.update_rule."""
        rule = _make_rule(test_user.id, priority=20)
        mock_engine.update_rule.return_value = rule

        rule_id = str(uuid.uuid4())
        await client.put(
            f"/api/context/rules/{rule_id}",
            json={"priority": 20},
        )
        call_kwargs = mock_engine.update_rule.call_args.kwargs
        assert "priority" in call_kwargs
        assert "name" not in call_kwargs


# ── DELETE /api/context/rules/{id} ───────────────────────────────


class TestDeleteRule:
    @pytest.mark.asyncio
    async def test_delete_returns_204(self, client, mock_engine):
        mock_engine.delete_rule.return_value = True

        rule_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/context/rules/{rule_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_404(self, client, mock_engine):
        mock_engine.delete_rule.return_value = False

        rule_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/context/rules/{rule_id}")
        assert resp.status_code == 404


# ── POST /api/context/rules/test — evaluate ──────────────────────


class TestRulesTestEndpoint:
    @pytest.mark.asyncio
    async def test_match_returns_persona_id(
        self, client, mock_engine, mock_service, test_user
    ):
        persona_id = str(uuid.uuid4())
        ctx = ContextData(
            user_id=str(test_user.id),
            location_zone="office",
            is_stale=False,
            ttl_seconds=900,
            updated_at="2026-03-23T15:00:00",
            created_at="2026-03-23T14:00:00",
        )
        mock_service.get_current.return_value = ctx
        mock_engine.evaluate.return_value = persona_id

        # For rule_name lookup
        rule = _make_rule(
            test_user.id, name="Office Rule", persona_id=persona_id
        )
        mock_engine.list_rules.return_value = [rule]

        resp = await client.post("/api/context/rules/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["match"] is True
        assert data["persona_id"] == persona_id
        assert data["rule_name"] == "Office Rule"

    @pytest.mark.asyncio
    async def test_no_match_returns_false(
        self, client, mock_engine, mock_service, test_user
    ):
        ctx = ContextData(
            user_id=str(test_user.id),
            is_stale=False,
            ttl_seconds=900,
            updated_at="2026-03-23T15:00:00",
            created_at="2026-03-23T14:00:00",
        )
        mock_service.get_current.return_value = ctx
        mock_engine.evaluate.return_value = None

        resp = await client.post("/api/context/rules/test")
        assert resp.status_code == 200
        assert resp.json() == {"match": False}

    @pytest.mark.asyncio
    async def test_no_context_returns_no_match(
        self, client, mock_engine, mock_service
    ):
        mock_service.get_current.return_value = None

        resp = await client.post("/api/context/rules/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["match"] is False
        assert data.get("reason") == "no_context"


# ── Auth enforcement ─────────────────────────────────────────────


class TestAuthEnforcement:
    """Verify all endpoints require authentication."""

    @pytest.fixture
    async def unauthed_client(self, mock_engine, mock_service, mock_broadcast):
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(rules_router)

        # Override service deps but NOT auth
        app.dependency_overrides[get_rules_engine] = lambda: mock_engine
        app.dependency_overrides[get_context_service] = lambda: mock_service
        app.dependency_overrides[get_context_broadcast] = lambda: mock_broadcast

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, unauthed_client):
        resp = await unauthed_client.get("/api/context/rules/")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, unauthed_client):
        resp = await unauthed_client.post(
            "/api/context/rules/",
            json={"name": "R", "conditions": {}, "persona_id": "x"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, unauthed_client):
        rule_id = str(uuid.uuid4())
        resp = await unauthed_client.put(
            f"/api/context/rules/{rule_id}",
            json={"name": "New"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, unauthed_client):
        rule_id = str(uuid.uuid4())
        resp = await unauthed_client.delete(f"/api/context/rules/{rule_id}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_test_endpoint_requires_auth(self, unauthed_client):
        resp = await unauthed_client.post("/api/context/rules/test")
        assert resp.status_code == 401


# ── Integration hook: context update triggers rule evaluation ────


class TestIntegrationHook:
    """Test that POST /api/context/update evaluates rules and emits
    persona_switched SSE event when a rule matches."""

    @pytest.fixture
    async def integration_client(
        self, test_user, mock_service, mock_broadcast
    ):
        """Client wired to the context router with rules_engine and
        persona_service on app.state (like the real app)."""
        from fastapi import FastAPI
        from app.auth.rate_limit import limiter

        app = FastAPI()
        app.state.limiter = limiter

        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded

        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.state.shutdown_event = asyncio.Event()

        # Mock rules engine and persona service on app.state
        mock_rules_engine = AsyncMock(spec=RulesEngine)
        mock_persona_service = AsyncMock()

        app.state.rules_engine = mock_rules_engine
        app.state.persona_service = mock_persona_service

        app.include_router(context_router)

        app.dependency_overrides[get_current_user_or_api] = lambda: test_user
        app.dependency_overrides[get_context_service] = lambda: mock_service
        app.dependency_overrides[get_context_broadcast] = lambda: mock_broadcast

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, mock_rules_engine, mock_persona_service

    @pytest.mark.asyncio
    async def test_context_update_evaluates_rules(
        self, integration_client, mock_service, test_user
    ):
        client, mock_rules_engine, mock_persona_service = integration_client

        ctx = ContextData(
            user_id=str(test_user.id),
            location_zone="office",
            is_stale=False,
            ttl_seconds=900,
            updated_at="2026-03-23T15:00:00",
            created_at="2026-03-23T14:00:00",
        )
        mock_service.update.return_value = ctx
        mock_rules_engine.evaluate.return_value = None

        resp = await client.post(
            "/api/context/update",
            json={"location_zone": "office"},
        )
        assert resp.status_code == 200
        mock_rules_engine.evaluate.assert_awaited_once_with(
            test_user.id, {"location_zone": "office"}
        )

    @pytest.mark.asyncio
    async def test_context_update_switches_persona_on_match(
        self, integration_client, mock_service, mock_broadcast, test_user
    ):
        client, mock_rules_engine, mock_persona_service = integration_client

        persona_id = str(uuid.uuid4())
        ctx = ContextData(
            user_id=str(test_user.id),
            location_zone="office",
            is_stale=False,
            ttl_seconds=900,
            updated_at="2026-03-23T15:00:00",
            created_at="2026-03-23T14:00:00",
        )
        mock_service.update.return_value = ctx
        mock_rules_engine.evaluate.return_value = persona_id
        mock_persona_service.get_active.return_value = None  # no active persona

        # persona_service.activate returns a PersonaData-like object
        activated = MagicMock()
        activated.id = persona_id
        activated.name = "Work Mode"
        mock_persona_service.activate.return_value = activated

        resp = await client.post(
            "/api/context/update",
            json={"location_zone": "office"},
        )
        assert resp.status_code == 200

        # Verify persona was activated
        mock_persona_service.activate.assert_awaited_once()

        # Verify persona_switched SSE event was broadcast
        # broadcast.publish is called twice: once for context_update, once for persona_switched
        assert mock_broadcast.publish.await_count == 2
        persona_event = mock_broadcast.publish.call_args_list[1][0][0]
        assert persona_event.event == "persona_switched"
        assert persona_event.data["persona_id"] == persona_id
        assert persona_event.data["persona_name"] == "Work Mode"

    @pytest.mark.asyncio
    async def test_context_update_skips_redundant_switch(
        self, integration_client, mock_service, mock_broadcast, test_user
    ):
        """No persona_switched event when the matched persona is already active."""
        client, mock_rules_engine, mock_persona_service = integration_client

        persona_id = str(uuid.uuid4())
        ctx = ContextData(
            user_id=str(test_user.id),
            location_zone="office",
            is_stale=False,
            ttl_seconds=900,
            updated_at="2026-03-23T15:00:00",
            created_at="2026-03-23T14:00:00",
        )
        mock_service.update.return_value = ctx
        mock_rules_engine.evaluate.return_value = persona_id

        # Active persona already matches
        active = MagicMock()
        active.id = persona_id
        mock_persona_service.get_active.return_value = active

        resp = await client.post(
            "/api/context/update",
            json={"location_zone": "office"},
        )
        assert resp.status_code == 200

        # Persona was NOT activated (already active)
        mock_persona_service.activate.assert_not_awaited()

        # Only the context_update event was broadcast (no persona_switched)
        assert mock_broadcast.publish.await_count == 1

    @pytest.mark.asyncio
    async def test_context_update_no_match_no_switch(
        self, integration_client, mock_service, mock_broadcast, test_user
    ):
        """No persona_switched event when no rule matches."""
        client, mock_rules_engine, mock_persona_service = integration_client

        ctx = ContextData(
            user_id=str(test_user.id),
            location_zone="home",
            is_stale=False,
            ttl_seconds=900,
            updated_at="2026-03-23T15:00:00",
            created_at="2026-03-23T14:00:00",
        )
        mock_service.update.return_value = ctx
        mock_rules_engine.evaluate.return_value = None

        resp = await client.post(
            "/api/context/update",
            json={"location_zone": "home"},
        )
        assert resp.status_code == 200
        mock_persona_service.get_active.assert_not_awaited()
        mock_persona_service.activate.assert_not_awaited()
        # Only context_update event
        assert mock_broadcast.publish.await_count == 1

    @pytest.mark.asyncio
    async def test_rule_evaluation_error_does_not_break_update(
        self, integration_client, mock_service, mock_broadcast, test_user
    ):
        """Rule evaluation failure is logged but doesn't prevent context update."""
        client, mock_rules_engine, mock_persona_service = integration_client

        ctx = ContextData(
            user_id=str(test_user.id),
            location_zone="office",
            is_stale=False,
            ttl_seconds=900,
            updated_at="2026-03-23T15:00:00",
            created_at="2026-03-23T14:00:00",
        )
        mock_service.update.return_value = ctx
        mock_rules_engine.evaluate.side_effect = RuntimeError("DB connection lost")

        resp = await client.post(
            "/api/context/update",
            json={"location_zone": "office"},
        )
        # Context update itself still succeeds
        assert resp.status_code == 200
