"""Pure field mapping between Todoist task data and bpkm:Task properties.

All functions are side-effect-free: no network, no logging, no state.
Property keys use full IRIs for bpkm properties because the ``bpkm:``
prefix is not in the platform's COMMON_PREFIXES.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone as tz

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Full IRI prefix for basic-pkm model properties
BPKM = "urn:sempkm:model:basic-pkm:"

# ---------------------------------------------------------------------------
# Priority mapping — Todoist inverts typical convention
#
# Todoist 1 = normal (lowest) → bpkm "low"
# Todoist 2 = medium           → bpkm "medium"
# Todoist 3 = high             → bpkm "high"
# Todoist 4 = urgent (highest) → bpkm "critical"
# ---------------------------------------------------------------------------

TODOIST_TO_BPKM_PRIORITY: dict[int, str] = {
    1: "low",
    2: "medium",
    3: "high",
    4: "critical",
}

BPKM_TO_TODOIST_PRIORITY: dict[str, int] = {
    v: k for k, v in TODOIST_TO_BPKM_PRIORITY.items()
}

# ---------------------------------------------------------------------------
# Status mapping — is_completed ↔ taskStatus
# ---------------------------------------------------------------------------

TODOIST_TO_BPKM_STATUS: dict[bool, str] = {
    False: "todo",
    True: "done",
}

BPKM_TO_TODOIST_STATUS: dict[str, bool] = {
    "todo": False,
    "in-progress": False,
    "done": True,
    "cancelled": True,
    "blocked": False,
}


# ---------------------------------------------------------------------------
# IRI slug
# ---------------------------------------------------------------------------


def compute_task_slug(task_id: str) -> str:
    """Compute a deterministic slug for a Todoist task.

    The slug is used as the local part of a platform-minted Task IRI:
    ``{base_namespace}/Task/td-{hash16}``.

    Args:
        task_id: Todoist task ID string.

    Returns:
        Slug string in the format ``td-{16 hex chars}``.
    """
    digest = hashlib.sha256(task_id.encode()).hexdigest()[:16]
    return f"td-{digest}"


# ---------------------------------------------------------------------------
# Due date extraction
# ---------------------------------------------------------------------------


def extract_due_date(due: dict | None) -> str | None:
    """Extract a YYYY-MM-DD date string from a Todoist due object.

    Handles three cases:
    1. ``due`` is None → returns None
    2. ``due.date`` is a date string (YYYY-MM-DD) → returns it directly
    3. ``due.datetime`` is present (YYYY-MM-DDTHH:MM:SS) → extracts date part

    The ``due.date`` field is always present when ``due`` exists (Todoist
    guarantees this), and is already in YYYY-MM-DD format. The ``datetime``
    field, when present, includes time — we only take the date portion.

    Args:
        due: Todoist due object or None.

    Returns:
        Date string in YYYY-MM-DD format, or None if no due date.
    """
    if due is None:
        return None

    # Prefer due.date — it's always present and already YYYY-MM-DD
    date_str = due.get("date")
    if date_str:
        # Ensure we only return the date portion (first 10 chars)
        return date_str[:10]

    # Fallback: extract date from datetime field
    dt_str = due.get("datetime")
    if dt_str:
        return dt_str[:10]

    return None


# ---------------------------------------------------------------------------
# Label handling
# ---------------------------------------------------------------------------


def map_labels(label_ids: list[str], labels_lookup: dict[str, str]) -> list[str]:
    """Map Todoist label names to bpkm tags.

    Todoist REST v2 returns label names directly in the ``labels`` array
    on task objects (not IDs). The labels_lookup is provided for cases
    where we need ID→name resolution, but typically labels are already
    strings.

    Args:
        label_ids: List of label names from the task.
        labels_lookup: Dict mapping label ID → label name (for reference).

    Returns:
        List of label name strings suitable for bpkm:tags.
    """
    # In REST v2, task.labels is already a list of name strings
    return list(label_ids)


# ---------------------------------------------------------------------------
# Property builder (Todoist → bpkm)
# ---------------------------------------------------------------------------


def build_task_properties(
    task: dict,
    labels_lookup: dict[str, str] | None = None,
    project_lookup: dict[str, str] | None = None,
    sync_time: str | None = None,
) -> dict:
    """Build a bpkm:Task properties dict from a Todoist task.

    Parameters
    ----------
    task:
        A Todoist task dict from the REST API.
    labels_lookup:
        Optional dict mapping label ID → label name. Not strictly needed
        for REST v2 (labels are already names) but kept for API compat.
    project_lookup:
        Optional dict mapping project ID → project name. Used to resolve
        ``project_id`` to a human-readable project name.
    sync_time:
        ISO-8601 timestamp for ``bpkm:lastSyncedAt``. When ``None``,
        the current UTC time is used.

    Returns
    -------
    dict
        Property mapping with full IRI keys. Keys with ``None``,
        empty-string, or empty-list values are omitted — except
        ``lastSyncedAt`` which is always present.
    """
    if sync_time is None:
        sync_time = datetime.now(tz.utc).isoformat()

    if labels_lookup is None:
        labels_lookup = {}
    if project_lookup is None:
        project_lookup = {}

    # Priority (default to 1 = low if missing)
    todoist_priority = task.get("priority", 1)
    bpkm_priority = TODOIST_TO_BPKM_PRIORITY.get(todoist_priority, "low")

    # Status
    is_completed = task.get("is_completed", False)
    bpkm_status = TODOIST_TO_BPKM_STATUS.get(is_completed, "todo")

    # Due date
    due_date = extract_due_date(task.get("due"))

    # Labels/tags — REST v2 returns names directly
    tags = map_labels(task.get("labels", []), labels_lookup)

    # Project name resolution
    project_id = task.get("project_id")
    project_name = project_lookup.get(project_id) if project_id else None

    # External URL and ID
    external_url = task.get("url", "")
    external_id = str(task.get("id", ""))

    props: dict[str, str | list[str] | None] = {
        "dcterms:title": task.get("content", ""),
        f"{BPKM}taskStatus": bpkm_status,
        f"{BPKM}priority": bpkm_priority,
        f"{BPKM}tags": tags,
        f"{BPKM}taskProject": project_name,
        f"{BPKM}dueDate": due_date,
        f"{BPKM}externalId": external_id,
        f"{BPKM}externalUrl": external_url,
        f"{BPKM}externalProvider": "todoist",
    }

    # Strip None, empty string, and empty list values
    cleaned = {
        k: v
        for k, v in props.items()
        if v is not None and v != "" and v != []
    }

    # lastSyncedAt is always present
    cleaned[f"{BPKM}lastSyncedAt"] = sync_time

    return cleaned


# ---------------------------------------------------------------------------
# Reverse mapping (bpkm → Todoist)
# ---------------------------------------------------------------------------


def build_todoist_task_data(task_props: dict) -> dict:
    """Build a Todoist task create/update body from bpkm properties.

    Maps bpkm properties back to Todoist REST API fields.

    Parameters
    ----------
    task_props:
        Property dict with full IRI keys.

    Returns
    -------
    dict
        Todoist task body. Only fields with values are included.
    """
    result: dict = {}

    # Content (title)
    title = task_props.get("dcterms:title")
    if title:
        result["content"] = title

    # Priority
    bpkm_priority = task_props.get(f"{BPKM}priority")
    if bpkm_priority:
        todoist_priority = BPKM_TO_TODOIST_PRIORITY.get(bpkm_priority)
        if todoist_priority is not None:
            result["priority"] = todoist_priority

    # Labels from tags
    tags = task_props.get(f"{BPKM}tags")
    if tags and isinstance(tags, list):
        result["labels"] = tags

    # Due date
    due_date = task_props.get(f"{BPKM}dueDate")
    if due_date:
        result["due_date"] = due_date

    return result
