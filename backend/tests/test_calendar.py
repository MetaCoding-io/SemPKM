"""Unit tests for calendar renderer backend: date field detection,
SPARQL query building, and FullCalendar event mapping.

Tests cover _detect_date_fields(), _build_calendar_select(), and
execute_calendar_query() on ViewSpecService.
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
    """Build a ViewSpecService with mocked dependencies."""
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


# ── _detect_date_fields ──────────────────────────────────────


class TestDetectDateFields:
    """Tests for _detect_date_fields() which finds start/end date
    properties for calendar rendering."""

    @pytest.mark.asyncio
    async def test_event_type_no_datatype(self):
        """Event type: schema:startDate/endDate detected via well-known path
        even when sh:datatype is None."""
        form = _make_form("urn:test:Event", [
            _make_property("http://purl.org/dc/terms/title", "Title", datatype="http://www.w3.org/2001/XMLSchema#string"),
            _make_property("https://schema.org/startDate", "Start Date"),  # No datatype!
            _make_property("https://schema.org/endDate", "End Date"),      # No datatype!
            _make_property("urn:test:location", "Location", datatype="http://www.w3.org/2001/XMLSchema#string"),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:test:Event")
        assert start is not None
        assert start.path == "https://schema.org/startDate"
        assert end is not None
        assert end.path == "https://schema.org/endDate"

    @pytest.mark.asyncio
    async def test_project_type_with_datatype(self):
        """Project type: schema:startDate/endDate detected via xsd:date datatype."""
        form = _make_form("urn:test:Project", [
            _make_property("http://purl.org/dc/terms/title", "Title", datatype="http://www.w3.org/2001/XMLSchema#string"),
            _make_property("https://schema.org/startDate", "Start Date", datatype="http://www.w3.org/2001/XMLSchema#date"),
            _make_property("https://schema.org/endDate", "End Date", datatype="http://www.w3.org/2001/XMLSchema#date"),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:test:Project")
        assert start is not None
        assert start.path == "https://schema.org/startDate"
        assert end is not None
        assert end.path == "https://schema.org/endDate"

    @pytest.mark.asyncio
    async def test_task_type_duedate_only(self):
        """Task type: bpkm:dueDate detected, no end field."""
        form = _make_form("urn:test:Task", [
            _make_property("http://purl.org/dc/terms/title", "Title", datatype="http://www.w3.org/2001/XMLSchema#string"),
            _make_property("urn:sempkm:model:basic-pkm:dueDate", "Due Date", datatype="http://www.w3.org/2001/XMLSchema#date"),
            _make_property("urn:sempkm:model:basic-pkm:completedDate", "Completed Date", datatype="http://www.w3.org/2001/XMLSchema#date"),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:test:Task")
        assert start is not None
        assert start.path == "urn:sempkm:model:basic-pkm:dueDate"
        # completedDate is not an end date
        assert end is None

    @pytest.mark.asyncio
    async def test_note_type_no_dates(self):
        """Note type: no date properties → returns (None, None)."""
        form = _make_form("urn:test:Note", [
            _make_property("http://purl.org/dc/terms/title", "Title", datatype="http://www.w3.org/2001/XMLSchema#string"),
            _make_property("urn:test:body", "Body", datatype="http://www.w3.org/2001/XMLSchema#string"),
            _make_property("urn:test:tags", "Tags", datatype="http://www.w3.org/2001/XMLSchema#string"),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:test:Note")
        assert start is None
        assert end is None

    @pytest.mark.asyncio
    async def test_no_shapes_service(self):
        """Returns (None, None) when shapes_service is None."""
        svc = _build_service(shapes_service_none=True)
        start, end = await svc._detect_date_fields("urn:test:Task")
        assert start is None
        assert end is None

    @pytest.mark.asyncio
    async def test_no_form_for_type(self):
        """Returns (None, None) when get_form_for_type returns None."""
        svc = _build_service(form_return=None)
        start, end = await svc._detect_date_fields("urn:test:Unknown")
        assert start is None
        assert end is None

    @pytest.mark.asyncio
    async def test_shapes_lookup_exception(self):
        """Returns (None, None) when shapes lookup raises."""
        svc = _build_service(form_side_effect=RuntimeError("shapes broken"))
        start, end = await svc._detect_date_fields("urn:test:Task")
        assert start is None
        assert end is None

    @pytest.mark.asyncio
    async def test_prefers_startdate_over_duedate(self):
        """When both startDate and dueDate exist, startDate wins for start field."""
        form = _make_form("urn:test:Hybrid", [
            _make_property("https://schema.org/startDate", "Start Date", datatype="http://www.w3.org/2001/XMLSchema#date"),
            _make_property("urn:test:dueDate", "Due Date", datatype="http://www.w3.org/2001/XMLSchema#date"),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:test:Hybrid")
        assert start is not None
        assert start.path == "https://schema.org/startDate"

    @pytest.mark.asyncio
    async def test_datetime_datatype_detected(self):
        """xsd:dateTime properties are also detected as date fields."""
        form = _make_form("urn:test:Log", [
            _make_property("urn:test:timestamp", "Timestamp", datatype="http://www.w3.org/2001/XMLSchema#dateTime"),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:test:Log")
        assert start is not None
        assert start.path == "urn:test:timestamp"
        assert end is None

    @pytest.mark.asyncio
    async def test_fallback_to_dcterms_created(self):
        """When only dcterms:created is a date field, it becomes the start."""
        form = _make_form("urn:test:Simple", [
            _make_property("http://purl.org/dc/terms/title", "Title", datatype="http://www.w3.org/2001/XMLSchema#string"),
            _make_property("http://purl.org/dc/terms/created", "Created", datatype="http://www.w3.org/2001/XMLSchema#dateTime"),
        ])
        svc = _build_service(form_return=form)
        start, end = await svc._detect_date_fields("urn:test:Simple")
        assert start is not None
        assert start.path == "http://purl.org/dc/terms/created"
        assert end is None


# ── _build_calendar_select ────────────────────────────────────


class TestBuildCalendarSelect:
    """Tests for _build_calendar_select() static method."""

    def test_basic_with_start_only(self):
        """Produces correct SPARQL with type and start path, no end."""
        query = ViewSpecService._build_calendar_select(
            "urn:test:Task", "urn:test:dueDate",
        )
        assert "SELECT ?s ?label ?startDate" in query
        assert "?endDate" not in query
        assert "rdf:type <urn:test:Task>" in query
        assert "<urn:test:dueDate> ?startDate" in query
        assert "OPTIONAL" in query
        assert "rdfs:label|dcterms:title" in query

    def test_with_start_and_end(self):
        """Produces SPARQL with both start and end date variables."""
        query = ViewSpecService._build_calendar_select(
            "urn:test:Event",
            "https://schema.org/startDate",
            end_path="https://schema.org/endDate",
        )
        assert "SELECT ?s ?label ?startDate ?endDate" in query
        assert "<https://schema.org/startDate> ?startDate" in query
        assert "OPTIONAL { ?s <https://schema.org/endDate> ?endDate }" in query

    def test_with_scope(self):
        """Scope filter injected as sub-select."""
        query = ViewSpecService._build_calendar_select(
            "urn:test:Event",
            "https://schema.org/startDate",
            scope_filter="?s <urn:ex:tag> 'meeting' .",
        )
        assert "{ SELECT ?s WHERE { ?s <urn:ex:tag> 'meeting' . } }" in query

    def test_no_scope(self):
        """No scope → no sub-select."""
        query = ViewSpecService._build_calendar_select(
            "urn:test:Event", "https://schema.org/startDate",
        )
        assert "{ SELECT ?s WHERE" not in query


# ── execute_calendar_query ────────────────────────────────────


class TestExecuteCalendarQuery:
    """Tests for execute_calendar_query() FullCalendar event mapping."""

    @pytest.mark.asyncio
    async def test_maps_to_fullcalendar_format(self):
        """Mock SPARQL results mapped to FullCalendar event objects."""
        bindings = [
            {
                "s": {"value": "urn:event:1"},
                "label": {"value": "Team Meeting"},
                "startDate": {"value": "2025-06-15T10:00:00"},
                "endDate": {"value": "2025-06-15T11:00:00"},
            },
            {
                "s": {"value": "urn:event:2"},
                "label": {"value": "All Day Event"},
                "startDate": {"value": "2025-06-20"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("https://schema.org/startDate", "Start Date")
        end_field = _make_property("https://schema.org/endDate", "End Date")

        result = await svc.execute_calendar_query(
            "urn:test:Event", start_field, end_field,
        )

        assert len(result["events"]) == 2

        # First event: dateTime → allDay=False
        ev1 = result["events"][0]
        assert ev1["id"] == "urn:event:1"
        assert ev1["title"] == "Team Meeting"
        assert ev1["start"] == "2025-06-15T10:00:00"
        assert ev1["end"] == "2025-06-15T11:00:00"
        assert ev1["allDay"] is False
        assert ev1["extendedProps"]["iri"] == "urn:event:1"

        # Second event: date → allDay=True, no end
        ev2 = result["events"][1]
        assert ev2["id"] == "urn:event:2"
        assert ev2["title"] == "All Day Event"
        assert ev2["start"] == "2025-06-20"
        assert ev2["allDay"] is True
        assert "end" not in ev2

    @pytest.mark.asyncio
    async def test_no_end_field(self):
        """When end_field is None, events have no end property."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Due Task"},
                "startDate": {"value": "2025-07-01"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:dueDate", "Due Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, None,
        )

        assert len(result["events"]) == 1
        assert "end" not in result["events"][0]
        assert result["date_fields"]["end"] is None

    @pytest.mark.asyncio
    async def test_deduplicates_subjects(self):
        """Duplicate subjects (same ?s) are counted only once."""
        bindings = [
            {
                "s": {"value": "urn:event:1"},
                "label": {"value": "Event One"},
                "startDate": {"value": "2025-06-15"},
            },
            {
                "s": {"value": "urn:event:1"},
                "label": {"value": "Event One Alt"},
                "startDate": {"value": "2025-06-15"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("https://schema.org/startDate", "Start Date")

        result = await svc.execute_calendar_query(
            "urn:test:Event", start_field, None,
        )

        assert len(result["events"]) == 1

    @pytest.mark.asyncio
    async def test_skips_empty_start(self):
        """Events without a start date value are skipped."""
        bindings = [
            {
                "s": {"value": "urn:event:1"},
                "label": {"value": "Valid"},
                "startDate": {"value": "2025-06-15"},
            },
            {
                "s": {"value": "urn:event:2"},
                "label": {"value": "No Start"},
                "startDate": {"value": ""},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("https://schema.org/startDate", "Start Date")

        result = await svc.execute_calendar_query(
            "urn:test:Event", start_field, None,
        )

        assert len(result["events"]) == 1
        assert result["events"][0]["id"] == "urn:event:1"

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """No bindings returns empty events list."""
        svc = _build_service(query_bindings=[])
        start_field = _make_property("https://schema.org/startDate", "Start Date")

        result = await svc.execute_calendar_query(
            "urn:test:Event", start_field, None,
        )

        assert result["events"] == []
        assert result["date_fields"]["start"]["path"] == "https://schema.org/startDate"

    @pytest.mark.asyncio
    async def test_date_fields_metadata(self):
        """Result includes date_fields metadata (paths and names)."""
        svc = _build_service(query_bindings=[])
        start_field = _make_property("https://schema.org/startDate", "Start Date")
        end_field = _make_property("https://schema.org/endDate", "End Date")

        result = await svc.execute_calendar_query(
            "urn:test:Event", start_field, end_field,
        )

        assert result["date_fields"]["start"]["path"] == "https://schema.org/startDate"
        assert result["date_fields"]["start"]["name"] == "Start Date"
        assert result["date_fields"]["end"]["path"] == "https://schema.org/endDate"
        assert result["date_fields"]["end"]["name"] == "End Date"

    @pytest.mark.asyncio
    async def test_query_failure_returns_empty(self):
        """When the SPARQL query fails, returns empty events without crashing."""
        svc = _build_service()
        svc._client.query = AsyncMock(side_effect=RuntimeError("triplestore down"))

        start_field = _make_property("https://schema.org/startDate", "Start Date")

        result = await svc.execute_calendar_query(
            "urn:test:Event", start_field, None,
        )

        assert result["events"] == []
        assert result["date_fields"]["start"]["path"] == "https://schema.org/startDate"

    @pytest.mark.asyncio
    async def test_label_fallback_to_local_name(self):
        """When label binding is absent, uses local name from IRI."""
        bindings = [
            {
                "s": {"value": "urn:event:my-meeting"},
                "startDate": {"value": "2025-06-15T09:00:00"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("https://schema.org/startDate", "Start Date")

        result = await svc.execute_calendar_query(
            "urn:test:Event", start_field, None,
        )

        assert result["events"][0]["title"] == "my-meeting"
