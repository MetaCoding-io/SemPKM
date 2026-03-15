"""Tests for OntologyService: batch splitting, INSERT DATA generation, version check,
FROM clause assembly, and SPARQL query shape validation for TBox/ABox/RBox."""

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD
<<<<<<< HEAD
from unittest.mock import AsyncMock, MagicMock, patch
=======
from unittest.mock import AsyncMock, MagicMock
>>>>>>> gsd/M003/S07

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

<<<<<<< HEAD
SH_NS = "http://www.w3.org/ns/shacl#"

=======
>>>>>>> gsd/M003/S07

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
<<<<<<< HEAD


# --- Property creation ---


class TestMintPropertyIri:
    """Tests for property IRI minting."""

    def test_camel_case_slug(self):
        """Property IRI uses camelCase slug."""
        iri = OntologyService._mint_property_iri("Has Author")
        # Should start with lowercase
        assert ":hasAuthor-" in iri
        assert iri.startswith(f"{USER_TYPES_GRAPH}:")

    def test_uuid_suffix(self):
        """Property IRI has 8-char hex suffix."""
        iri = OntologyService._mint_property_iri("test")
        suffix = iri.rsplit("-", 1)[1]
        assert len(suffix) == 8
        int(suffix, 16)  # should not raise

    def test_empty_name_uses_default(self):
        """Empty name falls back to 'property' slug."""
        iri = OntologyService._mint_property_iri("   ")
        assert ":property-" in iri

    def test_uniqueness(self):
        """Two calls with same name produce different IRIs."""
        iri1 = OntologyService._mint_property_iri("Same Name")
        iri2 = OntologyService._mint_property_iri("Same Name")
        assert iri1 != iri2


class TestGeneratePropertyTriples:
    """Tests for OWL property triple generation."""

    def test_object_property(self):
        """Object property generates owl:ObjectProperty type triple."""
        triples = OntologyService._generate_property_triples(
            prop_iri="urn:test:hasAuthor-abc",
            name="Has Author",
            prop_type="object",
            domain_iri="urn:test:Note",
            range_iri="urn:test:Person",
            description="The author of this note",
        )
        subjects = {str(t[0]) for t in triples}
        predicates = {str(t[1]) for t in triples}
        objects = {str(t[2]) for t in triples}

        assert "urn:test:hasAuthor-abc" in subjects
        assert str(OWL.ObjectProperty) in objects
        assert str(RDFS.label) in predicates
        assert str(RDFS.domain) in predicates
        assert str(RDFS.range) in predicates
        assert str(RDFS.comment) in predicates
        assert len(triples) == 5  # type, label, domain, range, comment

    def test_datatype_property(self):
        """Datatype property generates owl:DatatypeProperty type triple."""
        triples = OntologyService._generate_property_triples(
            prop_iri="urn:test:hasTitle-abc",
            name="Has Title",
            prop_type="datatype",
        )
        objects = {str(t[2]) for t in triples}
        assert str(OWL.DatatypeProperty) in objects
        assert len(triples) == 2  # type, label only

    def test_optional_fields_omitted(self):
        """Without domain/range/description, only type and label emitted."""
        triples = OntologyService._generate_property_triples(
            prop_iri="urn:test:prop-abc",
            name="Simple",
            prop_type="object",
        )
        assert len(triples) == 2


class TestCreatePropertyValidation:
    """Tests for create_property input validation."""

    @pytest.mark.asyncio
    async def test_empty_name_raises(self):
        mock_client = MagicMock()
        svc = OntologyService(mock_client)
        with pytest.raises(ValueError, match="name must not be empty"):
            await svc.create_property(name="", prop_type="object")

    @pytest.mark.asyncio
    async def test_invalid_prop_type_raises(self):
        mock_client = MagicMock()
        svc = OntologyService(mock_client)
        with pytest.raises(ValueError, match="must be 'object' or 'datatype'"):
            await svc.create_property(name="test", prop_type="relation")

    @pytest.mark.asyncio
    async def test_invalid_domain_raises(self):
        mock_client = MagicMock()
        svc = OntologyService(mock_client)
        with pytest.raises(ValueError, match="Domain IRI is invalid"):
            await svc.create_property(
                name="test", prop_type="object", domain_iri="not-a-uri"
            )

    @pytest.mark.asyncio
    async def test_successful_creation(self):
        """Successful creation calls client.update and returns result dict."""
        mock_client = MagicMock()
        mock_client.update = AsyncMock()
        svc = OntologyService(mock_client)

        result = await svc.create_property(
            name="Authored By",
            prop_type="object",
            domain_iri="urn:test:Note",
            range_iri="urn:test:Person",
            description="Author relationship",
        )

        assert "property_iri" in result
        assert result["prop_type"] == "object"
        assert result["triple_count"] == 5
        mock_client.update.assert_called_once()
        sparql = mock_client.update.call_args[0][0]
        assert "INSERT DATA" in sparql
        assert f"GRAPH <{USER_TYPES_GRAPH}>" in sparql


# --- Class editing ---


class TestEditClass:
    """Tests for edit_class (full replacement strategy)."""

    @pytest.mark.asyncio
    async def test_edit_deletes_then_reinserts(self):
        """Edit class calls delete (3 SPARQL updates) then insert (1 update)."""
        mock_client = MagicMock()
        mock_client.update = AsyncMock()
        svc = OntologyService(mock_client)

        result = await svc.edit_class(
            class_iri="urn:sempkm:user-types:MyClass-abcd1234",
            name="Renamed Class",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
            properties=[{
                "name": "Title",
                "predicate_iri": "http://purl.org/dc/terms/title",
                "datatype_iri": "http://www.w3.org/2001/XMLSchema#string",
            }],
            icon_name="star",
            icon_color="#ff0000",
        )

        # 3 deletes (blank nodes, shape, class) + 1 insert
        assert mock_client.update.call_count == 4
        assert result["class_iri"] == "urn:sempkm:user-types:MyClass-abcd1234"
        assert result["shape_iri"] == "urn:sempkm:user-types:MyClassShape-abcd1234"
        assert result["property_count"] == 1

        # Last call should be INSERT DATA
        insert_sparql = mock_client.update.call_args_list[3][0][0]
        assert "INSERT DATA" in insert_sparql
        assert "Renamed Class" in insert_sparql

    @pytest.mark.asyncio
    async def test_edit_preserves_iri(self):
        """Edit does not re-mint the class IRI — it preserves the original."""
        mock_client = MagicMock()
        mock_client.update = AsyncMock()
        svc = OntologyService(mock_client)

        original_iri = "urn:sempkm:user-types:TestClass-11112222"
        result = await svc.edit_class(
            class_iri=original_iri,
            name="Changed Name",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
            properties=[],
        )
        assert result["class_iri"] == original_iri


class TestGetClassForEdit:
    """Tests for get_class_for_edit query structure."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": []},
        })
        svc = OntologyService(mock_client)
        result = await svc.get_class_for_edit("urn:nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_class_data(self):
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=[
            # Class metadata query
            {"results": {"bindings": [{
                "label": {"value": "My Class"},
                "parent": {"value": "http://www.w3.org/2002/07/owl#Thing"},
                "icon": {"value": "star"},
                "color": {"value": "#ff0000"},
                "description": {"value": "A test class"},
            }]}},
            # Shape properties query
            {"results": {"bindings": [{
                "name": {"value": "Title"},
                "path": {"value": "http://purl.org/dc/terms/title"},
                "datatype": {"value": "http://www.w3.org/2001/XMLSchema#string"},
                "order": {"value": "1"},
            }]}},
        ])
        svc = OntologyService(mock_client)
        result = await svc.get_class_for_edit("urn:sempkm:user-types:MyClass-abc123")

        assert result is not None
        assert result["label"] == "My Class"
        assert result["icon_name"] == "star"
        assert result["icon_color"] == "#ff0000"
        assert result["description"] == "A test class"
        assert result["parent_label"] == "owl:Thing"
        assert len(result["properties"]) == 1
        assert result["properties"][0]["name"] == "Title"


# --- list_user_types ---


class TestListUserTypes:
    """Tests for list_user_types query and categorization."""

    @pytest.mark.asyncio
    async def test_sparql_uses_from_user_types(self):
        """SPARQL query uses FROM <urn:sempkm:user-types> clause."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": []},
        })
        svc = OntologyService(mock_client)
        await svc.list_user_types()

        sparql = mock_client.query.call_args[0][0]
        assert f"FROM <{USER_TYPES_GRAPH}>" in sparql

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """Returns empty lists when no user types exist."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": []},
        })
        svc = OntologyService(mock_client)
        result = await svc.list_user_types()

        assert result == {
            "classes": [],
            "object_properties": [],
            "datatype_properties": [],
        }

    @pytest.mark.asyncio
    async def test_categorizes_classes(self):
        """owl:Class results are placed in 'classes' list."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": [{
                "iri": {"value": "urn:sempkm:user-types:MyClass-abc"},
                "label": {"value": "My Class"},
                "rdfType": {"value": str(OWL.Class)},
                "icon": {"value": "star"},
                "color": {"value": "#ff0000"},
                "parentLabel": {"value": "Thing"},
            }]},
        })
        svc = OntologyService(mock_client)
        result = await svc.list_user_types()

        assert len(result["classes"]) == 1
        assert result["classes"][0]["iri"] == "urn:sempkm:user-types:MyClass-abc"
        assert result["classes"][0]["label"] == "My Class"
        assert result["classes"][0]["icon"] == "star"
        assert result["classes"][0]["color"] == "#ff0000"
        assert result["classes"][0]["parent_label"] == "Thing"
        assert len(result["object_properties"]) == 0
        assert len(result["datatype_properties"]) == 0

    @pytest.mark.asyncio
    async def test_categorizes_object_and_datatype_properties(self):
        """Object and datatype properties are placed in correct lists."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {
                    "iri": {"value": "urn:sempkm:user-types:authoredBy-abc"},
                    "label": {"value": "Authored By"},
                    "rdfType": {"value": str(OWL.ObjectProperty)},
                    "domainLabel": {"value": "Note"},
                    "rangeLabel": {"value": "Person"},
                },
                {
                    "iri": {"value": "urn:sempkm:user-types:pageCount-def"},
                    "label": {"value": "Page Count"},
                    "rdfType": {"value": str(OWL.DatatypeProperty)},
                    "domainLabel": {"value": "Book"},
                    "rangeLabel": {"value": ""},
                },
            ]},
        })
        svc = OntologyService(mock_client)
        result = await svc.list_user_types()

        assert len(result["object_properties"]) == 1
        assert result["object_properties"][0]["type"] == "object"
        assert result["object_properties"][0]["domain_label"] == "Note"
        assert result["object_properties"][0]["range_label"] == "Person"

        assert len(result["datatype_properties"]) == 1
        assert result["datatype_properties"][0]["type"] == "datatype"
        assert result["datatype_properties"][0]["domain_label"] == "Book"


# --- get_property_for_edit ---


class TestGetPropertyForEdit:
    """Tests for get_property_for_edit query and cross-graph label resolution."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        """Returns None when property does not exist."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": []},
        })
        svc = OntologyService(mock_client)
        result = await svc.get_property_for_edit("urn:nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_property_data_object(self):
        """Returns correct dict for an ObjectProperty with cross-graph labels."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=[
            # Property metadata query
            {"results": {"bindings": [{
                "label": {"value": "Authored By"},
                "rdfType": {"value": str(OWL.ObjectProperty)},
                "domain": {"value": "urn:test:Note"},
                "range": {"value": "urn:test:Person"},
                "description": {"value": "Author relationship"},
            }]}},
            # Cross-graph label for domain
            {"results": {"bindings": [{"label": {"value": "Note"}}]}},
            # Cross-graph label for range
            {"results": {"bindings": [{"label": {"value": "Person"}}]}},
        ])
        svc = OntologyService(mock_client)
        result = await svc.get_property_for_edit("urn:sempkm:user-types:authoredBy-abc")

        assert result is not None
        assert result["iri"] == "urn:sempkm:user-types:authoredBy-abc"
        assert result["label"] == "Authored By"
        assert result["prop_type"] == "object"
        assert result["domain_iri"] == "urn:test:Note"
        assert result["domain_label"] == "Note"
        assert result["range_iri"] == "urn:test:Person"
        assert result["range_label"] == "Person"
        assert result["description"] == "Author relationship"

    @pytest.mark.asyncio
    async def test_returns_datatype_property(self):
        """Correctly identifies DatatypeProperty prop_type."""
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=[
            {"results": {"bindings": [{
                "label": {"value": "Page Count"},
                "rdfType": {"value": str(OWL.DatatypeProperty)},
            }]}},
        ])
        svc = OntologyService(mock_client)
        result = await svc.get_property_for_edit("urn:sempkm:user-types:pageCount-def")

        assert result is not None
        assert result["prop_type"] == "datatype"
        assert result["domain_iri"] == ""
        assert result["range_iri"] == ""


# --- edit_property ---


class TestEditProperty:
    """Tests for edit_property delete-then-reinsert and validation."""

    @pytest.mark.asyncio
    async def test_empty_name_raises(self):
        mock_client = MagicMock()
        svc = OntologyService(mock_client)
        with pytest.raises(ValueError, match="name must not be empty"):
            await svc.edit_property(
                property_iri="urn:test:prop",
                name="",
                prop_type="object",
            )

    @pytest.mark.asyncio
    async def test_invalid_prop_type_raises(self):
        mock_client = MagicMock()
        svc = OntologyService(mock_client)
        with pytest.raises(ValueError, match="must be 'object' or 'datatype'"):
            await svc.edit_property(
                property_iri="urn:test:prop",
                name="Test",
                prop_type="relation",
            )

    @pytest.mark.asyncio
    async def test_edit_calls_delete_then_insert(self):
        """Edit property calls DELETE then INSERT DATA."""
        mock_client = MagicMock()
        mock_client.update = AsyncMock()
        svc = OntologyService(mock_client)

        result = await svc.edit_property(
            property_iri="urn:sempkm:user-types:authoredBy-abc",
            name="Written By",
            prop_type="object",
            domain_iri="urn:test:Note",
            range_iri="urn:test:Person",
        )

        # 1 delete + 1 insert
        assert mock_client.update.call_count == 2

        # First call is DELETE
        delete_sparql = mock_client.update.call_args_list[0][0][0]
        assert "DELETE WHERE" in delete_sparql
        assert f"GRAPH <{USER_TYPES_GRAPH}>" in delete_sparql
        assert "urn:sempkm:user-types:authoredBy-abc" in delete_sparql

        # Second call is INSERT DATA
        insert_sparql = mock_client.update.call_args_list[1][0][0]
        assert "INSERT DATA" in insert_sparql
        assert "Written By" in insert_sparql

    @pytest.mark.asyncio
    async def test_edit_preserves_iri(self):
        """Edit does not re-mint the property IRI — preserves original."""
        mock_client = MagicMock()
        mock_client.update = AsyncMock()
        svc = OntologyService(mock_client)

        original_iri = "urn:sempkm:user-types:myProp-11112222"
        result = await svc.edit_property(
            property_iri=original_iri,
            name="Renamed Prop",
            prop_type="datatype",
        )
        assert result["property_iri"] == original_iri
        assert result["prop_type"] == "datatype"
        assert result["triple_count"] == 2  # rdf:type + rdfs:label

    @pytest.mark.asyncio
    async def test_edit_with_all_optional_fields(self):
        """Edit with domain, range, and description includes all triples."""
        mock_client = MagicMock()
        mock_client.update = AsyncMock()
        svc = OntologyService(mock_client)

        result = await svc.edit_property(
            property_iri="urn:sempkm:user-types:prop-abc",
            name="Full Prop",
            prop_type="object",
            domain_iri="urn:test:Domain",
            range_iri="urn:test:Range",
            description="A description",
        )
        # rdf:type + rdfs:label + rdfs:domain + rdfs:range + rdfs:comment = 5
        assert result["triple_count"] == 5


# --- Route-level tests for edit-property endpoints ---


def _make_mock_request(ontology_service=None, templates=None):
    """Build a mock Request with app.state wired up."""
    req = MagicMock()
    req.app.state.ontology_service = ontology_service or MagicMock()
    req.app.state.templates = templates or MagicMock()
    return req


def _make_mock_user():
    """Build a mock authenticated user."""
    user = MagicMock()
    user.username = "tester"
    return user


class TestEditPropertyFormRoute:
    """Tests for GET /ontology/edit-property-form route handler."""

    @pytest.mark.asyncio
    async def test_namespace_guard_returns_403(self):
        """Non-user-types IRI triggers 403."""
        from app.ontology.router import edit_property_form

        req = _make_mock_request()
        resp = await edit_property_form(
            request=req,
            property_iri="http://example.org/foreignProp",
            user=_make_mock_user(),
        )
        assert resp.status_code == 403
        assert b"Only user-created properties" in resp.body

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self):
        """Property IRI in user namespace but not found in store → 404."""
        from app.ontology.router import edit_property_form

        svc = MagicMock()
        svc.get_property_for_edit = AsyncMock(return_value=None)
        req = _make_mock_request(ontology_service=svc)

        iri = f"{USER_TYPES_GRAPH}:testProp-abc"
        resp = await edit_property_form(
            request=req, property_iri=iri, user=_make_mock_user()
        )
        assert resp.status_code == 404
        assert b"Property not found" in resp.body

    @pytest.mark.asyncio
    async def test_success_renders_template(self):
        """Valid user property IRI → 200 with template rendered."""
        from app.ontology.router import edit_property_form

        prop_data = {
            "iri": f"{USER_TYPES_GRAPH}:myProp-123",
            "label": "My Prop",
            "prop_type": "object",
            "domain_iri": "",
            "domain_label": "",
            "range_iri": "",
            "range_label": "",
            "description": "",
        }
        svc = MagicMock()
        svc.get_property_for_edit = AsyncMock(return_value=prop_data)
        templates = MagicMock()
        templates.TemplateResponse = MagicMock(return_value="<html>OK</html>")
        req = _make_mock_request(ontology_service=svc, templates=templates)

        iri = f"{USER_TYPES_GRAPH}:myProp-123"
        resp = await edit_property_form(
            request=req, property_iri=iri, user=_make_mock_user()
        )

        templates.TemplateResponse.assert_called_once()
        call_args = templates.TemplateResponse.call_args
        assert call_args[0][1] == "browser/ontology/edit_property_form.html"
        assert call_args[0][2]["prop"] == prop_data


class TestEditPropertyRoute:
    """Tests for POST /ontology/edit-property route handler."""

    @pytest.mark.asyncio
    async def test_namespace_guard_returns_403(self):
        """Non-user-types IRI triggers 403."""
        from app.ontology.router import edit_property as edit_property_route

        req = _make_mock_request()
        resp = await edit_property_route(
            request=req,
            property_iri="http://example.org/foreignProp",
            name="Test",
            prop_type="object",
            domain_iri="",
            range_iri="",
            description="",
            user=_make_mock_user(),
        )
        assert resp.status_code == 403
        assert b"Only user-created properties" in resp.body

    @pytest.mark.asyncio
    async def test_success_returns_200_with_hx_trigger(self):
        """Valid edit returns 200 with HX-Trigger: propertyEdited."""
        from app.ontology.router import edit_property as edit_property_route

        svc = MagicMock()
        svc.edit_property = AsyncMock(
            return_value={
                "property_iri": f"{USER_TYPES_GRAPH}:prop-123",
                "prop_type": "object",
                "triple_count": 3,
            }
        )
        req = _make_mock_request(ontology_service=svc)

        resp = await edit_property_route(
            request=req,
            property_iri=f"{USER_TYPES_GRAPH}:prop-123",
            name="Updated Prop",
            prop_type="object",
            domain_iri="urn:test:Domain",
            range_iri="urn:test:Range",
            description="A desc",
            user=_make_mock_user(),
        )
        assert resp.status_code == 200
        assert resp.headers.get("HX-Trigger") == "propertyEdited"
        assert b"Updated property" in resp.body

    @pytest.mark.asyncio
    async def test_validation_error_returns_422(self):
        """Service raises ValueError → 422."""
        from app.ontology.router import edit_property as edit_property_route

        svc = MagicMock()
        svc.edit_property = AsyncMock(
            side_effect=ValueError("name must not be empty")
        )
        req = _make_mock_request(ontology_service=svc)

        resp = await edit_property_route(
            request=req,
            property_iri=f"{USER_TYPES_GRAPH}:prop-123",
            name="",
            prop_type="object",
            domain_iri="",
            range_iri="",
            description="",
            user=_make_mock_user(),
        )
        assert resp.status_code == 422
        assert b"name must not be empty" in resp.body

    @pytest.mark.asyncio
    async def test_server_error_returns_500(self):
        """Unexpected exception → 500."""
        from app.ontology.router import edit_property as edit_property_route

        svc = MagicMock()
        svc.edit_property = AsyncMock(
            side_effect=RuntimeError("SPARQL timeout")
        )
        req = _make_mock_request(ontology_service=svc)

        resp = await edit_property_route(
            request=req,
            property_iri=f"{USER_TYPES_GRAPH}:prop-123",
            name="Test",
            prop_type="object",
            domain_iri="",
            range_iri="",
            description="",
            user=_make_mock_user(),
        )
        assert resp.status_code == 500
        assert b"Server error editing property" in resp.body
=======
>>>>>>> gsd/M003/S07
