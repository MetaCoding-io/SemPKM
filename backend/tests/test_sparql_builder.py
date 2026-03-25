"""Unit tests for the centralised SPARQL builder module.

Covers:
- safe_iri: valid IRIs, malicious payloads, edge cases
- safe_literal: all special characters, datatype/language tags
- sparql_escape_string: consolidated escape function
- values_clause: construction and edge cases
- triple_pattern: variables, IRIs, and mixed
- validate_iri: boolean convenience wrapper
"""

from __future__ import annotations

import pytest

from app.sparql.builder import (
    safe_iri,
    safe_literal,
    sparql_escape_string,
    triple_pattern,
    validate_iri,
    values_clause,
)


# =====================================================================
# safe_iri — valid IRIs
# =====================================================================

class TestSafeIriValid:
    """Test that well-formed IRIs produce correct N3 serialization."""

    def test_http_iri(self):
        assert safe_iri("http://example.org/test") == "<http://example.org/test>"

    def test_https_iri(self):
        assert safe_iri("https://example.org/path/to/resource") == \
            "<https://example.org/path/to/resource>"

    def test_urn_iri(self):
        assert safe_iri("urn:sempkm:model:basic-pkm:Note") == \
            "<urn:sempkm:model:basic-pkm:Note>"

    def test_urn_seed_iri(self):
        assert safe_iri("urn:sempkm:model:basic-pkm:seed-note-arch") == \
            "<urn:sempkm:model:basic-pkm:seed-note-arch>"

    def test_mailto_iri(self):
        assert safe_iri("mailto:user@example.com") == \
            "<mailto:user@example.com>"

    def test_http_with_path_and_fragment(self):
        assert safe_iri("http://example.org/path#fragment") == \
            "<http://example.org/path#fragment>"

    def test_http_with_query_string(self):
        assert safe_iri("http://example.org/path?key=value") == \
            "<http://example.org/path?key=value>"

    def test_strips_surrounding_whitespace(self):
        """Leading/trailing whitespace should be stripped before validation."""
        assert safe_iri("  http://example.org/test  ") == \
            "<http://example.org/test>"


# =====================================================================
# safe_iri — malicious payloads (injection vectors)
# =====================================================================

class TestSafeIriMalicious:
    """Test that SPARQL injection payloads are rejected with ValueError."""

    def test_angle_bracket_breakout(self):
        """F-006 style: closing > then injecting a new triple pattern."""
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/test> . ?s ?p ?o } #")

    def test_comment_injection(self):
        """Payload that tries to break out with angle bracket and comment."""
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("x> . ?s ?p ?o } #")

    def test_newline_injection(self):
        """Newline character that would start a new SPARQL statement."""
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/test\nINSERT DATA { <x> <y> <z> }")

    def test_tab_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/test\there")

    def test_carriage_return_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/test\rhere")

    def test_space_in_iri(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/test here")

    def test_double_quote_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri('http://example.org/test"here')

    def test_backslash_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/test\\here")

    def test_brace_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/{malicious}")

    def test_less_than_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/<evil>")

    def test_null_byte_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/test\x00evil")

    def test_control_char_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://example.org/test\x07bell")


# =====================================================================
# safe_iri — scheme validation
# =====================================================================

class TestSafeIriScheme:
    """Test that non-allowed schemes are rejected."""

    def test_javascript_scheme(self):
        with pytest.raises(ValueError, match="not in allowed set"):
            safe_iri("javascript:alert(1)")

    def test_data_scheme(self):
        """data: URI rejected — may hit forbidden chars or scheme check."""
        with pytest.raises(ValueError):
            safe_iri("data:text/html,<h1>XSS</h1>")

    def test_data_scheme_clean(self):
        """data: URI without angle brackets — pure scheme rejection."""
        with pytest.raises(ValueError, match="not in allowed set"):
            safe_iri("data:text/plain;base64,SGVsbG8=")

    def test_file_scheme(self):
        with pytest.raises(ValueError, match="not in allowed set"):
            safe_iri("file:///etc/passwd")

    def test_ftp_scheme(self):
        with pytest.raises(ValueError, match="not in allowed set"):
            safe_iri("ftp://example.org/file")

    def test_no_scheme(self):
        with pytest.raises(ValueError, match="not in allowed set"):
            safe_iri("no-scheme-at-all")


# =====================================================================
# safe_iri — edge cases
# =====================================================================

class TestSafeIriEdgeCases:
    """Test edge cases and empty/None input."""

    def test_empty_string(self):
        with pytest.raises(ValueError, match="non-empty"):
            safe_iri("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="non-empty"):
            safe_iri("   ")

    def test_none(self):
        with pytest.raises(ValueError, match="non-empty"):
            safe_iri(None)  # type: ignore[arg-type]

    def test_http_without_host(self):
        with pytest.raises(ValueError, match="host component"):
            safe_iri("http:///path-only")

    def test_urn_without_path(self):
        with pytest.raises(ValueError, match="path component"):
            safe_iri("urn:")


# =====================================================================
# safe_literal — basic serialization
# =====================================================================

class TestSafeLiteral:
    """Test N3 serialization of string literals."""

    def test_simple_string(self):
        result = safe_literal("hello world")
        assert result == '"hello world"'

    def test_quotes_escaped(self):
        result = safe_literal('has "quotes"')
        assert '"' not in result[1:-1].replace('\\"', '')  # inner quotes escaped

    def test_newline_handling(self):
        result = safe_literal("line1\nline2")
        # rdflib uses triple-quoting for multiline
        assert "line1" in result
        assert "line2" in result

    def test_backslash_handling(self):
        result = safe_literal("path\\to\\file")
        assert "path" in result

    def test_tab_handling(self):
        result = safe_literal("col1\tcol2")
        assert "col1" in result

    def test_carriage_return_handling(self):
        result = safe_literal("line1\rline2")
        assert "line1" in result

    def test_mixed_special_chars(self):
        """String with all special characters at once."""
        result = safe_literal('a"b\\c\nd\re\tf')
        assert result  # Should produce valid N3

    def test_empty_string(self):
        assert safe_literal("") == '""'

    def test_none_raises(self):
        with pytest.raises(ValueError, match="must not be None"):
            safe_literal(None)  # type: ignore[arg-type]


class TestSafeLiteralTyped:
    """Test datatype and language tag handling."""

    def test_xsd_string_datatype(self):
        result = safe_literal(
            "hello",
            datatype="http://www.w3.org/2001/XMLSchema#string",
        )
        assert "^^" in result
        assert "XMLSchema#string" in result

    def test_xsd_integer_datatype(self):
        result = safe_literal(
            "42",
            datatype="http://www.w3.org/2001/XMLSchema#integer",
        )
        assert "^^" in result

    def test_language_tag(self):
        result = safe_literal("bonjour", lang="fr")
        assert result == '"bonjour"@fr'

    def test_language_tag_en(self):
        result = safe_literal("hello", lang="en")
        assert result == '"hello"@en'


# =====================================================================
# sparql_escape_string — consolidated escape function
# =====================================================================

class TestSparqlEscapeString:
    """Test the consolidated escape function that replaces all 9 scattered ones."""

    def test_backslash(self):
        assert sparql_escape_string("a\\b") == "a\\\\b"

    def test_double_quote(self):
        assert sparql_escape_string('a"b') == 'a\\"b'

    def test_single_quote(self):
        assert sparql_escape_string("a'b") == "a\\'b"

    def test_newline(self):
        assert sparql_escape_string("a\nb") == "a\\nb"

    def test_carriage_return(self):
        assert sparql_escape_string("a\rb") == "a\\rb"

    def test_tab(self):
        assert sparql_escape_string("a\tb") == "a\\tb"

    def test_all_at_once(self):
        """All special characters in one string."""
        result = sparql_escape_string('a\\b"c\'d\ne\rf\tg')
        assert result == 'a\\\\b\\"c\\\'d\\ne\\rf\\tg'

    def test_empty_string(self):
        assert sparql_escape_string("") == ""

    def test_no_special_chars(self):
        assert sparql_escape_string("hello world") == "hello world"

    def test_none_raises(self):
        with pytest.raises(ValueError, match="Cannot escape None"):
            sparql_escape_string(None)  # type: ignore[arg-type]

    def test_unicode_preserved(self):
        assert sparql_escape_string("café") == "café"

    def test_backslash_quote_combo(self):
        """The exact breakout vector from F-010: backslash-then-quote."""
        result = sparql_escape_string('\\"')
        assert result == '\\\\\\"'  # \ becomes \\ then " becomes \"


# =====================================================================
# values_clause
# =====================================================================

class TestValuesClause:
    """Test VALUES clause construction."""

    def test_single_iri(self):
        result = values_clause("type", ["http://example.org/A"])
        assert result == "VALUES (?type) { (<http://example.org/A>) }"

    def test_multiple_iris(self):
        result = values_clause("type", [
            "http://example.org/A",
            "http://example.org/B",
            "http://example.org/C",
        ])
        assert "(<http://example.org/A>)" in result
        assert "(<http://example.org/B>)" in result
        assert "(<http://example.org/C>)" in result
        assert result.startswith("VALUES (?type)")

    def test_var_name_with_question_mark(self):
        """Leading ? on var_name should be handled gracefully."""
        result = values_clause("?type", ["http://example.org/A"])
        assert result == "VALUES (?type) { (<http://example.org/A>) }"

    def test_empty_iris_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            values_clause("type", [])

    def test_empty_var_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            values_clause("", ["http://example.org/A"])

    def test_malicious_iri_in_list_raises(self):
        with pytest.raises(ValueError):
            values_clause("type", [
                "http://example.org/A",
                "http://example.org/B> . ?s ?p ?o } #",
            ])


# =====================================================================
# triple_pattern
# =====================================================================

class TestTriplePattern:
    """Test triple pattern construction."""

    def test_all_variables(self):
        assert triple_pattern("?s", "?p", "?o") == "?s ?p ?o ."

    def test_all_iris(self):
        result = triple_pattern(
            "http://example.org/s",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/Type",
        )
        assert result == (
            "<http://example.org/s> "
            "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> "
            "<http://example.org/Type> ."
        )

    def test_mixed_variables_and_iris(self):
        result = triple_pattern(
            "?s",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "?type",
        )
        assert result == (
            "?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type ."
        )

    def test_dollar_variable(self):
        assert triple_pattern("$s", "$p", "$o") == "$s $p $o ."

    def test_empty_subject_raises(self):
        with pytest.raises(ValueError, match="subject"):
            triple_pattern("", "?p", "?o")

    def test_none_predicate_raises(self):
        with pytest.raises(ValueError, match="predicate"):
            triple_pattern("?s", None, "?o")  # type: ignore[arg-type]

    def test_malicious_iri_object_raises(self):
        with pytest.raises(ValueError):
            triple_pattern(
                "?s",
                "?p",
                "http://example.org/test> . ?s ?p ?o } #",
            )


# =====================================================================
# validate_iri — boolean wrapper
# =====================================================================

class TestValidateIri:
    """Test the boolean convenience wrapper."""

    def test_valid_http(self):
        assert validate_iri("http://example.org/test") is True

    def test_valid_urn(self):
        assert validate_iri("urn:sempkm:model:basic-pkm:Note") is True

    def test_empty(self):
        assert validate_iri("") is False

    def test_injection_payload(self):
        assert validate_iri("http://x> . ?s ?p ?o } #") is False

    def test_javascript_scheme(self):
        assert validate_iri("javascript:alert(1)") is False

    def test_none(self):
        assert validate_iri(None) is False  # type: ignore[arg-type]
