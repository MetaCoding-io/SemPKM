"""Unit tests for RRULE expansion and virtual calendar event generation.

Tests cover _expand_rrule() static method and the recurrence-aware
path in execute_calendar_query() on ViewSpecService.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.services.shapes import NodeShapeForm, PropertyShape, ShapesService
from app.views.service import ViewSpecService


# ── Helpers (mirror test_calendar.py) ──────────────────────────


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


# ── _expand_rrule ─────────────────────────────────────────────


class TestExpandRrule:
    """Tests for ViewSpecService._expand_rrule() RRULE expansion."""

    def test_weekly_friday(self):
        """FREQ=WEEKLY;BYDAY=FR returns Fridays within the window."""
        dtstart = datetime(2025, 6, 6)  # A Friday
        range_start = datetime(2025, 6, 1)
        range_end = datetime(2025, 7, 1)

        results = ViewSpecService._expand_rrule(
            "FREQ=WEEKLY;BYDAY=FR", dtstart, range_start, range_end,
        )

        assert len(results) >= 4  # 4-5 Fridays in June 2025
        for dt in results:
            assert dt.weekday() == 4  # Friday

    def test_daily_recurrence(self):
        """FREQ=DAILY returns daily occurrences."""
        dtstart = datetime(2025, 6, 1)
        range_start = datetime(2025, 6, 1)
        range_end = datetime(2025, 6, 10)

        results = ViewSpecService._expand_rrule(
            "FREQ=DAILY", dtstart, range_start, range_end,
        )

        assert len(results) == 10  # June 1-10 inclusive

    def test_exdate_excludes_date(self):
        """EXDATE filtering removes excluded date from results."""
        dtstart = datetime(2025, 6, 6)  # Friday
        range_start = datetime(2025, 6, 1)
        range_end = datetime(2025, 7, 4)

        excluded = date(2025, 6, 13)  # Second Friday
        results = ViewSpecService._expand_rrule(
            "FREQ=WEEKLY;BYDAY=FR", dtstart, range_start, range_end,
            exdates=[excluded],
        )

        result_dates = [r.date() for r in results]
        assert excluded not in result_dates
        # Other Fridays still present
        assert date(2025, 6, 6) in result_dates
        assert date(2025, 6, 20) in result_dates

    def test_multiple_exdates(self):
        """Multiple EXDATE values all excluded."""
        dtstart = datetime(2025, 6, 6)
        range_start = datetime(2025, 6, 1)
        range_end = datetime(2025, 7, 4)

        excluded = [date(2025, 6, 13), date(2025, 6, 27)]
        results = ViewSpecService._expand_rrule(
            "FREQ=WEEKLY;BYDAY=FR", dtstart, range_start, range_end,
            exdates=excluded,
        )

        result_dates = [r.date() for r in results]
        for ex in excluded:
            assert ex not in result_dates

    def test_count_limit(self):
        """RRULE with COUNT=5 produces exactly 5 results (within window)."""
        dtstart = datetime(2025, 1, 1)
        range_start = datetime(2025, 1, 1)
        range_end = datetime(2025, 12, 31)

        results = ViewSpecService._expand_rrule(
            "FREQ=MONTHLY;COUNT=5", dtstart, range_start, range_end,
        )

        assert len(results) == 5

    def test_until_limit(self):
        """RRULE with UNTIL=date produces no results past that date."""
        dtstart = datetime(2025, 6, 1)
        range_start = datetime(2025, 6, 1)
        range_end = datetime(2025, 12, 31)

        results = ViewSpecService._expand_rrule(
            "FREQ=WEEKLY;UNTIL=20250701T000000", dtstart, range_start, range_end,
        )

        for dt in results:
            assert dt <= datetime(2025, 7, 1)

    def test_malformed_rrule_returns_empty(self):
        """Malformed RRULE string returns empty list, no exception."""
        dtstart = datetime(2025, 6, 1)
        range_start = datetime(2025, 6, 1)
        range_end = datetime(2025, 7, 1)

        results = ViewSpecService._expand_rrule(
            "NOT_A_VALID_RRULE", dtstart, range_start, range_end,
        )

        assert results == []

    def test_empty_rrule_returns_empty(self):
        """Empty RRULE string returns empty list."""
        dtstart = datetime(2025, 6, 1)
        results = ViewSpecService._expand_rrule(
            "", dtstart, datetime(2025, 6, 1), datetime(2025, 7, 1),
        )
        assert results == []

    def test_max_instances_cap(self):
        """max_instances parameter caps the number of returned occurrences."""
        dtstart = datetime(2025, 1, 1)
        range_start = datetime(2025, 1, 1)
        range_end = datetime(2025, 12, 31)

        results = ViewSpecService._expand_rrule(
            "FREQ=DAILY", dtstart, range_start, range_end,
            max_instances=3,
        )

        assert len(results) == 3

    def test_default_max_instances_is_52(self):
        """Default max_instances is 52 (roughly 1 year of weekly events)."""
        dtstart = datetime(2025, 1, 1)
        range_start = datetime(2025, 1, 1)
        range_end = datetime(2027, 12, 31)  # 3-year window

        results = ViewSpecService._expand_rrule(
            "FREQ=WEEKLY", dtstart, range_start, range_end,
        )

        assert len(results) == 52

    def test_outside_window_returns_empty(self):
        """RRULE with dtstart outside the expansion window returns empty."""
        dtstart = datetime(2020, 1, 1)
        range_start = datetime(2025, 6, 1)
        range_end = datetime(2025, 7, 1)

        results = ViewSpecService._expand_rrule(
            "FREQ=WEEKLY;COUNT=3", dtstart, range_start, range_end,
        )

        # COUNT=3 means only 3 occurrences from dtstart, all in 2020
        assert results == []

    def test_monthly_recurrence(self):
        """FREQ=MONTHLY returns monthly occurrences."""
        dtstart = datetime(2025, 1, 15)
        range_start = datetime(2025, 1, 1)
        range_end = datetime(2025, 6, 30)

        results = ViewSpecService._expand_rrule(
            "FREQ=MONTHLY", dtstart, range_start, range_end,
        )

        assert len(results) == 6  # Jan-Jun on the 15th
        for dt in results:
            assert dt.day == 15


# ── _build_calendar_select with recurrence fields ─────────────


class TestBuildCalendarSelectRecurrence:
    """Verify recurrenceRule and exceptionDates OPTIONAL clauses are present."""

    def test_recurrence_optional_clauses_present(self):
        """SPARQL includes OPTIONAL clauses for recurrenceRule and exceptionDates."""
        query = ViewSpecService._build_calendar_select(
            "urn:test:Task", "urn:test:dueDate",
        )
        assert "?recurrenceRule" in query
        assert "?exceptionDates" in query
        assert "OPTIONAL { ?s <urn:sempkm:model:basic-pkm:recurrenceRule> ?recurrenceRule }" in query
        assert "OPTIONAL { ?s <urn:sempkm:model:basic-pkm:exceptionDates> ?exceptionDates }" in query

    def test_select_includes_recurrence_vars(self):
        """SELECT clause includes both recurrence variables."""
        query = ViewSpecService._build_calendar_select(
            "urn:test:Event", "https://schema.org/startDate",
        )
        assert "?recurrenceRule ?exceptionDates" in query


# ── execute_calendar_query with recurrence ────────────────────


class TestExecuteCalendarQueryRecurrence:
    """Tests for virtual event generation from recurrence rules."""

    @pytest.mark.asyncio
    async def test_recurring_task_produces_virtual_events(self):
        """A task with recurrenceRule generates virtual events."""
        # Use a recent Friday so it falls within the ±6 month expansion window
        from datetime import datetime as dt_mod, timedelta as td_mod
        now = dt_mod.now()
        days_since_fri = (now.weekday() - 4) % 7
        recent_friday = now - td_mod(days=days_since_fri)
        start_str = recent_friday.strftime("%Y-%m-%dT10:00:00")
        end_str = recent_friday.strftime("%Y-%m-%dT11:00:00")

        bindings = [
            {
                "s": {"value": "urn:task:weekly-review"},
                "label": {"value": "Weekly Review"},
                "startDate": {"value": start_str},
                "endDate": {"value": end_str},
                "recurrenceRule": {"value": "FREQ=WEEKLY;BYDAY=FR"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")
        end_field = _make_property("urn:test:endDate", "End Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, end_field,
        )

        events = result["events"]
        # Should have the master event plus multiple virtual ones
        assert len(events) > 1

        master = events[0]
        assert master["id"] == "urn:task:weekly-review"
        assert master["extendedProps"]["recurrenceRule"] == "FREQ=WEEKLY;BYDAY=FR"

        # Virtual events
        virtuals = [e for e in events if e.get("extendedProps", {}).get("isVirtual")]
        assert len(virtuals) >= 4  # at least some Fridays in expansion window

    @pytest.mark.asyncio
    async def test_virtual_events_have_synthetic_id(self):
        """Virtual events use the __recurrence__ ID pattern."""
        bindings = [
            {
                "s": {"value": "urn:task:1"},
                "label": {"value": "Daily"},
                "startDate": {"value": "2025-06-01T09:00:00"},
                "endDate": {"value": "2025-06-01T10:00:00"},
                "recurrenceRule": {"value": "FREQ=DAILY;COUNT=3"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")
        end_field = _make_property("urn:test:endDate", "End Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, end_field,
        )

        virtuals = [e for e in result["events"] if e.get("extendedProps", {}).get("isVirtual")]
        for v in virtuals:
            assert "__recurrence__" in v["id"]
            assert v["id"].startswith("urn:task:1__recurrence__")

    @pytest.mark.asyncio
    async def test_virtual_events_have_isvirtual_and_masteriri(self):
        """Virtual events carry isVirtual=True and masterIri in extendedProps."""
        bindings = [
            {
                "s": {"value": "urn:task:abc"},
                "label": {"value": "Recurring"},
                "startDate": {"value": "2025-06-02T08:00:00"},
                "recurrenceRule": {"value": "FREQ=DAILY;COUNT=3"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, None,
        )

        virtuals = [e for e in result["events"] if e.get("extendedProps", {}).get("isVirtual")]
        for v in virtuals:
            assert v["extendedProps"]["isVirtual"] is True
            assert v["extendedProps"]["masterIri"] == "urn:task:abc"

    @pytest.mark.asyncio
    async def test_master_event_has_recurrence_rule_in_props(self):
        """The master event's extendedProps include recurrenceRule."""
        bindings = [
            {
                "s": {"value": "urn:task:master"},
                "label": {"value": "Master"},
                "startDate": {"value": "2025-06-06T10:00:00"},
                "recurrenceRule": {"value": "FREQ=WEEKLY;BYDAY=FR"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, None,
        )

        master = result["events"][0]
        assert master["id"] == "urn:task:master"
        assert master["extendedProps"]["recurrenceRule"] == "FREQ=WEEKLY;BYDAY=FR"
        # Master is NOT virtual
        assert "isVirtual" not in master["extendedProps"]

    @pytest.mark.asyncio
    async def test_exdates_exclude_virtual_occurrences(self):
        """Exception dates prevent virtual event generation for those dates."""
        # Daily recurrence starting June 1, with June 3 excluded
        bindings = [
            {
                "s": {"value": "urn:task:daily"},
                "label": {"value": "Daily Task"},
                "startDate": {"value": "2025-06-01T09:00:00"},
                "endDate": {"value": "2025-06-01T10:00:00"},
                "recurrenceRule": {"value": "FREQ=DAILY;COUNT=5"},
                "exceptionDates": {"value": "2025-06-03"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")
        end_field = _make_property("urn:test:endDate", "End Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, end_field,
        )

        all_starts = [e["start"] for e in result["events"]]
        # June 3 should not appear (excluded by EXDATE)
        june3_events = [s for s in all_starts if s.startswith("2025-06-03")]
        assert len(june3_events) == 0

    @pytest.mark.asyncio
    async def test_non_recurring_event_unchanged(self):
        """Events without recurrenceRule produce no virtual events."""
        bindings = [
            {
                "s": {"value": "urn:event:plain"},
                "label": {"value": "Plain Event"},
                "startDate": {"value": "2025-06-15T10:00:00"},
                "endDate": {"value": "2025-06-15T11:00:00"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("https://schema.org/startDate", "Start Date")
        end_field = _make_property("https://schema.org/endDate", "End Date")

        result = await svc.execute_calendar_query(
            "urn:test:Event", start_field, end_field,
        )

        assert len(result["events"]) == 1
        assert "recurrenceRule" not in result["events"][0]["extendedProps"]
        assert "isVirtual" not in result["events"][0]["extendedProps"]

    @pytest.mark.asyncio
    async def test_malformed_rrule_graceful_degradation(self):
        """Malformed recurrenceRule produces no virtual events but master event still appears."""
        bindings = [
            {
                "s": {"value": "urn:task:bad-rrule"},
                "label": {"value": "Bad Recurrence"},
                "startDate": {"value": "2025-06-01T09:00:00"},
                "recurrenceRule": {"value": "INVALID_RRULE_STRING"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, None,
        )

        # Master event is present
        assert len(result["events"]) == 1
        assert result["events"][0]["id"] == "urn:task:bad-rrule"
        # recurrenceRule is in extendedProps (so frontend can show indicator)
        assert result["events"][0]["extendedProps"]["recurrenceRule"] == "INVALID_RRULE_STRING"

    @pytest.mark.asyncio
    async def test_allday_recurring_event(self):
        """All-day recurring events (xsd:date, no 'T') produce all-day virtuals."""
        # Use a recent Friday so it falls within the ±6 month expansion window
        from datetime import datetime as dt_mod, timedelta as td_mod
        now = dt_mod.now()
        # Find the most recent Friday
        days_since_fri = (now.weekday() - 4) % 7
        recent_friday = (now - td_mod(days=days_since_fri)).strftime("%Y-%m-%d")

        bindings = [
            {
                "s": {"value": "urn:task:allday"},
                "label": {"value": "All Day Weekly"},
                "startDate": {"value": recent_friday},  # Friday, no time component
                "recurrenceRule": {"value": "FREQ=WEEKLY;BYDAY=FR;COUNT=4"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:dueDate", "Due Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, None,
        )

        events = result["events"]
        # Master + virtuals
        assert len(events) >= 2

        for ev in events:
            assert ev["allDay"] is True

    @pytest.mark.asyncio
    async def test_virtual_event_duration_preserved(self):
        """Virtual events preserve the original event's duration."""
        bindings = [
            {
                "s": {"value": "urn:task:dur"},
                "label": {"value": "2h Meeting"},
                "startDate": {"value": "2025-06-06T10:00:00"},
                "endDate": {"value": "2025-06-06T12:00:00"},  # 2 hours
                "recurrenceRule": {"value": "FREQ=WEEKLY;BYDAY=FR;COUNT=3"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")
        end_field = _make_property("urn:test:endDate", "End Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, end_field,
        )

        virtuals = [e for e in result["events"] if e.get("extendedProps", {}).get("isVirtual")]
        for v in virtuals:
            # Each virtual should have 2-hour duration
            start_dt = datetime.fromisoformat(v["start"])
            end_dt = datetime.fromisoformat(v["end"])
            assert (end_dt - start_dt) == timedelta(hours=2)

    @pytest.mark.asyncio
    async def test_mixed_recurring_and_plain(self):
        """Mix of recurring and non-recurring events in same result set."""
        # Use a recent Friday for recurring task within expansion window
        from datetime import datetime as dt_mod, timedelta as td_mod
        now = dt_mod.now()
        days_since_fri = (now.weekday() - 4) % 7
        recent_friday = now - td_mod(days=days_since_fri)
        start_str = recent_friday.strftime("%Y-%m-%dT10:00:00")
        plain_str = (recent_friday + td_mod(days=4)).strftime("%Y-%m-%dT14:00:00")

        bindings = [
            {
                "s": {"value": "urn:task:recurring"},
                "label": {"value": "Recurring"},
                "startDate": {"value": start_str},
                "recurrenceRule": {"value": "FREQ=WEEKLY;BYDAY=FR;COUNT=3"},
            },
            {
                "s": {"value": "urn:task:plain"},
                "label": {"value": "Plain"},
                "startDate": {"value": plain_str},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        start_field = _make_property("urn:test:startDate", "Start Date")

        result = await svc.execute_calendar_query(
            "urn:test:Task", start_field, None,
        )

        events = result["events"]
        # At least master recurring + some virtuals + plain event
        assert len(events) >= 3

        # Plain event has no virtual marker
        plain = [e for e in events if e["id"] == "urn:task:plain"]
        assert len(plain) == 1
        assert "isVirtual" not in plain[0]["extendedProps"]

        # Recurring has virtuals
        virtuals = [e for e in events if e.get("extendedProps", {}).get("isVirtual")]
        assert len(virtuals) >= 1
