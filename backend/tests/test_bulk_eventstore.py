"""Tests for EventStore.commit_bulk() and SDK BulkAccumulator.

Covers:
- Summary metadata structure (BulkEvent type, ~10 triples)
- Operation count and affected count accuracy
- Batch size limit enforcement (>1000 raises ValueError)
- Data triples still materialize correctly
- All-or-nothing undo semantics (transaction rollback)
- SDK bulk() context manager accumulation and submission
- SDK bulk() discards batch on exception
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest

from app.events.models import (
    BULK_EVENT_TYPE,
    EVENT_AFFECTED_COUNT,
    EVENT_OPERATION_COUNT,
    EVENT_PERFORMED_BY,
    EVENT_SOURCE,
    EVENT_SUMMARY,
    EVENT_TIMESTAMP,
)
from app.events.store import EventStore, EventResult, Operation
from rdflib import URIRef, Literal, RDF, XSD


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_client() -> AsyncMock:
    """Return a mock TriplestoreClient that simulates transaction lifecycle."""
    client = AsyncMock()
    client.begin_transaction.return_value = "http://rdf4j/txn/1"
    client.transaction_update.return_value = None
    client.commit_transaction.return_value = None
    client.rollback_transaction.return_value = None
    return client


@pytest.fixture()
def event_store(mock_client: AsyncMock) -> EventStore:
    return EventStore(mock_client)


def _make_operation(
    op_type: str = "object.create",
    affected_iris: list[str] | None = None,
    description: str = "test op",
    inserts: list[tuple] | None = None,
    deletes: list[tuple] | None = None,
) -> Operation:
    """Build a minimal Operation for testing."""
    return Operation(
        operation_type=op_type,
        affected_iris=affected_iris or ["urn:test:obj1"],
        description=description,
        data_triples=[],
        materialize_inserts=inserts or [
            (URIRef("urn:test:obj1"), RDF.type, URIRef("urn:test:Type")),
        ],
        materialize_deletes=deletes or [],
    )


# ---------------------------------------------------------------------------
# commit_bulk() metadata structure
# ---------------------------------------------------------------------------


class TestCommitBulkMetadata:
    """Verify that commit_bulk produces correct BulkEvent metadata."""

    @pytest.mark.asyncio
    async def test_produces_bulk_event_type(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        """The event graph should have rdf:type sempkm:BulkEvent."""
        ops = [_make_operation()]
        result = await event_store.commit_bulk(
            ops, performed_by=URIRef("urn:user:alice"), summary="test", source="app-1"
        )

        assert isinstance(result, EventResult)
        assert str(result.event_iri).startswith("urn:sempkm:event:")

        # Inspect the SPARQL sent to transaction_update
        first_update_call = mock_client.transaction_update.call_args_list[0]
        sparql = first_update_call[0][1]  # second positional arg

        assert "BulkEvent" in sparql
        assert "sempkm:summary" in sparql or "summary" in sparql.lower()

    @pytest.mark.asyncio
    async def test_metadata_triple_count_is_bounded(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        """Metadata should be ~7-8 triples regardless of batch size, not N*5."""
        ops = [_make_operation(affected_iris=[f"urn:test:obj{i}"]) for i in range(50)]
        await event_store.commit_bulk(
            ops,
            performed_by=URIRef("urn:user:alice"),
            summary="bulk import",
            source="importer",
        )

        # First transaction_update = event metadata graph
        first_sparql = mock_client.transaction_update.call_args_list[0][0][1]

        # Count triple lines (lines with " . " ending inside the INSERT DATA)
        triple_lines = [
            line for line in first_sparql.split("\n")
            if line.strip().endswith(" .")
            and not line.strip().startswith("GRAPH")
        ]
        # Should be ~7-8 triples (type, timestamp, summary, source, opCount, affectedCount, performedBy)
        # NOT 50*5 = 250
        assert len(triple_lines) <= 15, f"Expected ≤15 metadata triples, got {len(triple_lines)}"

    @pytest.mark.asyncio
    async def test_summary_and_source_in_metadata(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        """Summary and source strings appear in the event metadata."""
        ops = [_make_operation()]
        await event_store.commit_bulk(
            ops, summary="imported 50 contacts", source="crm-sync-app"
        )

        first_sparql = mock_client.transaction_update.call_args_list[0][0][1]
        assert "imported 50 contacts" in first_sparql
        assert "crm-sync-app" in first_sparql

    @pytest.mark.asyncio
    async def test_performed_by_included_when_provided(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        actor = URIRef("urn:user:bob")
        await event_store.commit_bulk(
            [_make_operation()], performed_by=actor, summary="s", source="x"
        )

        first_sparql = mock_client.transaction_update.call_args_list[0][0][1]
        assert "urn:user:bob" in first_sparql

    @pytest.mark.asyncio
    async def test_performed_by_omitted_when_none(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        await event_store.commit_bulk(
            [_make_operation()], performed_by=None, summary="s", source="x"
        )

        first_sparql = mock_client.transaction_update.call_args_list[0][0][1]
        assert "wasAssociatedWith" not in first_sparql


# ---------------------------------------------------------------------------
# Operation count and affected count
# ---------------------------------------------------------------------------


class TestBulkCounts:
    """Verify operation_count and affected_count accuracy."""

    @pytest.mark.asyncio
    async def test_operation_count_matches_input(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        ops = [_make_operation() for _ in range(7)]
        await event_store.commit_bulk(ops, summary="s", source="x")

        first_sparql = mock_client.transaction_update.call_args_list[0][0][1]
        # operationCount should be 7
        assert '"7"' in first_sparql

    @pytest.mark.asyncio
    async def test_affected_count_deduplicates_iris(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        """If 5 operations all affect urn:test:obj1, affectedCount should be 1."""
        ops = [_make_operation(affected_iris=["urn:test:obj1"]) for _ in range(5)]
        await event_store.commit_bulk(ops, summary="s", source="x")

        first_sparql = mock_client.transaction_update.call_args_list[0][0][1]
        # Should see affectedCount = 1 (all same IRI), operationCount = 5
        assert '"5"' in first_sparql  # operation count
        assert '"1"' in first_sparql  # affected count (deduplicated)

    @pytest.mark.asyncio
    async def test_affected_count_with_distinct_iris(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        ops = [
            _make_operation(affected_iris=["urn:test:a", "urn:test:b"]),
            _make_operation(affected_iris=["urn:test:b", "urn:test:c"]),
        ]
        await event_store.commit_bulk(ops, summary="s", source="x")

        first_sparql = mock_client.transaction_update.call_args_list[0][0][1]
        # 3 unique IRIs: a, b, c
        assert '"3"' in first_sparql  # affected count
        assert '"2"' in first_sparql  # operation count


# ---------------------------------------------------------------------------
# Batch size limit
# ---------------------------------------------------------------------------


class TestBulkBatchSizeLimit:
    """Enforce >1000 raises ValueError."""

    @pytest.mark.asyncio
    async def test_1000_operations_allowed(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        """Exactly 1000 should not raise."""
        ops = [_make_operation() for _ in range(1000)]
        result = await event_store.commit_bulk(ops, summary="s", source="x")
        assert result.event_iri is not None

    @pytest.mark.asyncio
    async def test_1001_operations_raises(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        ops = [_make_operation() for _ in range(1001)]
        with pytest.raises(ValueError, match="exceeds limit of 1000"):
            await event_store.commit_bulk(ops, summary="s", source="x")

        # Transaction should never have been started
        mock_client.begin_transaction.assert_not_called()


# ---------------------------------------------------------------------------
# Data triple materialization
# ---------------------------------------------------------------------------


class TestBulkMaterialization:
    """Data triples materialize identically to single commit."""

    @pytest.mark.asyncio
    async def test_inserts_materialize(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        triple = (URIRef("urn:test:x"), RDF.type, URIRef("urn:test:Foo"))
        ops = [_make_operation(inserts=[triple])]
        await event_store.commit_bulk(ops, summary="s", source="x")

        # Last INSERT DATA call (after metadata) should contain the data triple
        all_sparqls = [
            c[0][1] for c in mock_client.transaction_update.call_args_list
        ]
        insert_sparqls = [s for s in all_sparqls if "INSERT DATA" in s]
        # Should have at least 2: metadata + materialization
        assert len(insert_sparqls) >= 2
        materialization_sparql = insert_sparqls[-1]
        assert "urn:test:x" in materialization_sparql
        assert "urn:test:Foo" in materialization_sparql

    @pytest.mark.asyncio
    async def test_deletes_materialize_before_inserts(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        """Deletes should execute before inserts (same as single commit)."""
        delete_triple = (URIRef("urn:test:x"), URIRef("urn:test:name"), URIRef("?old_0"))
        insert_triple = (URIRef("urn:test:x"), URIRef("urn:test:name"), Literal("New"))
        ops = [_make_operation(
            deletes=[delete_triple],
            inserts=[insert_triple],
        )]
        await event_store.commit_bulk(ops, summary="s", source="x")

        all_sparqls = [
            c[0][1] for c in mock_client.transaction_update.call_args_list
        ]

        # Find indices of DELETE WHERE and last INSERT DATA
        delete_idx = None
        insert_idx = None
        for i, s in enumerate(all_sparqls):
            if "DELETE WHERE" in s:
                delete_idx = i
            if "INSERT DATA" in s and "urn:test:x" in s:
                insert_idx = i

        assert delete_idx is not None, "No DELETE WHERE found"
        assert insert_idx is not None, "No INSERT DATA for materialization found"
        assert delete_idx < insert_idx, "Deletes must precede inserts"


# ---------------------------------------------------------------------------
# All-or-nothing rollback
# ---------------------------------------------------------------------------


class TestBulkRollback:
    """Transaction failure rolls back everything."""

    @pytest.mark.asyncio
    async def test_rollback_on_transaction_failure(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        """If transaction_update fails, rollback should be called."""
        mock_client.transaction_update.side_effect = [
            None,  # metadata write succeeds
            RuntimeError("Triplestore down"),  # materialization fails
        ]

        ops = [_make_operation()]
        with pytest.raises(RuntimeError, match="Triplestore down"):
            await event_store.commit_bulk(ops, summary="s", source="x")

        mock_client.rollback_transaction.assert_called_once()
        mock_client.commit_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_rollback_on_commit_failure(
        self, event_store: EventStore, mock_client: AsyncMock
    ):
        """If commit_transaction fails, rollback should be called."""
        mock_client.commit_transaction.side_effect = RuntimeError("Commit failed")

        ops = [_make_operation()]
        with pytest.raises(RuntimeError, match="Commit failed"):
            await event_store.commit_bulk(ops, summary="s", source="x")

        mock_client.rollback_transaction.assert_called_once()


# ---------------------------------------------------------------------------
# SDK BulkAccumulator / CommandClient.bulk()
# ---------------------------------------------------------------------------


class TestSDKBulkContextManager:
    """Test the SDK CommandClient.bulk() async context manager."""

    @pytest.fixture()
    def mock_httpx_client(self) -> AsyncMock:
        client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "event_iri": "urn:sempkm:event:test",
            "timestamp": "2026-01-01T00:00:00Z",
            "operation_count": 2,
            "affected_count": 2,
        }
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response
        return client

    @pytest.mark.asyncio
    async def test_bulk_accumulates_and_submits(self, mock_httpx_client: AsyncMock):
        from sempkm_app_sdk.clients.commands import CommandClient

        client = CommandClient(
            mock_httpx_client,
            allowed_commands={"object.create", "body.set"},
        )

        async with client.bulk(summary="import", source="test-app") as batch:
            batch.add("object.create", {"type": "Note"})
            batch.add("body.set", {"iri": "urn:test:1", "body": "hello"})
            assert batch.operation_count == 2

        # Should have posted to /api/commands/bulk
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == "/api/commands/bulk"
        payload = call_args[1]["json"]
        assert len(payload["commands"]) == 2
        assert payload["summary"] == "import"
        assert payload["source"] == "test-app"

    @pytest.mark.asyncio
    async def test_bulk_discards_on_exception(self, mock_httpx_client: AsyncMock):
        from sempkm_app_sdk.clients.commands import CommandClient

        client = CommandClient(
            mock_httpx_client,
            allowed_commands={"object.create"},
        )

        with pytest.raises(ValueError, match="oops"):
            async with client.bulk(summary="s", source="x") as batch:
                batch.add("object.create", {"type": "Note"})
                raise ValueError("oops")

        # Should NOT have posted
        mock_httpx_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_empty_batch_no_submit(self, mock_httpx_client: AsyncMock):
        from sempkm_app_sdk.clients.commands import CommandClient

        client = CommandClient(
            mock_httpx_client,
            allowed_commands={"object.create"},
        )

        async with client.bulk(summary="s", source="x") as batch:
            pass  # no commands added

        # Should NOT have posted (empty batch)
        mock_httpx_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_permission_check_on_add(self, mock_httpx_client: AsyncMock):
        from sempkm_app_sdk.clients.commands import CommandClient

        client = CommandClient(
            mock_httpx_client,
            allowed_commands={"object.create"},
        )

        async with client.bulk(summary="s", source="x") as batch:
            with pytest.raises(PermissionError, match="not permitted"):
                batch.add("edge.create", {"source": "a", "target": "b", "predicate": "p"})

        # Nothing submitted since we didn't add successfully
        mock_httpx_client.post.assert_not_called()
