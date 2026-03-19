"""Pure field mapping between GitHub issue data and bpkm:Task properties.

All functions are side-effect-free: no network, no logging, no state.
Property keys use full IRIs for bpkm properties because the ``bpkm:``
prefix is not in the platform's COMMON_PREFIXES.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Full IRI prefix for basic-pkm model properties
BPKM = "urn:sempkm:model:basic-pkm:"

# GitHub issue state → bpkm:taskStatus
STATUS_MAP: dict[str, str] = {
    "open": "todo",
    "closed": "done",
}

# GitHub state_reason refines the basic state mapping.
# Available when state=="closed": "completed", "not_planned", "reopened"
# (reopened only appears transiently when state goes back to "open")
STATE_REASON_MAP: dict[str, str] = {
    "completed": "done",
    "not_planned": "cancelled",
    "reopened": "todo",
}

# bpkm:taskStatus → GitHub issue state (reverse for push sync, S03)
REVERSE_STATUS_MAP: dict[str, str] = {
    "todo": "open",
    "in-progress": "open",
    "done": "closed",
    "cancelled": "closed",
    "blocked": "open",
}


# ---------------------------------------------------------------------------
# IRI slug
# ---------------------------------------------------------------------------


def compute_issue_slug(repo_full_name: str, issue_number: int) -> str:
    """Compute a deterministic slug for a GitHub issue.

    The slug is used as the local part of a platform-minted Task IRI:
    ``{base_namespace}/Task/gh-{hash16}``.

    Args:
        repo_full_name: Full repository name (e.g. ``"owner/repo"``).
        issue_number: Issue number within the repository.

    Returns:
        Slug string in the format ``gh-{16 hex chars}``.
    """
    composite = f"{repo_full_name}#{issue_number}"
    digest = hashlib.sha256(composite.encode()).hexdigest()[:16]
    return f"gh-{digest}"


# ---------------------------------------------------------------------------
# URL parsing (for push sync)
# ---------------------------------------------------------------------------


def parse_external_url(url: str | None) -> tuple[str, str, int] | None:
    """Parse a GitHub issue/PR URL into ``(owner, repo, number)``.

    Handles both ``/issues/{N}`` and ``/pull/{N}`` path formats.
    Returns ``None`` for invalid, unparseable, or non-GitHub URLs.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
        if parsed.hostname not in ("github.com", "www.github.com"):
            return None
        # Path like /owner/repo/issues/42 or /owner/repo/pull/7
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 4:
            return None
        owner, repo, kind, number_str = parts[0], parts[1], parts[2], parts[3]
        if kind not in ("issues", "pull"):
            return None
        number = int(number_str)
        return (owner, repo, number)
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------


def _resolve_status(issue: dict) -> str:
    """Resolve bpkm:taskStatus from issue ``state`` and ``state_reason``.

    Uses ``STATE_REASON_MAP`` to refine the basic ``STATUS_MAP`` when
    ``state_reason`` is present. Falls back to ``STATUS_MAP`` otherwise.
    """
    state = issue.get("state", "open")
    state_reason = issue.get("state_reason")

    if state_reason and state_reason in STATE_REASON_MAP:
        return STATE_REASON_MAP[state_reason]

    return STATUS_MAP.get(state, "todo")


# ---------------------------------------------------------------------------
# Issue inspection
# ---------------------------------------------------------------------------


def is_pull_request(issue: dict) -> bool:
    """Return ``True`` if the issue dict represents a pull request.

    GitHub's ``/repos/{owner}/{repo}/issues`` endpoint returns both
    issues and PRs. PRs have a ``pull_request`` key in their JSON.
    """
    return "pull_request" in issue


def get_assignee_info(issue: dict) -> dict | None:
    """Extract assignee info from the first assignee in the issue.

    Returns:
        ``{"login": str, "email": str|None}`` from the first assignee,
        or ``None`` if no assignees.
    """
    assignees = issue.get("assignees", [])
    if not assignees:
        # Fallback to singular "assignee" field
        assignee = issue.get("assignee")
        if not assignee:
            return None
        return {
            "login": assignee.get("login", ""),
            "email": assignee.get("email"),
        }

    first = assignees[0]
    return {
        "login": first.get("login", ""),
        "email": first.get("email"),
    }


# ---------------------------------------------------------------------------
# Property builder (GitHub → bpkm)
# ---------------------------------------------------------------------------


def build_task_properties(
    issue: dict,
    repo_full_name: str,
    person_iri: str | None = None,
    sync_time: str | None = None,
) -> dict:
    """Build a properties dict for ``object.create`` / ``object.patch``.

    Parameters
    ----------
    issue:
        A GitHub issue dict from the REST API.
    repo_full_name:
        Full repo name (e.g. ``"owner/repo"``) — used for slug computation
        and project reference.
    person_iri:
        Optional SemPKM Person IRI for the first assignee.
    sync_time:
        ISO-8601 timestamp for ``bpkm:lastSyncedAt``.  When ``None``,
        the current UTC time is used.

    Returns
    -------
    dict
        Property mapping where keys are full IRIs (except ``dcterms:title``
        which uses the compact form recognised by the platform). Keys with
        ``None``, empty-string, or empty-list values are omitted — except
        ``lastSyncedAt`` which is always present.
    """
    from datetime import datetime, timezone as tz

    if sync_time is None:
        sync_time = datetime.now(tz.utc).isoformat()
    # Tags from labels
    labels = issue.get("labels", [])
    tags = [lbl["name"] for lbl in labels if isinstance(lbl, dict) and "name" in lbl]

    # Milestone fields
    milestone = issue.get("milestone")
    project_title = milestone.get("title") if milestone else None
    due_date = None
    if milestone and milestone.get("due_on"):
        due_date = milestone["due_on"][:10]

    # External provider: "github-pr" for PRs, "github" for issues
    provider = "github-pr" if is_pull_request(issue) else "github"

    props: dict[str, str | list[str] | None] = {
        "dcterms:title": issue.get("title", ""),
        f"{BPKM}taskStatus": _resolve_status(issue),
        f"{BPKM}tags": tags,
        f"{BPKM}assignedTo": person_iri,
        f"{BPKM}taskProject": project_title,
        f"{BPKM}externalId": f"#{issue['number']}",
        f"{BPKM}externalUrl": issue.get("html_url", ""),
        f"{BPKM}externalUuid": issue.get("node_id", ""),
        f"{BPKM}externalProvider": provider,
        f"{BPKM}dueDate": due_date,
    }

    # Strip None, empty string, and empty list values
    cleaned = {
        k: v
        for k, v in props.items()
        if v is not None and v != "" and v != []
    }

    # lastSyncedAt is always present (not stripped)
    cleaned[f"{BPKM}lastSyncedAt"] = sync_time

    return cleaned


# ---------------------------------------------------------------------------
# Timeline → linked issue extraction
# ---------------------------------------------------------------------------


def extract_linked_issue_numbers(
    timeline_events: list[dict],
    repo_full_name: str,
) -> list[tuple[str, int]]:
    """Extract deduplicated PR cross-references from timeline events.

    Filters timeline events for ``cross-referenced`` events whose source
    is a pull request in the same repository. Returns a sorted,
    deduplicated list of ``(repo_full_name, pr_number)`` tuples.

    Malformed events (missing keys, unexpected structure) are silently
    skipped — this is intentional since timeline data can be inconsistent.

    Args:
        timeline_events: List of event dicts from the timeline API.
        repo_full_name: Full repository name (e.g. ``"owner/repo"``)
            used to filter out cross-repo references.

    Returns:
        Sorted list of ``(repo_full_name, pr_number)`` tuples for
        same-repo PRs that reference the issue.
    """
    seen: set[tuple[str, int]] = set()

    for event in timeline_events:
        try:
            if event.get("event") != "cross-referenced":
                continue

            source_issue = event.get("source", {}).get("issue", {})

            # Must be a PR (has pull_request key), not an issue cross-ref
            if not source_issue.get("pull_request"):
                continue

            source_repo = source_issue.get("repository", {}).get("full_name")
            pr_number = source_issue.get("number")

            if not source_repo or pr_number is None:
                continue

            # Same-repo only
            if source_repo != repo_full_name:
                continue

            seen.add((source_repo, pr_number))
        except (TypeError, AttributeError, KeyError):
            # Malformed event — skip gracefully
            continue

    return sorted(seen, key=lambda t: t[1])


# ---------------------------------------------------------------------------
# Reverse mapping (bpkm → GitHub PATCH body)
# ---------------------------------------------------------------------------


def build_issue_patch(task_props: dict) -> dict:
    """Build a GitHub issue PATCH body from bpkm task properties.

    Maps bpkm properties back to the fields accepted by
    ``PATCH /repos/{owner}/{repo}/issues/{number}``.

    Parameters
    ----------
    task_props:
        Property dict with full IRI keys (e.g.
        ``urn:sempkm:model:basic-pkm:taskStatus``).

    Returns
    -------
    dict
        GitHub PATCH body. Only fields with non-None values are included.
        Empty dict means no pushable changes detected.
    """
    result: dict = {}

    # Title
    title = task_props.get("dcterms:title")
    if title:
        result["title"] = title

    # Status → state
    bpkm_status = task_props.get(f"{BPKM}taskStatus")
    if bpkm_status:
        gh_state = REVERSE_STATUS_MAP.get(bpkm_status)
        if gh_state:
            result["state"] = gh_state
            # Set state_reason for closed issues
            if gh_state == "closed":
                if bpkm_status == "cancelled":
                    result["state_reason"] = "not_planned"
                else:
                    result["state_reason"] = "completed"

    # Labels from tags
    tags = task_props.get(f"{BPKM}tags")
    if tags and isinstance(tags, list):
        result["labels"] = tags

    return result
