"""Tests for Asana field mapper — all extraction paths and edge cases.

Runs with ``pytest --noconftest`` — no fixtures or conftest required.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path setup — import the apps/asana-sync/services package
# ---------------------------------------------------------------------------
_apps_dir = str(Path(__file__).resolve().parent.parent.parent / "apps" / "asana-sync")
if _apps_dir not in sys.path:
    sys.path.insert(0, _apps_dir)

from services.field_mapper import (
    BPKM,
    COMPLETED_STATUS_MAP,
    strip_html_tags,
    extract_body,
    extract_status,
    extract_priority,
    extract_story_points,
    extract_tags,
    extract_followers,
    extract_assignee,
    extract_section_name,
    detect_milestone,
    extract_due_date,
    extract_start_date,
    compute_task_slug,
    build_task_properties,
    reverse_status_mapping,
    reverse_priority_mapping,
    build_asana_patch,
    resolve_section_gid_for_status,
    _resolve_enum_option_gid,
)


# ---------------------------------------------------------------------------
# Helpers — build realistic Asana task dicts
# ---------------------------------------------------------------------------


def _make_task(
    gid: str = "1234567890",
    name: str = "Test Task",
    completed: bool = False,
    notes: str | None = None,
    html_notes: str | None = None,
    custom_fields: list[dict] | None = None,
    tags: list[dict] | None = None,
    assignee: dict | None = None,
    followers: list[dict] | None = None,
    memberships: list[dict] | None = None,
    due_on: str | None = None,
    due_at: str | None = None,
    start_on: str | None = None,
    start_at: str | None = None,
    permalink_url: str = "https://app.asana.com/0/project/1234567890",
    resource_subtype: str = "default_task",
    **extra,
) -> dict:
    """Build a realistic Asana task dict with sensible defaults."""
    task: dict = {
        "gid": gid,
        "name": name,
        "completed": completed,
        "permalink_url": permalink_url,
        "resource_subtype": resource_subtype,
    }
    if notes is not None:
        task["notes"] = notes
    if html_notes is not None:
        task["html_notes"] = html_notes
    if custom_fields is not None:
        task["custom_fields"] = custom_fields
    if tags is not None:
        task["tags"] = tags
    if assignee is not None:
        task["assignee"] = assignee
    if followers is not None:
        task["followers"] = followers
    if memberships is not None:
        task["memberships"] = memberships
    if due_on is not None:
        task["due_on"] = due_on
    if due_at is not None:
        task["due_at"] = due_at
    if start_on is not None:
        task["start_on"] = start_on
    if start_at is not None:
        task["start_at"] = start_at
    task.update(extra)
    return task


def _make_custom_field(
    gid: str,
    name: str = "Status",
    enum_value_name: str | None = None,
    number_value: float | None = None,
) -> dict:
    """Build a custom field dict."""
    cf: dict = {"gid": gid, "name": name}
    if enum_value_name is not None:
        cf["enum_value"] = {"gid": "ev_" + gid, "name": enum_value_name}
    else:
        cf["enum_value"] = None
    if number_value is not None:
        cf["number_value"] = number_value
    return cf


def _make_membership(section_name: str | None = None) -> dict:
    """Build a membership dict."""
    m: dict = {"project": {"gid": "proj_1", "name": "My Project"}}
    if section_name is not None:
        m["section"] = {"gid": "sec_1", "name": section_name}
    else:
        m["section"] = None
    return m


# =========================================================================
# strip_html_tags
# =========================================================================


class TestStripHtmlTags:
    def test_basic_tags(self):
        assert strip_html_tags("<p>Hello</p>") == "Hello"

    def test_nested_tags(self):
        assert strip_html_tags("<div><b>Bold</b> text</div>") == "Bold text"

    def test_no_tags(self):
        assert strip_html_tags("Plain text") == "Plain text"

    def test_empty_string(self):
        assert strip_html_tags("") == ""

    def test_self_closing_tags(self):
        assert strip_html_tags("Before<br/>After") == "BeforeAfter"


# =========================================================================
# extract_body
# =========================================================================


class TestExtractBody:
    def test_html_notes_with_markup(self):
        task = _make_task(html_notes="<p>Hello <b>world</b></p>")
        result = extract_body(task)
        assert result is not None
        # Should contain "Hello" and "world" — exact format depends on markdownify
        assert "Hello" in result
        assert "world" in result

    def test_plain_notes_fallback(self):
        task = _make_task(notes="Just plain text")
        result = extract_body(task)
        assert result == "Just plain text"

    def test_html_notes_preferred_over_plain(self):
        task = _make_task(html_notes="<p>HTML version</p>", notes="Plain version")
        result = extract_body(task)
        assert result is not None
        assert "HTML version" in result

    def test_empty_html_notes_falls_back_to_plain(self):
        task = _make_task(html_notes="", notes="Fallback text")
        result = extract_body(task)
        assert result == "Fallback text"

    def test_whitespace_only_html_notes_falls_back(self):
        task = _make_task(html_notes="   ", notes="Fallback")
        result = extract_body(task)
        assert result == "Fallback"

    def test_no_notes_returns_none(self):
        task = _make_task()
        result = extract_body(task)
        assert result is None

    def test_empty_plain_notes_returns_none(self):
        task = _make_task(notes="")
        result = extract_body(task)
        assert result is None

    def test_whitespace_only_notes_returns_none(self):
        task = _make_task(notes="   ")
        result = extract_body(task)
        assert result is None


# =========================================================================
# extract_status — completed_only mode
# =========================================================================


class TestExtractStatusCompletedOnly:
    def test_completed_true_returns_done(self):
        task = _make_task(completed=True)
        config = {"status_source": "completed_only"}
        assert extract_status(task, config) == "done"

    def test_completed_false_returns_todo(self):
        task = _make_task(completed=False)
        config = {"status_source": "completed_only"}
        assert extract_status(task, config) == "todo"


# =========================================================================
# extract_status — custom_field mode
# =========================================================================


class TestExtractStatusCustomField:
    def test_matching_gid_with_valid_enum(self):
        cf = _make_custom_field("cf_status", enum_value_name="In Progress")
        task = _make_task(completed=False, custom_fields=[cf])
        config = {
            "status_source": "custom_field",
            "status_field_gid": "cf_status",
            "status_mapping": {"In Progress": "in-progress", "Done": "done"},
        }
        assert extract_status(task, config) == "in-progress"

    def test_matching_gid_enum_value_done(self):
        cf = _make_custom_field("cf_status", enum_value_name="Done")
        task = _make_task(completed=True, custom_fields=[cf])
        config = {
            "status_source": "custom_field",
            "status_field_gid": "cf_status",
            "status_mapping": {"In Progress": "in-progress", "Done": "done"},
        }
        assert extract_status(task, config) == "done"

    def test_missing_gid_falls_back_to_completed(self):
        cf = _make_custom_field("cf_other", enum_value_name="In Progress")
        task = _make_task(completed=True, custom_fields=[cf])
        config = {
            "status_source": "custom_field",
            "status_field_gid": "cf_status",
            "status_mapping": {"In Progress": "in-progress"},
        }
        assert extract_status(task, config) == "done"

    def test_none_enum_value_falls_back_to_completed(self):
        cf = _make_custom_field("cf_status", enum_value_name=None)
        task = _make_task(completed=False, custom_fields=[cf])
        config = {
            "status_source": "custom_field",
            "status_field_gid": "cf_status",
            "status_mapping": {"In Progress": "in-progress"},
        }
        assert extract_status(task, config) == "todo"

    def test_enum_value_not_in_mapping_falls_back(self):
        cf = _make_custom_field("cf_status", enum_value_name="Unknown Status")
        task = _make_task(completed=True, custom_fields=[cf])
        config = {
            "status_source": "custom_field",
            "status_field_gid": "cf_status",
            "status_mapping": {"In Progress": "in-progress", "Done": "done"},
        }
        assert extract_status(task, config) == "done"

    def test_no_custom_fields_at_all_falls_back(self):
        task = _make_task(completed=False)
        config = {
            "status_source": "custom_field",
            "status_field_gid": "cf_status",
            "status_mapping": {},
        }
        assert extract_status(task, config) == "todo"

    def test_empty_custom_fields_list_falls_back(self):
        task = _make_task(completed=True, custom_fields=[])
        config = {
            "status_source": "custom_field",
            "status_field_gid": "cf_status",
            "status_mapping": {},
        }
        assert extract_status(task, config) == "done"

    def test_no_status_field_gid_in_config_falls_back(self):
        cf = _make_custom_field("cf_status", enum_value_name="In Progress")
        task = _make_task(completed=False, custom_fields=[cf])
        config = {
            "status_source": "custom_field",
            "status_mapping": {"In Progress": "in-progress"},
        }
        assert extract_status(task, config) == "todo"


# =========================================================================
# extract_status — section mode
# =========================================================================


class TestExtractStatusSection:
    def test_section_name_in_mapping(self):
        task = _make_task(completed=False)
        config = {
            "status_source": "section",
            "status_mapping": {"In Progress": "in-progress", "Done": "done"},
        }
        assert extract_status(task, config, section_name="In Progress") == "in-progress"

    def test_section_name_not_in_mapping_falls_back(self):
        task = _make_task(completed=True)
        config = {
            "status_source": "section",
            "status_mapping": {"In Progress": "in-progress"},
        }
        assert extract_status(task, config, section_name="Unknown Section") == "done"

    def test_empty_section_name_falls_back(self):
        task = _make_task(completed=False)
        config = {
            "status_source": "section",
            "status_mapping": {"In Progress": "in-progress"},
        }
        assert extract_status(task, config, section_name="") == "todo"

    def test_none_section_name_falls_back(self):
        task = _make_task(completed=True)
        config = {
            "status_source": "section",
            "status_mapping": {"In Progress": "in-progress"},
        }
        assert extract_status(task, config, section_name=None) == "done"


# =========================================================================
# extract_status — default / missing mode
# =========================================================================


class TestExtractStatusDefault:
    def test_missing_status_source_falls_back_completed_true(self):
        task = _make_task(completed=True)
        assert extract_status(task, {}) == "done"

    def test_missing_status_source_falls_back_completed_false(self):
        task = _make_task(completed=False)
        assert extract_status(task, {}) == "todo"

    def test_unknown_status_source_falls_back(self):
        task = _make_task(completed=True)
        config = {"status_source": "unknown_mode"}
        assert extract_status(task, config) == "done"


# =========================================================================
# extract_priority
# =========================================================================


class TestExtractPriority:
    def test_matching_gid_with_valid_enum(self):
        cf = _make_custom_field("cf_prio", enum_value_name="High")
        task = _make_task(custom_fields=[cf])
        config = {
            "priority_field_gid": "cf_prio",
            "priority_mapping": {"High": "high", "Low": "low"},
        }
        assert extract_priority(task, config) == "high"

    def test_enum_value_low(self):
        cf = _make_custom_field("cf_prio", enum_value_name="Low")
        task = _make_task(custom_fields=[cf])
        config = {
            "priority_field_gid": "cf_prio",
            "priority_mapping": {"High": "high", "Low": "low"},
        }
        assert extract_priority(task, config) == "low"

    def test_no_matching_gid_returns_none(self):
        cf = _make_custom_field("cf_other", enum_value_name="High")
        task = _make_task(custom_fields=[cf])
        config = {
            "priority_field_gid": "cf_prio",
            "priority_mapping": {"High": "high"},
        }
        assert extract_priority(task, config) is None

    def test_none_enum_value_returns_none(self):
        cf = _make_custom_field("cf_prio", enum_value_name=None)
        task = _make_task(custom_fields=[cf])
        config = {
            "priority_field_gid": "cf_prio",
            "priority_mapping": {"High": "high"},
        }
        assert extract_priority(task, config) is None

    def test_enum_not_in_mapping_returns_none(self):
        cf = _make_custom_field("cf_prio", enum_value_name="Urgent")
        task = _make_task(custom_fields=[cf])
        config = {
            "priority_field_gid": "cf_prio",
            "priority_mapping": {"High": "high", "Low": "low"},
        }
        assert extract_priority(task, config) is None

    def test_no_priority_field_gid_returns_none(self):
        cf = _make_custom_field("cf_prio", enum_value_name="High")
        task = _make_task(custom_fields=[cf])
        config = {"priority_mapping": {"High": "high"}}
        assert extract_priority(task, config) is None

    def test_no_custom_fields_returns_none(self):
        task = _make_task()
        config = {
            "priority_field_gid": "cf_prio",
            "priority_mapping": {"High": "high"},
        }
        assert extract_priority(task, config) is None

    def test_empty_custom_fields_returns_none(self):
        task = _make_task(custom_fields=[])
        config = {
            "priority_field_gid": "cf_prio",
            "priority_mapping": {"High": "high"},
        }
        assert extract_priority(task, config) is None


# =========================================================================
# extract_story_points
# =========================================================================


class TestExtractStoryPoints:
    def test_matching_gid_with_number(self):
        cf = _make_custom_field("cf_sp", number_value=5.0)
        task = _make_task(custom_fields=[cf])
        config = {"story_points_field_gid": "cf_sp"}
        assert extract_story_points(task, config) == 5.0

    def test_matching_gid_zero_value(self):
        cf = _make_custom_field("cf_sp", number_value=0.0)
        task = _make_task(custom_fields=[cf])
        config = {"story_points_field_gid": "cf_sp"}
        assert extract_story_points(task, config) == 0.0

    def test_no_matching_gid(self):
        cf = _make_custom_field("cf_other", number_value=5.0)
        task = _make_task(custom_fields=[cf])
        config = {"story_points_field_gid": "cf_sp"}
        assert extract_story_points(task, config) is None

    def test_no_story_points_field_gid(self):
        cf = _make_custom_field("cf_sp", number_value=5.0)
        task = _make_task(custom_fields=[cf])
        config = {}
        assert extract_story_points(task, config) is None

    def test_no_custom_fields(self):
        task = _make_task()
        config = {"story_points_field_gid": "cf_sp"}
        assert extract_story_points(task, config) is None

    def test_none_number_value(self):
        cf: dict = {"gid": "cf_sp", "name": "Story Points", "number_value": None}
        task = _make_task(custom_fields=[cf])
        config = {"story_points_field_gid": "cf_sp"}
        assert extract_story_points(task, config) is None

    def test_fractional_value(self):
        cf = _make_custom_field("cf_sp", number_value=3.5)
        task = _make_task(custom_fields=[cf])
        config = {"story_points_field_gid": "cf_sp"}
        assert extract_story_points(task, config) == 3.5


# =========================================================================
# extract_tags
# =========================================================================


class TestExtractTags:
    def test_multiple_tags(self):
        tags = [{"gid": "1", "name": "bug"}, {"gid": "2", "name": "urgent"}]
        task = _make_task(tags=tags)
        assert extract_tags(task) == "bug,urgent"

    def test_single_tag(self):
        tags = [{"gid": "1", "name": "feature"}]
        task = _make_task(tags=tags)
        assert extract_tags(task) == "feature"

    def test_empty_tags_list(self):
        task = _make_task(tags=[])
        assert extract_tags(task) is None

    def test_no_tags_key(self):
        task = _make_task()
        assert extract_tags(task) is None

    def test_tag_with_no_name_skipped(self):
        tags = [{"gid": "1", "name": "valid"}, {"gid": "2"}]
        task = _make_task(tags=tags)
        assert extract_tags(task) == "valid"

    def test_all_tags_without_name(self):
        tags = [{"gid": "1"}, {"gid": "2"}]
        task = _make_task(tags=tags)
        assert extract_tags(task) is None


# =========================================================================
# extract_followers
# =========================================================================


class TestExtractFollowers:
    def test_multiple_followers(self):
        followers = [
            {"gid": "1", "email": "alice@example.com", "name": "Alice"},
            {"gid": "2", "email": "bob@example.com", "name": "Bob"},
        ]
        task = _make_task(followers=followers)
        result = extract_followers(task)
        assert len(result) == 2
        assert result[0] == {"email": "alice@example.com", "name": "Alice"}
        assert result[1] == {"email": "bob@example.com", "name": "Bob"}

    def test_empty_followers(self):
        task = _make_task(followers=[])
        assert extract_followers(task) == []

    def test_no_followers_key(self):
        task = _make_task()
        assert extract_followers(task) == []

    def test_follower_without_email_skipped(self):
        followers = [
            {"gid": "1", "name": "NoEmail"},
            {"gid": "2", "email": "has@email.com", "name": "HasEmail"},
        ]
        task = _make_task(followers=followers)
        result = extract_followers(task)
        assert len(result) == 1
        assert result[0]["email"] == "has@email.com"


# =========================================================================
# extract_assignee
# =========================================================================


class TestExtractAssignee:
    def test_present_with_email(self):
        assignee = {"gid": "1", "email": "alice@example.com", "name": "Alice"}
        task = _make_task(assignee=assignee)
        result = extract_assignee(task)
        assert result == {"email": "alice@example.com", "name": "Alice"}

    def test_none_assignee(self):
        task = _make_task(assignee=None)
        assert extract_assignee(task) is None

    def test_no_assignee_key(self):
        task = _make_task()
        assert extract_assignee(task) is None

    def test_assignee_without_email(self):
        assignee = {"gid": "1", "name": "NoEmail"}
        task = _make_task(assignee=assignee)
        assert extract_assignee(task) is None

    def test_assignee_with_empty_email(self):
        assignee = {"gid": "1", "email": "", "name": "EmptyEmail"}
        task = _make_task(assignee=assignee)
        assert extract_assignee(task) is None


# =========================================================================
# extract_section_name
# =========================================================================


class TestExtractSectionName:
    def test_present(self):
        memberships = [_make_membership(section_name="In Progress")]
        task = _make_task(memberships=memberships)
        assert extract_section_name(task) == "In Progress"

    def test_empty_memberships(self):
        task = _make_task(memberships=[])
        assert extract_section_name(task) is None

    def test_no_memberships_key(self):
        task = _make_task()
        assert extract_section_name(task) is None

    def test_membership_without_section(self):
        memberships = [_make_membership(section_name=None)]
        task = _make_task(memberships=memberships)
        assert extract_section_name(task) is None

    def test_multiple_memberships_uses_first(self):
        memberships = [
            _make_membership(section_name="First"),
            _make_membership(section_name="Second"),
        ]
        task = _make_task(memberships=memberships)
        assert extract_section_name(task) == "First"


# =========================================================================
# detect_milestone
# =========================================================================


class TestDetectMilestone:
    def test_milestone_subtype(self):
        task = _make_task(resource_subtype="milestone")
        assert detect_milestone(task) is True

    def test_default_task_subtype(self):
        task = _make_task(resource_subtype="default_task")
        assert detect_milestone(task) is False

    def test_no_subtype(self):
        task = _make_task()
        task.pop("resource_subtype", None)
        assert detect_milestone(task) is False


# =========================================================================
# extract_due_date / extract_start_date
# =========================================================================


class TestExtractDueDate:
    def test_due_on(self):
        task = _make_task(due_on="2025-06-15")
        assert extract_due_date(task) == "2025-06-15"

    def test_due_at_truncated(self):
        task = _make_task(due_at="2025-06-15T14:30:00.000Z")
        assert extract_due_date(task) == "2025-06-15"

    def test_due_on_preferred_over_due_at(self):
        task = _make_task(due_on="2025-06-15", due_at="2025-06-16T14:30:00.000Z")
        assert extract_due_date(task) == "2025-06-15"

    def test_neither_present(self):
        task = _make_task()
        assert extract_due_date(task) is None


class TestExtractStartDate:
    def test_start_on(self):
        task = _make_task(start_on="2025-06-01")
        assert extract_start_date(task) == "2025-06-01"

    def test_start_at_truncated(self):
        task = _make_task(start_at="2025-06-01T09:00:00.000Z")
        assert extract_start_date(task) == "2025-06-01"

    def test_start_on_preferred_over_start_at(self):
        task = _make_task(start_on="2025-06-01", start_at="2025-06-02T09:00:00.000Z")
        assert extract_start_date(task) == "2025-06-01"

    def test_neither_present(self):
        task = _make_task()
        assert extract_start_date(task) is None


# =========================================================================
# compute_task_slug
# =========================================================================


class TestComputeTaskSlug:
    def test_deterministic_output(self):
        task = _make_task(gid="1234567890")
        slug = compute_task_slug(task)
        assert slug == "asana-1234567890"

    def test_different_gid_different_slug(self):
        t1 = _make_task(gid="111")
        t2 = _make_task(gid="222")
        assert compute_task_slug(t1) != compute_task_slug(t2)

    def test_same_gid_same_slug(self):
        t1 = _make_task(gid="999")
        t2 = _make_task(gid="999")
        assert compute_task_slug(t1) == compute_task_slug(t2)


# =========================================================================
# build_task_properties — full integration
# =========================================================================


class TestBuildTaskProperties:
    def test_full_happy_path(self):
        cf_status = _make_custom_field("cf_status", enum_value_name="In Progress")
        cf_prio = _make_custom_field("cf_prio", enum_value_name="High")
        cf_sp = _make_custom_field("cf_sp", number_value=5.0)
        task = _make_task(
            gid="42",
            name="My Task",
            completed=False,
            notes="Task description",
            custom_fields=[cf_status, cf_prio, cf_sp],
            tags=[{"gid": "t1", "name": "bug"}, {"gid": "t2", "name": "urgent"}],
            due_on="2025-06-15",
            start_on="2025-06-01",
            permalink_url="https://app.asana.com/0/proj/42",
        )
        config = {
            "status_source": "custom_field",
            "status_field_gid": "cf_status",
            "status_mapping": {"In Progress": "in-progress", "Done": "done"},
            "priority_field_gid": "cf_prio",
            "priority_mapping": {"High": "high", "Low": "low"},
            "story_points_field_gid": "cf_sp",
        }
        type_iri, props = build_task_properties(
            task, config, sync_time="2025-06-15T12:00:00+00:00"
        )

        assert type_iri == f"{BPKM}Task"
        assert props["dcterms:title"] == "My Task"
        assert props[f"{BPKM}taskStatus"] == "in-progress"
        assert props[f"{BPKM}priority"] == "high"
        assert props[f"{BPKM}dueDate"] == "2025-06-15"
        assert props[f"{BPKM}startDate"] == "2025-06-01"
        assert props[f"{BPKM}tags"] == "bug,urgent"
        assert props[f"{BPKM}storyPoints"] == 5.0
        assert props[f"{BPKM}externalUrl"] == "https://app.asana.com/0/proj/42"
        assert props[f"{BPKM}externalId"] == "42"
        assert props[f"{BPKM}externalUuid"] == "42"
        assert props[f"{BPKM}externalProvider"] == "asana"
        assert props[f"{BPKM}lastSyncedAt"] == "2025-06-15T12:00:00+00:00"
        assert "dcterms:description" in props

    def test_minimal_task(self):
        task = _make_task(gid="99", name="Minimal")
        config = {"status_source": "completed_only"}
        type_iri, props = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )

        assert type_iri == f"{BPKM}Task"
        assert props["dcterms:title"] == "Minimal"
        assert props[f"{BPKM}taskStatus"] == "todo"
        assert props[f"{BPKM}externalProvider"] == "asana"
        assert props[f"{BPKM}externalId"] == "99"
        # No priority, no tags, no dates — should be absent
        assert f"{BPKM}priority" not in props
        assert f"{BPKM}tags" not in props
        assert f"{BPKM}dueDate" not in props
        assert f"{BPKM}startDate" not in props
        assert f"{BPKM}storyPoints" not in props

    def test_milestone_detection_changes_type(self):
        task = _make_task(resource_subtype="milestone")
        config = {}
        type_iri, props = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )
        assert type_iri == f"{BPKM}Milestone"

    def test_default_task_type(self):
        task = _make_task(resource_subtype="default_task")
        config = {}
        type_iri, _ = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )
        assert type_iri == f"{BPKM}Task"

    def test_none_values_omitted(self):
        task = _make_task()
        config = {}
        _, props = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )
        # Spot check — priority should be absent (no priority field configured)
        assert f"{BPKM}priority" not in props
        assert f"{BPKM}storyPoints" not in props
        assert f"{BPKM}tags" not in props

    def test_section_based_status(self):
        task = _make_task(completed=False)
        config = {
            "status_source": "section",
            "status_mapping": {"Done": "done", "In Progress": "in-progress"},
        }
        _, props = build_task_properties(
            task, config, section_name="Done", sync_time="2025-01-01T00:00:00Z"
        )
        assert props[f"{BPKM}taskStatus"] == "done"

    def test_completed_only_status(self):
        task = _make_task(completed=True)
        config = {"status_source": "completed_only"}
        _, props = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )
        assert props[f"{BPKM}taskStatus"] == "done"

    def test_auto_sync_time(self):
        """sync_time defaults to current UTC when not provided."""
        task = _make_task()
        config = {}
        _, props = build_task_properties(task, config)
        # Should have a lastSyncedAt — just verify it exists and is a string
        assert f"{BPKM}lastSyncedAt" in props
        assert isinstance(props[f"{BPKM}lastSyncedAt"], str)

    def test_body_included_when_present(self):
        task = _make_task(notes="Some description text")
        config = {}
        _, props = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )
        assert props.get("dcterms:description") == "Some description text"

    def test_body_absent_when_empty(self):
        task = _make_task()
        config = {}
        _, props = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )
        assert "dcterms:description" not in props

    def test_empty_string_values_omitted(self):
        task = _make_task(gid="", name="", permalink_url="")
        config = {}
        _, props = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )
        # Empty string values should not be in the output
        assert f"{BPKM}externalId" not in props
        assert f"{BPKM}externalUrl" not in props

    def test_story_points_zero_included(self):
        """Story points of 0.0 should still be included (it's not None)."""
        cf_sp = _make_custom_field("cf_sp", number_value=0.0)
        task = _make_task(custom_fields=[cf_sp])
        config = {"story_points_field_gid": "cf_sp"}
        _, props = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )
        assert props[f"{BPKM}storyPoints"] == 0.0

    def test_multiple_custom_fields_correct_selection(self):
        """When multiple custom fields exist, the right one is matched by GID."""
        cf1 = _make_custom_field("cf_status", enum_value_name="Done")
        cf2 = _make_custom_field("cf_prio", enum_value_name="High")
        cf3 = _make_custom_field("cf_other", enum_value_name="Something")
        task = _make_task(custom_fields=[cf1, cf2, cf3])
        config = {
            "status_source": "custom_field",
            "status_field_gid": "cf_status",
            "status_mapping": {"Done": "done"},
            "priority_field_gid": "cf_prio",
            "priority_mapping": {"High": "high"},
        }
        _, props = build_task_properties(
            task, config, sync_time="2025-01-01T00:00:00Z"
        )
        assert props[f"{BPKM}taskStatus"] == "done"
        assert props[f"{BPKM}priority"] == "high"


# =========================================================================
# Reverse mapping — bpkm → Asana format (for push sync)
# =========================================================================


def _make_field_config(
    status_source: str = "custom_field",
    status_field_gid: str = "cf_status",
    status_mapping: dict | None = None,
    priority_field_gid: str = "cf_prio",
    priority_mapping: dict | None = None,
) -> dict:
    """Build a field_config dict for reverse mapping tests."""
    return {
        "status_source": status_source,
        "status_field_gid": status_field_gid,
        "status_mapping": status_mapping or {},
        "priority_field_gid": priority_field_gid,
        "priority_mapping": priority_mapping or {},
    }


def _make_discovered_enum_fields(
    fields: list[tuple[str, str, list[tuple[str, str]]]] | None = None,
) -> list[dict]:
    """Build a discovered_enum_fields list.

    Each tuple is (field_gid, field_name, [(option_name, option_gid), ...]).
    """
    if fields is None:
        return []
    result = []
    for field_gid, field_name, options in fields:
        result.append({
            "gid": field_gid,
            "name": field_name,
            "resource_subtype": "enum",
            "enum_options": [
                {"name": opt_name, "gid": opt_gid}
                for opt_name, opt_gid in options
            ],
        })
    return result


def _make_discovered_sections(
    sections: list[tuple[str, str]] | None = None,
) -> list[dict]:
    """Build a discovered_sections list.

    Each tuple is (section_gid, section_name).
    """
    if sections is None:
        return []
    return [{"gid": gid, "name": name} for gid, name in sections]


class TestReverseStatusMapping:
    """reverse_status_mapping — all three status_source modes."""

    def test_custom_field_mapped(self):
        config = _make_field_config(
            status_source="custom_field",
            status_mapping={"In Progress": "in_progress", "Done": "done"},
        )
        result = reverse_status_mapping("in_progress", config)
        assert result == {"type": "custom_field", "enum_option_name": "In Progress"}

    def test_custom_field_unknown(self):
        config = _make_field_config(
            status_source="custom_field",
            status_mapping={"Done": "done"},
        )
        result = reverse_status_mapping("unknown_status", config)
        assert result is None

    def test_section_mapped(self):
        config = _make_field_config(
            status_source="section",
            status_mapping={"To Do": "todo", "In Progress": "in_progress"},
        )
        result = reverse_status_mapping("todo", config)
        assert result == {"type": "section", "section_name": "To Do"}

    def test_section_unknown(self):
        config = _make_field_config(
            status_source="section",
            status_mapping={"Done": "done"},
        )
        result = reverse_status_mapping("unknown", config)
        assert result is None

    def test_completed_only_done(self):
        config = _make_field_config(status_source="completed_only")
        result = reverse_status_mapping("done", config)
        assert result == {"type": "completed", "value": True}

    def test_completed_only_todo(self):
        config = _make_field_config(status_source="completed_only")
        result = reverse_status_mapping("todo", config)
        assert result == {"type": "completed", "value": False}

    def test_completed_only_any_non_done(self):
        config = _make_field_config(status_source="completed_only")
        result = reverse_status_mapping("in_progress", config)
        assert result == {"type": "completed", "value": False}

    def test_unknown_status_source(self):
        config = _make_field_config(status_source="unknown_source")
        result = reverse_status_mapping("done", config)
        assert result is None

    def test_missing_status_source(self):
        config = {"status_mapping": {}}
        result = reverse_status_mapping("done", config)
        assert result is None


class TestReversePriorityMapping:
    """reverse_priority_mapping — invert priority_mapping dict."""

    def test_mapped(self):
        config = _make_field_config(
            priority_mapping={"High": "high", "Low": "low"},
        )
        result = reverse_priority_mapping("high", config)
        assert result == "High"

    def test_unknown(self):
        config = _make_field_config(
            priority_mapping={"High": "high"},
        )
        result = reverse_priority_mapping("unknown", config)
        assert result is None

    def test_empty_mapping(self):
        config = _make_field_config(priority_mapping={})
        result = reverse_priority_mapping("high", config)
        assert result is None

    def test_missing_mapping_key(self):
        config = {}
        result = reverse_priority_mapping("high", config)
        assert result is None


class TestResolveEnumOptionGid:
    """_resolve_enum_option_gid — GID lookup in discovered fields."""

    def test_found(self):
        fields = _make_discovered_enum_fields([
            ("cf_status", "Status", [("Done", "opt_done"), ("Todo", "opt_todo")]),
        ])
        assert _resolve_enum_option_gid("cf_status", "Done", fields) == "opt_done"

    def test_field_not_found(self):
        fields = _make_discovered_enum_fields([
            ("cf_other", "Other", [("Done", "opt_done")]),
        ])
        assert _resolve_enum_option_gid("cf_missing", "Done", fields) is None

    def test_option_not_found(self):
        fields = _make_discovered_enum_fields([
            ("cf_status", "Status", [("Done", "opt_done")]),
        ])
        assert _resolve_enum_option_gid("cf_status", "Missing", fields) is None

    def test_empty_fields_list(self):
        assert _resolve_enum_option_gid("cf_status", "Done", []) is None

    def test_multiple_fields(self):
        fields = _make_discovered_enum_fields([
            ("cf_status", "Status", [("Done", "opt_s_done")]),
            ("cf_prio", "Priority", [("High", "opt_p_high")]),
        ])
        assert _resolve_enum_option_gid("cf_prio", "High", fields) == "opt_p_high"


class TestBuildAsanaPatch:
    """build_asana_patch — full PATCH body assembly."""

    def test_status_custom_field(self):
        config = _make_field_config(
            status_source="custom_field",
            status_field_gid="cf_status",
            status_mapping={"In Progress": "in_progress"},
        )
        fields = _make_discovered_enum_fields([
            ("cf_status", "Status", [("In Progress", "opt_ip")]),
        ])
        props = {f"{BPKM}taskStatus": "in_progress"}
        patch = build_asana_patch(props, config, fields)
        assert patch == {"custom_fields": {"cf_status": "opt_ip"}}

    def test_priority(self):
        config = _make_field_config(
            status_source="completed_only",
            priority_field_gid="cf_prio",
            priority_mapping={"High": "high"},
        )
        fields = _make_discovered_enum_fields([
            ("cf_prio", "Priority", [("High", "opt_high")]),
        ])
        props = {f"{BPKM}priority": "high"}
        patch = build_asana_patch(props, config, fields)
        assert patch == {"custom_fields": {"cf_prio": "opt_high"}}

    def test_title(self):
        config = _make_field_config(status_source="completed_only")
        props = {"dcterms:title": "New Title"}
        patch = build_asana_patch(props, config, [])
        assert patch == {"name": "New Title"}

    def test_combined(self):
        config = _make_field_config(
            status_source="custom_field",
            status_field_gid="cf_status",
            status_mapping={"Done": "done"},
            priority_field_gid="cf_prio",
            priority_mapping={"High": "high"},
        )
        fields = _make_discovered_enum_fields([
            ("cf_status", "Status", [("Done", "opt_done")]),
            ("cf_prio", "Priority", [("High", "opt_high")]),
        ])
        props = {
            "dcterms:title": "Updated",
            f"{BPKM}taskStatus": "done",
            f"{BPKM}priority": "high",
        }
        patch = build_asana_patch(props, config, fields)
        assert patch["name"] == "Updated"
        assert patch["custom_fields"]["cf_status"] == "opt_done"
        assert patch["custom_fields"]["cf_prio"] == "opt_high"

    def test_empty(self):
        config = _make_field_config(status_source="completed_only")
        patch = build_asana_patch({}, config, [])
        assert patch == {}

    def test_unknown_enum_gid(self):
        """Field GID not in discovered_enum_fields → field omitted."""
        config = _make_field_config(
            status_source="custom_field",
            status_field_gid="cf_status",
            status_mapping={"Done": "done"},
        )
        # discovered_enum_fields has a different field GID
        fields = _make_discovered_enum_fields([
            ("cf_other", "Other", [("Done", "opt_done")]),
        ])
        props = {f"{BPKM}taskStatus": "done"}
        patch = build_asana_patch(props, config, fields)
        assert patch == {}

    def test_unknown_option_name(self):
        """Option name not in enum_options → field omitted."""
        config = _make_field_config(
            status_source="custom_field",
            status_field_gid="cf_status",
            status_mapping={"Done": "done"},
        )
        fields = _make_discovered_enum_fields([
            ("cf_status", "Status", [("Completed", "opt_comp")]),  # not "Done"
        ])
        props = {f"{BPKM}taskStatus": "done"}
        patch = build_asana_patch(props, config, fields)
        assert patch == {}

    def test_section_mode_excludes_status(self):
        """Section-based status NOT included in custom_fields patch."""
        config = _make_field_config(
            status_source="section",
            status_mapping={"To Do": "todo"},
        )
        fields = _make_discovered_enum_fields([])
        props = {f"{BPKM}taskStatus": "todo"}
        patch = build_asana_patch(props, config, fields)
        # Section mode status is handled by section moves, not PATCH
        assert "custom_fields" not in patch
        assert "completed" not in patch

    def test_completed_only_done(self):
        """completed_only mode → completed: True in patch."""
        config = _make_field_config(status_source="completed_only")
        props = {f"{BPKM}taskStatus": "done"}
        patch = build_asana_patch(props, config, [])
        assert patch == {"completed": True}

    def test_completed_only_todo(self):
        """completed_only mode → completed: False in patch."""
        config = _make_field_config(status_source="completed_only")
        props = {f"{BPKM}taskStatus": "todo"}
        patch = build_asana_patch(props, config, [])
        assert patch == {"completed": False}


class TestResolveSectionGidForStatus:
    """resolve_section_gid_for_status — bpkm status → section GID."""

    def test_found(self):
        config = _make_field_config(
            status_source="section",
            status_mapping={"To Do": "todo", "In Progress": "in_progress"},
        )
        sections = _make_discovered_sections([
            ("sec_todo", "To Do"),
            ("sec_ip", "In Progress"),
        ])
        result = resolve_section_gid_for_status("todo", config, sections)
        assert result == "sec_todo"

    def test_unknown_status(self):
        config = _make_field_config(
            status_source="section",
            status_mapping={"Done": "done"},
        )
        sections = _make_discovered_sections([("sec_done", "Done")])
        result = resolve_section_gid_for_status("unknown", config, sections)
        assert result is None

    def test_section_not_in_discovered(self):
        """Section name found in mapping but GID not in discovered_sections."""
        config = _make_field_config(
            status_source="section",
            status_mapping={"To Do": "todo"},
        )
        # discovered_sections has different names
        sections = _make_discovered_sections([("sec_ip", "In Progress")])
        result = resolve_section_gid_for_status("todo", config, sections)
        assert result is None

    def test_empty_sections_list(self):
        config = _make_field_config(
            status_source="section",
            status_mapping={"To Do": "todo"},
        )
        result = resolve_section_gid_for_status("todo", config, [])
        assert result is None

    def test_empty_mapping(self):
        config = _make_field_config(
            status_source="section",
            status_mapping={},
        )
        sections = _make_discovered_sections([("sec_todo", "To Do")])
        result = resolve_section_gid_for_status("todo", config, sections)
        assert result is None
