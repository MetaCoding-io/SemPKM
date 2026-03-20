"""Unit tests for Monday.com Sync field mapper.

Loads ``field_mapper.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package. All functions are pure —
no mocks needed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load field_mapper module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "monday-sync"
    / "services"
    / "field_mapper.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("monday_field_mapper", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["monday_field_mapper"] = mod
    spec.loader.exec_module(mod)
    return mod


fm = _load_module()

BPKM = fm.BPKM


# ---------------------------------------------------------------------------
# Fixtures — sample Monday.com item dicts
# ---------------------------------------------------------------------------


def _make_item(**overrides) -> dict:
    """Build a realistic Monday.com item dict with sensible defaults.

    Follows the shape returned by Monday.com GraphQL API items queries.
    """
    column_values = overrides.pop("column_values", [
        {
            "id": "status_col",
            "type": "status",
            "text": "Working on it",
            "value": json.dumps({"label": "Working on it", "index": 1}),
        },
        {
            "id": "priority_col",
            "type": "status",
            "text": "High",
            "value": json.dumps({"label": "High", "index": 2}),
        },
        {
            "id": "date_col",
            "type": "date",
            "text": "2026-04-15",
            "value": json.dumps({"date": "2026-04-15", "changed_at": "2026-03-01T10:00:00Z"}),
        },
        {
            "id": "people_col",
            "type": "people",
            "text": "Alice",
            "value": json.dumps({"personsAndTeams": [{"id": 12345, "kind": "person"}]}),
        },
        {
            "id": "text_col",
            "type": "text",
            "text": "Sprint 7",
            "value": '"Sprint 7"',
        },
        {
            "id": "numbers_col",
            "type": "numbers",
            "text": "42",
            "value": '"42"',
        },
        {
            "id": "tags_col",
            "type": "tags",
            "text": "bug, urgent",
            "value": json.dumps({"tag_ids": [101, 202, 303]}),
        },
        {
            "id": "dropdown_col",
            "type": "dropdown",
            "text": "Feature, Backend",
            "value": json.dumps({"ids": [1, 2], "labels": ["Feature", "Backend"]}),
        },
        {
            "id": "long_text_col",
            "type": "long_text",
            "text": "Detailed description here",
            "value": json.dumps({"text": "Detailed description here", "value": "<p>Detailed</p>"}),
        },
    ])

    base = {
        "id": "9876543",
        "name": "Fix the widget",
        "column_values": column_values,
    }
    base.update(overrides)
    return base


def _full_column_mapping() -> dict[str, str]:
    """Return a complete column mapping for testing."""
    return {
        "taskStatus": "status_col",
        "priority": "priority_col",
        "dueDate": "date_col",
        "assignedTo": "people_col",
        "taskGroup": "text_col",
        "estimatedEffort": "numbers_col",
        "tags": "tags_col",
        "dropdown": "dropdown_col",
        "description": "long_text_col",
    }


# ===================================================================
# DEFAULT_STATUS_MAP tests
# ===================================================================

class TestDefaultStatusMap:
    def test_done_maps_to_done(self):
        assert fm.DEFAULT_STATUS_MAP["Done"] == "done"

    def test_working_on_it_maps_to_in_progress(self):
        assert fm.DEFAULT_STATUS_MAP["Working on it"] == "in-progress"

    def test_stuck_maps_to_blocked(self):
        assert fm.DEFAULT_STATUS_MAP["Stuck"] == "blocked"

    def test_not_started_maps_to_todo(self):
        assert fm.DEFAULT_STATUS_MAP["Not Started"] == "todo"

    def test_empty_string_maps_to_todo(self):
        assert fm.DEFAULT_STATUS_MAP[""] == "todo"


# ===================================================================
# DEFAULT_PRIORITY_MAP tests
# ===================================================================

class TestDefaultPriorityMap:
    def test_critical_maps_to_critical(self):
        assert fm.DEFAULT_PRIORITY_MAP["Critical ⚨"] == "critical"

    def test_high_maps_to_high(self):
        assert fm.DEFAULT_PRIORITY_MAP["High"] == "high"

    def test_medium_maps_to_medium(self):
        assert fm.DEFAULT_PRIORITY_MAP["Medium"] == "medium"

    def test_low_maps_to_low(self):
        assert fm.DEFAULT_PRIORITY_MAP["Low"] == "low"

    def test_empty_string_maps_to_low(self):
        assert fm.DEFAULT_PRIORITY_MAP[""] == "low"


# ===================================================================
# _extract_status tests
# ===================================================================

class TestExtractStatus:
    def test_dict_with_label(self):
        val = json.dumps({"label": "Done", "index": 5})
        assert fm._extract_status(val) == "done"

    def test_dict_working_on_it(self):
        val = json.dumps({"label": "Working on it", "index": 1})
        assert fm._extract_status(val) == "in-progress"

    def test_dict_stuck(self):
        val = json.dumps({"label": "Stuck", "index": 2})
        assert fm._extract_status(val) == "blocked"

    def test_dict_not_started(self):
        val = json.dumps({"label": "Not Started", "index": 0})
        assert fm._extract_status(val) == "todo"

    def test_already_parsed_dict(self):
        val = {"label": "Done", "index": 5}
        assert fm._extract_status(val) == "done"

    def test_none_returns_todo(self):
        assert fm._extract_status(None) == "todo"

    def test_empty_string_returns_todo(self):
        assert fm._extract_status("") == "todo"

    def test_null_string_returns_todo(self):
        assert fm._extract_status("null") == "todo"

    def test_unknown_label_defaults_to_todo(self):
        val = json.dumps({"label": "Custom Status", "index": 99})
        assert fm._extract_status(val) == "todo"

    def test_custom_label_mapping(self):
        custom_map = {"Review": "in-progress", "Approved": "done", "": "todo"}
        val = json.dumps({"label": "Review", "index": 3})
        assert fm._extract_status(val, label_mapping=custom_map) == "in-progress"

    def test_empty_label_in_dict(self):
        val = json.dumps({"label": "", "index": 0})
        assert fm._extract_status(val) == "todo"

    def test_missing_label_key_defaults_to_todo(self):
        val = json.dumps({"index": 1})
        assert fm._extract_status(val) == "todo"


# ===================================================================
# _extract_priority tests
# ===================================================================

class TestExtractPriority:
    def test_high_priority(self):
        val = json.dumps({"label": "High", "index": 2})
        assert fm._extract_priority(val) == "high"

    def test_critical_priority(self):
        val = json.dumps({"label": "Critical ⚨", "index": 4})
        assert fm._extract_priority(val) == "critical"

    def test_medium_priority(self):
        val = json.dumps({"label": "Medium", "index": 1})
        assert fm._extract_priority(val) == "medium"

    def test_low_priority(self):
        val = json.dumps({"label": "Low", "index": 0})
        assert fm._extract_priority(val) == "low"

    def test_none_returns_none(self):
        assert fm._extract_priority(None) is None

    def test_empty_label_returns_none(self):
        val = json.dumps({"label": "", "index": 0})
        assert fm._extract_priority(val) is None

    def test_unknown_label_returns_none(self):
        val = json.dumps({"label": "Urgent", "index": 5})
        assert fm._extract_priority(val) is None

    def test_custom_mapping(self):
        custom = {"P0": "critical", "P1": "high"}
        val = json.dumps({"label": "P0", "index": 0})
        assert fm._extract_priority(val, label_mapping=custom) == "critical"

    def test_already_parsed_dict(self):
        val = {"label": "High", "index": 2}
        assert fm._extract_priority(val) == "high"

    def test_null_string_returns_none(self):
        assert fm._extract_priority("null") is None


# ===================================================================
# _extract_date tests
# ===================================================================

class TestExtractDate:
    def test_date_dict(self):
        val = json.dumps({"date": "2026-04-15", "changed_at": "2026-03-01T10:00:00Z"})
        assert fm._extract_date(val) == "2026-04-15"

    def test_date_only_key(self):
        val = json.dumps({"date": "2025-01-01"})
        assert fm._extract_date(val) == "2025-01-01"

    def test_already_parsed_dict(self):
        val = {"date": "2026-12-31", "changed_at": "..."}
        assert fm._extract_date(val) == "2026-12-31"

    def test_none_returns_none(self):
        assert fm._extract_date(None) is None

    def test_empty_string_returns_none(self):
        assert fm._extract_date("") is None

    def test_null_string_returns_none(self):
        assert fm._extract_date("null") is None

    def test_dict_without_date_key_returns_none(self):
        val = json.dumps({"changed_at": "2026-01-01T00:00:00Z"})
        assert fm._extract_date(val) is None

    def test_date_truncated_to_10_chars(self):
        val = json.dumps({"date": "2026-04-15T23:59:59"})
        assert fm._extract_date(val) == "2026-04-15"

    def test_plain_string_date(self):
        assert fm._extract_date('"2026-06-15"') == "2026-06-15"


# ===================================================================
# _extract_people tests
# ===================================================================

class TestExtractPeople:
    def test_single_person(self):
        val = json.dumps({"personsAndTeams": [{"id": 12345, "kind": "person"}]})
        assert fm._extract_people(val) == 12345

    def test_multiple_people_returns_first(self):
        val = json.dumps({"personsAndTeams": [
            {"id": 111, "kind": "person"},
            {"id": 222, "kind": "person"},
        ]})
        assert fm._extract_people(val) == 111

    def test_team_skipped_for_person(self):
        val = json.dumps({"personsAndTeams": [
            {"id": 999, "kind": "team"},
            {"id": 555, "kind": "person"},
        ]})
        assert fm._extract_people(val) == 555

    def test_team_only_fallback(self):
        """If only teams exist, fall back to first entry's ID."""
        val = json.dumps({"personsAndTeams": [{"id": 999, "kind": "team"}]})
        assert fm._extract_people(val) == 999

    def test_none_returns_none(self):
        assert fm._extract_people(None) is None

    def test_empty_persons_list(self):
        val = json.dumps({"personsAndTeams": []})
        assert fm._extract_people(val) is None

    def test_null_string_returns_none(self):
        assert fm._extract_people("null") is None

    def test_already_parsed_dict(self):
        val = {"personsAndTeams": [{"id": 42, "kind": "person"}]}
        assert fm._extract_people(val) == 42

    def test_missing_persons_key(self):
        val = json.dumps({"some_other": "data"})
        assert fm._extract_people(val) is None


# ===================================================================
# _extract_text tests
# ===================================================================

class TestExtractText:
    def test_plain_string(self):
        assert fm._extract_text('"Hello world"') == "Hello world"

    def test_dict_with_text_key(self):
        val = json.dumps({"text": "Content here", "value": "<p>Content</p>"})
        assert fm._extract_text(val) == "Content here"

    def test_dict_with_value_key_only(self):
        val = json.dumps({"value": "Fallback value"})
        assert fm._extract_text(val) == "Fallback value"

    def test_none_returns_none(self):
        assert fm._extract_text(None) is None

    def test_empty_string_returns_none(self):
        assert fm._extract_text("") is None

    def test_null_string_returns_none(self):
        assert fm._extract_text("null") is None

    def test_already_parsed_dict(self):
        val = {"text": "Direct dict", "value": "..."}
        assert fm._extract_text(val) == "Direct dict"

    def test_whitespace_only_returns_none(self):
        assert fm._extract_text('"   "') is None


# ===================================================================
# _extract_long_text tests
# ===================================================================

class TestExtractLongText:
    def test_long_text_with_text_key(self):
        val = json.dumps({"text": "Long content", "value": "<p>Long</p>"})
        assert fm._extract_long_text(val) == "Long content"

    def test_none_returns_none(self):
        assert fm._extract_long_text(None) is None

    def test_delegates_to_extract_text(self):
        """_extract_long_text delegates to _extract_text."""
        val = json.dumps({"text": "Delegated", "value": "..."})
        assert fm._extract_long_text(val) == fm._extract_text(val)


# ===================================================================
# _extract_numbers tests
# ===================================================================

class TestExtractNumbers:
    def test_plain_number_string(self):
        assert fm._extract_numbers('"42"') == "42"

    def test_dict_with_value(self):
        val = json.dumps({"value": "100"})
        assert fm._extract_numbers(val) == "100"

    def test_none_returns_none(self):
        assert fm._extract_numbers(None) is None

    def test_empty_string_returns_none(self):
        assert fm._extract_numbers("") is None

    def test_null_string_returns_none(self):
        assert fm._extract_numbers("null") is None

    def test_already_parsed_dict(self):
        val = {"value": "3.14"}
        assert fm._extract_numbers(val) == "3.14"

    def test_integer_value(self):
        val = json.dumps({"value": 99})
        assert fm._extract_numbers(val) == "99"


# ===================================================================
# _extract_tags tests
# ===================================================================

class TestExtractTags:
    def test_tag_ids_list(self):
        val = json.dumps({"tag_ids": [1, 2, 3]})
        assert fm._extract_tags(val) == [1, 2, 3]

    def test_empty_tag_ids(self):
        val = json.dumps({"tag_ids": []})
        assert fm._extract_tags(val) == []

    def test_none_returns_empty_list(self):
        assert fm._extract_tags(None) == []

    def test_null_string_returns_empty_list(self):
        assert fm._extract_tags("null") == []

    def test_already_parsed_dict(self):
        val = {"tag_ids": [10, 20]}
        assert fm._extract_tags(val) == [10, 20]

    def test_missing_tag_ids_key(self):
        val = json.dumps({"some_other": "data"})
        assert fm._extract_tags(val) == []


# ===================================================================
# _extract_dropdown tests
# ===================================================================

class TestExtractDropdown:
    def test_labels_list(self):
        val = json.dumps({"ids": [1, 2], "labels": ["Feature", "Backend"]})
        assert fm._extract_dropdown(val) == ["Feature", "Backend"]

    def test_empty_labels(self):
        val = json.dumps({"ids": [], "labels": []})
        assert fm._extract_dropdown(val) == []

    def test_none_returns_empty_list(self):
        assert fm._extract_dropdown(None) == []

    def test_null_string_returns_empty_list(self):
        assert fm._extract_dropdown("null") == []

    def test_already_parsed_dict(self):
        val = {"ids": [1], "labels": ["Alpha"]}
        assert fm._extract_dropdown(val) == ["Alpha"]

    def test_alternative_values_format(self):
        val = json.dumps({"values": [
            {"id": 1, "name": "Option A"},
            {"id": 2, "name": "Option B"},
        ]})
        assert fm._extract_dropdown(val) == ["Option A", "Option B"]

    def test_missing_labels_key(self):
        val = json.dumps({"ids": [1, 2]})
        assert fm._extract_dropdown(val) == []


# ===================================================================
# compute_slug tests
# ===================================================================

class TestComputeSlug:
    def test_deterministic(self):
        slug1 = fm.compute_slug("Fix widget", "12345")
        slug2 = fm.compute_slug("Fix widget", "12345")
        assert slug1 == slug2

    def test_different_names_different_slugs(self):
        slug_a = fm.compute_slug("Task A", "1")
        slug_b = fm.compute_slug("Task B", "1")
        assert slug_a != slug_b

    def test_different_ids_different_slugs(self):
        slug_1 = fm.compute_slug("Same name", "1")
        slug_2 = fm.compute_slug("Same name", "2")
        assert slug_1 != slug_2

    def test_prefix_is_monday(self):
        slug = fm.compute_slug("Test", "99")
        assert slug.startswith("monday-")

    def test_format_monday_prefix_16_hex(self):
        slug = fm.compute_slug("Test", "99")
        hex_part = slug[len("monday-"):]
        assert len(hex_part) == 16
        int(hex_part, 16)  # validates hex

    def test_integer_item_id(self):
        slug_str = fm.compute_slug("Test", "99")
        slug_int = fm.compute_slug("Test", 99)
        assert slug_str == slug_int


# ===================================================================
# build_external_url tests
# ===================================================================

class TestBuildExternalUrl:
    def test_basic_url(self):
        url = fm.build_external_url("1234", "5678")
        assert url == "https://monday.com/boards/1234/pulses/5678"

    def test_integer_ids(self):
        url = fm.build_external_url(1234, 5678)
        assert url == "https://monday.com/boards/1234/pulses/5678"


# ===================================================================
# build_task_properties tests
# ===================================================================

class TestBuildTaskProperties:
    def test_full_item_all_mapped_columns(self):
        item = _make_item()
        mapping = _full_column_mapping()
        props, assignee_id = fm.build_task_properties(
            item, mapping, board_id="111",
            sync_time="2026-03-19T10:00:00+00:00",
        )
        assert props["dcterms:title"] == "Fix the widget"
        assert props[f"{BPKM}taskStatus"] == "in-progress"
        assert props[f"{BPKM}externalStatus"] == "Working on it"
        assert props[f"{BPKM}priority"] == "high"
        assert props[f"{BPKM}dueDate"] == "2026-04-15"
        assert props[f"{BPKM}externalId"] == "9876543"
        assert props[f"{BPKM}externalProvider"] == "monday"
        assert props[f"{BPKM}externalUrl"] == "https://monday.com/boards/111/pulses/9876543"
        assert props[f"{BPKM}lastSyncedAt"] == "2026-03-19T10:00:00+00:00"
        assert assignee_id == 12345

    def test_partial_mapping(self):
        """Only map some columns — unmapped ones don't appear in output."""
        item = _make_item()
        mapping = {"taskStatus": "status_col", "dueDate": "date_col"}
        props, assignee_id = fm.build_task_properties(item, mapping)
        assert props[f"{BPKM}taskStatus"] == "in-progress"
        assert props[f"{BPKM}dueDate"] == "2026-04-15"
        assert f"{BPKM}priority" not in props
        assert assignee_id is None

    def test_empty_column_values(self):
        """Item with no column values — only base properties set."""
        item = _make_item(column_values=[])
        mapping = _full_column_mapping()
        props, assignee_id = fm.build_task_properties(item, mapping)
        assert props["dcterms:title"] == "Fix the widget"
        assert props[f"{BPKM}externalId"] == "9876543"
        assert props[f"{BPKM}externalProvider"] == "monday"
        assert f"{BPKM}taskStatus" not in props
        assert f"{BPKM}priority" not in props
        assert assignee_id is None

    def test_column_mapping_references_nonexistent_column(self):
        """Mapping refers to column ID not in item — gracefully skipped."""
        item = _make_item(column_values=[])
        mapping = {"taskStatus": "nonexistent_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert f"{BPKM}taskStatus" not in props

    def test_custom_status_label_mapping(self):
        """User provides custom status label mapping."""
        item = _make_item(column_values=[{
            "id": "status_col",
            "type": "status",
            "text": "In Review",
            "value": json.dumps({"label": "In Review", "index": 3}),
        }])
        custom_status = {"In Review": "in-progress", "Shipped": "done", "": "todo"}
        props, _ = fm.build_task_properties(
            item, {"taskStatus": "status_col"},
            status_label_mapping=custom_status,
        )
        assert props[f"{BPKM}taskStatus"] == "in-progress"

    def test_custom_priority_label_mapping(self):
        """User provides custom priority label mapping."""
        item = _make_item(column_values=[{
            "id": "priority_col",
            "type": "status",
            "text": "P0",
            "value": json.dumps({"label": "P0", "index": 0}),
        }])
        custom_priority = {"P0": "critical", "P1": "high", "P2": "medium"}
        props, _ = fm.build_task_properties(
            item, {"priority": "priority_col"},
            priority_label_mapping=custom_priority,
        )
        assert props[f"{BPKM}priority"] == "critical"

    def test_null_column_value(self):
        """Column value is null JSON — extractors handle gracefully."""
        item = _make_item(column_values=[{
            "id": "status_col",
            "type": "status",
            "text": "",
            "value": None,
        }])
        props, _ = fm.build_task_properties(
            item, {"taskStatus": "status_col"},
        )
        # None value → default status from empty label
        assert props[f"{BPKM}taskStatus"] == "todo"

    def test_sync_time_default(self):
        """When sync_time is None, a timestamp is still generated."""
        item = _make_item(column_values=[])
        props, _ = fm.build_task_properties(item, {})
        assert f"{BPKM}lastSyncedAt" in props
        assert "T" in props[f"{BPKM}lastSyncedAt"]

    def test_sync_time_explicit(self):
        item = _make_item(column_values=[])
        props, _ = fm.build_task_properties(
            item, {}, sync_time="2026-01-01T00:00:00Z"
        )
        assert props[f"{BPKM}lastSyncedAt"] == "2026-01-01T00:00:00Z"

    def test_last_synced_at_never_stripped(self):
        """lastSyncedAt is present even when other optional fields are stripped."""
        item = _make_item(column_values=[])
        props, _ = fm.build_task_properties(item, {})
        assert f"{BPKM}lastSyncedAt" in props

    def test_external_url_with_board_id(self):
        item = _make_item()
        props, _ = fm.build_task_properties(
            item, {}, board_id="555"
        )
        assert props[f"{BPKM}externalUrl"] == "https://monday.com/boards/555/pulses/9876543"

    def test_external_url_without_board_id(self):
        item = _make_item()
        props, _ = fm.build_task_properties(item, {})
        assert f"{BPKM}externalUrl" not in props

    def test_assignee_returned_separately(self):
        """Person ID is returned as second element, not in props."""
        item = _make_item()
        mapping = {"assignedTo": "people_col"}
        props, assignee_id = fm.build_task_properties(item, mapping)
        assert assignee_id == 12345
        assert f"{BPKM}assignedTo" not in props

    def test_tags_extraction(self):
        item = _make_item()
        mapping = {"tags": "tags_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert props[f"{BPKM}tags"] == [101, 202, 303]

    def test_dropdown_extraction(self):
        item = _make_item()
        mapping = {"dropdown": "dropdown_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert props[f"{BPKM}tags"] == ["Feature", "Backend"]

    def test_description_extraction(self):
        item = _make_item()
        mapping = {"description": "long_text_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert props[f"{BPKM}description"] == "Detailed description here"

    def test_estimated_effort_extraction(self):
        item = _make_item()
        mapping = {"estimatedEffort": "numbers_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert props[f"{BPKM}estimatedEffort"] == "42"

    def test_task_group_extraction(self):
        item = _make_item()
        mapping = {"taskGroup": "text_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert props[f"{BPKM}taskGroup"] == "Sprint 7"

    def test_none_values_stripped_from_output(self):
        """Properties with None values are omitted from output."""
        item = _make_item(column_values=[{
            "id": "date_col",
            "type": "date",
            "text": "",
            "value": None,
        }])
        props, _ = fm.build_task_properties(item, {"dueDate": "date_col"})
        assert f"{BPKM}dueDate" not in props

    def test_empty_list_stripped_from_output(self):
        """Properties with empty list values are omitted from output."""
        item = _make_item(column_values=[{
            "id": "tags_col",
            "type": "tags",
            "text": "",
            "value": json.dumps({"tag_ids": []}),
        }])
        props, _ = fm.build_task_properties(item, {"tags": "tags_col"})
        assert f"{BPKM}tags" not in props


# ===================================================================
# build_reverse_column_values tests
# ===================================================================

class TestBuildReverseColumnValues:
    def test_status_reverse(self):
        props = {f"{BPKM}taskStatus": "done"}
        mapping = {"taskStatus": "status_col"}
        result = fm.build_reverse_column_values(props, mapping)
        assert "status_col" in result
        parsed = json.loads(result["status_col"])
        assert parsed == {"label": "Done"}

    def test_status_reverse_in_progress(self):
        props = {f"{BPKM}taskStatus": "in-progress"}
        mapping = {"taskStatus": "status_col"}
        result = fm.build_reverse_column_values(props, mapping)
        parsed = json.loads(result["status_col"])
        assert parsed == {"label": "Working on it"}

    def test_status_reverse_blocked(self):
        props = {f"{BPKM}taskStatus": "blocked"}
        mapping = {"taskStatus": "status_col"}
        result = fm.build_reverse_column_values(props, mapping)
        parsed = json.loads(result["status_col"])
        assert parsed == {"label": "Stuck"}

    def test_priority_reverse(self):
        props = {f"{BPKM}priority": "high"}
        mapping = {"priority": "priority_col"}
        result = fm.build_reverse_column_values(props, mapping)
        parsed = json.loads(result["priority_col"])
        assert parsed == {"label": "High"}

    def test_date_reverse(self):
        props = {f"{BPKM}dueDate": "2026-04-15"}
        mapping = {"dueDate": "date_col"}
        result = fm.build_reverse_column_values(props, mapping)
        parsed = json.loads(result["date_col"])
        assert parsed == {"date": "2026-04-15"}

    def test_text_reverse(self):
        props = {f"{BPKM}taskGroup": "Sprint 7"}
        mapping = {"taskGroup": "text_col"}
        result = fm.build_reverse_column_values(props, mapping)
        assert result["text_col"] == "Sprint 7"

    def test_numbers_reverse(self):
        props = {f"{BPKM}estimatedEffort": "42"}
        mapping = {"estimatedEffort": "numbers_col"}
        result = fm.build_reverse_column_values(props, mapping)
        assert result["numbers_col"] == "42"

    def test_people_reverse(self):
        props = {f"{BPKM}assignedTo": 12345}
        mapping = {"assignedTo": "people_col"}
        result = fm.build_reverse_column_values(props, mapping)
        parsed = json.loads(result["people_col"])
        assert parsed == {"personsAndTeams": [{"id": 12345, "kind": "person"}]}

    def test_people_reverse_string_id(self):
        props = {f"{BPKM}assignedTo": "67890"}
        mapping = {"assignedTo": "people_col"}
        result = fm.build_reverse_column_values(props, mapping)
        parsed = json.loads(result["people_col"])
        assert parsed["personsAndTeams"][0]["id"] == 67890

    def test_description_reverse(self):
        props = {f"{BPKM}description": "Task details"}
        mapping = {"description": "desc_col"}
        result = fm.build_reverse_column_values(props, mapping)
        assert result["desc_col"] == "Task details"

    def test_skips_unmapped_properties(self):
        props = {
            f"{BPKM}taskStatus": "done",
            f"{BPKM}priority": "high",
        }
        # Only status is mapped, priority is not
        mapping = {"taskStatus": "status_col"}
        result = fm.build_reverse_column_values(props, mapping)
        assert "status_col" in result
        assert len(result) == 1

    def test_empty_properties_returns_empty(self):
        result = fm.build_reverse_column_values({}, {"taskStatus": "col1"})
        assert result == {}

    def test_empty_mapping_returns_empty(self):
        props = {f"{BPKM}taskStatus": "done"}
        result = fm.build_reverse_column_values(props, {})
        assert result == {}

    def test_custom_reverse_status_mapping(self):
        custom_reverse = {"done": "Shipped", "in-progress": "Developing"}
        props = {f"{BPKM}taskStatus": "done"}
        mapping = {"taskStatus": "status_col"}
        result = fm.build_reverse_column_values(
            props, mapping, reverse_status_mapping=custom_reverse
        )
        parsed = json.loads(result["status_col"])
        assert parsed == {"label": "Shipped"}

    def test_custom_reverse_priority_mapping(self):
        custom_reverse = {"critical": "P0", "high": "P1"}
        props = {f"{BPKM}priority": "critical"}
        mapping = {"priority": "priority_col"}
        result = fm.build_reverse_column_values(
            props, mapping, reverse_priority_mapping=custom_reverse
        )
        parsed = json.loads(result["priority_col"])
        assert parsed == {"label": "P0"}

    def test_title_mapping_skipped(self):
        """Title is set via item name, not column values — should be skipped."""
        props = {"dcterms:title": "My Task"}
        mapping = {"title": "name_col"}
        result = fm.build_reverse_column_values(props, mapping)
        assert result == {}

    def test_none_property_value_skipped(self):
        props = {f"{BPKM}taskStatus": None}
        mapping = {"taskStatus": "status_col"}
        result = fm.build_reverse_column_values(props, mapping)
        assert result == {}


# ===================================================================
# Round-trip consistency tests
# ===================================================================

class TestRoundTripConsistency:
    def test_status_roundtrip_done(self):
        """Done → done → Done round-trips correctly."""
        bpkm_status = fm.DEFAULT_STATUS_MAP["Done"]
        monday_label = fm.REVERSE_STATUS_MAP[bpkm_status]
        assert monday_label == "Done"

    def test_status_roundtrip_working_on_it(self):
        """Working on it → in-progress → Working on it round-trips."""
        bpkm_status = fm.DEFAULT_STATUS_MAP["Working on it"]
        monday_label = fm.REVERSE_STATUS_MAP[bpkm_status]
        assert monday_label == "Working on it"

    def test_status_roundtrip_stuck(self):
        """Stuck → blocked → Stuck round-trips."""
        bpkm_status = fm.DEFAULT_STATUS_MAP["Stuck"]
        monday_label = fm.REVERSE_STATUS_MAP[bpkm_status]
        assert monday_label == "Stuck"

    def test_status_roundtrip_not_started(self):
        """Not Started → todo → Not Started round-trips."""
        bpkm_status = fm.DEFAULT_STATUS_MAP["Not Started"]
        monday_label = fm.REVERSE_STATUS_MAP[bpkm_status]
        assert monday_label == "Not Started"

    def test_priority_roundtrip_critical(self):
        """Critical ⚨ → critical → Critical ⚨ round-trips."""
        bpkm_prio = fm.DEFAULT_PRIORITY_MAP["Critical ⚨"]
        monday_label = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        assert monday_label == "Critical ⚨"

    def test_priority_roundtrip_high(self):
        bpkm_prio = fm.DEFAULT_PRIORITY_MAP["High"]
        monday_label = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        assert monday_label == "High"

    def test_priority_roundtrip_medium(self):
        bpkm_prio = fm.DEFAULT_PRIORITY_MAP["Medium"]
        monday_label = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        assert monday_label == "Medium"

    def test_priority_roundtrip_low(self):
        bpkm_prio = fm.DEFAULT_PRIORITY_MAP["Low"]
        monday_label = fm.REVERSE_PRIORITY_MAP[bpkm_prio]
        assert monday_label == "Low"

    def test_full_build_reverse_roundtrip(self):
        """build_task_properties → build_reverse_column_values preserves key data."""
        item = _make_item()
        mapping = {
            "taskStatus": "status_col",
            "priority": "priority_col",
            "dueDate": "date_col",
        }
        props, _ = fm.build_task_properties(
            item, mapping, sync_time="2026-03-19T10:00:00Z"
        )

        reverse = fm.build_reverse_column_values(props, mapping)

        # Status should round-trip
        status_parsed = json.loads(reverse["status_col"])
        assert status_parsed == {"label": "Working on it"}

        # Priority should round-trip
        priority_parsed = json.loads(reverse["priority_col"])
        assert priority_parsed == {"label": "High"}

        # Date should round-trip
        date_parsed = json.loads(reverse["date_col"])
        assert date_parsed == {"date": "2026-04-15"}


# ===================================================================
# REVERSE_STATUS_MAP tests
# ===================================================================

class TestReverseStatusMap:
    def test_todo_maps_to_not_started(self):
        assert fm.REVERSE_STATUS_MAP["todo"] == "Not Started"

    def test_in_progress_maps_to_working_on_it(self):
        assert fm.REVERSE_STATUS_MAP["in-progress"] == "Working on it"

    def test_done_maps_to_done(self):
        assert fm.REVERSE_STATUS_MAP["done"] == "Done"

    def test_blocked_maps_to_stuck(self):
        assert fm.REVERSE_STATUS_MAP["blocked"] == "Stuck"

    def test_cancelled_maps_to_done(self):
        assert fm.REVERSE_STATUS_MAP["cancelled"] == "Done"


# ===================================================================
# REVERSE_PRIORITY_MAP tests
# ===================================================================

class TestReversePriorityMap:
    def test_critical_maps_to_critical_emoji(self):
        assert fm.REVERSE_PRIORITY_MAP["critical"] == "Critical ⚨"

    def test_high_maps_to_high(self):
        assert fm.REVERSE_PRIORITY_MAP["high"] == "High"

    def test_medium_maps_to_medium(self):
        assert fm.REVERSE_PRIORITY_MAP["medium"] == "Medium"

    def test_low_maps_to_low(self):
        assert fm.REVERSE_PRIORITY_MAP["low"] == "Low"


# ===================================================================
# _parse_col_value tests
# ===================================================================

class TestParseColValue:
    def test_none(self):
        assert fm._parse_col_value(None) is None

    def test_empty_string(self):
        assert fm._parse_col_value("") is None

    def test_null_string(self):
        assert fm._parse_col_value("null") is None

    def test_json_dict(self):
        result = fm._parse_col_value('{"key": "val"}')
        assert result == {"key": "val"}

    def test_already_dict(self):
        d = {"key": "val"}
        assert fm._parse_col_value(d) is d

    def test_plain_text(self):
        result = fm._parse_col_value("not json at all {")
        assert result == "not json at all {"

    def test_json_string(self):
        result = fm._parse_col_value('"hello"')
        assert result == "hello"


# ===================================================================
# Edge case tests
# ===================================================================

class TestEdgeCases:
    def test_item_with_no_column_values_key(self):
        """Item dict missing column_values entirely."""
        item = {"id": "1", "name": "No columns"}
        props, assignee = fm.build_task_properties(item, {"taskStatus": "x"})
        assert props["dcterms:title"] == "No columns"
        assert assignee is None

    def test_column_value_with_empty_value_field(self):
        """Column has value='' (empty string) — should handle gracefully."""
        item = _make_item(column_values=[{
            "id": "status_col",
            "type": "status",
            "text": "",
            "value": "",
        }])
        props, _ = fm.build_task_properties(
            item, {"taskStatus": "status_col"}
        )
        assert props[f"{BPKM}taskStatus"] == "todo"

    def test_malformed_json_value_handled(self):
        """Column value is broken JSON — _parse_col_value returns raw string."""
        item = _make_item(column_values=[{
            "id": "text_col",
            "type": "text",
            "text": "fallback",
            "value": "{broken json",
        }])
        props, _ = fm.build_task_properties(
            item, {"taskGroup": "text_col"}
        )
        # The raw string "{broken json" is returned by _parse_col_value,
        # and _extract_text treats it as a plain string
        assert props[f"{BPKM}taskGroup"] == "{broken json"

    def test_multiple_column_mapping_entries(self):
        """Multiple bpkm properties mapped simultaneously."""
        item = _make_item()
        mapping = {
            "taskStatus": "status_col",
            "dueDate": "date_col",
            "tags": "tags_col",
        }
        props, _ = fm.build_task_properties(item, mapping)
        assert f"{BPKM}taskStatus" in props
        assert f"{BPKM}dueDate" in props
        assert f"{BPKM}tags" in props


# ===================================================================
# _extract_dependency tests
# ===================================================================

class TestExtractDependency:
    def test_extract_dependency_normal(self):
        val = json.dumps({"linkedPulseIds": [{"linkedPulseId": 123}]})
        assert fm._extract_dependency(val) == [123]

    def test_extract_dependency_multiple(self):
        val = json.dumps({"linkedPulseIds": [
            {"linkedPulseId": 100},
            {"linkedPulseId": 200},
            {"linkedPulseId": 300},
        ]})
        assert fm._extract_dependency(val) == [100, 200, 300]

    def test_extract_dependency_empty_list(self):
        val = json.dumps({"linkedPulseIds": []})
        assert fm._extract_dependency(val) == []

    def test_extract_dependency_none(self):
        assert fm._extract_dependency(None) == []

    def test_extract_dependency_missing_key(self):
        val = json.dumps({})
        assert fm._extract_dependency(val) == []

    def test_extract_dependency_malformed_entry(self):
        val = json.dumps({"linkedPulseIds": [{"foo": 1}]})
        assert fm._extract_dependency(val) == []

    def test_extract_dependency_mixed_valid_invalid(self):
        val = json.dumps({"linkedPulseIds": [
            {"linkedPulseId": 111},
            {"badKey": 999},
            {"linkedPulseId": 222},
        ]})
        assert fm._extract_dependency(val) == [111, 222]

    def test_extract_dependency_string_value(self):
        """JSON string wrapping — common for Monday.com column values."""
        val = '{"linkedPulseIds": [{"linkedPulseId": 456}]}'
        assert fm._extract_dependency(val) == [456]

    def test_extract_dependency_already_parsed_dict(self):
        val = {"linkedPulseIds": [{"linkedPulseId": 789}]}
        assert fm._extract_dependency(val) == [789]

    def test_extract_dependency_null_string(self):
        assert fm._extract_dependency("null") == []

    def test_extract_dependency_empty_string(self):
        assert fm._extract_dependency("") == []

    def test_extract_dependency_non_dict_linked_pulse_ids(self):
        """linkedPulseIds is not a list — should return empty."""
        val = json.dumps({"linkedPulseIds": "not a list"})
        assert fm._extract_dependency(val) == []

    def test_extract_dependency_registered_in_extractors(self):
        """dependency type is registered in _EXTRACTORS."""
        assert "dependency" in fm._EXTRACTORS
        assert fm._EXTRACTORS["dependency"] is fm._extract_dependency


# ===================================================================
# build_task_properties — dependency column tests
# ===================================================================

class TestBuildTaskPropertiesWithDependency:
    def test_dependency_column_stores_item_ids(self):
        """Dependency column mapped → _dependency_item_ids in output."""
        item = _make_item(column_values=[{
            "id": "dep_col",
            "type": "dependency",
            "text": "",
            "value": json.dumps({"linkedPulseIds": [{"linkedPulseId": 42}]}),
        }])
        mapping = {"dependency": "dep_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert props["_dependency_item_ids"] == [42]

    def test_dependency_item_ids_not_in_bpkm_namespace(self):
        """_dependency_item_ids is a temp key, not under BPKM namespace."""
        item = _make_item(column_values=[{
            "id": "dep_col",
            "type": "dependency",
            "text": "",
            "value": json.dumps({"linkedPulseIds": [{"linkedPulseId": 99}]}),
        }])
        mapping = {"dependency": "dep_col"}
        props, _ = fm.build_task_properties(item, mapping)
        # No BPKM key should contain "dependency"
        bpkm_dep_keys = [k for k in props if BPKM in k and "depend" in k.lower()]
        assert bpkm_dep_keys == []
        assert "_dependency_item_ids" in props

    def test_dependency_empty_not_stored(self):
        """Empty dependency list → no _dependency_item_ids key."""
        item = _make_item(column_values=[{
            "id": "dep_col",
            "type": "dependency",
            "text": "",
            "value": json.dumps({"linkedPulseIds": []}),
        }])
        mapping = {"dependency": "dep_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert "_dependency_item_ids" not in props

    def test_dependency_multiple_ids(self):
        """Multiple dependency IDs are stored."""
        item = _make_item(column_values=[{
            "id": "dep_col",
            "type": "dependency",
            "text": "",
            "value": json.dumps({"linkedPulseIds": [
                {"linkedPulseId": 10},
                {"linkedPulseId": 20},
            ]}),
        }])
        mapping = {"dependency": "dep_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert props["_dependency_item_ids"] == [10, 20]

    def test_dependency_coexists_with_other_properties(self):
        """Dependency column works alongside other mapped columns."""
        item = _make_item(column_values=[
            {
                "id": "status_col", "type": "status", "text": "Done",
                "value": json.dumps({"label": "Done", "index": 5}),
            },
            {
                "id": "dep_col", "type": "dependency", "text": "",
                "value": json.dumps({"linkedPulseIds": [{"linkedPulseId": 55}]}),
            },
        ])
        mapping = {"taskStatus": "status_col", "dependency": "dep_col"}
        props, _ = fm.build_task_properties(item, mapping)
        assert props[f"{BPKM}taskStatus"] == "done"
        assert props["_dependency_item_ids"] == [55]
