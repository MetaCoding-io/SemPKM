"""Comprehensive unit tests for the Linear→bpkm field mapper.

Loads ``field_mapper.py`` from the apps directory via importlib so that
the app does not need to be installed as a package.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load field_mapper module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "linear-sync"
    / "services"
    / "field_mapper.py"
)

spec = importlib.util.spec_from_file_location("field_mapper", _MODULE_PATH)
assert spec and spec.loader
field_mapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(field_mapper)

# Convenience aliases
normalize_status = field_mapper.normalize_status
normalize_priority = field_mapper.normalize_priority
map_labels_to_tags = field_mapper.map_labels_to_tags
compute_issue_slug = field_mapper.compute_issue_slug
build_task_properties = field_mapper.build_task_properties
build_issue_query = field_mapper.build_issue_query
BPKM = field_mapper.BPKM


# ===================================================================
# Helpers
# ===================================================================

def _make_issue(**overrides) -> dict:
    """Return a plausible Linear issue dict, with overrides."""
    base = {
        "id": "issue-uuid-001",
        "identifier": "ENG-123",
        "title": "Fix login bug",
        "description": "The login page crashes on Safari.",
        "state": {"type": "started"},
        "priority": 2,
        "dueDate": "2026-04-01",
        "completedAt": None,
        "labels": {"nodes": [{"name": "bug"}, {"name": "frontend"}]},
        "estimate": 3,
        "url": "https://linear.app/acme/issue/ENG-123",
        "trashed": False,
    }
    base.update(overrides)
    return base


# ===================================================================
# normalize_status
# ===================================================================


class TestNormalizeStatus:
    def test_backlog(self):
        assert normalize_status("backlog") == "todo"

    def test_unstarted(self):
        assert normalize_status("unstarted") == "todo"

    def test_started(self):
        assert normalize_status("started") == "in-progress"

    def test_completed(self):
        assert normalize_status("completed") == "done"

    def test_cancelled(self):
        assert normalize_status("cancelled") == "cancelled"

    def test_unknown_defaults_to_todo(self):
        assert normalize_status("triaged") == "todo"

    def test_empty_string_defaults_to_todo(self):
        assert normalize_status("") == "todo"


# ===================================================================
# normalize_priority
# ===================================================================


class TestNormalizePriority:
    def test_urgent(self):
        assert normalize_priority(1) == "critical"

    def test_high(self):
        assert normalize_priority(2) == "high"

    def test_medium(self):
        assert normalize_priority(3) == "medium"

    def test_low(self):
        assert normalize_priority(4) == "low"

    def test_no_priority_returns_none(self):
        assert normalize_priority(0) is None

    def test_unknown_returns_none(self):
        assert normalize_priority(99) is None


# ===================================================================
# map_labels_to_tags
# ===================================================================


class TestMapLabelsToTags:
    def test_multiple_labels(self):
        labels = [{"name": "bug"}, {"name": "frontend"}]
        assert map_labels_to_tags(labels) == ["bug", "frontend"]

    def test_empty_list(self):
        assert map_labels_to_tags([]) == []

    def test_none_returns_empty(self):
        assert map_labels_to_tags(None) == []

    def test_label_without_name_skipped(self):
        labels = [{"name": "bug"}, {"id": "no-name"}]
        assert map_labels_to_tags(labels) == ["bug"]

    def test_single_label(self):
        assert map_labels_to_tags([{"name": "design"}]) == ["design"]


# ===================================================================
# compute_issue_slug
# ===================================================================


class TestComputeIssueSlug:
    def test_determinism(self):
        slug1 = compute_issue_slug("ws-1", "issue-1")
        slug2 = compute_issue_slug("ws-1", "issue-1")
        assert slug1 == slug2

    def test_different_inputs_different_slugs(self):
        slug1 = compute_issue_slug("ws-1", "issue-1")
        slug2 = compute_issue_slug("ws-1", "issue-2")
        assert slug1 != slug2

    def test_different_workspace_different_slug(self):
        slug1 = compute_issue_slug("ws-1", "issue-1")
        slug2 = compute_issue_slug("ws-2", "issue-1")
        assert slug1 != slug2

    def test_format(self):
        slug = compute_issue_slug("ws-1", "issue-1")
        assert slug.startswith("issue-")
        # 'issue-' (6 chars) + 16 hex chars = 22 total
        assert len(slug) == 22
        assert re.match(r"^issue-[0-9a-f]{16}$", slug)


# ===================================================================
# build_task_properties
# ===================================================================


class TestBuildTaskProperties:
    SYNC_TIME = "2026-03-18T16:00:00+00:00"

    def test_full_issue_all_fields(self):
        issue = _make_issue(
            state={"type": "completed"},
            completedAt="2026-03-18T10:00:00.000Z",
        )
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)

        assert props["dcterms:title"] == "Fix login bug"
        assert props[f"{BPKM}taskStatus"] == "done"
        assert props[f"{BPKM}priority"] == "high"
        assert props[f"{BPKM}dueDate"] == "2026-04-01"
        assert props[f"{BPKM}completedDate"] == "2026-03-18"
        assert props[f"{BPKM}tags"] == ["bug", "frontend"]
        assert props[f"{BPKM}effort"] == "medium"
        assert props[f"{BPKM}externalId"] == "ENG-123"
        assert props[f"{BPKM}externalUrl"] == "https://linear.app/acme/issue/ENG-123"
        assert props[f"{BPKM}externalProvider"] == "linear"
        assert props[f"{BPKM}lastSyncedAt"] == self.SYNC_TIME
        assert props[f"{BPKM}syncDirection"] == "pull"

    def test_minimal_issue_nulls_omitted(self):
        issue = _make_issue(
            priority=0,
            dueDate=None,
            completedAt=None,
            labels={"nodes": []},
            estimate=None,
        )
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)

        # These should be omitted
        assert f"{BPKM}priority" not in props
        assert f"{BPKM}dueDate" not in props
        assert f"{BPKM}completedDate" not in props
        assert f"{BPKM}tags" not in props
        assert f"{BPKM}effort" not in props

        # These should always be present
        assert props["dcterms:title"] == "Fix login bug"
        assert props[f"{BPKM}taskStatus"] == "in-progress"
        assert props[f"{BPKM}externalId"] == "ENG-123"
        assert props[f"{BPKM}externalUrl"] == "https://linear.app/acme/issue/ENG-123"
        assert props[f"{BPKM}externalProvider"] == "linear"

    def test_priority_zero_omitted(self):
        issue = _make_issue(priority=0)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert f"{BPKM}priority" not in props

    def test_empty_labels_omitted(self):
        issue = _make_issue(labels={"nodes": []})
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert f"{BPKM}tags" not in props

    def test_completed_date_only_when_completed(self):
        # State is "started", not "completed" — completedDate should be omitted
        issue = _make_issue(
            state={"type": "started"},
            completedAt="2026-03-18T10:00:00.000Z",
        )
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert f"{BPKM}completedDate" not in props

    def test_completed_date_present_when_completed(self):
        issue = _make_issue(
            state={"type": "completed"},
            completedAt="2026-03-18T10:00:00.000Z",
        )
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}completedDate"] == "2026-03-18"

    def test_due_date_truncated_from_datetime(self):
        issue = _make_issue(dueDate="2026-04-01T00:00:00.000Z")
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}dueDate"] == "2026-04-01"

    def test_due_date_already_date_only(self):
        issue = _make_issue(dueDate="2026-04-01")
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}dueDate"] == "2026-04-01"

    def test_all_bpkm_keys_use_full_iris(self):
        issue = _make_issue(
            state={"type": "completed"},
            completedAt="2026-03-18T10:00:00.000Z",
        )
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        for key in props:
            if key == "dcterms:title":
                continue  # compact form is expected for dcterms
            assert key.startswith("urn:sempkm:model:basic-pkm:"), (
                f"Key {key!r} does not use full IRI"
            )

    def test_external_fields_always_present(self):
        issue = _make_issue()
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}externalId"] == "ENG-123"
        assert props[f"{BPKM}externalUrl"] == "https://linear.app/acme/issue/ENG-123"
        assert props[f"{BPKM}externalProvider"] == "linear"

    def test_sync_time_auto_generated_when_none(self):
        issue = _make_issue()
        props = build_task_properties(issue, "ws-1")
        # Should be a valid ISO datetime string
        assert f"{BPKM}lastSyncedAt" in props
        ts = props[f"{BPKM}lastSyncedAt"]
        assert isinstance(ts, str)
        assert len(ts) > 10  # longer than a bare date

    def test_labels_none_in_issue(self):
        """When labels key is None (not just empty nodes)."""
        issue = _make_issue(labels=None)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert f"{BPKM}tags" not in props

    def test_no_state_key_defaults_to_todo(self):
        """Issue missing 'state' entirely — should default gracefully."""
        issue = _make_issue()
        del issue["state"]
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}taskStatus"] == "todo"


# ===================================================================
# Effort mapping
# ===================================================================


class TestEffortMapping:
    SYNC_TIME = "2026-03-18T16:00:00+00:00"

    def test_known_estimate_1(self):
        issue = _make_issue(estimate=1)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}effort"] == "trivial"

    def test_known_estimate_2(self):
        issue = _make_issue(estimate=2)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}effort"] == "small"

    def test_known_estimate_3(self):
        issue = _make_issue(estimate=3)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}effort"] == "medium"

    def test_known_estimate_5(self):
        issue = _make_issue(estimate=5)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}effort"] == "large"

    def test_known_estimate_8(self):
        issue = _make_issue(estimate=8)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}effort"] == "epic"

    def test_unknown_estimate_stringified(self):
        issue = _make_issue(estimate=13)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert props[f"{BPKM}effort"] == "13"

    def test_estimate_zero_omitted(self):
        issue = _make_issue(estimate=0)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert f"{BPKM}effort" not in props

    def test_estimate_none_omitted(self):
        issue = _make_issue(estimate=None)
        props = build_task_properties(issue, "ws-1", sync_time=self.SYNC_TIME)
        assert f"{BPKM}effort" not in props


# ===================================================================
# build_issue_query
# ===================================================================


class TestBuildIssueQuery:
    def test_query_includes_team_filter(self):
        query, variables = build_issue_query(["team-1", "team-2"])
        assert "teamIds" in query
        assert "$teamIds" in query
        assert "team" in query
        assert variables["teamIds"] == ["team-1", "team-2"]

    def test_query_includes_updated_after_when_provided(self):
        query, variables = build_issue_query(
            ["team-1"], updated_after="2026-03-01T00:00:00Z"
        )
        assert "updatedAfter" in query
        assert "$updatedAfter" in query
        assert "updatedAt" in query
        assert "gte" in query
        assert variables["updatedAfter"] == "2026-03-01T00:00:00Z"

    def test_query_omits_updated_after_when_none(self):
        query, variables = build_issue_query(["team-1"])
        assert "updatedAfter" not in query
        assert "$updatedAfter" not in query
        assert "updatedAfter" not in variables

    def test_variables_dict_correct(self):
        _, variables = build_issue_query(
            ["t1", "t2"], updated_after="2026-01-01T00:00:00Z"
        )
        assert variables == {
            "teamIds": ["t1", "t2"],
            "updatedAfter": "2026-01-01T00:00:00Z",
        }

    def test_query_requests_all_fields(self):
        query, _ = build_issue_query(["team-1"])
        for field in [
            "id", "identifier", "title", "description", "url", "trashed",
            "state", "type", "priority", "dueDate", "completedAt",
            "labels", "name", "estimate", "assignee", "displayName",
            "email", "updatedAt", "createdAt", "hasNextPage", "endCursor",
        ]:
            assert field in query, f"Expected field {field!r} in query"

    def test_query_paginates_with_after(self):
        query, _ = build_issue_query(["team-1"])
        assert "$after" in query
        assert "after: $after" in query
        assert "first: 100" in query
