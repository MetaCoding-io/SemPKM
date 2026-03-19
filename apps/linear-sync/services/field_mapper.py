"""Pure field mapping between Linear issue data and bpkm:Task properties.

All functions are side-effect-free: no network, no logging, no state.
Property keys use full IRIs for bpkm properties because the ``bpkm:``
prefix is not in the platform's COMMON_PREFIXES.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Full IRI prefix for basic-pkm model properties
BPKM = "urn:sempkm:model:basic-pkm:"

# Linear state.type → bpkm:taskStatus
STATUS_MAP: dict[str, str] = {
    "backlog": "todo",
    "unstarted": "todo",
    "started": "in-progress",
    "completed": "done",
    "cancelled": "cancelled",
}

# Linear priority int (0-4) → bpkm:priority string
# 0 = No priority (omit)
PRIORITY_MAP: dict[int, str] = {
    1: "critical",
    2: "high",
    3: "medium",
    4: "low",
}

# bpkm taskStatus → Linear state.type (reverse of STATUS_MAP)
# Multiple Linear state.types map to "todo" — we pick "backlog" as the default
# reverse for "todo" since it's the most common unstarted state.
REVERSE_STATUS_MAP: dict[str, str] = {
    "todo": "backlog",
    "in-progress": "started",
    "done": "completed",
    "blocked": "unstarted",
    "cancelled": "cancelled",
}

# bpkm priority string → Linear priority int (reverse of PRIORITY_MAP)
REVERSE_PRIORITY_MAP: dict[str, int] = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
}


# Linear estimate int → bpkm:effort string (lossy)
EFFORT_MAP: dict[int, str | None] = {
    0: None,
    1: "trivial",
    2: "small",
    3: "medium",
    5: "large",
    8: "epic",
}


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


def normalize_status(state_type: str) -> str:
    """Map a Linear ``state.type`` to a bpkm taskStatus value.

    Unknown state types default to ``"todo"``.
    """
    return STATUS_MAP.get(state_type, "todo")


def normalize_priority(priority: int) -> str | None:
    """Map a Linear priority integer (0-4) to a bpkm priority string.

    Returns ``None`` for priority 0 (no priority) or unknown values.
    Callers should omit the property entirely when the return is None.
    """
    return PRIORITY_MAP.get(priority)


def map_labels_to_tags(labels: list[dict] | None) -> list[str]:
    """Extract tag names from a list of Linear label dicts.

    Each dict is expected to have a ``"name"`` key.  Returns an empty
    list for ``None`` or empty input.
    """
    if not labels:
        return []
    return [lbl["name"] for lbl in labels if "name" in lbl]


# ---------------------------------------------------------------------------
# Reverse mapping (bpkm → Linear)
# ---------------------------------------------------------------------------


def reverse_status(bpkm_status: str) -> str:
    """Map a bpkm taskStatus to a Linear ``state.type`` string.

    Unknown statuses default to ``"backlog"``.
    """
    return REVERSE_STATUS_MAP.get(bpkm_status, "backlog")


def reverse_priority(bpkm_priority: str) -> int | None:
    """Map a bpkm priority string to a Linear priority integer (1-4).

    Returns ``None`` for unknown priority values.  Callers should omit
    the priority field from the mutation input when the return is None.
    """
    return REVERSE_PRIORITY_MAP.get(bpkm_priority)


def build_issue_update_input(
    task_properties: dict,
    workflow_states: dict[tuple[str, str], str],
    team_id: str | None = None,
) -> dict:
    """Build a dict of ``IssueUpdateInput`` fields from bpkm task properties.

    Parameters
    ----------
    task_properties:
        Property dict with full IRI keys (e.g. ``urn:sempkm:model:basic-pkm:taskStatus``).
    workflow_states:
        Lookup dict mapping ``(team_id, state_type)`` → ``state_id`` UUID.
        Built from ``LinearClient.get_workflow_states()`` output.
    team_id:
        The Linear team ID — needed to look up the state UUID in
        ``workflow_states``.  If ``None``, stateId is skipped.

    Returns
    -------
    dict
        Only fields with non-None values are included.  Empty dict means
        no pushable changes detected.
    """
    result: dict = {}

    # Title
    title = task_properties.get("dcterms:title")
    if title:
        result["title"] = title

    # Status → stateId (requires workflow_states lookup)
    bpkm_status = task_properties.get(f"{BPKM}taskStatus")
    if bpkm_status and team_id:
        linear_state_type = reverse_status(bpkm_status)
        state_id = workflow_states.get((team_id, linear_state_type))
        if state_id:
            result["stateId"] = state_id

    # Priority
    bpkm_prio = task_properties.get(f"{BPKM}priority")
    if bpkm_prio:
        linear_prio = reverse_priority(bpkm_prio)
        if linear_prio is not None:
            result["priority"] = linear_prio

    # Due date — pass through as-is
    due_date = task_properties.get(f"{BPKM}dueDate")
    if due_date:
        result["dueDate"] = due_date

    return result


# ---------------------------------------------------------------------------
# IRI slug
# ---------------------------------------------------------------------------


def compute_issue_slug(workspace_id: str, issue_id: str) -> str:
    """Compute a deterministic slug for a Linear issue.

    The slug is used as the local part of a platform-minted Task IRI:
    ``{base_namespace}/Task/issue-{hash16}``.
    """
    digest = hashlib.sha256((workspace_id + issue_id).encode()).hexdigest()[:16]
    return f"issue-{digest}"


# ---------------------------------------------------------------------------
# Property builder
# ---------------------------------------------------------------------------


def build_task_properties(
    issue: dict,
    workspace_id: str,
    *,
    sync_time: str | None = None,
) -> dict:
    """Build a properties dict for ``object.create`` / ``object.patch``.

    Parameters
    ----------
    issue:
        A Linear issue dict matching the GraphQL shape returned by
        ``build_issue_query``.
    workspace_id:
        The Linear workspace / organisation ID — used for slug computation.
    sync_time:
        ISO-8601 UTC timestamp for ``lastSyncedAt``.  If ``None``,
        the current UTC time is used.

    Returns
    -------
    dict
        Property mapping where keys are full IRIs (except ``dcterms:title``
        which uses the compact form recognised by the platform).  Keys with
        ``None``, empty-string, or empty-list values are omitted.
    """
    if sync_time is None:
        sync_time = datetime.now(timezone.utc).isoformat()

    state_type = issue.get("state", {}).get("type", "")
    priority_val = normalize_priority(issue.get("priority", 0))

    # Due date — truncate to date-only if it contains a time component
    raw_due = issue.get("dueDate")
    due_date = raw_due[:10] if raw_due else None

    # Completed date — only set when the issue is actually completed
    raw_completed = issue.get("completedAt")
    completed_date: str | None = None
    if raw_completed and state_type == "completed":
        completed_date = raw_completed[:10]

    # Tags from labels
    label_nodes = issue.get("labels", {}).get("nodes", []) if issue.get("labels") else []
    tags = map_labels_to_tags(label_nodes)

    # Effort — known estimates map to named strings, unknown non-zero
    # estimates are stringified as-is
    raw_estimate = issue.get("estimate")
    effort: str | None = None
    if raw_estimate is not None and raw_estimate != 0:
        mapped = EFFORT_MAP.get(raw_estimate)
        if mapped is not None:
            effort = mapped
        else:
            # Unknown estimate value — stringify as-is
            effort = str(raw_estimate)

    # Assemble the full properties dict, then strip empties
    props: dict[str, str | list[str]] = {
        "dcterms:title": issue.get("title", ""),
        f"{BPKM}taskStatus": normalize_status(state_type),
        f"{BPKM}priority": priority_val,  # type: ignore[dict-item]
        f"{BPKM}dueDate": due_date,  # type: ignore[dict-item]
        f"{BPKM}completedDate": completed_date,  # type: ignore[dict-item]
        f"{BPKM}tags": tags,  # type: ignore[dict-item]
        f"{BPKM}effort": effort,  # type: ignore[dict-item]
        f"{BPKM}externalId": issue.get("identifier", ""),
        f"{BPKM}externalUuid": issue.get("id", ""),
        f"{BPKM}externalUrl": issue.get("url", ""),
        f"{BPKM}externalProvider": "linear",
        f"{BPKM}lastSyncedAt": sync_time,
        f"{BPKM}syncDirection": "pull",
    }

    # Strip None, empty string, and empty list values
    return {
        k: v
        for k, v in props.items()
        if v is not None and v != "" and v != []
    }


# ---------------------------------------------------------------------------
# GraphQL query builder
# ---------------------------------------------------------------------------

_ISSUE_FIELDS = """\
        id identifier title description url trashed
        state { type }
        priority
        dueDate
        completedAt
        labels { nodes { name } }
        estimate
        assignee { id displayName email }
        updatedAt
        createdAt"""

_QUERY_WITH_UPDATED_AFTER = (
    "query($teamIds: [String!]!, $after: String, $updatedAfter: DateTime) {\n"
    "  issues(\n"
    "    filter: {\n"
    "      team: { id: { in: $teamIds } }\n"
    "      updatedAt: { gte: $updatedAfter }\n"
    "    }\n"
    "    first: 100\n"
    "    after: $after\n"
    "  ) {\n"
    "    nodes {\n"
    f"{_ISSUE_FIELDS}\n"
    "    }\n"
    "    pageInfo { hasNextPage endCursor }\n"
    "  }\n"
    "}"
)

_QUERY_WITHOUT_UPDATED_AFTER = (
    "query($teamIds: [String!]!, $after: String) {\n"
    "  issues(\n"
    "    filter: {\n"
    "      team: { id: { in: $teamIds } }\n"
    "    }\n"
    "    first: 100\n"
    "    after: $after\n"
    "  ) {\n"
    "    nodes {\n"
    f"{_ISSUE_FIELDS}\n"
    "    }\n"
    "    pageInfo { hasNextPage endCursor }\n"
    "  }\n"
    "}"
)


def build_issue_query(
    team_ids: list[str],
    updated_after: str | None = None,
) -> tuple[str, dict]:
    """Build a GraphQL query and variables for paginated issue fetching.

    Parameters
    ----------
    team_ids:
        Linear team IDs to filter by.
    updated_after:
        Optional ISO-8601 datetime.  When provided the query includes an
        ``updatedAt >= $updatedAfter`` filter for delta sync.

    Returns
    -------
    tuple[str, dict]
        ``(query_string, variables_dict)``.  The ``$after`` cursor variable
        is left for the pagination layer (``LinearClient.query_paginated``).
    """
    if updated_after is not None:
        return _QUERY_WITH_UPDATED_AFTER, {
            "teamIds": team_ids,
            "updatedAfter": updated_after,
        }
    return _QUERY_WITHOUT_UPDATED_AFTER, {"teamIds": team_ids}
