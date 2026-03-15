"""Unit tests for OperationsLogService.

Validates SPARQL string generation, escaping, pagination logic,
and result parsing — all with a mocked TriplestoreClient (no
running triplestore needed).
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.ops_log import (
    OperationsLogService,
    OPS_LOG_GRAPH,
    PROV_ACTIVITY,
    PROV_STARTED_AT_TIME,
    PROV_ENDED_AT_TIME,
    PROV_WAS_ASSOCIATED_WITH,
    PROV_USED,
    SEMPKM_ACTIVITY_TYPE,
    SEMPKM_STATUS,
    SEMPKM_ERROR_MESSAGE,
    RDFS_LABEL,
    SYSTEM_ACTOR_IRI,
    _esc,
)


@pytest.fixture
def mock_client():
    """Create a mock TriplestoreClient with async methods."""
    client = AsyncMock()
    client.update = AsyncMock(return_value=None)
    client.query = AsyncMock(return_value={"results": {"bindings": []}})
    return client


@pytest.fixture
def service(mock_client):
    return OperationsLogService(mock_client)


# ---- _esc() tests ----


class TestEscaping:
    def test_esc_backslash(self):
        assert _esc("path\\to\\file") == "path\\\\to\\\\file"

    def test_esc_single_quote(self):
        assert _esc("it's a test") == "it\\'s a test"

    def test_esc_newline(self):
        assert _esc("line1\nline2") == "line1\\nline2"

    def test_esc_tab(self):
        assert _esc("col1\tcol2") == "col1\\tcol2"

    def test_esc_carriage_return(self):
        assert _esc("line\r\nend") == "line\\r\\nend"

    def test_esc_combined(self):
        """Multiple special chars in one string."""
        raw = "it's a\\path\nwith\ttabs"
        escaped = _esc(raw)
        assert "\\" in escaped  # backslash escaped
        assert "\\'" in escaped  # quote escaped
        assert "\\n" in escaped  # newline escaped
        assert "\\t" in escaped  # tab escaped

    def test_esc_plain_string(self):
        """No special chars — string passes through unchanged."""
        assert _esc("hello world") == "hello world"


# ---- log_activity() tests ----


class TestLogActivity:
    @pytest.mark.asyncio
    async def test_insert_data_contains_graph_wrapper(self, service, mock_client):
        await service.log_activity(
            activity_type="model.install",
            label="Installed test model",
        )
        sparql = mock_client.update.call_args[0][0]
        assert "INSERT DATA" in sparql
        assert f"GRAPH <{OPS_LOG_GRAPH}>" in sparql

    @pytest.mark.asyncio
    async def test_insert_contains_prov_activity_type(self, service, mock_client):
        await service.log_activity(
            activity_type="model.install",
            label="Installed test model",
        )
        sparql = mock_client.update.call_args[0][0]
        assert f"a <{PROV_ACTIVITY}>" in sparql

    @pytest.mark.asyncio
    async def test_insert_contains_prov_timestamps(self, service, mock_client):
        await service.log_activity(
            activity_type="inference.run",
            label="Ran inference",
            started_at="2025-01-15T10:00:00Z",
            ended_at="2025-01-15T10:01:00Z",
        )
        sparql = mock_client.update.call_args[0][0]
        assert f"<{PROV_STARTED_AT_TIME}>" in sparql
        assert f"<{PROV_ENDED_AT_TIME}>" in sparql
        assert "2025-01-15T10:00:00Z" in sparql
        assert "2025-01-15T10:01:00Z" in sparql

    @pytest.mark.asyncio
    async def test_insert_contains_activity_type_predicate(self, service, mock_client):
        await service.log_activity(
            activity_type="validation.run",
            label="Validation run",
        )
        sparql = mock_client.update.call_args[0][0]
        assert f"<{SEMPKM_ACTIVITY_TYPE}>" in sparql
        assert "'validation.run'" in sparql

    @pytest.mark.asyncio
    async def test_insert_contains_rdfs_label(self, service, mock_client):
        await service.log_activity(
            activity_type="model.install",
            label="Installed ACME Model v2",
        )
        sparql = mock_client.update.call_args[0][0]
        assert f"<{RDFS_LABEL}>" in sparql
        assert "Installed ACME Model v2" in sparql

    @pytest.mark.asyncio
    async def test_default_actor_is_system(self, service, mock_client):
        """When actor is None, defaults to urn:sempkm:system."""
        await service.log_activity(
            activity_type="validation.run",
            label="Validation run",
        )
        sparql = mock_client.update.call_args[0][0]
        assert f"<{PROV_WAS_ASSOCIATED_WITH}>" in sparql
        assert f"<{SYSTEM_ACTOR_IRI}>" in sparql

    @pytest.mark.asyncio
    async def test_custom_actor(self, service, mock_client):
        actor = "urn:sempkm:user:abc-123"
        await service.log_activity(
            activity_type="model.install",
            label="Install",
            actor=actor,
        )
        sparql = mock_client.update.call_args[0][0]
        assert f"<{actor}>" in sparql

    @pytest.mark.asyncio
    async def test_used_iris(self, service, mock_client):
        used = [
            "urn:sempkm:model:acme-model",
            "urn:sempkm:ontology:gist",
        ]
        await service.log_activity(
            activity_type="model.install",
            label="Install with deps",
            used_iris=used,
        )
        sparql = mock_client.update.call_args[0][0]
        assert f"<{PROV_USED}>" in sparql
        for iri in used:
            assert f"<{iri}>" in sparql

    @pytest.mark.asyncio
    async def test_failed_status_triples(self, service, mock_client):
        await service.log_activity(
            activity_type="inference.run",
            label="Inference failed",
            status="failed",
            error_message="Timeout after 30s",
        )
        sparql = mock_client.update.call_args[0][0]
        assert f"<{SEMPKM_STATUS}>" in sparql
        assert "'failed'" in sparql
        assert f"<{SEMPKM_ERROR_MESSAGE}>" in sparql
        assert "Timeout after 30s" in sparql

    @pytest.mark.asyncio
    async def test_no_status_triples_when_not_provided(self, service, mock_client):
        await service.log_activity(
            activity_type="model.install",
            label="Success install",
        )
        sparql = mock_client.update.call_args[0][0]
        assert f"<{SEMPKM_STATUS}>" not in sparql
        assert f"<{SEMPKM_ERROR_MESSAGE}>" not in sparql

    @pytest.mark.asyncio
    async def test_label_escaping(self, service, mock_client):
        """Special chars in label are properly escaped."""
        await service.log_activity(
            activity_type="model.install",
            label="Model's \"test\"\nwith newline",
        )
        sparql = mock_client.update.call_args[0][0]
        assert "\\'" in sparql  # escaped single quote
        assert "\\n" in sparql  # escaped newline

    @pytest.mark.asyncio
    async def test_returns_activity_iri(self, service, mock_client):
        iri = await service.log_activity(
            activity_type="model.install",
            label="Test",
        )
        assert iri.startswith("urn:sempkm:ops-log:")

    @pytest.mark.asyncio
    async def test_error_message_escaping(self, service, mock_client):
        """Error messages with special chars are escaped."""
        await service.log_activity(
            activity_type="inference.run",
            label="Failed",
            status="failed",
            error_message="Error: can't parse\tvalue\\path",
        )
        sparql = mock_client.update.call_args[0][0]
        assert "can\\'t" in sparql
        assert "\\t" in sparql
        assert "\\\\" in sparql


# ---- list_activities() tests ----


class TestListActivities:
    @pytest.mark.asyncio
    async def test_basic_query_structure(self, service, mock_client):
        await service.list_activities()
        sparql = mock_client.query.call_args[0][0]
        assert "SELECT" in sparql
        assert f"GRAPH <{OPS_LOG_GRAPH}>" in sparql
        assert "ORDER BY DESC(?startedAt)" in sparql

    @pytest.mark.asyncio
    async def test_cursor_filter(self, service, mock_client):
        cursor = "2025-01-15T10:00:00Z"
        await service.list_activities(cursor=cursor)
        sparql = mock_client.query.call_args[0][0]
        assert f'FILTER(?startedAt < "{cursor}"' in sparql

    @pytest.mark.asyncio
    async def test_activity_type_filter(self, service, mock_client):
        await service.list_activities(activity_type="model.install")
        sparql = mock_client.query.call_args[0][0]
        assert "FILTER(STR(?activityType)" in sparql
        assert "model.install" in sparql

    @pytest.mark.asyncio
    async def test_limit_plus_one_for_pagination(self, service, mock_client):
        """Fetches limit+1 rows to detect next page."""
        await service.list_activities(limit=20)
        sparql = mock_client.query.call_args[0][0]
        assert "LIMIT 21" in sparql

    @pytest.mark.asyncio
    async def test_no_next_cursor_when_fewer_results(self, service, mock_client):
        mock_client.query.return_value = {
            "results": {"bindings": [_make_binding("a1", "2025-01-15T10:00:00Z")]}
        }
        activities, next_cursor = await service.list_activities(limit=50)
        assert len(activities) == 1
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_next_cursor_when_more_results(self, service, mock_client):
        """When we get limit+1 results, return a cursor for the next page."""
        # Create 3 bindings, request limit=2 — should return 2 + cursor
        bindings = [
            _make_binding("a1", "2025-01-15T12:00:00Z"),
            _make_binding("a2", "2025-01-15T11:00:00Z"),
            _make_binding("a3", "2025-01-15T10:00:00Z"),
        ]
        mock_client.query.return_value = {"results": {"bindings": bindings}}
        activities, next_cursor = await service.list_activities(limit=2)
        assert len(activities) == 2
        assert next_cursor == "2025-01-15T11:00:00Z"

    @pytest.mark.asyncio
    async def test_result_parsing(self, service, mock_client):
        """Verify dict structure from SPARQL bindings."""
        mock_client.query.return_value = {
            "results": {
                "bindings": [
                    _make_binding(
                        "a1",
                        "2025-01-15T10:00:00Z",
                        activity_type="model.install",
                        label="Installed model",
                        ended_at="2025-01-15T10:01:00Z",
                        actor="urn:sempkm:user:u1",
                        status="success",
                    )
                ]
            }
        }
        activities, _ = await service.list_activities()
        assert len(activities) == 1
        a = activities[0]
        assert a["activity_type"] == "model.install"
        assert a["label"] == "Installed model"
        assert a["started_at"] == "2025-01-15T10:00:00Z"
        assert a["ended_at"] == "2025-01-15T10:01:00Z"
        assert a["actor"] == "urn:sempkm:user:u1"
        assert a["status"] == "success"

    @pytest.mark.asyncio
    async def test_combined_cursor_and_type_filter(self, service, mock_client):
        await service.list_activities(
            activity_type="inference.run",
            cursor="2025-06-01T00:00:00Z",
        )
        sparql = mock_client.query.call_args[0][0]
        assert "FILTER(?startedAt <" in sparql
        assert "FILTER(STR(?activityType)" in sparql


# ---- get_activity() tests ----


class TestGetActivity:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, service, mock_client):
        result = await service.get_activity("urn:sempkm:ops-log:nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_dict_with_iri(self, service, mock_client):
        iri = "urn:sempkm:ops-log:abc-123"
        mock_client.query.return_value = {
            "results": {
                "bindings": [
                    _make_binding(
                        "a1",
                        "2025-01-15T10:00:00Z",
                        include_iri=False,
                    )
                ]
            }
        }
        result = await service.get_activity(iri)
        assert result is not None
        assert result["iri"] == iri

    @pytest.mark.asyncio
    async def test_collects_used_iris(self, service, mock_client):
        iri = "urn:sempkm:ops-log:abc-123"
        binding1 = _make_binding("a1", "2025-01-15T10:00:00Z", include_iri=False)
        binding1["used"] = {"type": "uri", "value": "urn:sempkm:model:m1"}
        binding2 = _make_binding("a1", "2025-01-15T10:00:00Z", include_iri=False)
        binding2["used"] = {"type": "uri", "value": "urn:sempkm:model:m2"}
        mock_client.query.return_value = {
            "results": {"bindings": [binding1, binding2]}
        }
        result = await service.get_activity(iri)
        assert result is not None
        assert result["used"] == [
            "urn:sempkm:model:m1",
            "urn:sempkm:model:m2",
        ]

    @pytest.mark.asyncio
    async def test_query_uses_activity_iri(self, service, mock_client):
        iri = "urn:sempkm:ops-log:test-id"
        await service.get_activity(iri)
        sparql = mock_client.query.call_args[0][0]
        assert f"<{iri}>" in sparql


# ---- count_activities() tests ----


class TestCountActivities:
    @pytest.mark.asyncio
    async def test_count_all(self, service, mock_client):
        mock_client.query.return_value = {
            "results": {"bindings": [{"total": {"value": "42"}}]}
        }
        count = await service.count_activities()
        assert count == 42
        sparql = mock_client.query.call_args[0][0]
        assert "COUNT(?activity)" in sparql

    @pytest.mark.asyncio
    async def test_count_with_type_filter(self, service, mock_client):
        mock_client.query.return_value = {
            "results": {"bindings": [{"total": {"value": "5"}}]}
        }
        count = await service.count_activities(activity_type="model.install")
        assert count == 5
        sparql = mock_client.query.call_args[0][0]
        assert "FILTER(STR(?activityType)" in sparql
        assert "model.install" in sparql

    @pytest.mark.asyncio
    async def test_count_returns_zero_on_empty(self, service, mock_client):
        mock_client.query.return_value = {"results": {"bindings": []}}
        count = await service.count_activities()
        assert count == 0


# ---- Helper to build SPARQL JSON bindings ----


def _make_binding(
    activity_id: str = "a1",
    started_at: str = "2025-01-15T10:00:00Z",
    activity_type: str = "model.install",
    label: str = "Test activity",
    ended_at: str = "2025-01-15T10:01:00Z",
    actor: str = "urn:sempkm:system",
    status: str | None = None,
    error_message: str | None = None,
    include_iri: bool = True,
) -> dict:
    """Build a mock SPARQL JSON binding dict matching the SELECT pattern."""
    b: dict = {}
    if include_iri:
        b["activity"] = {
            "type": "uri",
            "value": f"urn:sempkm:ops-log:{activity_id}",
        }
    b["label"] = {"type": "literal", "value": label}
    b["activityType"] = {"type": "literal", "value": activity_type}
    b["startedAt"] = {
        "type": "literal",
        "value": started_at,
        "datatype": "http://www.w3.org/2001/XMLSchema#dateTime",
    }
    b["endedAt"] = {
        "type": "literal",
        "value": ended_at,
        "datatype": "http://www.w3.org/2001/XMLSchema#dateTime",
    }
    b["actor"] = {"type": "uri", "value": actor}
    if status:
        b["status"] = {"type": "literal", "value": status}
    if error_message:
        b["errorMessage"] = {"type": "literal", "value": error_message}
    return b
