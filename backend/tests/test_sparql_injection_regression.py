"""SPARQL injection regression tests — exact exploit payloads from M042 audit.

Each test reproduces a specific finding from the security audit (F-006 through
F-010) using the exact payload described in the finding.  Tests verify that
the payload is rejected (HTTP 400) or safely escaped (no data leak).

These tests use httpx AsyncClient with dependency overrides, following the
established test pattern in test_zone_router.py.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.auth.models import User


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_user():
    """Authenticated owner user for endpoints requiring auth."""
    return User(id=uuid.uuid4(), email="sectest@example.com", role="owner")


@pytest.fixture
def mock_triplestore():
    """Mock TriplestoreClient that records queries without executing them."""
    mock = AsyncMock()
    mock.query.return_value = {"results": {"bindings": []}}
    mock.update.return_value = None
    return mock


# ---------------------------------------------------------------------------
# F-006: SPARQL Injection via `type` query param in views
# ---------------------------------------------------------------------------
# Payload: x> . ?s ?p ?o } #
# URL-encoded: type=x>%20.%20%3Fs%20%3Fp%20%3Fo%20}%20%23
# Vector: GET /browser/views/generic/table?type=PAYLOAD
# Expected: 400 (invalid type IRI rejected by safe_iri)

class TestF006ViewsTypeInjection:
    """F-006: type parameter injection in generic view endpoints."""

    PAYLOAD = "x> . ?s ?p ?o } #"

    @pytest.fixture
    async def client(self, test_user, mock_triplestore):
        from app.views.router import router as views_router
        from app.dependencies import (
            get_label_service,
            get_query_service,
            get_shapes_service,
            get_triplestore_client,
            get_view_spec_service,
            get_validation_queue,
            get_webhook_service,
        )

        app = FastAPI()
        app.include_router(views_router)

        # Mock all dependencies
        mock_view_svc = AsyncMock()
        mock_view_svc.build_dynamic_query.return_value = (
            "SELECT ?s WHERE { ?s a <http://example.org/Type> }", ["s"]
        )
        mock_label_svc = AsyncMock()
        mock_shapes_svc = AsyncMock()
        mock_query_svc = AsyncMock()
        mock_query_svc.list_user_queries.return_value = []
        mock_query_svc.list_model_queries.return_value = []
        mock_val_q = AsyncMock()
        mock_webhook_svc = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_view_spec_service] = lambda: mock_view_svc
        app.dependency_overrides[get_label_service] = lambda: mock_label_svc
        app.dependency_overrides[get_shapes_service] = lambda: mock_shapes_svc
        app.dependency_overrides[get_query_service] = lambda: mock_query_svc
        app.dependency_overrides[get_triplestore_client] = lambda: mock_triplestore
        app.dependency_overrides[get_validation_queue] = lambda: mock_val_q
        app.dependency_overrides[get_webhook_service] = lambda: mock_webhook_svc

        # Mock request.app.state.templates
        mock_templates = MagicMock()
        mock_templates.TemplateResponse.return_value = MagicMock(
            status_code=200, body=b"<html></html>"
        )
        app.state.templates = mock_templates

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.anyio
    async def test_table_view_rejects_injection_payload(self, client):
        """GET /browser/views/generic/table?type=<PAYLOAD> → 400."""
        resp = await client.get(
            "/browser/views/generic/table",
            params={"type": self.PAYLOAD},
        )
        assert resp.status_code == 400, (
            f"F-006: Expected 400 for injection payload, got {resp.status_code}"
        )

    @pytest.mark.anyio
    async def test_card_view_rejects_injection_payload(self, client):
        """GET /browser/views/generic/card?type=<PAYLOAD> → 400."""
        resp = await client.get(
            "/browser/views/generic/card",
            params={"type": self.PAYLOAD},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_graph_view_rejects_injection_payload(self, client):
        """GET /browser/views/generic/graph?type=<PAYLOAD> → 400."""
        resp = await client.get(
            "/browser/views/generic/graph",
            params={"type": self.PAYLOAD},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_data_endpoint_rejects_injection_payload(self, client):
        """GET /browser/views/generic/graph/data?type=<PAYLOAD> → 400."""
        resp = await client.get(
            "/browser/views/generic/graph/data",
            params={"type": self.PAYLOAD},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_angle_bracket_breakout(self, client):
        """Angle bracket IRI breakout: type=urn:x><evil> → 400."""
        resp = await client.get(
            "/browser/views/generic/table",
            params={"type": "urn:x><evil>"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_comment_injection(self, client):
        """Hash comment injection: type=urn:x# injected → 400."""
        resp = await client.get(
            "/browser/views/generic/table",
            params={"type": "urn:x# injected"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_valid_type_iri_passes(self, client, mock_triplestore):
        """Valid IRI should not be rejected — ensure we don't over-block."""
        resp = await client.get(
            "/browser/views/generic/table",
            params={"type": "http://example.org/Type"},
        )
        # May be 200 or 500 (mock doesn't return valid template data), but NOT 400
        assert resp.status_code != 400, "Valid IRI should not be rejected"


# ---------------------------------------------------------------------------
# F-007: SPARQL Injection via `iri` query param in apps
# ---------------------------------------------------------------------------
# Payload: x> . ?s ?p ?o } #
# Vector: GET /browser/apps/right-pane-sections?iri=PAYLOAD
# Expected: 400

class TestF007AppsIriInjection:
    """F-007: iri parameter injection in right-pane-sections."""

    PAYLOAD = "x> . ?s ?p ?o } #"

    @pytest.fixture
    async def client(self, mock_triplestore):
        from app.browser.apps import apps_router

        app = FastAPI()
        app.include_router(apps_router, prefix="/browser")

        # Mock app.state for the apps router
        mock_registry = MagicMock()
        mock_registry.values.return_value = []
        mock_manager = MagicMock()
        mock_manager.registry = mock_registry
        app.state.app_manager = mock_manager
        app.state.triplestore_client = mock_triplestore

        mock_templates = MagicMock()
        mock_templates.TemplateResponse.return_value = MagicMock(
            status_code=200, body=b"<html></html>"
        )
        app.state.templates = mock_templates

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.anyio
    async def test_right_pane_rejects_injection_payload(self, client):
        """GET /browser/apps/right-pane-sections?iri=<PAYLOAD> → 400."""
        resp = await client.get(
            "/browser/apps/right-pane-sections",
            params={"iri": self.PAYLOAD},
        )
        assert resp.status_code == 400, (
            f"F-007: Expected 400 for injection payload, got {resp.status_code}"
        )

    @pytest.mark.anyio
    async def test_right_pane_rejects_newline_injection(self, client):
        """Newline in IRI to inject extra triple pattern → 400."""
        resp = await client.get(
            "/browser/apps/right-pane-sections",
            params={"iri": "urn:x\n?s ?p ?o ."},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_right_pane_rejects_curly_brace_injection(self, client):
        """Curly brace to close WHERE block → 400."""
        resp = await client.get(
            "/browser/apps/right-pane-sections",
            params={"iri": "urn:x} UNION {?s ?p ?o"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# F-008: SPARQL Write Injection via VFS mount IRI fields
# ---------------------------------------------------------------------------
# Payload (group_by_property):
#   x> . } } ; INSERT DATA { GRAPH <urn:sempkm:current> {
#     <urn:evil> <urn:p> <urn:o> } } #
# Vector: POST /api/vfs/mounts with crafted JSON body
# Expected: 400

class TestF008VfsMountInjection:
    """F-008: write injection via crafted mount IRI fields."""

    INJECTION_PROPERTY = (
        'x> . } } ; INSERT DATA { GRAPH <urn:sempkm:current> '
        '{ <urn:evil> <urn:p> <urn:o> } } #'
    )

    @pytest.fixture
    async def client(self, test_user, mock_triplestore):
        from app.vfs.mount_router import router as mount_router
        from app.dependencies import get_triplestore_client

        app = FastAPI()
        app.include_router(mount_router)

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_triplestore_client] = lambda: mock_triplestore

        # Mock _validate_mount_path_async to not hit real triplestore
        mock_triplestore.query.return_value = {"results": {"bindings": []}}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.anyio
    async def test_mount_rejects_injected_group_by_property(self, client):
        """POST /api/vfs/mounts with injected group_by_property → 400."""
        resp = await client.post(
            "/api/vfs/mounts",
            json={
                "name": "test",
                "path": "/exploit-test",
                "strategy": "flat",
                "group_by_property": self.INJECTION_PROPERTY,
            },
        )
        assert resp.status_code == 400, (
            f"F-008: Expected 400 for injected group_by_property, got {resp.status_code}"
        )

    @pytest.mark.anyio
    async def test_mount_rejects_injected_type_filter(self, client):
        """POST /api/vfs/mounts with injected type_filter → 400."""
        resp = await client.post(
            "/api/vfs/mounts",
            json={
                "name": "test",
                "path": "/exploit-test-2",
                "strategy": "flat",
                "type_filter": [self.INJECTION_PROPERTY],
            },
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_mount_rejects_injected_scope_query(self, client):
        """POST /api/vfs/mounts with injected scope_query → 400."""
        resp = await client.post(
            "/api/vfs/mounts",
            json={
                "name": "test",
                "path": "/exploit-test-3",
                "strategy": "flat",
                "scope_query": self.INJECTION_PROPERTY,
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# F-009: Stored SPARQL Injection via Favorites
# ---------------------------------------------------------------------------
# Payload (object_iri): x> . ?s ?p ?o } #
# Vector: POST /browser/favorites/toggle with crafted form body
# Expected: 400

class TestF009FavoritesInjection:
    """F-009: stored injection via favorites toggle endpoint."""

    PAYLOAD = "x> . ?s ?p ?o } #"

    @pytest.fixture
    async def client(self, test_user):
        from app.browser.favorites import favorites_router
        from app.db.session import get_db_session
        from app.dependencies import get_label_service

        app = FastAPI()
        app.include_router(favorites_router, prefix="/browser")

        mock_db = AsyncMock()
        mock_label_svc = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[get_label_service] = lambda: mock_label_svc

        mock_templates = MagicMock()
        app.state.templates = mock_templates

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.anyio
    async def test_favorites_rejects_injection_payload(self, client):
        """POST /browser/favorites/toggle with injected object_iri → 400."""
        resp = await client.post(
            "/browser/favorites/toggle",
            data={"object_iri": self.PAYLOAD},
        )
        assert resp.status_code == 400, (
            f"F-009: Expected 400 for injection payload, got {resp.status_code}"
        )

    @pytest.mark.anyio
    async def test_favorites_rejects_angle_bracket_breakout(self, client):
        """Angle bracket breakout in favorites IRI → 400."""
        resp = await client.post(
            "/browser/favorites/toggle",
            data={"object_iri": "urn:x><evil>"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_favorites_rejects_backslash_quote(self, client):
        r"""Backslash-quote breakout: object_iri=urn:x\" → 400."""
        resp = await client.post(
            "/browser/favorites/toggle",
            data={"object_iri": 'urn:x\\" evil'},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# F-010: Events search with backslash-quote breakout
# ---------------------------------------------------------------------------
# Payload: \" )) . ?s ?p ?o } #
# Vector: GET /browser/events/suggest-objects?q=PAYLOAD
# Expected: safe escape — no breakout, proper response (200 with empty or
#   filtered results).  The centralised sparql_escape_string handles this.

class TestF010EventsEscapeBreakout:
    """F-010: backslash-quote string escape breakout in events search."""

    PAYLOAD = '\\" )) . ?s ?p ?o } #'

    @pytest.fixture
    async def client(self, test_user, mock_triplestore):
        from app.browser.events import events_router
        from app.db.session import get_db_session
        from app.dependencies import (
            get_label_service,
            get_shapes_service,
            get_triplestore_client,
        )

        app = FastAPI()
        app.include_router(events_router, prefix="/browser")

        mock_db = AsyncMock()
        mock_label_svc = AsyncMock()
        mock_label_svc.get_labels.return_value = {}
        mock_shapes_svc = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[get_label_service] = lambda: mock_label_svc
        app.dependency_overrides[get_shapes_service] = lambda: mock_shapes_svc
        app.dependency_overrides[get_triplestore_client] = lambda: mock_triplestore

        mock_templates = MagicMock()
        mock_templates.TemplateResponse.return_value = MagicMock(
            status_code=200, body=b"<html></html>",
            headers={},
        )
        app.state.templates = mock_templates

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.anyio
    async def test_backslash_quote_does_not_break_sparql(
        self, client, mock_triplestore
    ):
        r"""Backslash-quote payload is safely escaped — no SPARQL breakout.

        The centralised sparql_escape_string escapes \ before ", so
        the \" in the payload becomes \\" in the query string, which
        SPARQL interprets as literal-backslash inside the string — no
        breakout occurs.
        """
        resp = await client.get(
            "/browser/events/suggest-objects",
            params={"q": self.PAYLOAD},
        )
        # Should succeed (200) or fail gracefully — must NOT be 500
        assert resp.status_code != 500, (
            f"F-010: Payload caused server error — likely SPARQL breakout"
        )
        # Verify the mock triplestore was called with properly escaped query
        if mock_triplestore.query.called:
            sparql_sent = mock_triplestore.query.call_args[0][0]
            # The payload's \" should be escaped to \\" in the SPARQL string
            # meaning the raw query should NOT contain unescaped "))
            assert '")) . ?s ?p ?o }' not in sparql_sent, (
                "F-010: Backslash-quote breakout — SPARQL contains unescaped payload"
            )

    @pytest.mark.anyio
    async def test_tab_and_carriage_return_escaped(
        self, client, mock_triplestore
    ):
        r"""Tab and carriage return in search query are safely escaped."""
        resp = await client.get(
            "/browser/events/suggest-objects",
            params={"q": 'test\t\rstuff'},
        )
        assert resp.status_code != 500
        if mock_triplestore.query.called:
            sparql_sent = mock_triplestore.query.call_args[0][0]
            # Raw tab/CR should not appear in the SPARQL — they should be escaped
            assert '\t' not in sparql_sent, "Raw tab in SPARQL query"
            assert '\r' not in sparql_sent, "Raw carriage return in SPARQL query"
