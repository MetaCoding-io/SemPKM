"""Tests for OntologyService.get_tbox_graph_data() and the /browser/ontology/tbox/graph-data endpoint.

Verifies:
- Node structure (id, label, source)
- Edge direction (parent→child for dagre TB layout)
- owl:Thing exclusion
- Blank node exclusion
- Source label assignment (gist vs model vs user)
- Error handling: empty arrays on SPARQL failure
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ontology.service import (
    GIST_GRAPH,
    GIST_NS,
    USER_TYPES_GRAPH,
    OntologyService,
    _property_source,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASIC_PKM_NS = "urn:sempkm:model:basic-pkm:"


def _make_service(query_side_effects: list) -> OntologyService:
    """Create an OntologyService with a mock triplestore client."""
    mock_client = MagicMock()
    mock_client.query = AsyncMock(side_effect=query_side_effects)
    return OntologyService(mock_client)


def _models_response(model_ids: list[str] | None = None) -> dict:
    """Build a mock SPARQL response for get_ontology_graph_iris()."""
    if model_ids is None:
        model_ids = ["basic-pkm"]
    return {
        "results": {
            "bindings": [
                {"modelId": {"value": mid}} for mid in model_ids
            ]
        }
    }


def _graph_data_response(bindings: list[dict]) -> dict:
    """Build a mock SPARQL response for get_tbox_graph_data() query."""
    return {"results": {"bindings": bindings}}


# ---------------------------------------------------------------------------
# _property_source unit tests
# ---------------------------------------------------------------------------


class TestPropertySource:
    """Verify source label determination for different IRI patterns."""

    def test_gist_iri(self):
        assert _property_source(f"{GIST_NS}Category") == "gist"

    def test_model_iri(self):
        assert _property_source("urn:sempkm:model:basic-pkm:Task") == "basic-pkm"

    def test_user_iri(self):
        assert _property_source(f"{USER_TYPES_GRAPH}:MyClass-abc12345") == "user"

    def test_other_iri(self):
        assert _property_source("http://example.org/Foo") == "other"


# ---------------------------------------------------------------------------
# get_tbox_graph_data tests
# ---------------------------------------------------------------------------


class TestGetTboxGraphData:
    """Tests for OntologyService.get_tbox_graph_data()."""

    @pytest.mark.asyncio
    async def test_returns_nodes_and_edges(self):
        """Basic case: two classes with a subClassOf edge."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([
                {
                    "class": {"value": f"{GIST_NS}Category"},
                    "label": {"value": "Category"},
                },
                {
                    "class": {"value": f"{BASIC_PKM_NS}Tag"},
                    "label": {"value": "Tag"},
                    "parent": {"value": f"{GIST_NS}Category"},
                },
            ]),
        ])

        result = await svc.get_tbox_graph_data()

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    @pytest.mark.asyncio
    async def test_node_structure(self):
        """Each node has id, label, and source fields."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([
                {
                    "class": {"value": f"{GIST_NS}Category"},
                    "label": {"value": "Category"},
                },
            ]),
        ])

        result = await svc.get_tbox_graph_data()
        node = result["nodes"][0]

        assert node["id"] == f"{GIST_NS}Category"
        assert node["label"] == "Category"
        assert node["source"] == "gist"

    @pytest.mark.asyncio
    async def test_edge_direction_parent_to_child(self):
        """Edges point parent→child (source=parent, target=child)."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([
                {
                    "class": {"value": f"{GIST_NS}Category"},
                    "label": {"value": "Category"},
                },
                {
                    "class": {"value": f"{BASIC_PKM_NS}Tag"},
                    "label": {"value": "Tag"},
                    "parent": {"value": f"{GIST_NS}Category"},
                },
            ]),
        ])

        result = await svc.get_tbox_graph_data()
        edge = result["edges"][0]

        assert edge["source"] == f"{GIST_NS}Category"
        assert edge["target"] == f"{BASIC_PKM_NS}Tag"
        assert edge["label"] == "subClassOf"

    @pytest.mark.asyncio
    async def test_source_labels_correctly_assigned(self):
        """Gist, model, and user classes get correct source labels."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([
                {
                    "class": {"value": f"{GIST_NS}Event"},
                    "label": {"value": "Event"},
                },
                {
                    "class": {"value": f"{BASIC_PKM_NS}Task"},
                    "label": {"value": "Task"},
                    "parent": {"value": f"{GIST_NS}Event"},
                },
                {
                    "class": {"value": f"{USER_TYPES_GRAPH}:CustomThing-abc123"},
                    "label": {"value": "CustomThing"},
                },
            ]),
        ])

        result = await svc.get_tbox_graph_data()

        source_map = {n["id"]: n["source"] for n in result["nodes"]}
        assert source_map[f"{GIST_NS}Event"] == "gist"
        assert source_map[f"{BASIC_PKM_NS}Task"] == "basic-pkm"
        assert source_map[f"{USER_TYPES_GRAPH}:CustomThing-abc123"] == "user"

    @pytest.mark.asyncio
    async def test_deduplicates_nodes_with_multiple_parents(self):
        """A class with two parents appears as one node with two edges."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([
                {
                    "class": {"value": f"{GIST_NS}Parent1"},
                    "label": {"value": "Parent1"},
                },
                {
                    "class": {"value": f"{GIST_NS}Parent2"},
                    "label": {"value": "Parent2"},
                },
                {
                    "class": {"value": f"{BASIC_PKM_NS}Child"},
                    "label": {"value": "Child"},
                    "parent": {"value": f"{GIST_NS}Parent1"},
                },
                {
                    "class": {"value": f"{BASIC_PKM_NS}Child"},
                    "label": {"value": "Child"},
                    "parent": {"value": f"{GIST_NS}Parent2"},
                },
            ]),
        ])

        result = await svc.get_tbox_graph_data()

        # 3 unique nodes, not 4
        assert len(result["nodes"]) == 3
        # 2 edges (one per parent)
        assert len(result["edges"]) == 2
        targets = [e["target"] for e in result["edges"]]
        assert targets.count(f"{BASIC_PKM_NS}Child") == 2

    @pytest.mark.asyncio
    async def test_parent_node_created_if_not_in_bindings(self):
        """If a parent IRI is only referenced by a child, a node is created for it."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([
                {
                    "class": {"value": f"{BASIC_PKM_NS}Child"},
                    "label": {"value": "Child"},
                    "parent": {"value": f"{GIST_NS}UnseenParent"},
                },
            ]),
        ])

        result = await svc.get_tbox_graph_data()

        node_ids = [n["id"] for n in result["nodes"]]
        assert f"{GIST_NS}UnseenParent" in node_ids
        assert f"{BASIC_PKM_NS}Child" in node_ids
        assert len(result["nodes"]) == 2

    @pytest.mark.asyncio
    async def test_empty_result_on_no_classes(self):
        """No classes returns empty nodes and edges."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([]),
        ])

        result = await svc.get_tbox_graph_data()

        assert result["nodes"] == []
        assert result["edges"] == []

    @pytest.mark.asyncio
    async def test_sparql_failure_returns_empty(self):
        """SPARQL error returns empty arrays, not an exception."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=Exception("connection refused"))
        svc = OntologyService(mock_client)

        result = await svc.get_tbox_graph_data()

        assert result == {"nodes": [], "edges": []}

    @pytest.mark.asyncio
    async def test_sparql_query_excludes_owl_thing(self):
        """The SPARQL query contains a FILTER to exclude owl:Thing."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([]),
        ])

        await svc.get_tbox_graph_data()

        # Inspect the second query call (first is get_ontology_graph_iris)
        sparql = svc._client.query.call_args_list[1][0][0]
        assert "owl:Thing" in sparql
        assert "FILTER(?class != owl:Thing)" in sparql

    @pytest.mark.asyncio
    async def test_sparql_query_filters_blank_nodes(self):
        """The SPARQL query filters out blank nodes via isIRI."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([]),
        ])

        await svc.get_tbox_graph_data()

        sparql = svc._client.query.call_args_list[1][0][0]
        assert "isIRI(?class)" in sparql

    @pytest.mark.asyncio
    async def test_sparql_query_uses_all_ontology_graphs(self):
        """The SPARQL query includes FROM clauses for gist + model + user-types."""
        svc = _make_service([
            _models_response(["basic-pkm", "crm"]),
            _graph_data_response([]),
        ])

        await svc.get_tbox_graph_data()

        sparql = svc._client.query.call_args_list[1][0][0]
        assert f"FROM <{GIST_GRAPH}>" in sparql
        assert "FROM <urn:sempkm:model:basic-pkm:ontology>" in sparql
        assert "FROM <urn:sempkm:model:crm:ontology>" in sparql
        assert f"FROM <{USER_TYPES_GRAPH}>" in sparql

    @pytest.mark.asyncio
    async def test_classes_without_parents_are_root_nodes(self):
        """Classes with no rdfs:subClassOf appear as nodes with no incoming edges."""
        svc = _make_service([
            _models_response(),
            _graph_data_response([
                {
                    "class": {"value": f"{GIST_NS}Content"},
                    "label": {"value": "Content"},
                    # No parent binding
                },
            ]),
        ])

        result = await svc.get_tbox_graph_data()

        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["id"] == f"{GIST_NS}Content"
        assert len(result["edges"]) == 0
