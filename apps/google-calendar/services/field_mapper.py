"""Pure field mapping between Google Calendar API event dicts and bpkm:Event properties.

All functions are side-effect-free: no network, no logging, no state.
Property keys use full IRIs for bpkm properties because the ``bpkm:``
prefix is not in the platform's COMMON_PREFIXES.
"""

from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Full IRI prefix for basic-pkm model properties
BPKM = "urn:sempkm:model:basic-pkm:"

# Google status → bpkm:eventStatus (1:1 mapping, no normalization needed)
STATUS_MAP: dict[str, str] = {
    "confirmed": "confirmed",
    "tentative": "tentative",
    "cancelled": "cancelled",
}

# Google responseStatus (camelCase) → bpkm:responseStatus (kebab-case)
RESPONSE_STATUS_MAP: dict[str, str] = {
    "needsAction": "needs-action",
    "accepted": "accepted",
    "declined": "declined",
    "tentative": "tentative",
}

# Reverse: bpkm:responseStatus → Google responseStatus (for push-back)
REVERSE_RESPONSE_STATUS_MAP: dict[str, str] = {
    "needs-action": "needsAction",
    "accepted": "accepted",
    "declined": "declined",
    "tentative": "tentative",
}

# Google visibility → bpkm:visibility
# "default" is explicitly excluded — omit the property entirely.
VISIBILITY_MAP: dict[str, str] = {
    "public": "public",
    "private": "private",
    "confidential": "confidential",
}

# Google transparency → bpkm:showAs
TRANSPARENCY_MAP: dict[str, str] = {
    "opaque": "busy",
    "transparent": "free",
}


# ---------------------------------------------------------------------------
# IRI slug
# ---------------------------------------------------------------------------


def compute_event_slug(calendar_id: str, event_id: str) -> str:
    """Compute a deterministic 16-char hex slug for a Google Calendar event.

    Used as the local part of a platform-minted Event IRI:
    ``{base_namespace}/Event/evt-{hash16}``.
    """
    return hashlib.sha256(f"{calendar_id}:{event_id}".encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Extraction helpers (all pure, all return None on missing data)
# ---------------------------------------------------------------------------


def detect_all_day(event: dict) -> tuple[bool, str | None, str | None]:
    """Detect whether an event is all-day and extract start/end values.

    Returns:
        ``(is_all_day, start_value, end_value)`` where values are
        date strings (all-day) or dateTime strings (timed).
    """
    start = event.get("start", {})
    end = event.get("end", {})

    if start.get("date"):
        return (True, start["date"], end.get("date"))
    return (False, start.get("dateTime"), end.get("dateTime"))


def extract_conference_url(event: dict) -> str | None:
    """Extract the video conference URL from an event.

    Checks ``conferenceData.entryPoints`` for the first video entry point.
    Falls back to ``hangoutLink``. Returns None if neither exists.
    """
    conf_data = event.get("conferenceData")
    if conf_data:
        for ep in conf_data.get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                return ep.get("uri")

    return event.get("hangoutLink")


def extract_response_status(event: dict) -> str | None:
    """Extract the authenticated user's response status from attendees.

    Finds the attendee dict where ``self == True`` and maps the
    ``responseStatus`` through ``RESPONSE_STATUS_MAP``.
    """
    for attendee in event.get("attendees", []):
        if attendee.get("self") is True:
            return RESPONSE_STATUS_MAP.get(attendee.get("responseStatus", ""))
    return None


def extract_rrule(event: dict) -> str | None:
    """Extract the RRULE string from recurrence data.

    Finds the first entry starting with ``"RRULE:"`` in the recurrence
    array and returns it with the prefix stripped.
    """
    for entry in event.get("recurrence", []):
        if isinstance(entry, str) and entry.startswith("RRULE:"):
            return entry[len("RRULE:"):]
    return None


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text, returning stripped plain text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def extract_body(event: dict) -> str | None:
    """Extract a plain-text body from the event description.

    Returns the HTML-stripped description, or None if empty/absent.
    """
    raw = event.get("description", "")
    if not raw:
        return None
    cleaned = strip_html_tags(raw)
    return cleaned if cleaned else None


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
        A Google Calendar event dict from the Calendar API v3.
    calendar_name:
        Human-readable name of the source calendar.
    sync_time:
        ISO-8601 UTC timestamp for ``bpkm:lastSyncedAt``.

    Returns
    -------
    dict
        Property mapping where keys are full IRIs (except ``dcterms:``
        prefixed ones which use compact form). Keys with ``None`` values
        are excluded.
    """
    is_all_day, start_val, end_val = detect_all_day(event)

    # Reminder minutes: first override, or omit
    reminder_minutes: str | None = None
    reminders = event.get("reminders", {})
    overrides = reminders.get("overrides")
    if overrides and len(overrides) > 0:
        reminder_minutes = str(overrides[0].get("minutes", ""))
        if not reminder_minutes:
            reminder_minutes = None

    props: dict[str, str | None] = {
        "dcterms:title": event.get("summary") or "(No title)",
        "schema:startDate": start_val,
        "schema:endDate": end_val,
        f"{BPKM}allDay": "true" if is_all_day else "false",
        f"{BPKM}timeZone": event.get("start", {}).get("timeZone"),
        f"{BPKM}eventStatus": STATUS_MAP.get(event.get("status", ""), "confirmed"),
        f"{BPKM}location": event.get("location"),
        f"{BPKM}visibility": VISIBILITY_MAP.get(event.get("visibility", "")),
        f"{BPKM}showAs": TRANSPARENCY_MAP.get(event.get("transparency", "")),
        f"{BPKM}conferenceUrl": extract_conference_url(event),
        f"{BPKM}recurrenceRule": extract_rrule(event),
        f"{BPKM}recurringEventId": event.get("recurringEventId"),
        f"{BPKM}responseStatus": extract_response_status(event),
        f"{BPKM}reminderMinutes": reminder_minutes,
        f"{BPKM}calendarName": calendar_name,
        f"{BPKM}externalId": event.get("id"),
        f"{BPKM}externalUrl": event.get("htmlLink"),
        f"{BPKM}externalProvider": "google-calendar",
        f"{BPKM}lastSyncedAt": sync_time,
        "dcterms:created": event.get("created"),
        "dcterms:modified": event.get("updated"),
    }

    # Strip None values
    return {k: v for k, v in props.items() if v is not None}


# ---------------------------------------------------------------------------
# Reverse mapping (push-back)
# ---------------------------------------------------------------------------


def build_event_patch(event_props: dict, google_email: str) -> dict:
    """Build a Google Calendar Events.patch body from bpkm event properties.

    Currently supports RSVP push-back only (per D213).  Constructs a
    partial attendees array with the self-attendee entry so that PATCH
    updates only the user's response status.

    Parameters
    ----------
    event_props:
        Property dict with full IRI keys (e.g.
        ``urn:sempkm:model:basic-pkm:responseStatus``).
    google_email:
        The authenticated user's Google email (from state).

    Returns
    -------
    dict
        Google Events.patch body with ``attendees`` and
        ``attendeesOmitted``, or empty dict if no pushable changes.
    """
    bpkm_status = event_props.get(f"{BPKM}responseStatus")
    if not bpkm_status:
        return {}

    gcal_status = REVERSE_RESPONSE_STATUS_MAP.get(bpkm_status)
    if not gcal_status:
        return {}

    return {
        "attendees": [
            {
                "email": google_email,
                "self": True,
                "responseStatus": gcal_status,
            }
        ],
        "attendeesOmitted": True,
    }
