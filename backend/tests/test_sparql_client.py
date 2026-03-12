"""Tests for SPARQL client safety functions.

Covers _strip_sparql_strings(), scope_to_current_graph(), and
check_member_query_safety() — the most injection-sensitive code paths
in the backend. COR-02 edge cases (keywords inside string literals)
are explicitly tested.
"""

import pytest
from fastapi import HTTPException

from app.rdf.namespaces import CURRENT_GRAPH_IRI, INFERRED_GRAPH_IRI
from app.sparql.client import (
    _strip_sparql_strings,
    check_member_query_safety,
    scope_to_current_graph,
)

CURRENT_GRAPH = str(CURRENT_GRAPH_IRI)
INFERRED_GRAPH = str(INFERRED_GRAPH_IRI)


# ── _strip_sparql_strings ──────────────────────────────────────────


class TestStripSparqlStrings:
    """Tests for _strip_sparql_strings()."""

    def test_double_quoted_string_blanked(self):
        """Double-quoted string interior replaced with spaces, delimiters kept."""
        query = 'SELECT ?s WHERE { ?s rdfs:label "hello world" }'
        result = _strip_sparql_strings(query)
        assert '"           "' in result
        # Keywords outside string survive
        assert "SELECT" in result
        assert "WHERE" in result

    def test_single_quoted_string_blanked(self):
        """Single-quoted string interior replaced with spaces, delimiters kept."""
        query = "SELECT ?s WHERE { ?s rdfs:label 'hello world' }"
        result = _strip_sparql_strings(query)
        assert "'           '" in result

    def test_triple_double_quoted_string_blanked(self):
        """Triple-double-quoted string interior blanked."""
        query = 'SELECT ?s WHERE { ?s rdfs:label """multi\nline""" }'
        result = _strip_sparql_strings(query)
        # Delimiters preserved, interior blanked
        assert '"""' in result
        assert "multi" not in result

    def test_triple_single_quoted_string_blanked(self):
        """Triple-single-quoted string interior blanked."""
        query = "SELECT ?s WHERE { ?s rdfs:label '''multi\nline''' }"
        result = _strip_sparql_strings(query)
        assert "'''" in result
        assert "multi" not in result

    def test_hash_comment_replaced_with_spaces(self):
        """Hash comment replaced entirely with spaces."""
        query = "SELECT ?s # this is a comment\nWHERE { ?s ?p ?o }"
        result = _strip_sparql_strings(query)
        assert "#" not in result
        assert "this is a comment" not in result
        # Newline preserved, WHERE keyword survives
        assert "\nWHERE" in result

    def test_escaped_quote_inside_string(self):
        """Escaped quote inside string does not break parsing."""
        query = r'SELECT ?s WHERE { ?s rdfs:label "say \"hi\"" }'
        result = _strip_sparql_strings(query)
        # Interior blanked — escaped quotes don't terminate the string
        assert "say" not in result
        # Delimiters present
        assert result.count('"') >= 2

    def test_mixed_strings_comments_keywords(self):
        """Only real keywords survive when query has strings, comments, and keywords."""
        query = (
            'SELECT ?s # FROM named graph\n'
            'WHERE { ?s rdfs:label "contains FROM and GRAPH keywords" }'
        )
        result = _strip_sparql_strings(query)
        # Real keywords survive
        assert "SELECT" in result
        assert "WHERE" in result
        # Keywords inside string and comment are blanked
        upper = result.upper()
        # Count FROM occurrences — should be zero (one was in comment, one in string)
        from_outside = [m for m in __import__("re").finditer(r"\bFROM\b", upper)]
        assert len(from_outside) == 0


# ── scope_to_current_graph ──────────────────────────────────────────


class TestScopeToCurrentGraph:
    """Tests for scope_to_current_graph()."""

    def test_basic_query_gets_from_injected(self):
        """Basic query gets FROM <urn:sempkm:current> injected before WHERE."""
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert result.index(f"FROM <{CURRENT_GRAPH}>") < result.index("WHERE")

    def test_all_graphs_returns_unchanged(self):
        """all_graphs=True returns query unchanged."""
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"
        result = scope_to_current_graph(query, all_graphs=True)
        assert result == query

    def test_existing_from_clause_unchanged(self):
        """Query with existing FROM clause returned unchanged."""
        query = "SELECT ?s FROM <urn:other:graph> WHERE { ?s ?p ?o }"
        result = scope_to_current_graph(query)
        assert result == query

    def test_graph_clause_referencing_current_unchanged(self):
        """Query with GRAPH clause referencing CURRENT_GRAPH returned unchanged."""
        query = f"SELECT ?s WHERE {{ GRAPH <{CURRENT_GRAPH}> {{ ?s ?p ?o }} }}"
        result = scope_to_current_graph(query)
        assert result == query

    def test_include_inferred_true_adds_inferred_graph(self):
        """include_inferred=True (default) adds FROM <urn:sempkm:inferred>."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        result = scope_to_current_graph(query, include_inferred=True)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert f"FROM <{INFERRED_GRAPH}>" in result

    def test_include_inferred_false_omits_inferred_graph(self):
        """include_inferred=False omits inferred graph."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        result = scope_to_current_graph(query, include_inferred=False)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert f"FROM <{INFERRED_GRAPH}>" not in result

    def test_shared_graphs_adds_from_clauses(self):
        """shared_graphs parameter adds additional FROM clauses."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        shared = ["urn:shared:graph1", "urn:shared:graph2"]
        result = scope_to_current_graph(query, shared_graphs=shared)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert "FROM <urn:shared:graph1>" in result
        assert "FROM <urn:shared:graph2>" in result

    def test_cor02_from_inside_string_still_gets_scoped(self):
        """COR-02: query with FROM inside a string literal still gets scoped."""
        query = 'SELECT ?s WHERE { ?s rdfs:label "FROM <urn:other:graph>" }'
        result = scope_to_current_graph(query)
        # The FROM inside the string should NOT prevent scoping
        assert f"FROM <{CURRENT_GRAPH}>" in result

    def test_no_where_clause_returned_as_is(self):
        """Query without WHERE clause returned as-is."""
        query = "DESCRIBE <urn:example:thing>"
        result = scope_to_current_graph(query)
        # No WHERE to inject before, so returned unchanged
        assert result == query


# ── check_member_query_safety ───────────────────────────────────────


class TestCheckMemberQuerySafety:
    """Tests for check_member_query_safety()."""

    def test_clean_select_passes(self):
        """Clean SELECT query passes without exception."""
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"
        # Should not raise
        check_member_query_safety(query)

    def test_from_clause_raises_403(self):
        """Query with FROM clause raises HTTPException 403."""
        query = "SELECT ?s FROM <urn:other:graph> WHERE { ?s ?p ?o }"
        with pytest.raises(HTTPException) as exc_info:
            check_member_query_safety(query)
        assert exc_info.value.status_code == 403

    def test_graph_clause_raises_403(self):
        """Query with GRAPH clause raises HTTPException 403."""
        query = "SELECT ?s WHERE { GRAPH <urn:other:graph> { ?s ?p ?o } }"
        with pytest.raises(HTTPException) as exc_info:
            check_member_query_safety(query)
        assert exc_info.value.status_code == 403

    def test_cor02_from_in_string_does_not_raise(self):
        """COR-02: FROM inside a string literal does NOT raise (false positive prevention)."""
        query = 'SELECT ?s WHERE { ?s rdfs:label "FROM <urn:other:graph>" }'
        # Should not raise — the FROM is inside a string, not a real clause
        check_member_query_safety(query)

    def test_cor02_graph_in_string_does_not_raise(self):
        """COR-02: GRAPH inside a string literal does NOT raise."""
        query = 'SELECT ?s WHERE { ?s rdfs:label "GRAPH <urn:g>" }'
        check_member_query_safety(query)

    def test_from_in_hash_comment_does_not_raise(self):
        """FROM in a hash comment does NOT raise."""
        query = "SELECT ?s # FROM <urn:other:graph>\nWHERE { ?s ?p ?o }"
        check_member_query_safety(query)

    def test_graph_in_hash_comment_does_not_raise(self):
        """GRAPH in a hash comment does NOT raise."""
        query = "SELECT ?s # GRAPH <urn:other:graph>\nWHERE { ?s ?p ?o }"
        check_member_query_safety(query)
