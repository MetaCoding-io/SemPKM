"""Tests for _serialize_rdf_term() from the event store.

Covers TEST-02 (unit test coverage) for RDF term serialization.
"""

import pytest
from rdflib import URIRef, Literal, BNode, Variable
from rdflib.namespace import XSD

from app.events.store import _serialize_rdf_term


class TestSerializeRdfTerm:
    """Tests for _serialize_rdf_term()."""

    def test_uriref_wrapped_in_angle_brackets(self):
        uri = URIRef("http://example.org/resource/1")
        assert _serialize_rdf_term(uri) == "<http://example.org/resource/1>"

    def test_plain_literal(self):
        lit = Literal("hello world")
        assert _serialize_rdf_term(lit) == '"hello world"'

    def test_literal_with_language_tag(self):
        lit = Literal("bonjour", lang="fr")
        assert _serialize_rdf_term(lit) == '"bonjour"@fr'

    def test_literal_with_datatype(self):
        lit = Literal("42", datatype=XSD.integer)
        assert _serialize_rdf_term(lit) == f'"42"^^<{XSD.integer}>'

    def test_literal_escapes_backslash(self):
        lit = Literal("back\\slash")
        assert _serialize_rdf_term(lit) == '"back\\\\slash"'

    def test_literal_escapes_double_quote(self):
        lit = Literal('say "hi"')
        assert _serialize_rdf_term(lit) == '"say \\"hi\\""'

    def test_literal_escapes_newline(self):
        lit = Literal("line1\nline2")
        assert _serialize_rdf_term(lit) == '"line1\\nline2"'

    def test_literal_escapes_carriage_return(self):
        lit = Literal("line1\rline2")
        assert _serialize_rdf_term(lit) == '"line1\\rline2"'

    def test_literal_escapes_tab(self):
        lit = Literal("col1\tcol2")
        assert _serialize_rdf_term(lit) == '"col1\\tcol2"'

    def test_literal_combined_special_chars(self):
        """Multiple special chars in one literal are all escaped."""
        lit = Literal('a\\b"c\nd')
        assert _serialize_rdf_term(lit) == '"a\\\\b\\"c\\nd"'

    def test_bnode_with_explicit_id(self):
        node = BNode("abc123")
        result = _serialize_rdf_term(node)
        assert result.startswith("_:")
        assert "abc123" in result

    def test_variable_prefixed_with_question_mark(self):
        var = Variable("subject")
        assert _serialize_rdf_term(var) == "?subject"

    def test_unsupported_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported RDF term type"):
            _serialize_rdf_term(42)

    def test_literal_with_language_and_special_chars(self):
        """Language-tagged literal with special chars gets both escaping and tag."""
        lit = Literal('say "yes"', lang="en")
        assert _serialize_rdf_term(lit) == '"say \\"yes\\""@en'

    def test_literal_with_datatype_and_special_chars(self):
        """Datatype literal with special chars gets both escaping and datatype."""
        lit = Literal("line1\nline2", datatype=XSD.string)
        assert _serialize_rdf_term(lit) == f'"line1\\nline2"^^<{XSD.string}>'
