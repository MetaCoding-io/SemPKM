"""Pure field mapping between Monday.com column values and bpkm:Task properties.

All functions are side-effect-free: no network, no logging, no state.
Property keys use full IRIs for bpkm properties because the ``bpkm:``
prefix is not in the platform's COMMON_PREFIXES.

Key design decisions:
- Monday.com columns are fully user-configurable. The mapper accepts a
  ``column_mapping`` dict that specifies which Monday.com column ID maps
  to which bpkm property.
- Column value format is asymmetric: read values have one JSON shape
  (e.g., status reads as ``{"label": "Working on it", "index": 1}``)
  but mutations expect a different shape (e.g., status writes as
  ``{"label": "Done"}``). Each column type has a dedicated extractor
  and serializer to handle both directions.
- Status/priority label mappings are user-configurable with sensible
  defaults that cover common Monday.com board configurations.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Full IRI prefix for basic-pkm model properties
BPKM = "urn:sempkm:model:basic-pkm:"

# Monday.com status label → bpkm:taskStatus
# Covers the most common default status labels in Monday.com boards.
DEFAULT_STATUS_MAP: dict[str, str] = {
    "Done": "done",
    "Working on it": "in-progress",
    "Stuck": "blocked",
    "Not Started": "todo",
    "": "todo",
}

# Monday.com priority label → bpkm:priority
# Covers the default priority column labels in Monday.com.
DEFAULT_PRIORITY_MAP: dict[str, str] = {
    "Critical ⚨": "critical",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "": "low",
}

# bpkm:taskStatus → Monday.com status label (reverse for push sync)
REVERSE_STATUS_MAP: dict[str, str] = {
    "todo": "Not Started",
    "in-progress": "Working on it",
    "done": "Done",
    "blocked": "Stuck",
    "cancelled": "Done",
}

# bpkm:priority → Monday.com priority label (reverse for push sync)
REVERSE_PRIORITY_MAP: dict[str, str] = {
    "critical": "Critical ⚨",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

# Mapping from bpkm property short names to their column types.
# Used by build_task_properties to dispatch to the correct extractor,
# and by build_reverse_column_values to dispatch to the correct serializer.
PROPERTY_COLUMN_TYPES: dict[str, str] = {
    "taskStatus": "status",
    "priority": "status",      # priority is a status-type column in Monday.com
    "dueDate": "date",
    "assignedTo": "people",
    "description": "long_text",
    "taskGroup": "text",
    "tags": "tags",
    "dropdown": "dropdown",
    "estimatedEffort": "numbers",
}


# ---------------------------------------------------------------------------
# Column value extractors (read direction: Monday.com → bpkm)
# ---------------------------------------------------------------------------


def _parse_col_value(col_value: str | dict | None) -> dict | str | None:
    """Parse a column value that may be a JSON string, dict, or None.

    Monday.com returns ``column_values[].value`` as a JSON string.
    Some API wrappers may pre-parse it into a dict.
    """
    if col_value is None:
        return None
    if isinstance(col_value, dict):
        return col_value
    if isinstance(col_value, str):
        if not col_value or col_value == "null":
            return None
        try:
            parsed = json.loads(col_value)
            return parsed
        except (json.JSONDecodeError, TypeError):
            return col_value  # plain text value
    return None


def _extract_status(
    col_value: str | dict | None,
    label_mapping: dict[str, str] | None = None,
) -> str:
    """Extract a bpkm status value from a Monday.com status column.

    Status column value shape (read): ``{"label": "Working on it", "index": 1}``

    Args:
        col_value: Raw column value (JSON string or dict).
        label_mapping: Maps Monday.com status labels to bpkm status values.
            Defaults to ``DEFAULT_STATUS_MAP``.

    Returns:
        bpkm status string. Defaults to ``"todo"`` for unknown labels.
    """
    if label_mapping is None:
        label_mapping = DEFAULT_STATUS_MAP

    parsed = _parse_col_value(col_value)
    if parsed is None:
        return label_mapping.get("", "todo")

    if isinstance(parsed, dict):
        label = parsed.get("label", "")
    else:
        label = str(parsed)

    return label_mapping.get(label, "todo")


def _extract_priority(
    col_value: str | dict | None,
    label_mapping: dict[str, str] | None = None,
) -> str | None:
    """Extract a bpkm priority value from a Monday.com priority column.

    Priority is a status-type column in Monday.com with labels like
    "High", "Medium", "Low", "Critical ⚨".

    Args:
        col_value: Raw column value (JSON string or dict).
        label_mapping: Maps Monday.com priority labels to bpkm priority values.
            Defaults to ``DEFAULT_PRIORITY_MAP``.

    Returns:
        bpkm priority string, or None for empty/unknown labels.
    """
    if label_mapping is None:
        label_mapping = DEFAULT_PRIORITY_MAP

    parsed = _parse_col_value(col_value)
    if parsed is None:
        return None

    if isinstance(parsed, dict):
        label = parsed.get("label", "")
    else:
        label = str(parsed)

    if not label:
        return None

    return label_mapping.get(label)


def _extract_date(col_value: str | dict | None) -> str | None:
    """Extract a date string from a Monday.com date column.

    Date column value shape (read): ``{"date": "2025-01-15", "changed_at": "..."}``

    Returns:
        Date string (YYYY-MM-DD) or None.
    """
    parsed = _parse_col_value(col_value)
    if parsed is None:
        return None

    if isinstance(parsed, dict):
        date_val = parsed.get("date")
        if date_val:
            return str(date_val)[:10]
        return None

    # Plain string date
    val = str(parsed).strip()
    return val[:10] if val else None


def _extract_people(col_value: str | dict | None) -> int | None:
    """Extract the first person's user ID from a Monday.com people column.

    People column value shape (read):
    ``{"personsAndTeams": [{"id": 12345, "kind": "person"}]}``

    Returns:
        First person's numeric ID, or None if no people assigned.
    """
    parsed = _parse_col_value(col_value)
    if parsed is None:
        return None

    if not isinstance(parsed, dict):
        return None

    persons = parsed.get("personsAndTeams", [])
    if not persons or not isinstance(persons, list):
        return None

    for entry in persons:
        if isinstance(entry, dict) and entry.get("kind") == "person":
            person_id = entry.get("id")
            if person_id is not None:
                return int(person_id)

    # Fallback: return first entry's id regardless of kind
    first = persons[0]
    if isinstance(first, dict) and "id" in first:
        return int(first["id"])

    return None


def _extract_text(col_value: str | dict | None) -> str | None:
    """Extract text from a Monday.com text column.

    Text column value can be a plain string or ``{"text": "...", "value": "..."}``.

    Returns:
        Text content or None.
    """
    parsed = _parse_col_value(col_value)
    if parsed is None:
        return None

    if isinstance(parsed, dict):
        # Long text or rich text column
        text = parsed.get("text")
        if text:
            return str(text)
        value = parsed.get("value")
        if value:
            return str(value)
        return None

    val = str(parsed).strip()
    return val if val else None


def _extract_long_text(col_value: str | dict | None) -> str | None:
    """Extract text from a Monday.com long_text column.

    Long text column value shape: ``{"text": "content", "value": "..."}``
    Delegates to _extract_text since the shape is compatible.

    Returns:
        Text content or None.
    """
    return _extract_text(col_value)


def _extract_numbers(col_value: str | dict | None) -> str | None:
    """Extract a numeric value from a Monday.com numbers column.

    Numbers column value can be ``"42"`` or ``{"value": "42"}``.

    Returns:
        String representation of the number, or None.
    """
    parsed = _parse_col_value(col_value)
    if parsed is None:
        return None

    if isinstance(parsed, dict):
        value = parsed.get("value")
        if value is not None:
            return str(value)
        return None

    val = str(parsed).strip()
    return val if val else None


def _extract_tags(col_value: str | dict | None) -> list[int]:
    """Extract tag IDs from a Monday.com tags column.

    Tags column value shape (read): ``{"tag_ids": [1, 2, 3]}``
    Tag IDs need to be resolved to names by the caller via ``get_tags()``.

    Returns:
        List of integer tag IDs (empty list if no tags).
    """
    parsed = _parse_col_value(col_value)
    if parsed is None:
        return []

    if isinstance(parsed, dict):
        tag_ids = parsed.get("tag_ids", [])
        if isinstance(tag_ids, list):
            return [int(tid) for tid in tag_ids if tid is not None]
        return []

    return []


def _extract_dropdown(col_value: str | dict | None) -> list[str]:
    """Extract dropdown labels from a Monday.com dropdown column.

    Dropdown column value shape (read):
    ``{"ids": [1, 2], "labels": ["Label A", "Label B"]}``
    or in some API versions: ``{"values": [{"id": 1, "name": "Label A"}]}``

    Returns:
        List of label strings (empty list if no selections).
    """
    parsed = _parse_col_value(col_value)
    if parsed is None:
        return []

    if isinstance(parsed, dict):
        # Primary format: {"labels": [...]}
        labels = parsed.get("labels")
        if isinstance(labels, list):
            return [str(lbl) for lbl in labels if lbl]

        # Alternative format: {"values": [{"id": ..., "name": "..."}]}
        values = parsed.get("values")
        if isinstance(values, list):
            return [
                str(v.get("name", ""))
                for v in values
                if isinstance(v, dict) and v.get("name")
            ]

        return []

    return []


def _extract_dependency(col_value: str | dict | None) -> list[int]:
    """Extract linked item IDs from a Monday.com dependency column.

    Dependency column value shape (read):
    ``{"linkedPulseIds": [{"linkedPulseId": 12345}]}``

    Returns:
        List of integer item IDs (empty list if no dependencies).
    """
    parsed = _parse_col_value(col_value)
    if parsed is None:
        return []
    if isinstance(parsed, dict):
        linked = parsed.get("linkedPulseIds", [])
        if isinstance(linked, list):
            return [
                int(lp["linkedPulseId"])
                for lp in linked
                if isinstance(lp, dict) and "linkedPulseId" in lp
            ]
    return []


# Dispatcher mapping column type strings to extractor functions.
# status and priority are handled specially (they need label mappings).
_EXTRACTORS: dict[str, callable] = {
    "date": _extract_date,
    "people": _extract_people,
    "text": _extract_text,
    "long_text": _extract_long_text,
    "numbers": _extract_numbers,
    "tags": _extract_tags,
    "dropdown": _extract_dropdown,
    "dependency": _extract_dependency,
}


# ---------------------------------------------------------------------------
# External URL construction
# ---------------------------------------------------------------------------


def build_external_url(board_id: str | int, item_id: str | int) -> str:
    """Construct a Monday.com item URL from board and item IDs.

    Monday.com items don't have a direct URL in the API response.
    The URL is constructed from the board_id and item_id.

    Returns:
        URL string like ``https://monday.com/boards/123/pulses/456``.
    """
    return f"https://monday.com/boards/{board_id}/pulses/{item_id}"


# ---------------------------------------------------------------------------
# IRI slug
# ---------------------------------------------------------------------------


def compute_slug(item_name: str, item_id: str | int) -> str:
    """Compute a deterministic slug for a Monday.com item.

    The slug is used as the local part of a platform-minted Task IRI:
    ``{base_namespace}/Task/monday-{hash16}``.

    Args:
        item_name: Monday.com item name (title).
        item_id: Monday.com item ID (numeric string or int).

    Returns:
        Slug string in the format ``monday-{16 hex chars}``.
    """
    composite = f"{item_name}#{item_id}"
    digest = hashlib.sha256(composite.encode()).hexdigest()[:16]
    return f"monday-{digest}"


# ---------------------------------------------------------------------------
# Property builder — Monday.com → bpkm (pull)
# ---------------------------------------------------------------------------


def build_task_properties(
    item: dict,
    column_mapping: dict[str, str],
    status_label_mapping: dict[str, str] | None = None,
    priority_label_mapping: dict[str, str] | None = None,
    board_id: str | int | None = None,
    sync_time: str | None = None,
) -> tuple[dict, int | None]:
    """Build a bpkm properties dict from a Monday.com item.

    Parameters
    ----------
    item:
        A Monday.com item dict with ``id``, ``name``, ``column_values``
        (list of ``{"id": "col_id", "text": "...", "value": "...", "type": "status"}``).
    column_mapping:
        Maps bpkm property short names to Monday.com column IDs.
        Example: ``{"taskStatus": "status_col", "dueDate": "date4",
        "assignedTo": "people_col", "priority": "priority_col"}``.
    status_label_mapping:
        Custom mapping from Monday.com status labels to bpkm taskStatus values.
        Defaults to ``DEFAULT_STATUS_MAP``.
    priority_label_mapping:
        Custom mapping from Monday.com priority labels to bpkm priority values.
        Defaults to ``DEFAULT_PRIORITY_MAP``.
    board_id:
        Optional board ID for constructing the external URL.
    sync_time:
        ISO-8601 UTC timestamp for ``bpkm:lastSyncedAt``. When ``None``,
        the current UTC time is used.

    Returns
    -------
    tuple[dict, int | None]
        A tuple of (properties_dict, assignee_user_id).
        ``assignee_user_id`` is the raw Monday.com person ID for the caller
        to resolve via PersonMatcher. It is ``None`` if no person is assigned.
    """
    if sync_time is None:
        sync_time = datetime.now(timezone.utc).isoformat()

    if status_label_mapping is None:
        status_label_mapping = DEFAULT_STATUS_MAP
    if priority_label_mapping is None:
        priority_label_mapping = DEFAULT_PRIORITY_MAP

    # Build column ID → column value lookup
    col_lookup: dict[str, dict] = {}
    for cv in item.get("column_values", []):
        if isinstance(cv, dict) and "id" in cv:
            col_lookup[cv["id"]] = cv

    item_id = str(item.get("id", ""))
    item_name = item.get("name", "")
    assignee_user_id: int | None = None

    # Start with always-present properties
    props: dict[str, str | list | None] = {
        "dcterms:title": item_name,
        f"{BPKM}externalId": item_id,
        f"{BPKM}externalProvider": "monday",
    }

    # External URL (requires board_id)
    if board_id is not None:
        props[f"{BPKM}externalUrl"] = build_external_url(board_id, item_id)

    # Process each mapped property
    for bpkm_prop, col_id in column_mapping.items():
        col_data = col_lookup.get(col_id)
        if col_data is None:
            continue

        # Get the raw value — prefer "value" (JSON), fall back to "text"
        raw_value = col_data.get("value")
        col_type = col_data.get("type", "")

        # Dispatch based on bpkm property name and column type
        if bpkm_prop == "taskStatus":
            value = _extract_status(raw_value, status_label_mapping)
            props[f"{BPKM}taskStatus"] = value
            # Also store the raw label for display
            parsed = _parse_col_value(raw_value)
            if isinstance(parsed, dict):
                label = parsed.get("label", "")
                if label:
                    props[f"{BPKM}externalStatus"] = label

        elif bpkm_prop == "priority":
            value = _extract_priority(raw_value, priority_label_mapping)
            if value:
                props[f"{BPKM}priority"] = value

        elif bpkm_prop == "dueDate":
            value = _extract_date(raw_value)
            if value:
                props[f"{BPKM}dueDate"] = value

        elif bpkm_prop == "assignedTo":
            assignee_user_id = _extract_people(raw_value)

        elif bpkm_prop == "description":
            value = _extract_long_text(raw_value) or _extract_text(raw_value)
            if value:
                props[f"{BPKM}description"] = value

        elif bpkm_prop == "taskGroup":
            # Text-type column used as group/sprint name
            value = _extract_text(raw_value)
            if value:
                props[f"{BPKM}taskGroup"] = value

        elif bpkm_prop == "tags":
            tag_ids = _extract_tags(raw_value)
            if tag_ids:
                props[f"{BPKM}tags"] = tag_ids

        elif bpkm_prop == "dropdown":
            labels = _extract_dropdown(raw_value)
            if labels:
                props[f"{BPKM}tags"] = labels

        elif bpkm_prop == "estimatedEffort":
            value = _extract_numbers(raw_value)
            if value:
                props[f"{BPKM}estimatedEffort"] = value

        elif bpkm_prop == "dependency":
            dep_ids = _extract_dependency(raw_value)
            if dep_ids:
                props["_dependency_item_ids"] = dep_ids

        else:
            # Generic extraction for unmapped property types
            col_type_lower = col_type.lower() if col_type else ""
            extractor = _EXTRACTORS.get(col_type_lower)
            if extractor:
                value = extractor(raw_value)
                if value is not None and value != "" and value != []:
                    props[f"{BPKM}{bpkm_prop}"] = value

    # Strip None, empty string, and empty list values
    cleaned = {
        k: v
        for k, v in props.items()
        if v is not None and v != "" and v != []
    }

    # lastSyncedAt is always present (never stripped)
    cleaned[f"{BPKM}lastSyncedAt"] = sync_time

    return cleaned, assignee_user_id


# ---------------------------------------------------------------------------
# Reverse mapping — bpkm → Monday.com (push)
# ---------------------------------------------------------------------------

# Maps bpkm property short names to serializer functions.
# Each serializer takes a bpkm property value and returns
# a JSON-serializable value for Monday.com mutation.


def _serialize_status(
    value: str,
    reverse_mapping: dict[str, str] | None = None,
) -> str:
    """Serialize a bpkm taskStatus to Monday.com status column value.

    Write format: ``{"label": "Done"}`` (JSON string).
    """
    if reverse_mapping is None:
        reverse_mapping = REVERSE_STATUS_MAP
    label = reverse_mapping.get(value)
    if label is None:
        return json.dumps({"label": value})
    return json.dumps({"label": label})


def _serialize_priority(
    value: str,
    reverse_mapping: dict[str, str] | None = None,
) -> str:
    """Serialize a bpkm priority to Monday.com priority column value.

    Write format: ``{"label": "High"}`` (JSON string).
    """
    if reverse_mapping is None:
        reverse_mapping = REVERSE_PRIORITY_MAP
    label = reverse_mapping.get(value)
    if label is None:
        return json.dumps({"label": value})
    return json.dumps({"label": label})


def _serialize_date(value: str) -> str:
    """Serialize a date to Monday.com date column value.

    Write format: ``{"date": "2025-01-15"}`` (JSON string).
    """
    return json.dumps({"date": value[:10]})


def _serialize_text(value: str) -> str:
    """Serialize text for Monday.com text column value.

    Write format: plain string value.
    """
    return str(value)


def _serialize_numbers(value: str) -> str:
    """Serialize a number for Monday.com numbers column value.

    Write format: plain numeric string.
    """
    return str(value)


def _serialize_people(value: int | str) -> str:
    """Serialize a person ID for Monday.com people column value.

    Write format: ``{"personsAndTeams": [{"id": 12345, "kind": "person"}]}``
    """
    person_id = int(value) if isinstance(value, str) else value
    return json.dumps({
        "personsAndTeams": [{"id": person_id, "kind": "person"}]
    })


def build_reverse_column_values(
    task_properties: dict,
    column_mapping: dict[str, str],
    reverse_status_mapping: dict[str, str] | None = None,
    reverse_priority_mapping: dict[str, str] | None = None,
) -> dict[str, str]:
    """Convert bpkm task properties to Monday.com column values for mutation.

    Parameters
    ----------
    task_properties:
        Property dict with full IRI keys or short bpkm property names.
    column_mapping:
        Maps bpkm property short names to Monday.com column IDs.
        Example: ``{"taskStatus": "status_col", "dueDate": "date4"}``.
    reverse_status_mapping:
        Custom reverse mapping from bpkm taskStatus to Monday.com status labels.
        Defaults to ``REVERSE_STATUS_MAP``.
    reverse_priority_mapping:
        Custom reverse mapping from bpkm priority to Monday.com priority labels.
        Defaults to ``REVERSE_PRIORITY_MAP``.

    Returns
    -------
    dict[str, str]
        Mapping of ``{column_id: json_value_string}`` ready for
        ``change_multiple_column_values``.
    """
    result: dict[str, str] = {}

    # Build a lookup that supports both full IRI keys and short names
    def _get_prop(short_name: str) -> str | int | None:
        full_key = f"{BPKM}{short_name}"
        val = task_properties.get(full_key)
        if val is not None:
            return val
        return task_properties.get(short_name)

    for bpkm_prop, col_id in column_mapping.items():
        if bpkm_prop == "taskStatus":
            value = _get_prop("taskStatus")
            if value:
                result[col_id] = _serialize_status(
                    str(value), reverse_status_mapping
                )

        elif bpkm_prop == "priority":
            value = _get_prop("priority")
            if value:
                result[col_id] = _serialize_priority(
                    str(value), reverse_priority_mapping
                )

        elif bpkm_prop == "dueDate":
            value = _get_prop("dueDate")
            if value:
                result[col_id] = _serialize_date(str(value))

        elif bpkm_prop == "assignedTo":
            value = _get_prop("assignedTo")
            if value is not None:
                try:
                    result[col_id] = _serialize_people(value)
                except (ValueError, TypeError):
                    pass

        elif bpkm_prop == "description":
            value = _get_prop("description")
            if value:
                result[col_id] = _serialize_text(str(value))

        elif bpkm_prop == "taskGroup":
            value = _get_prop("taskGroup")
            if value:
                result[col_id] = _serialize_text(str(value))

        elif bpkm_prop == "estimatedEffort":
            value = _get_prop("estimatedEffort")
            if value is not None:
                result[col_id] = _serialize_numbers(str(value))

        elif bpkm_prop == "title":
            # Title is set via item name, not column — skip
            pass

    return result
