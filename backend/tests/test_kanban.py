"""Unit tests for kanban renderer backend: status field detection,
SPARQL query building, and server-side grouping into columns.

Tests cover _detect_status_field(), _build_kanban_select(), and
execute_kanban_query() on ViewSpecService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.shapes import NodeShapeForm, PropertyShape, ShapesService
from app.views.service import ViewSpecService


# ── Helpers ────────────────────────────────────────────────────


def _make_property(
    path: str,
    name: str,
    order: float = 0.0,
    in_values: list[str] | None = None,
    datatype: str | None = None,
) -> PropertyShape:
    return PropertyShape(
        path=path,
        name=name,
        order=order,
        in_values=in_values or [],
        datatype=datatype,
    )


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
    shapes_service_none: bool = False,
    query_bindings: list[dict] | None = None,
) -> ViewSpecService:
    """Build a ViewSpecService with mocked dependencies.

    Args:
        form_return: Return value for shapes.get_form_for_type().
        form_side_effect: Exception to raise from get_form_for_type().
        shapes_service_none: If True, set _shapes_service to None.
        query_bindings: Mock SPARQL bindings returned from client.query().
    """
    if shapes_service_none:
        shapes = None
    else:
        shapes = MagicMock(spec=ShapesService)
        if form_side_effect:
            shapes.get_form_for_type = AsyncMock(side_effect=form_side_effect)
        else:
            shapes.get_form_for_type = AsyncMock(return_value=form_return)

    client = MagicMock()
    if query_bindings is not None:
        client.query = AsyncMock(return_value={
            "results": {"bindings": query_bindings},
        })
    else:
        client.query = AsyncMock(return_value={
            "results": {"bindings": []},
        })

    label_service = MagicMock()

    svc = ViewSpecService(
        client=client,
        label_service=label_service,
        shapes_service=shapes,
    )

    return svc


# ── _detect_status_field ──────────────────────────────────────


class TestDetectStatusField:
    """Tests for _detect_status_field() which finds the best sh:in
    property for kanban column grouping."""

    @pytest.mark.asyncio
    async def test_with_sh_in(self):
        """Property with in_values is found."""
        form = _make_form("urn:test:Task", [
            _make_property("urn:test:title", "Title"),
            _make_property(
                "urn:test:priority", "Priority",
                in_values=["low", "medium", "high"],
            ),
        ])
        svc = _build_service(form_return=form)
        prop, values = await svc._detect_status_field("urn:test:Task")
        assert prop is not None
        assert prop.path == "urn:test:priority"
        assert values == ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_prefers_status_path(self):
        """When multiple properties have in_values, prefers one with
        'status' in the path."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:priority", "Priority",
                in_values=["low", "medium", "high"],
            ),
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "in-progress", "done"],
            ),
        ])
        svc = _build_service(form_return=form)
        prop, values = await svc._detect_status_field("urn:test:Task")
        assert prop is not None
        assert prop.path == "urn:test:status"
        assert values == ["todo", "in-progress", "done"]

    @pytest.mark.asyncio
    async def test_prefers_status_path_case_insensitive(self):
        """'Status' in the path matches case-insensitively."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:priority", "Priority",
                in_values=["low", "medium", "high"],
            ),
            _make_property(
                "http://example.org/taskStatus", "Task Status",
                in_values=["open", "closed"],
            ),
        ])
        svc = _build_service(form_return=form)
        prop, values = await svc._detect_status_field("urn:test:Task")
        assert prop is not None
        assert prop.path == "http://example.org/taskStatus"
        assert values == ["open", "closed"]

    @pytest.mark.asyncio
    async def test_no_in_values(self):
        """Returns None when no property has in_values."""
        form = _make_form("urn:test:Task", [
            _make_property("urn:test:title", "Title"),
            _make_property("urn:test:body", "Body"),
        ])
        svc = _build_service(form_return=form)
        prop, values = await svc._detect_status_field("urn:test:Task")
        assert prop is None
        assert values == []

    @pytest.mark.asyncio
    async def test_no_shapes_service(self):
        """Returns None when shapes_service is None."""
        svc = _build_service(shapes_service_none=True)
        prop, values = await svc._detect_status_field("urn:test:Task")
        assert prop is None
        assert values == []

    @pytest.mark.asyncio
    async def test_no_form_for_type(self):
        """Returns None when get_form_for_type returns None."""
        svc = _build_service(form_return=None)
        prop, values = await svc._detect_status_field("urn:test:Unknown")
        assert prop is None
        assert values == []

    @pytest.mark.asyncio
    async def test_shapes_lookup_exception(self):
        """Returns None when shapes lookup raises an exception."""
        svc = _build_service(form_side_effect=RuntimeError("shapes broken"))
        prop, values = await svc._detect_status_field("urn:test:Task")
        assert prop is None
        assert values == []


# ── _build_kanban_select ──────────────────────────────────────


class TestBuildKanbanSelect:
    """Tests for _build_kanban_select() static method."""

    def test_basic(self):
        """Produces correct SPARQL with type and status path."""
        query = ViewSpecService._build_kanban_select(
            "urn:test:Task", "urn:test:status",
        )
        assert "SELECT ?s ?label ?statusValue" in query
        assert "rdf:type <urn:test:Task>" in query
        assert "<urn:test:status> ?statusValue" in query
        assert "OPTIONAL" in query
        assert "rdfs:label|dcterms:title" in query
        # No scope sub-select
        assert "{ SELECT ?s WHERE" not in query

    def test_with_scope(self):
        """Scope filter injected as sub-select."""
        query = ViewSpecService._build_kanban_select(
            "urn:test:Task",
            "urn:test:status",
            scope_filter="?s <urn:ex:tag> 'urgent' .",
        )
        assert "{ SELECT ?s WHERE { ?s <urn:ex:tag> 'urgent' . } }" in query
        assert "rdf:type <urn:test:Task>" in query
        assert "<urn:test:status> ?statusValue" in query

    def test_no_scope_filter_none(self):
        """Explicitly passing None for scope_filter produces no sub-select."""
        query = ViewSpecService._build_kanban_select(
            "urn:test:Task", "urn:test:status", scope_filter=None,
        )
        assert "{ SELECT ?s WHERE" not in query


# ── execute_kanban_query ──────────────────────────────────────


class TestExecuteKanbanQuery:
    """Tests for execute_kanban_query() grouping logic."""

    @pytest.mark.asyncio
    async def test_groups_by_status(self):
        """Mock SPARQL results grouped correctly into columns."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Task One"},
                "statusValue": {"value": "todo"},
            },
            {
                "s": {"value": "urn:task:2"},
                "label": {"value": "Task Two"},
                "statusValue": {"value": "done"},
            },
            {
                "s": {"value": "urn:task:3"},
                "label": {"value": "Task Three"},
                "statusValue": {"value": "todo"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "in-progress", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "in-progress", "done"],
        )

        assert result["total"] == 3
        assert len(result["columns"]) == 3  # no unset column

        todo_col = result["columns"][0]
        assert todo_col["value"] == "todo"
        assert todo_col["label"] == "Todo"
        assert len(todo_col["items"]) == 2

        in_progress_col = result["columns"][1]
        assert in_progress_col["value"] == "in-progress"
        assert in_progress_col["label"] == "In Progress"
        assert len(in_progress_col["items"]) == 0

        done_col = result["columns"][2]
        assert done_col["value"] == "done"
        assert done_col["label"] == "Done"
        assert len(done_col["items"]) == 1
        assert done_col["items"][0]["label"] == "Task Two"

    @pytest.mark.asyncio
    async def test_unset_column(self):
        """Objects with status value not in sh:in go to Unset column."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Task One"},
                "statusValue": {"value": "todo"},
            },
            {
                "s": {"value": "urn:task:2"},
                "label": {"value": "Task Two"},
                "statusValue": {"value": "archived"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        assert result["total"] == 2
        # 2 defined columns + 1 Unset
        assert len(result["columns"]) == 3
        unset_col = result["columns"][-1]
        assert unset_col["value"] == "__unset__"
        assert unset_col["label"] == "Unset"
        assert len(unset_col["items"]) == 1
        assert unset_col["items"][0]["iri"] == "urn:task:2"

    @pytest.mark.asyncio
    async def test_column_order_follows_sh_in(self):
        """Column order follows the status_values list (from sh:in)."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "T1"},
                "statusValue": {"value": "done"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "in-progress", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "in-progress", "done"],
        )

        col_values = [c["value"] for c in result["columns"]]
        assert col_values == ["todo", "in-progress", "done"]

    @pytest.mark.asyncio
    async def test_deduplicates_subjects(self):
        """Duplicate subjects (same ?s) are counted only once."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Task One"},
                "statusValue": {"value": "todo"},
            },
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Task One Alt Label"},
                "statusValue": {"value": "todo"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        assert result["total"] == 1
        assert len(result["columns"][0]["items"]) == 1

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """No bindings returns empty columns."""
        svc = _build_service(query_bindings=[])
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        assert result["total"] == 0
        assert len(result["columns"]) == 2
        assert all(len(c["items"]) == 0 for c in result["columns"])

    @pytest.mark.asyncio
    async def test_status_field_metadata(self):
        """Result includes status_field metadata (path and name)."""
        svc = _build_service(query_bindings=[])
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        assert result["status_field"]["path"] == "urn:test:status"
        assert result["status_field"]["name"] == "Status"

    @pytest.mark.asyncio
    async def test_query_failure_returns_empty_columns(self):
        """When the SPARQL query fails, returns empty columns without crashing."""
        svc = _build_service()
        svc._client.query = AsyncMock(side_effect=RuntimeError("triplestore down"))

        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        assert result["total"] == 0
        assert len(result["columns"]) == 2
        assert result["columns"][0]["value"] == "todo"
        assert result["columns"][1]["value"] == "done"

    @pytest.mark.asyncio
    async def test_label_fallback_to_local_name(self):
        """When label binding is absent, uses local name from IRI."""
        bindings = [
            {
                "s": {"value": "urn:task:my-task"},
                "statusValue": {"value": "todo"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo"],
        )

        assert result["columns"][0]["items"][0]["label"] == "my-task"


# ── _detect_enrichment_fields ─────────────────────────────────


class TestDetectEnrichmentFields:
    """Tests for _detect_enrichment_fields() which detects priority and
    date fields for kanban card enrichment."""

    @pytest.mark.asyncio
    async def test_priority_field_by_path(self):
        """Finds priority field when path contains 'priority'."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
            _make_property(
                "urn:test:priority", "Priority",
                in_values=["low", "medium", "high"],
            ),
        ])
        svc = _build_service(form_return=form)
        status = _make_property("urn:test:status", "Status", in_values=["todo", "done"])
        result = await svc._detect_enrichment_fields("urn:test:Task", status_field=status)
        assert result["priority_field"] is not None
        assert result["priority_field"].path == "urn:test:priority"

    @pytest.mark.asyncio
    async def test_priority_fallback_non_status_in(self):
        """Falls back to first non-status sh:in property when no 'priority' in path."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
            _make_property(
                "urn:test:severity", "Severity",
                in_values=["low", "high"],
            ),
        ])
        svc = _build_service(form_return=form)
        status = _make_property("urn:test:status", "Status", in_values=["todo", "done"])
        result = await svc._detect_enrichment_fields("urn:test:Task", status_field=status)
        assert result["priority_field"] is not None
        assert result["priority_field"].path == "urn:test:severity"

    @pytest.mark.asyncio
    async def test_priority_skips_status_field(self):
        """Status field is excluded from priority candidates even if it has sh:in."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
        ])
        svc = _build_service(form_return=form)
        status = _make_property("urn:test:status", "Status", in_values=["todo", "done"])
        result = await svc._detect_enrichment_fields("urn:test:Task", status_field=status)
        assert result["priority_field"] is None

    @pytest.mark.asyncio
    async def test_date_field_by_datatype(self):
        """Detects date field via xsd:date datatype."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
            _make_property(
                "urn:test:dueDate", "Due Date",
                datatype="http://www.w3.org/2001/XMLSchema#date",
            ),
        ])
        svc = _build_service(form_return=form)
        result = await svc._detect_enrichment_fields("urn:test:Task")
        assert result["date_field"] is not None
        assert result["date_field"].path == "urn:test:dueDate"

    @pytest.mark.asyncio
    async def test_no_enrichment_fields(self):
        """Type with only status and plain text fields returns nulls."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
            _make_property("urn:test:title", "Title"),
            _make_property("urn:test:body", "Body"),
        ])
        svc = _build_service(form_return=form)
        status = _make_property("urn:test:status", "Status", in_values=["todo", "done"])
        result = await svc._detect_enrichment_fields("urn:test:Task", status_field=status)
        assert result["priority_field"] is None
        assert result["date_field"] is None

    @pytest.mark.asyncio
    async def test_no_shapes_service(self):
        """Returns nulls when shapes_service is None."""
        svc = _build_service(shapes_service_none=True)
        result = await svc._detect_enrichment_fields("urn:test:Task")
        assert result["priority_field"] is None
        assert result["date_field"] is None


# ── _build_kanban_select with enrichment ──────────────────────


class TestBuildKanbanSelectEnrichment:
    """Tests for enrichment OPTIONAL clauses in _build_kanban_select()."""

    def test_with_priority_path(self):
        """OPTIONAL clause for priority added when priority_path is set."""
        query = ViewSpecService._build_kanban_select(
            "urn:test:Task", "urn:test:status",
            priority_path="urn:test:priority",
        )
        assert "?priorityValue" in query
        assert "OPTIONAL { ?s <urn:test:priority> ?priorityValue }" in query

    def test_with_date_path(self):
        """OPTIONAL clause for date added when date_path is set."""
        query = ViewSpecService._build_kanban_select(
            "urn:test:Task", "urn:test:status",
            date_path="urn:test:dueDate",
        )
        assert "?dateValue" in query
        assert "OPTIONAL { ?s <urn:test:dueDate> ?dateValue }" in query

    def test_with_both_enrichment_paths(self):
        """Both OPTIONAL clauses present when both paths provided."""
        query = ViewSpecService._build_kanban_select(
            "urn:test:Task", "urn:test:status",
            priority_path="urn:test:priority",
            date_path="urn:test:dueDate",
        )
        assert "?priorityValue" in query
        assert "?dateValue" in query
        assert "OPTIONAL { ?s <urn:test:priority> ?priorityValue }" in query
        assert "OPTIONAL { ?s <urn:test:dueDate> ?dateValue }" in query
        # Both in SELECT clause
        assert "SELECT ?s ?label ?statusValue ?priorityValue ?dateValue" in query

    def test_no_enrichment_paths(self):
        """No enrichment OPTIONAL clauses when both paths are None."""
        query = ViewSpecService._build_kanban_select(
            "urn:test:Task", "urn:test:status",
        )
        assert "?priorityValue" not in query
        assert "?dateValue" not in query
        assert "SELECT ?s ?label ?statusValue\n" in query


# ── execute_kanban_query enrichment ───────────────────────────


class TestExecuteKanbanQueryEnrichment:
    """Tests for enrichment data in execute_kanban_query() output."""

    @pytest.mark.asyncio
    async def test_items_include_enrichment_keys(self):
        """Items always include priority and due_date keys."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Task One"},
                "statusValue": {"value": "todo"},
                "priorityValue": {"value": "high"},
                "dateValue": {"value": "2026-04-15"},
            },
        ]
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
            _make_property(
                "urn:test:priority", "Priority",
                in_values=["low", "medium", "high"],
            ),
            _make_property(
                "urn:test:dueDate", "Due Date",
                datatype="http://www.w3.org/2001/XMLSchema#date",
            ),
        ])
        svc = _build_service(form_return=form, query_bindings=bindings)
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        item = result["columns"][0]["items"][0]
        assert item["priority"] == "high"
        assert item["due_date"] == "2026-04-15"

    @pytest.mark.asyncio
    async def test_items_null_enrichment_when_no_fields(self):
        """Items have None for priority/due_date when type has no enrichment."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Task One"},
                "statusValue": {"value": "todo"},
            },
        ]
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
            _make_property("urn:test:title", "Title"),
        ])
        svc = _build_service(form_return=form, query_bindings=bindings)
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        item = result["columns"][0]["items"][0]
        assert item["priority"] is None
        assert item["due_date"] is None

    @pytest.mark.asyncio
    async def test_enrichment_metadata_in_result(self):
        """Result includes enrichment metadata with field paths and names."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
            _make_property(
                "urn:test:priority", "Priority",
                in_values=["low", "medium", "high"],
            ),
            _make_property(
                "urn:test:dueDate", "Due Date",
                datatype="http://www.w3.org/2001/XMLSchema#date",
            ),
        ])
        svc = _build_service(form_return=form, query_bindings=[])
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        enrichment = result["enrichment"]
        assert enrichment["priority_field"] is not None
        assert enrichment["priority_field"]["path"] == "urn:test:priority"
        assert enrichment["priority_field"]["name"] == "Priority"
        assert enrichment["priority_field"]["values"] == ["low", "medium", "high"]
        assert enrichment["date_field"] is not None
        assert enrichment["date_field"]["path"] == "urn:test:dueDate"
        assert enrichment["date_field"]["name"] == "Due Date"

    @pytest.mark.asyncio
    async def test_enrichment_metadata_null_fields(self):
        """Enrichment metadata has null fields when type has no enrichment."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
        ])
        svc = _build_service(form_return=form, query_bindings=[])
        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        enrichment = result["enrichment"]
        assert enrichment["priority_field"] is None
        assert enrichment["date_field"] is None

    @pytest.mark.asyncio
    async def test_query_failure_includes_enrichment(self):
        """Even when SPARQL query fails, enrichment metadata is present."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "done"],
            ),
            _make_property(
                "urn:test:priority", "Priority",
                in_values=["low", "high"],
            ),
        ])
        svc = _build_service(form_return=form)
        svc._client.query = AsyncMock(side_effect=RuntimeError("triplestore down"))

        status_field = _make_property(
            "urn:test:status", "Status",
            in_values=["todo", "done"],
        )

        result = await svc.execute_kanban_query(
            "urn:test:Task", status_field, ["todo", "done"],
        )

        assert result["total"] == 0
        assert result["enrichment"] is not None
        assert result["enrichment"]["priority_field"]["path"] == "urn:test:priority"
