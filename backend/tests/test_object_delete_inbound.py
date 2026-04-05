"""Tests for inbound edge cleanup in bulk_delete_objects().

Verifies that bulk_delete_objects() removes both outbound triples
(<iri> ?p ?o) AND inbound triples (?s ?p <iri>) so no dangling
references remain after deletion.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from rdflib import URIRef

from app.rdf.namespaces import CURRENT_GRAPH


# --- Helpers ---

def make_sparql_bindings_outbound(iri: str, triples: list[tuple[str, str, str]]):
    """Build SPARQL JSON result for outbound query (SELECT ?p ?o)."""
    bindings = []
    for _s, p, o in triples:
        bindings.append({
            "p": {"type": "uri", "value": p},
            "o": {"type": "uri", "value": o},
        })
    return {"results": {"bindings": bindings}}


def make_sparql_bindings_inbound(iri: str, triples: list[tuple[str, str]]):
    """Build SPARQL JSON result for inbound query (SELECT ?s ?p)."""
    bindings = []
    for s, p in triples:
        bindings.append({
            "s": {"type": "uri", "value": s},
            "p": {"type": "uri", "value": p},
        })
    return {"results": {"bindings": bindings}}


def empty_result():
    return {"results": {"bindings": []}}


# --- Fixtures ---

@pytest.fixture
def mock_client():
    """Mock TriplestoreClient with configurable query responses."""
    client = AsyncMock()
    client.query = AsyncMock(return_value=empty_result())
    return client


@pytest.fixture
def mock_event_store():
    """Mock EventStore that records committed operations."""
    store = AsyncMock()
    event_result = MagicMock()
    event_result.event_iri = URIRef("urn:sempkm:event:test-123")
    event_result.affected_iris = []
    store.commit = AsyncMock(return_value=event_result)
    return store


@pytest.fixture
def mock_label_service():
    """Mock LabelService."""
    service = MagicMock()
    service.invalidate = MagicMock()
    return service


@pytest.fixture
def mock_user():
    """Mock user with required attributes."""
    user = MagicMock()
    user.id = "test-user"
    user.role = "owner"
    return user


# --- Tests ---

class TestInboundEdgeCleanup:
    """Verify that bulk_delete_objects() cleans up inbound references."""

    @pytest.mark.asyncio
    async def test_inbound_triples_included_in_deletes(
        self, mock_client, mock_event_store, mock_label_service, mock_user
    ):
        """Inbound edge triples (?s ?p <iri>) must appear in materialize_deletes."""
        target_iri = "http://example.org/data/note-1"
        referring_iri = "http://example.org/data/note-2"
        pred = "http://example.org/ontology/relatedTo"

        outbound = make_sparql_bindings_outbound(target_iri, [
            (target_iri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology/Note"),
        ])
        inbound = make_sparql_bindings_inbound(target_iri, [
            (referring_iri, pred),
        ])

        # First call: outbound query; Second call: inbound query
        mock_client.query = AsyncMock(side_effect=[outbound, inbound])

        request = AsyncMock()
        request.json = AsyncMock(return_value={"iris": [target_iri]})

        from app.browser.objects import bulk_delete_objects

        with patch("app.browser.objects.require_role", return_value=lambda: mock_user):
            response = await bulk_delete_objects(
                request=request,
                user=mock_user,
                client=mock_client,
                event_store=mock_event_store,
                label_service=mock_label_service,
            )

        # Extract the operation that was committed
        assert mock_event_store.commit.called
        operations = mock_event_store.commit.call_args[0][0]
        assert len(operations) == 1
        deletes = operations[0].materialize_deletes

        # Should contain 1 outbound + 1 inbound = 2 triples
        assert len(deletes) == 2

        # Verify the inbound triple is present
        inbound_triple = (URIRef(referring_iri), URIRef(pred), URIRef(target_iri))
        assert inbound_triple in deletes, f"Inbound triple {inbound_triple} not in deletes"

    @pytest.mark.asyncio
    async def test_outbound_triples_still_included(
        self, mock_client, mock_event_store, mock_label_service, mock_user
    ):
        """Outbound triples must still be collected (no regression)."""
        target_iri = "http://example.org/data/note-1"
        type_pred = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        type_obj = "http://example.org/ontology/Note"

        outbound = make_sparql_bindings_outbound(target_iri, [
            (target_iri, type_pred, type_obj),
        ])

        mock_client.query = AsyncMock(side_effect=[outbound, empty_result()])

        request = AsyncMock()
        request.json = AsyncMock(return_value={"iris": [target_iri]})

        from app.browser.objects import bulk_delete_objects

        with patch("app.browser.objects.require_role", return_value=lambda: mock_user):
            response = await bulk_delete_objects(
                request=request,
                user=mock_user,
                client=mock_client,
                event_store=mock_event_store,
                label_service=mock_label_service,
            )

        operations = mock_event_store.commit.call_args[0][0]
        deletes = operations[0].materialize_deletes

        outbound_triple = (URIRef(target_iri), URIRef(type_pred), URIRef(type_obj))
        assert outbound_triple in deletes, "Outbound triple missing from deletes"

    @pytest.mark.asyncio
    async def test_no_inbound_edges_still_works(
        self, mock_client, mock_event_store, mock_label_service, mock_user
    ):
        """Delete works when there are no inbound edges — only outbound triples collected."""
        target_iri = "http://example.org/data/note-1"
        type_pred = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        type_obj = "http://example.org/ontology/Note"

        outbound = make_sparql_bindings_outbound(target_iri, [
            (target_iri, type_pred, type_obj),
        ])

        # Outbound has triples, inbound is empty
        mock_client.query = AsyncMock(side_effect=[outbound, empty_result()])

        request = AsyncMock()
        request.json = AsyncMock(return_value={"iris": [target_iri]})

        from app.browser.objects import bulk_delete_objects

        with patch("app.browser.objects.require_role", return_value=lambda: mock_user):
            response = await bulk_delete_objects(
                request=request,
                user=mock_user,
                client=mock_client,
                event_store=mock_event_store,
                label_service=mock_label_service,
            )

        operations = mock_event_store.commit.call_args[0][0]
        assert len(operations) == 1
        deletes = operations[0].materialize_deletes
        assert len(deletes) == 1  # Only the outbound triple

    @pytest.mark.asyncio
    async def test_only_inbound_edges_creates_operation(
        self, mock_client, mock_event_store, mock_label_service, mock_user
    ):
        """If an IRI has no outbound triples but has inbound references, those are still cleaned up."""
        target_iri = "http://example.org/data/note-orphan"
        referring_iri = "http://example.org/data/note-2"
        pred = "http://example.org/ontology/mentions"

        inbound = make_sparql_bindings_inbound(target_iri, [
            (referring_iri, pred),
        ])

        # No outbound triples, but inbound exists
        mock_client.query = AsyncMock(side_effect=[empty_result(), inbound])

        request = AsyncMock()
        request.json = AsyncMock(return_value={"iris": [target_iri]})

        from app.browser.objects import bulk_delete_objects

        with patch("app.browser.objects.require_role", return_value=lambda: mock_user):
            response = await bulk_delete_objects(
                request=request,
                user=mock_user,
                client=mock_client,
                event_store=mock_event_store,
                label_service=mock_label_service,
            )

        assert mock_event_store.commit.called
        operations = mock_event_store.commit.call_args[0][0]
        assert len(operations) == 1
        deletes = operations[0].materialize_deletes
        inbound_triple = (URIRef(referring_iri), URIRef(pred), URIRef(target_iri))
        assert inbound_triple in deletes

    @pytest.mark.asyncio
    async def test_inbound_query_failure_logs_and_continues(
        self, mock_client, mock_event_store, mock_label_service, mock_user
    ):
        """If inbound query fails, outbound triples are still deleted (graceful degradation)."""
        target_iri = "http://example.org/data/note-1"
        type_pred = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        type_obj = "http://example.org/ontology/Note"

        outbound = make_sparql_bindings_outbound(target_iri, [
            (target_iri, type_pred, type_obj),
        ])

        # Outbound succeeds, inbound raises
        mock_client.query = AsyncMock(side_effect=[outbound, Exception("SPARQL timeout")])

        request = AsyncMock()
        request.json = AsyncMock(return_value={"iris": [target_iri]})

        from app.browser.objects import bulk_delete_objects

        with patch("app.browser.objects.require_role", return_value=lambda: mock_user):
            response = await bulk_delete_objects(
                request=request,
                user=mock_user,
                client=mock_client,
                event_store=mock_event_store,
                label_service=mock_label_service,
            )

        # Should still commit with the outbound triples
        assert mock_event_store.commit.called
        operations = mock_event_store.commit.call_args[0][0]
        deletes = operations[0].materialize_deletes
        assert len(deletes) == 1  # Only outbound, inbound failed gracefully

    @pytest.mark.asyncio
    async def test_no_triples_at_all_returns_zero_count(
        self, mock_client, mock_event_store, mock_label_service, mock_user
    ):
        """If no outbound or inbound triples exist, deleted_count should be 0."""
        target_iri = "http://example.org/data/note-ghost"

        # Both queries return empty
        mock_client.query = AsyncMock(side_effect=[empty_result(), empty_result()])

        request = AsyncMock()
        request.json = AsyncMock(return_value={"iris": [target_iri]})

        from app.browser.objects import bulk_delete_objects

        with patch("app.browser.objects.require_role", return_value=lambda: mock_user):
            response = await bulk_delete_objects(
                request=request,
                user=mock_user,
                client=mock_client,
                event_store=mock_event_store,
                label_service=mock_label_service,
            )

        assert not mock_event_store.commit.called
        import json
        body = json.loads(response.body.decode())
        assert body["deleted_count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_inbound_edges_all_collected(
        self, mock_client, mock_event_store, mock_label_service, mock_user
    ):
        """Multiple inbound references from different subjects are all collected."""
        target_iri = "http://example.org/data/concept-1"
        ref1 = "http://example.org/data/note-1"
        ref2 = "http://example.org/data/note-2"
        ref3 = "http://example.org/data/note-3"
        pred1 = "http://example.org/ontology/references"
        pred2 = "http://example.org/ontology/mentions"

        outbound = make_sparql_bindings_outbound(target_iri, [
            (target_iri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology/Concept"),
        ])
        inbound = make_sparql_bindings_inbound(target_iri, [
            (ref1, pred1),
            (ref2, pred1),
            (ref3, pred2),
        ])

        mock_client.query = AsyncMock(side_effect=[outbound, inbound])

        request = AsyncMock()
        request.json = AsyncMock(return_value={"iris": [target_iri]})

        from app.browser.objects import bulk_delete_objects

        with patch("app.browser.objects.require_role", return_value=lambda: mock_user):
            response = await bulk_delete_objects(
                request=request,
                user=mock_user,
                client=mock_client,
                event_store=mock_event_store,
                label_service=mock_label_service,
            )

        operations = mock_event_store.commit.call_args[0][0]
        deletes = operations[0].materialize_deletes

        # 1 outbound + 3 inbound = 4 triples
        assert len(deletes) == 4

        # All three inbound references present
        assert (URIRef(ref1), URIRef(pred1), URIRef(target_iri)) in deletes
        assert (URIRef(ref2), URIRef(pred1), URIRef(target_iri)) in deletes
        assert (URIRef(ref3), URIRef(pred2), URIRef(target_iri)) in deletes
