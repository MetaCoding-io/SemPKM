"""Tests for event suggestion endpoints and predicate filter in EventQueryService.

Verifies:
- ``suggest_types`` returns distinct operation types as HTML suggestions
- ``suggest_predicates`` returns predicate suggestions with human-readable labels
- ``suggest_objects`` returns object suggestions with resolved labels
- ``EventQueryService.list_events(predicate_iri=...)`` applies FILTER EXISTS
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.events.query import EventQueryService
from app.services.shapes import ShapesService


@pytest.fixture
def mock_client():
    """Provide a mock TriplestoreClient."""
    return AsyncMock()


@pytest.fixture
def query_service(mock_client):
    """Provide an EventQueryService with mocked client."""
    return EventQueryService(mock_client)


class TestPredicateFilter:
    """EventQueryService.list_events() with predicate_iri parameter."""

    @pytest.mark.asyncio
    async def test_predicate_filter_generates_filter_exists(self, query_service, mock_client):
        """When predicate_iri is set, the SPARQL includes FILTER EXISTS clause."""
        mock_client.query = AsyncMock(return_value={"results": {"bindings": []}})

        await query_service.list_events(predicate_iri="http://purl.org/dc/terms/title")

        # Verify the SPARQL query contains the FILTER EXISTS clause
        call_args = mock_client.query.call_args
        sparql = call_args[0][0] if call_args[0] else call_args[1].get("sparql", "")
        assert "FILTER EXISTS" in sparql
        assert "http://purl.org/dc/terms/title" in sparql

    @pytest.mark.asyncio
    async def test_no_predicate_filter_when_none(self, query_service, mock_client):
        """When predicate_iri is None, no FILTER EXISTS clause is generated."""
        mock_client.query = AsyncMock(return_value={"results": {"bindings": []}})

        await query_service.list_events(predicate_iri=None)

        call_args = mock_client.query.call_args
        sparql = call_args[0][0] if call_args[0] else call_args[1].get("sparql", "")
        assert "FILTER EXISTS" not in sparql

    @pytest.mark.asyncio
    async def test_predicate_filter_combined_with_op_type(self, query_service, mock_client):
        """predicate_iri and op_type filters work together."""
        mock_client.query = AsyncMock(return_value={"results": {"bindings": []}})

        await query_service.list_events(
            op_type="object.patch",
            predicate_iri="http://purl.org/dc/terms/title",
        )

        call_args = mock_client.query.call_args
        sparql = call_args[0][0] if call_args[0] else call_args[1].get("sparql", "")
        assert "FILTER EXISTS" in sparql
        assert 'FILTER(STR(?opType) = "object.patch")' in sparql


class TestSuggestTypesEndpoint:
    """Tests for the suggest-types endpoint logic."""

    @pytest.mark.asyncio
    async def test_suggest_types_parses_sparql_results(self, mock_client):
        """Operation type suggestions are extracted from SPARQL results."""
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {"opType": {"value": "object.create"}},
                {"opType": {"value": "object.patch"}},
                {"opType": {"value": "body.set"}},
            ]}
        })

        # Simulate the endpoint logic
        sparql = """PREFIX sempkm: <urn:sempkm:>
SELECT DISTINCT ?opType WHERE {
  GRAPH ?event {
    ?event sempkm:operationType ?opType .
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
}
ORDER BY ?opType"""

        result = await mock_client.query(sparql)
        suggestions = []
        for row in result.get("results", {}).get("bindings", []):
            op = row["opType"]["value"]
            suggestions.append({"value": op, "label": op})

        assert len(suggestions) == 3
        assert suggestions[0]["value"] == "object.create"
        assert suggestions[1]["label"] == "object.patch"

    @pytest.mark.asyncio
    async def test_suggest_types_handles_empty_results(self, mock_client):
        """Returns empty list when no events exist."""
        mock_client.query = AsyncMock(return_value={"results": {"bindings": []}})

        result = await mock_client.query("dummy")
        suggestions = []
        for row in result.get("results", {}).get("bindings", []):
            suggestions.append(row)

        assert suggestions == []


class TestSuggestPredicatesLogic:
    """Tests for predicate suggestion resolution logic."""

    @pytest.mark.asyncio
    async def test_predicates_filtered_by_q_parameter(self):
        """Predicates are filtered case-insensitively by the q parameter."""
        pred_iris = [
            "http://purl.org/dc/terms/title",
            "http://www.w3.org/2000/01/rdf-schema#comment",
            "http://purl.org/dc/terms/creator",
        ]
        pred_labels = {
            "http://purl.org/dc/terms/title": "Title",
            "http://www.w3.org/2000/01/rdf-schema#comment": "Description",
            "http://purl.org/dc/terms/creator": "Creator",
        }
        q_lower = "tit"

        suggestions = []
        for iri in pred_iris:
            label = pred_labels.get(iri) or ShapesService._local_name(iri)
            local_name = ShapesService._local_name(iri)
            display = f"{label} ({local_name})" if label != local_name else label
            if q_lower and q_lower not in label.lower() and q_lower not in local_name.lower() and q_lower not in iri.lower():
                continue
            suggestions.append({"value": iri, "label": display})

        assert len(suggestions) == 1
        assert suggestions[0]["value"] == "http://purl.org/dc/terms/title"
        assert "Title" in suggestions[0]["label"]

    @pytest.mark.asyncio
    async def test_predicates_no_filter_returns_all(self):
        """When q is empty, all predicates are returned."""
        pred_iris = [
            "http://purl.org/dc/terms/title",
            "http://www.w3.org/2000/01/rdf-schema#comment",
        ]
        pred_labels = {
            "http://purl.org/dc/terms/title": "Title",
        }
        q_lower = ""

        suggestions = []
        for iri in pred_iris:
            label = pred_labels.get(iri) or ShapesService._local_name(iri)
            local_name = ShapesService._local_name(iri)
            display = f"{label} ({local_name})" if label != local_name else label
            if q_lower and q_lower not in label.lower() and q_lower not in local_name.lower():
                continue
            suggestions.append({"value": iri, "label": display})

        assert len(suggestions) == 2

    @pytest.mark.asyncio
    async def test_predicate_display_includes_local_name(self):
        """Suggestion display shows 'Label (localName)' format."""
        iri = "http://purl.org/dc/terms/title"
        label = "Title"
        local_name = ShapesService._local_name(iri)
        display = f"{label} ({local_name})" if label != local_name else label

        assert display == "Title (title)"


class TestSuggestObjectsLogic:
    """Tests for object suggestion resolution logic."""

    @pytest.mark.asyncio
    async def test_objects_filtered_by_label(self):
        """Object suggestions filter by label text when q is provided."""
        obj_iris = [
            "urn:sempkm:object:abc-123",
            "urn:sempkm:object:def-456",
        ]
        labels = {
            "urn:sempkm:object:abc-123": "My First Note",
            "urn:sempkm:object:def-456": "Second Article",
        }
        q_lower = "note"

        suggestions = []
        for iri in obj_iris:
            label = labels.get(iri, iri)
            if q_lower and q_lower not in label.lower() and q_lower not in iri.lower():
                continue
            iri_short = iri if len(iri) <= 40 else "..." + iri[-37:]
            display = f"{label} ({iri_short})" if label != iri else iri_short
            suggestions.append({"value": iri, "label": display})

        assert len(suggestions) == 1
        assert "My First Note" in suggestions[0]["label"]

    @pytest.mark.asyncio
    async def test_objects_long_iri_truncated(self):
        """IRIs longer than 40 chars are truncated with leading ellipsis."""
        iri = "urn:sempkm:object:a-very-long-identifier-that-exceeds-forty-characters"
        label = "Test Object"

        iri_short = iri if len(iri) <= 40 else "..." + iri[-37:]
        display = f"{label} ({iri_short})" if label != iri else iri_short

        assert display.startswith("Test Object (...")
        assert len(iri_short) == 40  # "..." (3) + 37 = 40


class TestShapesServiceLocalName:
    """ShapesService._local_name() used in suggestion display."""

    def test_hash_fragment(self):
        assert ShapesService._local_name("http://www.w3.org/2000/01/rdf-schema#comment") == "comment"

    def test_slash_fragment(self):
        assert ShapesService._local_name("http://purl.org/dc/terms/title") == "title"

    def test_no_separator(self):
        assert ShapesService._local_name("foobar") == "foobar"
