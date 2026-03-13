"""Tests for the by-tag explorer mode and tag-children endpoint.

Covers:
  - _handle_by_tag is registered in EXPLORER_MODES and is async callable
  - SPARQL query construction produces valid UNION query
  - Tag value escaping in tag_children query (prevent SPARQL injection)
  - Handler accepts label_service and icon_svc kwargs
"""

import inspect

import pytest

from app.browser.workspace import (
    EXPLORER_MODES,
    _handle_by_tag,
    _sparql_escape,
)


class TestExplorerModeRegistration:
    """Verify _handle_by_tag is properly registered."""

    def test_by_tag_in_explorer_modes(self):
        assert "by-tag" in EXPLORER_MODES

    def test_by_tag_handler_is_callable(self):
        assert callable(EXPLORER_MODES["by-tag"])

    def test_by_tag_handler_is_async(self):
        assert inspect.iscoroutinefunction(EXPLORER_MODES["by-tag"])

    def test_by_tag_handler_is_handle_by_tag(self):
        assert EXPLORER_MODES["by-tag"] is _handle_by_tag


class TestHandlerSignature:
    """Verify handler accepts the expected keyword arguments."""

    def test_handle_by_tag_accepts_label_service(self):
        sig = inspect.signature(_handle_by_tag)
        assert "label_service" in sig.parameters

    def test_handle_by_tag_accepts_icon_svc(self):
        sig = inspect.signature(_handle_by_tag)
        assert "icon_svc" in sig.parameters

    def test_handle_by_tag_accepts_request(self):
        sig = inspect.signature(_handle_by_tag)
        assert "request" in sig.parameters

    def test_handle_by_tag_accepts_kwargs(self):
        """Handler should accept **_kwargs for forward-compat with dispatcher."""
        sig = inspect.signature(_handle_by_tag)
        has_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )
        assert has_var_keyword


class TestSparqlQueryConstruction:
    """Verify the SPARQL queries used by the by-tag explorer."""

    def test_by_tag_query_uses_union(self):
        """The main query must use UNION to combine bpkm:tags and schema:keywords."""
        # The SPARQL query is inlined in _handle_by_tag; verify its structure
        # by inspecting the source code
        source = inspect.getsource(_handle_by_tag)
        assert "UNION" in source
        assert "urn:sempkm:model:basic-pkm:tags" in source
        assert "https://schema.org/keywords" in source

    def test_by_tag_query_uses_count_distinct(self):
        """The main query must use COUNT(DISTINCT ?iri) to avoid double-counting."""
        source = inspect.getsource(_handle_by_tag)
        assert "COUNT(DISTINCT ?iri)" in source

    def test_by_tag_query_uses_group_by(self):
        source = inspect.getsource(_handle_by_tag)
        assert "GROUP BY ?tagValue" in source

    def test_by_tag_query_targets_current_graph(self):
        source = inspect.getsource(_handle_by_tag)
        assert "urn:sempkm:current" in source


class TestTagValueEscaping:
    """Verify SPARQL injection protection in tag value escaping."""

    def test_escape_double_quotes(self):
        assert _sparql_escape('tag"value') == 'tag\\"value'

    def test_escape_backslash(self):
        assert _sparql_escape("tag\\value") == "tag\\\\value"

    def test_escape_newline(self):
        assert _sparql_escape("tag\nvalue") == "tag\\nvalue"

    def test_escape_combined(self):
        result = _sparql_escape('a"b\\c\nd')
        assert result == 'a\\"b\\\\c\\nd'

    def test_escape_clean_string(self):
        assert _sparql_escape("clean-tag") == "clean-tag"

    def test_tag_children_query_uses_escape(self):
        """The tag_children endpoint must use _sparql_escape on the tag parameter."""
        from app.browser.workspace import tag_children
        source = inspect.getsource(tag_children)
        assert "_sparql_escape" in source


class TestTagChildrenQueryStructure:
    """Verify the tag_children SPARQL query structure."""

    def test_tag_children_uses_union(self):
        from app.browser.workspace import tag_children
        source = inspect.getsource(tag_children)
        assert "UNION" in source
        assert "urn:sempkm:model:basic-pkm:tags" in source
        assert "https://schema.org/keywords" in source

    def test_tag_children_resolves_labels(self):
        """tag_children query must include label resolution OPTIONALS."""
        from app.browser.workspace import tag_children
        source = inspect.getsource(tag_children)
        assert "_LABEL_OPTIONALS" in source
        assert "_LABEL_COALESCE" in source

    def test_tag_children_filters_rdfs_resource(self):
        """tag_children query must filter out rdfs:Resource type."""
        from app.browser.workspace import tag_children
        source = inspect.getsource(tag_children)
        assert "rdfs#Resource" in source or "Resource" in source
