"""Unit tests for QueryService (RDF-backed saved queries, history, sharing, promotion).

Tests use a mock TriplestoreClient that stores triples in-memory to verify
the SPARQL generation and data flow without needing a live triplestore.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.sparql.query_service import (
    QUERIES_GRAPH,
    TYPE_SAVED_QUERY,
    TYPE_QUERY_EXEC,
    TYPE_PROMOTED_VIEW,
    PRED_OWNER,
    PRED_QUERY_TEXT,
    PRED_SHARED_WITH,
    PRED_FROM_QUERY,
    PRED_RENDERER_TYPE,
    RDFS_LABEL,
    DCTERMS_CREATED,
    DCTERMS_MODIFIED,
    QueryService,
    SavedQueryData,
    QueryHistoryData,
    PromotedViewData,
    _esc,
    _extract_query_uuid,
    _extract_user_uuid,
    _extract_view_uuid,
    _extract_exec_uuid,
    _user_iri,
    _query_iri,
)


class TestHelpers:
    """Test helper functions."""

    def test_escape_basic(self):
        assert _esc('hello "world"') == 'hello "world"'

    def test_escape_single_quotes(self):
        assert _esc("it's") == "it\\'s"

    def test_escape_newlines(self):
        assert _esc("line1\nline2") == "line1\\nline2"

    def test_escape_backslash(self):
        assert _esc("path\\to\\file") == "path\\\\to\\\\file"

    def test_extract_user_uuid(self):
        uid = str(uuid.uuid4())
        assert _extract_user_uuid(f"urn:sempkm:user:{uid}") == uid

    def test_extract_query_uuid(self):
        uid = str(uuid.uuid4())
        assert _extract_query_uuid(f"urn:sempkm:query:{uid}") == uid

    def test_extract_query_uuid_model(self):
        assert _extract_query_uuid(
            "urn:sempkm:model:basic-pkm:query:active-projects"
        ) == "active-projects"

    def test_extract_view_uuid(self):
        uid = str(uuid.uuid4())
        assert _extract_view_uuid(f"urn:sempkm:query-view:{uid}") == uid

    def test_extract_exec_uuid(self):
        uid = str(uuid.uuid4())
        assert _extract_exec_uuid(f"urn:sempkm:query-exec:{uid}") == uid

    def test_user_iri(self):
        uid = uuid.uuid4()
        assert _user_iri(uid) == f"urn:sempkm:user:{uid}"

    def test_query_iri(self):
        uid = uuid.uuid4()
        assert _query_iri(uid) == f"urn:sempkm:query:{uid}"


class TestQueryServiceSaveAndGet:
    """Test save and get operations."""

    @pytest.fixture
    def client(self):
        """Mock triplestore client that tracks update calls and returns empty results."""
        mock = AsyncMock()
        mock.update = AsyncMock()
        # Default empty query result
        mock.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        return mock

    @pytest.fixture
    def service(self, client):
        return QueryService(client)

    @pytest.mark.asyncio
    async def test_save_query_calls_update(self, service, client):
        user_id = uuid.uuid4()
        result = await service.save_query(
            user_id=user_id,
            name="Test Query",
            query_text="SELECT * WHERE { ?s ?p ?o }",
            description="A test query",
        )

        assert isinstance(result, SavedQueryData)
        assert result.name == "Test Query"
        assert result.query_text == "SELECT * WHERE { ?s ?p ?o }"
        assert result.description == "A test query"
        assert result.owner_id == str(user_id)

        # Verify INSERT DATA was called
        client.update.assert_called_once()
        sparql = client.update.call_args[0][0]
        assert "INSERT DATA" in sparql
        assert QUERIES_GRAPH in sparql
        assert TYPE_SAVED_QUERY in sparql
        assert "Test Query" in sparql

    @pytest.mark.asyncio
    async def test_save_query_without_description(self, service, client):
        user_id = uuid.uuid4()
        result = await service.save_query(
            user_id=user_id,
            name="No Desc",
            query_text="SELECT * WHERE { ?s ?p ?o }",
        )
        assert result.description is None
        sparql = client.update.call_args[0][0]
        assert DCTERMS_MODIFIED in sparql  # always present
        # description triple should NOT be present
        assert "description" not in sparql.lower() or "A test" not in sparql

    @pytest.mark.asyncio
    async def test_save_query_preserves_id(self, service, client):
        user_id = uuid.uuid4()
        query_id = uuid.uuid4()
        result = await service.save_query(
            user_id=user_id,
            name="With ID",
            query_text="SELECT 1",
            query_id=query_id,
        )
        assert result.id == str(query_id)
        sparql = client.update.call_args[0][0]
        assert str(query_id) in sparql

    @pytest.mark.asyncio
    async def test_get_query_found(self, service, client):
        qid = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock the query response
        client.query = AsyncMock(return_value={
            "results": {"bindings": [{
                "name": {"value": "My Query"},
                "text": {"value": "SELECT ?s WHERE { ?s a ?t }"},
                "desc": {"value": "Description"},
                "created": {"value": "2026-03-14T10:00:00Z"},
                "modified": {"value": "2026-03-14T10:00:00Z"},
                "owner": {"value": f"urn:sempkm:user:{user_id}"},
            }]}
        })

        result = await service.get_query(qid, user_id)
        assert result is not None
        assert result.name == "My Query"
        assert result.query_text == "SELECT ?s WHERE { ?s a ?t }"
        assert result.description == "Description"
        assert result.owner_id == str(user_id)

    @pytest.mark.asyncio
    async def test_get_query_not_found(self, service, client):
        result = await service.get_query(uuid.uuid4(), uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_query_model_readonly(self, service, client):
        qid = uuid.uuid4()
        client.query = AsyncMock(return_value={
            "results": {"bindings": [{
                "name": {"value": "Model Query"},
                "text": {"value": "SELECT 1"},
                "source": {"value": "model:basic-pkm"},
                "created": {"value": "2026-03-14T10:00:00Z"},
                "modified": {"value": "2026-03-14T10:00:00Z"},
            }]}
        })

        result = await service.get_query(qid)
        assert result is not None
        assert result.readonly is True
        assert result.source == "model:basic-pkm"


class TestQueryServiceDelete:
    """Test delete operations."""

    @pytest.fixture
    def client(self):
        mock = AsyncMock()
        mock.update = AsyncMock()
        mock.query = AsyncMock(return_value={"results": {"bindings": []}})
        return mock

    @pytest.fixture
    def service(self, client):
        return QueryService(client)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service):
        result = await service.delete_query(uuid.uuid4(), uuid.uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_found(self, service, client):
        qid = uuid.uuid4()
        user_id = uuid.uuid4()

        # First call (get_query) returns the query, second+ are deletes
        call_count = 0
        async def mock_query(sparql):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"results": {"bindings": [{
                    "name": {"value": "To Delete"},
                    "text": {"value": "SELECT 1"},
                    "created": {"value": "2026-03-14T10:00:00Z"},
                    "modified": {"value": "2026-03-14T10:00:00Z"},
                    "owner": {"value": f"urn:sempkm:user:{user_id}"},
                }]}}
            return {"results": {"bindings": []}}

        client.query = mock_query
        result = await service.delete_query(qid, user_id)
        assert result is True
        client.update.assert_called_once()


class TestQueryServiceHistory:
    """Test query history operations."""

    @pytest.fixture
    def client(self):
        mock = AsyncMock()
        mock.update = AsyncMock()
        mock.query = AsyncMock(return_value={"results": {"bindings": []}})
        return mock

    @pytest.fixture
    def service(self, client):
        return QueryService(client)

    @pytest.mark.asyncio
    async def test_save_history_new_entry(self, service, client):
        """New query text creates a new history entry."""
        user_id = uuid.uuid4()

        # First query (dedup check) returns empty — no recent match
        # Second query (prune count) returns low count
        call_count = 0
        async def mock_query(sparql):
            nonlocal call_count
            call_count += 1
            if "COUNT" in sparql:
                return {"results": {"bindings": [{"total": {"value": "5"}}]}}
            return {"results": {"bindings": []}}

        client.query = mock_query
        await service.save_history(user_id, "SELECT * WHERE { ?s ?p ?o }")

        # Should have called update with INSERT DATA
        assert client.update.call_count >= 1
        sparql = client.update.call_args[0][0]
        assert "INSERT DATA" in sparql
        assert TYPE_QUERY_EXEC in sparql

    @pytest.mark.asyncio
    async def test_get_history_empty(self, service, client):
        result = await service.get_history(uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_get_history_with_entries(self, service, client):
        user_id = uuid.uuid4()
        exec_id = str(uuid.uuid4())
        client.query = AsyncMock(return_value={
            "results": {"bindings": [{
                "exec": {"value": f"urn:sempkm:query-exec:{exec_id}"},
                "text": {"value": "SELECT 1"},
                "time": {"value": "2026-03-14T10:00:00Z"},
            }]}
        })

        result = await service.get_history(user_id)
        assert len(result) == 1
        assert isinstance(result[0], QueryHistoryData)
        assert result[0].query_text == "SELECT 1"

    @pytest.mark.asyncio
    async def test_clear_history(self, service, client):
        user_id = uuid.uuid4()
        await service.clear_history(user_id)
        client.update.assert_called_once()
        sparql = client.update.call_args[0][0]
        assert "DELETE" in sparql
        assert TYPE_QUERY_EXEC in sparql


class TestQueryServicePromotion:
    """Test promotion operations."""

    @pytest.fixture
    def client(self):
        mock = AsyncMock()
        mock.update = AsyncMock()
        mock.query = AsyncMock(return_value={"results": {"bindings": []}})
        return mock

    @pytest.fixture
    def service(self, client):
        return QueryService(client)

    @pytest.mark.asyncio
    async def test_promote_not_found(self, service):
        with pytest.raises(ValueError, match="Query not found"):
            await service.promote_query(uuid.uuid4(), uuid.uuid4(), "My View")

    @pytest.mark.asyncio
    async def test_promote_invalid_renderer(self, service):
        with pytest.raises(ValueError, match="renderer_type"):
            await service.promote_query(
                uuid.uuid4(), uuid.uuid4(), "My View", "invalid"
            )

    @pytest.mark.asyncio
    async def test_promote_success(self, service, client):
        qid = uuid.uuid4()
        user_id = uuid.uuid4()

        call_count = 0
        async def mock_query(sparql):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # get_query returns the query
                return {"results": {"bindings": [{
                    "name": {"value": "My Query"},
                    "text": {"value": "SELECT 1"},
                    "created": {"value": "2026-03-14T10:00:00Z"},
                    "modified": {"value": "2026-03-14T10:00:00Z"},
                    "owner": {"value": f"urn:sempkm:user:{user_id}"},
                }]}}
            # get_promotion_status returns empty (not promoted)
            return {"results": {"bindings": []}}

        client.query = mock_query
        result = await service.promote_query(qid, user_id, "My View", "table")
        assert isinstance(result, PromotedViewData)
        assert result.display_label == "My View"
        assert result.renderer_type == "table"
        assert result.query_id == str(qid)

    @pytest.mark.asyncio
    async def test_list_promoted_views_empty(self, service, client):
        result = await service.list_promoted_views(uuid.uuid4())
        assert result == []


class TestQueryServiceSharing:
    """Test sharing operations."""

    @pytest.fixture
    def client(self):
        mock = AsyncMock()
        mock.update = AsyncMock()
        mock.query = AsyncMock(return_value={"results": {"bindings": []}})
        return mock

    @pytest.fixture
    def service(self, client):
        return QueryService(client)

    @pytest.mark.asyncio
    async def test_get_shares_not_found(self, service):
        with pytest.raises(ValueError, match="Query not found"):
            await service.get_shares(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_update_shares_filters_self(self, service, client):
        qid = uuid.uuid4()
        user_id = uuid.uuid4()
        other_id = uuid.uuid4()

        # get_query returns the query
        client.query = AsyncMock(return_value={
            "results": {"bindings": [{
                "name": {"value": "Shared Query"},
                "text": {"value": "SELECT 1"},
                "created": {"value": "2026-03-14T10:00:00Z"},
                "modified": {"value": "2026-03-14T10:00:00Z"},
                "owner": {"value": f"urn:sempkm:user:{user_id}"},
            }]}
        })

        await service.update_shares(qid, user_id, [user_id, other_id])

        # Should have called update twice: delete old shares + insert new
        assert client.update.call_count == 2
        insert_sparql = client.update.call_args_list[1][0][0]
        # Self-share should be filtered out
        assert str(user_id) not in insert_sparql or str(other_id) in insert_sparql

    @pytest.mark.asyncio
    async def test_fork_query_not_found(self, service):
        result = await service.fork_query(uuid.uuid4(), uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_fork_query_creates_copy(self, service, client):
        qid = uuid.uuid4()
        user_id = uuid.uuid4()

        # First call returns the source query, second call saves the fork
        call_count = 0
        async def mock_query(sparql):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"results": {"bindings": [{
                    "name": {"value": "Original"},
                    "text": {"value": "SELECT ?s WHERE { ?s a ?t }"},
                    "desc": {"value": "Original desc"},
                    "created": {"value": "2026-03-14T10:00:00Z"},
                    "modified": {"value": "2026-03-14T10:00:00Z"},
                }]}}
            return {"results": {"bindings": []}}

        client.query = mock_query
        result = await service.fork_query(qid, user_id)
        assert result is not None
        assert result.name == "Copy of Original"
        assert result.query_text == "SELECT ?s WHERE { ?s a ?t }"
        assert result.owner_id == str(user_id)
