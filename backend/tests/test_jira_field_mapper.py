"""Unit tests for Jira Sync field mapper.

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
    / "jira-sync"
    / "services"
    / "field_mapper.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("jira_field_mapper", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["jira_field_mapper"] = mod
    spec.loader.exec_module(mod)
    return mod


fm = _load_module()

BPKM = fm.BPKM


# ---------------------------------------------------------------------------
# Fixtures — sample Jira issue dicts
# ---------------------------------------------------------------------------


def _make_issue(**overrides) -> dict:
    """Build a realistic Jira issue dict with sensible defaults.

    Follows the shape returned by ``/rest/api/3/search``:
    top-level ``id``, ``key``, ``self``, and nested ``fields`` dict.

    If ``fields`` is passed as a keyword argument, it **replaces** the
    default fields entirely (for minimal-issue tests).
    """
    if "fields" in overrides:
        fields = overrides.pop("fields")
    else:
        fields = {
            "summary": "Fix the widget",
            "status": {
                "name": "In Progress",
                "statusCategory": {"key": "indeterminate"},
            },
            "priority": {"name": "High"},
            "duedate": "2026-04-15",
            "resolutiondate": None,
            "assignee": {"accountId": "abc123", "emailAddress": "alice@example.com"},
            "labels": [{"name": "bug"}, {"name": "urgent"}],
            "components": [{"name": "backend"}],
            "sprint": {"name": "Sprint 7"},
        }

    base = {
        "id": "10042",
        "key": "PROJ-42",
        "self": "https://mysite.atlassian.net/rest/api/3/issue/10042",
        "fields": fields,
    }
    base.update(overrides)
    return base


def _make_epic(**overrides) -> dict:
    """Build a Jira epic issue dict.

    If ``fields`` is passed, it **replaces** the default fields entirely.
    """
    if "fields" in overrides:
        fields = overrides.pop("fields")
    else:
        fields = {
            "summary": "Q2 Feature Epic",
            "status": {
                "name": "Done",
                "statusCategory": {"key": "done"},
            },
            "duedate": "2026-06-30",
            "issuetype": {"name": "Epic"},
        }

    base = {
        "id": "10100",
        "key": "PROJ-100",
        "self": "https://mysite.atlassian.net/rest/api/3/issue/10100",
        "fields": fields,
    }
    base.update(overrides)
    return base


# ===================================================================
# STATUS_MAP tests
# ===================================================================

class TestStatusMap:
    def test_new_maps_to_todo(self):
        assert fm.STATUS_MAP["new"] == "todo"

    def test_indeterminate_maps_to_in_progress(self):
        assert fm.STATUS_MAP["indeterminate"] == "in-progress"

    def test_done_maps_to_done(self):
        assert fm.STATUS_MAP["done"] == "done"

    def test_unknown_key_defaults_to_todo(self):
        assert fm.normalize_status("unknown") == "todo"

    def test_empty_string_defaults_to_todo(self):
        assert fm.normalize_status("") == "todo"


# ===================================================================
# PRIORITY_MAP tests
# ===================================================================

class TestPriorityMap:
    def test_highest_maps_to_critical(self):
        assert fm.PRIORITY_MAP["Highest"] == "critical"

    def test_critical_maps_to_critical(self):
        assert fm.PRIORITY_MAP["Critical"] == "critical"

    def test_blocker_maps_to_critical(self):
        assert fm.PRIORITY_MAP["Blocker"] == "critical"

    def test_high_maps_to_high(self):
        assert fm.PRIORITY_MAP["High"] == "high"

    def test_medium_maps_to_medium(self):
        assert fm.PRIORITY_MAP["Medium"] == "medium"

    def test_low_maps_to_low(self):
        assert fm.PRIORITY_MAP["Low"] == "low"

    def test_lowest_maps_to_low(self):
        assert fm.PRIORITY_MAP["Lowest"] == "low"

    def test_trivial_maps_to_low(self):
        assert fm.PRIORITY_MAP["Trivial"] == "low"

    def test_unknown_priority_returns_none(self):
        assert fm.normalize_priority("Nonexistent") is None

    def test_none_priority_returns_none(self):
        assert fm.normalize_priority(None) is None


# ===================================================================
# compute_issue_slug tests
# ===================================================================

class TestComputeIssueSlug:
    def test_deterministic(self):
        slug1 = fm.compute_issue_slug("PROJ", "PROJ-42")
        slug2 = fm.compute_issue_slug("PROJ", "PROJ-42")
        assert slug1 == slug2

    def test_different_projects_different_slugs(self):
        slug_a = fm.compute_issue_slug("PROJ", "PROJ-1")
        slug_b = fm.compute_issue_slug("OTHER", "OTHER-1")
        assert slug_a != slug_b

    def test_different_keys_different_slugs(self):
        slug_1 = fm.compute_issue_slug("PROJ", "PROJ-1")
        slug_2 = fm.compute_issue_slug("PROJ", "PROJ-2")
        assert slug_1 != slug_2

    def test_prefix_is_jira(self):
        slug = fm.compute_issue_slug("PROJ", "PROJ-99")
        assert slug.startswith("jira-")

    def test_format_jira_prefix_16_hex(self):
        slug = fm.compute_issue_slug("PROJ", "PROJ-99")
        hex_part = slug[5:]  # after "jira-"
        assert len(hex_part) == 16
        int(hex_part, 16)  # validates hex


# ===================================================================
# build_task_properties tests
# ===================================================================

class TestBuildTaskProperties:
    def test_full_issue_all_fields(self):
        issue = _make_issue()
        props = fm.build_task_properties(
            issue, person_iri="urn:person:alice",
            sync_time="2026-03-19T10:00:00+00:00",
        )
        assert props["dcterms:title"] == "Fix the widget"
        assert props[f"{BPKM}taskStatus"] == "in-progress"
        assert props[f"{BPKM}externalStatus"] == "In Progress"
        assert props[f"{BPKM}priority"] == "high"
        assert props[f"{BPKM}dueDate"] == "2026-04-15"
        assert f"{BPKM}completedDate" not in props  # no resolutiondate
        assert props[f"{BPKM}assignedTo"] == "urn:person:alice"
        assert "bug" in props[f"{BPKM}tags"]
        assert "urgent" in props[f"{BPKM}tags"]
        assert "backend" in props[f"{BPKM}tags"]  # from components
        assert props[f"{BPKM}taskGroup"] == "Sprint 7"
        assert props[f"{BPKM}externalId"] == "PROJ-42"
        assert props[f"{BPKM}externalUrl"] == "https://mysite.atlassian.net/browse/PROJ-42"
        assert props[f"{BPKM}externalUuid"] == "10042"
        assert props[f"{BPKM}externalProvider"] == "jira"
        assert props[f"{BPKM}lastSyncedAt"] == "2026-03-19T10:00:00+00:00"

    def test_minimal_issue(self):
        """Issue with only required fields — no labels, components, sprint, etc."""
        issue = _make_issue(fields={
            "summary": "Minimal task",
            "status": {
                "name": "To Do",
                "statusCategory": {"key": "new"},
            },
        })
        props = fm.build_task_properties(issue)
        assert props["dcterms:title"] == "Minimal task"
        assert props[f"{BPKM}taskStatus"] == "todo"
        assert props[f"{BPKM}externalStatus"] == "To Do"
        assert f"{BPKM}priority" not in props
        assert f"{BPKM}dueDate" not in props
        assert f"{BPKM}tags" not in props
        assert f"{BPKM}taskGroup" not in props
        assert f"{BPKM}lastSyncedAt" in props

    def test_empty_labels_and_components(self):
        issue = _make_issue(fields={
            "summary": "No tags",
            "status": {"name": "Open", "statusCategory": {"key": "new"}},
            "labels": [],
            "components": [],
        })
        props = fm.build_task_properties(issue)
        assert f"{BPKM}tags" not in props

    def test_labels_as_strings(self):
        """Some Jira API responses return labels as plain strings."""
        issue = _make_issue(fields={
            "summary": "String labels",
            "status": {"name": "Open", "statusCategory": {"key": "new"}},
            "labels": ["alpha", "beta"],
        })
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}tags"] == ["alpha", "beta"]

    def test_issue_with_sprint(self):
        issue = _make_issue(fields={
            "summary": "Sprint task",
            "status": {"name": "Active", "statusCategory": {"key": "indeterminate"}},
            "sprint": {"name": "Sprint 12", "state": "active"},
        })
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}taskGroup"] == "Sprint 12"

    def test_issue_with_resolution_date(self):
        issue = _make_issue(fields={
            "summary": "Resolved task",
            "status": {"name": "Done", "statusCategory": {"key": "done"}},
            "resolutiondate": "2026-03-18T14:30:00.000+0000",
        })
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}completedDate"] == "2026-03-18"

    def test_no_resolution_date_omitted(self):
        issue = _make_issue(fields={
            "summary": "Open task",
            "status": {"name": "Open", "statusCategory": {"key": "new"}},
            "resolutiondate": None,
        })
        props = fm.build_task_properties(issue)
        assert f"{BPKM}completedDate" not in props

    def test_assignee_via_person_iri(self):
        issue = _make_issue()
        props = fm.build_task_properties(issue, person_iri="urn:person:bob")
        assert props[f"{BPKM}assignedTo"] == "urn:person:bob"

    def test_no_person_iri_omits_assignee(self):
        issue = _make_issue()
        props = fm.build_task_properties(issue)
        assert f"{BPKM}assignedTo" not in props

    def test_sync_time_default(self):
        """When sync_time is None, a timestamp is still generated."""
        issue = _make_issue()
        props = fm.build_task_properties(issue)
        assert f"{BPKM}lastSyncedAt" in props
        assert "T" in props[f"{BPKM}lastSyncedAt"]

    def test_sync_time_explicit(self):
        issue = _make_issue()
        props = fm.build_task_properties(
            issue, sync_time="2026-01-01T00:00:00Z"
        )
        assert props[f"{BPKM}lastSyncedAt"] == "2026-01-01T00:00:00Z"

    def test_last_synced_at_not_stripped(self):
        """lastSyncedAt is present even when other optional fields are stripped."""
        issue = _make_issue(fields={
            "summary": "Bare",
            "status": {"name": "New", "statusCategory": {"key": "new"}},
        })
        props = fm.build_task_properties(issue)
        assert f"{BPKM}lastSyncedAt" in props

    def test_external_url_constructed_from_self(self):
        issue = _make_issue(
            self="https://acme.atlassian.net/rest/api/3/issue/99",
            key="ACME-99",
        )
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}externalUrl"] == "https://acme.atlassian.net/browse/ACME-99"

    def test_external_uuid_is_string(self):
        issue = _make_issue(id=12345)
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}externalUuid"] == "12345"

    def test_status_new_maps_to_todo(self):
        issue = _make_issue(fields={
            "summary": "New task",
            "status": {"name": "Open", "statusCategory": {"key": "new"}},
        })
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}taskStatus"] == "todo"

    def test_status_done_maps_to_done(self):
        issue = _make_issue(fields={
            "summary": "Done task",
            "status": {"name": "Closed", "statusCategory": {"key": "done"}},
        })
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}taskStatus"] == "done"

    def test_missing_status_category_defaults_to_todo(self):
        """If statusCategory is missing entirely, defaults to 'todo'."""
        issue = _make_issue(fields={
            "summary": "No status",
            "status": {"name": "Unknown"},
        })
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}taskStatus"] == "todo"

    def test_components_appended_to_tags(self):
        issue = _make_issue(fields={
            "summary": "Tagged task",
            "status": {"name": "Open", "statusCategory": {"key": "new"}},
            "labels": [{"name": "feature"}],
            "components": [{"name": "api"}, {"name": "docs"}],
        })
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}tags"] == ["feature", "api", "docs"]

    def test_due_date_truncated_to_date(self):
        issue = _make_issue(fields={
            "summary": "Dated task",
            "status": {"name": "Open", "statusCategory": {"key": "new"}},
            "duedate": "2026-12-31T23:59:59.000+0000",
        })
        props = fm.build_task_properties(issue)
        assert props[f"{BPKM}dueDate"] == "2026-12-31"

    def test_no_sprint_omits_task_group(self):
        issue = _make_issue(fields={
            "summary": "No sprint",
            "status": {"name": "Open", "statusCategory": {"key": "new"}},
        })
        props = fm.build_task_properties(issue)
        assert f"{BPKM}taskGroup" not in props


# ===================================================================
# build_milestone_properties tests
# ===================================================================

class TestBuildMilestoneProperties:
    def test_epic_done_maps_to_completed(self):
        epic = _make_epic()
        props = fm.build_milestone_properties(
            epic, sync_time="2026-03-19T10:00:00+00:00"
        )
        assert props["dcterms:title"] == "Q2 Feature Epic"
        assert props[f"{BPKM}milestoneStatus"] == "completed"
        assert props[f"{BPKM}targetDate"] == "2026-06-30"
        assert props[f"{BPKM}externalId"] == "PROJ-100"
        assert props[f"{BPKM}externalUrl"] == "https://mysite.atlassian.net/browse/PROJ-100"
        assert props[f"{BPKM}externalProvider"] == "jira"
        assert props[f"{BPKM}lastSyncedAt"] == "2026-03-19T10:00:00+00:00"

    def test_epic_active_status(self):
        epic = _make_epic(fields={
            "summary": "Active Epic",
            "status": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}},
            "duedate": "2026-09-15",
        })
        props = fm.build_milestone_properties(epic)
        assert props[f"{BPKM}milestoneStatus"] == "active"

    def test_epic_new_status_maps_to_active(self):
        epic = _make_epic(fields={
            "summary": "New Epic",
            "status": {"name": "To Do", "statusCategory": {"key": "new"}},
        })
        props = fm.build_milestone_properties(epic)
        assert props[f"{BPKM}milestoneStatus"] == "active"

    def test_minimal_epic(self):
        epic = _make_epic(fields={
            "summary": "Bare Epic",
            "status": {"name": "Open", "statusCategory": {"key": "new"}},
        })
        props = fm.build_milestone_properties(epic)
        assert props["dcterms:title"] == "Bare Epic"
        assert props[f"{BPKM}milestoneStatus"] == "active"
        assert f"{BPKM}targetDate" not in props
        assert f"{BPKM}lastSyncedAt" in props

    def test_milestone_sync_time_default(self):
        epic = _make_epic()
        props = fm.build_milestone_properties(epic)
        assert f"{BPKM}lastSyncedAt" in props
        assert "T" in props[f"{BPKM}lastSyncedAt"]


# ===================================================================
# build_issue_patch tests (reverse mapping)
# ===================================================================

class TestBuildIssuePatch:
    def test_title_mapping(self):
        patch = fm.build_issue_patch({"dcterms:title": "Updated Title"})
        assert patch["summary"] == "Updated Title"

    def test_priority_mapping_critical(self):
        patch = fm.build_issue_patch({f"{BPKM}priority": "critical"})
        assert patch["priority"] == {"name": "Highest"}

    def test_priority_mapping_high(self):
        patch = fm.build_issue_patch({f"{BPKM}priority": "high"})
        assert patch["priority"] == {"name": "High"}

    def test_priority_mapping_medium(self):
        patch = fm.build_issue_patch({f"{BPKM}priority": "medium"})
        assert patch["priority"] == {"name": "Medium"}

    def test_priority_mapping_low(self):
        patch = fm.build_issue_patch({f"{BPKM}priority": "low"})
        assert patch["priority"] == {"name": "Low"}

    def test_empty_props_empty_result(self):
        patch = fm.build_issue_patch({})
        assert patch == {}

    def test_unknown_priority_skipped(self):
        patch = fm.build_issue_patch({f"{BPKM}priority": "nonexistent"})
        assert "priority" not in patch

    def test_no_status_in_v1_push(self):
        """Per D237, status transitions are NOT in v1 push."""
        patch = fm.build_issue_patch({f"{BPKM}taskStatus": "done"})
        assert "status" not in patch
        assert "transition" not in patch

    def test_title_and_priority_together(self):
        patch = fm.build_issue_patch({
            "dcterms:title": "New Name",
            f"{BPKM}priority": "high",
        })
        assert patch["summary"] == "New Name"
        assert patch["priority"] == {"name": "High"}


# ===================================================================
# REVERSE_STATUS_MAP tests
# ===================================================================

class TestReverseStatusMap:
    def test_todo_maps_to_new(self):
        assert fm.REVERSE_STATUS_MAP["todo"] == "new"

    def test_in_progress_maps_to_indeterminate(self):
        assert fm.REVERSE_STATUS_MAP["in-progress"] == "indeterminate"

    def test_done_maps_to_done(self):
        assert fm.REVERSE_STATUS_MAP["done"] == "done"

    def test_blocked_maps_to_indeterminate(self):
        assert fm.REVERSE_STATUS_MAP["blocked"] == "indeterminate"

    def test_cancelled_maps_to_done(self):
        assert fm.REVERSE_STATUS_MAP["cancelled"] == "done"

    def test_unknown_reverse_status_defaults_to_new(self):
        assert fm.reverse_status("nonexistent") == "new"


# ===================================================================
# REVERSE_PRIORITY_MAP tests
# ===================================================================

class TestReversePriorityMap:
    def test_critical_maps_to_highest(self):
        assert fm.REVERSE_PRIORITY_MAP["critical"] == "Highest"

    def test_high_maps_to_high(self):
        assert fm.REVERSE_PRIORITY_MAP["high"] == "High"

    def test_medium_maps_to_medium(self):
        assert fm.REVERSE_PRIORITY_MAP["medium"] == "Medium"

    def test_low_maps_to_low(self):
        assert fm.REVERSE_PRIORITY_MAP["low"] == "Low"

    def test_unknown_reverse_priority_returns_none(self):
        assert fm.reverse_priority("nonexistent") is None


# ===================================================================
# Round-trip consistency tests
# ===================================================================

class TestRoundTripConsistency:
    def test_status_roundtrip_new(self):
        """new → todo → new round-trips correctly."""
        bpkm_status = fm.STATUS_MAP["new"]
        jira_cat = fm.REVERSE_STATUS_MAP[bpkm_status]
        assert jira_cat == "new"

    def test_status_roundtrip_indeterminate(self):
        """indeterminate → in-progress → indeterminate round-trips."""
        bpkm_status = fm.STATUS_MAP["indeterminate"]
        jira_cat = fm.REVERSE_STATUS_MAP[bpkm_status]
        assert jira_cat == "indeterminate"

    def test_status_roundtrip_done(self):
        """done → done → done round-trips."""
        bpkm_status = fm.STATUS_MAP["done"]
        jira_cat = fm.REVERSE_STATUS_MAP[bpkm_status]
        assert jira_cat == "done"

    def test_priority_roundtrip_critical(self):
        """Highest → critical → Highest round-trips."""
        bpkm_prio = fm.PRIORITY_MAP["Highest"]
        jira_prio = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        assert jira_prio == "Highest"

    def test_priority_roundtrip_high(self):
        bpkm_prio = fm.PRIORITY_MAP["High"]
        jira_prio = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        assert jira_prio == "High"

    def test_priority_roundtrip_medium(self):
        bpkm_prio = fm.PRIORITY_MAP["Medium"]
        jira_prio = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        assert jira_prio == "Medium"

    def test_priority_roundtrip_low(self):
        bpkm_prio = fm.PRIORITY_MAP["Low"]
        jira_prio = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        assert jira_prio == "Low"

    def test_priority_lossy_blocker(self):
        """Blocker → critical → Highest (lossy — Blocker lost)."""
        bpkm_prio = fm.PRIORITY_MAP["Blocker"]
        jira_prio = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        # Lossy: Blocker maps to critical, which reverses to Highest (not Blocker)
        assert jira_prio == "Highest"

    def test_priority_lossy_lowest(self):
        """Lowest → low → Low (lossy — Lowest lost)."""
        bpkm_prio = fm.PRIORITY_MAP["Lowest"]
        jira_prio = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        assert jira_prio == "Low"
