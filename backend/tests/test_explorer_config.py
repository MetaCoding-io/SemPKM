"""Unit tests for explorer config query composition engine and endpoints.

Tests that ``build_explorer_query`` and ``build_group_folders_query``
produce well-formed SPARQL for all configuration layer combinations.

Tests that the ``/explorer/config-tree`` and ``/explorer/config-children``
endpoints render the expected HTML structure.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.browser._helpers import get_icon_service
from app.browser.explorer_config import (
    ExplorerConfig,
    build_explorer_query,
    build_group_folders_query,
)
from app.browser.workspace import workspace_router
from app.dependencies import get_label_service


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

    def test_prop_prefix_stripped_from_group_by(self):
        """Frontend sends 'prop:' prefix for property IRIs — should be stripped."""
        cfg = ExplorerConfig(group_by="prop:urn:sempkm:model:basic-pkm:taskStatus")
        assert cfg.group_by == "urn:sempkm:model:basic-pkm:taskStatus"

    def test_prop_prefix_stripped_from_sort_by(self):
        """Frontend sends 'prop:' prefix for property IRIs — should be stripped."""
        cfg = ExplorerConfig(sort_by="prop:urn:sempkm:model:basic-pkm:dueDate")
        assert cfg.sort_by == "urn:sempkm:model:basic-pkm:dueDate"

    def test_builtin_group_by_not_stripped(self):
        """Built-in values like 'type' and 'tag' should not be affected."""
        cfg = ExplorerConfig(group_by="type")
        assert cfg.group_by == "type"

    def test_builtin_sort_by_not_stripped(self):
        """Built-in values like 'label' and 'created' should not be affected."""
        cfg = ExplorerConfig(sort_by="label")
        assert cfg.sort_by == "label"


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


# ── Endpoint tests ───────────────────────────────────────────────────


def _make_test_app() -> FastAPI:
    """Create a minimal FastAPI app mounting workspace_router with mocked deps."""
    from pathlib import Path

    from jinja2_fragments.fastapi import Jinja2Blocks

    app = FastAPI()

    templates_dir = Path(__file__).resolve().parent.parent / "app" / "templates"
    templates = Jinja2Blocks(directory=str(templates_dir))
    app.state.templates = templates

    # Mock triplestore client
    mock_client = AsyncMock()
    mock_client.query = AsyncMock(return_value={"results": {"bindings": []}})
    app.state.triplestore_client = mock_client

    # Mock auth — skip authentication
    mock_user = MagicMock()
    mock_user.id = "test-user"
    mock_user.role = "owner"
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Mock label service
    mock_label_svc = AsyncMock()
    mock_label_svc.resolve_batch = AsyncMock(return_value={})
    app.dependency_overrides[get_label_service] = lambda: mock_label_svc

    # Mock icon service
    mock_icon_svc = MagicMock()
    mock_icon_svc.get_type_icon = MagicMock(return_value={
        "icon": "circle",
        "color": "var(--color-text-faint)",
        "size": 14,
    })
    app.dependency_overrides[get_icon_service] = lambda: mock_icon_svc

    app.include_router(workspace_router)
    return app


class TestConfigTreeEndpoint:
    """Tests for GET /explorer/config-tree."""

    @pytest.fixture
    def app(self):
        return _make_test_app()

    async def test_config_tree_empty_returns_empty_state(self, app):
        """No objects → empty state message."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/explorer/config-tree")
        assert resp.status_code == 200
        assert "No objects match this configuration" in resp.text

    async def test_config_tree_flat_returns_objects(self, app):
        """Flat mode (no group_by) renders leaf nodes."""
        app.state.triplestore_client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {
                    "iri": {"value": "urn:test:obj1"},
                    "label": {"value": "Object One"},
                    "typeIri": {"value": "https://example.org/Task"},
                },
                {
                    "iri": {"value": "urn:test:obj2"},
                    "label": {"value": "Object Two"},
                    "typeIri": {"value": "https://example.org/Task"},
                },
            ]}
        })
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/explorer/config-tree?sort_by=label")
        assert resp.status_code == 200
        assert "Object One" in resp.text
        assert "Object Two" in resp.text
        assert 'data-testid="config-leaf"' in resp.text

    async def test_config_tree_grouped_returns_folders(self, app):
        """Grouped mode renders folder nodes with counts."""
        app.state.triplestore_client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {
                    "groupValue": {"value": "https://example.org/Task"},
                    "groupLabel": {"value": "Task"},
                    "count": {"value": "5"},
                },
                {
                    "groupValue": {"value": "https://example.org/Note"},
                    "groupLabel": {"value": "Note"},
                    "count": {"value": "3"},
                },
            ]}
        })
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/explorer/config-tree?group_by=type")
        assert resp.status_code == 200
        assert 'data-testid="config-folder"' in resp.text
        assert "Task" in resp.text
        assert "Note" in resp.text
        assert "5" in resp.text
        assert "3" in resp.text

    async def test_config_tree_forwards_params_to_children(self, app):
        """Folder nodes include config params in hx-get for children endpoint."""
        app.state.triplestore_client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {
                    "groupValue": {"value": "https://example.org/Task"},
                    "groupLabel": {"value": "Task"},
                    "count": {"value": "2"},
                },
            ]}
        })
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/explorer/config-tree?group_by=type&sort_by=created&sort_order=desc"
            )
        assert resp.status_code == 200
        # The hx-get should include forwarded config params
        assert "sort_by=created" in resp.text
        assert "sort_order=desc" in resp.text


class TestConfigChildrenEndpoint:
    """Tests for GET /explorer/config-children."""

    @pytest.fixture
    def app(self):
        return _make_test_app()

    async def test_config_children_returns_filtered_objects(self, app):
        """Returns only objects matching the requested group_value."""
        app.state.triplestore_client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {
                    "iri": {"value": "urn:test:task1"},
                    "label": {"value": "Task Alpha"},
                    "typeIri": {"value": "https://example.org/Task"},
                    "groupValue": {"value": "active"},
                },
                {
                    "iri": {"value": "urn:test:task2"},
                    "label": {"value": "Task Beta"},
                    "typeIri": {"value": "https://example.org/Task"},
                    "groupValue": {"value": "done"},
                },
                {
                    "iri": {"value": "urn:test:task3"},
                    "label": {"value": "Task Gamma"},
                    "typeIri": {"value": "https://example.org/Task"},
                    "groupValue": {"value": "active"},
                },
            ]}
        })
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/explorer/config-children?group_value=active"
                "&group_by=https%3A%2F%2Fexample.org%2Fstatus"
            )
        assert resp.status_code == 200
        assert "Task Alpha" in resp.text
        assert "Task Gamma" in resp.text
        assert "Task Beta" not in resp.text
        assert 'data-testid="config-child"' in resp.text

    async def test_config_children_empty_group(self, app):
        """Empty group returns 'No objects in this group'."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/explorer/config-children?group_value=nonexistent&group_by=type"
            )
        assert resp.status_code == 200
        assert "No objects in this group" in resp.text
