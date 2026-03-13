"""Tests for tag-splitting utilities.

Covers split_tag_values() for comma-separated string decomposition
and is_tag_property() for identifying tag-bearing RDF predicates.
These tests are written ahead of the implementation (T02) and are
expected to fail with ImportError until the functions exist.
"""

import pytest

from app.commands.handlers.object_patch import split_tag_values, is_tag_property


# --- split_tag_values ---

class TestSplitTagValues:
    """Unit tests for split_tag_values()."""

    def test_basic_comma_split(self):
        assert split_tag_values("a,b,c") == ["a", "b", "c"]

    def test_trims_whitespace(self):
        assert split_tag_values("a, b , c") == ["a", "b", "c"]

    def test_single_value_passthrough(self):
        assert split_tag_values("single") == ["single"]

    def test_empty_string_returns_empty_list(self):
        assert split_tag_values("") == []

    def test_skips_empty_segments(self):
        assert split_tag_values("a,,b") == ["a", "b"]

    def test_whitespace_only_returns_empty_list(self):
        assert split_tag_values("  ") == []

    def test_trailing_comma(self):
        assert split_tag_values("a,b,") == ["a", "b"]

    def test_leading_comma(self):
        assert split_tag_values(",a,b") == ["a", "b"]


# --- is_tag_property ---

class TestIsTagProperty:
    """Unit tests for is_tag_property()."""

    def test_bpkm_tags_is_tag_property(self):
        assert is_tag_property("urn:sempkm:model:basic-pkm:tags") is True

    def test_schema_keywords_is_tag_property(self):
        assert is_tag_property("https://schema.org/keywords") is True

    def test_dcterms_title_is_not_tag_property(self):
        assert is_tag_property("http://purl.org/dc/terms/title") is False

    def test_arbitrary_predicate_is_not_tag_property(self):
        assert is_tag_property("http://example.org/foo") is False
