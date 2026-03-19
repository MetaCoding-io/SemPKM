"""Unit tests for GitHub Sync field mapper.

Loads ``field_mapper.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package. All functions are pure —
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
    / "github-sync"
    / "services"
    / "field_mapper.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("github_field_mapper", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["github_field_mapper"] = mod
    spec.loader.exec_module(mod)
    return mod


fm = _load_module()

BPKM = fm.BPKM


# ---------------------------------------------------------------------------
# Fixtures — sample GitHub issue dicts
# ---------------------------------------------------------------------------

def _make_issue(**overrides) -> dict:
    """Build a minimal GitHub issue dict with sensible defaults."""
    base = {
        "number": 42,
        "title": "Fix the widget",
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/42",
        "node_id": "I_kwDOTest42",
        "labels": [{"name": "bug"}, {"name": "urgent"}],
        "assignees": [{"login": "alice", "email": "alice@example.com"}],
        "milestone": {
            "title": "v1.0",
            "due_on": "2026-04-01T07:00:00Z",
        },
    }
    base.update(overrides)
    return base


# ===================================================================
# compute_issue_slug tests
# ===================================================================

class TestComputeIssueSlug:
    def test_deterministic(self):
        slug1 = fm.compute_issue_slug("owner/repo", 42)
        slug2 = fm.compute_issue_slug("owner/repo", 42)
        assert slug1 == slug2

    def test_different_repos_different_slugs(self):
        slug_a = fm.compute_issue_slug("owner/repo-a", 1)
        slug_b = fm.compute_issue_slug("owner/repo-b", 1)
        assert slug_a != slug_b

    def test_different_numbers_different_slugs(self):
        slug_1 = fm.compute_issue_slug("owner/repo", 1)
        slug_2 = fm.compute_issue_slug("owner/repo", 2)
        assert slug_1 != slug_2

    def test_format_gh_prefix_16_hex(self):
        slug = fm.compute_issue_slug("owner/repo", 99)
        assert slug.startswith("gh-")
        hex_part = slug[3:]
        assert len(hex_part) == 16
        # Verify it's valid hex
        int(hex_part, 16)


# ===================================================================
# build_task_properties tests
# ===================================================================

class TestBuildTaskProperties:
    def test_basic_issue_all_fields(self):
        issue = _make_issue()
        props = fm.build_task_properties(issue, "owner/repo", person_iri="urn:person:alice")
        assert props["dcterms:title"] == "Fix the widget"
        assert props[f"{BPKM}taskStatus"] == "todo"
        assert props[f"{BPKM}tags"] == ["bug", "urgent"]
        assert props[f"{BPKM}assignedTo"] == "urn:person:alice"
        assert props[f"{BPKM}taskProject"] == "v1.0"
        assert props[f"{BPKM}externalId"] == "#42"
        assert props[f"{BPKM}externalUrl"] == "https://github.com/owner/repo/issues/42"
        assert props[f"{BPKM}externalUuid"] == "I_kwDOTest42"
        assert props[f"{BPKM}externalProvider"] == "github"
        assert props[f"{BPKM}dueDate"] == "2026-04-01"

    def test_missing_optional_fields(self):
        issue = _make_issue(labels=[], assignees=[], milestone=None)
        props = fm.build_task_properties(issue, "owner/repo")
        # tags and assignedTo should be omitted (empty list / None)
        assert f"{BPKM}tags" not in props
        assert f"{BPKM}assignedTo" not in props
        assert f"{BPKM}taskProject" not in props
        assert f"{BPKM}dueDate" not in props
        # Core fields still present
        assert props["dcterms:title"] == "Fix the widget"
        assert props[f"{BPKM}externalId"] == "#42"

    def test_open_maps_to_todo(self):
        issue = _make_issue(state="open")
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}taskStatus"] == "todo"

    def test_closed_maps_to_done(self):
        issue = _make_issue(state="closed")
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}taskStatus"] == "done"

    def test_closed_not_planned_maps_to_cancelled(self):
        issue = _make_issue(state="closed", state_reason="not_planned")
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}taskStatus"] == "cancelled"

    def test_closed_completed_maps_to_done(self):
        issue = _make_issue(state="closed", state_reason="completed")
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}taskStatus"] == "done"

    def test_reopened_maps_to_todo(self):
        issue = _make_issue(state="open", state_reason="reopened")
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}taskStatus"] == "todo"

    def test_labels_mapped_as_tags(self):
        issue = _make_issue(labels=[{"name": "enhancement"}, {"name": "p1"}])
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}tags"] == ["enhancement", "p1"]

    def test_first_assignee_iri_passed_through(self):
        props = fm.build_task_properties(
            _make_issue(), "owner/repo", person_iri="urn:person:bob"
        )
        assert props[f"{BPKM}assignedTo"] == "urn:person:bob"

    def test_no_person_iri_omits_assignee(self):
        props = fm.build_task_properties(_make_issue(), "owner/repo")
        assert f"{BPKM}assignedTo" not in props

    def test_milestone_title_as_project(self):
        issue = _make_issue(milestone={"title": "Sprint 3", "due_on": None})
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}taskProject"] == "Sprint 3"

    def test_external_id_format(self):
        issue = _make_issue(number=123)
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}externalId"] == "#123"

    def test_external_url(self):
        issue = _make_issue(html_url="https://github.com/foo/bar/issues/7")
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}externalUrl"] == "https://github.com/foo/bar/issues/7"

    def test_external_uuid(self):
        issue = _make_issue(node_id="MDU6SXNz_abc")
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}externalUuid"] == "MDU6SXNz_abc"

    def test_external_provider_github_for_issue(self):
        issue = _make_issue()
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}externalProvider"] == "github"

    def test_external_provider_github_pr_for_pull_request(self):
        issue = _make_issue(pull_request={"url": "..."})
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}externalProvider"] == "github-pr"

    def test_due_date_from_milestone(self):
        issue = _make_issue(milestone={"title": "v2", "due_on": "2026-06-15T00:00:00Z"})
        props = fm.build_task_properties(issue, "owner/repo")
        assert props[f"{BPKM}dueDate"] == "2026-06-15"

    def test_no_due_date_when_milestone_has_no_due_on(self):
        issue = _make_issue(milestone={"title": "v2", "due_on": None})
        props = fm.build_task_properties(issue, "owner/repo")
        assert f"{BPKM}dueDate" not in props


# ===================================================================
# is_pull_request tests
# ===================================================================

class TestIsPullRequest:
    def test_issue_without_pr_key(self):
        assert fm.is_pull_request({"number": 1, "title": "bug"}) is False

    def test_issue_with_pr_key(self):
        assert fm.is_pull_request({"number": 1, "pull_request": {"url": "..."}}) is True

    def test_pr_as_issue(self):
        """GitHub returns PRs with pull_request key even in issues endpoint."""
        issue = _make_issue(pull_request={"url": "...", "merged_at": None})
        assert fm.is_pull_request(issue) is True


# ===================================================================
# get_assignee_info tests
# ===================================================================

class TestGetAssigneeInfo:
    def test_no_assignees(self):
        issue = _make_issue(assignees=[], assignee=None)
        assert fm.get_assignee_info(issue) is None

    def test_one_assignee_with_email(self):
        issue = _make_issue(
            assignees=[{"login": "alice", "email": "alice@example.com"}]
        )
        info = fm.get_assignee_info(issue)
        assert info == {"login": "alice", "email": "alice@example.com"}

    def test_one_assignee_without_email(self):
        issue = _make_issue(
            assignees=[{"login": "bob", "email": None}]
        )
        info = fm.get_assignee_info(issue)
        assert info == {"login": "bob", "email": None}

    def test_multiple_assignees_takes_first(self):
        issue = _make_issue(
            assignees=[
                {"login": "first", "email": "first@example.com"},
                {"login": "second", "email": "second@example.com"},
            ]
        )
        info = fm.get_assignee_info(issue)
        assert info["login"] == "first"

    def test_fallback_to_singular_assignee(self):
        """When assignees list is missing, fall back to singular assignee field."""
        issue = {"number": 1, "assignee": {"login": "solo", "email": "solo@x.com"}}
        info = fm.get_assignee_info(issue)
        assert info == {"login": "solo", "email": "solo@x.com"}


# ===================================================================
# build_issue_patch tests (reverse mapping)
# ===================================================================

class TestBuildIssuePatch:
    def test_title_mapping(self):
        patch = fm.build_issue_patch({"dcterms:title": "New Title"})
        assert patch["title"] == "New Title"

    def test_status_todo_to_open(self):
        patch = fm.build_issue_patch({f"{BPKM}taskStatus": "todo"})
        assert patch["state"] == "open"

    def test_status_done_to_closed(self):
        patch = fm.build_issue_patch({f"{BPKM}taskStatus": "done"})
        assert patch["state"] == "closed"
        assert patch["state_reason"] == "completed"

    def test_status_cancelled_to_closed_not_planned(self):
        patch = fm.build_issue_patch({f"{BPKM}taskStatus": "cancelled"})
        assert patch["state"] == "closed"
        assert patch["state_reason"] == "not_planned"

    def test_labels_reverse_mapping(self):
        patch = fm.build_issue_patch({f"{BPKM}tags": ["bug", "urgent"]})
        assert patch["labels"] == ["bug", "urgent"]

    def test_empty_properties(self):
        patch = fm.build_issue_patch({})
        assert patch == {}

    def test_in_progress_to_open(self):
        patch = fm.build_issue_patch({f"{BPKM}taskStatus": "in-progress"})
        assert patch["state"] == "open"

    def test_blocked_to_open(self):
        patch = fm.build_issue_patch({f"{BPKM}taskStatus": "blocked"})
        assert patch["state"] == "open"


# ===================================================================
# STATUS_MAP / REVERSE_STATUS_MAP coverage tests
# ===================================================================

class TestStatusMaps:
    def test_all_status_map_entries(self):
        assert fm.STATUS_MAP["open"] == "todo"
        assert fm.STATUS_MAP["closed"] == "done"

    def test_all_reverse_status_entries(self):
        assert fm.REVERSE_STATUS_MAP["todo"] == "open"
        assert fm.REVERSE_STATUS_MAP["in-progress"] == "open"
        assert fm.REVERSE_STATUS_MAP["done"] == "closed"
        assert fm.REVERSE_STATUS_MAP["cancelled"] == "closed"
        assert fm.REVERSE_STATUS_MAP["blocked"] == "open"

    def test_roundtrip_open_todo(self):
        """open → todo → open round-trips correctly."""
        bpkm = fm.STATUS_MAP["open"]
        gh = fm.REVERSE_STATUS_MAP[bpkm]
        assert gh == "open"

    def test_roundtrip_closed_done(self):
        """closed → done → closed round-trips correctly."""
        bpkm = fm.STATUS_MAP["closed"]
        gh = fm.REVERSE_STATUS_MAP[bpkm]
        assert gh == "closed"


# ===================================================================
# extract_linked_issue_numbers tests
# ===================================================================

def _make_cross_ref_event(
    pr_number: int,
    repo_full_name: str = "owner/repo",
    has_pull_request: bool = True,
) -> dict:
    """Build a cross-referenced timeline event."""
    issue_data: dict = {
        "number": pr_number,
        "repository": {"full_name": repo_full_name},
    }
    if has_pull_request:
        issue_data["pull_request"] = {"url": "..."}
    return {
        "event": "cross-referenced",
        "source": {"issue": issue_data},
    }


class TestExtractLinkedIssueNumbers:

    def test_cross_referenced_with_pr(self):
        """Returns (repo, number) for a cross-referenced PR event."""
        events = [_make_cross_ref_event(10, "owner/repo")]
        result = fm.extract_linked_issue_numbers(events, "owner/repo")
        assert result == [("owner/repo", 10)]

    def test_cross_referenced_without_pr(self):
        """Skips event where source.issue has no pull_request key (issue cross-ref)."""
        events = [_make_cross_ref_event(10, "owner/repo", has_pull_request=False)]
        result = fm.extract_linked_issue_numbers(events, "owner/repo")
        assert result == []

    def test_cross_repo_filtered_out(self):
        """Skips event from a different repository."""
        events = [_make_cross_ref_event(10, "other-owner/other-repo")]
        result = fm.extract_linked_issue_numbers(events, "owner/repo")
        assert result == []

    def test_same_repo_included(self):
        """Includes event from the same repository."""
        events = [_make_cross_ref_event(5, "owner/repo")]
        result = fm.extract_linked_issue_numbers(events, "owner/repo")
        assert result == [("owner/repo", 5)]

    def test_empty_timeline(self):
        """Returns empty list for empty timeline."""
        result = fm.extract_linked_issue_numbers([], "owner/repo")
        assert result == []

    def test_duplicate_dedup(self):
        """Two events with same PR number deduplicated to one."""
        events = [
            _make_cross_ref_event(10, "owner/repo"),
            _make_cross_ref_event(10, "owner/repo"),
        ]
        result = fm.extract_linked_issue_numbers(events, "owner/repo")
        assert result == [("owner/repo", 10)]

    def test_malformed_event_skipped(self):
        """Events missing source or source.issue are skipped without error."""
        events = [
            {"event": "cross-referenced"},  # no source
            {"event": "cross-referenced", "source": {}},  # no issue
            {"event": "cross-referenced", "source": {"issue": {}}},  # no repo/number
            {"event": "labeled", "label": {"name": "bug"}},  # not cross-referenced
            None,  # completely wrong type
        ]
        result = fm.extract_linked_issue_numbers(events, "owner/repo")
        assert result == []

    def test_multiple_prs_referencing_issue(self):
        """Returns all unique PR numbers, sorted."""
        events = [
            _make_cross_ref_event(20, "owner/repo"),
            _make_cross_ref_event(5, "owner/repo"),
            _make_cross_ref_event(15, "owner/repo"),
        ]
        result = fm.extract_linked_issue_numbers(events, "owner/repo")
        assert result == [("owner/repo", 5), ("owner/repo", 15), ("owner/repo", 20)]

    def test_mixed_same_and_cross_repo(self):
        """Only same-repo PRs are returned when mixed with cross-repo."""
        events = [
            _make_cross_ref_event(10, "owner/repo"),
            _make_cross_ref_event(20, "other/repo"),
            _make_cross_ref_event(30, "owner/repo"),
        ]
        result = fm.extract_linked_issue_numbers(events, "owner/repo")
        assert result == [("owner/repo", 10), ("owner/repo", 30)]


# ===================================================================
# parse_external_url tests
# ===================================================================

class TestParseExternalUrl:
    def test_issue_url(self):
        result = fm.parse_external_url("https://github.com/owner/repo/issues/42")
        assert result == ("owner", "repo", 42)

    def test_pr_url(self):
        result = fm.parse_external_url("https://github.com/owner/repo/pull/7")
        assert result == ("owner", "repo", 7)

    def test_invalid_url(self):
        result = fm.parse_external_url("not a url at all")
        assert result is None

    def test_non_github_url(self):
        result = fm.parse_external_url("https://gitlab.com/owner/repo/issues/1")
        assert result is None

    def test_missing_segments(self):
        result = fm.parse_external_url("https://github.com/owner/repo")
        assert result is None

    def test_no_path(self):
        result = fm.parse_external_url("https://github.com/")
        assert result is None

    def test_none_input(self):
        result = fm.parse_external_url(None)
        assert result is None

    def test_empty_string(self):
        result = fm.parse_external_url("")
        assert result is None

    def test_wrong_path_type(self):
        """URL with /tree/ or /blob/ instead of /issues/ or /pull/."""
        result = fm.parse_external_url("https://github.com/owner/repo/tree/main")
        assert result is None

    def test_www_github(self):
        """www.github.com should also be accepted."""
        result = fm.parse_external_url("https://www.github.com/owner/repo/issues/10")
        assert result == ("owner", "repo", 10)


# ===================================================================
# build_task_properties lastSyncedAt tests
# ===================================================================

class TestBuildTaskPropertiesLastSyncedAt:
    def test_last_synced_at_present_in_output(self):
        issue = _make_issue()
        props = fm.build_task_properties(issue, "owner/repo")
        assert f"{BPKM}lastSyncedAt" in props
        # Should be an ISO timestamp string
        assert "T" in props[f"{BPKM}lastSyncedAt"]

    def test_custom_sync_time_used(self):
        issue = _make_issue()
        props = fm.build_task_properties(
            issue, "owner/repo", sync_time="2026-03-18T10:00:00+00:00"
        )
        assert props[f"{BPKM}lastSyncedAt"] == "2026-03-18T10:00:00+00:00"

    def test_last_synced_at_not_stripped(self):
        """lastSyncedAt is present even when other optional fields are stripped."""
        issue = _make_issue(labels=[], assignees=[], milestone=None)
        props = fm.build_task_properties(issue, "owner/repo")
        # Stripped fields should be absent
        assert f"{BPKM}tags" not in props
        assert f"{BPKM}assignedTo" not in props
        # But lastSyncedAt is always there
        assert f"{BPKM}lastSyncedAt" in props
