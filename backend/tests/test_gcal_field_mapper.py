"""Unit tests for Google Calendar field mapper.

Loads ``field_mapper.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package.  All functions are pure —
no mocks needed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load field_mapper module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "google-calendar"
    / "services"
    / "field_mapper.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("gcal_field_mapper", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gcal_field_mapper"] = mod
    spec.loader.exec_module(mod)
    return mod


fm = _load_module()

BPKM = fm.BPKM

SYNC_TIME = "2026-03-18T12:00:00+00:00"


# ---------------------------------------------------------------------------
# Fixture factory — builds a Google Calendar event dict with defaults
# ---------------------------------------------------------------------------

def _make_event(**overrides) -> dict:
    """Build a minimal Google Calendar event dict with sensible defaults."""
    base = {
        "id": "abc123event",
        "summary": "Team Standup",
        "status": "confirmed",
        "htmlLink": "https://www.google.com/calendar/event?eid=abc123",
        "created": "2026-01-10T08:00:00.000Z",
        "updated": "2026-03-15T14:30:00.000Z",
        "start": {
            "dateTime": "2026-03-20T09:00:00-04:00",
            "timeZone": "America/New_York",
        },
        "end": {
            "dateTime": "2026-03-20T09:30:00-04:00",
            "timeZone": "America/New_York",
        },
        "reminders": {"useDefault": True},
    }
    base.update(overrides)
    return base


# ===================================================================
# compute_event_slug tests
# ===================================================================

class TestComputeEventSlug:
    def test_deterministic(self):
        slug1 = fm.compute_event_slug("cal@group.calendar.google.com", "evt123")
        slug2 = fm.compute_event_slug("cal@group.calendar.google.com", "evt123")
        assert slug1 == slug2

    def test_different_calendar_ids_different_slugs(self):
        slug_a = fm.compute_event_slug("calA@google.com", "evt1")
        slug_b = fm.compute_event_slug("calB@google.com", "evt1")
        assert slug_a != slug_b

    def test_different_event_ids_different_slugs(self):
        slug_1 = fm.compute_event_slug("cal@google.com", "evt1")
        slug_2 = fm.compute_event_slug("cal@google.com", "evt2")
        assert slug_1 != slug_2

    def test_format_16_hex_chars(self):
        slug = fm.compute_event_slug("cal@google.com", "evt99")
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
        assert start == "2026-03-20T09:00:00-04:00"
        assert end == "2026-03-20T09:30:00-04:00"

    def test_all_day_event(self):
        event = _make_event(
            start={"date": "2026-03-20"},
            end={"date": "2026-03-21"},
        )
        is_all_day, start, end = fm.detect_all_day(event)
        assert is_all_day is True
        assert start == "2026-03-20"
        assert end == "2026-03-21"

    def test_missing_start_returns_none_values(self):
        event = _make_event(start={}, end={})
        is_all_day, start, end = fm.detect_all_day(event)
        assert is_all_day is False
        assert start is None
        assert end is None


# ===================================================================
# extract_conference_url tests
# ===================================================================

class TestExtractConferenceUrl:
    def test_video_entry_point(self):
        event = _make_event(conferenceData={
            "entryPoints": [
                {"entryPointType": "phone", "uri": "tel:+1234567890"},
                {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"},
            ]
        })
        assert fm.extract_conference_url(event) == "https://meet.google.com/abc-defg-hij"

    def test_hangout_link_fallback(self):
        event = _make_event(hangoutLink="https://hangouts.google.com/call/xyz")
        assert fm.extract_conference_url(event) == "https://hangouts.google.com/call/xyz"

    def test_no_conference_data(self):
        event = _make_event()
        assert fm.extract_conference_url(event) is None

    def test_conference_data_phone_only(self):
        event = _make_event(conferenceData={
            "entryPoints": [
                {"entryPointType": "phone", "uri": "tel:+1234567890"},
            ]
        })
        assert fm.extract_conference_url(event) is None

    def test_video_preferred_over_hangout_link(self):
        """When both conferenceData.video and hangoutLink exist, video wins."""
        event = _make_event(
            conferenceData={
                "entryPoints": [
                    {"entryPointType": "video", "uri": "https://meet.google.com/new"},
                ]
            },
            hangoutLink="https://hangouts.google.com/old",
        )
        assert fm.extract_conference_url(event) == "https://meet.google.com/new"


# ===================================================================
# extract_response_status tests
# ===================================================================

class TestExtractResponseStatus:
    def test_self_attendee_found(self):
        event = _make_event(attendees=[
            {"email": "other@example.com", "responseStatus": "accepted"},
            {"email": "me@example.com", "self": True, "responseStatus": "tentative"},
        ])
        assert fm.extract_response_status(event) == "tentative"

    def test_no_self_attendee(self):
        event = _make_event(attendees=[
            {"email": "other@example.com", "responseStatus": "accepted"},
        ])
        assert fm.extract_response_status(event) is None

    def test_no_attendees_array(self):
        event = _make_event()
        assert fm.extract_response_status(event) is None

    def test_self_in_first_position(self):
        event = _make_event(attendees=[
            {"email": "me@example.com", "self": True, "responseStatus": "needsAction"},
            {"email": "other@example.com", "responseStatus": "declined"},
        ])
        assert fm.extract_response_status(event) == "needs-action"

    def test_needs_action_kebab_case(self):
        """Verify camelCase → kebab-case normalization."""
        event = _make_event(attendees=[
            {"email": "me@example.com", "self": True, "responseStatus": "needsAction"},
        ])
        assert fm.extract_response_status(event) == "needs-action"


# ===================================================================
# extract_rrule tests
# ===================================================================

class TestExtractRrule:
    def test_single_rrule(self):
        event = _make_event(recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"])
        assert fm.extract_rrule(event) == "FREQ=WEEKLY;BYDAY=MO,WE,FR"

    def test_rrule_with_exdate(self):
        event = _make_event(recurrence=[
            "RRULE:FREQ=DAILY",
            "EXDATE:20260320T090000Z",
        ])
        assert fm.extract_rrule(event) == "FREQ=DAILY"

    def test_no_recurrence(self):
        event = _make_event()
        assert fm.extract_rrule(event) is None

    def test_recurrence_with_only_exdate(self):
        event = _make_event(recurrence=["EXDATE:20260320T090000Z"])
        assert fm.extract_rrule(event) is None


# ===================================================================
# strip_html_tags tests
# ===================================================================

class TestStripHtmlTags:
    def test_simple_html(self):
        assert fm.strip_html_tags("<p>Hello world</p>") == "Hello world"

    def test_nested_tags(self):
        assert fm.strip_html_tags("<div><b>Bold</b> text</div>") == "Bold text"

    def test_no_html(self):
        assert fm.strip_html_tags("plain text") == "plain text"

    def test_empty_string(self):
        assert fm.strip_html_tags("") == ""

    def test_whitespace_only_after_stripping(self):
        assert fm.strip_html_tags("<br>  <br>") == ""


# ===================================================================
# extract_body tests
# ===================================================================

class TestExtractBody:
    def test_html_description(self):
        event = _make_event(description="<p>Meeting notes</p>")
        assert fm.extract_body(event) == "Meeting notes"

    def test_plain_text(self):
        event = _make_event(description="Just some text")
        assert fm.extract_body(event) == "Just some text"

    def test_empty_description(self):
        event = _make_event(description="")
        assert fm.extract_body(event) is None

    def test_no_description(self):
        event = _make_event()
        assert fm.extract_body(event) is None


# ===================================================================
# build_event_properties tests — the big one
# ===================================================================

class TestBuildEventProperties:
    def test_full_timed_event(self):
        """Timed event with all core fields present."""
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)

        assert props["dcterms:title"] == "Team Standup"
        assert props["schema:startDate"] == "2026-03-20T09:00:00-04:00"
        assert props["schema:endDate"] == "2026-03-20T09:30:00-04:00"
        assert props[f"{BPKM}allDay"] == "false"
        assert props[f"{BPKM}timeZone"] == "America/New_York"
        assert props[f"{BPKM}eventStatus"] == "confirmed"
        assert props[f"{BPKM}externalId"] == "abc123event"
        assert props[f"{BPKM}externalUrl"] == "https://www.google.com/calendar/event?eid=abc123"
        assert props[f"{BPKM}externalProvider"] == "google-calendar"
        assert props[f"{BPKM}lastSyncedAt"] == SYNC_TIME
        assert props[f"{BPKM}calendarName"] == "Work"
        assert props["dcterms:created"] == "2026-01-10T08:00:00.000Z"
        assert props["dcterms:modified"] == "2026-03-15T14:30:00.000Z"

    def test_all_day_event(self):
        event = _make_event(
            start={"date": "2026-04-01"},
            end={"date": "2026-04-02"},
        )
        props = fm.build_event_properties(event, "Personal", SYNC_TIME)
        assert props[f"{BPKM}allDay"] == "true"
        assert props["schema:startDate"] == "2026-04-01"
        assert props["schema:endDate"] == "2026-04-02"
        # No timeZone for all-day
        assert f"{BPKM}timeZone" not in props

    def test_minimal_event_summary_only(self):
        """Event with only required fields — most optional fields absent."""
        event = {
            "id": "min1",
            "summary": "Quick sync",
            "start": {"dateTime": "2026-03-20T10:00:00Z"},
            "end": {"dateTime": "2026-03-20T10:15:00Z"},
        }
        props = fm.build_event_properties(event, "Cal", SYNC_TIME)
        assert props["dcterms:title"] == "Quick sync"
        assert props[f"{BPKM}allDay"] == "false"
        assert props[f"{BPKM}eventStatus"] == "confirmed"  # default
        assert props[f"{BPKM}externalProvider"] == "google-calendar"
        # Optional fields should be absent
        assert f"{BPKM}location" not in props
        assert f"{BPKM}visibility" not in props
        assert f"{BPKM}showAs" not in props
        assert f"{BPKM}conferenceUrl" not in props
        assert f"{BPKM}recurrenceRule" not in props
        assert f"{BPKM}recurringEventId" not in props
        assert f"{BPKM}responseStatus" not in props
        assert f"{BPKM}reminderMinutes" not in props

    def test_event_with_conference_data(self):
        event = _make_event(conferenceData={
            "entryPoints": [
                {"entryPointType": "video", "uri": "https://meet.google.com/xyz"},
            ]
        })
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}conferenceUrl"] == "https://meet.google.com/xyz"

    def test_event_with_hangout_link(self):
        event = _make_event(hangoutLink="https://hangouts.google.com/call/abc")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}conferenceUrl"] == "https://hangouts.google.com/call/abc"

    def test_event_with_rrule(self):
        event = _make_event(recurrence=["RRULE:FREQ=MONTHLY;BYMONTHDAY=15"])
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}recurrenceRule"] == "FREQ=MONTHLY;BYMONTHDAY=15"

    def test_recurring_exception_has_recurring_event_id(self):
        event = _make_event(recurringEventId="master_event_123")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}recurringEventId"] == "master_event_123"

    def test_visibility_default_omitted(self):
        """When visibility is 'default', bpkm:visibility must NOT be in the output."""
        event = _make_event(visibility="default")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}visibility" not in props

    def test_visibility_private(self):
        event = _make_event(visibility="private")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}visibility"] == "private"

    def test_visibility_absent_omitted(self):
        """When visibility is not present at all, bpkm:visibility is omitted."""
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}visibility" not in props

    def test_transparency_opaque_to_busy(self):
        event = _make_event(transparency="opaque")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}showAs"] == "busy"

    def test_transparency_transparent_to_free(self):
        event = _make_event(transparency="transparent")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}showAs"] == "free"

    def test_transparency_absent_omitted(self):
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}showAs" not in props

    def test_reminders_with_overrides(self):
        event = _make_event(reminders={
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 15}],
        })
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}reminderMinutes"] == "15"

    def test_reminders_use_default_no_overrides(self):
        """When useDefault=True and no overrides, reminderMinutes is omitted."""
        event = _make_event(reminders={"useDefault": True})
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}reminderMinutes" not in props

    def test_reminders_no_reminders_field(self):
        event = _make_event()
        # Default _make_event has reminders, remove it
        del event["reminders"]
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}reminderMinutes" not in props

    def test_self_attendee_response_status(self):
        event = _make_event(attendees=[
            {"email": "other@example.com", "responseStatus": "accepted"},
            {"email": "me@example.com", "self": True, "responseStatus": "accepted"},
        ])
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}responseStatus"] == "accepted"

    def test_missing_summary_defaults_to_no_title(self):
        event = _make_event()
        del event["summary"]
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props["dcterms:title"] == "(No title)"

    def test_empty_summary_defaults_to_no_title(self):
        event = _make_event(summary="")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props["dcterms:title"] == "(No title)"

    def test_external_provider_always_google_calendar(self):
        """externalProvider must be exactly 'google-calendar', not 'google' or 'gcal'."""
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}externalProvider"] == "google-calendar"

    def test_location_present(self):
        event = _make_event(location="123 Main St, Springfield")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}location"] == "123 Main St, Springfield"

    def test_location_absent_omitted(self):
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert f"{BPKM}location" not in props

    def test_status_tentative(self):
        event = _make_event(status="tentative")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}eventStatus"] == "tentative"

    def test_status_cancelled(self):
        event = _make_event(status="cancelled")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}eventStatus"] == "cancelled"

    def test_status_unknown_defaults_to_confirmed(self):
        event = _make_event(status="weird_status")
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}eventStatus"] == "confirmed"

    def test_none_values_excluded(self):
        """No key in the output dict should have a None value."""
        event = _make_event()
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        for k, v in props.items():
            assert v is not None, f"Key {k!r} has None value"

    def test_created_and_modified_timestamps(self):
        event = _make_event(
            created="2026-01-01T00:00:00.000Z",
            updated="2026-03-18T10:00:00.000Z",
        )
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props["dcterms:created"] == "2026-01-01T00:00:00.000Z"
        assert props["dcterms:modified"] == "2026-03-18T10:00:00.000Z"

    def test_all_day_produces_true_string(self):
        """bpkm:allDay must be the string 'true', not boolean True."""
        event = _make_event(
            start={"date": "2026-05-01"},
            end={"date": "2026-05-02"},
        )
        props = fm.build_event_properties(event, "Cal", SYNC_TIME)
        assert props[f"{BPKM}allDay"] == "true"
        assert isinstance(props[f"{BPKM}allDay"], str)

    def test_timed_produces_false_string(self):
        """bpkm:allDay must be the string 'false', not boolean False."""
        event = _make_event()
        props = fm.build_event_properties(event, "Cal", SYNC_TIME)
        assert props[f"{BPKM}allDay"] == "false"
        assert isinstance(props[f"{BPKM}allDay"], str)

    def test_multiple_reminder_overrides_takes_first(self):
        event = _make_event(reminders={
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 10},
                {"method": "email", "minutes": 30},
            ],
        })
        props = fm.build_event_properties(event, "Work", SYNC_TIME)
        assert props[f"{BPKM}reminderMinutes"] == "10"


# ===================================================================
# Normalization map constant tests
# ===================================================================

class TestNormalizationMaps:
    def test_status_map_entries(self):
        assert fm.STATUS_MAP == {
            "confirmed": "confirmed",
            "tentative": "tentative",
            "cancelled": "cancelled",
        }

    def test_response_status_map_entries(self):
        assert fm.RESPONSE_STATUS_MAP == {
            "needsAction": "needs-action",
            "accepted": "accepted",
            "declined": "declined",
            "tentative": "tentative",
        }

    def test_visibility_map_excludes_default(self):
        assert "default" not in fm.VISIBILITY_MAP
        assert fm.VISIBILITY_MAP == {
            "public": "public",
            "private": "private",
            "confidential": "confidential",
        }

    def test_transparency_map_entries(self):
        assert fm.TRANSPARENCY_MAP == {
            "opaque": "busy",
            "transparent": "free",
        }

    def test_reverse_response_status_map_entries(self):
        assert fm.REVERSE_RESPONSE_STATUS_MAP == {
            "needs-action": "needsAction",
            "accepted": "accepted",
            "declined": "declined",
            "tentative": "tentative",
        }

    def test_reverse_response_status_is_true_inverse(self):
        """Every entry in RESPONSE_STATUS_MAP should have a matching reverse."""
        for gcal_val, bpkm_val in fm.RESPONSE_STATUS_MAP.items():
            assert fm.REVERSE_RESPONSE_STATUS_MAP[bpkm_val] == gcal_val


# ===================================================================
# build_event_patch tests
# ===================================================================

class TestBuildEventPatch:
    """Test reverse mapping for RSVP push-back."""

    def test_accepted_mapping(self):
        props = {f"{fm.BPKM}responseStatus": "accepted"}
        result = fm.build_event_patch(props, "user@example.com")
        assert result == {
            "attendees": [
                {"email": "user@example.com", "self": True, "responseStatus": "accepted"}
            ],
            "attendeesOmitted": True,
        }

    def test_declined_mapping(self):
        props = {f"{fm.BPKM}responseStatus": "declined"}
        result = fm.build_event_patch(props, "user@example.com")
        assert result["attendees"][0]["responseStatus"] == "declined"

    def test_tentative_mapping(self):
        props = {f"{fm.BPKM}responseStatus": "tentative"}
        result = fm.build_event_patch(props, "user@example.com")
        assert result["attendees"][0]["responseStatus"] == "tentative"

    def test_needs_action_mapping(self):
        props = {f"{fm.BPKM}responseStatus": "needs-action"}
        result = fm.build_event_patch(props, "user@example.com")
        assert result["attendees"][0]["responseStatus"] == "needsAction"

    def test_no_response_status_returns_empty(self):
        props = {f"{fm.BPKM}eventStatus": "confirmed"}
        result = fm.build_event_patch(props, "user@example.com")
        assert result == {}

    def test_unknown_status_returns_empty(self):
        props = {f"{fm.BPKM}responseStatus": "maybe-later"}
        result = fm.build_event_patch(props, "user@example.com")
        assert result == {}

    def test_self_flag_set(self):
        props = {f"{fm.BPKM}responseStatus": "accepted"}
        result = fm.build_event_patch(props, "test@gmail.com")
        assert result["attendees"][0]["self"] is True

    def test_email_matches_input(self):
        props = {f"{fm.BPKM}responseStatus": "accepted"}
        result = fm.build_event_patch(props, "specific@company.com")
        assert result["attendees"][0]["email"] == "specific@company.com"

    def test_attendees_omitted_flag(self):
        props = {f"{fm.BPKM}responseStatus": "declined"}
        result = fm.build_event_patch(props, "user@example.com")
        assert result["attendeesOmitted"] is True
