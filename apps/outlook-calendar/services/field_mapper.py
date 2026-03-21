"""Pure field mapping between Microsoft Graph API event dicts and bpkm:Event properties.

All functions are side-effect-free: no network, no logging, no state.
Property keys use full IRIs for bpkm properties because the ``bpkm:``
prefix is not in the platform's COMMON_PREFIXES.

The recurrence converter (``convert_recurrence_to_rrule``) translates
Outlook's structured recurrence objects (6 pattern types × 3 range types
= 18 combinations) into RFC 5545 RRULE strings.
"""

from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------
# Conditional import — markdownify is optional
# ---------------------------------------------------------------------------

try:
    from markdownify import markdownify as md
except ImportError:
    md = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Full IRI prefix for basic-pkm model properties
BPKM = "urn:sempkm:model:basic-pkm:"

# Outlook showAs → bpkm:showAs
SHOW_AS_MAP: dict[str, str] = {
    "free": "free",
    "tentative": "tentative",
    "busy": "busy",
    "oof": "out-of-office",
    "workingElsewhere": "working-elsewhere",
    "unknown": "busy",
}

# Outlook sensitivity → bpkm:visibility (None means omit property)
SENSITIVITY_MAP: dict[str, str | None] = {
    "normal": None,
    "personal": None,
    "private": "private",
    "confidential": "confidential",
}

# Outlook responseStatus.response → bpkm:responseStatus
RESPONSE_STATUS_MAP: dict[str, str] = {
    "none": "needs-action",
    "organizer": "accepted",
    "tentativelyAccepted": "tentative",
    "accepted": "accepted",
    "declined": "declined",
    "notResponded": "needs-action",
}

# Reverse: bpkm:responseStatus → Outlook responseStatus.response (for push-back)
# "organizer" has no reverse — you can't set yourself as organizer via RSVP.
# "none" and "notResponded" both map to "needs-action"; reverse picks "notResponded".
REVERSE_RESPONSE_STATUS_MAP: dict[str, str] = {
    "needs-action": "notResponded",
    "accepted": "accepted",
    "declined": "declined",
    "tentative": "tentativelyAccepted",
}

# Outlook recurrence daysOfWeek → RRULE BYDAY abbreviations
DAY_OF_WEEK_MAP: dict[str, str] = {
    "sunday": "SU",
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
}

# Outlook recurrence index → RRULE positional value
RELATIVE_INDEX_MAP: dict[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "last": -1,
}


# ---------------------------------------------------------------------------
# IRI slug
# ---------------------------------------------------------------------------


def compute_event_slug(calendar_id: str, event_id: str) -> str:
    """Compute a deterministic 16-char hex slug for an Outlook Calendar event.

    Used as the local part of a platform-minted Event IRI:
    ``{base_namespace}/Event/evt-{hash16}``.
    """
    return hashlib.sha256(f"{calendar_id}:{event_id}".encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Extraction helpers (all pure, all return None on missing data)
# ---------------------------------------------------------------------------


def detect_all_day(event: dict) -> tuple[bool, str | None, str | None]:
    """Detect whether an event is all-day and extract start/end values.

    Outlook uses an explicit ``isAllDay`` boolean.  Start/end are always
    in ``event["start"]["dateTime"]`` and ``event["end"]["dateTime"]``
    regardless of all-day status (Outlook uses midnight-to-midnight for
    all-day events rather than a separate date-only field).

    Returns:
        ``(is_all_day, start_value, end_value)``
    """
    is_all_day = event.get("isAllDay", False)
    start = event.get("start", {})
    end = event.get("end", {})
    return (bool(is_all_day), start.get("dateTime"), end.get("dateTime"))


def extract_conference_url(event: dict) -> str | None:
    """Extract the video conference URL from an event.

    Checks ``onlineMeeting.joinUrl`` first, then ``onlineMeetingUrl``
    as a fallback.  Returns None if neither exists.
    """
    online_meeting = event.get("onlineMeeting")
    if online_meeting:
        join_url = online_meeting.get("joinUrl")
        if join_url:
            return join_url

    return event.get("onlineMeetingUrl")


def extract_response_status(event: dict) -> str | None:
    """Extract the user's response status.

    Outlook provides this directly at ``responseStatus.response``
    (unlike Google where you search the attendees list for self=True).
    """
    response_status = event.get("responseStatus")
    if not response_status:
        return None
    response = response_status.get("response", "")
    return RESPONSE_STATUS_MAP.get(response)


def derive_event_status(event: dict) -> str:
    """Derive bpkm:eventStatus from multiple Outlook fields.

    Outlook has no single ``status`` field like Google.  The status is
    derived:
    - ``isCancelled=True`` → ``"cancelled"``
    - ``responseStatus.response == "tentativelyAccepted"`` → ``"tentative"``
    - All other cases → ``"confirmed"``
    """
    if event.get("isCancelled") is True:
        return "cancelled"
    response_status = event.get("responseStatus", {})
    if response_status.get("response") == "tentativelyAccepted":
        return "tentative"
    return "confirmed"


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text, returning stripped plain text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def extract_body(event: dict) -> str | None:
    """Extract body content, converting HTML to Markdown if possible.

    Checks ``body.contentType``:
    - ``"html"``: convert via markdownify (if available) or strip HTML tags
    - ``"text"``: pass through as-is

    Returns None if the body is empty or absent.
    """
    body = event.get("body")
    if not body:
        return None

    content = body.get("content", "")
    if not content or not content.strip():
        return None

    content_type = body.get("contentType", "text")

    if content_type == "html":
        if md is not None:
            result = md(content).strip()
            return result if result else None
        return strip_html_tags(content) or None

    # text or any other type — pass through
    cleaned = content.strip()
    return cleaned if cleaned else None


def extract_categories_as_tags(event: dict) -> str | None:
    """Extract Outlook categories as a comma-separated tags string.

    Returns None if categories is empty or missing.
    """
    categories = event.get("categories")
    if not categories:
        return None
    return ",".join(categories)


def extract_rrule(event: dict) -> str | None:
    """Extract recurrence rule from event, converting to RRULE string."""
    return convert_recurrence_to_rrule(event.get("recurrence"))


# ---------------------------------------------------------------------------
# Recurrence converter
# ---------------------------------------------------------------------------


def convert_recurrence_to_rrule(recurrence: dict | None) -> str | None:
    """Convert an Outlook recurrence object to an RFC 5545 RRULE string.

    Input: Outlook recurrence dict ``{"pattern": {...}, "range": {...}}``
    or None.

    Output: RRULE string (without the ``RRULE:`` prefix) or None.

    Handles all 6 pattern types × 3 range types = 18 combinations:
    - Pattern types: daily, weekly, absoluteMonthly, relativeMonthly,
      absoluteYearly, relativeYearly
    - Range types: endDate, numbered, noEnd
    """
    if not recurrence:
        return None

    pattern = recurrence.get("pattern")
    rec_range = recurrence.get("range")
    if not pattern:
        return None

    pattern_type = pattern.get("type", "")
    interval = pattern.get("interval", 1)

    parts: list[str] = []

    # --- FREQ and pattern-specific components ---
    if pattern_type == "daily":
        parts.append("FREQ=DAILY")

    elif pattern_type == "weekly":
        parts.append("FREQ=WEEKLY")
        days = _convert_days_of_week(pattern.get("daysOfWeek", []))
        if days:
            parts.append(f"BYDAY={days}")

    elif pattern_type == "absoluteMonthly":
        parts.append("FREQ=MONTHLY")
        day_of_month = pattern.get("dayOfMonth")
        if day_of_month is not None:
            parts.append(f"BYMONTHDAY={day_of_month}")

    elif pattern_type == "relativeMonthly":
        parts.append("FREQ=MONTHLY")
        byday = _convert_relative_day(pattern)
        if byday:
            parts.append(f"BYDAY={byday}")

    elif pattern_type == "absoluteYearly":
        parts.append("FREQ=YEARLY")
        month = pattern.get("month")
        if month is not None:
            parts.append(f"BYMONTH={month}")
        day_of_month = pattern.get("dayOfMonth")
        if day_of_month is not None:
            parts.append(f"BYMONTHDAY={day_of_month}")

    elif pattern_type == "relativeYearly":
        parts.append("FREQ=YEARLY")
        month = pattern.get("month")
        if month is not None:
            parts.append(f"BYMONTH={month}")
        byday = _convert_relative_day(pattern)
        if byday:
            parts.append(f"BYDAY={byday}")

    else:
        # Unknown pattern type — return None
        return None

    # --- INTERVAL ---
    if interval and interval > 1:
        parts.append(f"INTERVAL={interval}")

    # --- Range ---
    if rec_range:
        range_type = rec_range.get("type", "")

        if range_type == "endDate":
            end_date = rec_range.get("endDate", "")
            if end_date:
                # Format: YYYYMMDD → YYYYMMDDToooooZ
                date_str = end_date.replace("-", "")
                parts.append(f"UNTIL={date_str}T000000Z")

        elif range_type == "numbered":
            count = rec_range.get("numberOfOccurrences")
            if count is not None:
                parts.append(f"COUNT={count}")

        # noEnd — omit UNTIL and COUNT

    return ";".join(parts)


def _convert_days_of_week(days: list[str]) -> str:
    """Convert Outlook daysOfWeek list to RRULE BYDAY value.

    Example: ``["monday", "wednesday", "friday"]`` → ``"MO,WE,FR"``
    """
    mapped = [DAY_OF_WEEK_MAP[d] for d in days if d in DAY_OF_WEEK_MAP]
    return ",".join(mapped)


def _convert_relative_day(pattern: dict) -> str | None:
    """Convert a relative pattern (relativeMonthly/relativeYearly) BYDAY value.

    Uses ``index`` for position and first entry in ``daysOfWeek`` for the day.
    Example: index="second", daysOfWeek=["tuesday"] → ``"2TU"``
    Example: index="last", daysOfWeek=["friday"] → ``"-1FR"``
    """
    index_str = pattern.get("index", "")
    position = RELATIVE_INDEX_MAP.get(index_str)
    if position is None:
        return None

    days = pattern.get("daysOfWeek", [])
    if not days:
        return None

    day_abbr = DAY_OF_WEEK_MAP.get(days[0])
    if not day_abbr:
        return None

    return f"{position}{day_abbr}"


# ---------------------------------------------------------------------------
# Property builder
# ---------------------------------------------------------------------------


def build_event_properties(
    event: dict,
    calendar_name: str,
    sync_time: str,
) -> dict:
    """Build a properties dict for ``object.create`` / ``object.patch``.

    Parameters
    ----------
    event:
        A Microsoft Graph event dict.
    calendar_name:
        Human-readable name of the source calendar.
    sync_time:
        ISO-8601 UTC timestamp for ``bpkm:lastSyncedAt``.

    Returns
    -------
    dict
        Property mapping where keys are full IRIs (except ``dcterms:``
        and ``schema:`` prefixed ones which use compact form).
        Keys with ``None`` values are excluded.
    """
    is_all_day, start_val, end_val = detect_all_day(event)

    # Reminder minutes: only if reminders are enabled
    reminder_minutes: str | None = None
    if event.get("isReminderOn"):
        mins = event.get("reminderMinutesBeforeStart")
        if mins is not None:
            reminder_minutes = str(mins)

    # Sensitivity → visibility (None values mean "omit")
    visibility = SENSITIVITY_MAP.get(event.get("sensitivity", ""))

    props: dict[str, str | None] = {
        "dcterms:title": event.get("subject") or "(No title)",
        "schema:startDate": start_val,
        "schema:endDate": end_val,
        f"{BPKM}allDay": "true" if is_all_day else "false",
        f"{BPKM}timeZone": event.get("start", {}).get("timeZone"),
        f"{BPKM}eventStatus": derive_event_status(event),
        f"{BPKM}location": (event.get("location") or {}).get("displayName"),
        f"{BPKM}showAs": SHOW_AS_MAP.get(event.get("showAs", "")),
        f"{BPKM}visibility": visibility,
        f"{BPKM}conferenceUrl": extract_conference_url(event),
        f"{BPKM}recurrenceRule": extract_rrule(event),
        f"{BPKM}recurringEventId": event.get("seriesMasterId"),
        f"{BPKM}responseStatus": extract_response_status(event),
        f"{BPKM}reminderMinutes": reminder_minutes,
        f"{BPKM}calendarName": calendar_name,
        f"{BPKM}tags": extract_categories_as_tags(event),
        f"{BPKM}externalId": event.get("id"),
        f"{BPKM}externalUrl": event.get("webLink"),
        f"{BPKM}externalProvider": "outlook-calendar",
        f"{BPKM}lastSyncedAt": sync_time,
        "dcterms:description": extract_body(event),
        "dcterms:created": event.get("createdDateTime"),
        "dcterms:modified": event.get("lastModifiedDateTime"),
    }

    # Strip None values
    return {k: v for k, v in props.items() if v is not None}


# ---------------------------------------------------------------------------
# Reverse mapping (push-back)
# ---------------------------------------------------------------------------


def build_event_patch(event_props: dict, microsoft_email: str) -> dict:
    """Build a Microsoft Graph Events PATCH body from bpkm event properties.

    Currently supports RSVP push-back only (per D222).  Constructs a
    partial attendees array so that PATCH updates only the user's
    response status.

    Parameters
    ----------
    event_props:
        Property dict with full IRI keys (e.g.
        ``urn:sempkm:model:basic-pkm:responseStatus``).
    microsoft_email:
        The authenticated user's Microsoft email (from state).

    Returns
    -------
    dict
        Microsoft Graph Events PATCH body with response status update,
        or empty dict if no pushable changes.
    """
    bpkm_status = event_props.get(f"{BPKM}responseStatus")
    if not bpkm_status:
        return {}

    outlook_status = REVERSE_RESPONSE_STATUS_MAP.get(bpkm_status)
    if not outlook_status:
        return {}

    return {
        "attendees": [
            {
                "emailAddress": {"address": microsoft_email},
                "status": {"response": outlook_status},
            }
        ],
    }
