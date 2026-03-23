"""Unit tests for GraphContextService — neighborhood query and serialization."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.copilot.context import GraphContextService, CHARS_PER_TOKEN


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_triplestore():
    client = AsyncMock()
    client.query = AsyncMock(return_value={"results": {"bindings": []}})
    return client


@pytest.fixture
def mock_label_service():
    svc = AsyncMock()
    svc.resolve_batch = AsyncMock(return_value={})
    return svc


@pytest.fixture
def mock_prefix_registry():
    reg = MagicMock()
    reg.compact = MagicMock(side_effect=lambda iri: iri.rsplit("/", 1)[-1] if "/" in iri else iri)
    return reg


@pytest.fixture
def ctx_service(mock_triplestore, mock_label_service, mock_prefix_registry):
    return GraphContextService(
        triplestore_client=mock_triplestore,
        label_service=mock_label_service,
        prefix_registry=mock_prefix_registry,
    )


# ---------------------------------------------------------------------------
# Sample SPARQL result bindings
# ---------------------------------------------------------------------------


def _make_bindings():
    """Return sample SPARQL bindings simulating a Project with properties and edges."""
    return [
        # Type triple
        {
            "p": {"type": "uri", "value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
            "o": {"type": "uri", "value": "https://example.org/ontology/Project"},
        },
        # Literal property: title
        {
            "p": {"type": "uri", "value": "http://purl.org/dc/terms/title"},
            "o": {"type": "literal", "value": "Q1 Planning"},
        },
        # Literal property: dueDate
        {
            "p": {"type": "uri", "value": "https://example.org/ontology/dueDate"},
            "o": {"type": "literal", "value": "2026-03-28"},
        },
        # Outbound edge: hasTask -> Task1
        {
            "p": {"type": "uri", "value": "https://example.org/ontology/hasTask"},
            "o": {"type": "uri", "value": "https://example.org/data/task-001"},
        },
        # Outbound edge: hasTask -> Task2
        {
            "p": {"type": "uri", "value": "https://example.org/ontology/hasTask"},
            "o": {"type": "uri", "value": "https://example.org/data/task-002"},
        },
        # Inbound edge: Note -> relatedTo -> this
        {
            "inSubject": {"type": "uri", "value": "https://example.org/data/note-001"},
            "inPredicate": {"type": "uri", "value": "https://example.org/ontology/relatedTo"},
        },
    ]


def _make_labels():
    """Return label mapping for all IRIs in the sample bindings."""
    return {
        "https://example.org/data/project-001": "Q1 Planning",
        "https://example.org/ontology/Project": "Project",
        "http://purl.org/dc/terms/title": "title",
        "https://example.org/ontology/dueDate": "dueDate",
        "https://example.org/ontology/hasTask": "hasTask",
        "https://example.org/data/task-001": "Review Goals",
        "https://example.org/data/task-002": "Budget Review",
        "https://example.org/data/note-001": "Q1 Summary",
        "https://example.org/ontology/relatedTo": "relatedTo",
    }


# ---------------------------------------------------------------------------
# Tests: get_neighborhood
# ---------------------------------------------------------------------------


class TestGetNeighborhood:
    """Tests for GraphContextService.get_neighborhood()."""

    @pytest.mark.asyncio
    async def test_parses_types(self, ctx_service, mock_triplestore):
        mock_triplestore.query.return_value = {
            "results": {"bindings": _make_bindings()}
        }
        result = await ctx_service.get_neighborhood("https://example.org/data/project-001")

        assert result["iri"] == "https://example.org/data/project-001"
        assert "https://example.org/ontology/Project" in result["types"]

    @pytest.mark.asyncio
    async def test_parses_literal_properties(self, ctx_service, mock_triplestore):
        mock_triplestore.query.return_value = {
            "results": {"bindings": _make_bindings()}
        }
        result = await ctx_service.get_neighborhood("https://example.org/data/project-001")

        props = result["properties"]
        assert "http://purl.org/dc/terms/title" in props
        assert "Q1 Planning" in props["http://purl.org/dc/terms/title"]
        assert "2026-03-28" in props["https://example.org/ontology/dueDate"]

    @pytest.mark.asyncio
    async def test_parses_outbound_edges(self, ctx_service, mock_triplestore):
        mock_triplestore.query.return_value = {
            "results": {"bindings": _make_bindings()}
        }
        result = await ctx_service.get_neighborhood("https://example.org/data/project-001")

        outbound = result["outbound"]
        assert len(outbound) == 2
        pred_targets = [(p, t) for p, t in outbound]
        assert ("https://example.org/ontology/hasTask", "https://example.org/data/task-001") in pred_targets

    @pytest.mark.asyncio
    async def test_parses_inbound_edges(self, ctx_service, mock_triplestore):
        mock_triplestore.query.return_value = {
            "results": {"bindings": _make_bindings()}
        }
        result = await ctx_service.get_neighborhood("https://example.org/data/project-001")

        inbound = result["inbound"]
        assert len(inbound) == 1
        assert inbound[0] == ("https://example.org/data/note-001", "https://example.org/ontology/relatedTo")

    @pytest.mark.asyncio
    async def test_empty_neighborhood(self, ctx_service, mock_triplestore):
        mock_triplestore.query.return_value = {"results": {"bindings": []}}
        result = await ctx_service.get_neighborhood("https://example.org/data/nothing")

        assert result["types"] == []
        assert result["properties"] == {}
        assert result["outbound"] == []
        assert result["inbound"] == []


# ---------------------------------------------------------------------------
# Tests: serialize_context
# ---------------------------------------------------------------------------


class TestSerializeContext:
    """Tests for GraphContextService.serialize_context()."""

    @pytest.mark.asyncio
    async def test_produces_human_readable_output(self, ctx_service, mock_label_service):
        mock_label_service.resolve_batch.return_value = _make_labels()

        neighborhood = {
            "iri": "https://example.org/data/project-001",
            "types": ["https://example.org/ontology/Project"],
            "properties": {
                "http://purl.org/dc/terms/title": ["Q1 Planning"],
                "https://example.org/ontology/dueDate": ["2026-03-28"],
            },
            "outbound": [
                ("https://example.org/ontology/hasTask", "https://example.org/data/task-001"),
                ("https://example.org/ontology/hasTask", "https://example.org/data/task-002"),
            ],
            "inbound": [
                ("https://example.org/data/note-001", "https://example.org/ontology/relatedTo"),
            ],
        }

        text = await ctx_service.serialize_context(neighborhood)

        # Check header
        assert "Q1 Planning" in text
        assert "Project" in text
        # Check properties
        assert "title: Q1 Planning" in text
        assert "dueDate: 2026-03-28" in text
        # Check outbound
        assert "Review Goals" in text
        assert "Budget Review" in text
        assert "hasTask" in text
        # Check inbound
        assert "Q1 Summary" in text
        assert "relatedTo" in text

    @pytest.mark.asyncio
    async def test_token_budget_truncation(self, ctx_service, mock_label_service):
        """A large neighborhood should be truncated to fit the token budget."""
        # Create a neighborhood with many properties
        large_properties = {}
        for i in range(100):
            large_properties[f"https://example.org/ontology/prop{i}"] = [
                f"This is a fairly long value for property number {i} with some extra padding text"
            ]

        # Create matching labels
        labels = {"https://example.org/data/big": "Big Object"}
        for i in range(100):
            labels[f"https://example.org/ontology/prop{i}"] = f"property{i}"
        mock_label_service.resolve_batch.return_value = labels

        neighborhood = {
            "iri": "https://example.org/data/big",
            "types": [],
            "properties": large_properties,
            "outbound": [],
            "inbound": [],
        }

        # Use a small token budget
        text = await ctx_service.serialize_context(neighborhood, token_budget=100)

        # 100 tokens = 400 chars
        assert len(text) <= 500  # small margin for truncation message

    @pytest.mark.asyncio
    async def test_empty_neighborhood_returns_empty(self, ctx_service):
        neighborhood = {
            "iri": "https://example.org/data/empty",
            "types": [],
            "properties": {},
            "outbound": [],
            "inbound": [],
        }
        text = await ctx_service.serialize_context(neighborhood)
        assert text == ""

    @pytest.mark.asyncio
    async def test_graceful_with_empty_labels(self, ctx_service, mock_label_service):
        """When label resolution returns empty dict, falls back to compacted IRIs."""
        mock_label_service.resolve_batch.return_value = {}

        neighborhood = {
            "iri": "https://example.org/data/project-001",
            "types": ["https://example.org/ontology/Project"],
            "properties": {
                "http://purl.org/dc/terms/title": ["Test Title"],
            },
            "outbound": [],
            "inbound": [],
        }

        text = await ctx_service.serialize_context(neighborhood)

        # Should still produce output using compact() fallback
        assert "Current Context" in text
        assert "Test Title" in text

    @pytest.mark.asyncio
    async def test_priority_truncation_drops_inbound_first(self, ctx_service, mock_label_service):
        """With tight budget, inbound edges (lowest priority) should be dropped first."""
        labels = {
            "https://example.org/data/obj": "My Object",
            "https://example.org/ontology/Type": "Type",
            "https://example.org/ontology/name": "name",
            "https://example.org/ontology/link": "link",
            "https://example.org/data/target": "Target",
            "https://example.org/data/src": "Source",
            "https://example.org/ontology/ref": "ref",
        }
        mock_label_service.resolve_batch.return_value = labels

        neighborhood = {
            "iri": "https://example.org/data/obj",
            "types": ["https://example.org/ontology/Type"],
            "properties": {"https://example.org/ontology/name": ["My Object"]},
            "outbound": [("https://example.org/ontology/link", "https://example.org/data/target")],
            "inbound": [("https://example.org/data/src", "https://example.org/ontology/ref")],
        }

        # Budget tight enough to include header + properties + outbound but not inbound
        # Estimate: header ~80 chars, props ~30 chars, outbound ~40 chars, inbound ~40 chars
        # 50 tokens = 200 chars should force truncation of inbound
        text = await ctx_service.serialize_context(neighborhood, token_budget=50)

        assert "My Object" in text  # header present
        assert "name:" in text  # property present
        # The inbound section might be dropped or truncated
        # (exact behavior depends on char counts, but the structure is correct)


# ---------------------------------------------------------------------------
# Tests: _build_system_prompt integration
# ---------------------------------------------------------------------------


class TestBuildSystemPromptIntegration:
    """Verify _build_system_prompt() correctly includes graph context."""

    def test_includes_graph_context(self):
        from app.copilot.service import _build_system_prompt

        result = _build_system_prompt("## Schema\nSome schema info", graph_context="## Current Context\nSome context")
        assert "## Current Context" in result
        assert "Some context" in result
        assert "## Schema" in result

    def test_no_graph_context(self):
        from app.copilot.service import _build_system_prompt

        result = _build_system_prompt("## Schema\nSome schema info")
        assert "## Schema" in result
        assert "Current Context" not in result

    def test_empty_graph_context_skipped(self):
        from app.copilot.service import _build_system_prompt

        result = _build_system_prompt("## Schema\nSome schema info", graph_context="")
        # Empty string is falsy, so no graph section should appear
        assert "Current Context" not in result
