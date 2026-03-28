"""Tests for federation SHA-256 integrity hash and namespace filtering.

Covers:
- Export includes content_hash
- Import with correct hash passes
- Import with wrong hash fails
- Import with missing hash logs warning but proceeds
- Namespace filter rejects sempkm: predicates
- Namespace filter rejects owl:Class triples
- Namespace filter rejects sh: predicates
- Namespace filter allows normal data triples
- Namespace filter allows urn:sempkm:shared: graph IRIs in subjects
"""

import hashlib
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rdflib import Literal, URIRef

from app.federation.namespace_filter import filter_federation_triples
from app.federation.patch import serialize_patch
from app.federation.schemas import PatchExportResponse
from app.events.store import Operation


# ---------------------------------------------------------------------------
# Helper: build a minimal mock for FederationService.sync_shared_graph
# ---------------------------------------------------------------------------


def _make_service():
    """Create a FederationService with mocked client and event_store."""
    from app.federation.service import FederationService

    client = AsyncMock()
    event_store = AsyncMock()
    svc = FederationService(client, event_store)
    return svc, client, event_store


def _mock_patch_text():
    """Generate a small RDF Patch and its SHA-256 hash."""
    op = Operation(
        operation_type="test",
        affected_iris=["urn:test:1"],
        description="test op",
        data_triples=[],
        materialize_inserts=[
            (URIRef("urn:test:1"), URIRef("http://purl.org/dc/terms/title"), Literal("Hello")),
        ],
        materialize_deletes=[],
    )
    graph_iri = "urn:sempkm:shared:abc123"
    patch_text = serialize_patch([op], graph_iri)
    content_hash = hashlib.sha256(patch_text.encode("utf-8")).hexdigest()
    return patch_text, content_hash, graph_iri


# ===================================================================
# A. Export includes content_hash
# ===================================================================


class TestExportContentHash:
    """Tests for SHA-256 hash in PatchExportResponse."""

    def test_export_includes_content_hash(self):
        """PatchExportResponse accepts and returns content_hash."""
        resp = PatchExportResponse(
            patch_text="A <urn:s> <urn:p> <urn:o> <urn:g> .\n",
            event_count=1,
            since="2024-01-01T00:00:00Z",
            graph_iri="urn:sempkm:shared:test",
            content_hash="abc123hash",
        )
        assert resp.content_hash == "abc123hash"

    def test_export_hash_matches_content(self):
        """The hash should match SHA-256 of patch_text."""
        patch_text, expected_hash, graph_iri = _mock_patch_text()
        resp = PatchExportResponse(
            patch_text=patch_text,
            event_count=1,
            since="2024-01-01T00:00:00Z",
            graph_iri=graph_iri,
            content_hash=expected_hash,
        )
        computed = hashlib.sha256(resp.patch_text.encode("utf-8")).hexdigest()
        assert computed == resp.content_hash

    def test_export_content_hash_optional(self):
        """content_hash defaults to None for backward compat."""
        resp = PatchExportResponse(
            patch_text="",
            event_count=0,
            since="2024-01-01T00:00:00Z",
            graph_iri="urn:sempkm:shared:test",
        )
        assert resp.content_hash is None


# ===================================================================
# B. Import with correct hash passes
# ===================================================================


class TestSyncHashVerification:
    """Tests for hash verification in sync_shared_graph."""

    @pytest.mark.asyncio
    async def test_import_correct_hash_passes(self):
        """Sync with matching content_hash should apply patches."""
        svc, client, event_store = _make_service()
        patch_text, content_hash, graph_iri = _mock_patch_text()

        # Mock _get_last_sync → None (first sync)
        client.query = AsyncMock(return_value={"results": {"bindings": []}})
        client.update = AsyncMock()

        # Mock HTTP response with correct hash
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "patch_text": patch_text,
            "event_count": 1,
            "content_hash": content_hash,
        }

        with patch("app.federation.service.httpx.AsyncClient") as mock_httpx:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_resp)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_instance

            with patch("app.federation.service.validate_outbound_url"):
                result = await svc.sync_shared_graph(
                    graph_iri=graph_iri,
                    remote_instance_url="https://remote.example.com",
                    local_webid="urn:sempkm:user:local",
                )

        # Should have applied — event_store.commit called
        assert event_store.commit.called
        assert result.errors == [] or all("Failed" not in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_import_wrong_hash_fails(self):
        """Sync with mismatching content_hash should fail without applying."""
        svc, client, event_store = _make_service()
        patch_text, _, graph_iri = _mock_patch_text()

        client.query = AsyncMock(return_value={"results": {"bindings": []}})
        client.update = AsyncMock()

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "patch_text": patch_text,
            "event_count": 1,
            "content_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        }

        with patch("app.federation.service.httpx.AsyncClient") as mock_httpx:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_resp)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_instance

            with patch("app.federation.service.validate_outbound_url"):
                result = await svc.sync_shared_graph(
                    graph_iri=graph_iri,
                    remote_instance_url="https://remote.example.com",
                    local_webid="urn:sempkm:user:local",
                )

        # Should NOT have applied
        assert not event_store.commit.called
        assert result.applied == 0
        assert any("Integrity check failed" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_import_missing_hash_logs_warning(self, caplog):
        """Sync without content_hash should log warning and proceed."""
        svc, client, event_store = _make_service()
        patch_text, _, graph_iri = _mock_patch_text()

        client.query = AsyncMock(return_value={"results": {"bindings": []}})
        client.update = AsyncMock()

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "patch_text": patch_text,
            "event_count": 1,
            # No content_hash field
        }

        with patch("app.federation.service.httpx.AsyncClient") as mock_httpx:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_resp)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_instance

            with patch("app.federation.service.validate_outbound_url"):
                with caplog.at_level(logging.WARNING, logger="app.federation.service"):
                    result = await svc.sync_shared_graph(
                        graph_iri=graph_iri,
                        remote_instance_url="https://remote.example.com",
                        local_webid="urn:sempkm:user:local",
                    )

        # Should still apply (backward compat)
        assert event_store.commit.called
        # Should have logged a warning
        assert any("content_hash" in r.message for r in caplog.records)


# ===================================================================
# C. Namespace filter tests
# ===================================================================


class TestNamespaceFilter:
    """Tests for filter_federation_triples()."""

    def test_rejects_sempkm_predicates(self):
        """Triples with urn:sempkm: predicates should be rejected."""
        triples = [
            (
                URIRef("urn:test:1"),
                URIRef("urn:sempkm:internal:someProp"),
                Literal("value"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 0
        assert len(rejected) == 1

    def test_rejects_sempkm_subjects(self):
        """Triples with urn:sempkm: subjects should be rejected."""
        triples = [
            (
                URIRef("urn:sempkm:user:123"),
                URIRef("http://purl.org/dc/terms/title"),
                Literal("Hacker"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 0
        assert len(rejected) == 1

    def test_rejects_owl_class_triples(self):
        """rdf:type owl:Class triples should be rejected."""
        triples = [
            (
                URIRef("urn:test:MaliciousClass"),
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                URIRef("http://www.w3.org/2002/07/owl#Class"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 0
        assert len(rejected) == 1

    def test_rejects_owl_ontology_type(self):
        """rdf:type owl:Ontology triples should be rejected."""
        triples = [
            (
                URIRef("urn:test:evil-ontology"),
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                URIRef("http://www.w3.org/2002/07/owl#Ontology"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 0
        assert len(rejected) == 1

    def test_rejects_shacl_predicates(self):
        """Triples with sh: predicates should be rejected."""
        triples = [
            (
                URIRef("urn:test:shape1"),
                URIRef("http://www.w3.org/ns/shacl#targetClass"),
                URIRef("urn:test:SomeClass"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 0
        assert len(rejected) == 1

    def test_rejects_shacl_nodeshape_type(self):
        """rdf:type sh:NodeShape triples should be rejected."""
        triples = [
            (
                URIRef("urn:test:shape1"),
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                URIRef("http://www.w3.org/ns/shacl#NodeShape"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 0
        assert len(rejected) == 1

    def test_allows_normal_data_triples(self):
        """Normal data triples with non-system namespaces pass through."""
        triples = [
            (
                URIRef("urn:test:obj1"),
                URIRef("http://purl.org/dc/terms/title"),
                Literal("My Document"),
            ),
            (
                URIRef("urn:test:obj1"),
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                URIRef("http://example.org/Document"),
            ),
            (
                URIRef("urn:test:obj1"),
                URIRef("http://xmlns.com/foaf/0.1/name"),
                Literal("Alice"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 3
        assert len(rejected) == 0

    def test_allows_shared_graph_iris_in_subjects(self):
        """urn:sempkm:shared:* subjects should be allowed (federation graph)."""
        triples = [
            (
                URIRef("urn:sempkm:shared:abc123"),
                URIRef("http://purl.org/dc/terms/title"),
                Literal("Shared Graph Title"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 1
        assert len(rejected) == 0

    def test_mixed_triples_split_correctly(self):
        """A mix of allowed and rejected triples splits correctly."""
        triples = [
            # Allowed: normal data
            (URIRef("urn:test:1"), URIRef("http://purl.org/dc/terms/title"), Literal("Good")),
            # Rejected: sempkm predicate
            (URIRef("urn:test:1"), URIRef("urn:sempkm:internal:evil"), Literal("Bad")),
            # Allowed: shared graph subject
            (URIRef("urn:sempkm:shared:x"), URIRef("http://purl.org/dc/terms/title"), Literal("OK")),
            # Rejected: owl:Class type
            (
                URIRef("urn:test:X"),
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                URIRef("http://www.w3.org/2002/07/owl#Class"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 2
        assert len(rejected) == 2

    def test_empty_input(self):
        """Empty triple list should return empty results."""
        allowed, rejected = filter_federation_triples([])
        assert allowed == []
        assert rejected == []

    def test_rejects_owl_object_property_type(self):
        """rdf:type owl:ObjectProperty should be rejected."""
        triples = [
            (
                URIRef("urn:test:prop"),
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                URIRef("http://www.w3.org/2002/07/owl#ObjectProperty"),
            ),
        ]
        allowed, rejected = filter_federation_triples(triples)
        assert len(allowed) == 0
        assert len(rejected) == 1
