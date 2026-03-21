"""Unit tests for Outlook Calendar field mapper.

Loads ``field_mapper.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package.  All functions are pure —
no mocks needed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Load field_mapper module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "outlook-calendar"
    / "services"
    / "field_mapper.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("outlook_field_mapper", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["outlook_field_mapper"] = mod
    spec.loader.exec_module(mod)
    return mod


fm = _load_module()

BPKM = fm.BPKM

SYNC_TIME = "2026-03-18T12:00:00+00:00"


# ---------------------------------------------------------------------------
# Fixture factory — builds an Outlook event dict with defaults
# ---------------------------------------------------------------------------

def _make_event(**overrides) -> dict:
    """Build a minimal Outlook Graph API event dict with sensible defaults."""
    base = {
        "id": "AAMkAGI2abc123",
        "subject": "Team Standup",
        "webLink": "https://outlook.office365.com/owa/?itemid=abc123",
        "createdDateTime": "2026-01-10T08:00:00.0000000Z",
        "lastModifiedDateTime": "2026-03-15T14:30:00.0000000Z",
        "isAllDay": False,
        "isCancelled": False,
        "sensitivity": "normal",
        "showAs": "busy",
        "isReminderOn": False,
        "start": {
            "dateTime": "2026-03-20T09:00:00.0000000",
            "timeZone": "America/New_York",
        },
        "end": {
            "dateTime": "2026-03-20T09:30:00.0000000",
            "timeZone": "America/New_York",
        },
        "responseStatus": {
            "response": "organizer",
            "time": "0001-01-01T00:00:00Z",
        },
    }
    base.update(overrides)
    return base


# ===================================================================
# compute_event_slug tests
# ===================================================================

class TestComputeEventSlug:
    def test_deterministic(self):
        slug1 = fm.compute_event_slug("cal-id-123", "evt-abc")
        slug2 = fm.compute_event_slug("cal-id-123", "evt-abc")
        assert slug1 == slug2

    def test_different_inputs_differ(self):
        slug_a = fm.compute_event_slug("calA", "evt1")
        slug_b = fm.compute_event_slug("calB", "evt1")
        assert slug_a != slug_b

    def test_format_16_hex_chars(self):
        slug = fm.compute_event_slug("calendar", "event99")
        assert len(slug) == 16
        int(slug, 16)  # valid hex


# ===================================================================
# detect_all_day tests
# ===================================================================

class TestDetectAllDay:
    def test_timed_event(self):
        event = _make_event()
        is_all_day, start, end = fm.detect_all_day(event)
        assert is_all_day is False
        assert start == "2026-03-20T09:00:00.0000000"
        assert end == "2026-03-20T09:30:00.0000000"

    def test_all_day_event(self):
        event = _make_event(isAllDay=True)
        is_all_day, start, end = fm.detect_all_day(event)
        assert is_all_day is True
        assert start == "2026-03-20T09:00:00.0000000"

    def test_missing_field_defaults_false(self):
        event = _make_event()
        del event["isAllDay"]
        is_all_day, start, end = fm.detect_all_day(event)
        assert is_all_day is False


# ===================================================================
# extract_conference_url tests
# ===================================================================

class TestExtractConferenceUrl:
    def test_online_meeting_join_url(self):
        event = _make_event(onlineMeeting={
            "joinUrl": "https://teams.microsoft.com/l/meetup-join/abc123"
        })
        assert fm.extract_conference_url(event) == "https://teams.microsoft.com/l/meetup-join/abc123"

    def test_online_meeting_url_fallback(self):
        event = _make_event(
            onlineMeetingUrl="https://teams.live.com/meet/xyz"
        )
        assert fm.extract_conference_url(event) == "https://teams.live.com/meet/xyz"

    def test_neither_present(self):
        event = _make_event()
        assert fm.extract_conference_url(event) is None

    def test_join_url_preferred_over_fallback(self):
        event = _make_event(
            onlineMeeting={"joinUrl": "https://teams.com/primary"},
            onlineMeetingUrl="https://teams.com/fallback",
        )
        assert fm.extract_conference_url(event) == "https://teams.com/primary"


# ===================================================================
# extract_response_status tests
# ===================================================================

class TestExtractResponseStatus:
    def test_none_response(self):
        event = _make_event(responseStatus={"response": "none"})
        assert fm.extract_response_status(event) == "needs-action"

    def test_organizer_response(self):
        event = _make_event(responseStatus={"response": "organizer"})
        assert fm.extract_response_status(event) == "accepted"

    def test_tentatively_accepted_response(self):
        event = _make_event(responseStatus={"response": "tentativelyAccepted"})
        assert fm.extract_response_status(event) == "tentative"

    def test_accepted_response(self):
        event = _make_event(responseStatus={"response": "accepted"})
        assert fm.extract_response_status(event) == "accepted"

    def test_declined_response(self):
        event = _make_event(responseStatus={"response": "declined"})
        assert fm.extract_response_status(event) == "declined"

    def test_not_responded(self):
        event = _make_event(responseStatus={"response": "notResponded"})
        assert fm.extract_response_status(event) == "needs-action"

    def test_missing_response_status(self):
        event = _make_event()
        del event["responseStatus"]
        assert fm.extract_response_status(event) is None


# ===================================================================
# derive_event_status tests
# ===================================================================

class TestDeriveEventStatus:
    def test_cancelled(self):
        event = _make_event(isCancelled=True)
        assert fm.derive_event_status(event) == "cancelled"

    def test_tentatively_accepted(self):
        event = _make_event(
            isCancelled=False,
            responseStatus={"response": "tentativelyAccepted"},
        )
        assert fm.derive_event_status(event) == "tentative"

    def test_default_confirmed(self):
        event = _make_event()
        assert fm.derive_event_status(event) == "confirmed"


# ===================================================================
# strip_html_tags tests
# ===================================================================

class TestStripHtmlTags:
    def test_basic_html(self):
        assert fm.strip_html_tags("<p>Hello world</p>") == "Hello world"

    def test_nested_tags(self):
        assert fm.strip_html_tags("<div><b>Bold</b> text</div>") == "Bold text"

    def test_empty_string(self):
        assert fm.strip_html_tags("") == ""


# ===================================================================
# extract_body tests
# ===================================================================

class TestExtractBody:
    def test_html_body_with_strip_fallback(self):
        """When markdownify is unavailable, HTML is stripped via regex."""
        event = _make_event(body={
            "contentType": "html",
            "content": "<p>Meeting notes</p>",
        })
        # Force the strip_html_tags path
        original_md = fm.md
        try:
            fm.md = None
            result = fm.extract_body(event)
            assert result == "Meeting notes"
        finally:
            fm.md = original_md

    def test_html_body_with_markdownify(self):
        """When markdownify is available, it is used for HTML conversion."""
        event = _make_event(body={
            "contentType": "html",
            "content": "<h1>Title</h1><p>Paragraph</p>",
        })
        if fm.md is not None:
            result = fm.extract_body(event)
            # markdownify should produce markdown, not raw HTML
            assert "<h1>" not in (result or "")
            assert "Title" in (result or "")
        else:
            pytest.skip("markdownify not installed")

    def test_plain_text_body(self):
        event = _make_event(body={
            "contentType": "text",
            "content": "Just some text",
        })
        assert fm.extract_body(event) == "Just some text"

    def test_empty_body(self):
        event = _make_event(body={
            "contentType": "text",
            "content": "",
        })
        assert fm.extract_body(event) is None

    def test_missing_body(self):
        event = _make_event()
        assert fm.extract_body(event) is None

    def test_whitespace_only_html_body(self):
        event = _make_event(body={
            "contentType": "html",
            "content": "   \n  ",
        })
        assert fm.extract_body(event) is None


# ===================================================================
# extract_categories_as_tags tests
# ===================================================================

class TestExtractCategoriesAsTags:
    def test_array_with_items(self):
        event = _make_event(categories=["Work", "Urgent", "Project X"])
        assert fm.extract_categories_as_tags(event) == "Work,Urgent,Project X"

    def test_empty_array(self):
        event = _make_event(categories=[])
        assert fm.extract_categories_as_tags(event) is None

    def test_missing_categories(self):
        event = _make_event()
        assert fm.extract_categories_as_tags(event) is None

    def test_single_category(self):
        event = _make_event(categories=["Personal"])
        assert fm.extract_categories_as_tags(event) == "Personal"


# ===================================================================
# SHOW_AS_MAP constant tests
# ===================================================================

class TestShowAsMap:
    def test_free(self):
        assert fm.SHOW_AS_MAP["free"] == "free"

    def test_tentative(self):
        assert fm.SHOW_AS_MAP["tentative"] == "tentative"

    def test_busy(self):
        assert fm.SHOW_AS_MAP["busy"] == "busy"

    def test_oof(self):
        assert fm.SHOW_AS_MAP["oof"] == "out-of-office"

    def test_working_elsewhere(self):
        assert fm.SHOW_AS_MAP["workingElsewhere"] == "working-elsewhere"

    def test_unknown(self):
        assert fm.SHOW_AS_MAP["unknown"] == "busy"


# ===================================================================
# SENSITIVITY_MAP constant tests
# ===================================================================

class TestSensitivityMap:
    def test_normal_is_none(self):
        assert fm.SENSITIVITY_MAP["normal"] is None

    def test_personal_is_none(self):
        assert fm.SENSITIVITY_MAP["personal"] is None

    def test_private(self):
        assert fm.SENSITIVITY_MAP["private"] == "private"

    def test_confidential(self):
        assert fm.SENSITIVITY_MAP["confidential"] == "confidential"


# ===================================================================
# RESPONSE_STATUS_MAP constant tests
# ===================================================================

class TestResponseStatusMap:
    def test_all_entries(self):
        assert fm.RESPONSE_STATUS_MAP == {
            "none": "needs-action",
            "organizer": "accepted",
            "tentativelyAccepted": "tentative",
            "accepted": "accepted",
            "declined": "declined",
            "notResponded": "needs-action",
        }


# ===================================================================
# REVERSE_RESPONSE_STATUS_MAP constant tests
# ===================================================================

class TestReverseResponseStatusMap:
    def test_all_entries(self):
        assert fm.REVERSE_RESPONSE_STATUS_MAP == {
            "needs-action": "notResponded",
            "accepted": "accepted",
            "declined": "declined",
            "tentative": "tentativelyAccepted",
        }

    def test_round_trip_where_reversible(self):
        """accepted→accepted→accepted, declined→declined→declined, tentative round-trips."""
        for bpkm_val, outlook_val in fm.REVERSE_RESPONSE_STATUS_MAP.items():
            assert fm.RESPONSE_STATUS_MAP.get(outlook_val) == bpkm_val


# ===================================================================
# convert_recurrence_to_rrule — 18 combinations + edge cases
# ===================================================================

class TestConvertRecurrenceToRrule:
    """Tests for all 6 pattern types × 3 range types = 18 basic combos
    plus edge cases."""

    # --- daily × 3 ranges ---

    def test_daily_no_end(self):
        rec = {
            "pattern": {"type": "daily", "interval": 1},
            "range": {"type": "noEnd", "startDate": "2026-03-01"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=DAILY"

    def test_daily_end_date(self):
        rec = {
            "pattern": {"type": "daily", "interval": 1},
            "range": {"type": "endDate", "startDate": "2026-03-01", "endDate": "2026-06-30"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=DAILY;UNTIL=20260630T000000Z"

    def test_daily_numbered(self):
        rec = {
            "pattern": {"type": "daily", "interval": 1},
            "range": {"type": "numbered", "startDate": "2026-03-01", "numberOfOccurrences": 10},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=DAILY;COUNT=10"

    # --- weekly × 3 ranges ---

    def test_weekly_no_end(self):
        rec = {
            "pattern": {"type": "weekly", "interval": 1, "daysOfWeek": ["monday", "wednesday", "friday"]},
            "range": {"type": "noEnd", "startDate": "2026-03-01"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=WEEKLY;BYDAY=MO,WE,FR"

    def test_weekly_end_date(self):
        rec = {
            "pattern": {"type": "weekly", "interval": 1, "daysOfWeek": ["tuesday"]},
            "range": {"type": "endDate", "startDate": "2026-03-01", "endDate": "2026-12-31"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=WEEKLY;BYDAY=TU;UNTIL=20261231T000000Z"

    def test_weekly_numbered(self):
        rec = {
            "pattern": {"type": "weekly", "interval": 1, "daysOfWeek": ["thursday"]},
            "range": {"type": "numbered", "startDate": "2026-03-01", "numberOfOccurrences": 5},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=WEEKLY;BYDAY=TH;COUNT=5"

    # --- absoluteMonthly × 3 ranges ---

    def test_absolute_monthly_no_end(self):
        rec = {
            "pattern": {"type": "absoluteMonthly", "interval": 1, "dayOfMonth": 15},
            "range": {"type": "noEnd", "startDate": "2026-01-15"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=MONTHLY;BYMONTHDAY=15"

    def test_absolute_monthly_end_date(self):
        rec = {
            "pattern": {"type": "absoluteMonthly", "interval": 1, "dayOfMonth": 1},
            "range": {"type": "endDate", "startDate": "2026-01-01", "endDate": "2026-12-31"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=MONTHLY;BYMONTHDAY=1;UNTIL=20261231T000000Z"

    def test_absolute_monthly_numbered(self):
        rec = {
            "pattern": {"type": "absoluteMonthly", "interval": 1, "dayOfMonth": 28},
            "range": {"type": "numbered", "startDate": "2026-01-28", "numberOfOccurrences": 12},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=MONTHLY;BYMONTHDAY=28;COUNT=12"

    # --- relativeMonthly × 3 ranges ---

    def test_relative_monthly_no_end(self):
        rec = {
            "pattern": {"type": "relativeMonthly", "interval": 1, "daysOfWeek": ["tuesday"], "index": "second"},
            "range": {"type": "noEnd", "startDate": "2026-01-01"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=MONTHLY;BYDAY=2TU"

    def test_relative_monthly_end_date(self):
        rec = {
            "pattern": {"type": "relativeMonthly", "interval": 1, "daysOfWeek": ["monday"], "index": "first"},
            "range": {"type": "endDate", "startDate": "2026-01-01", "endDate": "2026-07-01"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=MONTHLY;BYDAY=1MO;UNTIL=20260701T000000Z"

    def test_relative_monthly_numbered(self):
        rec = {
            "pattern": {"type": "relativeMonthly", "interval": 1, "daysOfWeek": ["friday"], "index": "third"},
            "range": {"type": "numbered", "startDate": "2026-01-01", "numberOfOccurrences": 6},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=MONTHLY;BYDAY=3FR;COUNT=6"

    # --- absoluteYearly × 3 ranges ---

    def test_absolute_yearly_no_end(self):
        rec = {
            "pattern": {"type": "absoluteYearly", "interval": 1, "month": 3, "dayOfMonth": 15},
            "range": {"type": "noEnd", "startDate": "2026-03-15"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=YEARLY;BYMONTH=3;BYMONTHDAY=15"

    def test_absolute_yearly_end_date(self):
        rec = {
            "pattern": {"type": "absoluteYearly", "interval": 1, "month": 12, "dayOfMonth": 25},
            "range": {"type": "endDate", "startDate": "2026-12-25", "endDate": "2030-12-25"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=YEARLY;BYMONTH=12;BYMONTHDAY=25;UNTIL=20301225T000000Z"

    def test_absolute_yearly_numbered(self):
        rec = {
            "pattern": {"type": "absoluteYearly", "interval": 1, "month": 7, "dayOfMonth": 4},
            "range": {"type": "numbered", "startDate": "2026-07-04", "numberOfOccurrences": 3},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=YEARLY;BYMONTH=7;BYMONTHDAY=4;COUNT=3"

    # --- relativeYearly × 3 ranges ---

    def test_relative_yearly_no_end(self):
        rec = {
            "pattern": {"type": "relativeYearly", "interval": 1, "month": 11, "daysOfWeek": ["thursday"], "index": "fourth"},
            "range": {"type": "noEnd", "startDate": "2026-11-01"},
        }
        # US Thanksgiving: 4th Thursday of November
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=YEARLY;BYMONTH=11;BYDAY=4TH"

    def test_relative_yearly_end_date(self):
        rec = {
            "pattern": {"type": "relativeYearly", "interval": 1, "month": 5, "daysOfWeek": ["monday"], "index": "last"},
            "range": {"type": "endDate", "startDate": "2026-05-01", "endDate": "2030-05-31"},
        }
        # US Memorial Day: last Monday of May
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=YEARLY;BYMONTH=5;BYDAY=-1MO;UNTIL=20300531T000000Z"

    def test_relative_yearly_numbered(self):
        rec = {
            "pattern": {"type": "relativeYearly", "interval": 1, "month": 1, "daysOfWeek": ["monday"], "index": "third"},
            "range": {"type": "numbered", "startDate": "2026-01-01", "numberOfOccurrences": 5},
        }
        # MLK Day: 3rd Monday of January
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=YEARLY;BYMONTH=1;BYDAY=3MO;COUNT=5"

    # --- Edge cases ---

    def test_interval_greater_than_one(self):
        rec = {
            "pattern": {"type": "daily", "interval": 3},
            "range": {"type": "noEnd", "startDate": "2026-01-01"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=DAILY;INTERVAL=3"

    def test_weekly_interval_biweekly(self):
        rec = {
            "pattern": {"type": "weekly", "interval": 2, "daysOfWeek": ["monday"]},
            "range": {"type": "noEnd", "startDate": "2026-01-01"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=WEEKLY;BYDAY=MO;INTERVAL=2"

    def test_multiple_days_of_week(self):
        rec = {
            "pattern": {"type": "weekly", "interval": 1, "daysOfWeek": ["monday", "tuesday", "wednesday", "thursday", "friday"]},
            "range": {"type": "noEnd", "startDate": "2026-01-01"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"

    def test_none_recurrence(self):
        assert fm.convert_recurrence_to_rrule(None) is None

    def test_empty_dict_recurrence(self):
        assert fm.convert_recurrence_to_rrule({}) is None

    def test_relative_monthly_last_friday(self):
        rec = {
            "pattern": {"type": "relativeMonthly", "interval": 1, "daysOfWeek": ["friday"], "index": "last"},
            "range": {"type": "noEnd", "startDate": "2026-01-01"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=MONTHLY;BYDAY=-1FR"

    def test_unknown_pattern_type(self):
        rec = {
            "pattern": {"type": "custom", "interval": 1},
            "range": {"type": "noEnd"},
        }
        assert fm.convert_recurrence_to_rrule(rec) is None

    def test_monthly_interval_quarterly(self):
        rec = {
            "pattern": {"type": "absoluteMonthly", "interval": 3, "dayOfMonth": 1},
            "range": {"type": "noEnd", "startDate": "2026-01-01"},
        }
        assert fm.convert_recurrence_to_rrule(rec) == "FREQ=MONTHLY;BYMONTHDAY=1;INTERVAL=3"


# ===================================================================
# build_event_properties tests
# ===================================================================

class TestBuildEventProperties:
    def test_full_event(self):
        """Timed event with all core fields present."""
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)

        assert props["dcterms:title"] == "Team Standup"
        assert props["schema:startDate"] == "2026-03-20T09:00:00.0000000"
        assert props["schema:endDate"] == "2026-03-20T09:30:00.0000000"
        assert props[f"{BPKM}allDay"] == "false"
        assert props[f"{BPKM}timeZone"] == "America/New_York"
        assert props[f"{BPKM}eventStatus"] == "confirmed"
        assert props[f"{BPKM}showAs"] == "busy"
        assert props[f"{BPKM}externalId"] == "AAMkAGI2abc123"
        assert props[f"{BPKM}externalUrl"] == "https://outlook.office365.com/owa/?itemid=abc123"
        assert props[f"{BPKM}externalProvider"] == "outlook-calendar"
        assert props[f"{BPKM}lastSyncedAt"] == SYNC_TIME
        assert props[f"{BPKM}calendarName"] == "Work"
        assert props[f"{BPKM}responseStatus"] == "accepted"  # organizer → accepted
        assert props["dcterms:created"] == "2026-01-10T08:00:00.0000000Z"
        assert props["dcterms:modified"] == "2026-03-15T14:30:00.0000000Z"

    def test_minimal_event(self):
        """Event with only required fields — most optional fields absent."""
        event = {
            "id": "min1",
            "subject": "Quick sync",
            "start": {"dateTime": "2026-03-20T10:00:00Z"},
            "end": {"dateTime": "2026-03-20T10:15:00Z"},
        }
        props = fm.build_event_properties(event, "Cal", SYNC_TIME)
        assert props["dcterms:title"] == "Quick sync"
        assert props[f"{BPKM}allDay"] == "false"
        assert props[f"{BPKM}eventStatus"] == "confirmed"
        assert props[f"{BPKM}externalProvider"] == "outlook-calendar"
        # Optional fields should be absent
        assert f"{BPKM}location" not in props
        assert f"{BPKM}visibility" not in props
        assert f"{BPKM}conferenceUrl" not in props
        assert f"{BPKM}recurrenceRule" not in props
        assert f"{BPKM}recurringEventId" not in props
        assert f"{BPKM}reminderMinutes" not in props
        assert f"{BPKM}tags" not in props

    def test_outlook_specific_fields(self):
        """Outlook-specific fields: showAs, sensitivity, categories, conferenceUrl."""
        event = _make_event(
            showAs="oof",
            sensitivity="confidential",
            categories=["Project Alpha", "Urgent"],
            onlineMeeting={"joinUrl": "https://teams.microsoft.com/l/meetup"},
            location={"displayName": "Conference Room B"},
            isReminderOn=True,
            reminderMinutesBeforeStart=15,
            seriesMasterId="AAMkAGI2master999",
        )
        props = fm.build_event_properties(event, "Calendar", SYNC_TIME)
        assert props[f"{BPKM}showAs"] == "out-of-office"
        assert props[f"{BPKM}visibility"] == "confidential"
        assert props[f"{BPKM}tags"] == "Project Alpha,Urgent"
        assert props[f"{BPKM}conferenceUrl"] == "https://teams.microsoft.com/l/meetup"
        assert props[f"{BPKM}location"] == "Conference Room B"
        assert props[f"{BPKM}reminderMinutes"] == "15"
        assert props[f"{BPKM}recurringEventId"] == "AAMkAGI2master999"

    def test_sensitivity_normal_omits_visibility(self):
        """Normal sensitivity → no visibility property."""
        event = _make_event(sensitivity="normal")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}visibility" not in props

    def test_sensitivity_personal_omits_visibility(self):
        """Personal sensitivity → no visibility property."""
        event = _make_event(sensitivity="personal")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}visibility" not in props

    def test_sensitivity_private_maps_visibility(self):
        event = _make_event(sensitivity="private")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}visibility"] == "private"

    def test_categories_as_tags(self):
        event = _make_event(categories=["Work", "Review"])
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}tags"] == "Work,Review"

    def test_no_categories_omits_tags(self):
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}tags" not in props

    def test_all_day_event(self):
        event = _make_event(isAllDay=True)
        props = fm.build_event_properties(event, "Personal", SYNC_TIME)
        assert props[f"{BPKM}allDay"] == "true"

    def test_missing_subject_defaults_no_title(self):
        event = _make_event()
        del event["subject"]
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props["dcterms:title"] == "(No title)"

    def test_empty_subject_defaults_no_title(self):
        event = _make_event(subject="")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props["dcterms:title"] == "(No title)"

    def test_none_values_excluded(self):
        """No key in the output dict should have a None value."""
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        for k, v in props.items():
            assert v is not None, f"Key {k!r} has None value"

    def test_external_provider_always_outlook(self):
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}externalProvider"] == "outlook-calendar"

    def test_all_day_string_true(self):
        """bpkm:allDay must be string 'true', not boolean."""
        event = _make_event(isAllDay=True)
        props = fm.build_event_properties(event, "Cal", SYNC_TIME)
        assert props[f"{BPKM}allDay"] == "true"
        assert isinstance(props[f"{BPKM}allDay"], str)

    def test_timed_string_false(self):
        """bpkm:allDay must be string 'false', not boolean."""
        event = _make_event()
        props = fm.build_event_properties(event, "Cal", SYNC_TIME)
        assert props[f"{BPKM}allDay"] == "false"
        assert isinstance(props[f"{BPKM}allDay"], str)

    def test_reminder_enabled(self):
        event = _make_event(isReminderOn=True, reminderMinutesBeforeStart=30)
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}reminderMinutes"] == "30"

    def test_reminder_disabled_omits(self):
        event = _make_event(isReminderOn=False, reminderMinutesBeforeStart=15)
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}reminderMinutes" not in props

    def test_body_html_in_properties(self):
        """HTML body appears as dcterms:description after conversion."""
        event = _make_event(body={
            "contentType": "html",
            "content": "<p>Agenda items</p>",
        })
        # Use strip fallback to avoid markdownify dependency
        original_md = fm.md
        try:
            fm.md = None
            props = fm.build_event_properties(event, "Work", SYNC_TIME)
            assert props["dcterms:description"] == "Agenda items"
        finally:
            fm.md = original_md

    def test_recurrence_in_properties(self):
        event = _make_event(recurrence={
            "pattern": {"type": "weekly", "interval": 1, "daysOfWeek": ["monday"]},
            "range": {"type": "noEnd", "startDate": "2026-03-01"},
        })
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}recurrenceRule"] == "FREQ=WEEKLY;BYDAY=MO"

    def test_show_as_all_values(self):
        """All showAs values map correctly through build_event_properties."""
        for outlook_val, expected in fm.SHOW_AS_MAP.items():
            event = _make_event(showAs=outlook_val)
            props = fm.build_event_properties(event, "W", SYNC_TIME)
            assert props[f"{BPKM}showAs"] == expected, f"showAs={outlook_val}"


# ===================================================================
# build_event_patch tests
# ===================================================================

class TestBuildEventPatch:
    def test_accepted_mapping(self):
        props = {f"{BPKM}responseStatus": "accepted"}
        result = fm.build_event_patch(props, "user@outlook.com")
        assert result == {
            "attendees": [
                {
                    "emailAddress": {"address": "user@outlook.com"},
                    "status": {"response": "accepted"},
                }
            ],
        }

    def test_declined_mapping(self):
        props = {f"{BPKM}responseStatus": "declined"}
        result = fm.build_event_patch(props, "user@outlook.com")
        assert result["attendees"][0]["status"]["response"] == "declined"

    def test_tentative_mapping(self):
        props = {f"{BPKM}responseStatus": "tentative"}
        result = fm.build_event_patch(props, "user@outlook.com")
        assert result["attendees"][0]["status"]["response"] == "tentativelyAccepted"

    def test_needs_action_mapping(self):
        props = {f"{BPKM}responseStatus": "needs-action"}
        result = fm.build_event_patch(props, "user@outlook.com")
        assert result["attendees"][0]["status"]["response"] == "notResponded"

    def test_no_status_returns_empty(self):
        props = {f"{BPKM}eventStatus": "confirmed"}
        result = fm.build_event_patch(props, "user@outlook.com")
        assert result == {}

    def test_unknown_status_returns_empty(self):
        props = {f"{BPKM}responseStatus": "maybe-later"}
        result = fm.build_event_patch(props, "user@outlook.com")
        assert result == {}

    def test_email_matches_input(self):
        props = {f"{BPKM}responseStatus": "accepted"}
        result = fm.build_event_patch(props, "specific@company.com")
        assert result["attendees"][0]["emailAddress"]["address"] == "specific@company.com"

    def test_outlook_attendee_structure(self):
        """Verify the Outlook-specific structure differs from Google's."""
        props = {f"{BPKM}responseStatus": "accepted"}
        result = fm.build_event_patch(props, "user@outlook.com")
        att = result["attendees"][0]
        # Outlook uses nested emailAddress/status objects, not flat email/self/responseStatus
        assert "emailAddress" in att
        assert "status" in att
        assert "email" not in att  # Google's format
        assert "self" not in att   # Google's format


# ===================================================================
# DAY_OF_WEEK_MAP constant tests
# ===================================================================

class TestDayOfWeekMap:
    def test_all_seven_days(self):
        assert fm.DAY_OF_WEEK_MAP == {
            "sunday": "SU",
            "monday": "MO",
            "tuesday": "TU",
            "wednesday": "WE",
            "thursday": "TH",
            "friday": "FR",
            "saturday": "SA",
        }


# ===================================================================
# RELATIVE_INDEX_MAP constant tests
# ===================================================================

class TestRelativeIndexMap:
    def test_all_entries(self):
        assert fm.RELATIVE_INDEX_MAP == {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "last": -1,
        }


# ===================================================================
# extract_rrule wrapper tests
# ===================================================================

class TestExtractRrule:
    def test_with_recurrence(self):
        event = _make_event(recurrence={
            "pattern": {"type": "daily", "interval": 1},
            "range": {"type": "noEnd"},
        })
        assert fm.extract_rrule(event) == "FREQ=DAILY"

    def test_without_recurrence(self):
        event = _make_event()
        assert fm.extract_rrule(event) is None
