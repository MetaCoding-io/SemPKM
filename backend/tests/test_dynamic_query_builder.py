"""Unit tests for the dynamic query builder and generic view registration.

Tests ViewSpecService.build_dynamic_query(), get_generic_columns(),
register_generic_views(), and get_generic_spec() using a mocked ShapesService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.shapes import NodeShapeForm, PropertyShape, ShapesService
from app.views.service import ViewSpecService, _var_name_from_iri


# ── Fixtures ───────────────────────────────────────────────────


def _make_property(path: str, name: str, order: float = 0.0) -> PropertyShape:
    """Create a PropertyShape with minimal fields for testing."""
    return PropertyShape(path=path, name=name, order=order)


def _make_form(
    target_class: str,
    properties: list[PropertyShape],
    label: str = "Test Shape",
) -> NodeShapeForm:
    return NodeShapeForm(
        shape_iri=f"urn:test:{label.lower().replace(' ', '-')}",
        target_class=target_class,
        label=label,
        properties=properties,
    )


def _build_service(
    form_return: NodeShapeForm | None = None,
    form_side_effect: Exception | None = None,
) -> ViewSpecService:
    """Build a ViewSpecService with a mocked ShapesService."""
    shapes = MagicMock(spec=ShapesService)
    if form_side_effect:
        shapes.get_form_for_type = AsyncMock(side_effect=form_side_effect)
    else:
        shapes.get_form_for_type = AsyncMock(return_value=form_return)

    client = MagicMock()
    label_service = MagicMock()

    svc = ViewSpecService(
        client=client,
        label_service=label_service,
        shapes_service=shapes,
    )
    return svc


# ── register_generic_views / get_generic_spec ──────────────────


class TestGenericViewRegistration:
    def test_register_creates_three_specs(self):
        svc = _build_service()
        svc.register_generic_views()
        assert len(svc._generic_specs) == 3

    def test_register_correct_iris(self):
        svc = _build_service()
        svc.register_generic_views()
        iris = {s.spec_iri for s in svc._generic_specs}
        assert iris == {
            "urn:sempkm:view:generic-table",
            "urn:sempkm:view:generic-card",
            "urn:sempkm:view:generic-graph",
        }

    def test_register_correct_renderer_types(self):
        svc = _build_service()
        svc.register_generic_views()
        types = {s.renderer_type for s in svc._generic_specs}
        assert types == {"table", "card", "graph"}

    def test_register_source_model_is_system(self):
        svc = _build_service()
        svc.register_generic_views()
        for spec in svc._generic_specs:
            assert spec.source_model == "system"

    def test_get_generic_spec_valid(self):
        svc = _build_service()
        svc.register_generic_views()
        spec = svc.get_generic_spec("table")
        assert spec is not None
        assert spec.renderer_type == "table"

    def test_get_generic_spec_invalid(self):
        svc = _build_service()
        svc.register_generic_views()
        assert svc.get_generic_spec("timeline") is None

    def test_get_generic_spec_before_registration(self):
        svc = _build_service()
        assert svc.get_generic_spec("table") is None


# ── get_generic_columns ────────────────────────────────────────


class TestGetGenericColumns:
    @pytest.mark.asyncio
    async def test_no_type_returns_defaults(self):
        svc = _build_service()
        shapes, cols = await svc.get_generic_columns(None)
        assert shapes == []
        assert cols == ["label", "type", "created", "modified"]

    @pytest.mark.asyncio
    async def test_empty_type_returns_defaults(self):
        svc = _build_service()
        shapes, cols = await svc.get_generic_columns("")
        assert shapes == []
        assert cols == ["label", "type", "created", "modified"]

    @pytest.mark.asyncio
    async def test_type_not_found_returns_defaults(self):
        svc = _build_service(form_return=None)
        shapes, cols = await svc.get_generic_columns("http://example.org/Missing")
        assert shapes == []
        assert cols == ["label", "type", "created", "modified"]

    @pytest.mark.asyncio
    async def test_sparse_shape_returns_defaults(self):
        """≤2 properties should fall back to defaults."""
        form = _make_form("http://example.org/Sparse", [
            _make_property("http://example.org/title", "Title", 1.0),
            _make_property("http://example.org/desc", "Description", 2.0),
        ])
        svc = _build_service(form_return=form)
        shapes, cols = await svc.get_generic_columns("http://example.org/Sparse")
        assert shapes == []
        assert cols == ["label", "type", "created", "modified"]

    @pytest.mark.asyncio
    async def test_rich_shape_returns_shacl_columns(self):
        """≥3 properties should return SHACL-derived columns."""
        form = _make_form("http://example.org/Note", [
            _make_property("http://example.org/title", "Title", 1.0),
            _make_property("http://example.org/body", "Body", 2.0),
            _make_property("http://example.org/status", "Status", 3.0),
        ])
        svc = _build_service(form_return=form)
        shapes, cols = await svc.get_generic_columns("http://example.org/Note")
        assert len(shapes) == 3
        assert cols == ["title", "body", "status"]

    @pytest.mark.asyncio
    async def test_column_order_stability(self):
        """Two calls with the same type should return the same column order."""
        form = _make_form("http://example.org/Note", [
            _make_property("http://example.org/z_field", "Z Field", 2.0),
            _make_property("http://example.org/a_field", "A Field", 1.0),
            _make_property("http://example.org/m_field", "M Field", 1.0),
        ])
        svc = _build_service(form_return=form)
        _, cols1 = await svc.get_generic_columns("http://example.org/Note")
        _, cols2 = await svc.get_generic_columns("http://example.org/Note")
        assert cols1 == cols2
        # order=1.0 has two: sorted by name → A Field, M Field, then order=2.0 → Z Field
        assert cols1 == ["a_field", "m_field", "z_field"]

    @pytest.mark.asyncio
    async def test_shapes_service_exception_returns_defaults(self):
        """If ShapesService throws, gracefully degrade to defaults."""
        svc = _build_service(form_side_effect=RuntimeError("triplestore down"))
        shapes, cols = await svc.get_generic_columns("http://example.org/Note")
        assert shapes == []
        assert cols == ["label", "type", "created", "modified"]


# ── Variable name helpers ──────────────────────────────────────


class TestVarNameFromIRI:
    def test_simple_fragment(self):
        assert _var_name_from_iri("http://example.org/vocab#title") == "title"

    def test_simple_slash(self):
        assert _var_name_from_iri("http://example.org/title") == "title"

    def test_special_chars_sanitized(self):
        assert _var_name_from_iri("http://example.org/has-body.text") == "has_body_text"

    def test_leading_digits_stripped(self):
        assert _var_name_from_iri("http://example.org/123field") == "field"

    def test_all_digits_fallback(self):
        assert _var_name_from_iri("http://example.org/123") == "v"

    def test_colon_delimited(self):
        assert _var_name_from_iri("urn:sempkm:myProp") == "myProp"


class TestVariableDeduplication:
    @pytest.mark.asyncio
    async def test_duplicate_local_names_get_suffix(self):
        """Two properties with the same local name should get _2 suffix."""
        form = _make_form("http://example.org/Thing", [
            _make_property("http://vocab-a.org/name", "Name A", 1.0),
            _make_property("http://vocab-b.org/name", "Name B", 2.0),
            _make_property("http://vocab-c.org/other", "Other", 3.0),
        ])
        svc = _build_service(form_return=form)
        _, cols = await svc.get_generic_columns("http://example.org/Thing")
        assert cols == ["name", "name_2", "other"]


# ── build_dynamic_query ────────────────────────────────────────


class TestBuildDynamicQuery:
    @pytest.mark.asyncio
    async def test_all_types_default_columns(self):
        """No type → default columns, no type filter."""
        svc = _build_service()
        query, cols = await svc.build_dynamic_query(None)
        assert "?s" in query
        assert "?label" in query
        assert "?type" in query
        assert "?created" in query
        assert "?modified" in query
        assert "FROM" not in query
        assert "?s rdf:type ?type ." in query  # mandatory type binding for subject grounding
        assert cols == ["label", "type", "created", "modified"]

    @pytest.mark.asyncio
    async def test_typed_with_rich_shapes(self):
        """Typed query with ≥3 properties → SHACL columns + type filter."""
        form = _make_form("http://example.org/Note", [
            _make_property("http://purl.org/dc/terms/title", "Title", 1.0),
            _make_property("http://example.org/body", "Body", 2.0),
            _make_property("http://example.org/status", "Status", 3.0),
        ])
        svc = _build_service(form_return=form)
        query, cols = await svc.build_dynamic_query("http://example.org/Note")
        assert "rdf:type <http://example.org/Note>" in query
        assert "?title" in query
        assert "?body" in query
        assert "?status" in query
        assert "FROM" not in query
        assert cols == ["title", "body", "status"]

    @pytest.mark.asyncio
    async def test_typed_with_sparse_shapes_falls_back(self):
        """Typed with ≤2 properties → defaults."""
        form = _make_form("http://example.org/Sparse", [
            _make_property("http://example.org/title", "Title", 1.0),
        ])
        svc = _build_service(form_return=form)
        query, cols = await svc.build_dynamic_query("http://example.org/Sparse")
        assert "?label" in query
        assert "?type" in query
        assert cols == ["label", "type", "created", "modified"]

    @pytest.mark.asyncio
    async def test_type_not_found_falls_back(self):
        """Type not in shapes → defaults."""
        svc = _build_service(form_return=None)
        query, cols = await svc.build_dynamic_query("http://example.org/Unknown")
        assert "?label" in query
        assert cols == ["label", "type", "created", "modified"]

    @pytest.mark.asyncio
    async def test_no_from_clause(self):
        """Query must never contain FROM — scope_to_current_graph adds it."""
        form = _make_form("http://example.org/Note", [
            _make_property("http://example.org/a", "A", 1.0),
            _make_property("http://example.org/b", "B", 2.0),
            _make_property("http://example.org/c", "C", 3.0),
        ])
        svc = _build_service(form_return=form)
        query, _ = await svc.build_dynamic_query("http://example.org/Note")
        assert "FROM" not in query

    @pytest.mark.asyncio
    async def test_graph_renderer_construct(self):
        """Graph renderer → CONSTRUCT with LIMIT 200."""
        svc = _build_service()
        query, cols = await svc.build_dynamic_query(None, renderer="graph")
        assert "CONSTRUCT" in query
        assert "LIMIT 200" in query
        assert cols == []

    @pytest.mark.asyncio
    async def test_graph_renderer_with_type_filter(self):
        """Graph renderer with type → type filter in WHERE."""
        svc = _build_service()
        query, _ = await svc.build_dynamic_query(
            "http://example.org/Note", renderer="graph",
        )
        assert "CONSTRUCT" in query
        assert "rdf:type <http://example.org/Note>" in query
        assert "LIMIT 200" in query

    @pytest.mark.asyncio
    async def test_default_select_has_optional_blocks(self):
        """Default query uses OPTIONAL for all non-subject bindings."""
        svc = _build_service()
        query, _ = await svc.build_dynamic_query(None)
        # All columns should be in OPTIONAL blocks
        assert query.count("OPTIONAL") >= 3  # label, type, created, modified (label is one combined)

    @pytest.mark.asyncio
    async def test_shacl_select_has_optional_per_property(self):
        """SHACL query wraps each property in OPTIONAL."""
        form = _make_form("http://example.org/Note", [
            _make_property("http://example.org/a", "A", 1.0),
            _make_property("http://example.org/b", "B", 2.0),
            _make_property("http://example.org/c", "C", 3.0),
        ])
        svc = _build_service(form_return=form)
        query, _ = await svc.build_dynamic_query("http://example.org/Note")
        # label optional + 3 property optionals = at least 4
        assert query.count("OPTIONAL") >= 4

    @pytest.mark.asyncio
    async def test_shacl_select_includes_label(self):
        """SHACL query should always include ?label via COALESCE/alt path."""
        form = _make_form("http://example.org/Note", [
            _make_property("http://example.org/a", "A", 1.0),
            _make_property("http://example.org/b", "B", 2.0),
            _make_property("http://example.org/c", "C", 3.0),
        ])
        svc = _build_service(form_return=form)
        query, _ = await svc.build_dynamic_query("http://example.org/Note")
        assert "?label" in query

    @pytest.mark.asyncio
    async def test_default_select_with_type_filter(self):
        """Default select with type_iri present → type filter line added."""
        svc = _build_service(form_return=None)
        query, _ = await svc.build_dynamic_query("http://example.org/Foo")
        assert "rdf:type <http://example.org/Foo>" in query
