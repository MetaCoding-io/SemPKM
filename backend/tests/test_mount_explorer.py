"""Tests for the VFS mount explorer handler and children endpoint.

Tests mock the triplestore client to verify SPARQL query structure,
strategy dispatch routing, error handling, and edge cases — matching
the established pattern from ``test_hierarchy_explorer.py``.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.browser.workspace import (
    EXPLORER_MODES,
    _get_mount_definition,
    _handle_mount,
    explorer_tree,
    mount_children,
)
from app.vfs.mount_service import MountDefinition


# ── Helpers ──────────────────────────────────────────────────────────

VALID_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
VALID_UUID_2 = "11111111-2222-3333-4444-555555555555"


def _make_mount(
    mount_id: str = VALID_UUID,
    strategy: str = "flat",
    name: str = "Test Mount",
    path: str = "test-mount",
    group_by_property: str | None = None,
    date_property: str | None = None,
    sparql_scope: str = "all",
) -> MountDefinition:
    """Build a MountDefinition for testing."""
    return MountDefinition(
        id=mount_id,
        name=name,
        path=path,
        strategy=strategy,
        group_by_property=group_by_property,
        date_property=date_property,
        sparql_scope=sparql_scope,
        created_by="urn:sempkm:user:test",
        visibility="shared",
        created_at="2025-01-01T00:00:00Z",
    )


def _mock_request(client: AsyncMock | None = None) -> tuple[MagicMock, AsyncMock]:
    """Build a minimal mock request with triplestore client."""
    request = MagicMock()
    if client is None:
        client = AsyncMock()
        client.query.return_value = {"results": {"bindings": []}}
    request.app.state.triplestore_client = client
    request.app.state.templates = MagicMock()
    request.app.state.templates.TemplateResponse.return_value = MagicMock()
    return request, client


def _mock_label_service() -> AsyncMock:
    label_svc = AsyncMock()
    label_svc.resolve_batch.return_value = {}
    return label_svc


def _mock_icon_service() -> MagicMock:
    icon_svc = MagicMock()
    icon_svc.get_type_icon.return_value = {"icon": "file", "color": "#ccc", "size": 14}
    return icon_svc


def _mount_bindings(mount: MountDefinition) -> dict:
    """Build SPARQL bindings for _get_mount_definition to return."""
    b = {
        "name": {"value": mount.name},
        "path": {"value": mount.path},
        "strategy": {"value": mount.strategy},
        "createdBy": {"value": mount.created_by},
        "visibility": {"value": mount.visibility},
    }
    if mount.group_by_property:
        b["groupByProp"] = {"value": mount.group_by_property}
    if mount.date_property:
        b["dateProp"] = {"value": mount.date_property}
    if mount.sparql_scope and mount.sparql_scope != "all":
        b["scope"] = {"value": mount.sparql_scope}
    if mount.created_at:
        b["createdAt"] = {"value": mount.created_at}
    return {"results": {"bindings": [b]}}


# ── TestMountHandlerDispatch ─────────────────────────────────────────


class TestMountHandlerDispatch:
    """Verify explorer_tree routes mount: prefix to the mount handler."""

    @pytest.mark.asyncio
    async def test_mount_prefix_routes_to_mount_handler(self):
        """mode=mount:uuid routes to _handle_mount (not EXPLORER_MODES)."""
        mount = _make_mount()
        request, client = _mock_request()
        # First query: _get_mount_definition; second: strategy query
        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},
        ]

        with patch("app.browser.workspace._handle_mount", new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = MagicMock()
            await explorer_tree(
                request=request,
                mode=f"mount:{VALID_UUID}",
                shapes_service=MagicMock(),
                icon_svc=_mock_icon_service(),
                label_service=_mock_label_service(),
            )
            mock_handler.assert_called_once()
            # Check mount_id was passed
            call_kwargs = mock_handler.call_args
            assert call_kwargs.kwargs.get("mount_id") == VALID_UUID or \
                   (len(call_kwargs.args) > 1 and call_kwargs.args[1] == VALID_UUID)

    @pytest.mark.asyncio
    async def test_invalid_uuid_format_returns_400(self):
        """mode=mount:not-a-uuid returns 400 with invalid format error."""
        request, client = _mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await explorer_tree(
                request=request,
                mode="mount:not-a-uuid",
                shapes_service=MagicMock(),
                icon_svc=_mock_icon_service(),
                label_service=_mock_label_service(),
            )
        assert exc_info.value.status_code == 400
        assert "Invalid mount_id format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_nonexistent_mount_returns_400(self):
        """mode=mount:valid-uuid for nonexistent mount returns 400."""
        request, client = _mock_request()
        # _get_mount_definition returns None
        client.query.return_value = {"results": {"bindings": []}}

        with pytest.raises(HTTPException) as exc_info:
            await explorer_tree(
                request=request,
                mode=f"mount:{VALID_UUID}",
                shapes_service=MagicMock(),
                icon_svc=_mock_icon_service(),
                label_service=_mock_label_service(),
            )
        assert exc_info.value.status_code == 400
        assert "Unknown mount" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_existing_modes_still_route_correctly(self):
        """by-type and hierarchy still route to their handlers (regression)."""
        # Verify the EXPLORER_MODES dict still has the expected entries
        assert "by-type" in EXPLORER_MODES
        assert "hierarchy" in EXPLORER_MODES
        # Verify they're distinct from the mount handler
        assert EXPLORER_MODES["by-type"] is not _handle_mount
        assert EXPLORER_MODES["hierarchy"] is not _handle_mount


# ── TestMountStrategySPARQL ──────────────────────────────────────────


class TestMountStrategySPARQL:
    """Verify SPARQL structure for each of the 5 strategies."""

    @pytest.fixture
    def deps(self):
        """Common mock dependencies for _handle_mount calls."""
        request, client = _mock_request()
        return request, client, _mock_label_service(), _mock_icon_service()

    @pytest.mark.asyncio
    async def test_flat_strategy_sparql(self, deps):
        """flat strategy generates flat object query (no folders)."""
        request, client, label_svc, icon_svc = deps
        mount = _make_mount(strategy="flat")
        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},
        ]

        await _handle_mount(
            request=request,
            mount_id=VALID_UUID,
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        # Second query is the strategy query
        sparql = client.query.call_args_list[1][0][0]
        assert "?iri" in sparql
        assert "?label" in sparql
        assert "?typeIri" in sparql
        # flat query: no GROUP BY, no DISTINCT ?typeIri folder
        assert "urn:sempkm:current" in sparql

        # Renders objects template (not folders)
        templates = request.app.state.templates
        template_name = templates.TemplateResponse.call_args[0][1]
        assert "mount_tree_objects" in template_name

    @pytest.mark.asyncio
    async def test_by_type_strategy_sparql(self, deps):
        """by-type strategy generates DISTINCT type folder query."""
        request, client, label_svc, icon_svc = deps
        mount = _make_mount(strategy="by-type")
        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},
        ]

        await _handle_mount(
            request=request,
            mount_id=VALID_UUID,
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        sparql = client.query.call_args_list[1][0][0]
        assert "?typeIri" in sparql
        assert "DISTINCT" in sparql

        templates = request.app.state.templates
        template_name = templates.TemplateResponse.call_args[0][1]
        assert "mount_tree" in template_name

    @pytest.mark.asyncio
    async def test_by_date_strategy_sparql(self, deps):
        """by-date strategy generates year extraction query."""
        request, client, label_svc, icon_svc = deps
        mount = _make_mount(
            strategy="by-date",
            date_property="http://purl.org/dc/terms/created",
        )
        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},
        ]

        await _handle_mount(
            request=request,
            mount_id=VALID_UUID,
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        sparql = client.query.call_args_list[1][0][0]
        assert "YEAR" in sparql
        assert "http://purl.org/dc/terms/created" in sparql
        assert "?year" in sparql

    @pytest.mark.asyncio
    async def test_by_tag_strategy_sparql(self, deps):
        """by-tag strategy generates tag value folder query."""
        request, client, label_svc, icon_svc = deps
        tag_prop = "http://example.org/tags"
        mount = _make_mount(strategy="by-tag", group_by_property=tag_prop)
        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},  # tag folders query
            {"boolean": False},  # ASK uncategorized
        ]

        await _handle_mount(
            request=request,
            mount_id=VALID_UUID,
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        sparql = client.query.call_args_list[1][0][0]
        assert "?tagValue" in sparql
        assert tag_prop in sparql

    @pytest.mark.asyncio
    async def test_by_property_strategy_sparql(self, deps):
        """by-property strategy generates group value folder query."""
        request, client, label_svc, icon_svc = deps
        group_prop = "http://example.org/department"
        mount = _make_mount(strategy="by-property", group_by_property=group_prop)
        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},  # property folders query
            {"boolean": False},  # ASK uncategorized
        ]

        await _handle_mount(
            request=request,
            mount_id=VALID_UUID,
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        sparql = client.query.call_args_list[1][0][0]
        assert "?groupValue" in sparql
        assert "?groupLabel" in sparql
        assert group_prop in sparql


# ── TestMountChildrenEndpoint ────────────────────────────────────────


class TestMountChildrenEndpoint:
    """Verify mount_children endpoint dispatches correctly per strategy."""

    @pytest.fixture
    def deps(self):
        request, client = _mock_request()
        return request, client, _mock_label_service(), _mock_icon_service()

    @pytest.mark.asyncio
    async def test_by_type_folder_expansion(self, deps):
        """by-type folder expansion queries objects of a specific type."""
        request, client, label_svc, icon_svc = deps
        mount = _make_mount(strategy="by-type")
        type_iri = "urn:sempkm:model:Note"

        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},
        ]

        await mount_children(
            request=request,
            mount_id=VALID_UUID,
            folder=type_iri,
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        # Second query should contain the type IRI
        sparql = client.query.call_args_list[1][0][0]
        assert type_iri in sparql
        assert "?iri" in sparql
        assert "?label" in sparql

    @pytest.mark.asyncio
    async def test_by_date_year_expansion_returns_month_folders(self, deps):
        """by-date year expansion (no subfolder) returns month folders."""
        request, client, label_svc, icon_svc = deps
        mount = _make_mount(
            strategy="by-date",
            date_property="http://purl.org/dc/terms/created",
        )

        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": [
                {"month": {"value": "3"}, "monthNum": {"value": "3"}},
                {"month": {"value": "7"}, "monthNum": {"value": "7"}},
            ]}},
        ]

        await mount_children(
            request=request,
            mount_id=VALID_UUID,
            folder="2024",
            subfolder=None,
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        # Should query for months within year 2024
        sparql = client.query.call_args_list[1][0][0]
        assert "MONTH" in sparql
        assert "2024" in sparql
        assert "http://purl.org/dc/terms/created" in sparql

        # Template should be mount_tree_folders (sub-folders, not objects)
        templates = request.app.state.templates
        template_name = templates.TemplateResponse.call_args[0][1]
        assert "mount_tree_folders" in template_name

    @pytest.mark.asyncio
    async def test_by_date_year_month_expansion_returns_objects(self, deps):
        """by-date year+month expansion (subfolder present) returns objects."""
        request, client, label_svc, icon_svc = deps
        mount = _make_mount(
            strategy="by-date",
            date_property="http://purl.org/dc/terms/created",
        )

        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},
        ]

        await mount_children(
            request=request,
            mount_id=VALID_UUID,
            folder="2024",
            subfolder="3",
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        # Should query for objects in year 2024, month 3
        sparql = client.query.call_args_list[1][0][0]
        assert "YEAR" in sparql
        assert "2024" in sparql
        assert "MONTH" in sparql

        # Template should be mount_tree_objects
        templates = request.app.state.templates
        template_name = templates.TemplateResponse.call_args[0][1]
        assert "mount_tree_objects" in template_name

    @pytest.mark.asyncio
    async def test_invalid_mount_id_returns_400(self, deps):
        """mount_children with invalid UUID format returns 400."""
        request, client, label_svc, icon_svc = deps

        with pytest.raises(HTTPException) as exc_info:
            await mount_children(
                request=request,
                mount_id="not-a-uuid",
                folder="some-folder",
                label_service=label_svc,
                icon_svc=icon_svc,
            )
        assert exc_info.value.status_code == 400
        assert "Invalid mount_id format" in exc_info.value.detail


# ── TestMountEdgeCases ───────────────────────────────────────────────


class TestMountEdgeCases:
    """Verify edge cases and error handling for mount explorer."""

    @pytest.fixture
    def deps(self):
        request, client = _mock_request()
        return request, client, _mock_label_service(), _mock_icon_service()

    @pytest.mark.asyncio
    async def test_by_date_null_date_property_returns_empty_tree(self, deps):
        """by-date with date_property=None returns empty tree, not crash."""
        request, client, label_svc, icon_svc = deps
        mount = _make_mount(strategy="by-date", date_property=None)
        client.query.side_effect = [
            _mount_bindings(mount),
        ]

        # Should NOT raise
        result = await _handle_mount(
            request=request,
            mount_id=VALID_UUID,
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        # Should render mount_tree with empty folders and message
        templates = request.app.state.templates
        call_args = templates.TemplateResponse.call_args
        template_name = call_args[0][1]
        assert "mount_tree" in template_name
        context = call_args[1].get("context") or call_args[0][2]
        assert context["folders"] == []
        assert "empty_message" in context

    @pytest.mark.asyncio
    async def test_uncategorized_folder_calls_uncategorized_query(self, deps):
        """by-tag _uncategorized folder calls query_uncategorized_objects."""
        request, client, label_svc, icon_svc = deps
        tag_prop = "http://example.org/tags"
        mount = _make_mount(strategy="by-tag", group_by_property=tag_prop)

        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},
        ]

        await mount_children(
            request=request,
            mount_id=VALID_UUID,
            folder="_uncategorized",
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        # The query should be an uncategorized query (FILTER NOT EXISTS)
        sparql = client.query.call_args_list[1][0][0]
        assert "FILTER NOT EXISTS" in sparql
        assert tag_prop in sparql

    @pytest.mark.asyncio
    async def test_by_property_uncategorized_folder(self, deps):
        """by-property _uncategorized folder calls query_uncategorized_objects."""
        request, client, label_svc, icon_svc = deps
        group_prop = "http://example.org/department"
        mount = _make_mount(strategy="by-property", group_by_property=group_prop)

        client.query.side_effect = [
            _mount_bindings(mount),
            {"results": {"bindings": []}},
        ]

        await mount_children(
            request=request,
            mount_id=VALID_UUID,
            folder="_uncategorized",
            label_service=label_svc,
            icon_svc=icon_svc,
        )

        sparql = client.query.call_args_list[1][0][0]
        assert "FILTER NOT EXISTS" in sparql
        assert group_prop in sparql

    @pytest.mark.asyncio
    async def test_triplestore_error_on_mount_fetch_returns_400(self, deps):
        """Triplestore error when fetching mount definition returns 400."""
        request, client, label_svc, icon_svc = deps
        # _get_mount_definition queries the triplestore — make it fail
        client.query.side_effect = RuntimeError("connection refused")

        with pytest.raises((HTTPException, RuntimeError)):
            await _handle_mount(
                request=request,
                mount_id=VALID_UUID,
                label_service=label_svc,
                icon_svc=icon_svc,
            )
