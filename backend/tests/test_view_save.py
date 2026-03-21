"""Unit tests for save_promoted_view() and list_promoted_views() with new fields.

Tests the direct save path for generic views (no pre-existing query required),
the extended PromotedViewData fields (type_filter, scope_query_id), and
the updated list_promoted_views() OPTIONAL SPARQL bindings.
"""

import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.sparql.query_service import (
    QueryService,
    PromotedViewData,
    QUERIES_GRAPH,
    TYPE_PROMOTED_VIEW,
    PRED_OWNER,
    PRED_RENDERER_TYPE,
    PRED_TYPE_FILTER,
    PRED_SCOPE_QUERY,
    PRED_FROM_QUERY,
    PRED_QUERY_TEXT,
    RDFS_LABEL,
    VALID_RENDERERS,
)


# ── Helpers ────────────────────────────────────────────────────


def _mock_client() -> MagicMock:
    """Build a mock TriplestoreClient with async query/update."""
    client = MagicMock()
    client.query = AsyncMock(return_value={"results": {"bindings": []}})
    client.update = AsyncMock()
    return client


def _build_service(client=None) -> QueryService:
    if client is None:
        client = _mock_client()
    return QueryService(client)


# ── save_promoted_view ─────────────────────────────────────────


class TestSavePromotedView:
    """Tests for QueryService.save_promoted_view()."""

    @pytest.mark.asyncio
    async def test_creates_basic_view(self):
        """Saves a view with only required fields — no type_filter, no scope."""
        client = _mock_client()
        svc = _build_service(client)
        user_id = uuid.uuid4()

        result = await svc.save_promoted_view(
            user_id=user_id,
            display_label="My Table View",
            renderer_type="table",
        )

        assert isinstance(result, PromotedViewData)
        assert result.display_label == "My Table View"
        assert result.renderer_type == "table"
        assert result.type_filter == ""
        assert result.scope_query_id == ""
        assert result.query_id == ""
        # Verify INSERT was called
        client.update.assert_called_once()
        sparql = client.update.call_args[0][0]
        assert "INSERT DATA" in sparql
        assert TYPE_PROMOTED_VIEW in sparql
        assert PRED_RENDERER_TYPE in sparql
        assert RDFS_LABEL in sparql
        # Optional fields should NOT be present
        assert PRED_TYPE_FILTER not in sparql
        assert PRED_SCOPE_QUERY not in sparql
        assert PRED_FROM_QUERY not in sparql

    @pytest.mark.asyncio
    async def test_creates_view_with_type_filter(self):
        """Saves a view with type_filter — triple is included."""
        client = _mock_client()
        svc = _build_service(client)
        user_id = uuid.uuid4()

        result = await svc.save_promoted_view(
            user_id=user_id,
            display_label="Notes Only",
            renderer_type="card",
            type_filter="http://example.org/Note",
        )

        assert result.type_filter == "http://example.org/Note"
        assert result.renderer_type == "card"
        sparql = client.update.call_args[0][0]
        assert PRED_TYPE_FILTER in sparql
        assert "http://example.org/Note" in sparql
        # No scope query
        assert PRED_SCOPE_QUERY not in sparql

    @pytest.mark.asyncio
    async def test_creates_view_with_scope_query(self):
        """Saves a view with scope_query_id — triple and fromQuery link included."""
        client = _mock_client()
        svc = _build_service(client)
        user_id = uuid.uuid4()
        scope_id = str(uuid.uuid4())

        result = await svc.save_promoted_view(
            user_id=user_id,
            display_label="Scoped Graph",
            renderer_type="graph",
            scope_query_id=scope_id,
        )

        assert result.scope_query_id == scope_id
        assert result.query_id == scope_id
        sparql = client.update.call_args[0][0]
        assert PRED_SCOPE_QUERY in sparql
        assert PRED_FROM_QUERY in sparql
        assert scope_id in sparql

    @pytest.mark.asyncio
    async def test_creates_view_with_all_fields(self):
        """Saves a view with type_filter AND scope_query_id."""
        client = _mock_client()
        svc = _build_service(client)
        user_id = uuid.uuid4()
        scope_id = str(uuid.uuid4())

        result = await svc.save_promoted_view(
            user_id=user_id,
            display_label="Full Config",
            renderer_type="table",
            type_filter="http://example.org/Project",
            scope_query_id=scope_id,
        )

        assert result.type_filter == "http://example.org/Project"
        assert result.scope_query_id == scope_id
        sparql = client.update.call_args[0][0]
        assert PRED_TYPE_FILTER in sparql
        assert PRED_SCOPE_QUERY in sparql
        assert PRED_FROM_QUERY in sparql

    @pytest.mark.asyncio
    async def test_rejects_invalid_renderer(self):
        """Invalid renderer_type raises ValueError."""
        svc = _build_service()
        with pytest.raises(ValueError, match="renderer_type must be one of"):
            await svc.save_promoted_view(
                user_id=uuid.uuid4(),
                display_label="Bad",
                renderer_type="invalid",
            )

    @pytest.mark.asyncio
    async def test_returns_unique_view_id(self):
        """Each call generates a unique view ID."""
        client = _mock_client()
        svc = _build_service(client)
        user_id = uuid.uuid4()

        r1 = await svc.save_promoted_view(user_id, "View A", "table")
        r2 = await svc.save_promoted_view(user_id, "View B", "table")
        assert r1.id != r2.id

    @pytest.mark.asyncio
    async def test_sparql_targets_queries_graph(self):
        """INSERT targets the urn:sempkm:queries named graph."""
        client = _mock_client()
        svc = _build_service(client)

        await svc.save_promoted_view(uuid.uuid4(), "Test", "table")
        sparql = client.update.call_args[0][0]
        assert QUERIES_GRAPH in sparql


# ── list_promoted_views with new fields ────────────────────────


class TestListPromotedViewsExtended:
    """Tests for list_promoted_views() returning type_filter and scope_query_id."""

    @pytest.mark.asyncio
    async def test_returns_all_fields_when_present(self):
        """All OPTIONAL bindings are populated when data exists."""
        view_id = str(uuid.uuid4())
        query_id = str(uuid.uuid4())
        client = _mock_client()
        client.query = AsyncMock(return_value={
            "results": {"bindings": [{
                "view": {"value": f"urn:sempkm:query-view:{view_id}"},
                "query": {"value": f"urn:sempkm:query:{query_id}"},
                "label": {"value": "Full View"},
                "renderer": {"value": "table"},
                "text": {"value": "SELECT ?s WHERE { ?s a <urn:Type> }"},
                "typeFilter": {"value": "http://example.org/Note"},
                "scopeQuery": {"value": query_id},
            }]}
        })
        svc = _build_service(client)

        result = await svc.list_promoted_views(uuid.uuid4())
        assert len(result) == 1
        pv = result[0]
        assert pv.display_label == "Full View"
        assert pv.renderer_type == "table"
        assert pv.query_id == query_id
        assert pv.query_text == "SELECT ?s WHERE { ?s a <urn:Type> }"
        assert pv.type_filter == "http://example.org/Note"
        assert pv.scope_query_id == query_id

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(self):
        """Views saved without a query, type_filter, or scope_query return defaults."""
        view_id = str(uuid.uuid4())
        client = _mock_client()
        client.query = AsyncMock(return_value={
            "results": {"bindings": [{
                "view": {"value": f"urn:sempkm:query-view:{view_id}"},
                "label": {"value": "Simple View"},
                "renderer": {"value": "card"},
            }]}
        })
        svc = _build_service(client)

        result = await svc.list_promoted_views(uuid.uuid4())
        assert len(result) == 1
        pv = result[0]
        assert pv.display_label == "Simple View"
        assert pv.renderer_type == "card"
        assert pv.query_id == ""
        assert pv.query_text == ""
        assert pv.type_filter == ""
        assert pv.scope_query_id == ""

    @pytest.mark.asyncio
    async def test_sparql_uses_optional_clauses(self):
        """The generated SPARQL includes OPTIONAL for fromQuery, typeFilter, scopeQuery."""
        client = _mock_client()
        svc = _build_service(client)

        await svc.list_promoted_views(uuid.uuid4())
        sparql = client.query.call_args[0][0]
        assert "OPTIONAL" in sparql
        assert PRED_FROM_QUERY in sparql
        assert PRED_TYPE_FILTER in sparql
        assert PRED_SCOPE_QUERY in sparql

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_views(self):
        """Returns empty list when user has no promoted views."""
        client = _mock_client()
        svc = _build_service(client)

        result = await svc.list_promoted_views(uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_views_mixed_fields(self):
        """Multiple views — some with all fields, some with none."""
        v1 = str(uuid.uuid4())
        v2 = str(uuid.uuid4())
        q1 = str(uuid.uuid4())
        client = _mock_client()
        client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {
                    "view": {"value": f"urn:sempkm:query-view:{v1}"},
                    "query": {"value": f"urn:sempkm:query:{q1}"},
                    "label": {"value": "Query-based View"},
                    "renderer": {"value": "table"},
                    "text": {"value": "SELECT ?s WHERE { ?s a <urn:T> }"},
                },
                {
                    "view": {"value": f"urn:sempkm:query-view:{v2}"},
                    "label": {"value": "Generic View"},
                    "renderer": {"value": "graph"},
                    "typeFilter": {"value": "http://example.org/Project"},
                },
            ]}
        })
        svc = _build_service(client)

        result = await svc.list_promoted_views(uuid.uuid4())
        assert len(result) == 2

        pv1 = result[0]
        assert pv1.query_id == q1
        assert pv1.query_text == "SELECT ?s WHERE { ?s a <urn:T> }"
        assert pv1.type_filter == ""

        pv2 = result[1]
        assert pv2.query_id == ""
        assert pv2.query_text == ""
        assert pv2.type_filter == "http://example.org/Project"
        assert pv2.scope_query_id == ""


# ── delete_promoted_view ───────────────────────────────────────


class TestDeletePromotedView:
    """Tests for QueryService.delete_promoted_view()."""

    @pytest.mark.asyncio
    async def test_deletes_view_by_id(self):
        """delete_promoted_view sends DELETE SPARQL for the view IRI."""
        client = _mock_client()
        svc = _build_service(client)
        view_id = uuid.uuid4()
        user_id = uuid.uuid4()

        result = await svc.delete_promoted_view(view_id, user_id)
        assert result is True
        client.update.assert_called_once()
        sparql = client.update.call_args[0][0]
        assert "DELETE" in sparql
        assert str(view_id) in sparql
        assert str(user_id) in sparql
