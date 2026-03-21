"""Exhaustive tests for CalDAV iCalendar field mapper.

Tests build real icalendar.Event components using the library's `.add()` API
rather than mocking internals — this validates actual library behavior.

Loads ``field_mapper.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package (same pattern as test_caldav_client).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from icalendar import Alarm, Calendar, Event
from icalendar import vCalAddress

# ---------------------------------------------------------------------------
# Load module from apps directory (hyphenated dir name can't be imported)
# ---------------------------------------------------------------------------

_APPS_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "caldav-calendar"
_SERVICES_DIR = _APPS_DIR / "services"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fm = _load_module("caldav_field_mapper", _SERVICES_DIR / "field_mapper.py")

BPKM = fm.BPKM
STATUS_MAP = fm.STATUS_MAP
CLASS_MAP = fm.CLASS_MAP
TRANSP_MAP = fm.TRANSP_MAP
PARTSTAT_MAP = fm.PARTSTAT_MAP
REVERSE_RESPONSE_STATUS_MAP = fm.REVERSE_RESPONSE_STATUS_MAP

compute_event_slug = fm.compute_event_slug
detect_all_day = fm.detect_all_day
extract_timezone = fm.extract_timezone
extract_status = fm.extract_status
extract_visibility = fm.extract_visibility
extract_show_as = fm.extract_show_as
extract_rrule = fm.extract_rrule
extract_recurrence_id = fm.extract_recurrence_id
extract_attendees = fm.extract_attendees
extract_self_response_status = fm.extract_self_response_status
extract_organizer = fm.extract_organizer
extract_reminder_minutes = fm.extract_reminder_minutes
extract_categories = fm.extract_categories
strip_html_tags = fm.strip_html_tags
extract_body = fm.extract_body
build_event_properties = fm.build_event_properties
build_event_patch = fm.build_event_patch
modify_vevent_partstat = fm.modify_vevent_partstat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(**kwargs) -> Event:
    """Create a minimal icalendar Event with given properties."""
    e = Event()
    for key, val in kwargs.items():
        e.add(key, val)
    return e


def _make_attendee(email: str, cn: str | None = None, partstat: str | None = None) -> vCalAddress:
    """Create a vCalAddress attendee with optional params."""
    addr = vCalAddress(f"mailto:{email}")
    if cn:
        addr.params["CN"] = cn
    if partstat:
        addr.params["PARTSTAT"] = partstat
    return addr


# ===========================================================================
# compute_event_slug
# ===========================================================================


class TestComputeEventSlug:
    def test_deterministic(self):
        slug1 = compute_event_slug("/cal/personal/", "uid-123")
        slug2 = compute_event_slug("/cal/personal/", "uid-123")
        assert slug1 == slug2

    def test_prefix(self):
        slug = compute_event_slug("/cal/personal/", "uid-123")
        assert slug.startswith("caldav-")

    def test_length(self):
        slug = compute_event_slug("/cal/personal/", "uid-123")
        # "caldav-" (7) + 12 hex chars = 19
        assert len(slug) == 19

    def test_different_inputs_different_slugs(self):
        slug1 = compute_event_slug("/cal/a/", "uid-1")
        slug2 = compute_event_slug("/cal/b/", "uid-1")
        slug3 = compute_event_slug("/cal/a/", "uid-2")
        assert slug1 != slug2
        assert slug1 != slug3
        assert slug2 != slug3

    def test_hex_chars(self):
        slug = compute_event_slug("/cal/", "uid")
        suffix = slug[len("caldav-"):]
        assert len(suffix) == 12
        int(suffix, 16)  # Should not raise


# ===========================================================================
# detect_all_day
# ===========================================================================


class TestDetectAllDay:
    def test_timed_event(self):
        e = _make_event(
            DTSTART=datetime(2025, 3, 15, 10, 0, 0, tzinfo=ZoneInfo("America/New_York")),
            DTEND=datetime(2025, 3, 15, 11, 0, 0, tzinfo=ZoneInfo("America/New_York")),
        )
        is_all_day, start, end = detect_all_day(e)
        assert is_all_day is False
        assert "T10:00:00" in start
        assert "T11:00:00" in end

    def test_all_day_event(self):
        e = _make_event(DTSTART=date(2025, 3, 15), DTEND=date(2025, 3, 16))
        is_all_day, start, end = detect_all_day(e)
        assert is_all_day is True
        assert start == "2025-03-15"
        assert end == "2025-03-16"

    def test_timezone_aware_datetime(self):
        e = _make_event(
            DTSTART=datetime(2025, 6, 1, 14, 30, 0, tzinfo=timezone.utc),
            DTEND=datetime(2025, 6, 1, 15, 30, 0, tzinfo=timezone.utc),
        )
        is_all_day, start, end = detect_all_day(e)
        assert is_all_day is False
        assert start is not None
        assert "+00:00" in start or "Z" in start

    def test_no_dtstart(self):
        e = Event()
        is_all_day, start, end = detect_all_day(e)
        assert is_all_day is False
        assert start is None
        assert end is None

    def test_dtstart_only_no_dtend(self):
        e = _make_event(DTSTART=datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc))
        is_all_day, start, end = detect_all_day(e)
        assert is_all_day is False
        assert start is not None
        assert end is None


# ===========================================================================
# extract_timezone
# ===========================================================================


class TestExtractTimezone:
    def test_tzid_present(self):
        e = _make_event(DTSTART=datetime(2025, 1, 15, 10, 0, 0, tzinfo=ZoneInfo("America/New_York")))
        tz = extract_timezone(e)
        assert tz is not None
        assert "New_York" in tz or "America" in tz

    def test_utc(self):
        e = _make_event(DTSTART=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc))
        tz = extract_timezone(e)
        assert tz == "UTC"

    def test_no_dtstart(self):
        e = Event()
        tz = extract_timezone(e)
        assert tz is None

    def test_all_day_no_timezone(self):
        e = _make_event(DTSTART=date(2025, 3, 15))
        tz = extract_timezone(e)
        # All-day dates don't have timezone
        assert tz is None


# ===========================================================================
# extract_status
# ===========================================================================


class TestExtractStatus:
    def test_tentative(self):
        e = _make_event(STATUS="TENTATIVE")
        assert extract_status(e) == "tentative"

    def test_confirmed(self):
        e = _make_event(STATUS="CONFIRMED")
        assert extract_status(e) == "confirmed"

    def test_cancelled(self):
        e = _make_event(STATUS="CANCELLED")
        assert extract_status(e) == "cancelled"

    def test_missing(self):
        e = Event()
        assert extract_status(e) is None

    def test_unknown_value(self):
        e = _make_event(STATUS="DRAFT")
        assert extract_status(e) is None

    def test_case_insensitive(self):
        e = _make_event(STATUS="CONFIRMED")
        assert extract_status(e) == "confirmed"


# ===========================================================================
# extract_visibility
# ===========================================================================


class TestExtractVisibility:
    def test_public(self):
        e = _make_event(CLASS="PUBLIC")
        assert extract_visibility(e) == "public"

    def test_private(self):
        e = _make_event(CLASS="PRIVATE")
        assert extract_visibility(e) == "private"

    def test_confidential(self):
        e = _make_event(CLASS="CONFIDENTIAL")
        assert extract_visibility(e) == "confidential"

    def test_missing(self):
        e = Event()
        assert extract_visibility(e) is None


# ===========================================================================
# extract_show_as
# ===========================================================================


class TestExtractShowAs:
    def test_opaque(self):
        e = _make_event(TRANSP="OPAQUE")
        assert extract_show_as(e) == "busy"

    def test_transparent(self):
        e = _make_event(TRANSP="TRANSPARENT")
        assert extract_show_as(e) == "free"

    def test_missing(self):
        e = Event()
        assert extract_show_as(e) is None


# ===========================================================================
# extract_rrule
# ===========================================================================


class TestExtractRrule:
    def test_weekly_rule(self):
        e = _make_event(RRULE={"FREQ": "WEEKLY", "BYDAY": "MO"})
        rule = extract_rrule(e)
        assert rule is not None
        assert "FREQ=WEEKLY" in rule
        assert "BYDAY=MO" in rule

    def test_daily_rule(self):
        e = _make_event(RRULE={"FREQ": "DAILY", "COUNT": 10})
        rule = extract_rrule(e)
        assert rule is not None
        assert "FREQ=DAILY" in rule
        assert "COUNT=10" in rule

    def test_no_rrule_prefix(self):
        e = _make_event(RRULE={"FREQ": "WEEKLY"})
        rule = extract_rrule(e)
        assert not rule.startswith("RRULE:")

    def test_missing(self):
        e = Event()
        assert extract_rrule(e) is None


# ===========================================================================
# extract_recurrence_id
# ===========================================================================


class TestExtractRecurrenceId:
    def test_datetime_value(self):
        dt = datetime(2025, 3, 15, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        e = Event()
        e.add("RECURRENCE-ID", dt)
        recid = extract_recurrence_id(e)
        assert recid is not None
        assert "2025-03-15" in recid
        assert "T10:00:00" in recid

    def test_date_value(self):
        e = Event()
        e.add("RECURRENCE-ID", date(2025, 3, 15))
        recid = extract_recurrence_id(e)
        assert recid == "2025-03-15"

    def test_missing(self):
        e = Event()
        assert extract_recurrence_id(e) is None


# ===========================================================================
# extract_attendees
# ===========================================================================


class TestExtractAttendees:
    def test_single_attendee(self):
        """Single ATTENDEE returns vCalAddress (not list) — must normalize."""
        e = Event()
        addr = _make_attendee("alice@example.com", cn="Alice", partstat="ACCEPTED")
        e.add("ATTENDEE", addr)
        result = extract_attendees(e)
        assert len(result) == 1
        assert result[0]["email"] == "alice@example.com"
        assert result[0]["name"] == "Alice"
        assert result[0]["partstat"] == "accepted"

    def test_multiple_attendees(self):
        """Multiple ATTENDEEs return a list."""
        e = Event()
        e.add("ATTENDEE", _make_attendee("alice@example.com", cn="Alice"))
        e.add("ATTENDEE", _make_attendee("bob@example.com", cn="Bob", partstat="DECLINED"))
        result = extract_attendees(e)
        assert len(result) == 2
        emails = {a["email"] for a in result}
        assert "alice@example.com" in emails
        assert "bob@example.com" in emails

    def test_zero_attendees(self):
        e = Event()
        result = extract_attendees(e)
        assert result == []

    def test_mailto_stripping(self):
        e = Event()
        addr = _make_attendee("user@test.com")
        e.add("ATTENDEE", addr)
        result = extract_attendees(e)
        assert result[0]["email"] == "user@test.com"
        assert "mailto:" not in result[0]["email"]

    def test_attendee_with_cn_and_partstat(self):
        e = Event()
        addr = _make_attendee("jane@example.com", cn="Jane Doe", partstat="TENTATIVE")
        e.add("ATTENDEE", addr)
        result = extract_attendees(e)
        assert result[0]["name"] == "Jane Doe"
        assert result[0]["partstat"] == "tentative"

    def test_attendee_without_cn(self):
        e = Event()
        addr = vCalAddress("mailto:anon@example.com")
        e.add("ATTENDEE", addr)
        result = extract_attendees(e)
        assert result[0]["email"] == "anon@example.com"
        assert result[0]["name"] is None

    def test_attendee_partstat_needs_action(self):
        e = Event()
        addr = _make_attendee("user@example.com", partstat="NEEDS-ACTION")
        e.add("ATTENDEE", addr)
        result = extract_attendees(e)
        assert result[0]["partstat"] == "needs-action"

    def test_attendee_no_partstat(self):
        e = Event()
        addr = _make_attendee("user@example.com")
        e.add("ATTENDEE", addr)
        result = extract_attendees(e)
        assert result[0]["partstat"] is None


# ===========================================================================
# extract_self_response_status
# ===========================================================================


class TestExtractSelfResponseStatus:
    def test_self_found(self):
        e = Event()
        e.add("ATTENDEE", _make_attendee("me@example.com", partstat="ACCEPTED"))
        e.add("ATTENDEE", _make_attendee("other@example.com", partstat="DECLINED"))
        result = extract_self_response_status(e, "me@example.com")
        assert result == "accepted"

    def test_self_not_found(self):
        e = Event()
        e.add("ATTENDEE", _make_attendee("other@example.com", partstat="ACCEPTED"))
        result = extract_self_response_status(e, "me@example.com")
        assert result is None

    def test_no_user_email(self):
        e = Event()
        e.add("ATTENDEE", _make_attendee("someone@example.com", partstat="ACCEPTED"))
        result = extract_self_response_status(e, None)
        assert result is None

    def test_case_insensitive_match(self):
        e = Event()
        e.add("ATTENDEE", _make_attendee("Me@Example.COM", partstat="TENTATIVE"))
        result = extract_self_response_status(e, "me@example.com")
        assert result == "tentative"


# ===========================================================================
# extract_organizer
# ===========================================================================


class TestExtractOrganizer:
    def test_with_cn(self):
        e = Event()
        org = vCalAddress("mailto:boss@example.com")
        org.params["CN"] = "The Boss"
        e.add("ORGANIZER", org)
        result = extract_organizer(e)
        assert result is not None
        assert result["email"] == "boss@example.com"
        assert result["name"] == "The Boss"

    def test_without_cn(self):
        e = Event()
        org = vCalAddress("mailto:nemo@example.com")
        e.add("ORGANIZER", org)
        result = extract_organizer(e)
        assert result is not None
        assert result["email"] == "nemo@example.com"
        assert result["name"] is None

    def test_missing(self):
        e = Event()
        result = extract_organizer(e)
        assert result is None

    def test_mailto_stripping(self):
        e = Event()
        org = vCalAddress("mailto:user@test.com")
        e.add("ORGANIZER", org)
        result = extract_organizer(e)
        assert "mailto:" not in result["email"]


# ===========================================================================
# extract_reminder_minutes
# ===========================================================================


class TestExtractReminderMinutes:
    def test_15_min_before(self):
        e = Event()
        e.add("SUMMARY", "Test")
        alarm = Alarm()
        alarm.add("ACTION", "DISPLAY")
        alarm.add("TRIGGER", timedelta(minutes=-15))
        e.add_component(alarm)
        result = extract_reminder_minutes(e)
        assert result == 15

    def test_1_hour_before(self):
        e = Event()
        alarm = Alarm()
        alarm.add("ACTION", "DISPLAY")
        alarm.add("TRIGGER", timedelta(hours=-1))
        e.add_component(alarm)
        result = extract_reminder_minutes(e)
        assert result == 60

    def test_no_valarm(self):
        e = Event()
        result = extract_reminder_minutes(e)
        assert result is None

    def test_multiple_valarms_takes_first(self):
        e = Event()
        a1 = Alarm()
        a1.add("ACTION", "DISPLAY")
        a1.add("TRIGGER", timedelta(minutes=-10))
        a2 = Alarm()
        a2.add("ACTION", "EMAIL")
        a2.add("TRIGGER", timedelta(minutes=-30))
        e.add_component(a1)
        e.add_component(a2)
        result = extract_reminder_minutes(e)
        assert result == 10

    def test_positive_timedelta(self):
        """Some providers use positive timedelta (after event start)."""
        e = Event()
        alarm = Alarm()
        alarm.add("ACTION", "DISPLAY")
        alarm.add("TRIGGER", timedelta(minutes=5))
        e.add_component(alarm)
        result = extract_reminder_minutes(e)
        assert result == 5


# ===========================================================================
# extract_categories
# ===========================================================================


class TestExtractCategories:
    def test_single_category(self):
        e = _make_event(CATEGORIES=["Work"])
        result = extract_categories(e)
        assert result == ["Work"]

    def test_multiple_comma_separated(self):
        e = _make_event(CATEGORIES=["Work", "Important"])
        result = extract_categories(e)
        assert "Work" in result
        assert "Important" in result

    def test_multiple_categories_properties(self):
        """Multiple CATEGORIES properties → list of vCategory."""
        e = Event()
        e.add("CATEGORIES", ["Work"])
        e.add("CATEGORIES", ["Personal"])
        result = extract_categories(e)
        assert "Work" in result
        assert "Personal" in result

    def test_missing(self):
        e = Event()
        result = extract_categories(e)
        assert result == []

    def test_whitespace_stripping(self):
        e = _make_event(CATEGORIES=["  Spaces  "])
        result = extract_categories(e)
        assert len(result) >= 1
        assert all(cat == cat.strip() for cat in result)


# ===========================================================================
# strip_html_tags / extract_body
# ===========================================================================


class TestStripHtmlTags:
    def test_basic_html(self):
        assert strip_html_tags("<p>Hello</p>") == "Hello"

    def test_nested_html(self):
        assert strip_html_tags("<div><b>Bold</b> text</div>") == "Bold text"

    def test_no_html(self):
        assert strip_html_tags("Plain text") == "Plain text"

    def test_empty_string(self):
        assert strip_html_tags("") == ""

    def test_br_tags(self):
        result = strip_html_tags("Line 1<br>Line 2<br/>Line 3")
        assert "Line 1" in result
        assert "Line 2" in result
        assert "<br" not in result


class TestExtractBody:
    def test_plain_text(self):
        e = _make_event(DESCRIPTION="Meeting notes here")
        assert extract_body(e) == "Meeting notes here"

    def test_html_stripping(self):
        e = _make_event(DESCRIPTION="<p>Meeting <b>notes</b></p>")
        result = extract_body(e)
        assert result == "Meeting notes"

    def test_missing(self):
        e = Event()
        assert extract_body(e) is None


# ===========================================================================
# build_event_properties — integration tests
# ===========================================================================


class TestBuildEventProperties:
    def test_full_event(self):
        """Full event with all properties produces complete dict."""
        e = Event()
        e.add("SUMMARY", "Team Standup")
        e.add("DTSTART", datetime(2025, 3, 15, 10, 0, 0, tzinfo=ZoneInfo("America/New_York")))
        e.add("DTEND", datetime(2025, 3, 15, 10, 30, 0, tzinfo=ZoneInfo("America/New_York")))
        e.add("STATUS", "CONFIRMED")
        e.add("LOCATION", "Room 42")
        e.add("CLASS", "PUBLIC")
        e.add("TRANSP", "OPAQUE")
        e.add("UID", "uid-standup-123")
        e.add("CREATED", datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
        e.add("LAST-MODIFIED", datetime(2025, 3, 10, 8, 0, 0, tzinfo=timezone.utc))
        e.add("DESCRIPTION", "Daily sync meeting")
        e.add("CATEGORIES", ["Work", "Daily"])
        e.add("RRULE", {"FREQ": "WEEKLY", "BYDAY": ["MO", "WE", "FR"]})

        # Add attendee
        e.add("ATTENDEE", _make_attendee("me@example.com", cn="Me", partstat="ACCEPTED"))
        e.add("ATTENDEE", _make_attendee("colleague@example.com", cn="Colleague", partstat="TENTATIVE"))

        # Add organizer
        org = vCalAddress("mailto:boss@example.com")
        org.params["CN"] = "Boss"
        e.add("ORGANIZER", org)

        # Add alarm
        alarm = Alarm()
        alarm.add("ACTION", "DISPLAY")
        alarm.add("TRIGGER", timedelta(minutes=-10))
        e.add_component(alarm)

        props = build_event_properties(
            e,
            calendar_name="Work Calendar",
            sync_time="2025-03-15T12:00:00Z",
            user_email="me@example.com",
        )

        assert props["dcterms:title"] == "Team Standup"
        assert "T10:00:00" in props["schema:startDate"]
        assert "T10:30:00" in props["schema:endDate"]
        assert props[f"{BPKM}allDay"] == "false"
        assert props[f"{BPKM}eventStatus"] == "confirmed"
        assert props[f"{BPKM}location"] == "Room 42"
        assert props[f"{BPKM}visibility"] == "public"
        assert props[f"{BPKM}showAs"] == "busy"
        assert props[f"{BPKM}externalId"] == "uid-standup-123"
        assert props[f"{BPKM}externalProvider"] == "caldav"
        assert props[f"{BPKM}calendarName"] == "Work Calendar"
        assert props[f"{BPKM}lastSyncedAt"] == "2025-03-15T12:00:00Z"
        assert props[f"{BPKM}responseStatus"] == "accepted"
        assert props[f"{BPKM}reminderMinutes"] == 10
        assert "FREQ=WEEKLY" in props[f"{BPKM}recurrenceRule"]
        assert "Work" in props[f"{BPKM}tags"]
        assert "Daily" in props[f"{BPKM}tags"]
        assert props[f"{BPKM}body"] == "Daily sync meeting"
        assert len(props[f"{BPKM}attendees"]) == 2
        assert props[f"{BPKM}organizer"]["email"] == "boss@example.com"
        assert props["dcterms:created"] is not None
        assert props["dcterms:modified"] is not None

    def test_minimal_event(self):
        """Event with only title still produces valid dict."""
        e = _make_event(SUMMARY="Quick Note")
        props = build_event_properties(e, calendar_name="Personal", sync_time="2025-03-15T12:00:00Z")

        assert props["dcterms:title"] == "Quick Note"
        assert props[f"{BPKM}allDay"] == "false"
        assert props[f"{BPKM}externalProvider"] == "caldav"
        assert props[f"{BPKM}calendarName"] == "Personal"
        assert props[f"{BPKM}lastSyncedAt"] == "2025-03-15T12:00:00Z"
        # Optional fields should be absent (not None)
        assert f"{BPKM}eventStatus" not in props
        assert f"{BPKM}location" not in props
        assert f"{BPKM}visibility" not in props
        assert f"{BPKM}recurrenceRule" not in props

    def test_all_day_event(self):
        """All-day event produces correct date strings and allDay=true."""
        e = _make_event(
            SUMMARY="Holiday",
            DTSTART=date(2025, 12, 25),
            DTEND=date(2025, 12, 26),
        )
        props = build_event_properties(e, calendar_name="Holidays", sync_time="2025-03-15T12:00:00Z")

        assert props[f"{BPKM}allDay"] == "true"
        assert props["schema:startDate"] == "2025-12-25"
        assert props["schema:endDate"] == "2025-12-26"

    def test_no_title_fallback(self):
        """Event without SUMMARY gets '(No title)' fallback."""
        e = _make_event(DTSTART=datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc))
        props = build_event_properties(e, calendar_name="Cal", sync_time="2025-01-01T00:00:00Z")
        assert props["dcterms:title"] == "(No title)"

    def test_none_values_excluded(self):
        """None values are not present in the output dict."""
        e = _make_event(SUMMARY="Simple")
        props = build_event_properties(e, calendar_name="Cal", sync_time="2025-01-01T00:00:00Z")
        for key, val in props.items():
            assert val is not None, f"Key {key} should not have None value"

    def test_attendees_as_dicts(self):
        """Attendees appear as dicts, not IRIs (person matching is T02)."""
        e = Event()
        e.add("SUMMARY", "Meeting")
        e.add("ATTENDEE", _make_attendee("alice@example.com", cn="Alice", partstat="ACCEPTED"))
        props = build_event_properties(e, calendar_name="Cal", sync_time="2025-01-01T00:00:00Z")
        assert f"{BPKM}attendees" in props
        assert isinstance(props[f"{BPKM}attendees"], list)
        assert props[f"{BPKM}attendees"][0]["email"] == "alice@example.com"

    def test_organizer_as_dict(self):
        """Organizer appears as a dict, not an IRI."""
        e = Event()
        e.add("SUMMARY", "Meeting")
        org = vCalAddress("mailto:boss@example.com")
        org.params["CN"] = "Boss"
        e.add("ORGANIZER", org)
        props = build_event_properties(e, calendar_name="Cal", sync_time="2025-01-01T00:00:00Z")
        assert f"{BPKM}organizer" in props
        assert isinstance(props[f"{BPKM}organizer"], dict)
        assert props[f"{BPKM}organizer"]["email"] == "boss@example.com"

    def test_url_property(self):
        """URL property maps to externalUrl."""
        e = Event()
        e.add("SUMMARY", "Test")
        e.add("URL", "https://example.com/event/123")
        props = build_event_properties(e, calendar_name="Cal", sync_time="2025-01-01T00:00:00Z")
        assert props[f"{BPKM}externalUrl"] == "https://example.com/event/123"

    def test_empty_attendees_excluded(self):
        """Empty attendees list is not included in output."""
        e = _make_event(SUMMARY="Solo")
        props = build_event_properties(e, calendar_name="Cal", sync_time="2025-01-01T00:00:00Z")
        assert f"{BPKM}attendees" not in props

    def test_empty_categories_excluded(self):
        """Empty categories list is not included in output."""
        e = _make_event(SUMMARY="Plain")
        props = build_event_properties(e, calendar_name="Cal", sync_time="2025-01-01T00:00:00Z")
        assert f"{BPKM}tags" not in props


# ===========================================================================
# build_event_patch
# ===========================================================================


class TestBuildEventPatch:
    def test_returns_empty_for_no_response_status(self):
        """Empty props → no pushable changes."""
        result = build_event_patch({}, "user@test.com")
        assert result == {}

    def test_returns_empty_for_unmapped_status(self):
        """Unknown responseStatus value → not pushable."""
        result = build_event_patch({f"{BPKM}responseStatus": "unknown-value"}, "user@test.com")
        assert result == {}

    def test_returns_empty_for_no_user_email(self):
        """Valid status but no user_email → can't push RSVP."""
        result = build_event_patch({f"{BPKM}responseStatus": "accepted"}, None)
        assert result == {}

    def test_returns_empty_for_empty_user_email(self):
        """Empty string user_email → can't push RSVP."""
        result = build_event_patch({f"{BPKM}responseStatus": "accepted"}, "")
        assert result == {}

    def test_returns_accepted(self):
        result = build_event_patch({f"{BPKM}responseStatus": "accepted"}, "user@test.com")
        assert result == {"responseStatus": "ACCEPTED"}

    def test_returns_declined(self):
        result = build_event_patch({f"{BPKM}responseStatus": "declined"}, "user@test.com")
        assert result == {"responseStatus": "DECLINED"}

    def test_returns_tentative(self):
        result = build_event_patch({f"{BPKM}responseStatus": "tentative"}, "user@test.com")
        assert result == {"responseStatus": "TENTATIVE"}

    def test_returns_needs_action(self):
        result = build_event_patch({f"{BPKM}responseStatus": "needs-action"}, "user@test.com")
        assert result == {"responseStatus": "NEEDS-ACTION"}


# ===========================================================================
# modify_vevent_partstat
# ===========================================================================


def _build_test_ics(attendees: list[tuple[str, dict]] | None = None) -> str:
    """Build a minimal VCALENDAR string with VEVENT and optional ATTENDEEs.

    Each attendee is a tuple of (email, params_dict) where params_dict
    can contain CN, PARTSTAT, ROLE, RSVP, etc.
    """
    cal = Calendar()
    cal.add("prodid", "-//Test//Test//EN")
    cal.add("version", "2.0")

    event = Event()
    event.add("summary", "Test Meeting")
    event.add("dtstart", datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc))
    event.add("dtend", datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc))
    event.add("uid", "test-uid-001@example.com")

    if attendees:
        for email, params in attendees:
            att = vCalAddress(f"mailto:{email}")
            for k, v in params.items():
                att.params[k] = v
            event.add("attendee", att, encode=0)

    cal.add_component(event)
    return cal.to_ical().decode("utf-8")


class TestModifyVeventPartstat:
    def test_modifies_single_attendee(self):
        """Single ATTENDEE with NEEDS-ACTION → set to ACCEPTED."""
        ics = _build_test_ics([
            ("alice@example.com", {"PARTSTAT": "NEEDS-ACTION", "CN": "Alice"}),
        ])
        result = modify_vevent_partstat(ics, "alice@example.com", "ACCEPTED")

        # Re-parse and verify
        cal = Calendar.from_ical(result)
        for comp in cal.walk():
            if comp.name == "VEVENT":
                raw = comp.get("ATTENDEE")
                assert str(raw.params["PARTSTAT"]) == "ACCEPTED"

    def test_modifies_correct_attendee_in_multi(self):
        """Three ATTENDEEs — only the target gets modified."""
        ics = _build_test_ics([
            ("alice@example.com", {"PARTSTAT": "ACCEPTED", "CN": "Alice"}),
            ("bob@example.com", {"PARTSTAT": "NEEDS-ACTION", "CN": "Bob"}),
            ("carol@example.com", {"PARTSTAT": "DECLINED", "CN": "Carol"}),
        ])
        result = modify_vevent_partstat(ics, "bob@example.com", "TENTATIVE")

        cal = Calendar.from_ical(result)
        for comp in cal.walk():
            if comp.name == "VEVENT":
                attendees = comp.get("ATTENDEE")
                assert isinstance(attendees, list)
                status_map = {}
                for att in attendees:
                    email = str(att).replace("mailto:", "")
                    status_map[email.lower()] = str(att.params["PARTSTAT"])
                assert status_map["alice@example.com"] == "ACCEPTED"
                assert status_map["bob@example.com"] == "TENTATIVE"
                assert status_map["carol@example.com"] == "DECLINED"

    def test_returns_unchanged_when_email_not_found(self):
        """User email doesn't match any ATTENDEE → return original."""
        ics = _build_test_ics([
            ("alice@example.com", {"PARTSTAT": "ACCEPTED"}),
        ])
        result = modify_vevent_partstat(ics, "nobody@example.com", "DECLINED")
        assert result == ics  # Exact same string — no modification

    def test_case_insensitive_mailto(self):
        """Email matching is case-insensitive."""
        ics = _build_test_ics([
            ("User@Example.COM", {"PARTSTAT": "NEEDS-ACTION"}),
        ])
        result = modify_vevent_partstat(ics, "user@example.com", "ACCEPTED")

        cal = Calendar.from_ical(result)
        for comp in cal.walk():
            if comp.name == "VEVENT":
                raw = comp.get("ATTENDEE")
                assert str(raw.params["PARTSTAT"]) == "ACCEPTED"

    def test_round_trip_modify_then_extract(self):
        """Modify PARTSTAT, then use extract_attendees to verify consistency."""
        ics = _build_test_ics([
            ("alice@example.com", {"PARTSTAT": "NEEDS-ACTION", "CN": "Alice"}),
        ])
        modified_ics = modify_vevent_partstat(ics, "alice@example.com", "DECLINED")

        cal = Calendar.from_ical(modified_ics)
        for comp in cal.walk():
            if comp.name == "VEVENT":
                attendees = extract_attendees(comp)
                assert len(attendees) == 1
                assert attendees[0]["email"] == "alice@example.com"
                assert attendees[0]["partstat"] == "declined"  # mapped value

    def test_no_attendees_returns_unchanged(self):
        """VEVENT with no ATTENDEE property → returns unchanged."""
        ics = _build_test_ics()  # No attendees
        result = modify_vevent_partstat(ics, "alice@example.com", "ACCEPTED")
        assert result == ics

    def test_preserves_other_attendee_params(self):
        """Only PARTSTAT is changed; CN, ROLE, RSVP are preserved."""
        ics = _build_test_ics([
            ("alice@example.com", {
                "PARTSTAT": "NEEDS-ACTION",
                "CN": "Alice Smith",
                "ROLE": "REQ-PARTICIPANT",
                "RSVP": "TRUE",
            }),
        ])
        result = modify_vevent_partstat(ics, "alice@example.com", "ACCEPTED")

        cal = Calendar.from_ical(result)
        for comp in cal.walk():
            if comp.name == "VEVENT":
                raw = comp.get("ATTENDEE")
                assert str(raw.params["PARTSTAT"]) == "ACCEPTED"
                assert str(raw.params["CN"]) == "Alice Smith"
                assert str(raw.params["ROLE"]) == "REQ-PARTICIPANT"
                assert str(raw.params["RSVP"]) == "TRUE"


# ===========================================================================
# Enum map completeness
# ===========================================================================


class TestEnumMaps:
    def test_status_map_keys(self):
        assert set(STATUS_MAP.keys()) == {"TENTATIVE", "CONFIRMED", "CANCELLED"}

    def test_class_map_keys(self):
        assert set(CLASS_MAP.keys()) == {"PUBLIC", "PRIVATE", "CONFIDENTIAL"}

    def test_transp_map_keys(self):
        assert set(TRANSP_MAP.keys()) == {"OPAQUE", "TRANSPARENT"}

    def test_partstat_map_keys(self):
        assert set(PARTSTAT_MAP.keys()) == {"NEEDS-ACTION", "ACCEPTED", "DECLINED", "TENTATIVE"}

    def test_reverse_response_map_invertible(self):
        """Reverse map is the inverse of PARTSTAT_MAP."""
        for k, v in PARTSTAT_MAP.items():
            assert REVERSE_RESPONSE_STATUS_MAP[v] == k
