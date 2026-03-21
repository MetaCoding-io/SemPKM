"""Unit tests for Todoist field mapper.

Loads ``field_mapper.py`` from the apps directory using importlib. All
functions are pure — no mocking needed for the mapping logic itself.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "todoist-sync"
)
_SERVICES_DIR = _APPS_DIR / "services"
_AUTH_PATH = _SERVICES_DIR / "auth.py"
_MAPPER_PATH = _SERVICES_DIR / "field_mapper.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Set up pseudo-package for relative imports
pkg_name = "todoist_sync_services_fm"
pkg = types.ModuleType(pkg_name)
pkg.__path__ = [str(_SERVICES_DIR)]
pkg.__package__ = pkg_name
sys.modules[pkg_name] = pkg

auth = _load_module(f"{pkg_name}.auth", _AUTH_PATH)
sys.modules[f"{pkg_name}.auth"] = auth

mapper = _load_module(f"{pkg_name}.field_mapper", _MAPPER_PATH)

BPKM = mapper.BPKM
FIXED_SYNC_TIME = "2026-03-19T12:00:00+00:00"


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_task(
    task_id: str = "100",
    content: str = "Test task",
    project_id: str = "200",
    priority: int = 1,
    is_completed: bool = False,
    labels: list[str] | None = None,
    due: dict | None = None,
    url: str = "https://todoist.com/showTask?id=100",
    description: str = "",
    **extra,
) -> dict:
    """Build a Todoist task dict with sensible defaults."""
    task = {
        "id": task_id,
        "content": content,
        "description": description,
        "project_id": project_id,
        "priority": priority,
        "is_completed": is_completed,
        "labels": labels or [],
        "url": url,
    }
    if due is not None:
        task["due"] = due
    task.update(extra)
    return task


# ---------------------------------------------------------------------------
# Tests: Priority mapping — Todoist → bpkm
# ---------------------------------------------------------------------------


class TestTodoistToBpkmPriority:
    """Todoist priority (1–4) → bpkm priority string."""

    def test_priority_1_maps_to_low(self):
        assert mapper.TODOIST_TO_BPKM_PRIORITY[1] == "low"

    def test_priority_2_maps_to_medium(self):
        assert mapper.TODOIST_TO_BPKM_PRIORITY[2] == "medium"

    def test_priority_3_maps_to_high(self):
        assert mapper.TODOIST_TO_BPKM_PRIORITY[3] == "high"

    def test_priority_4_maps_to_critical(self):
        assert mapper.TODOIST_TO_BPKM_PRIORITY[4] == "critical"

    def test_all_four_levels_present(self):
        assert len(mapper.TODOIST_TO_BPKM_PRIORITY) == 4


# ---------------------------------------------------------------------------
# Tests: Priority mapping — bpkm → Todoist
# ---------------------------------------------------------------------------


class TestBpkmToTodoistPriority:
    """bpkm priority string → Todoist priority (1–4)."""

    def test_low_maps_to_1(self):
        assert mapper.BPKM_TO_TODOIST_PRIORITY["low"] == 1

    def test_medium_maps_to_2(self):
        assert mapper.BPKM_TO_TODOIST_PRIORITY["medium"] == 2

    def test_high_maps_to_3(self):
        assert mapper.BPKM_TO_TODOIST_PRIORITY["high"] == 3

    def test_critical_maps_to_4(self):
        assert mapper.BPKM_TO_TODOIST_PRIORITY["critical"] == 4

    def test_roundtrip_all_levels(self):
        """Every Todoist priority roundtrips through both maps."""
        for todoist_val, bpkm_val in mapper.TODOIST_TO_BPKM_PRIORITY.items():
            assert mapper.BPKM_TO_TODOIST_PRIORITY[bpkm_val] == todoist_val


# ---------------------------------------------------------------------------
# Tests: Status mapping — Todoist → bpkm
# ---------------------------------------------------------------------------


class TestTodoistToBpkmStatus:
    """is_completed (bool) → bpkm taskStatus."""

    def test_false_maps_to_todo(self):
        assert mapper.TODOIST_TO_BPKM_STATUS[False] == "todo"

    def test_true_maps_to_done(self):
        assert mapper.TODOIST_TO_BPKM_STATUS[True] == "done"


# ---------------------------------------------------------------------------
# Tests: Status mapping — bpkm → Todoist
# ---------------------------------------------------------------------------


class TestBpkmToTodoistStatus:
    """bpkm taskStatus → is_completed (bool)."""

    def test_todo_maps_to_false(self):
        assert mapper.BPKM_TO_TODOIST_STATUS["todo"] is False

    def test_in_progress_maps_to_false(self):
        assert mapper.BPKM_TO_TODOIST_STATUS["in-progress"] is False

    def test_done_maps_to_true(self):
        assert mapper.BPKM_TO_TODOIST_STATUS["done"] is True

    def test_cancelled_maps_to_true(self):
        assert mapper.BPKM_TO_TODOIST_STATUS["cancelled"] is True

    def test_blocked_maps_to_false(self):
        assert mapper.BPKM_TO_TODOIST_STATUS["blocked"] is False


# ---------------------------------------------------------------------------
# Tests: Due date extraction
# ---------------------------------------------------------------------------


class TestExtractDueDate:
    """Due date extraction from Todoist due object."""

    def test_none_due_returns_none(self):
        assert mapper.extract_due_date(None) is None

    def test_date_only(self):
        due = {"date": "2026-03-15", "is_recurring": False}
        assert mapper.extract_due_date(due) == "2026-03-15"

    def test_date_with_datetime(self):
        """When both date and datetime are present, date field is used."""
        due = {
            "date": "2026-03-15",
            "datetime": "2026-03-15T14:00:00",
            "timezone": "America/New_York",
        }
        assert mapper.extract_due_date(due) == "2026-03-15"

    def test_datetime_only_fallback(self):
        """If date is missing but datetime is present, extract date from datetime."""
        due = {"datetime": "2026-03-15T14:00:00"}
        assert mapper.extract_due_date(due) == "2026-03-15"

    def test_empty_due_object(self):
        """Empty dict returns None."""
        assert mapper.extract_due_date({}) is None

    def test_due_with_recurring_flag(self):
        """Recurring flag doesn't affect date extraction."""
        due = {"date": "2026-04-01", "is_recurring": True, "string": "every day"}
        assert mapper.extract_due_date(due) == "2026-04-01"

    def test_date_with_time_component_strips_time(self):
        """If date field somehow includes time info, only first 10 chars taken."""
        due = {"date": "2026-03-15T00:00:00Z"}
        assert mapper.extract_due_date(due) == "2026-03-15"

    def test_date_field_none_but_datetime_present(self):
        """Explicit None date with datetime present falls back to datetime."""
        due = {"date": None, "datetime": "2026-06-01T09:00:00"}
        assert mapper.extract_due_date(due) == "2026-06-01"

    def test_date_field_empty_string_but_datetime_present(self):
        """Empty string date with datetime present falls back to datetime."""
        due = {"date": "", "datetime": "2026-06-01T09:00:00"}
        assert mapper.extract_due_date(due) == "2026-06-01"


# ---------------------------------------------------------------------------
# Tests: Label mapping
# ---------------------------------------------------------------------------


class TestMapLabels:
    """Label name list → bpkm tags."""

    def test_empty_labels(self):
        assert mapper.map_labels([], {}) == []

    def test_single_label(self):
        assert mapper.map_labels(["urgent"], {}) == ["urgent"]

    def test_multiple_labels(self):
        result = mapper.map_labels(["urgent", "home", "groceries"], {})
        assert result == ["urgent", "home", "groceries"]

    def test_labels_lookup_not_used_for_rest_v2(self):
        """REST v2 already provides names — lookup dict is ignored."""
        result = mapper.map_labels(["work"], {"300": "work"})
        assert result == ["work"]


# ---------------------------------------------------------------------------
# Tests: Task slug
# ---------------------------------------------------------------------------


class TestComputeTaskSlug:
    """Deterministic slug generation from task ID."""

    def test_slug_format(self):
        slug = mapper.compute_task_slug("100")
        assert slug.startswith("td-")
        assert len(slug) == 3 + 16  # "td-" + 16 hex chars

    def test_deterministic(self):
        """Same input always produces same slug."""
        slug1 = mapper.compute_task_slug("100")
        slug2 = mapper.compute_task_slug("100")
        assert slug1 == slug2

    def test_different_ids_produce_different_slugs(self):
        slug1 = mapper.compute_task_slug("100")
        slug2 = mapper.compute_task_slug("101")
        assert slug1 != slug2


# ---------------------------------------------------------------------------
# Tests: build_task_properties — full integration
# ---------------------------------------------------------------------------


class TestBuildTaskProperties:
    """Full property builder from Todoist task → bpkm dict."""

    def test_basic_task(self):
        task = _make_task()
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)

        assert props["dcterms:title"] == "Test task"
        assert props[f"{BPKM}taskStatus"] == "todo"
        assert props[f"{BPKM}priority"] == "low"
        assert props[f"{BPKM}externalId"] == "100"
        assert props[f"{BPKM}externalProvider"] == "todoist"
        assert props[f"{BPKM}lastSyncedAt"] == FIXED_SYNC_TIME

    def test_completed_task(self):
        task = _make_task(is_completed=True)
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}taskStatus"] == "done"

    def test_priority_4_maps_to_critical(self):
        task = _make_task(priority=4)
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}priority"] == "critical"

    def test_priority_3_maps_to_high(self):
        task = _make_task(priority=3)
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}priority"] == "high"

    def test_priority_2_maps_to_medium(self):
        task = _make_task(priority=2)
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}priority"] == "medium"

    def test_priority_1_maps_to_low(self):
        task = _make_task(priority=1)
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}priority"] == "low"

    def test_with_due_date(self):
        task = _make_task(due={"date": "2026-04-01"})
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}dueDate"] == "2026-04-01"

    def test_without_due_date(self):
        task = _make_task()  # no due key
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert f"{BPKM}dueDate" not in props

    def test_with_labels(self):
        task = _make_task(labels=["urgent", "home"])
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}tags"] == ["urgent", "home"]

    def test_empty_labels_omitted(self):
        task = _make_task(labels=[])
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert f"{BPKM}tags" not in props

    def test_with_project_lookup(self):
        task = _make_task(project_id="200")
        project_lookup = {"200": "Personal", "201": "Work"}
        props = mapper.build_task_properties(
            task, project_lookup=project_lookup, sync_time=FIXED_SYNC_TIME
        )
        assert props[f"{BPKM}taskProject"] == "Personal"

    def test_project_not_in_lookup(self):
        task = _make_task(project_id="999")
        project_lookup = {"200": "Personal"}
        props = mapper.build_task_properties(
            task, project_lookup=project_lookup, sync_time=FIXED_SYNC_TIME
        )
        assert f"{BPKM}taskProject" not in props

    def test_no_project_lookup(self):
        task = _make_task(project_id="200")
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert f"{BPKM}taskProject" not in props

    def test_external_url(self):
        task = _make_task(url="https://todoist.com/showTask?id=100")
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}externalUrl"] == "https://todoist.com/showTask?id=100"

    def test_external_id_is_string(self):
        task = _make_task(task_id="12345")
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}externalId"] == "12345"
        assert isinstance(props[f"{BPKM}externalId"], str)

    def test_sync_time_always_present(self):
        task = _make_task()
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert f"{BPKM}lastSyncedAt" in props

    def test_auto_sync_time(self):
        """When sync_time is None, current UTC time is used."""
        task = _make_task()
        props = mapper.build_task_properties(task)
        assert f"{BPKM}lastSyncedAt" in props
        # Should be an ISO timestamp string
        assert "T" in props[f"{BPKM}lastSyncedAt"]

    def test_none_values_stripped(self):
        """Properties with None values are not included."""
        task = _make_task()
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        for v in props.values():
            assert v is not None

    def test_empty_string_values_stripped(self):
        """Properties with empty string values are not included (except title)."""
        task = _make_task(url="")
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert f"{BPKM}externalUrl" not in props

    def test_full_task_with_all_fields(self):
        """Full task with all fields populated."""
        task = _make_task(
            task_id="555",
            content="Full task",
            project_id="200",
            priority=3,
            is_completed=False,
            labels=["work", "important"],
            due={"date": "2026-06-15", "is_recurring": False},
            url="https://todoist.com/showTask?id=555",
        )
        project_lookup = {"200": "Work Projects"}
        props = mapper.build_task_properties(
            task, project_lookup=project_lookup, sync_time=FIXED_SYNC_TIME
        )

        assert props["dcterms:title"] == "Full task"
        assert props[f"{BPKM}taskStatus"] == "todo"
        assert props[f"{BPKM}priority"] == "high"
        assert props[f"{BPKM}tags"] == ["work", "important"]
        assert props[f"{BPKM}taskProject"] == "Work Projects"
        assert props[f"{BPKM}dueDate"] == "2026-06-15"
        assert props[f"{BPKM}externalId"] == "555"
        assert props[f"{BPKM}externalUrl"] == "https://todoist.com/showTask?id=555"
        assert props[f"{BPKM}externalProvider"] == "todoist"
        assert props[f"{BPKM}lastSyncedAt"] == FIXED_SYNC_TIME

    def test_missing_priority_defaults_to_low(self):
        """Task without priority key defaults to Todoist 1 → bpkm low."""
        task = _make_task()
        del task["priority"]
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert props[f"{BPKM}priority"] == "low"

    def test_missing_content_defaults_to_empty(self):
        """Task without content key produces empty title (stripped)."""
        task = _make_task()
        del task["content"]
        props = mapper.build_task_properties(task, sync_time=FIXED_SYNC_TIME)
        assert "dcterms:title" not in props


# ---------------------------------------------------------------------------
# Tests: build_todoist_task_data (reverse mapping)
# ---------------------------------------------------------------------------


class TestBuildTodoistTaskData:
    """bpkm properties → Todoist task data."""

    def test_title_to_content(self):
        result = mapper.build_todoist_task_data({"dcterms:title": "Buy milk"})
        assert result["content"] == "Buy milk"

    def test_priority_low_to_1(self):
        result = mapper.build_todoist_task_data({f"{BPKM}priority": "low"})
        assert result["priority"] == 1

    def test_priority_medium_to_2(self):
        result = mapper.build_todoist_task_data({f"{BPKM}priority": "medium"})
        assert result["priority"] == 2

    def test_priority_high_to_3(self):
        result = mapper.build_todoist_task_data({f"{BPKM}priority": "high"})
        assert result["priority"] == 3

    def test_priority_critical_to_4(self):
        result = mapper.build_todoist_task_data({f"{BPKM}priority": "critical"})
        assert result["priority"] == 4

    def test_tags_to_labels(self):
        result = mapper.build_todoist_task_data({f"{BPKM}tags": ["work", "urgent"]})
        assert result["labels"] == ["work", "urgent"]

    def test_due_date(self):
        result = mapper.build_todoist_task_data({f"{BPKM}dueDate": "2026-04-01"})
        assert result["due_date"] == "2026-04-01"

    def test_empty_props_returns_empty_dict(self):
        result = mapper.build_todoist_task_data({})
        assert result == {}

    def test_unknown_priority_ignored(self):
        result = mapper.build_todoist_task_data({f"{BPKM}priority": "unknown"})
        assert "priority" not in result

    def test_full_reverse_mapping(self):
        props = {
            "dcterms:title": "Updated task",
            f"{BPKM}priority": "high",
            f"{BPKM}tags": ["home"],
            f"{BPKM}dueDate": "2026-07-01",
        }
        result = mapper.build_todoist_task_data(props)
        assert result == {
            "content": "Updated task",
            "priority": 3,
            "labels": ["home"],
            "due_date": "2026-07-01",
        }
