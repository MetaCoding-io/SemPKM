"""Tests for predicate label resolution and helptext extraction.

Verifies that ``ShapesService.get_labels_for_predicates()`` and
``ShapesService.get_helptext_for_predicates()`` correctly extract
human-readable labels and helptext from SHACL property shapes, and
that the ``event_detail()`` route collects predicate IRIs from event data.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, SH, XSD

from app.services.shapes import ShapesService, SEMPKM_EDIT_HELPTEXT


def _build_shapes_graph() -> Graph:
    """Build a small shapes graph with PropertyShapes for testing.

    Includes:
    - dcterms:title: sh:name + editHelpText + sh:description
    - rdfs:comment: sh:name + sh:description (no editHelpText)
    - dcterms:creator: rdfs:label on path node only (no sh:name)
    - schema:dateCreated: sh:name only (no helptext/description)
    """
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

    # PropertyShape for schema:dateCreated — sh:name only (no helptext)
    date_shape = URIRef("urn:test:shape:dateCreated")
    g.add((date_shape, RDF.type, SH.PropertyShape))
    g.add((date_shape, SH.path, URIRef("http://schema.org/dateCreated")))
    g.add((date_shape, SH.name, Literal("Date Created")))

    return g


def _build_shapes_graph_with_inline_props() -> Graph:
    """Build a shapes graph where PropertyShapes are blank nodes via sh:property.

    Ensures the label/helptext methods traverse inline shapes (no rdf:type
    sh:PropertyShape) linked by sh:property from a NodeShape.
    """
    g = Graph()
    ns = URIRef("urn:test:NodeShape1")
    g.add((ns, RDF.type, SH.NodeShape))

    # Inline property shape (blank node, no explicit rdf:type sh:PropertyShape)
    bnode = BNode()
    g.add((ns, SH.property, bnode))
    g.add((bnode, SH.path, URIRef("http://purl.org/dc/terms/title")))
    g.add((bnode, SH.name, Literal("Title")))
    g.add((bnode, SEMPKM_EDIT_HELPTEXT, Literal("Enter a title.")))

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

    @pytest.mark.asyncio
    async def test_resolves_inline_property_shapes(self, shapes_service):
        """Blank-node PropertyShapes linked via sh:property (no rdf:type) are resolved."""
        shapes_service._fetch_shapes_graph = AsyncMock(
            return_value=_build_shapes_graph_with_inline_props()
        )
        result = await shapes_service.get_labels_for_predicates(
            ["http://purl.org/dc/terms/title"]
        )
        assert result == {"http://purl.org/dc/terms/title": "Title"}

    @pytest.mark.asyncio
    async def test_date_created_sh_name_only(self, shapes_service):
        """PropertyShape with sh:name and no helptext still resolves label."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_labels_for_predicates(
            ["http://schema.org/dateCreated"]
        )
        assert result == {"http://schema.org/dateCreated": "Date Created"}


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

    @pytest.mark.asyncio
    async def test_resolves_inline_property_shapes(self, shapes_service):
        """Blank-node PropertyShapes linked via sh:property resolve helptext."""
        shapes_service._fetch_shapes_graph = AsyncMock(
            return_value=_build_shapes_graph_with_inline_props()
        )
        result = await shapes_service.get_helptext_for_predicates(
            ["http://purl.org/dc/terms/title"]
        )
        assert result == {"http://purl.org/dc/terms/title": "Enter a title."}

    @pytest.mark.asyncio
    async def test_date_created_has_no_helptext(self, shapes_service):
        """schema:dateCreated has sh:name but no helptext — excluded from result."""
        shapes_service._fetch_shapes_graph = AsyncMock(return_value=_build_shapes_graph())
        result = await shapes_service.get_helptext_for_predicates(
            ["http://schema.org/dateCreated"]
        )
        assert result == {}


class TestEventDetailPredicateCollection:
    """Verify that event_detail route correctly collects predicate IRIs."""

    def test_collects_from_new_values_and_data_triples(self):
        """Predicate IRIs are gathered from both new_values dict and data_triples list."""
        # Simulate the collection logic from event_detail()
        from app.events.query import EventDetail, EventSummary

        detail = EventDetail(
            summary=EventSummary(
                event_iri="urn:sempkm:event:test",
                timestamp="2025-01-01T00:00:00Z",
                operation_type="object.create",
                affected_iris=["urn:sempkm:object:1"],
            ),
            data_triples=[
                ("urn:sempkm:object:1", "http://purl.org/dc/terms/title", "My Object"),
                ("urn:sempkm:object:1", "http://schema.org/dateCreated", "2025-01-01"),
                ("urn:sempkm:object:1", "http://www.w3.org/2000/01/rdf-schema#comment", "A note"),
            ],
            before_values={},
            new_values={
                "http://purl.org/dc/terms/title": "My Object",
            },
            body_diff=None,
        )

        # Replicate the collection logic from the event_detail route
        pred_iris: list[str] = list(detail.new_values.keys())
        pred_iris.extend(
            p for _, p, _ in detail.data_triples if p not in pred_iris
        )

        assert "http://purl.org/dc/terms/title" in pred_iris
        assert "http://schema.org/dateCreated" in pred_iris
        assert "http://www.w3.org/2000/01/rdf-schema#comment" in pred_iris
        # dcterms:title should appear only once (from new_values, not duplicated from data_triples)
        assert pred_iris.count("http://purl.org/dc/terms/title") == 1
        assert len(pred_iris) == 3

    def test_empty_event_returns_empty_list(self):
        """Event with no data yields empty predicate list."""
        from app.events.query import EventDetail, EventSummary

        detail = EventDetail(
            summary=EventSummary(
                event_iri="urn:sempkm:event:empty",
                timestamp="2025-01-01T00:00:00Z",
                operation_type="object.create",
                affected_iris=[],
            ),
            data_triples=[],
            before_values={},
            new_values={},
            body_diff=None,
        )

        pred_iris: list[str] = list(detail.new_values.keys())
        pred_iris.extend(
            p for _, p, _ in detail.data_triples if p not in pred_iris
        )

        assert pred_iris == []
