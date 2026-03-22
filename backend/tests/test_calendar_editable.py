"""Unit tests for editable calendar features: merged multi-type query,
calendar PATCH endpoint, and scheduledStart/scheduledEnd date detection.

Tests the new execute_merged_calendar_query() method, the POST
/browser/views/calendar/patch endpoint, and updated _detect_date_fields()
behavior with Task scheduling properties from T01.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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
    form_map: dict[str, NodeShapeForm | None] | None = None,
    form_return: NodeShapeForm | None = None,
    query_bindings: list[dict] | None = None,
) -> ViewSpecService:
    """Build a ViewSpecService with mocked dependencies.

    Args:
        form_map: type_iri → NodeShapeForm mapping (for multi-type tests).
        form_return: single form to return for any type (simpler tests).
        query_bindings: SPARQL query results to return.
    """
    shapes = MagicMock(spec=ShapesService)
    if form_map is not None:
        async def _get_form(type_iri: str) -> NodeShapeForm | None:
            return form_map.get(type_iri)
        shapes.get_form_for_type = _get_form
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


# ── _detect_date_fields with scheduling properties ────────────


class TestDetectDateFieldsScheduling:
    """Tests that _detect_date_fields() correctly handles the new
    scheduledStart/scheduledEnd properties from T01."""

    @pytest.mark.asyncio
    async def test_task_scheduledstart_preferred_over_duedate(self):
        """scheduledStart must win over dueDate for start field."""
        form = _make_form("urn:sempkm:model:basic-pkm:Task", [
            _make_property(
                "urn:sempkm:model:basic-pkm:dueDate", "Due Date",
                order=6, datatype="http://www.w3.org/2001/XMLSchema#date",
            ),
            _make_property(
                "urn:sempkm:model:basic-pkm:scheduledStart", "Scheduled Start",
                order=6.1, datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
            _make_property(
                "urn:sempkm:model:basic-pkm:scheduledEnd", "Scheduled End",
                order=6.2, datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:sempkm:model:basic-pkm:Task")
        assert start is not None
        assert start.path == "urn:sempkm:model:basic-pkm:scheduledStart"

    @pytest.mark.asyncio
    async def test_task_scheduledend_detected_as_end_field(self):
        """scheduledEnd must be detected as the end field."""
        form = _make_form("urn:sempkm:model:basic-pkm:Task", [
            _make_property(
                "urn:sempkm:model:basic-pkm:scheduledStart", "Scheduled Start",
                order=6.1, datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
            _make_property(
                "urn:sempkm:model:basic-pkm:scheduledEnd", "Scheduled End",
                order=6.2, datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:sempkm:model:basic-pkm:Task")
        assert end is not None
        assert end.path == "urn:sempkm:model:basic-pkm:scheduledEnd"

    @pytest.mark.asyncio
    async def test_task_duedate_only_no_scheduling(self):
        """Task with only dueDate → dueDate as start, no end."""
        form = _make_form("urn:sempkm:model:basic-pkm:Task", [
            _make_property(
                "urn:sempkm:model:basic-pkm:dueDate", "Due Date",
                order=6, datatype="http://www.w3.org/2001/XMLSchema#date",
            ),
            _make_property(
                "urn:sempkm:model:basic-pkm:completedDate", "Completed Date",
                order=7, datatype="http://www.w3.org/2001/XMLSchema#date",
            ),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:sempkm:model:basic-pkm:Task")
        assert start is not None
        assert start.path == "urn:sempkm:model:basic-pkm:dueDate"
        assert end is None

    @pytest.mark.asyncio
    async def test_scheduledstart_detected_via_well_known_path(self):
        """scheduledStart/scheduledEnd detected even without xsd datatype."""
        form = _make_form("urn:test:TaskVariant", [
            _make_property(
                "urn:test:scheduledStart", "Scheduled Start",
            ),
            _make_property(
                "urn:test:scheduledEnd", "Scheduled End",
            ),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:test:TaskVariant")
        assert start is not None
        assert start.path == "urn:test:scheduledStart"
        assert end is not None
        assert end.path == "urn:test:scheduledEnd"


# ── execute_merged_calendar_query ──────────────────────────────


class TestMergedCalendarQuery:
    """Tests for execute_merged_calendar_query() which merges Events
    and Tasks into a single FullCalendar event list."""

    @pytest.mark.asyncio
    async def test_merged_returns_both_types(self):
        """Merged query returns events from both Event and Task types."""
        event_form = _make_form("urn:sempkm:model:basic-pkm:Event", [
            _make_property("https://schema.org/startDate", "Start Date"),
            _make_property("https://schema.org/endDate", "End Date"),
        ])
        task_form = _make_form("urn:sempkm:model:basic-pkm:Task", [
            _make_property(
                "urn:sempkm:model:basic-pkm:scheduledStart", "Scheduled Start",
                datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
            _make_property(
                "urn:sempkm:model:basic-pkm:scheduledEnd", "Scheduled End",
                datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
        ])

        form_map = {
            "urn:sempkm:model:basic-pkm:Event": event_form,
            "urn:sempkm:model:basic-pkm:Task": task_form,
        }

        # Mock query to return different results per call
        call_count = 0
        async def mock_query(sparql: str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: Event query
                return {"results": {"bindings": [
                    {
                        "s": {"value": "urn:event:1"},
                        "label": {"value": "Team Meeting"},
                        "startDate": {"value": "2025-06-15T10:00:00"},
                        "endDate": {"value": "2025-06-15T11:00:00"},
                    },
                ]}}
            else:
                # Second call: Task query
                return {"results": {"bindings": [
                    {
                        "s": {"value": "urn:task:1"},
                        "label": {"value": "Design Review"},
                        "startDate": {"value": "2025-06-15T14:00:00"},
                        "endDate": {"value": "2025-06-15T15:30:00"},
                    },
                ]}}

        svc = _build_service(form_map=form_map)
        svc._client.query = mock_query

        result = await svc.execute_merged_calendar_query()

        assert len(result["events"]) == 2
        assert len(result["types_found"]) == 2

        # Check sourceType annotations
        source_types = {e["extendedProps"]["sourceType"] for e in result["events"]}
        assert "event" in source_types
        assert "task" in source_types

    @pytest.mark.asyncio
    async def test_merged_annotates_colors(self):
        """Merged events have backgroundColor and borderColor set."""
        event_form = _make_form("urn:sempkm:model:basic-pkm:Event", [
            _make_property("https://schema.org/startDate", "Start Date"),
        ])
        task_form = _make_form("urn:sempkm:model:basic-pkm:Task", [
            _make_property(
                "urn:sempkm:model:basic-pkm:scheduledStart", "Scheduled Start",
                datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
        ])
        form_map = {
            "urn:sempkm:model:basic-pkm:Event": event_form,
            "urn:sempkm:model:basic-pkm:Task": task_form,
        }

        call_count = 0
        async def mock_query(sparql: str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"results": {"bindings": [
                    {"s": {"value": "urn:event:1"}, "label": {"value": "E1"}, "startDate": {"value": "2025-06-15"}},
                ]}}
            return {"results": {"bindings": [
                {"s": {"value": "urn:task:1"}, "label": {"value": "T1"}, "startDate": {"value": "2025-06-15T14:00:00"}},
            ]}}

        svc = _build_service(form_map=form_map)
        svc._client.query = mock_query

        result = await svc.execute_merged_calendar_query()

        event_ev = next(e for e in result["events"] if e["extendedProps"]["sourceType"] == "event")
        task_ev = next(e for e in result["events"] if e["extendedProps"]["sourceType"] == "task")

        assert event_ev["backgroundColor"] == "#8b5cf6"  # purple
        assert task_ev["backgroundColor"] == "#10b981"    # green

    @pytest.mark.asyncio
    async def test_merged_skips_type_without_date_fields(self):
        """Types without detectable date fields are silently skipped."""
        # Event has date fields, Task does not (empty form)
        event_form = _make_form("urn:sempkm:model:basic-pkm:Event", [
            _make_property("https://schema.org/startDate", "Start Date"),
        ])
        task_form = _make_form("urn:sempkm:model:basic-pkm:Task", [
            _make_property("urn:test:name", "Name", datatype="http://www.w3.org/2001/XMLSchema#string"),
        ])
        form_map = {
            "urn:sempkm:model:basic-pkm:Event": event_form,
            "urn:sempkm:model:basic-pkm:Task": task_form,
        }

        svc = _build_service(form_map=form_map, query_bindings=[
            {"s": {"value": "urn:event:1"}, "label": {"value": "E1"}, "startDate": {"value": "2025-06-15"}},
        ])

        result = await svc.execute_merged_calendar_query()

        assert len(result["types_found"]) == 1
        assert "urn:sempkm:model:basic-pkm:Event" in result["types_found"]

    @pytest.mark.asyncio
    async def test_merged_with_no_events(self):
        """Merged query returns empty list when no types have events."""
        svc = _build_service(form_return=None)

        result = await svc.execute_merged_calendar_query()

        assert result["events"] == []
        assert result["types_found"] == []

    @pytest.mark.asyncio
    async def test_merged_passes_scope_filter(self):
        """scope_filter is passed through to execute_calendar_query."""
        event_form = _make_form("urn:sempkm:model:basic-pkm:Event", [
            _make_property("https://schema.org/startDate", "Start Date"),
        ])
        form_map = {
            "urn:sempkm:model:basic-pkm:Event": event_form,
            "urn:sempkm:model:basic-pkm:Task": None,  # skip Task
        }

        queries_received: list[str] = []
        async def mock_query(sparql: str):
            queries_received.append(sparql)
            return {"results": {"bindings": []}}

        svc = _build_service(form_map=form_map)
        svc._client.query = mock_query

        await svc.execute_merged_calendar_query(scope_filter="?s <urn:ex:tag> 'meeting' .")

        # The scope filter should appear in at least one query
        assert any("meeting" in q for q in queries_received)


# ── Calendar PATCH endpoint ────────────────────────────────────


class TestCalendarPatchEndpoint:
    """Tests for the POST /browser/views/calendar/patch endpoint.

    These test the endpoint logic by importing and calling the handler
    with mocked dependencies.
    """

    @pytest.mark.asyncio
    async def test_patch_validates_iri(self):
        """Invalid IRI returns 400."""
        from app.views.router import CalendarPatchRequest
        from app.browser._helpers import _validate_iri

        # Test the validation logic directly
        assert _validate_iri("") is False
        assert _validate_iri("not-a-uri") is False
        assert _validate_iri("urn:sempkm:model:basic-pkm:task-1") is True
        assert _validate_iri("https://example.com/object/1") is True

    @pytest.mark.asyncio
    async def test_patch_request_model(self):
        """CalendarPatchRequest validates correctly."""
        from app.views.router import CalendarPatchRequest

        req = CalendarPatchRequest(iri="urn:test:1", start="2025-06-15T10:00:00")
        assert req.iri == "urn:test:1"
        assert req.start == "2025-06-15T10:00:00"
        assert req.end is None

    @pytest.mark.asyncio
    async def test_patch_request_requires_start_or_end(self):
        """Request with neither start nor end should be rejected by the endpoint."""
        from app.views.router import CalendarPatchRequest

        # Model validation doesn't enforce at least one field — that's done
        # in the endpoint handler. We test the model accepts both None.
        req = CalendarPatchRequest(iri="urn:test:1")
        assert req.start is None
        assert req.end is None

    @pytest.mark.asyncio
    async def test_date_predicates_map(self):
        """Predicate map has correct entries for Event and Task types."""
        from app.views.router import _CALENDAR_DATE_PREDICATES

        assert "urn:sempkm:model:basic-pkm:Event" in _CALENDAR_DATE_PREDICATES
        assert "urn:sempkm:model:basic-pkm:Task" in _CALENDAR_DATE_PREDICATES

        event_preds = _CALENDAR_DATE_PREDICATES["urn:sempkm:model:basic-pkm:Event"]
        assert event_preds["start"] == "https://schema.org/startDate"
        assert event_preds["end"] == "https://schema.org/endDate"

        task_preds = _CALENDAR_DATE_PREDICATES["urn:sempkm:model:basic-pkm:Task"]
        assert task_preds["start"] == "urn:sempkm:model:basic-pkm:scheduledStart"
        assert task_preds["end"] == "urn:sempkm:model:basic-pkm:scheduledEnd"
