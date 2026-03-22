"""Tests for MirrorService and mirror router.

Covers:
- Endpoint allowlist validation
- Triple extraction from SPARQL JSON bindings
- Mirror result storage with provenance
- Clear mirrored data
- Mirror stats
- Router endpoint validation (403 for blocked endpoints)
- Empty binding handling
- Provenance graph IRI format
- Config parsing
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.sparql.mirror import MIRROR_PROV_PREFIX, MirrorResult, MirrorService


# ---------------------------------------------------------------------------
# Config: get_allowed_endpoints parsing
# ---------------------------------------------------------------------------


class TestGetAllowedEndpoints:
    """Test Settings.get_allowed_endpoints() parsing."""

    def test_empty_string(self):
        s = Settings(federation_allowed_endpoints="")
        assert s.get_allowed_endpoints() == []

    def test_whitespace_only(self):
        s = Settings(federation_allowed_endpoints="   ")
        assert s.get_allowed_endpoints() == []

    def test_single_endpoint(self):
        s = Settings(
            federation_allowed_endpoints="https://query.wikidata.org/sparql"
        )
        assert s.get_allowed_endpoints() == [
            "https://query.wikidata.org/sparql"
        ]

    def test_multiple_endpoints(self):
        s = Settings(
            federation_allowed_endpoints="https://query.wikidata.org/sparql,https://dbpedia.org/sparql"
        )
        result = s.get_allowed_endpoints()
        assert len(result) == 2
        assert "https://query.wikidata.org/sparql" in result
        assert "https://dbpedia.org/sparql" in result

    def test_whitespace_around_commas(self):
        s = Settings(
            federation_allowed_endpoints="  https://a.org/sparql , https://b.org/sparql  "
        )
        result = s.get_allowed_endpoints()
        assert result == ["https://a.org/sparql", "https://b.org/sparql"]

    def test_trailing_comma(self):
        s = Settings(
            federation_allowed_endpoints="https://a.org/sparql,"
        )
        result = s.get_allowed_endpoints()
        assert result == ["https://a.org/sparql"]


# ---------------------------------------------------------------------------
# MirrorService: validate_endpoint
# ---------------------------------------------------------------------------


class TestValidateEndpoint:
    """Test MirrorService.validate_endpoint().

    validate_endpoint() now delegates to get_merged_endpoints() which
    returns dicts with ``{url, source, removable}`` shape.
    """

    def _make_service(self):
        client = AsyncMock()
        return MirrorService(client)

    @patch("app.sparql.mirror.get_merged_endpoints")
    def test_allowed_endpoint(self, mock_merged):
        mock_merged.return_value = [
            {"url": "https://query.wikidata.org/sparql", "source": "env", "removable": False},
            {"url": "https://dbpedia.org/sparql", "source": "env", "removable": False},
        ]
        service = self._make_service()
        assert service.validate_endpoint("https://query.wikidata.org/sparql") is True

    @patch("app.sparql.mirror.get_merged_endpoints")
    def test_blocked_endpoint(self, mock_merged):
        mock_merged.return_value = [
            {"url": "https://query.wikidata.org/sparql", "source": "env", "removable": False},
        ]
        service = self._make_service()
        assert service.validate_endpoint("https://evil.com/sparql") is False

    @patch("app.sparql.mirror.get_merged_endpoints")
    def test_empty_allowlist_blocks_all(self, mock_merged):
        mock_merged.return_value = []
        service = self._make_service()
        assert service.validate_endpoint("https://query.wikidata.org/sparql") is False

    @patch("app.sparql.mirror.get_merged_endpoints")
    def test_whitespace_trimmed(self, mock_merged):
        mock_merged.return_value = [
            {"url": "https://query.wikidata.org/sparql", "source": "env", "removable": False},
        ]
        service = self._make_service()
        assert service.validate_endpoint("  https://query.wikidata.org/sparql  ") is True


# ---------------------------------------------------------------------------
# MirrorService: _extract_triples
# ---------------------------------------------------------------------------


class TestExtractTriples:
    """Test triple extraction from SPARQL JSON bindings."""

    def _make_service(self):
        client = AsyncMock()
        return MirrorService(client)

    def test_three_uri_vars(self):
        service = self._make_service()
        bindings = [
            {
                "s": {"type": "uri", "value": "http://example.org/Alice"},
                "p": {"type": "uri", "value": "http://xmlns.com/foaf/0.1/knows"},
                "o": {"type": "uri", "value": "http://example.org/Bob"},
            }
        ]
        result = service._extract_triples(bindings, ["s", "p", "o"])
        assert len(result) == 1
        assert result[0] == (
            "http://example.org/Alice",
            "http://xmlns.com/foaf/0.1/knows",
            "http://example.org/Bob",
        )

    def test_two_uri_vars_uses_see_also(self):
        service = self._make_service()
        bindings = [
            {
                "s": {"type": "uri", "value": "http://example.org/Alice"},
                "o": {"type": "uri", "value": "http://example.org/Bob"},
            }
        ]
        result = service._extract_triples(bindings, ["s", "o"])
        assert len(result) == 1
        assert result[0][1] == "http://www.w3.org/2000/01/rdf-schema#seeAlso"

    def test_literal_values_skipped(self):
        service = self._make_service()
        bindings = [
            {
                "s": {"type": "uri", "value": "http://example.org/Alice"},
                "name": {"type": "literal", "value": "Alice"},
            }
        ]
        result = service._extract_triples(bindings, ["s", "name"])
        assert len(result) == 0

    def test_deduplication(self):
        service = self._make_service()
        bindings = [
            {
                "s": {"type": "uri", "value": "http://example.org/Alice"},
                "p": {"type": "uri", "value": "http://xmlns.com/foaf/0.1/knows"},
                "o": {"type": "uri", "value": "http://example.org/Bob"},
            },
            {
                "s": {"type": "uri", "value": "http://example.org/Alice"},
                "p": {"type": "uri", "value": "http://xmlns.com/foaf/0.1/knows"},
                "o": {"type": "uri", "value": "http://example.org/Bob"},
            },
        ]
        result = service._extract_triples(bindings, ["s", "p", "o"])
        assert len(result) == 1

    def test_empty_bindings(self):
        service = self._make_service()
        result = service._extract_triples([], ["s", "p", "o"])
        assert result == []

    def test_missing_var_in_binding(self):
        service = self._make_service()
        bindings = [
            {
                "s": {"type": "uri", "value": "http://example.org/Alice"},
                # "p" is missing
                "o": {"type": "uri", "value": "http://example.org/Bob"},
            }
        ]
        result = service._extract_triples(bindings, ["s", "p", "o"])
        # Only 2 URIs found → uses seeAlso predicate
        assert len(result) == 1
        assert result[0][1] == "http://www.w3.org/2000/01/rdf-schema#seeAlso"


# ---------------------------------------------------------------------------
# MirrorService: mirror_results
# ---------------------------------------------------------------------------


class TestMirrorResults:
    """Test mirror_results() async method."""

    @pytest.mark.asyncio
    async def test_mirror_with_triples(self):
        client = AsyncMock()
        service = MirrorService(client)

        bindings = [
            {
                "s": {"type": "uri", "value": "http://example.org/Alice"},
                "p": {"type": "uri", "value": "http://xmlns.com/foaf/0.1/knows"},
                "o": {"type": "uri", "value": "http://example.org/Bob"},
            }
        ]
        result = await service.mirror_results(
            bindings, ["s", "p", "o"], "https://query.wikidata.org/sparql"
        )

        assert isinstance(result, MirrorResult)
        assert result.triple_count == 1
        assert result.endpoint == "https://query.wikidata.org/sparql"
        assert result.provenance_graph.startswith(MIRROR_PROV_PREFIX)

        # Verify INSERT DATA was called for triples
        update_calls = client.update.call_args_list
        assert len(update_calls) >= 2  # data insert + provenance insert

        # Data insert should contain the triple
        data_sparql = update_calls[0][0][0]
        assert "urn:sempkm:mirrored" in data_sparql
        assert "http://example.org/Alice" in data_sparql
        assert "http://xmlns.com/foaf/0.1/knows" in data_sparql
        assert "http://example.org/Bob" in data_sparql

    @pytest.mark.asyncio
    async def test_mirror_with_empty_bindings(self):
        client = AsyncMock()
        service = MirrorService(client)

        result = await service.mirror_results(
            [], ["s", "p", "o"], "https://query.wikidata.org/sparql"
        )

        assert result.triple_count == 0
        assert result.provenance_graph.startswith(MIRROR_PROV_PREFIX)
        # Only provenance insert, no data insert
        assert client.update.call_count == 1

    @pytest.mark.asyncio
    async def test_provenance_contains_endpoint_and_timestamp(self):
        client = AsyncMock()
        service = MirrorService(client)

        bindings = [
            {
                "s": {"type": "uri", "value": "http://example.org/A"},
                "p": {"type": "uri", "value": "http://example.org/rel"},
                "o": {"type": "uri", "value": "http://example.org/B"},
            }
        ]
        result = await service.mirror_results(
            bindings, ["s", "p", "o"], "https://query.wikidata.org/sparql"
        )

        # Find the provenance INSERT DATA call
        prov_call = None
        for call in client.update.call_args_list:
            sparql = call[0][0]
            if "prov#wasAttributedTo" in sparql:
                prov_call = sparql
                break

        assert prov_call is not None
        assert "https://query.wikidata.org/sparql" in prov_call
        assert "prov#generatedAtTime" in prov_call
        assert result.provenance_graph in prov_call

    @pytest.mark.asyncio
    async def test_provenance_graph_iri_contains_uuid(self):
        client = AsyncMock()
        service = MirrorService(client)

        result = await service.mirror_results(
            [], ["s"], "https://example.org/sparql"
        )

        # Extract UUID part from provenance graph IRI
        uuid_part = result.provenance_graph.replace(MIRROR_PROV_PREFIX, "")
        # Should be a valid UUID
        parsed = uuid.UUID(uuid_part)
        assert str(parsed) == uuid_part


# ---------------------------------------------------------------------------
# MirrorService: clear_mirrored
# ---------------------------------------------------------------------------


class TestClearMirrored:
    """Test clear_mirrored() async method."""

    @pytest.mark.asyncio
    async def test_clear_calls_clear_graph(self):
        client = AsyncMock()
        # Mock count query
        client.query.return_value = {
            "results": {"bindings": [{"count": {"value": "5"}}]}
        }

        service = MirrorService(client)
        count = await service.clear_mirrored()

        assert count == 5
        # Should have called CLEAR GRAPH for the mirrored graph
        update_calls = [c[0][0] for c in client.update.call_args_list]
        assert any("CLEAR GRAPH <urn:sempkm:mirrored>" in s for s in update_calls)

    @pytest.mark.asyncio
    async def test_clear_removes_provenance_graphs(self):
        client = AsyncMock()
        # First query: count triples
        # Second query: list provenance graphs
        client.query.side_effect = [
            {"results": {"bindings": [{"count": {"value": "3"}}]}},
            {
                "results": {
                    "bindings": [
                        {"g": {"value": f"{MIRROR_PROV_PREFIX}abc-123"}},
                        {"g": {"value": f"{MIRROR_PROV_PREFIX}def-456"}},
                    ]
                }
            },
        ]

        service = MirrorService(client)
        count = await service.clear_mirrored()

        assert count == 3
        # Should clear mirrored graph + 2 provenance graphs
        update_calls = [c[0][0] for c in client.update.call_args_list]
        assert any("CLEAR GRAPH <urn:sempkm:mirrored>" in s for s in update_calls)
        assert any(f"CLEAR GRAPH <{MIRROR_PROV_PREFIX}abc-123>" in s for s in update_calls)
        assert any(f"CLEAR GRAPH <{MIRROR_PROV_PREFIX}def-456>" in s for s in update_calls)


# ---------------------------------------------------------------------------
# MirrorService: get_mirror_stats
# ---------------------------------------------------------------------------


class TestGetMirrorStats:
    """Test get_mirror_stats() async method."""

    @pytest.mark.asyncio
    async def test_stats_returns_count_and_endpoints(self):
        client = AsyncMock()
        client.query.side_effect = [
            # Count query
            {"results": {"bindings": [{"count": {"value": "10"}}]}},
            # Endpoints query
            {
                "results": {
                    "bindings": [
                        {"endpoint": {"value": "https://query.wikidata.org/sparql"}},
                        {"endpoint": {"value": "https://dbpedia.org/sparql"}},
                    ]
                }
            },
        ]

        service = MirrorService(client)
        stats = await service.get_mirror_stats()

        assert stats["triple_count"] == 10
        assert len(stats["source_endpoints"]) == 2
        assert "https://query.wikidata.org/sparql" in stats["source_endpoints"]

    @pytest.mark.asyncio
    async def test_stats_empty(self):
        client = AsyncMock()
        client.query.side_effect = [
            {"results": {"bindings": [{"count": {"value": "0"}}]}},
            {"results": {"bindings": []}},
        ]

        service = MirrorService(client)
        stats = await service.get_mirror_stats()

        assert stats["triple_count"] == 0
        assert stats["source_endpoints"] == []


# ---------------------------------------------------------------------------
# Router: endpoint validation
# ---------------------------------------------------------------------------


class TestMirrorRouter:
    """Test mirror_router endpoints via direct function calls."""

    @pytest.mark.asyncio
    @patch("app.sparql.mirror.get_merged_endpoints")
    async def test_post_mirror_blocked_endpoint(self, mock_merged):
        """Blocked endpoint returns False from validate_endpoint."""
        mock_merged.return_value = [
            {"url": "https://query.wikidata.org/sparql", "source": "env", "removable": False},
        ]

        client = AsyncMock()
        service = MirrorService(client)

        assert not service.validate_endpoint("https://evil.com/sparql")

    @pytest.mark.asyncio
    async def test_list_endpoints(self):
        """GET /endpoints returns allowlist."""
        from app.sparql.mirror_router import list_endpoints

        # Create a mock user
        user = MagicMock()
        user.email = "test@example.com"

        with patch("app.sparql.mirror_router.get_merged_endpoints") as mock_merged:
            mock_merged.return_value = [
                {"url": "https://query.wikidata.org/sparql", "source": "env", "removable": False},
            ]
            result = await list_endpoints(user=user)

        assert result["allowlist_configured"] is True
        assert len(result["endpoints"]) == 1
        assert result["endpoints"][0]["url"] == "https://query.wikidata.org/sparql"

    @pytest.mark.asyncio
    async def test_list_endpoints_empty(self):
        """GET /endpoints with no allowlist configured."""
        from app.sparql.mirror_router import list_endpoints

        user = MagicMock()
        user.email = "test@example.com"

        with patch("app.sparql.mirror_router.get_merged_endpoints") as mock_merged:
            mock_merged.return_value = []
            result = await list_endpoints(user=user)

        assert result["allowlist_configured"] is False
        assert result["endpoints"] == []


# ---------------------------------------------------------------------------
# MirrorResult dataclass
# ---------------------------------------------------------------------------


class TestMirrorResult:
    """Test MirrorResult dataclass."""

    def test_creation(self):
        result = MirrorResult(
            triple_count=5,
            provenance_graph="urn:sempkm:mirror-prov:abc",
            endpoint="https://example.org/sparql",
        )
        assert result.triple_count == 5
        assert result.provenance_graph == "urn:sempkm:mirror-prov:abc"
        assert result.endpoint == "https://example.org/sparql"
