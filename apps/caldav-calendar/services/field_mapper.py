"""Pure field mapping between iCalendar VEVENT components and bpkm:Event properties.

All functions are side-effect-free: no network, no logging, no state.
Property keys use full IRIs for bpkm properties because the ``bpkm:``
prefix is not in the platform's COMMON_PREFIXES.

The icalendar library returns typed objects (vDate, vDatetime, vCalAddress,
vRecur) with different access patterns for single vs multi-valued properties.
Each extraction function handles these type variations defensively.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta

import icalendar


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Full IRI prefix for basic-pkm model properties
BPKM = "urn:sempkm:model:basic-pkm:"

# iCalendar STATUS → bpkm:eventStatus
STATUS_MAP: dict[str, str] = {
    "TENTATIVE": "tentative",
    "CONFIRMED": "confirmed",
    "CANCELLED": "cancelled",
}

# iCalendar CLASS → bpkm:visibility
CLASS_MAP: dict[str, str] = {
    "PUBLIC": "public",
    "PRIVATE": "private",
    "CONFIDENTIAL": "confidential",
}

# iCalendar TRANSP → bpkm:showAs
TRANSP_MAP: dict[str, str] = {
    "OPAQUE": "busy",
    "TRANSPARENT": "free",
}

# iCalendar PARTSTAT → bpkm:responseStatus
PARTSTAT_MAP: dict[str, str] = {
    "NEEDS-ACTION": "needs-action",
    "ACCEPTED": "accepted",
    "DECLINED": "declined",
    "TENTATIVE": "tentative",
}

# Reverse: bpkm:responseStatus → iCalendar PARTSTAT (for push-back)
REVERSE_RESPONSE_STATUS_MAP: dict[str, str] = {
    "needs-action": "NEEDS-ACTION",
    "accepted": "ACCEPTED",
    "declined": "DECLINED",
    "tentative": "TENTATIVE",
}


# ---------------------------------------------------------------------------
# IRI slug
# ---------------------------------------------------------------------------


def compute_event_slug(calendar_href: str, uid: str) -> str:
    """Compute a deterministic slug for a CalDAV event.

    Used as the local part of a platform-minted Event IRI:
    ``{base_namespace}/Event/caldav-{hash12}``.
    """
    raw = f"{calendar_href}:{uid}"
    return "caldav-" + hashlib.sha256(raw.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Extraction helpers (all pure, all return None on missing data)
# ---------------------------------------------------------------------------


def detect_all_day(component) -> tuple[bool, str | None, str | None]:
    """Detect whether a VEVENT is all-day and extract start/end as strings.

    Returns:
        ``(is_all_day, start_str, end_str)`` where values are
        xsd:date strings (all-day) or xsd:dateTime ISO strings (timed).

    Note: ``isinstance(dt, date) and not isinstance(dt, datetime)`` is
    required because ``datetime`` is a subclass of ``date``.
    """
    dtstart_prop = component.get("DTSTART")
    dtend_prop = component.get("DTEND")

    if dtstart_prop is None:
        return (False, None, None)

    dt_start = dtstart_prop.dt
    is_all_day = isinstance(dt_start, date) and not isinstance(dt_start, datetime)

    if is_all_day:
        start_str = dt_start.isoformat()
        end_str = dtend_prop.dt.isoformat() if dtend_prop else None
        return (True, start_str, end_str)

    start_str = dt_start.isoformat()
    end_str = dtend_prop.dt.isoformat() if dtend_prop else None
    return (False, start_str, end_str)


def extract_timezone(component) -> str | None:
    """Extract the TZID parameter from DTSTART, if present."""
    dtstart_prop = component.get("DTSTART")
    if dtstart_prop is None:
        return None

    tzid = dtstart_prop.params.get("TZID")
    if tzid:
        return str(tzid)

    # For UTC datetimes, check if the dt has UTC tzinfo
    dt = dtstart_prop.dt
    if isinstance(dt, datetime) and dt.tzinfo is not None:
        tz_name = str(dt.tzinfo)
        if tz_name == "UTC" or tz_name == "datetime.timezone.utc":
            return "UTC"
        # ZoneInfo objects have .key attribute
        if hasattr(dt.tzinfo, "key"):
            return dt.tzinfo.key

    return None


def extract_status(component) -> str | None:
    """Extract STATUS and map to bpkm:eventStatus (case-insensitive)."""
    status = component.get("STATUS")
    if status is None:
        return None
    return STATUS_MAP.get(str(status).upper())


def extract_visibility(component) -> str | None:
    """Extract CLASS and map to bpkm:visibility (case-insensitive)."""
    cls = component.get("CLASS")
    if cls is None:
        return None
    return CLASS_MAP.get(str(cls).upper())


def extract_show_as(component) -> str | None:
    """Extract TRANSP and map to bpkm:showAs (case-insensitive)."""
    transp = component.get("TRANSP")
    if transp is None:
        return None
    return TRANSP_MAP.get(str(transp).upper())


def extract_rrule(component) -> str | None:
    """Extract RRULE as a clean RFC 5545 string (no ``RRULE:`` prefix).

    The icalendar library's ``vRecur.to_ical()`` returns bytes like
    ``b'FREQ=WEEKLY;BYDAY=MO'`` — already without the RRULE: prefix.
    We strip it defensively in case a future library version changes.
    """
    rrule = component.get("RRULE")
    if rrule is None:
        return None
    raw = rrule.to_ical().decode("utf-8")
    if raw.upper().startswith("RRULE:"):
        raw = raw[len("RRULE:"):]
    return raw


def extract_recurrence_id(component) -> str | None:
    """Extract RECURRENCE-ID as an ISO string."""
    recid = component.get("RECURRENCE-ID")
    if recid is None:
        return None
    dt = recid.dt
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.isoformat()
    return dt.isoformat()


def _normalize_to_list(value) -> list:
    """Normalize a single value or list to a list. None → empty list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_attendees(component) -> list[dict]:
    """Extract ATTENDEE(s) as a list of dicts with email, name, partstat.

    Handles the icalendar library quirk: ``component.get('ATTENDEE')``
    returns a single ``vCalAddress`` for one attendee, a ``list`` for
    multiple, and ``None`` for zero.
    """
    raw = component.get("ATTENDEE")
    attendees = _normalize_to_list(raw)

    result = []
    for att in attendees:
        email = str(att)
        # Strip mailto: prefix (case-insensitive)
        if email.lower().startswith("mailto:"):
            email = email[len("mailto:"):]

        name = att.params.get("CN")
        name = str(name) if name else None

        partstat = att.params.get("PARTSTAT")
        partstat_mapped = PARTSTAT_MAP.get(str(partstat).upper()) if partstat else None

        result.append({
            "email": email,
            "name": name,
            "partstat": partstat_mapped,
        })

    return result


def extract_self_response_status(component, user_email: str | None) -> str | None:
    """Find the authenticated user's attendee entry and return their response status.

    Matches by email (case-insensitive). Returns mapped PARTSTAT or None.
    """
    if not user_email:
        return None

    attendees = extract_attendees(component)
    user_lower = user_email.lower()

    for att in attendees:
        if att["email"].lower() == user_lower:
            return att.get("partstat")

    return None


def extract_organizer(component) -> dict | None:
    """Extract ORGANIZER as a dict with email and name."""
    org = component.get("ORGANIZER")
    if org is None:
        return None

    email = str(org)
    if email.lower().startswith("mailto:"):
        email = email[len("mailto:"):]

    name = org.params.get("CN")
    name = str(name) if name else None

    return {"email": email, "name": name}


def extract_reminder_minutes(component) -> int | None:
    """Extract the first VALARM trigger as positive minutes.

    Walks VALARM subcomponents, takes the first one with a TRIGGER,
    converts the (typically negative) timedelta to positive minutes.
    """
    for sub in component.subcomponents:
        if sub.name == "VALARM":
            trigger = sub.get("TRIGGER")
            if trigger is None:
                continue
            td = trigger.dt
            if isinstance(td, timedelta):
                return int(abs(td.total_seconds()) / 60)
    return None


def extract_categories(component) -> list[str]:
    """Extract CATEGORIES as a flat list of strings.

    Handles icalendar library quirks:
    - Single ``add('CATEGORIES', [...])`` → ``vCategory`` with ``to_ical()``
      returning comma-separated bytes
    - Multiple ``add('CATEGORIES', [...])`` → ``list`` of ``vCategory``
    - Each vCategory's ``to_ical()`` returns comma-separated bytes
    """
    raw = component.get("CATEGORIES")
    if raw is None:
        return []

    items = _normalize_to_list(raw)

    result = []
    for item in items:
        decoded = item.to_ical().decode("utf-8")
        for cat in decoded.split(","):
            stripped = cat.strip()
            if stripped:
                result.append(stripped)

    return result


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text, returning stripped plain text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def extract_body(component) -> str | None:
    """Extract DESCRIPTION as plain text (HTML stripped if present)."""
    desc = component.get("DESCRIPTION")
    if desc is None:
        return None
    raw = str(desc)
    if not raw:
        return None
    cleaned = strip_html_tags(raw)
    return cleaned if cleaned else None


# ---------------------------------------------------------------------------
# Property builder
# ---------------------------------------------------------------------------


def build_event_properties(
    component,
    calendar_name: str,
    sync_time: str,
    user_email: str | None = None,
) -> dict:
    """Build a properties dict for ``object.create`` / ``object.patch``.

    Parameters
    ----------
    component:
        An ``icalendar.Event`` component (parsed VEVENT).
    calendar_name:
        Human-readable name of the source calendar.
    sync_time:
        ISO-8601 UTC timestamp for ``bpkm:lastSyncedAt``.
    user_email:
        The authenticated user's email for self-response-status extraction.

    Returns
    -------
    dict
        Property mapping where keys are full IRIs (except ``dcterms:``/
        ``schema:`` prefixed ones which use compact form). Keys with
        ``None`` values are excluded.
    """
    is_all_day, start_val, end_val = detect_all_day(component)

    # UID for externalId
    uid = component.get("UID")
    uid_str = str(uid) if uid else None

    # LOCATION
    location = component.get("LOCATION")
    location_str = str(location) if location else None

    # CREATED / LAST-MODIFIED
    created_prop = component.get("CREATED")
    created_str = None
    if created_prop is not None:
        created_str = created_prop.dt.isoformat()

    modified_prop = component.get("LAST-MODIFIED")
    modified_str = None
    if modified_prop is not None:
        modified_str = modified_prop.dt.isoformat()

    # URL
    url_prop = component.get("URL")
    url_str = str(url_prop) if url_prop else None

    # Extract attendees / organizer as dicts (person matching is in T02)
    attendees = extract_attendees(component)
    organizer = extract_organizer(component)

    # Categories → tags
    categories = extract_categories(component)

    # Title with fallback
    summary = component.get("SUMMARY")
    title = str(summary) if summary else "(No title)"

    props: dict[str, object] = {
        "dcterms:title": title,
        "schema:startDate": start_val,
        "schema:endDate": end_val,
        f"{BPKM}allDay": "true" if is_all_day else "false",
        f"{BPKM}timeZone": extract_timezone(component),
        f"{BPKM}eventStatus": extract_status(component),
        f"{BPKM}location": location_str,
        f"{BPKM}visibility": extract_visibility(component),
        f"{BPKM}showAs": extract_show_as(component),
        f"{BPKM}recurrenceRule": extract_rrule(component),
        f"{BPKM}recurringEventId": extract_recurrence_id(component),
        f"{BPKM}responseStatus": extract_self_response_status(component, user_email),
        f"{BPKM}reminderMinutes": extract_reminder_minutes(component),
        f"{BPKM}tags": categories if categories else None,
        f"{BPKM}externalId": uid_str,
        f"{BPKM}externalUrl": url_str,
        f"{BPKM}externalProvider": "caldav",
        f"{BPKM}calendarName": calendar_name,
        f"{BPKM}lastSyncedAt": sync_time,
        "dcterms:created": created_str,
        "dcterms:modified": modified_str,
    }

    # Body extracted separately (not a flat property in the dict for create)
    body = extract_body(component)
    if body is not None:
        props[f"{BPKM}body"] = body

    # Attendees and organizer as dicts (T02 sync engine resolves to IRIs)
    if attendees:
        props[f"{BPKM}attendees"] = attendees
    if organizer:
        props[f"{BPKM}organizer"] = organizer

    # Strip None values
    return {k: v for k, v in props.items() if v is not None}


# ---------------------------------------------------------------------------
# Reverse mapping (push-back)
# ---------------------------------------------------------------------------


def build_event_patch(event_props: dict, user_email: str | None) -> dict:
    """Build an iCalendar VEVENT patch from bpkm event properties.

    Extracts pushable changes (currently RSVP status) from the bpkm property
    dict and maps them back to iCalendar values.

    Parameters
    ----------
    event_props : dict
        Property dict with full-IRI keys (e.g. ``urn:sempkm:model:basic-pkm:responseStatus``).
    user_email : str or None
        The authenticated user's email. Required for RSVP push-back
        (identifies which ATTENDEE to modify).

    Returns
    -------
    dict
        Patch dict with iCalendar-level keys. Currently supports:
        ``{"responseStatus": "<PARTSTAT>"}`` for RSVP changes.
        Empty dict if no pushable changes detected.
    """
    if not user_email:
        return {}

    response_status = event_props.get(f"{BPKM}responseStatus")
    if not response_status:
        return {}

    partstat = REVERSE_RESPONSE_STATUS_MAP.get(response_status)
    if not partstat:
        return {}

    return {"responseStatus": partstat}


def modify_vevent_partstat(
    ics_text: str, user_email: str, new_partstat: str
) -> str:
    """Modify the PARTSTAT of a specific ATTENDEE in an iCalendar VCALENDAR.

    Parses *ics_text*, finds the VEVENT, locates the ATTENDEE whose
    ``mailto:`` URI matches *user_email* (case-insensitive on the email
    portion), sets its ``PARTSTAT`` parameter to *new_partstat*, and
    regenerates the full VCALENDAR string.

    Parameters
    ----------
    ics_text : str
        A complete VCALENDAR string containing at least one VEVENT.
    user_email : str
        Email to match against ATTENDEE ``mailto:`` URIs.
    new_partstat : str
        iCalendar PARTSTAT value (e.g. ``"ACCEPTED"``, ``"DECLINED"``).

    Returns
    -------
    str
        The regenerated VCALENDAR string with the modified PARTSTAT,
        or the original *ics_text* unchanged if no matching ATTENDEE
        was found or the VEVENT has no ATTENDEEs.
    """
    cal = icalendar.Calendar.from_ical(ics_text)
    user_lower = user_email.lower()
    modified = False

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        raw_attendees = component.get("ATTENDEE")
        if raw_attendees is None:
            continue

        # Determine if single or list — work directly to preserve format
        if isinstance(raw_attendees, list):
            for attendee in raw_attendees:
                email = str(attendee)
                if email.lower().startswith("mailto:"):
                    email = email[len("mailto:"):]
                if email.lower() == user_lower:
                    attendee.params["PARTSTAT"] = icalendar.vText(new_partstat)
                    modified = True
                    break
        else:
            # Single vCalAddress
            email = str(raw_attendees)
            if email.lower().startswith("mailto:"):
                email = email[len("mailto:"):]
            if email.lower() == user_lower:
                raw_attendees.params["PARTSTAT"] = icalendar.vText(new_partstat)
                modified = True

    if not modified:
        return ics_text

    return cal.to_ical().decode("utf-8")
