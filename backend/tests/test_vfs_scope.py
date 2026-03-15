"""Tests for VFS scope filter resolution (M006/S02).

Verifies that build_scope_filter correctly handles saved_query_id
resolution and _extract_where_body parsing.
"""

from app.vfs.strategies import _extract_where_body, build_scope_filter
from app.vfs.mount_service import MountDefinition


class TestExtractWhereBody:
    """Test SPARQL WHERE clause extraction."""

    def test_simple_select(self):
        query = "SELECT ?s WHERE { ?s a <http://example.org/Type> }"
        body = _extract_where_body(query)
        # ?s should be renamed to ?iri
        assert "?iri" in body
        assert "<http://example.org/Type>" in body

    def test_select_with_iri_var(self):
        query = "SELECT ?iri WHERE { ?iri a <http://example.org/Type> . ?iri <http://example.org/active> true }"
        body = _extract_where_body(query)
        assert "?iri" in body
        assert "a <http://example.org/Type>" in body

    def test_multiline_query(self):
        query = """
        PREFIX bpkm: <http://example.org/bpkm/>
        SELECT ?s WHERE {
          ?s a bpkm:Note .
          ?s bpkm:tags "project" .
        }
        """
        body = _extract_where_body(query)
        assert "?iri" in body  # ?s renamed
        assert 'bpkm:Note' in body

    def test_no_where_clause(self):
        """Fallback: return raw text if WHERE not found."""
        query = "ASK { ?s ?p ?o }"
        body = _extract_where_body(query)
        assert body == query


class TestBuildScopeFilter:
    """Test scope filter construction."""

    def _make_mount(self, sparql_scope="all", saved_query_id=None):
        return MountDefinition(
            id="test-id",
            name="test",
            path="test",
            strategy="flat",
            sparql_scope=sparql_scope,
            saved_query_id=saved_query_id,
        )

    def test_scope_all_returns_empty(self):
        mount = self._make_mount(sparql_scope="all")
        assert build_scope_filter(mount) == ""

    def test_scope_none_returns_empty(self):
        mount = self._make_mount(sparql_scope=None)
        assert build_scope_filter(mount) == ""

    def test_custom_sparql_scope(self):
        mount = self._make_mount(sparql_scope="?iri a <http://example.org/Note>")
        result = build_scope_filter(mount)
        assert "?iri a <http://example.org/Note>" in result
        assert "SELECT ?iri WHERE" in result

    def test_resolved_query_takes_precedence(self):
        mount = self._make_mount(sparql_scope="?iri a <http://example.org/OldType>")
        query_text = "SELECT ?s WHERE { ?s a <http://example.org/NewType> }"
        result = build_scope_filter(mount, resolved_query_text=query_text)
        assert "<http://example.org/NewType>" in result
        assert "<http://example.org/OldType>" not in result

    def test_resolved_query_renames_variables(self):
        mount = self._make_mount()
        query_text = "SELECT ?s WHERE { ?s a <http://example.org/Note> }"
        result = build_scope_filter(mount, resolved_query_text=query_text)
        assert "?iri" in result

    def test_no_resolved_query_falls_back(self):
        mount = self._make_mount(sparql_scope="?iri a <http://example.org/Note>")
        result = build_scope_filter(mount, resolved_query_text=None)
        assert "<http://example.org/Note>" in result
