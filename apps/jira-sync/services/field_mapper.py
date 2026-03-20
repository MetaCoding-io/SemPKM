"""Pure field mapping between Jira Cloud issue data and bpkm:Task properties.

All functions are side-effect-free: no network, no logging, no state.
Property keys use full IRIs for bpkm properties because the ``bpkm:``
prefix is not in the platform's COMMON_PREFIXES.

Key design decisions:
- D233/D235: Always normalise via ``statusCategory.key`` (new / indeterminate /
  done) — never ``status.name``.  The actual status name is stored in
  ``bpkm:externalStatus`` for display purposes.
- D237: Push sync is limited to title/description/priority for v1.
  No status transitions — they require Jira transition IDs.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Full IRI prefix for basic-pkm model properties
BPKM = "urn:sempkm:model:basic-pkm:"

# Jira statusCategory.key → bpkm:taskStatus
# These three keys are the only values Jira ever returns for statusCategory.key.
STATUS_MAP: dict[str, str] = {
    "new": "todo",
    "indeterminate": "in-progress",
    "done": "done",
}

# Jira priority.name → bpkm:priority
# Covers all built-in Jira priority names plus common aliases.
PRIORITY_MAP: dict[str, str] = {
    "Highest": "critical",
    "Critical": "critical",
    "Blocker": "critical",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Lowest": "low",
    "Trivial": "low",
}

# bpkm:taskStatus → Jira statusCategory.key (reverse)
# Multiple bpkm statuses can map to the same category.
REVERSE_STATUS_MAP: dict[str, str] = {
    "todo": "new",
    "in-progress": "indeterminate",
    "done": "done",
    "blocked": "indeterminate",
    "cancelled": "done",
}

# bpkm:priority → Jira priority.name (reverse)
# Each bpkm priority maps to a single canonical Jira name.
REVERSE_PRIORITY_MAP: dict[str, str] = {
    "critical": "Highest",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


def normalize_status(status_category_key: str) -> str:
    """Map a Jira ``statusCategory.key`` to a bpkm taskStatus value.

    Unknown keys default to ``"todo"``.
    """
    return STATUS_MAP.get(status_category_key, "todo")


def normalize_priority(priority_name: str | None) -> str | None:
    """Map a Jira priority name to a bpkm priority string.

    Returns ``None`` for ``None`` or unknown priority names.
    Callers should omit the property entirely when the return is None.
    """
    if priority_name is None:
        return None
    return PRIORITY_MAP.get(priority_name)


# ---------------------------------------------------------------------------
# Reverse mapping helpers
# ---------------------------------------------------------------------------


def reverse_status(bpkm_status: str) -> str:
    """Map a bpkm taskStatus to a Jira ``statusCategory.key``.

    Unknown statuses default to ``"new"``.
    """
    return REVERSE_STATUS_MAP.get(bpkm_status, "new")


def reverse_priority(bpkm_priority: str) -> str | None:
    """Map a bpkm priority string to a Jira priority name.

    Returns ``None`` for unknown priority values.
    """
    return REVERSE_PRIORITY_MAP.get(bpkm_priority)


# ---------------------------------------------------------------------------
# IRI slug
# ---------------------------------------------------------------------------


def compute_issue_slug(project_key: str, issue_key: str) -> str:
    """Compute a deterministic slug for a Jira issue.

    The slug is used as the local part of a platform-minted Task IRI:
    ``{base_namespace}/Task/jira-{hash16}``.

    Args:
        project_key: Jira project key (e.g. ``"PROJ"``).
        issue_key: Jira issue key (e.g. ``"PROJ-123"``).

    Returns:
        Slug string in the format ``jira-{16 hex chars}``.
    """
    composite = f"{project_key}#{issue_key}"
    digest = hashlib.sha256(composite.encode()).hexdigest()[:16]
    return f"jira-{digest}"


# ---------------------------------------------------------------------------
# Tag extraction helpers
# ---------------------------------------------------------------------------


def _extract_tags(issue: dict) -> list[str]:
    """Extract tags from labels and components.

    Labels come as a list of label dicts with ``"name"`` keys.
    Components come as a list of component dicts with ``"name"`` keys.
    Both are merged into a single tags list (labels first, then components).
    """
    tags: list[str] = []

    # Labels — list of dicts with "name" key, or list of strings
    labels = issue.get("labels") or []
    for lbl in labels:
        if isinstance(lbl, dict) and "name" in lbl:
            tags.append(lbl["name"])
        elif isinstance(lbl, str):
            tags.append(lbl)

    # Components — list of dicts with "name" key
    components = issue.get("components") or []
    for comp in components:
        if isinstance(comp, dict) and "name" in comp:
            tags.append(comp["name"])

    return tags


# ---------------------------------------------------------------------------
# Property builder — Jira → bpkm (pull)
# ---------------------------------------------------------------------------


def build_task_properties(
    issue: dict,
    person_iri: str | None = None,
    sync_time: str | None = None,
) -> dict:
    """Build a bpkm properties dict from a Jira issue.

    Parameters
    ----------
    issue:
        A Jira issue dict from the REST API (``/rest/api/3/search`` shape).
        Expected to have ``fields`` sub-dict, or flat field access.
        The function reads from ``issue["fields"]`` if present, otherwise
        treats the dict itself as the fields dict.
    person_iri:
        Optional SemPKM Person IRI for the assignee.
    sync_time:
        ISO-8601 UTC timestamp for ``bpkm:lastSyncedAt``.  When ``None``,
        the current UTC time is used.

    Returns
    -------
    dict
        Property mapping where keys are full IRIs (except ``dcterms:title``
        which uses the compact form recognised by the platform). Keys with
        ``None``, empty-string, or empty-list values are omitted — except
        ``lastSyncedAt`` which is always present.
    """
    if sync_time is None:
        sync_time = datetime.now(timezone.utc).isoformat()

    # Support both nested {"fields": {...}} and flat dict shapes
    fields = issue.get("fields", issue)

    # Status — always via statusCategory.key per D233/D235
    status_obj = fields.get("status") or {}
    status_cat = status_obj.get("statusCategory") or {}
    status_category_key = status_cat.get("key", "")
    status_name = status_obj.get("name")

    # Priority
    priority_obj = fields.get("priority") or {}
    priority_name = priority_obj.get("name")

    # Due date — truncate to date-only
    raw_due = fields.get("duedate")
    due_date = raw_due[:10] if raw_due else None

    # Completed date — only when resolved
    raw_resolution = fields.get("resolutiondate")
    completed_date: str | None = None
    if raw_resolution:
        completed_date = raw_resolution[:10]

    # Tags from labels + components
    tags = _extract_tags(fields)

    # Sprint
    sprint = fields.get("sprint") or {}
    sprint_name = sprint.get("name") if isinstance(sprint, dict) else None

    # External ID — the issue key (e.g. "PROJ-123")
    issue_key = issue.get("key") or fields.get("key", "")

    # External URL — constructed from the site in the issue's self link
    external_url = _build_external_url(issue, issue_key)

    # External UUID — the Jira issue ID
    issue_id = str(issue.get("id", ""))

    # Assemble properties
    props: dict[str, str | list[str] | None] = {
        "dcterms:title": fields.get("summary", ""),
        f"{BPKM}taskStatus": normalize_status(status_category_key),
        f"{BPKM}externalStatus": status_name,
        f"{BPKM}priority": normalize_priority(priority_name),
        f"{BPKM}dueDate": due_date,
        f"{BPKM}completedDate": completed_date,
        f"{BPKM}assignedTo": person_iri,
        f"{BPKM}tags": tags,
        f"{BPKM}taskGroup": sprint_name,
        f"{BPKM}externalId": issue_key,
        f"{BPKM}externalUrl": external_url,
        f"{BPKM}externalUuid": issue_id,
        f"{BPKM}externalProvider": "jira",
    }

    # Strip None, empty string, and empty list values
    cleaned = {
        k: v
        for k, v in props.items()
        if v is not None and v != "" and v != []
    }

    # lastSyncedAt is always present (never stripped)
    cleaned[f"{BPKM}lastSyncedAt"] = sync_time

    return cleaned


def _build_external_url(issue: dict, issue_key: str) -> str:
    """Construct the browse URL for a Jira issue.

    Extracts the site hostname from the issue's ``self`` URL
    (e.g. ``https://mysite.atlassian.net/rest/api/3/issue/10001``).
    Falls back to empty string if ``self`` is not present.
    """
    self_url = issue.get("self", "")
    if self_url and issue_key:
        # Extract scheme + host from the self URL
        # e.g. "https://mysite.atlassian.net/rest/api/3/issue/10001"
        # → "https://mysite.atlassian.net"
        try:
            from urllib.parse import urlparse

            parsed = urlparse(self_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            return f"{base}/browse/{issue_key}"
        except Exception:
            pass
    return ""


# ---------------------------------------------------------------------------
# Property builder — Jira Epic → bpkm:Milestone (pull)
# ---------------------------------------------------------------------------


def build_milestone_properties(
    epic: dict,
    sync_time: str | None = None,
) -> dict:
    """Build a bpkm Milestone properties dict from a Jira epic.

    Parameters
    ----------
    epic:
        A Jira issue dict for an Epic.
    sync_time:
        ISO-8601 UTC timestamp for ``bpkm:lastSyncedAt``.  When ``None``,
        the current UTC time is used.

    Returns
    -------
    dict
        Property mapping for a Milestone object.
    """
    if sync_time is None:
        sync_time = datetime.now(timezone.utc).isoformat()

    fields = epic.get("fields", epic)

    # Status category for milestone status
    status_obj = fields.get("status") or {}
    status_cat = status_obj.get("statusCategory") or {}
    status_category_key = status_cat.get("key", "")

    milestone_status = "completed" if status_category_key == "done" else "active"

    # Due date → target date
    raw_due = fields.get("duedate")
    target_date = raw_due[:10] if raw_due else None

    # External ID
    epic_key = epic.get("key") or fields.get("key", "")

    # External URL
    external_url = _build_external_url(epic, epic_key)

    props: dict[str, str | None] = {
        "dcterms:title": fields.get("summary", ""),
        f"{BPKM}milestoneStatus": milestone_status,
        f"{BPKM}targetDate": target_date,
        f"{BPKM}externalId": epic_key,
        f"{BPKM}externalUrl": external_url,
        f"{BPKM}externalProvider": "jira",
    }

    # Strip None, empty string values
    cleaned = {
        k: v
        for k, v in props.items()
        if v is not None and v != ""
    }

    # lastSyncedAt always present
    cleaned[f"{BPKM}lastSyncedAt"] = sync_time

    return cleaned


# ---------------------------------------------------------------------------
# Reverse mapping — bpkm → Jira (push)
# ---------------------------------------------------------------------------


def build_issue_patch(
    task_props: dict,
    description_adf: dict | None = None,
) -> dict:
    """Build a Jira issue update body from bpkm task properties.

    Per D237: v1 push sync is limited to title, description, and priority.
    No status transitions — those require Jira transition IDs which
    vary per project workflow.

    Parameters
    ----------
    task_props:
        Property dict with full IRI keys or compact form keys.
    description_adf:
        Optional ADF document dict (from ``markdown_to_adf()``).
        When provided and non-empty, included as the ``description``
        field in the Jira update payload.

    Returns
    -------
    dict
        Jira-compatible fields dict. Only fields with non-None values
        are included. Empty dict means no pushable changes detected.
    """
    result: dict = {}

    # Title → summary
    title = task_props.get("dcterms:title")
    if title:
        result["summary"] = title

    # Priority → priority.name via reverse map
    bpkm_prio = task_props.get(f"{BPKM}priority")
    if bpkm_prio:
        jira_prio = reverse_priority(bpkm_prio)
        if jira_prio is not None:
            result["priority"] = {"name": jira_prio}

    # Description → ADF document (v3 API format)
    if description_adf:
        result["description"] = description_adf

    # Per D237: NO status mapping in v1 push (no transition IDs)

    return result
