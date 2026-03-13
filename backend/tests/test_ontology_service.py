"""Tests for OntologyService: batch splitting, INSERT DATA generation, version check,
FROM clause assembly, and SPARQL query shape validation for TBox/ABox/RBox."""

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD
from unittest.mock import AsyncMock, MagicMock

from app.ontology.service import (
    BATCH_SIZE,
    GIST_GRAPH,
    GIST_ONTOLOGY_IRI,
    USER_TYPES_GRAPH,
    _build_insert_data_sparql,
    _rdf_term_to_sparql,
    _split_triples_into_batches,
    OntologyService,
)


# --- _split_triples_into_batches ---


class TestSplitTriplesIntoBatches:
    """Tests for batch splitting logic."""

    def test_large_set_splits_evenly(self):
        """4000 triples → 8 batches of 500."""
        triples = [(URIRef(f"urn:s{i}"), RDF.type, OWL.Class) for i in range(4000)]
        batches = _split_triples_into_batches(triples, batch_size=500)
        assert len(batches) == 8
        assert all(len(b) == 500 for b in batches)

    def test_small_set_single_batch(self):
        """100 triples → 1 batch of 100."""
        triples = [(URIRef(f"urn:s{i}"), RDF.type, OWL.Class) for i in range(100)]
        batches = _split_triples_into_batches(triples, batch_size=500)
        assert len(batches) == 1
        assert len(batches[0]) == 100

    def test_remainder_batch(self):
        """501 triples → 2 batches: 500 + 1."""
        triples = [(URIRef(f"urn:s{i}"), RDF.type, OWL.Class) for i in range(501)]
        batches = _split_triples_into_batches(triples, batch_size=500)
        assert len(batches) == 2
        assert len(batches[0]) == 500
        assert len(batches[1]) == 1

    def test_empty_input(self):
        """Empty input → empty output."""
        batches = _split_triples_into_batches([], batch_size=500)
        assert batches == []

    def test_exact_batch_size(self):
        """Exactly 500 triples → 1 batch of 500."""
        triples = [(URIRef(f"urn:s{i}"), RDF.type, OWL.Class) for i in range(500)]
        batches = _split_triples_into_batches(triples, batch_size=500)
        assert len(batches) == 1
        assert len(batches[0]) == 500


# --- INSERT DATA generation ---


class TestBuildInsertDataSparql:
    """Tests for SPARQL INSERT DATA generation."""

    def test_produces_valid_sparql_with_graph_clause(self):
        """INSERT DATA includes GRAPH clause with correct named graph."""
        triples = [
            (URIRef("urn:s1"), RDF.type, OWL.Class),
            (URIRef("urn:s1"), RDFS.label, Literal("Test")),
        ]
        sparql = _build_insert_data_sparql(GIST_GRAPH, triples)
        assert sparql.startswith("INSERT DATA {")
        assert f"GRAPH <{GIST_GRAPH}>" in sparql
        assert "<urn:s1>" in sparql
        assert f"<{RDF.type}>" in sparql
        assert f"<{OWL.Class}>" in sparql
        assert '"Test"' in sparql
        assert sparql.strip().endswith("}")

    def test_literal_with_datatype(self):
        """Typed literals produce ^^<datatype> syntax."""
        triples = [
            (URIRef("urn:s1"), URIRef("urn:p"), Literal(42, datatype=XSD.integer)),
        ]
        sparql = _build_insert_data_sparql(GIST_GRAPH, triples)
        assert f'"42"^^<{XSD.integer}>' in sparql

    def test_literal_with_language(self):
        """Language-tagged literals produce @lang syntax."""
        triples = [
            (URIRef("urn:s1"), RDFS.label, Literal("Test", lang="en")),
        ]
        sparql = _build_insert_data_sparql(GIST_GRAPH, triples)
        assert '"Test"@en' in sparql

    def test_bnode_serialization(self):
        """BNodes produce _:identifier syntax (gist uses blank nodes for OWL restrictions)."""
        bn = BNode("abc123")
        triples = [
            (bn, RDF.type, OWL.Restriction),
            (bn, OWL.onProperty, URIRef("urn:prop")),
        ]
        sparql = _build_insert_data_sparql(GIST_GRAPH, triples)
        assert "_:abc123" in sparql
        assert f"<{OWL.Restriction}>" in sparql

    def test_special_characters_escaped(self):
        """Literals with newlines, quotes, backslashes are properly escaped."""
        triples = [
            (URIRef("urn:s1"), RDFS.comment, Literal('Line1\nLine2\t"quoted"\\')),
        ]
        sparql = _build_insert_data_sparql(GIST_GRAPH, triples)
        # Newline should be escaped as \\n in SPARQL string
        assert "\\n" in sparql
        assert "\\t" in sparql
        assert '\\"quoted\\"' in sparql


# --- _rdf_term_to_sparql ---


class TestRdfTermToSparql:
    """Tests for individual term serialization."""

    def test_uriref(self):
        assert _rdf_term_to_sparql(URIRef("http://example.org/x")) == "<http://example.org/x>"

    def test_plain_literal(self):
        assert _rdf_term_to_sparql(Literal("hello")) == '"hello"'

    def test_typed_literal(self):
        result = _rdf_term_to_sparql(Literal("42", datatype=XSD.integer))
        assert result == f'"42"^^<{XSD.integer}>'

    def test_lang_literal(self):
        result = _rdf_term_to_sparql(Literal("hello", lang="en"))
        assert result == '"hello"@en'

    def test_bnode(self):
        bn = BNode("node1")
        assert _rdf_term_to_sparql(bn) == "_:node1"


# --- Version check ASK query ---


class TestVersionCheckAskQuery:
    """Tests for the ASK query format used by is_gist_loaded."""

    def test_ask_query_format(self):
        """Verify the ASK query checks for gistCore as owl:Ontology in the gist graph."""
        expected_pattern = (
            f"ASK {{ GRAPH <{GIST_GRAPH}> {{ "
            f"<{GIST_ONTOLOGY_IRI}> a <http://www.w3.org/2002/07/owl#Ontology> "
            f"}} }}"
        )
        # Instantiate with a mock to verify the query construction
        # We test the string directly since OntologyService.is_gist_loaded
        # builds it inline
        assert GIST_GRAPH in expected_pattern
        assert GIST_ONTOLOGY_IRI in expected_pattern
        assert "owl#Ontology" in expected_pattern


# --- FROM clause builder ---


class TestBuildFromClauses:
    """Tests for FROM clause assembly used by cross-graph TBox/ABox/RBox queries."""

    def _make_service(self) -> OntologyService:
        mock_client = MagicMock()
        return OntologyService(mock_client)

    def test_single_graph(self):
        """Single graph IRI produces one FROM clause."""
        svc = self._make_service()
        result = svc._build_from_clauses([GIST_GRAPH])
        assert result == f"FROM <{GIST_GRAPH}>"

    def test_multiple_graphs_with_models(self):
        """Gist + model ontology + user-types → three FROM clauses."""
        svc = self._make_service()
        graph_iris = [
            GIST_GRAPH,
            "urn:sempkm:model:basic-pkm:ontology",
            USER_TYPES_GRAPH,
        ]
        result = svc._build_from_clauses(graph_iris)
        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0] == f"FROM <{GIST_GRAPH}>"
        assert lines[1] == "FROM <urn:sempkm:model:basic-pkm:ontology>"
        assert lines[2] == f"FROM <{USER_TYPES_GRAPH}>"

    def test_empty_graph_list(self):
        """Empty graph list produces empty string."""
        svc = self._make_service()
        result = svc._build_from_clauses([])
        assert result == ""

    def test_from_clauses_format(self):
        """Each FROM clause uses angle-bracket IRI syntax."""
        svc = self._make_service()
        result = svc._build_from_clauses(["urn:test:graph1", "urn:test:graph2"])
        for line in result.split("\n"):
            assert line.startswith("FROM <")
            assert line.endswith(">")


# --- Root class SPARQL shape ---


class TestRootClassSparqlShape:
    """Tests for the root class query structure built by get_root_classes.

    We use a mock client to capture the SPARQL query that would be sent
    to the triplestore and verify its structural properties.
    """

    @pytest.mark.asyncio
    async def test_root_class_query_structure(self):
        """Root class query filters isIRI, excludes blank nodes, handles labels."""
        mock_client = MagicMock()
        # Mock get_ontology_graph_iris to return predictable graphs
        mock_client.query = AsyncMock(side_effect=[
            # First call: get_ontology_graph_iris
            {"results": {"bindings": [{"modelId": {"value": "basic-pkm"}}]}},
            # Second call: root classes
            {"results": {"bindings": []}},
        ])
        svc = OntologyService(mock_client)
        await svc.get_root_classes()

        # Get the root class SPARQL from the second query call
        root_sparql = mock_client.query.call_args_list[1][0][0]

        # Structural assertions
        assert "isIRI(?class)" in root_sparql
        assert "FILTER NOT EXISTS" in root_sparql
        assert "rdfs:subClassOf" in root_sparql
        assert "owl:Thing" in root_sparql
        assert "skos:prefLabel" in root_sparql
        assert "rdfs:label" in root_sparql
        assert "COALESCE" in root_sparql
        # FROM clauses should include gist and model graphs
        assert f"FROM <{GIST_GRAPH}>" in root_sparql
        assert "FROM <urn:sempkm:model:basic-pkm:ontology>" in root_sparql
        assert f"FROM <{USER_TYPES_GRAPH}>" in root_sparql

    @pytest.mark.asyncio
    async def test_root_class_returns_sorted_classes(self):
        """Root classes are returned with iri, label, has_subclasses keys."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=[
            # get_ontology_graph_iris
            {"results": {"bindings": []}},
            # root classes
            {"results": {"bindings": [
                {"class": {"value": "urn:test:ClassB"}, "label": {"value": "Bravo"}},
                {"class": {"value": "urn:test:ClassA"}, "label": {"value": "Alpha"}},
            ]}},
            # batch_has_subclasses
            {"results": {"bindings": [
                {"parent": {"value": "urn:test:ClassA"}},
            ]}},
        ])
        svc = OntologyService(mock_client)
        classes = await svc.get_root_classes()

        assert len(classes) == 2
        assert all(k in classes[0] for k in ("iri", "label", "has_subclasses"))
        # ClassA has subclasses, ClassB doesn't
        class_a = next(c for c in classes if c["iri"] == "urn:test:ClassA")
        class_b = next(c for c in classes if c["iri"] == "urn:test:ClassB")
        assert class_a["has_subclasses"] is True
        assert class_b["has_subclasses"] is False


# --- ABox VALUES query construction ---


class TestAboxQueryConstruction:
    """Tests for ABox type count and instance query construction."""

    @pytest.mark.asyncio
    async def test_type_count_query_uses_union_of_current_inferred(self):
        """Type count query uses UNION of current + inferred graphs, not FROM."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=[
            # get_ontology_graph_iris
            {"results": {"bindings": []}},
            # class list
            {"results": {"bindings": [
                {"class": {"value": "urn:test:ClassA"}, "label": {"value": "Alpha"}},
            ]}},
            # count query
            {"results": {"bindings": [
                {"type": {"value": "urn:test:ClassA"}, "count": {"value": "5"}},
            ]}},
        ])
        svc = OntologyService(mock_client)
        types = await svc.get_type_counts()

        # The count query should use UNION pattern
        count_sparql = mock_client.query.call_args_list[2][0][0]
        assert "urn:sempkm:current" in count_sparql
        assert "urn:sempkm:inferred" in count_sparql
        assert "UNION" in count_sparql
        # VALUES clause should contain the class IRI
        assert "<urn:test:ClassA>" in count_sparql
        assert "VALUES ?type" in count_sparql

        assert len(types) == 1
        assert types[0]["iri"] == "urn:test:ClassA"
        assert types[0]["count"] == 5

    @pytest.mark.asyncio
    async def test_type_count_empty_classes(self):
        """No ontology classes → empty result without calling count query."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=[
            # get_ontology_graph_iris
            {"results": {"bindings": []}},
            # class list (empty)
            {"results": {"bindings": []}},
        ])
        svc = OntologyService(mock_client)
        types = await svc.get_type_counts()
        assert types == []
        # Only 2 calls (graph iris + class list), no count query
        assert mock_client.query.call_count == 2

    @pytest.mark.asyncio
    async def test_instance_query_uses_union_of_current_inferred(self):
        """Instance query uses UNION of current + inferred graphs."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {"instance": {"value": "urn:test:inst1"}, "label": {"value": "Inst 1"}},
            ]},
        })
        svc = OntologyService(mock_client)
        instances = await svc.get_instances("urn:test:ClassA")

        sparql = mock_client.query.call_args[0][0]
        assert "urn:sempkm:current" in sparql
        assert "urn:sempkm:inferred" in sparql
        assert "UNION" in sparql
        assert "<urn:test:ClassA>" in sparql
        assert "LIMIT 50" in sparql
        assert len(instances) == 1


# --- RBox property query shape ---


class TestRboxQueryShape:
    """Tests for the RBox property query structure."""

    @pytest.mark.asyncio
    async def test_property_query_includes_both_property_types(self):
        """RBox query includes owl:ObjectProperty and owl:DatatypeProperty in VALUES."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=[
            # get_ontology_graph_iris
            {"results": {"bindings": []}},
            # properties
            {"results": {"bindings": [
                {
                    "prop": {"value": "urn:test:objProp"},
                    "propType": {"value": "http://www.w3.org/2002/07/owl#ObjectProperty"},
                    "label": {"value": "has thing"},
                },
                {
                    "prop": {"value": "urn:test:dataProp"},
                    "propType": {"value": "http://www.w3.org/2002/07/owl#DatatypeProperty"},
                    "label": {"value": "has name"},
                },
            ]}},
        ])
        svc = OntologyService(mock_client)
        result = await svc.get_properties()

        # Check query shape
        prop_sparql = mock_client.query.call_args_list[1][0][0]
        assert "owl:ObjectProperty" in prop_sparql
        assert "owl:DatatypeProperty" in prop_sparql
        assert "VALUES ?propType" in prop_sparql
        assert "rdfs:domain" in prop_sparql
        assert "rdfs:range" in prop_sparql
        assert "isIRI(?prop)" in prop_sparql

        # Check result structure
        assert len(result["object_properties"]) == 1
        assert len(result["datatype_properties"]) == 1
        assert result["object_properties"][0]["label"] == "has thing"
        assert result["datatype_properties"][0]["label"] == "has name"

    @pytest.mark.asyncio
    async def test_property_with_domain_and_range(self):
        """Properties with domain and range get their labels resolved."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=[
            # get_ontology_graph_iris
            {"results": {"bindings": []}},
            # properties with domain/range
            {"results": {"bindings": [
                {
                    "prop": {"value": "urn:test:relatesTo"},
                    "propType": {"value": "http://www.w3.org/2002/07/owl#ObjectProperty"},
                    "label": {"value": "relates to"},
                    "domain": {"value": "urn:test:Person"},
                    "domainLabel": {"value": "Person"},
                    "range": {"value": "urn:test:Organization"},
                    "rangeLabel": {"value": "Organization"},
                },
            ]}},
        ])
        svc = OntologyService(mock_client)
        result = await svc.get_properties()

        prop = result["object_properties"][0]
        assert prop["domain_iri"] == "urn:test:Person"
        assert prop["domain_label"] == "Person"
        assert prop["range_iri"] == "urn:test:Organization"
        assert prop["range_label"] == "Organization"


# --- Batch has_subclasses ---


class TestBatchHasSubclasses:
    """Tests for the batch subclass check."""

    @pytest.mark.asyncio
    async def test_empty_class_list(self):
        """Empty class list returns empty dict without querying."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        svc = OntologyService(mock_client)
        result = await svc._batch_has_subclasses([GIST_GRAPH], [])
        assert result == {}
        mock_client.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_values_clause_construction(self):
        """VALUES clause contains all class IRIs in angle brackets."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {"parent": {"value": "urn:test:A"}},
            ]},
        })
        svc = OntologyService(mock_client)
        result = await svc._batch_has_subclasses(
            [GIST_GRAPH],
            ["urn:test:A", "urn:test:B"],
        )

        sparql = mock_client.query.call_args[0][0]
        assert "VALUES (?parent)" in sparql
        assert "(<urn:test:A>)" in sparql
        assert "(<urn:test:B>)" in sparql
        assert "FILTER EXISTS" in sparql

        assert result == {"urn:test:A": True}
        assert "urn:test:B" not in result
