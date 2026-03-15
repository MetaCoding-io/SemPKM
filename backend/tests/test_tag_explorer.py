"""Tests for the by-tag explorer mode and tag-children endpoint.

Covers:
  - _handle_by_tag is registered in EXPLORER_MODES and is async callable
  - _handle_by_tag uses build_tag_tree for hierarchical grouping
  - SPARQL query construction produces valid UNION query
  - Tag value escaping in tag_children query (prevent SPARQL injection)
  - Handler accepts label_service and icon_svc kwargs
  - tag_children accepts both `tag` and `prefix` parameters
"""

import inspect

import pytest

from app.browser.workspace import (
    EXPLORER_MODES,
    _handle_by_tag,
    _sparql_escape,
    tag_children,
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


class TestHandlerUsesBuildTagTree:
    """Verify _handle_by_tag uses build_tag_tree for hierarchical grouping."""

    def test_handler_imports_build_tag_tree(self):
        """The workspace module must import build_tag_tree."""
        from app.browser import workspace
        assert hasattr(workspace, 'build_tag_tree') or 'build_tag_tree' in dir(workspace)

    def test_handler_calls_build_tag_tree(self):
        """The handler source must reference build_tag_tree."""
        source = inspect.getsource(_handle_by_tag)
        assert "build_tag_tree" in source

    def test_handler_passes_nodes_to_template(self):
        """The handler must pass 'nodes' (not 'folders') to the template."""
        source = inspect.getsource(_handle_by_tag)
        assert '"nodes"' in source or "'nodes'" in source


class TestSparqlQueryConstruction:
    """Verify the SPARQL queries used by the by-tag explorer."""

    def test_by_tag_query_uses_union(self):
        """The main query must use UNION to combine bpkm:tags and schema:keywords."""
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
        source = inspect.getsource(tag_children)
        assert "_sparql_escape" in source


class TestTagChildrenQueryStructure:
    """Verify the tag_children SPARQL query structure."""

    def test_tag_children_uses_union(self):
        source = inspect.getsource(tag_children)
        assert "UNION" in source
        assert "urn:sempkm:model:basic-pkm:tags" in source
        assert "https://schema.org/keywords" in source

    def test_tag_children_resolves_labels(self):
        """tag_children query must include label resolution OPTIONALS."""
        source = inspect.getsource(tag_children)
        assert "_LABEL_OPTIONALS" in source
        assert "_LABEL_COALESCE" in source

    def test_tag_children_filters_rdfs_resource(self):
        """tag_children query must filter out rdfs:Resource type."""
        source = inspect.getsource(tag_children)
        assert "rdfs#Resource" in source or "Resource" in source


class TestTagChildrenPrefixParameter:
    """Verify tag_children supports the prefix parameter for sub-folder queries."""

    def test_tag_children_accepts_prefix_parameter(self):
        """The tag_children endpoint must accept a 'prefix' query parameter."""
        sig = inspect.signature(tag_children)
        assert "prefix" in sig.parameters

    def test_tag_children_prefix_has_default_none(self):
        """The prefix parameter defaults to None for backward compat."""
        sig = inspect.signature(tag_children)
        prefix_param = sig.parameters["prefix"]
        assert prefix_param.default is None

    def test_tag_children_still_accepts_tag(self):
        """The tag parameter must still exist for backward compatibility."""
        sig = inspect.signature(tag_children)
        assert "tag" in sig.parameters

    def test_tag_children_tag_has_default_none(self):
        """The tag parameter defaults to None (optional now)."""
        sig = inspect.signature(tag_children)
        tag_param = sig.parameters["tag"]
        assert tag_param.default is None

    def test_tag_children_prefix_uses_build_tag_tree(self):
        """The prefix code path must use build_tag_tree for grouping."""
        source = inspect.getsource(tag_children)
        assert "build_tag_tree" in source

    def test_tag_children_prefix_uses_strstarts(self):
        """The prefix SPARQL query must use STRSTARTS filter."""
        source = inspect.getsource(tag_children)
        assert "STRSTARTS" in source

    def test_tag_children_returns_folder_template_for_prefix(self):
        """The prefix code path must render tag_tree_folder.html."""
        source = inspect.getsource(tag_children)
        assert "tag_tree_folder.html" in source

    def test_tag_children_returns_objects_template_for_tag(self):
        """The tag code path must render tag_tree_objects.html."""
        source = inspect.getsource(tag_children)
        assert "tag_tree_objects.html" in source

    def test_tag_children_rejects_no_params(self):
        """When neither tag nor prefix is provided, must return 400."""
        source = inspect.getsource(tag_children)
        assert "400" in source
        assert "Missing required parameter" in source or "tag or prefix" in source
