"""Unit tests verifying that execute_table_query and execute_cards_query
inject PREFIX declarations into reconstructed SPARQL queries.

These tests catch the bug where WHERE bodies use prefixed names (rdf:type,
rdfs:label, dcterms:created, etc.) but the reconstructed count/data/subjects
queries omitted all PREFIX declarations, causing SPARQL parse errors.
"""

import math

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.views.service import ViewSpec, ViewSpecService


# ── Helpers ────────────────────────────────────────────────────

_SAMPLE_SPARQL = """\
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?s ?label ?type ?created ?modified
FROM <urn:sempkm:current>
WHERE {
  ?s rdf:type ?type .
  OPTIONAL { ?s rdfs:label|dcterms:title ?label }
  OPTIONAL { ?s dcterms:created ?created }
  OPTIONAL { ?s dcterms:modified ?modified }
}
"""


def _make_view_spec(
    source_model: str = "model",
    columns: list[str] | None = None,
) -> ViewSpec:
    """Build a minimal ViewSpec with the sample SPARQL query."""
    return ViewSpec(
        spec_iri="urn:test:view-spec",
        target_class="urn:test:TestClass",
        renderer_type="table",
        label="Test Table",
        sparql_query=_SAMPLE_SPARQL,
        columns=columns or ["label", "type", "created", "modified"],
        source_model=source_model,
        sort_default="label",
    )


def _build_service() -> ViewSpecService:
    """Build a ViewSpecService with a mock triplestore client."""
    from app.services.shapes import ShapesService

    shapes = MagicMock(spec=ShapesService)
    shapes.get_form_for_type = AsyncMock(return_value=None)

    client = MagicMock()
    # The query method is async
    client.query = AsyncMock(return_value={"results": {"bindings": []}})

    label_service = MagicMock()
    # resolve_batch is async and returns a dict of IRI->label
    label_service.resolve_batch = AsyncMock(return_value={})

    svc = ViewSpecService(
        client=client,
        label_service=label_service,
        shapes_service=shapes,
    )
    return svc


def _assert_prefixes_present(query: str, msg: str = "") -> None:
    """Assert common PREFIX declarations are present in a query string."""
    prefix = msg + ": " if msg else ""
    assert "PREFIX rdf:" in query, f"{prefix}missing PREFIX rdf: in query"
    assert "PREFIX rdfs:" in query, f"{prefix}missing PREFIX rdfs: in query"
    assert "PREFIX dcterms:" in query, f"{prefix}missing PREFIX dcterms: in query"


# ── execute_table_query tests ──────────────────────────────────


class TestTableQueryPrefixInjection:
    """Verify execute_table_query injects PREFIX declarations."""

    @pytest.mark.asyncio
    async def test_count_query_has_prefixes(self):
        """The count query sent to the triplestore must include PREFIXes."""
        svc = _build_service()
        spec = _make_view_spec()

        # Track what queries are sent
        sent_queries: list[str] = []
        original_query = svc._client.query

        async def capture_query(q):
            sent_queries.append(q)
            return {"results": {"bindings": [{"total": {"value": "0"}}]}}

        svc._client.query = AsyncMock(side_effect=capture_query)

        await svc.execute_table_query(spec)

        # At least 2 queries: count + data
        assert len(sent_queries) >= 2, f"Expected >=2 queries, got {len(sent_queries)}"

        count_query = sent_queries[0]
        _assert_prefixes_present(count_query, "count_query")
        assert "COUNT" in count_query.upper()

    @pytest.mark.asyncio
    async def test_data_query_has_prefixes(self):
        """The data query sent to the triplestore must include PREFIXes."""
        svc = _build_service()
        spec = _make_view_spec()

        sent_queries: list[str] = []

        async def capture_query(q):
            sent_queries.append(q)
            if "COUNT" in q.upper():
                return {"results": {"bindings": [{"total": {"value": "5"}}]}}
            return {"results": {"bindings": []}}

        svc._client.query = AsyncMock(side_effect=capture_query)

        await svc.execute_table_query(spec)

        assert len(sent_queries) >= 2
        data_query = sent_queries[1]
        _assert_prefixes_present(data_query, "data_query")
        assert "LIMIT" in data_query.upper()

    @pytest.mark.asyncio
    async def test_table_returns_rows_when_triplestore_responds(self):
        """execute_table_query returns non-empty rows when the mock returns data."""
        svc = _build_service()
        spec = _make_view_spec()

        async def mock_query(q):
            if "COUNT" in q.upper():
                return {"results": {"bindings": [{"total": {"value": "2"}}]}}
            return {
                "results": {
                    "bindings": [
                        {
                            "s": {"value": "urn:test:obj1"},
                            "label": {"value": "Object One"},
                            "type": {"value": "urn:test:TypeA"},
                            "created": {"value": "2025-01-01"},
                            "modified": {"value": "2025-01-02"},
                        },
                        {
                            "s": {"value": "urn:test:obj2"},
                            "label": {"value": "Object Two"},
                            "type": {"value": "urn:test:TypeB"},
                            "created": {"value": "2025-02-01"},
                            "modified": {"value": "2025-02-02"},
                        },
                    ]
                }
            }

        svc._client.query = AsyncMock(side_effect=mock_query)

        result = await svc.execute_table_query(spec)

        assert result["total"] == 2
        assert len(result["rows"]) == 2
        assert result["rows"][0]["label"] == "Object One"
        assert result["rows"][1]["label"] == "Object Two"


# ── execute_cards_query tests ──────────────────────────────────


class TestCardsQueryPrefixInjection:
    """Verify execute_cards_query injects PREFIX declarations."""

    @pytest.mark.asyncio
    async def test_count_query_has_prefixes(self):
        """The cards count query must include PREFIXes."""
        svc = _build_service()
        spec = _make_view_spec()

        sent_queries: list[str] = []

        async def capture_query(q):
            sent_queries.append(q)
            return {"results": {"bindings": [{"total": {"value": "0"}}]}}

        svc._client.query = AsyncMock(side_effect=capture_query)

        await svc.execute_cards_query(spec)

        # At least 1 query (count); if total==0 no subjects query
        assert len(sent_queries) >= 1
        count_query = sent_queries[0]
        _assert_prefixes_present(count_query, "cards count_query")
        assert "COUNT" in count_query.upper()

    @pytest.mark.asyncio
    async def test_subjects_query_has_prefixes(self):
        """The cards subjects query must include PREFIXes."""
        svc = _build_service()
        spec = _make_view_spec()

        sent_queries: list[str] = []
        _empty = {"results": {"bindings": []}}

        async def capture_query(q):
            sent_queries.append(q)
            if "COUNT" in q.upper():
                return {"results": {"bindings": [{"total": {"value": "3"}}]}}
            if "DISTINCT ?s" in q:
                return {
                    "results": {
                        "bindings": [
                            {"s": {"value": "urn:test:obj1"}},
                        ]
                    }
                }
            # All follow-up queries (props, outbound, inbound, types)
            return _empty

        svc._client.query = AsyncMock(side_effect=capture_query)

        await svc.execute_cards_query(spec)

        # Expect count + subjects + follow-up queries
        assert len(sent_queries) >= 2
        subjects_query = sent_queries[1]
        _assert_prefixes_present(subjects_query, "cards subjects_query")
        assert "DISTINCT ?s" in subjects_query

    @pytest.mark.asyncio
    async def test_cards_returns_results_when_triplestore_responds(self):
        """execute_cards_query returns non-empty cards when mock returns data."""
        svc = _build_service()
        spec = _make_view_spec()

        _empty = {"results": {"bindings": []}}

        async def mock_query(q):
            if "COUNT" in q.upper():
                return {"results": {"bindings": [{"total": {"value": "1"}}]}}
            if "DISTINCT ?s" in q:
                return {
                    "results": {
                        "bindings": [
                            {"s": {"value": "urn:test:obj1"}},
                        ]
                    }
                }
            # props query returns a label
            if "isLiteral" in q:
                return {
                    "results": {
                        "bindings": [
                            {
                                "s": {"value": "urn:test:obj1"},
                                "p": {"value": "http://www.w3.org/2000/01/rdf-schema#label"},
                                "o": {"value": "Card One", "type": "literal"},
                            },
                        ]
                    }
                }
            # All other follow-up queries (outbound, inbound, types)
            return _empty

        svc._client.query = AsyncMock(side_effect=mock_query)

        result = await svc.execute_cards_query(spec)

        assert result["total"] == 1
        assert len(result["cards"]) == 1
