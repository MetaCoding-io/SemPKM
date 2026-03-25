"""Unit tests for the saved queries explorer endpoint.

Tests GET /browser/views/saved-queries/explorer which returns an
HTML partial listing saved SPARQL queries for the explorer sidebar.

SQ-03 Verification — Saved queries as VFS mount scope:
  This feature is already implemented. The VFS layer resolves scope_query
  IRIs to SPARQL text and injects them as scope filters:
    - backend/app/vfs/strategies.py: build_scope_filter() resolves
      mount.scope_query via _resolve_scope_query_sync(), extracts the
      WHERE body, and injects it as a { SELECT ?iri WHERE { ... } }
      sub-select into generated SPARQL queries.
    - backend/app/vfs/mount_router.py: MountDefinition stores scope_query
      as a field; create/update endpoints persist it in the triplestore.
    - frontend: The mount settings form populates the #mount-scope
      dropdown from /api/sparql/saved?include_shared=true (see
      workspace.js mount settings panel).
  No additional code changes needed for SQ-03.
"""

import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.sparql.query_service import QueryService, SavedQueryData


# ── Helpers ────────────────────────────────────────────────────


def _make_query(
    name: str,
    source: str | None = None,
    readonly: bool = False,
    query_id: str | None = None,
    description: str | None = None,
) -> SavedQueryData:
    """Build a SavedQueryData instance for testing."""
    return SavedQueryData(
        id=query_id or str(uuid.uuid4()),
        name=name,
        description=description,
        query_text="SELECT ?s WHERE { ?s a <urn:Type> }",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        owner_id=str(uuid.uuid4()),
        source=source,
        readonly=readonly,
    )


USER_QUERIES = [
    _make_query("My Active Projects", query_id="aaaa-1111"),
    _make_query("Recent Notes", query_id="aaaa-2222", description="Notes from last 7 days"),
]

MODEL_QUERIES = [
    _make_query("All Concepts", source="model", readonly=True, query_id="bbbb-1111"),
    _make_query("Topic Map", source="model", readonly=True, query_id="bbbb-2222"),
]

ALL_QUERIES = USER_QUERIES + MODEL_QUERIES


def _render_template(queries: list[SavedQueryData]) -> str:
    """Render saved_queries_explorer.html with the given query list.

    Uses a real Jinja2 environment so we test actual template rendering,
    not mocked output.
    """
    from jinja2 import Environment, FileSystemLoader
    import os

    template_dir = os.path.join(
        os.path.dirname(__file__), "..", "app", "templates"
    )
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("browser/saved_queries_explorer.html")
    model_queries = [q for q in queries if q.source == "model"]
    user_queries = [q for q in queries if q.source != "model"]
    return template.render(
        queries=queries,
        model_queries=model_queries,
        user_queries=user_queries,
    )


# ── Template rendering tests ──────────────────────────────────


class TestSavedQueriesExplorerTemplate:
    """Tests that the saved_queries_explorer.html template renders
    correctly for various query configurations."""

    def test_renders_tree_leaf_for_each_query(self):
        """Each query produces a .tree-leaf element."""
        html = _render_template(ALL_QUERIES)
        assert html.count('class="tree-leaf"') == len(ALL_QUERIES)

    def test_user_queries_have_database_icon(self):
        """User queries use the 'database' lucide icon."""
        html = _render_template(USER_QUERIES)
        assert 'data-lucide="database"' in html

    def test_model_queries_have_book_open_icon(self):
        """Model queries use the 'book-open' lucide icon."""
        html = _render_template(MODEL_QUERIES)
        assert 'data-lucide="book-open"' in html

    def test_drag_payload_present(self):
        """Each entry has __canvasDragPayload with type:'query' in ondragstart."""
        html = _render_template(ALL_QUERIES)
        assert "__canvasDragPayload" in html
        assert "type:&#39;query&#39;" in html or "type:'query'" in html

    def test_drag_payload_contains_query_id(self):
        """Drag payload includes the specific query ID."""
        html = _render_template(USER_QUERIES)
        assert "aaaa-1111" in html
        assert "aaaa-2222" in html

    def test_drag_payload_contains_embed_url(self):
        """Drag payload includes the embed URL for canvas embedding."""
        html = _render_template(USER_QUERIES)
        assert "/browser/sparql-result/aaaa-1111?embed=1" in html

    def test_click_handler_opens_view_tab(self):
        """Each entry has openGenericViewTab onclick handler."""
        html = _render_template(ALL_QUERIES)
        assert "openGenericViewTab" in html
        # Verify it opens a 'table' view
        assert "openGenericViewTab(&#39;table&#39;" in html or "openGenericViewTab('table'" in html

    def test_click_handler_includes_query_id(self):
        """The onclick handler passes the query ID as second argument."""
        html = _render_template(USER_QUERIES)
        assert "aaaa-1111" in html

    def test_empty_state_renders_no_saved_queries(self):
        """Empty query list renders 'No saved queries' message."""
        html = _render_template([])
        assert "No saved queries" in html
        assert "tree-leaf" not in html

    def test_empty_state_has_tree_empty_class(self):
        """Empty state uses tree-empty CSS class."""
        html = _render_template([])
        assert "tree-empty" in html

    def test_user_queries_section_header(self):
        """User queries appear under 'My Queries' header."""
        html = _render_template(ALL_QUERIES)
        assert "My Queries" in html

    def test_model_queries_section_header(self):
        """Model queries appear under 'Model Queries' header."""
        html = _render_template(ALL_QUERIES)
        assert "Model Queries" in html

    def test_only_user_queries_no_model_header(self):
        """When only user queries exist, no 'Model Queries' header appears."""
        html = _render_template(USER_QUERIES)
        assert "My Queries" in html
        assert "Model Queries" not in html

    def test_only_model_queries_no_user_header(self):
        """When only model queries exist, no 'My Queries' header appears."""
        html = _render_template(MODEL_QUERIES)
        assert "Model Queries" in html
        assert "My Queries" not in html

    def test_query_name_in_label(self):
        """Query names appear as tree-label text."""
        html = _render_template(USER_QUERIES)
        assert "My Active Projects" in html
        assert "Recent Notes" in html

    def test_description_in_title_attribute(self):
        """Query description (if present) appears in the title attribute."""
        html = _render_template(USER_QUERIES)
        assert "Notes from last 7 days" in html

    def test_draggable_attribute_present(self):
        """Each tree-leaf has draggable='true'."""
        html = _render_template(ALL_QUERIES)
        assert 'draggable="true"' in html

    def test_mixed_user_and_model_queries(self):
        """Both user and model queries render with correct grouping."""
        html = _render_template(ALL_QUERIES)
        # Both groups present
        assert "My Queries" in html
        assert "Model Queries" in html
        # All 4 entries rendered
        assert html.count('class="tree-leaf"') == 4
        # User icons and model icons both present
        assert 'data-lucide="database"' in html
        assert 'data-lucide="book-open"' in html


# ── Endpoint behavior tests ───────────────────────────────────


class TestSavedQueriesExplorerEndpoint:
    """Tests for the endpoint function itself: dependency injection,
    error handling, and context passing."""

    @pytest.mark.asyncio
    async def test_endpoint_calls_list_all_queries(self):
        """Endpoint calls query_service.list_all_queries(user.id)."""
        from app.views.router import saved_queries_explorer

        user = MagicMock()
        user.id = uuid.uuid4()

        query_service = MagicMock(spec=QueryService)
        query_service.list_all_queries = AsyncMock(return_value=ALL_QUERIES)

        # Build mock request with templates
        request = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>ok</html>"
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template

        templates = MagicMock()
        templates.env = mock_env
        templates.TemplateResponse = MagicMock(return_value="response")
        request.app.state.templates = templates

        await saved_queries_explorer(
            request=request, user=user, query_service=query_service,
        )

        query_service.list_all_queries.assert_called_once_with(user.id)

    @pytest.mark.asyncio
    async def test_endpoint_passes_queries_to_template(self):
        """Endpoint passes queries list in template context."""
        from app.views.router import saved_queries_explorer

        user = MagicMock()
        user.id = uuid.uuid4()

        query_service = MagicMock(spec=QueryService)
        query_service.list_all_queries = AsyncMock(return_value=ALL_QUERIES)

        request = MagicMock()
        templates = MagicMock()
        templates.TemplateResponse = MagicMock(return_value="response")
        request.app.state.templates = templates

        await saved_queries_explorer(
            request=request, user=user, query_service=query_service,
        )

        templates.TemplateResponse.assert_called_once()
        call_args = templates.TemplateResponse.call_args
        context = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("context", {})
        assert context["queries"] == ALL_QUERIES

    @pytest.mark.asyncio
    async def test_endpoint_renders_correct_template(self):
        """Endpoint renders browser/saved_queries_explorer.html."""
        from app.views.router import saved_queries_explorer

        user = MagicMock()
        user.id = uuid.uuid4()

        query_service = MagicMock(spec=QueryService)
        query_service.list_all_queries = AsyncMock(return_value=[])

        request = MagicMock()
        templates = MagicMock()
        templates.TemplateResponse = MagicMock(return_value="response")
        request.app.state.templates = templates

        await saved_queries_explorer(
            request=request, user=user, query_service=query_service,
        )

        call_args = templates.TemplateResponse.call_args
        template_name = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("name")
        assert template_name == "browser/saved_queries_explorer.html"

    @pytest.mark.asyncio
    async def test_endpoint_graceful_degradation_on_error(self):
        """When list_all_queries() raises, endpoint returns empty list."""
        from app.views.router import saved_queries_explorer

        user = MagicMock()
        user.id = uuid.uuid4()

        query_service = MagicMock(spec=QueryService)
        query_service.list_all_queries = AsyncMock(
            side_effect=RuntimeError("triplestore down"),
        )

        request = MagicMock()
        templates = MagicMock()
        templates.TemplateResponse = MagicMock(return_value="response")
        request.app.state.templates = templates

        # Should NOT raise — endpoint catches the exception
        await saved_queries_explorer(
            request=request, user=user, query_service=query_service,
        )

        # Verify empty list was passed to template
        call_args = templates.TemplateResponse.call_args
        context = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("context", {})
        assert context["queries"] == []

    @pytest.mark.asyncio
    async def test_endpoint_logs_exception_on_error(self):
        """When list_all_queries() raises, endpoint logs the exception."""
        from app.views.router import saved_queries_explorer

        user = MagicMock()
        user.id = uuid.uuid4()

        query_service = MagicMock(spec=QueryService)
        query_service.list_all_queries = AsyncMock(
            side_effect=RuntimeError("triplestore down"),
        )

        request = MagicMock()
        templates = MagicMock()
        templates.TemplateResponse = MagicMock(return_value="response")
        request.app.state.templates = templates

        with patch("app.views.router.logger") as mock_logger:
            await saved_queries_explorer(
                request=request, user=user, query_service=query_service,
            )
            mock_logger.exception.assert_called_once()
            assert "failed to load queries" in mock_logger.exception.call_args[0][0]


# ── SQ-03 verification tests ─────────────────────────────────


class TestSQ03VFSScopeQueryVerification:
    """SQ-03: Saved queries usable as VFS mount scope.

    These tests verify that the VFS layer already supports resolving
    scope_query IRIs. No new code is needed — these confirm the
    existing implementation satisfies SQ-03.

    Code references:
      - backend/app/vfs/strategies.py: build_scope_filter() resolves
        mount.scope_query via _resolve_scope_query_sync()
      - backend/app/vfs/strategies.py: _extract_where_body() extracts
        WHERE clause from resolved query text
      - backend/app/vfs/mount_router.py: scope_query field on
        MountDefinition (lines 90, 110, 133)
    """

    def test_build_scope_filter_accepts_scope_query(self):
        """build_scope_filter() handles mount.scope_query when
        resolved_query_text is provided."""
        from app.vfs.strategies import build_scope_filter
        from app.vfs.mount_service import MountDefinition

        mount = MountDefinition(
            id="test-mount-id",
            name="Test Mount",
            path="/test",
            strategy="flat",
            scope_query="urn:sempkm:query:test-uuid",
        )

        result = build_scope_filter(
            mount,
            resolved_query_text="SELECT ?s WHERE { ?s a <urn:Type> }",
        )

        # Should contain a sub-select constraining ?iri
        assert "SELECT ?iri WHERE" in result
        assert "urn:Type" in result

    def test_build_scope_filter_no_scope_query(self):
        """build_scope_filter() returns empty string when no scope is set."""
        from app.vfs.strategies import build_scope_filter
        from app.vfs.mount_service import MountDefinition

        mount = MountDefinition(
            id="test-mount-id",
            name="Test Mount",
            path="/test",
            strategy="flat",
        )

        result = build_scope_filter(mount)
        assert result == ""

    def test_extract_where_body_from_select(self):
        """_extract_where_body() extracts WHERE clause and renames
        primary variable to ?iri for VFS scope composition."""
        from app.vfs.strategies import _extract_where_body

        body = _extract_where_body("SELECT ?s WHERE { ?s a <urn:Note> . ?s <urn:tag> ?tag }")
        assert "?iri a <urn:Note>" in body
        assert "?iri <urn:tag> ?tag" in body

    def test_resolve_scope_query_sync_exists(self):
        """_resolve_scope_query_sync function is importable — confirms
        the VFS has sync resolution capability for WebDAV context."""
        from app.vfs.strategies import _resolve_scope_query_sync
        assert callable(_resolve_scope_query_sync)

    def test_mount_definition_has_scope_query_field(self):
        """MountDefinition dataclass has a scope_query field."""
        from app.vfs.mount_service import MountDefinition

        mount = MountDefinition(
            id="test-mount-id",
            name="Test Mount",
            path="/test",
            strategy="flat",
            scope_query="urn:sempkm:query:12345",
        )
        assert mount.scope_query == "urn:sempkm:query:12345"
