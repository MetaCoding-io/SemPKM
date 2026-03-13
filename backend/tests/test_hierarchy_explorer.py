"""Tests for the hierarchy explorer mode — SPARQL query structure, handler
registration, and children endpoint validation.

These tests verify correctness without requiring a running triplestore.
They inspect query strings via mock capture, validate handler wiring,
and test IRI validation on the children endpoint.
"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.browser._helpers import _validate_iri
from app.browser.workspace import (
    EXPLORER_MODES,
    _handle_hierarchy,
    explorer_children,
)


# ── SPARQL query structure — root objects ────────────────────────────


class TestHierarchyRootSPARQL:
    """Verify the root-objects SPARQL query structure via mock capture."""

    @pytest.fixture
    def mock_request(self):
        """Build a minimal mock request with triplestore client."""
        request = MagicMock()
        client = AsyncMock()
        client.query.return_value = {"results": {"bindings": []}}
        request.app.state.triplestore_client = client
        request.app.state.templates = MagicMock()
        request.app.state.templates.TemplateResponse.return_value = MagicMock()
        return request, client

    @pytest.fixture
    def mock_label_service(self):
        label_svc = AsyncMock()
        label_svc.resolve_batch.return_value = {}
        return label_svc

    @pytest.fixture
    def mock_icon_service(self):
        icon_svc = MagicMock()
        icon_svc.get_type_icon.return_value = "file"
        return icon_svc

    @pytest.mark.asyncio
    async def test_root_query_uses_filter_not_exists(
        self, mock_request, mock_label_service, mock_icon_service
    ):
        """Root query must use FILTER NOT EXISTS for dcterms:isPartOf."""
        request, client = mock_request
        await _handle_hierarchy(
            request=request,
            label_service=mock_label_service,
            icon_svc=mock_icon_service,
        )
        sparql = client.query.call_args[0][0]
        assert "FILTER NOT EXISTS" in sparql
        assert "dcterms:isPartOf" in sparql

    @pytest.mark.asyncio
    async def test_root_query_scoped_to_current_graph(
        self, mock_request, mock_label_service, mock_icon_service
    ):
        """Root query must be scoped to GRAPH <urn:sempkm:current>."""
        request, client = mock_request
        await _handle_hierarchy(
            request=request,
            label_service=mock_label_service,
            icon_svc=mock_icon_service,
        )
        sparql = client.query.call_args[0][0]
        assert "GRAPH <urn:sempkm:current>" in sparql

    @pytest.mark.asyncio
    async def test_root_query_selects_obj_and_type(
        self, mock_request, mock_label_service, mock_icon_service
    ):
        """Root query must select ?obj and ?type for icon resolution."""
        request, client = mock_request
        await _handle_hierarchy(
            request=request,
            label_service=mock_label_service,
            icon_svc=mock_icon_service,
        )
        sparql = client.query.call_args[0][0]
        assert "?obj" in sparql
        assert "?type" in sparql

    @pytest.mark.asyncio
    async def test_root_query_renders_hierarchy_tree_template(
        self, mock_request, mock_label_service, mock_icon_service
    ):
        """Handler renders hierarchy_tree.html template."""
        request, client = mock_request
        templates = request.app.state.templates
        await _handle_hierarchy(
            request=request,
            label_service=mock_label_service,
            icon_svc=mock_icon_service,
        )
        template_name = templates.TemplateResponse.call_args[0][1]
        assert template_name == "browser/hierarchy_tree.html"

    @pytest.mark.asyncio
    async def test_root_query_deduplicates_objects(
        self, mock_request, mock_label_service, mock_icon_service
    ):
        """Objects with multiple types are de-duplicated (first type wins)."""
        request, client = mock_request
        client.query.return_value = {
            "results": {
                "bindings": [
                    {
                        "obj": {"value": "urn:sempkm:obj:1"},
                        "type": {"value": "urn:sempkm:model:Note"},
                    },
                    {
                        "obj": {"value": "urn:sempkm:obj:1"},
                        "type": {"value": "urn:sempkm:model:Document"},
                    },
                    {
                        "obj": {"value": "urn:sempkm:obj:2"},
                        "type": {"value": "urn:sempkm:model:Note"},
                    },
                ]
            }
        }
        templates = request.app.state.templates
        await _handle_hierarchy(
            request=request,
            label_service=mock_label_service,
            icon_svc=mock_icon_service,
        )
        ctx = templates.TemplateResponse.call_args[1].get("context")
        if ctx is None:
            # positional args: (request, template_name, context_dict)
            ctx = templates.TemplateResponse.call_args[0][2]
        objects = ctx["objects"]
        assert len(objects) == 2
        iris = [o["iri"] for o in objects]
        assert "urn:sempkm:obj:1" in iris
        assert "urn:sempkm:obj:2" in iris

    @pytest.mark.asyncio
    async def test_root_query_handles_triplestore_failure(
        self, mock_request, mock_label_service, mock_icon_service
    ):
        """SPARQL errors fall back to empty results, not exceptions."""
        request, client = mock_request
        client.query.side_effect = RuntimeError("connection refused")
        templates = request.app.state.templates
        await _handle_hierarchy(
            request=request,
            label_service=mock_label_service,
            icon_svc=mock_icon_service,
        )
        ctx = templates.TemplateResponse.call_args[1].get("context")
        if ctx is None:
            ctx = templates.TemplateResponse.call_args[0][2]
        assert ctx["objects"] == []


# ── SPARQL query structure — children ────────────────────────────────


class TestHierarchyChildrenSPARQL:
    """Verify the children SPARQL query structure via mock capture."""

    @pytest.fixture
    def mock_deps(self):
        """Build mock dependencies for explorer_children."""
        request = MagicMock()
        client = AsyncMock()
        client.query.return_value = {"results": {"bindings": []}}
        request.app.state.triplestore_client = client
        request.app.state.templates = MagicMock()
        request.app.state.templates.TemplateResponse.return_value = MagicMock()

        label_svc = AsyncMock()
        label_svc.resolve_batch.return_value = {}

        icon_svc = MagicMock()
        icon_svc.get_type_icon.return_value = "file"

        return request, client, label_svc, icon_svc

    @pytest.mark.asyncio
    async def test_children_query_contains_parent_iri(self, mock_deps):
        """Children query must reference the parent IRI in dcterms:isPartOf."""
        request, client, label_svc, icon_svc = mock_deps
        parent = "https://example.org/parent/1"
        await explorer_children(
            request=request,
            parent=parent,
            label_service=label_svc,
            icon_svc=icon_svc,
        )
        sparql = client.query.call_args[0][0]
        assert "dcterms:isPartOf" in sparql
        assert parent in sparql

    @pytest.mark.asyncio
    async def test_children_query_scoped_to_current_graph(self, mock_deps):
        """Children query must be scoped to GRAPH <urn:sempkm:current>."""
        request, client, label_svc, icon_svc = mock_deps
        parent = "https://example.org/parent/1"
        await explorer_children(
            request=request,
            parent=parent,
            label_service=label_svc,
            icon_svc=icon_svc,
        )
        sparql = client.query.call_args[0][0]
        assert "GRAPH <urn:sempkm:current>" in sparql

    @pytest.mark.asyncio
    async def test_children_query_renders_children_template(self, mock_deps):
        """Children endpoint renders hierarchy_children.html template."""
        request, client, label_svc, icon_svc = mock_deps
        parent = "https://example.org/parent/1"
        templates = request.app.state.templates
        await explorer_children(
            request=request,
            parent=parent,
            label_service=label_svc,
            icon_svc=icon_svc,
        )
        template_name = templates.TemplateResponse.call_args[0][1]
        assert template_name == "browser/hierarchy_children.html"


# ── Handler registration ────────────────────────────────────────────


class TestHierarchyHandlerRegistration:
    """Verify _handle_hierarchy is properly registered in EXPLORER_MODES."""

    def test_hierarchy_in_explorer_modes(self):
        """_handle_hierarchy is registered under key 'hierarchy'."""
        assert "hierarchy" in EXPLORER_MODES
        assert EXPLORER_MODES["hierarchy"] is _handle_hierarchy

    def test_handle_hierarchy_is_async(self):
        """_handle_hierarchy is an async (coroutine) function."""
        assert inspect.iscoroutinefunction(_handle_hierarchy)

    def test_handle_hierarchy_is_not_placeholder(self):
        """_handle_hierarchy does not render explorer_placeholder.html.

        Inspect the source to confirm it references hierarchy_tree.html
        rather than the generic placeholder template.
        """
        source = inspect.getsource(_handle_hierarchy)
        assert "explorer_placeholder.html" not in source
        assert "hierarchy_tree.html" in source


# ── Children endpoint IRI validation ────────────────────────────────


class TestChildrenEndpointValidation:
    """Verify that the children endpoint rejects invalid IRIs."""

    @pytest.mark.asyncio
    async def test_invalid_iri_raises_400(self):
        """Invalid parent IRI should raise HTTPException with status 400."""
        request = MagicMock()
        label_svc = AsyncMock()
        icon_svc = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await explorer_children(
                request=request,
                parent="not-a-valid-iri",
                label_service=label_svc,
                icon_svc=icon_svc,
            )
        assert exc_info.value.status_code == 400
        assert "Invalid IRI" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_empty_iri_raises_400(self):
        """Empty parent IRI should raise HTTPException with status 400."""
        request = MagicMock()
        label_svc = AsyncMock()
        icon_svc = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await explorer_children(
                request=request,
                parent="",
                label_service=label_svc,
                icon_svc=icon_svc,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_sparql_injection_iri_raises_400(self):
        """IRI with SPARQL injection characters must be rejected."""
        request = MagicMock()
        label_svc = AsyncMock()
        icon_svc = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await explorer_children(
                request=request,
                parent='https://example.org/obj"> ; DROP',
                label_service=label_svc,
                icon_svc=icon_svc,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_iri_does_not_raise(self):
        """Valid parent IRI should not raise — query proceeds."""
        request = MagicMock()
        client = AsyncMock()
        client.query.return_value = {"results": {"bindings": []}}
        request.app.state.triplestore_client = client
        request.app.state.templates = MagicMock()
        request.app.state.templates.TemplateResponse.return_value = MagicMock()

        label_svc = AsyncMock()
        label_svc.resolve_batch.return_value = {}
        icon_svc = MagicMock()

        # Should not raise
        await explorer_children(
            request=request,
            parent="https://example.org/parent/1",
            label_service=label_svc,
            icon_svc=icon_svc,
        )
        # Verify query was actually called
        assert client.query.called
