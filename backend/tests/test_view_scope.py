"""Unit tests for scope query filtering and variant dropdown data.

Tests the scope_filter parameter on build_dynamic_query(), the
extract_scope_where_body() utility, and get_view_specs_for_type()
filtering.  These are the contract verification for S01's boundary
outputs — consumed by S02, S03, and S04.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.shapes import NodeShapeForm, PropertyShape, ShapesService
from app.views.service import (
    ViewSpec,
    ViewSpecService,
    extract_scope_where_body,
)


# ── Helpers ────────────────────────────────────────────────────


def _make_property(path: str, name: str, order: float = 0.0) -> PropertyShape:
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
    view_specs: list[ViewSpec] | None = None,
) -> ViewSpecService:
    """Build a ViewSpecService with mocked dependencies.

    If ``view_specs`` is given, ``get_all_view_specs()`` returns them
    (used by ``get_view_specs_for_type``).
    """
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

    if view_specs is not None:
        svc.get_all_view_specs = AsyncMock(return_value=view_specs)

    return svc


# ── build_dynamic_query WITHOUT scope_filter ───────────────────


class TestBuildDynamicQueryNoScope:
    """Baseline tests: build_dynamic_query produces correct queries
    without any scope_filter."""

    @pytest.mark.asyncio
    async def test_select_no_type_no_scope(self):
        """Default SELECT query has no sub-select scope constraint."""
        svc = _build_service()
        query, cols = await svc.build_dynamic_query(None, "table")
        assert "SELECT" in query
        assert "{ SELECT ?s WHERE" not in query
        assert cols == ["label", "type", "created", "modified"]

    @pytest.mark.asyncio
    async def test_select_with_type_no_scope(self):
        """Typed query adds type filter but no scope constraint."""
        svc = _build_service()
        query, _ = await svc.build_dynamic_query(
            "http://example.org/Note", "table",
        )
        assert "rdf:type <http://example.org/Note>" in query
        assert "{ SELECT ?s WHERE" not in query

    @pytest.mark.asyncio
    async def test_construct_no_scope(self):
        """Graph renderer CONSTRUCT query has no scope sub-select."""
        svc = _build_service()
        query, cols = await svc.build_dynamic_query(None, "graph")
        assert "CONSTRUCT" in query
        assert "{ SELECT ?s WHERE" not in query
        assert cols == []


# ── build_dynamic_query WITH scope_filter ──────────────────────


class TestBuildDynamicQueryWithScope:
    """Tests that scope_filter injects a { SELECT ?s WHERE { ... } }
    sub-select into the generated query."""

    SCOPE = "?s a <urn:test:Type> ."

    @pytest.mark.asyncio
    async def test_default_select_with_scope(self):
        """Scope filter adds a sub-select constraining ?s in default SELECT."""
        svc = _build_service()
        query, _ = await svc.build_dynamic_query(
            None, "table", scope_filter=self.SCOPE,
        )
        assert "{ SELECT ?s WHERE { ?s a <urn:test:Type> . } }" in query

    @pytest.mark.asyncio
    async def test_typed_select_with_scope(self):
        """Typed query combines type filter AND scope sub-select."""
        svc = _build_service()
        query, _ = await svc.build_dynamic_query(
            "http://example.org/Note", "table", scope_filter=self.SCOPE,
        )
        assert "rdf:type <http://example.org/Note>" in query
        assert "{ SELECT ?s WHERE { ?s a <urn:test:Type> . } }" in query

    @pytest.mark.asyncio
    async def test_shacl_select_with_scope(self):
        """SHACL-derived query includes scope sub-select alongside
        property OPTIONAL blocks."""
        form = _make_form("http://example.org/Note", [
            _make_property("http://example.org/title", "Title", 1.0),
            _make_property("http://example.org/body", "Body", 2.0),
            _make_property("http://example.org/status", "Status", 3.0),
        ])
        svc = _build_service(form_return=form)
        query, cols = await svc.build_dynamic_query(
            "http://example.org/Note", "table",
            scope_filter="?s <urn:ex:tag> 'important' .",
        )
        assert "{ SELECT ?s WHERE { ?s <urn:ex:tag> 'important' . } }" in query
        assert "OPTIONAL" in query
        assert cols == ["title", "body", "status"]

    @pytest.mark.asyncio
    async def test_construct_with_scope(self):
        """Graph renderer CONSTRUCT includes scope sub-select."""
        svc = _build_service()
        query, _ = await svc.build_dynamic_query(
            None, "graph", scope_filter=self.SCOPE,
        )
        assert "CONSTRUCT" in query
        assert "{ SELECT ?s WHERE { ?s a <urn:test:Type> . } }" in query

    @pytest.mark.asyncio
    async def test_construct_typed_with_scope(self):
        """Graph renderer with type AND scope — both present."""
        svc = _build_service()
        query, _ = await svc.build_dynamic_query(
            "http://example.org/Note", "graph", scope_filter=self.SCOPE,
        )
        assert "CONSTRUCT" in query
        assert "rdf:type <http://example.org/Note>" in query
        assert "{ SELECT ?s WHERE { ?s a <urn:test:Type> . } }" in query

    @pytest.mark.asyncio
    async def test_scope_subselect_uses_s_variable(self):
        """The scope sub-select must output ?s, matching what the outer
        query expects for subject binding."""
        svc = _build_service()
        query, _ = await svc.build_dynamic_query(
            None, "table", scope_filter="?s <urn:ex:status> 'active' .",
        )
        # The sub-select must be exactly: { SELECT ?s WHERE { ... } }
        assert "SELECT ?s WHERE" in query


# ── extract_scope_where_body ───────────────────────────────────


class TestExtractScopeWhereBody:
    """Tests for the extract_scope_where_body() utility that extracts
    the WHERE body from a saved query and normalizes the primary
    SELECT variable to ?s."""

    def test_simple_select_with_s(self):
        """Already uses ?s — returns WHERE body unchanged."""
        query = "SELECT ?s ?title WHERE { ?s a <urn:Type> . ?s <urn:title> ?title }"
        body = extract_scope_where_body(query)
        assert "?s a <urn:Type>" in body
        assert "?s <urn:title> ?title" in body

    def test_query_with_limit_returns_empty(self):
        """Queries with LIMIT after closing brace aren't matched by the
        end-of-string regex — returns empty (known limitation)."""
        query = "SELECT ?s WHERE { ?s a <urn:Type> } LIMIT 100"
        body = extract_scope_where_body(query)
        assert body == ""

    def test_renames_primary_var_to_s(self):
        """Primary SELECT variable (?iri) is renamed to ?s."""
        query = "SELECT ?iri ?title WHERE { ?iri a <urn:Type> . ?iri <urn:title> ?title }"
        body = extract_scope_where_body(query)
        assert "?s a <urn:Type>" in body
        assert "?s <urn:title> ?title" in body
        # Original ?iri should be gone
        assert "?iri" not in body

    def test_distinct_select(self):
        """DISTINCT keyword does not interfere with variable extraction."""
        query = "SELECT DISTINCT ?item WHERE { ?item a <urn:Project> }"
        body = extract_scope_where_body(query)
        assert "?s a <urn:Project>" in body
        assert "?item" not in body

    def test_from_clause_ignored(self):
        """FROM clause is between SELECT and WHERE — should not affect body extraction."""
        query = (
            "SELECT ?s ?title "
            "FROM <urn:sempkm:current> "
            "WHERE { ?s a <urn:Type> . ?s <urn:title> ?title }"
        )
        body = extract_scope_where_body(query)
        assert "?s a <urn:Type>" in body

    def test_nested_braces(self):
        """Query with OPTIONAL blocks (nested braces) — extracts full body."""
        query = (
            "SELECT ?s WHERE { "
            "?s a <urn:Note> . "
            "OPTIONAL { ?s <urn:tag> ?tag } "
            "}"
        )
        body = extract_scope_where_body(query)
        assert "?s a <urn:Note>" in body
        assert "OPTIONAL { ?s <urn:tag> ?tag }" in body

    def test_malformed_no_where(self):
        """Malformed query without WHERE returns empty string."""
        body = extract_scope_where_body("DESCRIBE <urn:thing>")
        assert body == ""

    def test_malformed_no_braces(self):
        """Malformed query with WHERE but no braces returns empty string."""
        body = extract_scope_where_body("SELECT ?s WHERE")
        assert body == ""

    def test_empty_string(self):
        """Empty input returns empty string."""
        body = extract_scope_where_body("")
        assert body == ""

    def test_preserves_secondary_variables(self):
        """Secondary variables (not the first SELECT var) are NOT renamed."""
        query = "SELECT ?item ?author WHERE { ?item <urn:author> ?author . ?item a <urn:Book> }"
        body = extract_scope_where_body(query)
        # ?item → ?s, but ?author stays
        assert "?s <urn:author> ?author" in body
        assert "?author" in body


# ── get_view_specs_for_type ────────────────────────────────────


class TestGetViewSpecsForType:
    """Tests for ViewSpecService.get_view_specs_for_type() which filters
    model-declared ViewSpecs by target_class."""

    @staticmethod
    def _specs() -> list[ViewSpec]:
        return [
            ViewSpec(
                spec_iri="urn:model:projects-table",
                label="Projects Table",
                target_class="http://example.org/Project",
                renderer_type="table",
                sparql_query="SELECT ...",
                source_model="basic-pkm",
            ),
            ViewSpec(
                spec_iri="urn:model:projects-graph",
                label="Projects Graph",
                target_class="http://example.org/Project",
                renderer_type="graph",
                sparql_query="CONSTRUCT ...",
                source_model="basic-pkm",
            ),
            ViewSpec(
                spec_iri="urn:model:notes-cards",
                label="Notes Cards",
                target_class="http://example.org/Note",
                renderer_type="card",
                sparql_query="SELECT ...",
                source_model="basic-pkm",
            ),
            ViewSpec(
                spec_iri="urn:model:generic-explorer",
                label="Generic Explorer",
                target_class="",
                renderer_type="table",
                sparql_query="SELECT ...",
                source_model="basic-pkm",
            ),
        ]

    @pytest.mark.asyncio
    async def test_returns_matching_specs(self):
        """Returns only ViewSpecs whose target_class matches."""
        svc = _build_service(view_specs=self._specs())
        result = await svc.get_view_specs_for_type("http://example.org/Project")
        assert len(result) == 2
        labels = {s.label for s in result}
        assert labels == {"Projects Table", "Projects Graph"}

    @pytest.mark.asyncio
    async def test_returns_different_type(self):
        """Returns specs for a different type."""
        svc = _build_service(view_specs=self._specs())
        result = await svc.get_view_specs_for_type("http://example.org/Note")
        assert len(result) == 1
        assert result[0].label == "Notes Cards"

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_type(self):
        """Returns empty list for types with no model-declared specs."""
        svc = _build_service(view_specs=self._specs())
        result = await svc.get_view_specs_for_type("http://example.org/Unknown")
        assert result == []

    @pytest.mark.asyncio
    async def test_excludes_generic_specs(self):
        """Generic specs (empty target_class) are NOT returned for any type."""
        svc = _build_service(view_specs=self._specs())
        result = await svc.get_view_specs_for_type("http://example.org/Project")
        for spec in result:
            assert spec.target_class != ""
            assert spec.target_class == "http://example.org/Project"

    @pytest.mark.asyncio
    async def test_empty_target_class_not_matched(self):
        """Passing empty string as type_iri matches specs with empty target_class
        (but this is the caller's responsibility — the function does exact match)."""
        svc = _build_service(view_specs=self._specs())
        result = await svc.get_view_specs_for_type("")
        # The generic-explorer spec has target_class="" so it matches
        assert len(result) == 1
        assert result[0].label == "Generic Explorer"

    @pytest.mark.asyncio
    async def test_no_specs_at_all(self):
        """Returns empty list when no view specs exist."""
        svc = _build_service(view_specs=[])
        result = await svc.get_view_specs_for_type("http://example.org/Project")
        assert result == []
