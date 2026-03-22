"""Tests for SPARQL client safety functions.

Covers _strip_sparql_strings(), scope_to_current_graph(), and
check_member_query_safety() — the most injection-sensitive code paths
in the backend. COR-02 edge cases (keywords inside string literals)
are explicitly tested.
"""

import pytest
from fastapi import HTTPException

from app.rdf.namespaces import CURRENT_GRAPH_IRI, INFERRED_GRAPH_IRI, MIRRORED_GRAPH_IRI
from app.sparql.client import (
    _find_outer_where,
    _strip_sparql_strings,
    check_member_query_safety,
    scope_to_current_graph,
)

CURRENT_GRAPH = str(CURRENT_GRAPH_IRI)
INFERRED_GRAPH = str(INFERRED_GRAPH_IRI)
MIRRORED_GRAPH = str(MIRRORED_GRAPH_IRI)


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

    def test_service_clause_raises_403(self):
        """Query with SERVICE clause raises HTTPException 403."""
        query = "SELECT ?s WHERE { SERVICE <http://dbpedia.org/sparql> { ?s ?p ?o } }"
        with pytest.raises(HTTPException) as exc_info:
            check_member_query_safety(query)
        assert exc_info.value.status_code == 403
        assert "SERVICE" in exc_info.value.detail

    def test_service_in_string_literal_does_not_raise(self):
        """SERVICE inside a string literal does NOT raise (false positive prevention)."""
        query = 'SELECT ?s WHERE { ?s rdfs:label "SERVICE <http://example.org>" }'
        check_member_query_safety(query)

    def test_service_in_hash_comment_does_not_raise(self):
        """SERVICE in a hash comment does NOT raise."""
        query = "SELECT ?s # SERVICE <http://example.org>\nWHERE { ?s ?p ?o }"
        check_member_query_safety(query)


# ── _find_outer_where ───────────────────────────────────────────────


class TestFindOuterWhere:
    """Tests for _find_outer_where() brace-depth-aware WHERE detection."""

    def test_simple_query_finds_where(self):
        """Simple SELECT query — finds WHERE at depth 0."""
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"
        pos = _find_outer_where(query)
        assert pos is not None
        assert query[pos:pos + 5].upper() == "WHERE"

    def test_service_inner_where_skipped(self):
        """WHERE inside a SERVICE block is not returned."""
        query = (
            "SELECT ?s ?label WHERE {\n"
            "  ?s a <http://example.org/Type> .\n"
            "  SERVICE <http://dbpedia.org/sparql> {\n"
            "    ?s rdfs:label ?label\n"
            "  }\n"
            "}"
        )
        pos = _find_outer_where(query)
        assert pos is not None
        # The returned position should be the outer WHERE, not any inner one
        assert pos == query.index("WHERE")

    def test_nested_braces_skipped(self):
        """WHERE-like text inside nested braces at depth > 0 is skipped."""
        # Simulate a sub-select with its own WHERE
        query = (
            "SELECT ?s WHERE {\n"
            "  { SELECT ?s WHERE { ?s a ?t } }\n"
            "}"
        )
        pos = _find_outer_where(query)
        assert pos is not None
        # Should find the first (outer) WHERE
        assert pos == query.index("WHERE")

    def test_no_where_returns_none(self):
        """Query without WHERE returns None."""
        query = "DESCRIBE <urn:example:thing>"
        pos = _find_outer_where(query)
        assert pos is None

    def test_where_in_string_ignored(self):
        """WHERE inside a string literal is not found."""
        query = 'SELECT ?s WHERE { ?s rdfs:label "WHERE is a keyword" }'
        pos = _find_outer_where(query)
        assert pos is not None
        # Should find the real WHERE, not the one in the string
        assert pos < query.index('"WHERE')

    def test_where_in_comment_ignored(self):
        """WHERE inside a hash comment is not found."""
        query = "SELECT ?s # WHERE is here\nWHERE { ?s ?p ?o }"
        pos = _find_outer_where(query)
        assert pos is not None
        # Should find the WHERE on the second line
        assert query[pos:pos + 5] == "WHERE"
        assert pos > query.index("#")

    def test_lowercase_where_found(self):
        """Lowercase 'where' is detected."""
        query = "SELECT ?s where { ?s ?p ?o }"
        pos = _find_outer_where(query)
        assert pos is not None
        assert query[pos:pos + 5] == "where"

    def test_mixed_case_where_found(self):
        """Mixed case 'Where' is detected."""
        query = "SELECT ?s Where { ?s ?p ?o }"
        pos = _find_outer_where(query)
        assert pos is not None
        assert query[pos:pos + 5] == "Where"


# ── SERVICE pass-through tests ──────────────────────────────────────


class TestServicePassThrough:
    """Tests for SERVICE clause handling in scope_to_current_graph()."""

    def test_basic_service_query_from_before_outer_where(self):
        """SERVICE query gets FROM injected before outer WHERE, SERVICE block unchanged."""
        query = (
            "SELECT ?s ?label WHERE {\n"
            "  ?s a <http://example.org/Type> .\n"
            "  SERVICE <http://dbpedia.org/sparql> {\n"
            "    ?s rdfs:label ?label\n"
            "  }\n"
            "}"
        )
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        # FROM should appear before outer WHERE
        assert result.index(f"FROM <{CURRENT_GRAPH}>") < result.index("WHERE")
        # SERVICE block should be completely unchanged
        assert "SERVICE <http://dbpedia.org/sparql>" in result
        assert "?s rdfs:label ?label" in result

    def test_service_with_inner_where_not_mangled(self):
        """SERVICE with its own WHERE keyword — FROM not injected at inner WHERE."""
        query = (
            "SELECT ?s ?label WHERE {\n"
            "  ?s a <http://example.org/Type> .\n"
            "  SERVICE <http://dbpedia.org/sparql> {\n"
            "    SELECT ?s ?label WHERE {\n"
            "      ?s rdfs:label ?label\n"
            "    }\n"
            "  }\n"
            "}"
        )
        result = scope_to_current_graph(query)
        # Only one FROM <current> should be injected (before the outer WHERE)
        assert result.count(f"FROM <{CURRENT_GRAPH}>") == 1
        # The inner "WHERE" inside SERVICE should not have FROM before it
        from_pos = result.index(f"FROM <{CURRENT_GRAPH}>")
        outer_where_pos = result.index("WHERE", from_pos + len(f"FROM <{CURRENT_GRAPH}>"))
        inner_service_pos = result.index("SERVICE")
        # FROM comes before outer WHERE which comes before SERVICE
        assert from_pos < outer_where_pos < inner_service_pos

    def test_nested_service_both_inner_blocks_unchanged(self):
        """Nested SERVICE (SERVICE inside SERVICE) — both inner blocks unchanged."""
        query = (
            "SELECT ?s ?label ?desc WHERE {\n"
            "  ?s a <http://example.org/Type> .\n"
            "  SERVICE <http://endpoint1.org/sparql> {\n"
            "    ?s rdfs:label ?label .\n"
            "    SERVICE <http://endpoint2.org/sparql> {\n"
            "      ?s <http://schema.org/description> ?desc\n"
            "    }\n"
            "  }\n"
            "}"
        )
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        # Both SERVICE blocks should be intact
        assert "SERVICE <http://endpoint1.org/sparql>" in result
        assert "SERVICE <http://endpoint2.org/sparql>" in result

    def test_service_inside_optional_unchanged(self):
        """SERVICE inside OPTIONAL — SERVICE block unchanged, outer FROM injected."""
        query = (
            "SELECT ?s ?label WHERE {\n"
            "  ?s a <http://example.org/Type> .\n"
            "  OPTIONAL {\n"
            "    SERVICE <http://dbpedia.org/sparql> {\n"
            "      ?s rdfs:label ?label\n"
            "    }\n"
            "  }\n"
            "}"
        )
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        # SERVICE inside OPTIONAL should be unchanged
        assert "SERVICE <http://dbpedia.org/sparql>" in result
        assert "?s rdfs:label ?label" in result

    def test_query_with_only_service_no_outer_body(self):
        """Query with SERVICE as the only pattern — handled gracefully."""
        query = (
            "SELECT ?s ?label WHERE {\n"
            "  SERVICE <http://dbpedia.org/sparql> {\n"
            "    ?s rdfs:label ?label\n"
            "  }\n"
            "}"
        )
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert "SERVICE <http://dbpedia.org/sparql>" in result

    def test_service_keyword_inside_string_literal_not_detected(self):
        """SERVICE keyword inside string literal does not affect scoping."""
        query = 'SELECT ?s WHERE { ?s rdfs:label "SERVICE <http://example.org>" }'
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        # The string should be preserved as-is
        assert '"SERVICE <http://example.org>"' in result

    def test_service_keyword_inside_comment_not_detected(self):
        """SERVICE keyword inside comment does not affect scoping."""
        query = (
            "SELECT ?s # SERVICE <http://example.org>\n"
            "WHERE { ?s ?p ?o }"
        )
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result

    def test_multiple_service_blocks(self):
        """Multiple SERVICE blocks in one query — all preserved, FROM before outer WHERE."""
        query = (
            "SELECT ?s ?label ?desc WHERE {\n"
            "  ?s a <http://example.org/Type> .\n"
            "  SERVICE <http://dbpedia.org/sparql> {\n"
            "    ?s rdfs:label ?label\n"
            "  }\n"
            "  SERVICE <http://wikidata.org/sparql> {\n"
            "    ?s <http://schema.org/description> ?desc\n"
            "  }\n"
            "}"
        )
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert "SERVICE <http://dbpedia.org/sparql>" in result
        assert "SERVICE <http://wikidata.org/sparql>" in result
        # FROM appears exactly once for current graph
        assert result.count(f"FROM <{CURRENT_GRAPH}>") == 1

    def test_service_silent_keyword_form(self):
        """SERVICE SILENT form is preserved."""
        query = (
            "SELECT ?s ?label WHERE {\n"
            "  ?s a <http://example.org/Type> .\n"
            "  SERVICE SILENT <http://dbpedia.org/sparql> {\n"
            "    ?s rdfs:label ?label\n"
            "  }\n"
            "}"
        )
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert "SERVICE SILENT <http://dbpedia.org/sparql>" in result

    def test_construct_with_service(self):
        """CONSTRUCT query with SERVICE — FROM injected before outer WHERE."""
        query = (
            "CONSTRUCT { ?s rdfs:label ?label } WHERE {\n"
            "  ?s a <http://example.org/Type> .\n"
            "  SERVICE <http://dbpedia.org/sparql> {\n"
            "    ?s rdfs:label ?label\n"
            "  }\n"
            "}"
        )
        result = scope_to_current_graph(query)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        # CONSTRUCT template braces are at depth > 0 before the WHERE —
        # the outer WHERE is found after the closing } of the template
        assert "SERVICE <http://dbpedia.org/sparql>" in result


# ── Mirrored graph tests ───────────────────────────────────────────


class TestMirroredGraph:
    """Tests for include_mirrored parameter in scope_to_current_graph()."""

    def test_include_mirrored_true_adds_mirrored_graph(self):
        """include_mirrored=True (default) adds FROM <urn:sempkm:mirrored>."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        result = scope_to_current_graph(query, include_mirrored=True)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert f"FROM <{MIRRORED_GRAPH}>" in result

    def test_include_mirrored_false_omits_mirrored_graph(self):
        """include_mirrored=False omits mirrored graph."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        result = scope_to_current_graph(query, include_mirrored=False)
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert f"FROM <{MIRRORED_GRAPH}>" not in result

    def test_default_includes_mirrored(self):
        """Default call includes mirrored graph."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        result = scope_to_current_graph(query)
        assert f"FROM <{MIRRORED_GRAPH}>" in result

    def test_mirrored_with_inferred_and_shared(self):
        """All graph types can be combined."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        shared = ["urn:shared:graph1"]
        result = scope_to_current_graph(
            query, include_mirrored=True, include_inferred=True, shared_graphs=shared
        )
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert f"FROM <{INFERRED_GRAPH}>" in result
        assert f"FROM <{MIRRORED_GRAPH}>" in result
        assert "FROM <urn:shared:graph1>" in result

    def test_mirrored_false_inferred_false(self):
        """Both mirrored and inferred can be disabled."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        result = scope_to_current_graph(
            query, include_mirrored=False, include_inferred=False
        )
        assert f"FROM <{CURRENT_GRAPH}>" in result
        assert f"FROM <{INFERRED_GRAPH}>" not in result
        assert f"FROM <{MIRRORED_GRAPH}>" not in result

    def test_mirrored_with_service_query(self):
        """Mirrored graph is included in queries that also have SERVICE blocks."""
        query = (
            "SELECT ?s ?label WHERE {\n"
            "  ?s a <http://example.org/Type> .\n"
            "  SERVICE <http://dbpedia.org/sparql> {\n"
            "    ?s rdfs:label ?label\n"
            "  }\n"
            "}"
        )
        result = scope_to_current_graph(query)
        assert f"FROM <{MIRRORED_GRAPH}>" in result
        assert "SERVICE <http://dbpedia.org/sparql>" in result
