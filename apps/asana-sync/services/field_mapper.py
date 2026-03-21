"""Pure field mapping between Asana task data and bpkm:Task properties.

All functions are side-effect-free: no network, no logging, no state.
Property keys use full IRIs for bpkm properties because the ``bpkm:``
prefix is not in the platform's COMMON_PREFIXES.

Status extraction supports three configurable modes via ``field_config``:

- ``completed_only`` — maps ``task["completed"]`` boolean to done/todo
- ``custom_field`` — reads a custom enum field by GID
- ``section`` — maps the task's section name to a status

Priority and story points are extracted from custom fields by GID, with
the mapping defined in ``field_config``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

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

# Boolean completed → bpkm:taskStatus
COMPLETED_STATUS_MAP: dict[bool, str] = {
    True: "done",
    False: "todo",
}


# ---------------------------------------------------------------------------
# HTML / body helpers
# ---------------------------------------------------------------------------


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text, returning stripped plain text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def extract_body(task: dict) -> str | None:
    """Extract body content from an Asana task.

    Checks ``html_notes`` first (converts HTML → Markdown via
    markdownify if available, otherwise strips tags), then falls back
    to ``notes`` (plain text passthrough).

    Returns None if the body is empty or absent.
    """
    html_notes = task.get("html_notes")
    if html_notes and html_notes.strip():
        if md is not None:
            result = md(html_notes).strip()
            return result if result else None
        stripped = strip_html_tags(html_notes)
        return stripped if stripped else None

    notes = task.get("notes")
    if notes and notes.strip():
        return notes.strip()

    return None


# ---------------------------------------------------------------------------
# Status extraction — three configurable modes
# ---------------------------------------------------------------------------


def _status_from_completed(task: dict) -> str:
    """Fall back to completed boolean → done/todo."""
    return COMPLETED_STATUS_MAP.get(task.get("completed", False), "todo")


def extract_status(task: dict, field_config: dict, section_name: str | None = None) -> str:
    """Extract bpkm:taskStatus from an Asana task.

    Reads ``field_config["status_source"]`` to decide the extraction
    mode:

    - ``"completed_only"``: map ``task["completed"]`` via
      COMPLETED_STATUS_MAP.
    - ``"custom_field"``: find the custom field whose ``gid`` equals
      ``field_config["status_field_gid"]``, look up its
      ``enum_value.name`` in ``field_config["status_mapping"]``.
      Falls back to completed boolean on mismatch.
    - ``"section"``: look up *section_name* in
      ``field_config["status_mapping"]``.
      Falls back to completed boolean if not found.
    - Missing / unknown ``status_source``: falls back to completed
      boolean.
    """
    source = field_config.get("status_source")

    if source == "completed_only":
        return _status_from_completed(task)

    if source == "custom_field":
        target_gid = field_config.get("status_field_gid")
        mapping = field_config.get("status_mapping", {})
        if target_gid:
            for cf in task.get("custom_fields", []):
                if cf.get("gid") == target_gid:
                    enum_val = cf.get("enum_value")
                    if enum_val is not None:
                        name = enum_val.get("name", "")
                        mapped = mapping.get(name)
                        if mapped is not None:
                            return mapped
                    # enum_value is None or name not in mapping
                    break
        # fall back
        return _status_from_completed(task)

    if source == "section":
        mapping = field_config.get("status_mapping", {})
        if section_name and section_name in mapping:
            return mapping[section_name]
        return _status_from_completed(task)

    # Default / missing status_source
    return _status_from_completed(task)


# ---------------------------------------------------------------------------
# Priority extraction from custom field
# ---------------------------------------------------------------------------


def extract_priority(task: dict, field_config: dict) -> str | None:
    """Extract bpkm:priority from an Asana custom enum field.

    Looks for a custom field matching
    ``field_config["priority_field_gid"]`` by GID, then maps
    ``enum_value.name`` via ``field_config["priority_mapping"]``.

    Returns None if no priority field is configured, no match is found,
    or the enum value is not in the mapping.
    """
    target_gid = field_config.get("priority_field_gid")
    if not target_gid:
        return None

    mapping = field_config.get("priority_mapping", {})
    for cf in task.get("custom_fields", []):
        if cf.get("gid") == target_gid:
            enum_val = cf.get("enum_value")
            if enum_val is not None:
                name = enum_val.get("name", "")
                return mapping.get(name)
            return None

    return None


# ---------------------------------------------------------------------------
# Story points extraction from custom number field
# ---------------------------------------------------------------------------


def extract_story_points(task: dict, field_config: dict) -> float | None:
    """Extract story points from an Asana custom number field.

    Looks for a custom field matching
    ``field_config["story_points_field_gid"]`` by GID, then returns
    its ``number_value``.

    Returns None if no story points field is configured or no match.
    """
    target_gid = field_config.get("story_points_field_gid")
    if not target_gid:
        return None

    for cf in task.get("custom_fields", []):
        if cf.get("gid") == target_gid:
            return cf.get("number_value")

    return None


# ---------------------------------------------------------------------------
# Simple field extractors
# ---------------------------------------------------------------------------


def extract_tags(task: dict) -> str | None:
    """Extract tags as a comma-separated string.

    Reads ``task["tags"]`` list, returns comma-separated ``tag["name"]``
    values. Returns None if empty or missing.
    """
    tags = task.get("tags")
    if not tags:
        return None
    names = [t["name"] for t in tags if t.get("name")]
    return ",".join(names) if names else None


def extract_followers(task: dict) -> list[dict[str, str]]:
    """Extract followers as a list of ``{email, name}`` dicts.

    Returns an empty list if no followers are present.
    """
    followers = task.get("followers")
    if not followers:
        return []
    return [
        {"email": f.get("email", ""), "name": f.get("name", "")}
        for f in followers
        if f.get("email")
    ]


def extract_assignee(task: dict) -> dict[str, str] | None:
    """Extract assignee as an ``{email, name}`` dict.

    Returns None if the task has no assignee or the assignee has no
    email.
    """
    assignee = task.get("assignee")
    if not assignee or not assignee.get("email"):
        return None
    return {"email": assignee["email"], "name": assignee.get("name", "")}


def extract_section_name(task: dict) -> str | None:
    """Extract the section name from the first membership.

    Reads ``task["memberships"][0]["section"]["name"]``.
    Returns None if not available.
    """
    memberships = task.get("memberships")
    if not memberships:
        return None
    first = memberships[0] if memberships else None
    if not first:
        return None
    section = first.get("section")
    if not section:
        return None
    return section.get("name")


def detect_milestone(task: dict) -> bool:
    """Return True if the task is an Asana milestone.

    Milestones have ``resource_subtype`` set to ``"milestone"``.
    """
    return task.get("resource_subtype") == "milestone"


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def extract_due_date(task: dict) -> str | None:
    """Extract due date from ``due_on`` or truncate ``due_at`` to date.

    Returns an ISO date string (YYYY-MM-DD) or None.
    """
    due_on = task.get("due_on")
    if due_on:
        return due_on[:10]
    due_at = task.get("due_at")
    if due_at:
        return due_at[:10]
    return None


def extract_start_date(task: dict) -> str | None:
    """Extract start date from ``start_on`` or truncate ``start_at``.

    Returns an ISO date string (YYYY-MM-DD) or None.
    """
    start_on = task.get("start_on")
    if start_on:
        return start_on[:10]
    start_at = task.get("start_at")
    if start_at:
        return start_at[:10]
    return None


# ---------------------------------------------------------------------------
# Slug computation
# ---------------------------------------------------------------------------


def compute_task_slug(task: dict) -> str:
    """Compute a deterministic slug from the task GID.

    Returns ``asana-{gid}`` as a stable identifier.
    """
    return f"asana-{task['gid']}"


# ---------------------------------------------------------------------------
# Main property builder
# ---------------------------------------------------------------------------


def build_task_properties(
    task: dict,
    field_config: dict,
    section_name: str | None = None,
    *,
    sync_time: str | None = None,
) -> tuple[str, dict]:
    """Build a properties dict for ``object.create`` / ``object.patch``.

    Parameters
    ----------
    task:
        An Asana task dict as returned by ``AsanaClient.get_tasks()``
        with the full opt_fields expansion.
    field_config:
        Configuration dict from StateClient containing status_source,
        status_field_gid, status_mapping, priority_field_gid,
        priority_mapping, story_points_field_gid, etc.
    section_name:
        The section name for section-based status mapping. Typically
        from ``extract_section_name(task)`` or from the sync engine's
        section lookup.
    sync_time:
        ISO-8601 UTC timestamp for ``lastSyncedAt``.  If ``None``,
        the current UTC time is used.

    Returns
    -------
    tuple[str, dict]
        ``(type_iri, properties)`` where type_iri is either
        ``bpkm:Milestone`` or ``bpkm:Task``, and properties is a
        dict of full-IRI bpkm keys → values with None/empty values
        omitted.
    """
    if sync_time is None:
        sync_time = datetime.now(timezone.utc).isoformat()

    # Determine type
    is_milestone = detect_milestone(task)
    type_iri = f"{BPKM}Milestone" if is_milestone else f"{BPKM}Task"

    # Extract body
    body = extract_body(task)

    # Build properties — all extractions
    props: dict[str, str | float | None] = {
        "dcterms:title": task.get("name"),
        f"{BPKM}taskStatus": extract_status(task, field_config, section_name),
        f"{BPKM}priority": extract_priority(task, field_config),
        f"{BPKM}dueDate": extract_due_date(task),
        f"{BPKM}startDate": extract_start_date(task),
        f"{BPKM}tags": extract_tags(task),
        f"{BPKM}storyPoints": extract_story_points(task, field_config),
        f"{BPKM}externalUrl": task.get("permalink_url"),
        f"{BPKM}externalId": task.get("gid"),
        f"{BPKM}externalUuid": task.get("gid"),
        f"{BPKM}externalProvider": "asana",
        f"{BPKM}lastSyncedAt": sync_time,
    }

    # Add body if present
    if body:
        props["dcterms:description"] = body

    # Strip None and empty-string values
    clean_props = {
        k: v
        for k, v in props.items()
        if v is not None and v != ""
    }

    return type_iri, clean_props


# ---------------------------------------------------------------------------
# Reverse mapping — bpkm properties → Asana API format (for push sync)
# ---------------------------------------------------------------------------


def _invert_mapping(mapping: dict[str, str]) -> dict[str, str]:
    """Invert a {source: target} mapping to {target: source}.

    If multiple source keys map to the same target, the last one wins.
    """
    return {v: k for k, v in mapping.items()}


def reverse_status_mapping(
    bpkm_status: str, field_config: dict
) -> dict[str, str | bool] | None:
    """Convert a bpkm status back to an Asana-side representation.

    Returns a dict describing the Asana target:

    - ``{"type": "custom_field", "enum_option_name": "..."}``
      when ``status_source`` is ``"custom_field"``
    - ``{"type": "section", "section_name": "..."}``
      when ``status_source`` is ``"section"``
    - ``{"type": "completed", "value": True/False}``
      when ``status_source`` is ``"completed_only"``

    Returns None if the bpkm status cannot be reverse-mapped.
    """
    source = field_config.get("status_source")

    if source == "completed_only":
        return {"type": "completed", "value": bpkm_status == "done"}

    if source == "custom_field":
        mapping = field_config.get("status_mapping", {})
        inverted = _invert_mapping(mapping)
        enum_name = inverted.get(bpkm_status)
        if enum_name is None:
            return None
        return {"type": "custom_field", "enum_option_name": enum_name}

    if source == "section":
        mapping = field_config.get("status_mapping", {})
        inverted = _invert_mapping(mapping)
        section_name = inverted.get(bpkm_status)
        if section_name is None:
            return None
        return {"type": "section", "section_name": section_name}

    return None


def reverse_priority_mapping(
    bpkm_priority: str, field_config: dict
) -> str | None:
    """Convert a bpkm priority back to an Asana enum option name.

    Inverts ``field_config["priority_mapping"]``
    (``{AsanaEnumName: bpkmPriority}``) and looks up the given
    bpkm_priority. Returns the Asana enum option name or None.
    """
    mapping = field_config.get("priority_mapping", {})
    inverted = _invert_mapping(mapping)
    return inverted.get(bpkm_priority)


def _resolve_enum_option_gid(
    field_gid: str,
    option_name: str,
    discovered_enum_fields: list[dict],
) -> str | None:
    """Find the GID of an enum option within discovered custom fields.

    Scans ``discovered_enum_fields`` for a field matching *field_gid*,
    then scans its ``enum_options`` for an entry matching *option_name*.
    Returns the option's GID or None.
    """
    for field in discovered_enum_fields:
        if field.get("gid") == field_gid:
            for option in field.get("enum_options", []):
                if option.get("name") == option_name:
                    return option.get("gid")
            return None  # field found but option not found
    return None  # field not found


def build_asana_patch(
    bpkm_properties: dict,
    field_config: dict,
    discovered_enum_fields: list[dict],
) -> dict:
    """Assemble an Asana PATCH body from changed bpkm properties.

    Handles:

    - **Title** → ``{"name": "..."}``
    - **Status (custom_field mode)** → ``{"custom_fields": {gid: option_gid}}``
    - **Status (completed_only mode)** → ``{"completed": True/False}``
    - **Priority** → ``{"custom_fields": {gid: option_gid}}``

    Status in section mode is handled separately via section moves
    (not included in the PATCH body).

    Returns a dict suitable for ``AsanaClient.update_task()``.
    May be empty if no pushable changes are present.
    """
    patch: dict = {}
    custom_fields: dict[str, str] = {}

    # Title
    title = bpkm_properties.get("dcterms:title")
    if title is not None:
        patch["name"] = title

    # Status — depends on status_source
    status = bpkm_properties.get(f"{BPKM}taskStatus")
    if status is not None:
        rev = reverse_status_mapping(status, field_config)
        if rev is not None:
            if rev["type"] == "custom_field":
                status_gid = field_config.get("status_field_gid")
                if status_gid:
                    option_gid = _resolve_enum_option_gid(
                        status_gid, rev["enum_option_name"], discovered_enum_fields
                    )
                    if option_gid:
                        custom_fields[status_gid] = option_gid
            elif rev["type"] == "completed":
                patch["completed"] = rev["value"]
            # section type is handled separately — not in PATCH body

    # Priority
    priority = bpkm_properties.get(f"{BPKM}priority")
    if priority is not None:
        priority_name = reverse_priority_mapping(priority, field_config)
        if priority_name is not None:
            priority_gid = field_config.get("priority_field_gid")
            if priority_gid:
                option_gid = _resolve_enum_option_gid(
                    priority_gid, priority_name, discovered_enum_fields
                )
                if option_gid:
                    custom_fields[priority_gid] = option_gid

    if custom_fields:
        patch["custom_fields"] = custom_fields

    return patch


def resolve_section_gid_for_status(
    bpkm_status: str,
    field_config: dict,
    discovered_sections: list[dict],
) -> str | None:
    """Resolve a bpkm status to an Asana section GID.

    Inverts ``field_config["status_mapping"]`` (``{SectionName: bpkmStatus}``)
    to find the section name, then scans ``discovered_sections`` for the
    matching name → GID.

    Returns the section GID string or None if no mapping is found.
    """
    mapping = field_config.get("status_mapping", {})
    inverted = _invert_mapping(mapping)
    section_name = inverted.get(bpkm_status)
    if section_name is None:
        return None

    for section in discovered_sections:
        if section.get("name") == section_name:
            return section.get("gid")

    return None
