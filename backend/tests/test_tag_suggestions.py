"""Tests for the tag-suggestions endpoint logic.

Validates:
- SPARQL query generation for empty and non-empty queries
- Special character escaping in query strings
- Result parsing from SPARQL bindings format
- Result ordering (count DESC, then alphabetical)
- build_tag_suggestions_sparql and parse_tag_bindings are pure functions
"""

import pytest

from app.browser.search import (
    _sparql_escape,
    build_tag_suggestions_sparql,
    parse_tag_bindings,
)


# ---------------------------------------------------------------------------
# SPARQL query generation
# ---------------------------------------------------------------------------


class TestBuildTagSuggestionsSparql:
    """Unit tests for build_tag_suggestions_sparql()."""

    def test_empty_query_has_no_filter(self):
        """Empty q returns SPARQL without a FILTER clause."""
        sparql = build_tag_suggestions_sparql("")
        assert "FILTER" not in sparql

    def test_empty_query_has_union(self):
        """Empty q still queries both tag predicates via UNION."""
        sparql = build_tag_suggestions_sparql("")
        assert "UNION" in sparql
        assert "urn:sempkm:model:basic-pkm:tags" in sparql
        assert "https://schema.org/keywords" in sparql

    def test_empty_query_has_group_and_order(self):
        """Empty q includes GROUP BY, ORDER BY, and LIMIT."""
        sparql = build_tag_suggestions_sparql("")
        assert "GROUP BY ?tagValue" in sparql
        assert "ORDER BY DESC(?count) ?tagValue" in sparql
        assert "LIMIT 30" in sparql

    def test_prefix_filter_applied(self):
        """Non-empty q adds case-insensitive CONTAINS filter."""
        sparql = build_tag_suggestions_sparql("arch")
        assert 'FILTER(CONTAINS(LCASE(?tagValue), LCASE("arch")))' in sparql

    def test_prefix_filter_preserves_union(self):
        """Non-empty q still queries both predicates."""
        sparql = build_tag_suggestions_sparql("design")
        assert "UNION" in sparql
        assert "urn:sempkm:model:basic-pkm:tags" in sparql
        assert "https://schema.org/keywords" in sparql

    def test_limit_30(self):
        """Query always limits to 30 results."""
        for q in ["", "test", "a"]:
            sparql = build_tag_suggestions_sparql(q)
            assert "LIMIT 30" in sparql

    def test_count_aggregation(self):
        """Query counts distinct subjects per tag value."""
        sparql = build_tag_suggestions_sparql("")
        assert "COUNT(DISTINCT ?s)" in sparql


# ---------------------------------------------------------------------------
# SPARQL escaping
# ---------------------------------------------------------------------------


class TestSparqlEscape:
    """Unit tests for _sparql_escape()."""

    def test_plain_text_unchanged(self):
        """Plain ASCII text passes through unchanged."""
        assert _sparql_escape("architecture") == "architecture"

    def test_double_quote_escaped(self):
        """Double quotes are backslash-escaped."""
        assert _sparql_escape('say "hello"') == 'say \\"hello\\"'

    def test_backslash_escaped(self):
        """Backslashes are doubled."""
        assert _sparql_escape("a\\b") == "a\\\\b"

    def test_newline_escaped(self):
        """Newlines become literal \\n."""
        assert _sparql_escape("line1\nline2") == "line1\\nline2"

    def test_combined_escaping(self):
        """Multiple special chars in one string are all escaped."""
        result = _sparql_escape('a\\b"c\nd')
        assert result == 'a\\\\b\\"c\\nd'

    def test_empty_string(self):
        """Empty string passes through."""
        assert _sparql_escape("") == ""


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------


class TestParseTagBindings:
    """Unit tests for parse_tag_bindings()."""

    def test_empty_bindings(self):
        """Empty bindings list produces empty results."""
        assert parse_tag_bindings([]) == []

    def test_single_binding(self):
        """Single binding is parsed correctly."""
        bindings = [
            {
                "tagValue": {"type": "literal", "value": "architecture"},
                "count": {"type": "literal", "value": "5"},
            }
        ]
        result = parse_tag_bindings(bindings)
        assert result == [{"value": "architecture", "count": 5}]

    def test_multiple_bindings(self):
        """Multiple bindings produce corresponding results in order."""
        bindings = [
            {
                "tagValue": {"type": "literal", "value": "design"},
                "count": {"type": "literal", "value": "9"},
            },
            {
                "tagValue": {"type": "literal", "value": "architecture"},
                "count": {"type": "literal", "value": "3"},
            },
        ]
        result = parse_tag_bindings(bindings)
        assert len(result) == 2
        assert result[0] == {"value": "design", "count": 9}
        assert result[1] == {"value": "architecture", "count": 3}

    def test_skips_empty_tag_value(self):
        """Bindings with empty tagValue are skipped."""
        bindings = [
            {
                "tagValue": {"type": "literal", "value": ""},
                "count": {"type": "literal", "value": "1"},
            },
            {
                "tagValue": {"type": "literal", "value": "valid"},
                "count": {"type": "literal", "value": "2"},
            },
        ]
        result = parse_tag_bindings(bindings)
        assert len(result) == 1
        assert result[0]["value"] == "valid"

    def test_missing_count_defaults_to_zero(self):
        """If count is missing from binding, defaults to 0."""
        bindings = [
            {
                "tagValue": {"type": "literal", "value": "lonely"},
            }
        ]
        result = parse_tag_bindings(bindings)
        assert result == [{"value": "lonely", "count": 0}]

    def test_count_parsed_as_int(self):
        """Count values are parsed as integers, not strings."""
        bindings = [
            {
                "tagValue": {"type": "literal", "value": "test"},
                "count": {"type": "literal", "value": "42"},
            }
        ]
        result = parse_tag_bindings(bindings)
        assert isinstance(result[0]["count"], int)
        assert result[0]["count"] == 42


# ---------------------------------------------------------------------------
# Query + escaping integration
# ---------------------------------------------------------------------------


class TestQueryEscapingIntegration:
    """Verify escaping is applied in generated SPARQL."""

    def test_double_quote_in_query(self):
        """Double quotes in q are escaped in the SPARQL filter."""
        sparql = build_tag_suggestions_sparql('test"value')
        assert 'test\\"value' in sparql
        # Must not have unescaped double-quote breaking the SPARQL string
        assert 'LCASE("test\\"value")' in sparql

    def test_backslash_in_query(self):
        """Backslashes in q are escaped in the SPARQL filter."""
        sparql = build_tag_suggestions_sparql("a\\b")
        assert "a\\\\b" in sparql

    def test_newline_in_query(self):
        """Newlines in q are escaped in the SPARQL filter."""
        sparql = build_tag_suggestions_sparql("line1\nline2")
        assert "line1\\nline2" in sparql
