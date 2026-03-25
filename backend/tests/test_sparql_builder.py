"""Tests for the centralized SPARQL builder module.

Covers: safe_iri, safe_literal, sparql_escape_string, values_clause,
triple_pattern — including malicious payloads and edge cases.
"""

import pytest

from app.sparql.builder import (
    safe_iri,
    safe_literal,
    sparql_escape_string,
    triple_pattern,
    values_clause,
)


# =====================================================================
# safe_iri
# =====================================================================


class TestSafeIri:
    """Validates IRI sanitisation and N3 serialization."""

    # --- Valid IRIs ---

    def test_http_iri(self):
        assert safe_iri("http://example.org/test") == "<http://example.org/test>"

    def test_https_iri(self):
        assert safe_iri("https://example.org/test") == "<https://example.org/test>"

    def test_urn_iri(self):
        assert (
            safe_iri("urn:sempkm:model:basic-pkm:Note")
            == "<urn:sempkm:model:basic-pkm:Note>"
        )

    def test_urn_with_colon_path(self):
        assert (
            safe_iri("urn:sempkm:model:basic-pkm:seed-note-arch")
            == "<urn:sempkm:model:basic-pkm:seed-note-arch>"
        )

    def test_http_with_path(self):
        assert (
            safe_iri("http://example.org/ns#Thing")
            == "<http://example.org/ns#Thing>"
        )

    def test_https_with_query_param(self):
        result = safe_iri("https://example.org/page?id=42")
        assert result == "<https://example.org/page?id=42>"

    # --- Empty / None ---

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            safe_iri("")

    def test_none_raises(self):
        with pytest.raises((ValueError, TypeError)):
            safe_iri(None)  # type: ignore[arg-type]

    # --- Invalid schemes ---

    def test_unknown_scheme_raises(self):
        with pytest.raises(ValueError, match="not allowed"):
            safe_iri("ftp://example.org/file")

    def test_no_scheme_raises(self):
        with pytest.raises(ValueError, match="no scheme"):
            safe_iri("example.org/test")

    def test_relative_path_raises(self):
        with pytest.raises(ValueError):
            safe_iri("/relative/path")

    # --- HTTP without netloc ---

    def test_http_no_host_raises(self):
        with pytest.raises(ValueError, match="must have a host"):
            safe_iri("http:///path-only")

    # --- URN without path ---

    def test_urn_empty_path_raises(self):
        with pytest.raises(ValueError, match="must have a path"):
            safe_iri("urn:")

    # --- SPARQL injection payloads ---

    def test_angle_bracket_breakout(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://evil.com/x> . <http://evil.com/y")

    def test_closing_angle_bracket(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://evil.com/x>")

    def test_opening_angle_bracket(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("<http://evil.com/x")

    def test_double_quote_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri('http://evil.com/x"injected')

    def test_comment_injection_via_newline(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://evil.com/x\n# comment")

    def test_whitespace_injection_space(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://evil.com/x y")

    def test_whitespace_injection_tab(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://evil.com/x\ty")

    def test_carriage_return_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://evil.com/x\ry")

    def test_backslash_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://evil.com/x\\y")

    def test_curly_brace_injection(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri("http://evil.com/x{y}")

    def test_complex_sparql_injection(self):
        """Full multi-statement injection payload."""
        payload = (
            'http://evil.com/x> . <http://evil.com/y> <http://evil.com/z> "injected'
        )
        with pytest.raises(ValueError, match="forbidden characters"):
            safe_iri(payload)


# =====================================================================
# safe_literal
# =====================================================================


class TestSafeLiteral:
    """Validates literal serialization via rdflib."""

    def test_simple_string(self):
        result = safe_literal("hello")
        assert result == '"hello"'

    def test_empty_string(self):
        result = safe_literal("")
        assert result == '""'

    def test_double_quotes_escaped(self):
        result = safe_literal('say "hi"')
        assert '\\"' in result
        assert result.startswith('"')

    def test_backslash_escaped(self):
        result = safe_literal("back\\slash")
        assert "\\\\" in result

    def test_newline_handling(self):
        """rdflib uses triple-quotes for strings with newlines — both forms are valid SPARQL."""
        result = safe_literal("line1\nline2")
        # rdflib produces triple-quoted form: """line1\nline2"""
        # Both triple-quote and escaped forms are valid SPARQL
        assert "line1" in result
        assert "line2" in result

    def test_tab_handling(self):
        result = safe_literal("col1\tcol2")
        assert "col1" in result
        assert "col2" in result

    def test_carriage_return_handling(self):
        result = safe_literal("cr\rhere")
        assert "cr" in result

    def test_with_xsd_datatype(self):
        from rdflib import XSD

        result = safe_literal("42", datatype=str(XSD.integer))
        assert "42" in result
        assert "integer" in result
        assert "^^" in result

    def test_with_language_tag(self):
        result = safe_literal("hello", lang="en")
        assert result == '"hello"@en'

    def test_none_value_raises(self):
        with pytest.raises(ValueError, match="must not be None"):
            safe_literal(None)  # type: ignore[arg-type]

    def test_single_quotes(self):
        result = safe_literal("it's fine")
        assert "it" in result
        assert "fine" in result

    def test_all_special_chars(self):
        """Ensure a string with every special character round-trips safely."""
        val = 'a\\b"c\nd\re\tf'
        result = safe_literal(val)
        # Must produce a syntactically valid N3 literal
        assert result.startswith('"')


# =====================================================================
# sparql_escape_string
# =====================================================================


class TestSparqlEscapeString:
    """Tests the consolidated string-escape function."""

    def test_plain_string_unchanged(self):
        assert sparql_escape_string("hello world") == "hello world"

    def test_backslash_escaped(self):
        assert sparql_escape_string("a\\b") == "a\\\\b"

    def test_double_quote_escaped(self):
        assert sparql_escape_string('a"b') == 'a\\"b'

    def test_single_quote_escaped(self):
        assert sparql_escape_string("a'b") == "a\\'b"

    def test_newline_escaped(self):
        assert sparql_escape_string("a\nb") == "a\\nb"

    def test_carriage_return_escaped(self):
        assert sparql_escape_string("a\rb") == "a\\rb"

    def test_tab_escaped(self):
        assert sparql_escape_string("a\tb") == "a\\tb"

    def test_all_special_chars_combined(self):
        raw = 'a\\b"c\'d\ne\rf\tg'
        expected = 'a\\\\b\\"c\\\'d\\ne\\rf\\tg'
        assert sparql_escape_string(raw) == expected

    def test_empty_string(self):
        assert sparql_escape_string("") == ""

    def test_none_raises(self):
        with pytest.raises(ValueError, match="Cannot escape None"):
            sparql_escape_string(None)  # type: ignore[arg-type]

    def test_unicode_preserved(self):
        assert sparql_escape_string("café ☕") == "café ☕"

    def test_already_escaped_gets_double_escaped(self):
        """Prevent double-escape bugs: caller should only escape once."""
        assert sparql_escape_string("a\\nb") == "a\\\\nb"

    def test_multiline_string(self):
        raw = "line1\nline2\nline3"
        assert sparql_escape_string(raw) == "line1\\nline2\\nline3"

    def test_windows_line_ending(self):
        raw = "line1\r\nline2"
        assert sparql_escape_string(raw) == "line1\\r\\nline2"


# =====================================================================
# values_clause
# =====================================================================


class TestValuesClause:
    """Tests VALUES clause construction."""

    def test_single_iri(self):
        result = values_clause("type", ["http://example.org/A"])
        assert result == "VALUES (?type) { (<http://example.org/A>) }"

    def test_multiple_iris(self):
        result = values_clause(
            "type", ["http://example.org/A", "http://example.org/B"]
        )
        assert "(<http://example.org/A>)" in result
        assert "(<http://example.org/B>)" in result
        assert result.startswith("VALUES (?type)")

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="at least one IRI"):
            values_clause("type", [])

    def test_empty_var_name_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            values_clause("", ["http://example.org/A"])

    def test_invalid_iri_in_list_raises(self):
        with pytest.raises(ValueError):
            values_clause("type", ["http://example.org/A", "not-an-iri"])

    def test_malicious_iri_in_list_raises(self):
        with pytest.raises(ValueError):
            values_clause("type", ["http://example.org/A", "http://evil.com/x> DROP"])

    def test_urn_iris(self):
        result = values_clause("model", ["urn:sempkm:model:basic-pkm:Note"])
        assert "(<urn:sempkm:model:basic-pkm:Note>)" in result


# =====================================================================
# triple_pattern
# =====================================================================


class TestTriplePattern:
    """Tests triple pattern construction."""

    def test_all_iris(self):
        result = triple_pattern(
            "http://example.org/s", "http://example.org/p", "http://example.org/o"
        )
        assert result == "<http://example.org/s> <http://example.org/p> <http://example.org/o> ."

    def test_variable_subject(self):
        result = triple_pattern("?s", "http://example.org/p", "http://example.org/o")
        assert result.startswith("?s ")

    def test_variable_object(self):
        result = triple_pattern(
            "http://example.org/s", "http://example.org/p", "?obj"
        )
        assert result.endswith("?obj .")

    def test_dollar_variable(self):
        result = triple_pattern("$s", "http://example.org/p", "$o")
        assert result == "$s <http://example.org/p> $o ."

    def test_all_variables(self):
        result = triple_pattern("?s", "?p", "?o")
        assert result == "?s ?p ?o ."

    def test_empty_subject_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            triple_pattern("", "http://example.org/p", "?o")

    def test_empty_predicate_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            triple_pattern("?s", "", "?o")

    def test_malicious_iri_subject_raises(self):
        with pytest.raises(ValueError):
            triple_pattern(
                "http://evil.com/x> DROP", "http://example.org/p", "?o"
            )

    def test_mixed_iris_and_variables(self):
        result = triple_pattern(
            "http://example.org/s", "?p", "http://example.org/o"
        )
        assert result == "<http://example.org/s> ?p <http://example.org/o> ."
