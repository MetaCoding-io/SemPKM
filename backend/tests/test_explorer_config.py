"""Unit tests for explorer config query composition engine.

Tests that ``build_explorer_query`` and ``build_group_folders_query``
produce well-formed SPARQL for all configuration layer combinations.
"""

import pytest

from app.browser.explorer_config import (
    ExplorerConfig,
    build_explorer_query,
    build_group_folders_query,
)


# ── ExplorerConfig defaults ─────────────────────────────────────────


class TestExplorerConfigDefaults:
    def test_defaults(self):
        cfg = ExplorerConfig()
        assert cfg.type_filter is None
        assert cfg.group_by is None
        assert cfg.sort_by == "label"
        assert cfg.sort_order == "asc"

    def test_invalid_sort_order_normalised(self):
        cfg = ExplorerConfig(sort_order="backwards")
        assert cfg.sort_order == "asc"


# ── build_explorer_query ─────────────────────────────────────────────


class TestBuildExplorerQuery:
    """Tests for the main explorer query composition."""

    def test_no_config_returns_all_objects_sorted_by_label(self):
        """Empty config → all objects, sorted by label ascending."""
        cfg = ExplorerConfig()
        sparql = build_explorer_query(cfg)

        assert "SELECT ?iri ?label ?typeIri ?groupValue ?groupLabel ?sortValue" in sparql
        assert "FROM <urn:sempkm:current>" in sparql
        assert "?iri a ?typeIri ." in sparql
        assert "ORDER BY ?label" in sparql
        # Should have label resolution COALESCE
        assert "COALESCE(?t, ?r, ?s, ?sn, ?f" in sparql
        # Should filter out rdfs:Resource
        assert "FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)" in sparql
        # No type constraint beyond base pattern
        assert sparql.count("?iri a") == 1  # only the base pattern

    def test_type_filter_only(self):
        """Type filter → adds ?iri a <type> constraint."""
        cfg = ExplorerConfig(type_filter="https://example.org/Task")
        sparql = build_explorer_query(cfg)

        assert "<https://example.org/Task>" in sparql
        # Two ?iri a patterns: base + filter
        assert sparql.count("?iri a") == 2

    def test_group_by_type(self):
        """group_by='type' → binds groupValue to typeIri."""
        cfg = ExplorerConfig(group_by="type")
        sparql = build_explorer_query(cfg)

        assert "BIND(?typeIri AS ?groupValue)" in sparql
        assert "?groupLabel" in sparql

    def test_group_by_tag(self):
        """group_by='tag' → produces UNION across tag predicates."""
        cfg = ExplorerConfig(group_by="tag")
        sparql = build_explorer_query(cfg)

        assert "UNION" in sparql
        assert "urn:sempkm:vocab:basic-pkm:tags" in sparql
        assert "https://schema.org/keywords" in sparql

    def test_group_by_property_iri(self):
        """group_by=property IRI → OPTIONAL bind on that property."""
        cfg = ExplorerConfig(group_by="https://example.org/status")
        sparql = build_explorer_query(cfg)

        assert "<https://example.org/status>" in sparql
        assert "OPTIONAL" in sparql
        assert "?groupValue" in sparql
        assert "?groupLabel" in sparql

    def test_sort_by_label_asc(self):
        """sort_by='label' + asc → ORDER BY ?label."""
        cfg = ExplorerConfig(sort_by="label", sort_order="asc")
        sparql = build_explorer_query(cfg)

        assert "ORDER BY ?label" in sparql
        assert "DESC" not in sparql.split("ORDER BY")[1]

    def test_sort_by_label_desc(self):
        """sort_by='label' + desc → ORDER BY DESC(?label)."""
        cfg = ExplorerConfig(sort_by="label", sort_order="desc")
        sparql = build_explorer_query(cfg)

        assert "ORDER BY DESC(?label)" in sparql

    def test_sort_by_created_asc(self):
        """sort_by='created' + asc → binds sortValue, ORDER BY ?sortValue."""
        cfg = ExplorerConfig(sort_by="created", sort_order="asc")
        sparql = build_explorer_query(cfg)

        assert "dcterms:created" in sparql or "dc/terms/created" in sparql
        assert "?sortValue" in sparql
        assert "ORDER BY ?sortValue" in sparql

    def test_sort_by_created_desc(self):
        """sort_by='created' + desc → ORDER BY DESC(?sortValue)."""
        cfg = ExplorerConfig(sort_by="created", sort_order="desc")
        sparql = build_explorer_query(cfg)

        assert "ORDER BY DESC(?sortValue)" in sparql

    def test_sort_by_property_iri(self):
        """sort_by=property IRI → OPTIONAL bind, ORDER BY ?sortValue."""
        cfg = ExplorerConfig(sort_by="https://example.org/dueDate")
        sparql = build_explorer_query(cfg)

        assert "<https://example.org/dueDate>" in sparql
        assert "?sortValue" in sparql
        assert "ORDER BY ?sortValue" in sparql

    def test_combined_filter_group_sort(self):
        """All three layers compose correctly in a single query."""
        cfg = ExplorerConfig(
            type_filter="https://example.org/Task",
            group_by="https://example.org/status",
            sort_by="created",
            sort_order="desc",
        )
        sparql = build_explorer_query(cfg)

        # Filter
        assert "<https://example.org/Task>" in sparql
        # Group
        assert "<https://example.org/status>" in sparql
        assert "?groupValue" in sparql
        assert "?groupLabel" in sparql
        # Sort
        assert "?sortValue" in sparql
        assert "ORDER BY DESC(?sortValue)" in sparql
        # Always present
        assert "FROM <urn:sempkm:current>" in sparql
        assert "FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)" in sparql

    def test_group_by_type_with_type_filter(self):
        """Type filter + group_by='type' compose (filter narrows, group still binds)."""
        cfg = ExplorerConfig(
            type_filter="https://example.org/Task",
            group_by="type",
        )
        sparql = build_explorer_query(cfg)

        assert "<https://example.org/Task>" in sparql
        assert "BIND(?typeIri AS ?groupValue)" in sparql


# ── build_group_folders_query ────────────────────────────────────────


class TestBuildGroupFoldersQuery:
    """Tests for the folder-level group query."""

    def test_no_grouping_returns_none(self):
        """No group_by → returns None."""
        cfg = ExplorerConfig()
        assert build_group_folders_query(cfg) is None

    def test_group_by_type(self):
        """group_by='type' → distinct types with counts."""
        cfg = ExplorerConfig(group_by="type")
        sparql = build_group_folders_query(cfg)

        assert sparql is not None
        assert "COUNT(DISTINCT ?iri)" in sparql
        assert "GROUP BY ?groupValue ?groupLabel" in sparql
        assert "ORDER BY ?groupLabel" in sparql
        assert "BIND(?typeIri AS ?groupValue)" in sparql

    def test_group_by_tag(self):
        """group_by='tag' → distinct tag values with counts."""
        cfg = ExplorerConfig(group_by="tag")
        sparql = build_group_folders_query(cfg)

        assert sparql is not None
        assert "UNION" in sparql
        assert "COUNT(DISTINCT ?iri)" in sparql

    def test_group_by_property_iri(self):
        """group_by=property IRI → distinct property values with counts."""
        cfg = ExplorerConfig(group_by="https://example.org/priority")
        sparql = build_group_folders_query(cfg)

        assert sparql is not None
        assert "<https://example.org/priority>" in sparql
        assert "COUNT(DISTINCT ?iri)" in sparql
        assert "GROUP BY" in sparql

    def test_group_folders_with_type_filter(self):
        """Type filter narrows the group folders query."""
        cfg = ExplorerConfig(
            type_filter="https://example.org/Task",
            group_by="type",
        )
        sparql = build_group_folders_query(cfg)

        assert sparql is not None
        assert "<https://example.org/Task>" in sparql
        assert "COUNT(DISTINCT ?iri)" in sparql

    def test_group_folders_filters_rdfs_resource(self):
        """Group folders query filters out rdfs:Resource."""
        cfg = ExplorerConfig(group_by="type")
        sparql = build_group_folders_query(cfg)

        assert "FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)" in sparql
