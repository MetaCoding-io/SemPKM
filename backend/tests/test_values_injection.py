"""Tests for inject_values_binding() — parameterized SPARQL with VALUES clause.

Verifies correct VALUES placement inside WHERE body, IRI validation,
variable name sanitization, and no-op behavior for empty/invalid inputs.
"""

import pytest

from app.views.service import inject_values_binding


class TestInjectValuesBinding:
    """Unit tests for inject_values_binding()."""

    def test_injects_values_into_simple_select(self):
        """VALUES clause appears inside WHERE body of a simple SELECT."""
        query = "SELECT ?s ?title WHERE { ?s a <urn:ex:Note> . ?s <urn:ex:title> ?title . }"
        result = inject_values_binding(query, "project", "urn:sempkm:model:basic-pkm:seed-proj-1")
        assert "VALUES ?project { <urn:sempkm:model:basic-pkm:seed-proj-1> }" in result
        # VALUES must be inside WHERE { ... }
        where_start = result.upper().index("WHERE")
        values_pos = result.index("VALUES ?project")
        brace_pos = result.index("{", where_start)
        assert values_pos > brace_pos, "VALUES clause must be inside WHERE body"

    def test_injects_values_with_nested_braces(self):
        """VALUES clause works with queries that have nested braces (OPTIONAL, UNION)."""
        query = (
            "SELECT ?s ?title WHERE {\n"
            "  ?s a <urn:ex:Note> .\n"
            "  OPTIONAL { ?s <urn:ex:title> ?title }\n"
            "}"
        )
        result = inject_values_binding(query, "ctx", "https://example.org/thing/1")
        assert "VALUES ?ctx { <https://example.org/thing/1> }" in result
        # Ensure original patterns are still present
        assert "OPTIONAL { ?s <urn:ex:title> ?title }" in result

    def test_noop_when_iri_empty(self):
        """Empty IRI returns query unchanged — no VALUES injected."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "x", "")
        assert result == query

    def test_noop_when_iri_invalid_angle_brackets(self):
        """IRI containing < or > fails validation — query returned unchanged."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "x", "not<valid>iri")
        assert result == query
        assert "VALUES" not in result

    def test_noop_when_iri_invalid_quotes(self):
        """IRI containing quotes fails validation — query returned unchanged."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "x", 'urn:ex:"injected"')
        assert result == query

    def test_noop_when_iri_invalid_whitespace(self):
        """IRI with spaces fails validation — query returned unchanged."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "x", "urn:ex:has space")
        assert result == query

    def test_var_name_sanitized_rejects_special_chars(self):
        """Variable names with non-alphanumeric chars (injection attempt) rejected."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "x} . ?s ?p ?o . VALUES ?y {<http://evil>", "urn:ex:thing")
        assert result == query
        assert "VALUES" not in result

    def test_var_name_rejects_empty(self):
        """Empty var_name is rejected."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "", "urn:ex:thing")
        assert result == query

    def test_var_name_rejects_starts_with_digit(self):
        """Variable names starting with a digit are rejected (invalid SPARQL)."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "1bad", "urn:ex:thing")
        assert result == query

    def test_var_name_allows_underscore(self):
        """Variable names with underscores are valid."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "my_var", "urn:ex:thing")
        assert "VALUES ?my_var { <urn:ex:thing> }" in result

    def test_values_placed_at_start_of_where_body(self):
        """VALUES clause appears before existing triple patterns."""
        query = "SELECT ?s ?title WHERE { ?s a <urn:ex:Note> . ?s <urn:ex:title> ?title . }"
        result = inject_values_binding(query, "project", "urn:sempkm:model:basic-pkm:proj1")
        # Find WHERE { then VALUES should come before ?s a
        where_match_end = result.upper().index("WHERE") + len("WHERE")
        brace_pos = result.index("{", where_match_end)
        body = result[brace_pos + 1:]
        stripped = body.lstrip()
        assert stripped.startswith("VALUES ?project"), f"Expected VALUES at start of WHERE body, got: {stripped[:60]}"

    def test_accepts_http_iri(self):
        """HTTP IRIs are accepted."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "item", "https://example.org/resource/42")
        assert "VALUES ?item { <https://example.org/resource/42> }" in result

    def test_accepts_urn_iri(self):
        """URN-scheme IRIs are accepted."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "item", "urn:sempkm:model:basic-pkm:seed-note-1")
        assert "VALUES ?item { <urn:sempkm:model:basic-pkm:seed-note-1> }" in result

    # --- Edge cases (T03) ---

    def test_nested_optional_and_union_braces(self):
        """VALUES placed correctly with deeply nested OPTIONAL + UNION braces."""
        query = (
            "SELECT ?s ?title ?tag WHERE {\n"
            "  ?s a <urn:ex:Note> .\n"
            "  OPTIONAL {\n"
            "    ?s <urn:ex:title> ?title .\n"
            "    OPTIONAL { ?s <urn:ex:subtitle> ?sub }\n"
            "  }\n"
            "  { ?s <urn:ex:tag> ?tag } UNION { ?s <urn:ex:category> ?tag }\n"
            "}"
        )
        result = inject_values_binding(query, "project", "urn:ex:proj1")
        assert "VALUES ?project { <urn:ex:proj1> }" in result
        # All original patterns preserved
        assert "OPTIONAL {" in result
        assert "UNION" in result
        assert "?s <urn:ex:subtitle> ?sub" in result
        # VALUES is before original patterns
        where_idx = result.upper().index("WHERE")
        brace_idx = result.index("{", where_idx)
        body = result[brace_idx + 1:].lstrip()
        assert body.startswith("VALUES ?project"), f"Expected VALUES at start, got: {body[:60]}"

    def test_subquery_nested_where(self):
        """VALUES in outer WHERE when query contains a subquery with its own WHERE."""
        query = (
            "SELECT ?s ?count WHERE {\n"
            "  ?s a <urn:ex:Project> .\n"
            "  {\n"
            "    SELECT ?s (COUNT(?n) AS ?count) WHERE {\n"
            "      ?n <urn:ex:belongsTo> ?s .\n"
            "    } GROUP BY ?s\n"
            "  }\n"
            "}"
        )
        result = inject_values_binding(query, "ctx", "urn:ex:p1")
        assert "VALUES ?ctx { <urn:ex:p1> }" in result
        # VALUES should be in the outer WHERE, before original patterns
        first_where = result.upper().index("WHERE")
        first_brace = result.index("{", first_where)
        body = result[first_brace + 1:].lstrip()
        assert body.startswith("VALUES ?ctx"), f"VALUES not at outer WHERE start: {body[:80]}"
        # Subquery still intact
        assert "SELECT ?s (COUNT(?n) AS ?count) WHERE" in result
        assert "GROUP BY ?s" in result

    def test_var_name_rejects_dot(self):
        """Variable name with dot is rejected."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "my.var", "urn:ex:thing")
        assert result == query
        assert "VALUES" not in result

    def test_var_name_rejects_hyphen(self):
        """Variable name with hyphen is rejected."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "my-var", "urn:ex:thing")
        assert result == query
        assert "VALUES" not in result

    def test_var_name_rejects_space(self):
        """Variable name with space is rejected."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "my var", "urn:ex:thing")
        assert result == query
        assert "VALUES" not in result

    def test_var_name_rejects_sparql_keyword_injection(self):
        """Variable name that is a SPARQL keyword-like injection is rejected."""
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        # Semicolons, curly braces are not \w chars — regex rejects them
        result = inject_values_binding(query, "x;DROP", "urn:ex:thing")
        assert result == query

    def test_very_long_iri(self):
        """IRI over 500 characters is accepted if structurally valid."""
        long_path = "a" * 500
        long_iri = f"urn:sempkm:model:{long_path}"
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "item", long_iri)
        assert f"VALUES ?item {{ <{long_iri}> }}" in result
        assert len(long_iri) > 500

    def test_unicode_iri(self):
        """IRI with unicode characters in path passes validation."""
        unicode_iri = "urn:sempkm:model:café-résumé-naïve"
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "item", unicode_iri)
        assert f"VALUES ?item {{ <{unicode_iri}> }}" in result

    def test_unicode_iri_cjk(self):
        """IRI with CJK characters passes validation."""
        cjk_iri = "urn:sempkm:model:知識管理"
        query = "SELECT ?s WHERE { ?s a <urn:ex:Note> . }"
        result = inject_values_binding(query, "item", cjk_iri)
        assert f"VALUES ?item {{ <{cjk_iri}> }}" in result

    def test_no_where_clause_returns_unchanged(self):
        """Query without WHERE clause is returned unchanged."""
        query = "DESCRIBE <urn:ex:thing>"
        result = inject_values_binding(query, "x", "urn:ex:thing")
        assert result == query
        assert "VALUES" not in result

    def test_construct_without_where_returns_unchanged(self):
        """CONSTRUCT query without WHERE returns unchanged."""
        query = "CONSTRUCT { ?s ?p ?o } FROM <urn:ex:graph>"
        result = inject_values_binding(query, "x", "urn:ex:thing")
        # No WHERE clause to inject into
        assert "VALUES" not in result
