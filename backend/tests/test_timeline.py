"""Unit tests for timeline renderer backend: SPARQL query construction,
dependency grouping, date fallback, date stripping, and empty results.

Tests cover _build_timeline_select() and execute_timeline_query() on
ViewSpecService, following the test_calendar.py pattern.
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
    datatype: str | None = None,
    in_values: list[str] | None = None,
) -> PropertyShape:
    return PropertyShape(
        path=path,
        name=name,
        order=order,
        datatype=datatype,
        in_values=in_values or [],
    )


def _build_service(
    query_bindings: list[dict] | None = None,
    form_return: NodeShapeForm | None = None,
) -> ViewSpecService:
    """Build a ViewSpecService with mocked dependencies."""
    shapes = MagicMock(spec=ShapesService)
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


# ── _build_timeline_select ────────────────────────────────────


class TestBuildTimelineSelect:
    """Tests for _build_timeline_select() static method."""

    def test_basic_with_start_and_end(self):
        """Produces correct SPARQL with type, start/end paths, and dependency/priority/status OPTIONALs."""
        query = ViewSpecService._build_timeline_select(
            "urn:sempkm:model:basic-pkm:Task",
            "urn:sempkm:model:basic-pkm:scheduledStart",
            end_path="urn:sempkm:model:basic-pkm:scheduledEnd",
        )
        assert "SELECT ?s ?label ?startDate ?endDate ?dep ?priority ?status" in query
        assert "rdf:type <urn:sempkm:model:basic-pkm:Task>" in query
        assert "<urn:sempkm:model:basic-pkm:scheduledStart> ?startDate" in query
        assert "OPTIONAL { ?s <urn:sempkm:model:basic-pkm:scheduledEnd> ?endDate }" in query
        assert "OPTIONAL { ?s <urn:sempkm:model:basic-pkm:dependsOn> ?dep }" in query
        assert "OPTIONAL { ?s <urn:sempkm:model:basic-pkm:priority> ?priority }" in query
        assert "OPTIONAL { ?s <urn:sempkm:model:basic-pkm:taskStatus> ?status }" in query
        assert "rdfs:label|dcterms:title" in query

    def test_with_scope_filter(self):
        """Scope filter injected as sub-select."""
        query = ViewSpecService._build_timeline_select(
            "urn:test:Task",
            "urn:test:startDate",
            scope_filter="?s <urn:ex:tag> 'sprint-1' .",
        )
        assert "{ SELECT ?s WHERE { ?s <urn:ex:tag> 'sprint-1' . } }" in query

    def test_no_end_path(self):
        """Only start field, endDate still in SELECT (from query pattern) but no explicit OPTIONAL for end_path."""
        query = ViewSpecService._build_timeline_select(
            "urn:test:Task",
            "urn:test:dueDate",
        )
        # startDate is required (non-OPTIONAL)
        assert "<urn:test:dueDate> ?startDate" in query
        # endDate appears in SELECT but no end_path OPTIONAL clause
        assert "SELECT ?s ?label ?startDate ?endDate ?dep ?priority ?status" in query
        # No specific OPTIONAL for end_path
        assert "OPTIONAL { ?s <urn:test:dueDate> ?endDate" not in query

    def test_no_scope(self):
        """No scope → no sub-select."""
        query = ViewSpecService._build_timeline_select(
            "urn:test:Task", "urn:test:startDate",
        )
        assert "{ SELECT ?s WHERE" not in query


# ── execute_timeline_query ────────────────────────────────────


class TestExecuteTimelineQuery:
    """Tests for execute_timeline_query() grouping and mapping."""

    @pytest.mark.asyncio
    async def test_groups_deps(self):
        """3 rows for 1 task with 2 deps → single task with dependencies: [dep1, dep2]."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Build API"},
                "startDate": {"value": "2025-06-15"},
                "endDate": {"value": "2025-06-20"},
                "dep": {"value": "urn:task:2"},
            },
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Build API"},
                "startDate": {"value": "2025-06-15"},
                "endDate": {"value": "2025-06-20"},
                "dep": {"value": "urn:task:3"},
            },
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Build API"},
                "startDate": {"value": "2025-06-15"},
                "endDate": {"value": "2025-06-20"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")
        end_field = _make_property("urn:test:endDate", "End Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, end_field,
        )

        assert len(result["tasks"]) == 1
        task = result["tasks"][0]
        assert task["id"] == "urn:task:1"
        assert task["name"] == "Build API"
        assert task["start"] == "2025-06-15"
        assert task["end"] == "2025-06-20"
        assert set(task["dependencies"]) == {"urn:task:2", "urn:task:3"}
        assert result["dependency_count"] == 2

    @pytest.mark.asyncio
    async def test_date_fallback_end_absent(self):
        """When endDate is absent, fallback to startDate + 1 day."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Quick Task"},
                "startDate": {"value": "2025-06-15"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:dueDate", "Due Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, None,
        )

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["start"] == "2025-06-15"
        assert result["tasks"][0]["end"] == "2025-06-16"  # +1 day

    @pytest.mark.asyncio
    async def test_strips_datetime_to_date(self):
        """2024-01-15T14:00:00Z → 2024-01-15."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Meeting"},
                "startDate": {"value": "2024-01-15T14:00:00Z"},
                "endDate": {"value": "2024-01-16T18:00:00Z"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")
        end_field = _make_property("urn:test:endDate", "End Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, end_field,
        )

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["start"] == "2024-01-15"
        assert result["tasks"][0]["end"] == "2024-01-16"

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """No results → {"tasks": [], "dependency_count": 0}."""
        svc = _build_service(query_bindings=[])
        start_field = _make_property("urn:test:startDate", "Start Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, None,
        )

        assert result["tasks"] == []
        assert result["dependency_count"] == 0

    @pytest.mark.asyncio
    async def test_no_date_excluded(self):
        """Tasks without startDate are not in result."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Has Date"},
                "startDate": {"value": "2025-06-15"},
            },
            {
                "s": {"value": "urn:task:2"},
                "label": {"value": "No Date"},
                "startDate": {"value": ""},
            },
            {
                "s": {"value": "urn:task:3"},
                "label": {"value": "Also No Date"},
                # startDate not present at all
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, None,
        )

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["id"] == "urn:task:1"

    @pytest.mark.asyncio
    async def test_status_maps_to_custom_class(self):
        """Task status maps to Frappe Gantt bar CSS class."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Done Task"},
                "startDate": {"value": "2025-06-15"},
                "endDate": {"value": "2025-06-20"},
                "status": {"value": "done"},
            },
            {
                "s": {"value": "urn:task:2"},
                "label": {"value": "Active Task"},
                "startDate": {"value": "2025-06-16"},
                "endDate": {"value": "2025-06-21"},
                "status": {"value": "in-progress"},
            },
            {
                "s": {"value": "urn:task:3"},
                "label": {"value": "No Status"},
                "startDate": {"value": "2025-06-17"},
                "endDate": {"value": "2025-06-22"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")
        end_field = _make_property("urn:test:endDate", "End Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, end_field,
        )

        tasks_by_id = {t["id"]: t for t in result["tasks"]}
        assert tasks_by_id["urn:task:1"]["custom_class"] == "bar-done"
        assert tasks_by_id["urn:task:2"]["custom_class"] == "bar-active"
        assert tasks_by_id["urn:task:3"]["custom_class"] == ""

    @pytest.mark.asyncio
    async def test_query_failure_returns_empty(self):
        """When SPARQL query fails, returns empty tasks without crashing."""
        svc = _build_service()
        svc._client.query = AsyncMock(side_effect=RuntimeError("triplestore down"))

        start_field = _make_property("urn:test:startDate", "Start Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, None,
        )

        assert result["tasks"] == []
        assert result["dependency_count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_tasks_with_deps(self):
        """Multiple tasks, each with different dependency counts."""
        bindings = [
            {
                "s": {"value": "urn:task:A"},
                "label": {"value": "Task A"},
                "startDate": {"value": "2025-06-10"},
                "endDate": {"value": "2025-06-12"},
            },
            {
                "s": {"value": "urn:task:B"},
                "label": {"value": "Task B"},
                "startDate": {"value": "2025-06-13"},
                "endDate": {"value": "2025-06-15"},
                "dep": {"value": "urn:task:A"},
            },
            {
                "s": {"value": "urn:task:C"},
                "label": {"value": "Task C"},
                "startDate": {"value": "2025-06-16"},
                "endDate": {"value": "2025-06-18"},
                "dep": {"value": "urn:task:A"},
            },
            {
                "s": {"value": "urn:task:C"},
                "label": {"value": "Task C"},
                "startDate": {"value": "2025-06-16"},
                "endDate": {"value": "2025-06-18"},
                "dep": {"value": "urn:task:B"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")
        end_field = _make_property("urn:test:endDate", "End Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, end_field,
        )

        assert len(result["tasks"]) == 3
        tasks_by_id = {t["id"]: t for t in result["tasks"]}
        assert tasks_by_id["urn:task:A"]["dependencies"] == []
        assert tasks_by_id["urn:task:B"]["dependencies"] == ["urn:task:A"]
        assert set(tasks_by_id["urn:task:C"]["dependencies"]) == {"urn:task:A", "urn:task:B"}
        assert result["dependency_count"] == 3

    @pytest.mark.asyncio
    async def test_deduplicates_dependency_iris(self):
        """Same dependency IRI appearing in multiple rows is counted once."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Task"},
                "startDate": {"value": "2025-06-15"},
                "dep": {"value": "urn:task:2"},
            },
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Task"},
                "startDate": {"value": "2025-06-15"},
                "dep": {"value": "urn:task:2"},  # duplicate
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, None,
        )

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["dependencies"] == ["urn:task:2"]
        assert result["dependency_count"] == 1

    @pytest.mark.asyncio
    async def test_label_fallback_to_local_name(self):
        """When label binding is absent, uses local name from IRI."""
        bindings = [
            {
                "s": {"value": "urn:task:my-important-task"},
                "startDate": {"value": "2025-06-15"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, None,
        )

        assert result["tasks"][0]["name"] == "my-important-task"

    @pytest.mark.asyncio
    async def test_progress_defaults_to_zero(self):
        """All tasks have progress=0 by default."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Task 1"},
                "startDate": {"value": "2025-06-15"},
                "endDate": {"value": "2025-06-20"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")
        end_field = _make_property("urn:test:endDate", "End Date")

        result = await svc.execute_timeline_query(
            "urn:test:Task", start_field, end_field,
        )

        assert result["tasks"][0]["progress"] == 0
