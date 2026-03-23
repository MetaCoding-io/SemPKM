"""Unit tests for the RDF import parser: format detection, parsing, subject
extraction, and blank node skolemization."""

from __future__ import annotations

import pytest
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS

from app.rdf_import.parser import (
    detect_format,
    extract_subjects,
    parse_rdf,
    skolemize_bnodes,
)

EX = Namespace("http://example.org/")


# -----------------------------------------------------------------------
# Format detection — text content heuristics
# -----------------------------------------------------------------------


class TestDetectFormat:
    """Tests for detect_format()."""

    def test_detect_format_jsonld_object(self):
        assert detect_format('{"@context": "http://schema.org/"}') == "json-ld"

    def test_detect_format_jsonld_array(self):
        assert detect_format('[{"@id": "http://example.org/1"}]') == "json-ld"

    def test_detect_format_turtle(self):
        content = '@prefix ex: <http://example.org/> .\nex:a a ex:Thing .'
        assert detect_format(content) == "turtle"

    def test_detect_format_turtle_base(self):
        content = '@base <http://example.org/> .\n<a> a <Thing> .'
        assert detect_format(content) == "turtle"

    def test_detect_format_turtle_prefix_uppercase(self):
        content = 'PREFIX ex: <http://example.org/>\nex:a a ex:Thing .'
        assert detect_format(content) == "turtle"

    def test_detect_format_ntriples(self):
        content = '<http://example.org/s> <http://example.org/p> "hello" .\n'
        assert detect_format(content) == "nt"

    def test_detect_format_fallback_turtle(self):
        # Ambiguous content falls back to turtle
        assert detect_format("some random text") == "turtle"

    def test_detect_format_whitespace_stripped(self):
        # Leading whitespace shouldn't break detection
        content = '   \n  {"@context": {}}'
        assert detect_format(content) == "json-ld"


# -----------------------------------------------------------------------
# Format detection — file extension
# -----------------------------------------------------------------------


class TestDetectFormatFileExtension:
    """Tests for detect_format() file extension path."""

    def test_jsonld_extension(self):
        assert detect_format("", filename="data.jsonld") == "json-ld"

    def test_ttl_extension(self):
        assert detect_format("", filename="schema.ttl") == "turtle"

    def test_nt_extension(self):
        assert detect_format("", filename="dump.nt") == "nt"

    def test_json_extension(self):
        # .json files are guessed as json-ld by rdflib
        assert detect_format("", filename="data.json") == "json-ld"


# -----------------------------------------------------------------------
# Format detection — override
# -----------------------------------------------------------------------


class TestDetectFormatOverride:
    """Tests for detect_format() override parameter."""

    def test_override_always_wins(self):
        # Content looks like JSON-LD but override says turtle
        assert detect_format('{"@context": {}}', format_override="turtle") == "turtle"

    def test_override_wins_over_filename(self):
        assert detect_format("", filename="data.jsonld", format_override="nt") == "nt"


# -----------------------------------------------------------------------
# Parsing — valid inputs
# -----------------------------------------------------------------------


VALID_JSONLD = """{
  "@context": {
    "ex": "http://example.org/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
  },
  "@graph": [
    {
      "@id": "ex:alice",
      "@type": "ex:Person",
      "rdfs:label": "Alice"
    },
    {
      "@id": "ex:bob",
      "@type": "ex:Person",
      "rdfs:label": "Bob"
    }
  ]
}"""

VALID_TURTLE = """\
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:proj1 a ex:Project ;
    rdfs:label "Project One" .

ex:proj2 a ex:Project ;
    rdfs:label "Project Two" .
"""

VALID_NTRIPLES = (
    '<http://example.org/x> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
    '<http://example.org/Widget> .\n'
    '<http://example.org/x> <http://www.w3.org/2000/01/rdf-schema#label> "X" .\n'
)


class TestParseValid:
    """Tests for parse_rdf() with valid input."""

    def test_parse_valid_jsonld(self):
        result = parse_rdf(VALID_JSONLD, format="json-ld")
        assert result.errors == []
        assert result.total_triples > 0
        assert result.format_used == "json-ld"
        # Two typed subjects (alice, bob)
        assert len(result.subjects) == 2
        iris = {s.iri for s in result.subjects}
        assert "http://example.org/alice" in iris
        assert "http://example.org/bob" in iris

    def test_parse_valid_turtle(self):
        result = parse_rdf(VALID_TURTLE, format="turtle")
        assert result.errors == []
        assert result.total_triples >= 4  # 2 types + 2 labels
        assert result.format_used == "turtle"
        assert len(result.subjects) == 2

    def test_parse_valid_ntriples(self):
        result = parse_rdf(VALID_NTRIPLES, format="nt")
        assert result.errors == []
        assert result.total_triples == 2
        assert result.format_used == "nt"
        assert len(result.subjects) == 1
        assert result.subjects[0].iri == "http://example.org/x"


# -----------------------------------------------------------------------
# Parsing — invalid input
# -----------------------------------------------------------------------


class TestParseInvalid:
    """Tests for parse_rdf() with malformed input."""

    def test_parse_invalid_returns_errors(self):
        bad_turtle = "@prefix ex: <broken\nex:a a ex:B ."
        result = parse_rdf(bad_turtle, format="turtle")
        assert len(result.errors) > 0
        assert result.subjects == []
        assert result.raw_graph is None
        # Error is a string, not an exception object
        assert isinstance(result.errors[0], str)

    def test_parse_invalid_jsonld(self):
        result = parse_rdf("{not valid json", format="json-ld")
        assert len(result.errors) > 0
        assert result.subjects == []


# -----------------------------------------------------------------------
# Subject extraction
# -----------------------------------------------------------------------


class TestExtractSubjects:
    """Tests for extract_subjects()."""

    def test_types_and_labels(self):
        g = Graph()
        g.add((EX.alice, RDF.type, EX.Person))
        g.add((EX.alice, RDFS.label, Literal("Alice")))
        g.add((EX.alice, EX.age, Literal(30)))

        subjects = extract_subjects(g)
        assert len(subjects) == 1
        s = subjects[0]
        assert s.iri == str(EX.alice)
        assert str(EX.Person) in s.types
        assert s.label == "Alice"
        # type + label + age = 3 predicates
        assert s.property_count == 3
        assert s.is_blank_node is False

    def test_label_precedence_dcterms_title_wins(self):
        """dcterms:title should beat rdfs:label when both are present."""
        g = Graph()
        g.add((EX.item, RDF.type, EX.Thing))
        g.add((EX.item, DCTERMS.title, Literal("DCT Title")))
        g.add((EX.item, RDFS.label, Literal("RDFS Label")))

        subjects = extract_subjects(g)
        assert subjects[0].label == "DCT Title"

    def test_label_qname_fallback(self):
        """When no label predicate exists, the local name part of the IRI is used."""
        g = Graph()
        g.add((EX.myThing, RDF.type, EX.Widget))

        subjects = extract_subjects(g)
        assert subjects[0].label == "myThing"

    def test_top_level_heuristic(self):
        """Nested blank node subjects should be excluded from top-level."""
        g = Graph()
        bnode = BNode()
        g.add((EX.doc, RDF.type, EX.Document))
        g.add((EX.doc, RDFS.label, Literal("My Doc")))
        g.add((EX.doc, EX.author, bnode))  # bnode is referenced as object
        g.add((bnode, RDF.type, EX.Person))
        g.add((bnode, RDFS.label, Literal("Nested Author")))

        subjects = extract_subjects(g)
        # Only EX.doc should be top-level — bnode appears as object of EX.doc
        assert len(subjects) == 1
        assert subjects[0].iri == str(EX.doc)
        assert subjects[0].label == "My Doc"

    def test_top_level_heuristic_fallback_all(self):
        """If all subjects reference each other, show all."""
        g = Graph()
        g.add((EX.a, EX.knows, EX.b))
        g.add((EX.b, EX.knows, EX.a))

        subjects = extract_subjects(g)
        # Both are in object position, so heuristic yields nothing → return all
        assert len(subjects) == 2


# -----------------------------------------------------------------------
# Blank node skolemization
# -----------------------------------------------------------------------


class TestSkolemize:
    """Tests for skolemize_bnodes()."""

    def test_consistency(self):
        """Same BNode used as subject and object should map to the same URI."""
        g = Graph()
        b = BNode()
        g.add((b, RDF.type, EX.Thing))
        g.add((EX.container, EX.child, b))

        new_g, mapping = skolemize_bnodes(g)

        # The mapping should contain exactly one BNode
        assert len(mapping) == 1
        skolem_uri = mapping[b]

        # Find the triple where skolem_uri is subject
        subj_types = list(new_g.objects(skolem_uri, RDF.type))
        assert EX.Thing in subj_types

        # Find the triple where skolem_uri is object
        parents = list(new_g.subjects(EX.child, skolem_uri))
        assert EX.container in parents

    def test_iri_format(self):
        """Skolemized URIs should start with urn:sempkm:import:."""
        g = Graph()
        b = BNode()
        g.add((b, RDF.type, EX.Item))

        _, mapping = skolemize_bnodes(g)
        for uri in mapping.values():
            assert str(uri).startswith("urn:sempkm:import:")

    def test_preserves_non_bnodes(self):
        """Regular URIRefs and Literals should be unchanged."""
        g = Graph()
        g.add((EX.alpha, RDF.type, EX.Widget))
        g.add((EX.alpha, RDFS.label, Literal("Alpha")))

        new_g, mapping = skolemize_bnodes(g)

        assert len(mapping) == 0  # no BNodes to map
        assert (EX.alpha, RDF.type, EX.Widget) in new_g
        assert (EX.alpha, RDFS.label, Literal("Alpha")) in new_g

    def test_preserves_namespace_bindings(self):
        """Namespace bindings should be carried over."""
        g = Graph()
        g.bind("ex", EX)
        g.add((EX.x, RDF.type, EX.Y))

        new_g, _ = skolemize_bnodes(g)
        ns_map = dict(new_g.namespaces())
        assert "ex" in ns_map
        assert str(ns_map["ex"]) == str(EX)

    def test_multiple_bnodes(self):
        """Multiple distinct BNodes should each get unique URIs."""
        g = Graph()
        b1, b2 = BNode(), BNode()
        g.add((b1, RDF.type, EX.A))
        g.add((b2, RDF.type, EX.B))

        _, mapping = skolemize_bnodes(g)
        assert len(mapping) == 2
        uris = list(mapping.values())
        assert str(uris[0]) != str(uris[1])
