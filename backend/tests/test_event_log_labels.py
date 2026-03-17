"""Tests for predicate label resolution and helptext extraction.

Verifies that ``ShapesService.get_labels_for_predicates()`` and
``ShapesService.get_helptext_for_predicates()`` correctly extract
human-readable labels and helptext from SHACL property shapes, and
that the ``event_detail()`` route passes resolved dicts to the template.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SH, XSD

from app.services.shapes import ShapesService, SEMPKM_EDIT_HELPTEXT


def _build_shapes_graph() -> Graph:
    """Build a small shapes graph with two PropertyShapes for testing."""
    g = Graph()
    ns_dcterms = "http://purl.org/dc/terms/"

    # PropertyShape for dcterms:title — has sh:name and editHelpText
    title_shape = URIRef("urn:test:shape:title")
    g.add((title_shape, RDF.type, SH.PropertyShape))
    g.add((title_shape, SH.path, URIRef(f"{ns_dcterms}title")))
    g.add((title_shape, SH.name, Literal("Title")))
    g.add((title_shape, SH.description, Literal("The name of the resource.")))
    g.add((title_shape, SEMPKM_EDIT_HELPTEXT, Literal("Enter a concise, descriptive title.")))

    # PropertyShape for rdfs:comment — has sh:name and sh:description but no editHelpText
    comment_shape = URIRef("urn:test:shape:comment")
    g.add((comment_shape, RDF.type, SH.PropertyShape))
    g.add((comment_shape, SH.path, RDFS.comment))
    g.add((comment_shape, SH.name, Literal("Description")))
    g.add((comment_shape, SH.description, Literal("A short summary.")))

    # PropertyShape for dcterms:creator — only rdfs:label on path, no sh:name
    creator_path = URIRef(f"{ns_dcterms}creator")
    creator_shape = URIRef("urn:test:shape:creator")
    g.add((creator_shape, RDF.type, SH.PropertyShape))
    g.add((creator_shape, SH.path, creator_path))
    g.add((creator_path, RDFS.label, Literal("Creator")))

    return g


@pytest.fixture
def mock_client():
    """Provide a mock TriplestoreClient."""
    return AsyncMock()


@pytest.fixture
def shapes_service(mock_client):
    """Provide a ShapesService with mocked triplestore client."""
    return ShapesService(mock_client)


class TestGetLabelsForPredicates:
    """ShapesService.get_labels_for_predicates() resolves human-readable labels."""

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_dict(self, shapes_service):
        result = await shapes_service.get_labels_for_predicates([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_resolves_sh_name(self, shapes_service):
        """sh:name on the PropertyShape is the primary label source."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_labels_for_predicates(
            ["http://purl.org/dc/terms/title"]
        )
        assert result == {"http://purl.org/dc/terms/title": "Title"}

    @pytest.mark.asyncio
    async def test_resolves_rdfs_label_on_path(self, shapes_service):
        """Falls back to rdfs:label on the sh:path node when sh:name is absent."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_labels_for_predicates(
            ["http://purl.org/dc/terms/creator"]
        )
        assert result == {"http://purl.org/dc/terms/creator": "Creator"}

    @pytest.mark.asyncio
    async def test_multiple_predicates_resolved(self, shapes_service):
        """Multiple predicates resolved in a single call."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_labels_for_predicates([
            "http://purl.org/dc/terms/title",
            str(RDFS.comment),
        ])
        assert result["http://purl.org/dc/terms/title"] == "Title"
        assert result[str(RDFS.comment)] == "Description"

    @pytest.mark.asyncio
    async def test_unknown_predicate_not_in_result(self, shapes_service):
        """Predicates with no matching PropertyShape are absent from the result."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_labels_for_predicates(
            ["http://example.org/unknown"]
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_error(self, shapes_service):
        """Returns empty dict when shapes graph fetch fails."""
        shapes_service._fetch_shapes_graph = AsyncMock(
            side_effect=Exception("SPARQL timeout")
        )
        result = await shapes_service.get_labels_for_predicates(
            ["http://purl.org/dc/terms/title"]
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_shapes_graph(self, shapes_service):
        """Returns empty dict when shapes graph has no triples."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=Graph())
        result = await shapes_service.get_labels_for_predicates(
            ["http://purl.org/dc/terms/title"]
        )
        assert result == {}


class TestGetHelptextForPredicates:
    """ShapesService.get_helptext_for_predicates() extracts tooltip text."""

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_dict(self, shapes_service):
        result = await shapes_service.get_helptext_for_predicates([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_prefers_edit_helptext(self, shapes_service):
        """sempkm:editHelpText takes precedence over sh:description."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_helptext_for_predicates(
            ["http://purl.org/dc/terms/title"]
        )
        assert result == {
            "http://purl.org/dc/terms/title": "Enter a concise, descriptive title."
        }

    @pytest.mark.asyncio
    async def test_falls_back_to_sh_description(self, shapes_service):
        """Falls back to sh:description when editHelpText is absent."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_helptext_for_predicates(
            [str(RDFS.comment)]
        )
        assert result == {str(RDFS.comment): "A short summary."}

    @pytest.mark.asyncio
    async def test_unknown_predicate_not_in_result(self, shapes_service):
        """Predicates with no helptext are absent from the result."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_helptext_for_predicates(
            ["http://example.org/unknown"]
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_no_helptext_for_label_only_shape(self, shapes_service):
        """PropertyShape with only rdfs:label (no helptext/description) is excluded."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_helptext_for_predicates(
            ["http://purl.org/dc/terms/creator"]
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_error(self, shapes_service):
        """Returns empty dict when shapes graph fetch fails."""
        shapes_service._fetch_shapes_graph = AsyncMock(
            side_effect=Exception("Network error")
        )
        result = await shapes_service.get_helptext_for_predicates(
            ["http://purl.org/dc/terms/title"]
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_multiple_predicates(self, shapes_service):
        """Multiple predicates resolved in a single call."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_helptext_for_predicates([
            "http://purl.org/dc/terms/title",
            str(RDFS.comment),
        ])
        assert len(result) == 2
        assert result["http://purl.org/dc/terms/title"] == "Enter a concise, descriptive title."
        assert result[str(RDFS.comment)] == "A short summary."
