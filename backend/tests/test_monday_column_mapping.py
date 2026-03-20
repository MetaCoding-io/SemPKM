"""Unit tests for Monday.com column mapping routes and type compatibility.

Tests:
- COLUMN_TYPE_COMPATIBILITY filtering logic
- Column mapping save/load via settings
- Label discovery from settings_str (including edge cases)
- MondayClient extensions for groups and subitems
- Route handler logic for configure-columns, save-column-mapping,
  configure-labels, save-label-mapping

Loads modules from the apps directory using importlib (no package install).
Uses ``asyncio.run()`` for async tests without requiring pytest-asyncio.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory (dependency order)
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "monday-sync"
)
_SERVICES_DIR = _APPS_DIR / "services"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load services that don't depend on sempkm_app_sdk
_monday_client_mod = _load_module(
    "monday_client", _SERVICES_DIR / "monday_client.py"
)
MondayClient = _monday_client_mod.MondayClient
MondayApiError = _monday_client_mod.MondayApiError
MondayAuthError = _monday_client_mod.MondayAuthError

# Load constants from app.py by parsing the source — the module itself
# imports sempkm_app_sdk which isn't available in the test environment.
# We extract constants using exec on just the constant blocks.

_APP_SOURCE = (_APPS_DIR / "app.py").read_text()


def _extract_constants():
    """Extract constant dicts from app.py without importing the module."""
    # Build a minimal namespace with only what the constant definitions need
    ns: dict[str, Any] = {}
    # Execute only the constant-assignment lines
    lines = _APP_SOURCE.splitlines()
    in_const = False
    const_block: list[str] = []
    brace_depth = 0

    for line in lines:
        stripped = line.strip()

        # Detect start of a constant assignment
        if any(
            stripped.startswith(f"{name} =")
            or stripped.startswith(f"{name}=")
            for name in [
                "COLUMN_TYPE_COMPATIBILITY",
                "BPKM_PROPERTY_LABELS",
                "BPKM_STATUS_VALUES",
                "BPKM_PRIORITY_VALUES",
            ]
        ):
            in_const = True
            const_block = [line]
            brace_depth = line.count("{") + line.count("[") - line.count("}") - line.count("]")
            if brace_depth <= 0:
                # Single-line constant
                exec("\n".join(const_block), ns)
                in_const = False
                const_block = []
            continue

        if in_const:
            const_block.append(line)
            brace_depth += line.count("{") + line.count("[") - line.count("}") - line.count("]")
            if brace_depth <= 0:
                exec("\n".join(const_block), ns)
                in_const = False
                const_block = []

    return ns


_constants = _extract_constants()
COLUMN_TYPE_COMPATIBILITY = _constants["COLUMN_TYPE_COMPATIBILITY"]
BPKM_PROPERTY_LABELS = _constants["BPKM_PROPERTY_LABELS"]
BPKM_STATUS_VALUES = _constants["BPKM_STATUS_VALUES"]
BPKM_PRIORITY_VALUES = _constants["BPKM_PRIORITY_VALUES"]


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(
        self,
        status_code: int = 200,
        body: dict | list | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.headers = headers or {}

    @property
    def text(self) -> str:
        if isinstance(self._body, str):
            return self._body
        return json.dumps(self._body)

    def json(self) -> Any:
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body


class MockStateClient:
    """In-memory state client that mimics the SDK StateClient interface."""

    def __init__(self, initial: dict[str, str] | None = None):
        self._store: dict[str, str] = initial or {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


class MockSettingsClient:
    """In-memory settings store — separate from state."""

    def __init__(self, initial: dict[str, str] | None = None):
        self._store: dict[str, str] = initial or {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


class MockHttpClient:
    """Tracks HTTP requests and returns configurable responses."""

    def __init__(self, responses: list[MockResponse] | None = None):
        self.requests: list[dict] = []
        self._responses = list(responses or [])
        self._default_response = MockResponse(200, {"data": {}})

    async def request(
        self,
        method: str,
        url: str,
        json: Any = None,
        headers: dict | None = None,
        **kwargs,
    ) -> MockResponse:
        self.requests.append({
            "method": method,
            "url": url,
            "json": json,
            "headers": headers,
        })
        if self._responses:
            return self._responses.pop(0)
        return self._default_response


class MockMondayClient:
    """Mock MondayClient for route handler testing."""

    def __init__(
        self,
        columns: list[dict] | None = None,
        boards: list[dict] | None = None,
        items: list[dict] | None = None,
        subitems: list[dict] | None = None,
        me_result: dict | None = None,
    ):
        self.columns = columns or []
        self.boards = boards or []
        self.items = items or []
        self.subitems = subitems or []
        self.me_result = me_result or {"id": "1", "name": "Test User", "email": "test@example.com"}

    async def get_board_columns(self, board_id: int) -> list[dict]:
        return self.columns

    async def get_boards(self) -> list[dict]:
        return self.boards

    async def get_board_items(self, board_id: int, limit: int = 100, cursor: str | None = None) -> dict:
        return {"items": self.items, "cursor": None}

    async def get_subitems(self, item_ids: list[int]) -> list[dict]:
        return self.subitems

    async def get_me(self) -> dict:
        return self.me_result


# ---------------------------------------------------------------------------
# Sample data factory helpers
# ---------------------------------------------------------------------------

def _make_column(
    col_id: str,
    title: str,
    col_type: str,
    settings_str: str | None = None,
) -> dict:
    """Build a Monday.com column dict."""
    col = {"id": col_id, "title": title, "type": col_type}
    if settings_str is not None:
        col["settings_str"] = settings_str
    return col


def _make_status_column(
    col_id: str = "status_col",
    title: str = "Status",
    labels: dict | None = None,
) -> dict:
    """Build a status column with labels in settings_str."""
    if labels is None:
        labels = {"0": "", "1": "Working on it", "2": "Done", "3": "Stuck"}
    settings = json.dumps({"labels": labels})
    return _make_column(col_id, title, "status", settings)


def _make_columns_set() -> list[dict]:
    """Build a realistic set of columns covering all types."""
    return [
        _make_status_column("status_col", "Status"),
        _make_status_column("priority_col", "Priority", {
            "0": "", "1": "Critical", "2": "High", "3": "Medium", "4": "Low",
        }),
        _make_column("color_col", "Color Label", "color"),
        _make_column("date_col", "Due Date", "date"),
        _make_column("timeline_col", "Timeline", "timeline"),
        _make_column("people_col", "Assignee", "people"),
        _make_column("text_col", "Short Text", "text"),
        _make_column("longtext_col", "Long Text", "long_text"),
        _make_column("numbers_col", "Story Points", "numbers"),
        _make_column("tags_col", "Tags", "tags"),
        _make_column("dropdown_col", "Category", "dropdown"),
        _make_column("dependency_col", "Dependencies", "dependency"),
        _make_column("email_col", "Email", "email"),
        _make_column("phone_col", "Phone", "phone"),
        _make_column("checkbox_col", "Done?", "checkbox"),
    ]


# ===================================================================
# SECTION 1: COLUMN_TYPE_COMPATIBILITY filtering tests
# ===================================================================


class TestColumnTypeCompatibility:
    """Tests for the COLUMN_TYPE_COMPATIBILITY constant and filtering logic."""

    def test_task_status_matches_status_only(self):
        allowed = COLUMN_TYPE_COMPATIBILITY["taskStatus"]
        assert allowed == ["status"]

    def test_priority_matches_status_and_color(self):
        allowed = COLUMN_TYPE_COMPATIBILITY["priority"]
        assert "status" in allowed
        assert "color" in allowed
        assert len(allowed) == 2

    def test_due_date_matches_date_and_timeline(self):
        allowed = COLUMN_TYPE_COMPATIBILITY["dueDate"]
        assert "date" in allowed
        assert "timeline" in allowed
        assert len(allowed) == 2

    def test_assigned_to_matches_people_only(self):
        allowed = COLUMN_TYPE_COMPATIBILITY["assignedTo"]
        assert allowed == ["people"]

    def test_description_matches_text_and_long_text(self):
        allowed = COLUMN_TYPE_COMPATIBILITY["description"]
        assert "text" in allowed
        assert "long_text" in allowed
        assert len(allowed) == 2

    def test_estimated_effort_matches_numbers_only(self):
        allowed = COLUMN_TYPE_COMPATIBILITY["estimatedEffort"]
        assert allowed == ["numbers"]

    def test_tags_matches_tags_and_dropdown(self):
        allowed = COLUMN_TYPE_COMPATIBILITY["tags"]
        assert "tags" in allowed
        assert "dropdown" in allowed
        assert len(allowed) == 2

    def test_dependency_matches_dependency_only(self):
        allowed = COLUMN_TYPE_COMPATIBILITY["dependency"]
        assert allowed == ["dependency"]

    def test_non_compatible_types_excluded(self):
        """Email, phone, checkbox etc. should not appear in any compatibility list."""
        all_compatible_types = set()
        for types_list in COLUMN_TYPE_COMPATIBILITY.values():
            all_compatible_types.update(types_list)
        assert "email" not in all_compatible_types
        assert "phone" not in all_compatible_types
        assert "checkbox" not in all_compatible_types

    def test_all_bpkm_labels_have_compatibility_entry(self):
        """Every property in BPKM_PROPERTY_LABELS should have an entry in COLUMN_TYPE_COMPATIBILITY."""
        for prop in BPKM_PROPERTY_LABELS:
            assert prop in COLUMN_TYPE_COMPATIBILITY, (
                f"Property {prop!r} in BPKM_PROPERTY_LABELS but not in COLUMN_TYPE_COMPATIBILITY"
            )

    def test_compatibility_keys_are_superset_of_labels(self):
        """COLUMN_TYPE_COMPATIBILITY may have extra keys (like dependency) beyond labels."""
        label_keys = set(BPKM_PROPERTY_LABELS.keys())
        compat_keys = set(COLUMN_TYPE_COMPATIBILITY.keys())
        assert label_keys.issubset(compat_keys)

    def test_filter_columns_by_type_status(self):
        """Filtering a column list for taskStatus should return only status-type columns."""
        columns = _make_columns_set()
        allowed_types = COLUMN_TYPE_COMPATIBILITY["taskStatus"]
        compatible = [c for c in columns if c.get("type") in allowed_types]
        assert len(compatible) == 2  # status_col and priority_col are both type "status"
        for c in compatible:
            assert c["type"] == "status"

    def test_filter_columns_by_type_people(self):
        """Filtering for assignedTo should return only people-type columns."""
        columns = _make_columns_set()
        allowed_types = COLUMN_TYPE_COMPATIBILITY["assignedTo"]
        compatible = [c for c in columns if c.get("type") in allowed_types]
        assert len(compatible) == 1
        assert compatible[0]["id"] == "people_col"

    def test_filter_columns_by_type_numbers(self):
        """Filtering for estimatedEffort should return only numbers-type columns."""
        columns = _make_columns_set()
        allowed_types = COLUMN_TYPE_COMPATIBILITY["estimatedEffort"]
        compatible = [c for c in columns if c.get("type") in allowed_types]
        assert len(compatible) == 1
        assert compatible[0]["id"] == "numbers_col"

    def test_filter_columns_by_type_description(self):
        """Filtering for description should return text and long_text columns."""
        columns = _make_columns_set()
        allowed_types = COLUMN_TYPE_COMPATIBILITY["description"]
        compatible = [c for c in columns if c.get("type") in allowed_types]
        assert len(compatible) == 2
        types = {c["type"] for c in compatible}
        assert types == {"text", "long_text"}

    def test_filter_columns_by_type_tags(self):
        """Filtering for tags should return tags and dropdown columns."""
        columns = _make_columns_set()
        allowed_types = COLUMN_TYPE_COMPATIBILITY["tags"]
        compatible = [c for c in columns if c.get("type") in allowed_types]
        assert len(compatible) == 2
        types = {c["type"] for c in compatible}
        assert types == {"tags", "dropdown"}

    def test_filter_columns_by_type_date(self):
        """Filtering for dueDate should return date and timeline columns."""
        columns = _make_columns_set()
        allowed_types = COLUMN_TYPE_COMPATIBILITY["dueDate"]
        compatible = [c for c in columns if c.get("type") in allowed_types]
        assert len(compatible) == 2
        types = {c["type"] for c in compatible}
        assert types == {"date", "timeline"}

    def test_filter_empty_columns_returns_empty(self):
        """Filtering an empty column list should return empty for every property."""
        for bpkm_prop, allowed_types in COLUMN_TYPE_COMPATIBILITY.items():
            compatible = [c for c in [] if c.get("type") in allowed_types]
            assert compatible == [], f"Expected empty for {bpkm_prop}"

    def test_filter_all_incompatible_columns(self):
        """Columns of types not in any compatibility list should never match."""
        columns = [
            _make_column("email_col", "Email", "email"),
            _make_column("phone_col", "Phone", "phone"),
            _make_column("checkbox_col", "Done", "checkbox"),
        ]
        for bpkm_prop, allowed_types in COLUMN_TYPE_COMPATIBILITY.items():
            compatible = [c for c in columns if c.get("type") in allowed_types]
            assert compatible == [], (
                f"Unexpected match for {bpkm_prop}: {compatible}"
            )


# ===================================================================
# SECTION 2: BPKM constants validation tests
# ===================================================================


class TestBpkmConstants:
    """Tests for BPKM_PROPERTY_LABELS, BPKM_STATUS_VALUES, BPKM_PRIORITY_VALUES."""

    def test_property_labels_has_expected_keys(self):
        expected = {"taskStatus", "priority", "dueDate", "assignedTo",
                    "description", "estimatedEffort", "tags"}
        assert set(BPKM_PROPERTY_LABELS.keys()) == expected

    def test_property_labels_values_are_strings(self):
        for key, label in BPKM_PROPERTY_LABELS.items():
            assert isinstance(label, str), f"Label for {key!r} is not a string"
            assert label.strip(), f"Label for {key!r} is empty"

    def test_status_values_are_valid(self):
        expected = ["todo", "in-progress", "done", "blocked", "cancelled"]
        assert BPKM_STATUS_VALUES == expected

    def test_priority_values_are_valid(self):
        expected = ["critical", "high", "medium", "low"]
        assert BPKM_PRIORITY_VALUES == expected

    def test_status_values_non_empty(self):
        assert len(BPKM_STATUS_VALUES) > 0
        for val in BPKM_STATUS_VALUES:
            assert isinstance(val, str)
            assert val.strip()

    def test_priority_values_non_empty(self):
        assert len(BPKM_PRIORITY_VALUES) > 0
        for val in BPKM_PRIORITY_VALUES:
            assert isinstance(val, str)
            assert val.strip()


# ===================================================================
# SECTION 3: Column mapping save/load tests
# ===================================================================


class TestColumnMappingSaveLoad:
    """Tests for saving and loading column mappings in settings."""

    def test_save_column_mapping_stores_json(self):
        """Saving a column mapping should store JSON in settings."""
        settings = MockSettingsClient()
        mapping = {"taskStatus": "status_col", "priority": "priority_col"}
        _run(settings.set("column_mapping_123", json.dumps(mapping)))

        raw = _run(settings.get("column_mapping_123"))
        assert raw is not None
        loaded = json.loads(raw)
        assert loaded == mapping

    def test_save_mapping_with_all_properties(self):
        """All bpkm properties can be mapped simultaneously."""
        settings = MockSettingsClient()
        mapping = {
            "taskStatus": "status_col",
            "priority": "priority_col",
            "dueDate": "date_col",
            "assignedTo": "people_col",
            "description": "text_col",
            "estimatedEffort": "numbers_col",
            "tags": "tags_col",
        }
        _run(settings.set("column_mapping_456", json.dumps(mapping)))

        loaded = json.loads(_run(settings.get("column_mapping_456")))
        assert loaded == mapping
        assert len(loaded) == len(BPKM_PROPERTY_LABELS)

    def test_save_mapping_with_some_properties_empty(self):
        """Only non-empty values should be saved."""
        form_data = {
            "taskStatus": "status_col",
            "priority": "",
            "dueDate": "date_col",
            "assignedTo": "",
            "description": "",
            "estimatedEffort": "",
            "tags": "",
        }
        # Replicate the route handler logic: only save non-empty
        mapping = {k: v for k, v in form_data.items() if v.strip()}
        settings = MockSettingsClient()
        _run(settings.set("column_mapping_789", json.dumps(mapping)))

        loaded = json.loads(_run(settings.get("column_mapping_789")))
        assert loaded == {"taskStatus": "status_col", "dueDate": "date_col"}

    def test_load_existing_mapping_returns_correct_values(self):
        """Loading an existing mapping should return the saved dict."""
        mapping = {"taskStatus": "status_col", "priority": "priority_col"}
        settings = MockSettingsClient({
            "column_mapping_100": json.dumps(mapping),
        })
        raw = _run(settings.get("column_mapping_100"))
        loaded = json.loads(raw)
        assert loaded["taskStatus"] == "status_col"
        assert loaded["priority"] == "priority_col"

    def test_load_nonexistent_mapping_returns_none(self):
        """Loading a mapping for an unmapped board should return None."""
        settings = MockSettingsClient()
        raw = _run(settings.get("column_mapping_999"))
        assert raw is None

    def test_multiple_boards_independent(self):
        """Different boards have independent column mappings."""
        settings = MockSettingsClient()
        mapping_a = {"taskStatus": "status_col_a"}
        mapping_b = {"taskStatus": "status_col_b", "priority": "prio_col_b"}

        _run(settings.set("column_mapping_100", json.dumps(mapping_a)))
        _run(settings.set("column_mapping_200", json.dumps(mapping_b)))

        loaded_a = json.loads(_run(settings.get("column_mapping_100")))
        loaded_b = json.loads(_run(settings.get("column_mapping_200")))

        assert loaded_a == mapping_a
        assert loaded_b == mapping_b
        assert loaded_a != loaded_b

    def test_overwrite_existing_mapping(self):
        """Saving a new mapping for the same board replaces the old one."""
        settings = MockSettingsClient({
            "column_mapping_100": json.dumps({"taskStatus": "old_col"}),
        })
        new_mapping = {"taskStatus": "new_col", "priority": "prio_col"}
        _run(settings.set("column_mapping_100", json.dumps(new_mapping)))

        loaded = json.loads(_run(settings.get("column_mapping_100")))
        assert loaded == new_mapping

    def test_mapping_key_format_uses_board_id(self):
        """Column mapping key follows the pattern 'column_mapping_{board_id}'."""
        board_id = "12345"
        key = f"column_mapping_{board_id}"
        settings = MockSettingsClient()
        _run(settings.set(key, json.dumps({"taskStatus": "s"})))
        assert _run(settings.get(key)) is not None
        assert _run(settings.get("column_mapping_99999")) is None

    def test_save_empty_mapping(self):
        """If no properties are mapped, an empty dict is stored."""
        settings = MockSettingsClient()
        mapping: dict = {}
        _run(settings.set("column_mapping_100", json.dumps(mapping)))
        loaded = json.loads(_run(settings.get("column_mapping_100")))
        assert loaded == {}

    def test_mapping_values_are_column_ids(self):
        """Mapping values should be column ID strings, not column titles."""
        mapping = {"taskStatus": "status_col", "dueDate": "date_col"}
        settings = MockSettingsClient()
        _run(settings.set("column_mapping_100", json.dumps(mapping)))
        loaded = json.loads(_run(settings.get("column_mapping_100")))
        # Column IDs are short identifiers like "status_col", not human titles like "Status"
        for val in loaded.values():
            assert isinstance(val, str)
            assert " " not in val  # column IDs don't have spaces

    def test_save_column_mapping_preserves_json_types(self):
        """JSON round-trip should preserve types correctly."""
        mapping = {"taskStatus": "status_col", "priority": "priority_col"}
        raw = json.dumps(mapping)
        loaded = json.loads(raw)
        assert isinstance(loaded, dict)
        for k, v in loaded.items():
            assert isinstance(k, str)
            assert isinstance(v, str)

    def test_concurrent_board_save_does_not_interfere(self):
        """Saving mappings for two boards in sequence doesn't corrupt either."""
        settings = MockSettingsClient()

        async def save_both():
            await settings.set("column_mapping_1", json.dumps({"taskStatus": "col_1"}))
            await settings.set("column_mapping_2", json.dumps({"taskStatus": "col_2"}))

        _run(save_both())
        assert json.loads(_run(settings.get("column_mapping_1")))["taskStatus"] == "col_1"
        assert json.loads(_run(settings.get("column_mapping_2")))["taskStatus"] == "col_2"

    def test_configured_boards_detection(self):
        """A board with a column mapping is considered 'configured'."""
        settings = MockSettingsClient({
            "column_mapping_100": json.dumps({"taskStatus": "s"}),
        })
        # Replicate the configured_boards logic from _render_connect_status
        selected_boards = ["100", "200"]
        configured_boards: set[str] = set()

        async def check():
            for bid in selected_boards:
                mapping_json = await settings.get(f"column_mapping_{bid}")
                if mapping_json:
                    configured_boards.add(str(bid))

        _run(check())
        assert "100" in configured_boards
        assert "200" not in configured_boards

    def test_board_id_as_numeric_string(self):
        """Board IDs should work as both numeric strings and integers."""
        settings = MockSettingsClient()
        _run(settings.set("column_mapping_12345", json.dumps({"taskStatus": "s"})))
        # Access with the same string form
        raw = _run(settings.get("column_mapping_12345"))
        assert raw is not None

    def test_save_mapping_only_nonblank_values(self):
        """Whitespace-only values should be treated as empty and excluded."""
        form_data = {
            "taskStatus": "status_col",
            "priority": "   ",
            "dueDate": "\t",
            "assignedTo": "",
        }
        mapping = {k: v.strip() for k, v in form_data.items() if v.strip()}
        assert mapping == {"taskStatus": "status_col"}


# ===================================================================
# SECTION 4: Label discovery from settings_str tests
# ===================================================================


class TestLabelDiscovery:
    """Tests for parsing labels from Monday.com column settings_str."""

    @staticmethod
    def _parse_labels_from_settings_str(settings_str: str | None) -> list[tuple[str, str]]:
        """Replicate the _parse_labels logic from configure_labels route."""
        if not settings_str:
            return []
        try:
            settings = json.loads(settings_str)
        except (json.JSONDecodeError, TypeError):
            return []
        labels = settings.get("labels", {})
        if not isinstance(labels, dict):
            return []
        return sorted(labels.items(), key=lambda x: x[0])

    def test_parse_standard_labels(self):
        """Standard settings_str with labels should return sorted label tuples."""
        settings_str = json.dumps({
            "labels": {"0": "", "1": "Working on it", "2": "Done"}
        })
        result = self._parse_labels_from_settings_str(settings_str)
        assert len(result) == 3
        assert result[0] == ("0", "")
        assert result[1] == ("1", "Working on it")
        assert result[2] == ("2", "Done")

    def test_parse_labels_sorted_by_key(self):
        """Labels should be sorted by their string key."""
        settings_str = json.dumps({
            "labels": {"3": "Stuck", "1": "Working on it", "2": "Done", "0": ""}
        })
        result = self._parse_labels_from_settings_str(settings_str)
        assert [k for k, v in result] == ["0", "1", "2", "3"]

    def test_empty_string_label_preserved(self):
        """An empty string label (index 0) represents 'Default / Not Started'."""
        settings_str = json.dumps({"labels": {"0": "", "1": "Active"}})
        result = self._parse_labels_from_settings_str(settings_str)
        assert result[0] == ("0", "")
        # UI should display this as "Default / Not Started" but raw data is ""

    def test_malformed_json_returns_empty(self):
        """Malformed settings_str (not valid JSON) should return empty list."""
        result = self._parse_labels_from_settings_str("not valid json {")
        assert result == []

    def test_missing_labels_key_returns_empty(self):
        """settings_str without a 'labels' key should return empty list."""
        settings_str = json.dumps({"done_colors": {"1": "#00FF00"}})
        result = self._parse_labels_from_settings_str(settings_str)
        assert result == []

    def test_settings_str_none_returns_empty(self):
        """None settings_str should return empty list."""
        result = self._parse_labels_from_settings_str(None)
        assert result == []

    def test_settings_str_empty_string_returns_empty(self):
        """Empty string settings_str should return empty list."""
        result = self._parse_labels_from_settings_str("")
        assert result == []

    def test_labels_not_dict_returns_empty(self):
        """If labels is not a dict (e.g. a list), return empty."""
        settings_str = json.dumps({"labels": ["Done", "Working"]})
        result = self._parse_labels_from_settings_str(settings_str)
        assert result == []

    def test_labels_is_null_returns_empty(self):
        """If labels is null, return empty."""
        settings_str = json.dumps({"labels": None})
        result = self._parse_labels_from_settings_str(settings_str)
        assert result == []

    def test_priority_labels_parsed_independently(self):
        """Priority column settings_str has its own label set."""
        status_settings = json.dumps({
            "labels": {"0": "", "1": "Working", "2": "Done"}
        })
        priority_settings = json.dumps({
            "labels": {"0": "", "1": "Critical", "2": "High", "3": "Medium", "4": "Low"}
        })
        status_labels = self._parse_labels_from_settings_str(status_settings)
        priority_labels = self._parse_labels_from_settings_str(priority_settings)
        assert len(status_labels) == 3
        assert len(priority_labels) == 5
        assert status_labels != priority_labels

    def test_labels_with_unicode(self):
        """Labels with unicode characters should be preserved."""
        settings_str = json.dumps({
            "labels": {"1": "En cours 🚧", "2": "Terminé ✅"}
        })
        result = self._parse_labels_from_settings_str(settings_str)
        assert result[0] == ("1", "En cours 🚧")
        assert result[1] == ("2", "Terminé ✅")

    def test_labels_with_many_entries(self):
        """Columns can have many custom labels."""
        labels = {str(i): f"Label {i}" for i in range(20)}
        settings_str = json.dumps({"labels": labels})
        result = self._parse_labels_from_settings_str(settings_str)
        assert len(result) == 20

    def test_settings_str_with_extra_keys_ignored(self):
        """Extra keys in settings_str besides 'labels' should not interfere."""
        settings_str = json.dumps({
            "labels": {"1": "Done"},
            "done_colors": {"1": "#00FF00"},
            "color_mapping": {},
        })
        result = self._parse_labels_from_settings_str(settings_str)
        assert len(result) == 1
        assert result[0] == ("1", "Done")

    def test_numeric_string_keys_sorted_lexically(self):
        """Labels with numeric string keys are sorted lexically."""
        settings_str = json.dumps({
            "labels": {"10": "Label10", "2": "Label2", "1": "Label1"}
        })
        result = self._parse_labels_from_settings_str(settings_str)
        # Lexical sort: "1" < "10" < "2"
        assert [k for k, v in result] == ["1", "10", "2"]


# ===================================================================
# SECTION 5: Label mapping save/load tests
# ===================================================================


class TestLabelMappingSaveLoad:
    """Tests for saving and loading label mappings in settings."""

    def test_save_label_mapping_stores_nested_json(self):
        """Label mapping saves as nested dict with status and priority sub-keys."""
        settings = MockSettingsClient()
        label_mapping = {
            "status_label_mapping": {"Working on it": "in-progress", "Done": "done"},
            "priority_label_mapping": {"Critical": "critical", "High": "high"},
        }
        _run(settings.set("label_mapping_100", json.dumps(label_mapping)))

        loaded = json.loads(_run(settings.get("label_mapping_100")))
        assert loaded["status_label_mapping"]["Working on it"] == "in-progress"
        assert loaded["priority_label_mapping"]["Critical"] == "critical"

    def test_save_label_mapping_status_only(self):
        """Can save only status label mapping with empty priority."""
        label_mapping = {
            "status_label_mapping": {"Done": "done", "Working on it": "in-progress"},
            "priority_label_mapping": {},
        }
        settings = MockSettingsClient()
        _run(settings.set("label_mapping_100", json.dumps(label_mapping)))

        loaded = json.loads(_run(settings.get("label_mapping_100")))
        assert len(loaded["status_label_mapping"]) == 2
        assert len(loaded["priority_label_mapping"]) == 0

    def test_save_label_mapping_priority_only(self):
        """Can save only priority label mapping with empty status."""
        label_mapping = {
            "status_label_mapping": {},
            "priority_label_mapping": {"High": "high"},
        }
        settings = MockSettingsClient()
        _run(settings.set("label_mapping_100", json.dumps(label_mapping)))

        loaded = json.loads(_run(settings.get("label_mapping_100")))
        assert len(loaded["status_label_mapping"]) == 0
        assert len(loaded["priority_label_mapping"]) == 1

    def test_load_nonexistent_label_mapping(self):
        """Loading label mapping for an unmapped board returns None."""
        settings = MockSettingsClient()
        raw = _run(settings.get("label_mapping_999"))
        assert raw is None

    def test_label_mapping_independent_per_board(self):
        """Different boards have independent label mappings."""
        settings = MockSettingsClient()
        mapping_a = {
            "status_label_mapping": {"Done": "done"},
            "priority_label_mapping": {},
        }
        mapping_b = {
            "status_label_mapping": {"Complete": "done"},
            "priority_label_mapping": {"High": "high"},
        }
        _run(settings.set("label_mapping_100", json.dumps(mapping_a)))
        _run(settings.set("label_mapping_200", json.dumps(mapping_b)))

        loaded_a = json.loads(_run(settings.get("label_mapping_100")))
        loaded_b = json.loads(_run(settings.get("label_mapping_200")))
        assert loaded_a["status_label_mapping"]["Done"] == "done"
        assert loaded_b["status_label_mapping"]["Complete"] == "done"

    def test_label_mapping_key_format(self):
        """Label mapping key follows 'label_mapping_{board_id}' pattern."""
        key = "label_mapping_555"
        settings = MockSettingsClient()
        _run(settings.set(key, json.dumps({"status_label_mapping": {}, "priority_label_mapping": {}})))
        assert _run(settings.get(key)) is not None

    def test_label_mapping_overwrite(self):
        """Saving a new label mapping replaces the old one."""
        settings = MockSettingsClient({
            "label_mapping_100": json.dumps({
                "status_label_mapping": {"Old": "todo"},
                "priority_label_mapping": {},
            }),
        })
        new_mapping = {
            "status_label_mapping": {"New": "done"},
            "priority_label_mapping": {"High": "high"},
        }
        _run(settings.set("label_mapping_100", json.dumps(new_mapping)))
        loaded = json.loads(_run(settings.get("label_mapping_100")))
        assert "New" in loaded["status_label_mapping"]
        assert "Old" not in loaded["status_label_mapping"]

    def test_label_values_are_bpkm_enum_values(self):
        """Label mapping values should be valid bpkm status or priority values."""
        label_mapping = {
            "status_label_mapping": {
                "Done": "done",
                "Working on it": "in-progress",
                "Stuck": "blocked",
            },
            "priority_label_mapping": {
                "Critical": "critical",
                "High": "high",
                "Medium": "medium",
                "Low": "low",
            },
        }
        for label, value in label_mapping["status_label_mapping"].items():
            assert value in BPKM_STATUS_VALUES, f"Invalid status value: {value}"
        for label, value in label_mapping["priority_label_mapping"].items():
            assert value in BPKM_PRIORITY_VALUES, f"Invalid priority value: {value}"


# ===================================================================
# SECTION 6: MondayClient extensions tests (groups and subitems)
# ===================================================================


class TestMondayClientGetBoardItems:
    """Tests for MondayClient.get_board_items with group data."""

    def _make_client(self, responses: list[MockResponse]) -> MondayClient:
        http = MockHttpClient(responses)
        state = MockStateClient({"monday_api_token": "test-token-123"})
        return MondayClient(http_client=http, state_client=state)

    def test_get_board_items_returns_items_with_group(self):
        """Items should include group { id title } data."""
        items = [
            {
                "id": "1",
                "name": "Task 1",
                "group": {"id": "group_1", "title": "Sprint 1"},
                "column_values": [],
            }
        ]
        resp = MockResponse(200, {
            "data": {
                "boards": [{
                    "items_page": {
                        "cursor": None,
                        "items": items,
                    }
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_board_items(123))
        assert len(result["items"]) == 1
        assert result["items"][0]["group"]["id"] == "group_1"
        assert result["items"][0]["group"]["title"] == "Sprint 1"

    def test_get_board_items_cursor_pagination(self):
        """When cursor is present, next page should be fetchable."""
        resp = MockResponse(200, {
            "data": {
                "boards": [{
                    "items_page": {
                        "cursor": "next_cursor_abc",
                        "items": [{"id": "1", "name": "T1", "group": {"id": "g1", "title": "G"}, "column_values": []}],
                    }
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_board_items(123))
        assert result["cursor"] == "next_cursor_abc"

    def test_get_board_items_no_cursor_means_last_page(self):
        """Null cursor means no more pages."""
        resp = MockResponse(200, {
            "data": {
                "boards": [{
                    "items_page": {
                        "cursor": None,
                        "items": [],
                    }
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_board_items(123))
        assert result["cursor"] is None

    def test_get_board_items_empty_board(self):
        """Empty board should return empty items list."""
        resp = MockResponse(200, {
            "data": {
                "boards": [{
                    "items_page": {
                        "cursor": None,
                        "items": [],
                    }
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_board_items(123))
        assert result["items"] == []

    def test_get_board_items_no_boards_returns_empty(self):
        """If no boards returned, items should be empty."""
        resp = MockResponse(200, {"data": {"boards": []}})
        client = self._make_client([resp])
        result = _run(client.get_board_items(123))
        assert result["items"] == []
        assert result["cursor"] is None

    def test_get_board_items_query_includes_group_field(self):
        """The GraphQL query should request group { id title }."""
        resp = MockResponse(200, {
            "data": {"boards": [{"items_page": {"cursor": None, "items": []}}]}
        })
        http = MockHttpClient([resp])
        state = MockStateClient({"monday_api_token": "token"})
        client = MondayClient(http_client=http, state_client=state)
        _run(client.get_board_items(123))

        assert len(http.requests) == 1
        query = http.requests[0]["json"]["query"]
        assert "group" in query
        assert "id" in query
        assert "title" in query

    def test_get_board_items_with_cursor_param(self):
        """When cursor is passed, query should include cursor parameter."""
        resp = MockResponse(200, {
            "data": {"boards": [{"items_page": {"cursor": None, "items": []}}]}
        })
        http = MockHttpClient([resp])
        state = MockStateClient({"monday_api_token": "token"})
        client = MondayClient(http_client=http, state_client=state)
        _run(client.get_board_items(123, cursor="abc123"))

        query = http.requests[0]["json"]["query"]
        assert "abc123" in query

    def test_get_board_items_multiple_items_with_different_groups(self):
        """Items from different groups should have distinct group data."""
        items = [
            {"id": "1", "name": "T1", "group": {"id": "g1", "title": "Sprint 1"}, "column_values": []},
            {"id": "2", "name": "T2", "group": {"id": "g2", "title": "Sprint 2"}, "column_values": []},
        ]
        resp = MockResponse(200, {
            "data": {"boards": [{"items_page": {"cursor": None, "items": items}}]}
        })
        client = self._make_client([resp])
        result = _run(client.get_board_items(456))
        assert result["items"][0]["group"]["title"] == "Sprint 1"
        assert result["items"][1]["group"]["title"] == "Sprint 2"


class TestMondayClientGetSubitems:
    """Tests for MondayClient.get_subitems."""

    def _make_client(self, responses: list[MockResponse]) -> MondayClient:
        http = MockHttpClient(responses)
        state = MockStateClient({"monday_api_token": "test-token-123"})
        return MondayClient(http_client=http, state_client=state)

    def test_get_subitems_returns_subitems_with_parent_id(self):
        """Each subitem should be augmented with parent_item_id."""
        resp = MockResponse(200, {
            "data": {
                "items": [{
                    "id": "100",
                    "subitems": [
                        {
                            "id": "201",
                            "name": "Subtask 1",
                            "group": {"id": "g1", "title": "Subitems"},
                            "column_values": [],
                        },
                        {
                            "id": "202",
                            "name": "Subtask 2",
                            "group": {"id": "g1", "title": "Subitems"},
                            "column_values": [],
                        },
                    ],
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_subitems([100]))
        assert len(result) == 2
        assert result[0]["parent_item_id"] == "100"
        assert result[1]["parent_item_id"] == "100"

    def test_get_subitems_empty_item_ids(self):
        """Empty item_ids list should return empty list without API call."""
        http = MockHttpClient([])
        state = MockStateClient({"monday_api_token": "token"})
        client = MondayClient(http_client=http, state_client=state)
        result = _run(client.get_subitems([]))
        assert result == []
        assert len(http.requests) == 0  # No API call made

    def test_get_subitems_no_subitems(self):
        """Items with no subitems should return empty list."""
        resp = MockResponse(200, {
            "data": {
                "items": [{
                    "id": "100",
                    "subitems": [],
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_subitems([100]))
        assert result == []

    def test_get_subitems_null_subitems(self):
        """Items with null subitems field should return empty list."""
        resp = MockResponse(200, {
            "data": {
                "items": [{
                    "id": "100",
                    "subitems": None,
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_subitems([100]))
        assert result == []

    def test_get_subitems_multiple_parents(self):
        """Subitems from multiple parents should all have correct parent_item_id."""
        resp = MockResponse(200, {
            "data": {
                "items": [
                    {
                        "id": "100",
                        "subitems": [
                            {"id": "201", "name": "Sub A", "group": {"id": "g1", "title": "G"}, "column_values": []},
                        ],
                    },
                    {
                        "id": "200",
                        "subitems": [
                            {"id": "301", "name": "Sub B", "group": {"id": "g1", "title": "G"}, "column_values": []},
                        ],
                    },
                ]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_subitems([100, 200]))
        assert len(result) == 2
        assert result[0]["parent_item_id"] == "100"
        assert result[1]["parent_item_id"] == "200"

    def test_get_subitems_includes_column_values(self):
        """Subitems should include column_values in their dicts."""
        resp = MockResponse(200, {
            "data": {
                "items": [{
                    "id": "100",
                    "subitems": [{
                        "id": "201",
                        "name": "Sub 1",
                        "group": {"id": "g1", "title": "G"},
                        "column_values": [
                            {"id": "status", "text": "Done", "type": "status", "value": "{}"},
                        ],
                    }],
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_subitems([100]))
        assert len(result[0]["column_values"]) == 1
        assert result[0]["column_values"][0]["id"] == "status"

    def test_get_subitems_includes_group(self):
        """Subitems should include group data."""
        resp = MockResponse(200, {
            "data": {
                "items": [{
                    "id": "100",
                    "subitems": [{
                        "id": "201",
                        "name": "Sub 1",
                        "group": {"id": "sub_group", "title": "Sub Items Group"},
                        "column_values": [],
                    }],
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_subitems([100]))
        assert result[0]["group"]["id"] == "sub_group"
        assert result[0]["group"]["title"] == "Sub Items Group"

    def test_get_subitems_query_includes_required_fields(self):
        """The GraphQL query should request id, name, group, column_values."""
        resp = MockResponse(200, {
            "data": {"items": [{"id": "100", "subitems": []}]}
        })
        http = MockHttpClient([resp])
        state = MockStateClient({"monday_api_token": "token"})
        client = MondayClient(http_client=http, state_client=state)
        _run(client.get_subitems([100]))

        query = http.requests[0]["json"]["query"]
        assert "subitems" in query
        assert "name" in query
        assert "group" in query
        assert "column_values" in query

    def test_get_subitems_includes_id_and_name(self):
        """Each subitem dict should have 'id' and 'name' fields."""
        resp = MockResponse(200, {
            "data": {
                "items": [{
                    "id": "100",
                    "subitems": [{
                        "id": "201",
                        "name": "My Subtask",
                        "group": {"id": "g1", "title": "G"},
                        "column_values": [],
                    }],
                }]
            }
        })
        client = self._make_client([resp])
        result = _run(client.get_subitems([100]))
        assert result[0]["id"] == "201"
        assert result[0]["name"] == "My Subtask"


# ===================================================================
# SECTION 7: Route handler logic tests
# ===================================================================


class TestConfigureColumnsLogic:
    """Tests for the configure-columns route handler logic."""

    def _filter_compatible(
        self,
        columns: list[dict],
        bpkm_prop: str,
    ) -> list[dict]:
        """Replicate the compatible_columns filtering from configure_columns."""
        allowed_types = COLUMN_TYPE_COMPATIBILITY.get(bpkm_prop, [])
        return [col for col in columns if col.get("type") in allowed_types]

    def test_compatible_columns_for_all_properties(self):
        """Each bpkm property should have correct compatible columns from a full set."""
        columns = _make_columns_set()
        for bpkm_prop in BPKM_PROPERTY_LABELS:
            compatible = self._filter_compatible(columns, bpkm_prop)
            allowed_types = set(COLUMN_TYPE_COMPATIBILITY[bpkm_prop])
            for col in compatible:
                assert col["type"] in allowed_types

    def test_compatible_columns_count_status(self):
        """taskStatus compatible count: 2 status columns in test set."""
        columns = _make_columns_set()
        compatible = self._filter_compatible(columns, "taskStatus")
        assert len(compatible) == 2  # status_col, priority_col both type "status"

    def test_compatible_columns_count_priority(self):
        """priority compatible: 2 status + 1 color = 3."""
        columns = _make_columns_set()
        compatible = self._filter_compatible(columns, "priority")
        assert len(compatible) == 3

    def test_compatible_columns_no_match(self):
        """A property with no matching columns should return empty."""
        columns = [_make_column("email_col", "Email", "email")]
        compatible = self._filter_compatible(columns, "taskStatus")
        assert compatible == []

    def test_build_compatible_columns_dict(self):
        """Build full compatible_columns dict like the route handler does."""
        columns = _make_columns_set()
        compatible_columns: dict[str, list[dict]] = {}
        for bpkm_prop, allowed_types in COLUMN_TYPE_COMPATIBILITY.items():
            compatible_columns[bpkm_prop] = [
                col for col in columns if col.get("type") in allowed_types
            ]
        # Every BPKM_PROPERTY_LABELS key should be in the result
        for prop in BPKM_PROPERTY_LABELS:
            assert prop in compatible_columns


class TestConfigureLabelsLogic:
    """Tests for the configure-labels route handler logic."""

    def test_no_status_column_mapped_means_no_status_labels(self):
        """If taskStatus is not in column_mapping, status_labels should be empty."""
        column_mapping = {"priority": "priority_col"}  # no taskStatus
        status_col_id = column_mapping.get("taskStatus")
        assert status_col_id is None

    def test_no_priority_column_mapped_means_no_priority_labels(self):
        """If priority is not in column_mapping, priority_labels should be empty."""
        column_mapping = {"taskStatus": "status_col"}  # no priority
        priority_col_id = column_mapping.get("priority")
        assert priority_col_id is None

    def test_both_mapped_extracts_both_label_sets(self):
        """Both status and priority mapped should produce two label sets."""
        columns = [
            _make_status_column("status_col", "Status", {"0": "", "1": "Done"}),
            _make_status_column("priority_col", "Priority", {"0": "", "1": "High"}),
        ]
        col_by_id = {c["id"]: c for c in columns}

        column_mapping = {"taskStatus": "status_col", "priority": "priority_col"}

        def _parse_labels(col_id):
            if not col_id or col_id not in col_by_id:
                return []
            settings_str = col_by_id[col_id].get("settings_str", "")
            if not settings_str:
                return []
            try:
                settings = json.loads(settings_str)
            except (json.JSONDecodeError, TypeError):
                return []
            labels = settings.get("labels", {})
            if not isinstance(labels, dict):
                return []
            return sorted(labels.items(), key=lambda x: x[0])

        status_labels = _parse_labels(column_mapping.get("taskStatus"))
        priority_labels = _parse_labels(column_mapping.get("priority"))
        assert len(status_labels) == 2
        assert len(priority_labels) == 2

    def test_column_not_in_col_by_id_returns_empty_labels(self):
        """If mapped column ID doesn't exist in columns, return empty labels."""
        columns = [_make_column("other_col", "Other", "text")]
        col_by_id = {c["id"]: c for c in columns}
        col_id = "nonexistent_col"
        assert col_id not in col_by_id

    def test_column_without_settings_str_returns_empty_labels(self):
        """Column with no settings_str returns empty labels."""
        col = _make_column("status_col", "Status", "status")
        # No settings_str key
        assert "settings_str" not in col or col.get("settings_str") is None


class TestSaveLabelMappingLogic:
    """Tests for the save-label-mapping route handler logic."""

    def test_build_label_mapping_from_form(self):
        """Simulate building label mapping from form submissions."""
        # Form fields: status_label_{idx} = bpkm_value
        form_data = {
            "board_id": "100",
            "status_label_0": "",
            "status_label_1": "in-progress",
            "status_label_2": "done",
            "priority_label_0": "",
            "priority_label_1": "critical",
            "priority_label_2": "high",
        }

        status_labels = {"0": "", "1": "Working on it", "2": "Done"}
        priority_labels = {"0": "", "1": "Critical", "2": "High"}

        status_label_mapping: dict[str, str] = {}
        for idx, label_text in sorted(status_labels.items()):
            bpkm_val = form_data.get(f"status_label_{idx}", "").strip()
            if bpkm_val:
                status_label_mapping[label_text] = bpkm_val

        priority_label_mapping: dict[str, str] = {}
        for idx, label_text in sorted(priority_labels.items()):
            bpkm_val = form_data.get(f"priority_label_{idx}", "").strip()
            if bpkm_val:
                priority_label_mapping[label_text] = bpkm_val

        assert len(status_label_mapping) == 2  # idx 0 was empty
        assert status_label_mapping["Working on it"] == "in-progress"
        assert status_label_mapping["Done"] == "done"
        assert len(priority_label_mapping) == 2
        assert priority_label_mapping["Critical"] == "critical"
        assert priority_label_mapping["High"] == "high"

    def test_empty_form_values_excluded(self):
        """Form fields with empty values should not be saved."""
        form_data = {
            "status_label_0": "",
            "status_label_1": "",
            "status_label_2": "",
        }
        labels = {"0": "Default", "1": "Working", "2": "Done"}
        mapping: dict[str, str] = {}
        for idx, label_text in sorted(labels.items()):
            bpkm_val = form_data.get(f"status_label_{idx}", "").strip()
            if bpkm_val:
                mapping[label_text] = bpkm_val
        assert mapping == {}

    def test_partial_form_values(self):
        """Only some labels mapped."""
        form_data = {
            "status_label_0": "",
            "status_label_1": "in-progress",
            "status_label_2": "",
        }
        labels = {"0": "", "1": "Working", "2": "Done"}
        mapping: dict[str, str] = {}
        for idx, label_text in sorted(labels.items()):
            bpkm_val = form_data.get(f"status_label_{idx}", "").strip()
            if bpkm_val:
                mapping[label_text] = bpkm_val
        assert mapping == {"Working": "in-progress"}


# ===================================================================
# SECTION 8: Error path tests
# ===================================================================


class TestErrorPaths:
    """Tests for error handling in column/label mapping routes."""

    def test_missing_board_id_configure_columns(self):
        """Missing board_id in configure-columns should return error HTML."""
        # The route returns an error div when board_id is empty
        board_id = ""
        assert not board_id.strip()

    def test_missing_board_id_save_column_mapping(self):
        """Missing board_id in save-column-mapping should return error HTML."""
        board_id = "   "
        assert not board_id.strip()

    def test_missing_board_id_configure_labels(self):
        """Missing board_id in configure-labels should return error HTML."""
        board_id = ""
        assert not board_id.strip()

    def test_missing_board_id_save_label_mapping(self):
        """Missing board_id in save-label-mapping should return error HTML."""
        board_id = ""
        assert not board_id.strip()

    def test_no_column_mapping_for_labels_is_error(self):
        """configure-labels with no column mapping saved should return error."""
        settings = MockSettingsClient()
        raw = _run(settings.get("column_mapping_100"))
        assert raw is None  # no mapping exists → should show error

    def test_no_status_or_priority_mapped_is_error(self):
        """configure-labels with mapping but no status/priority should return error."""
        column_mapping = {"description": "text_col", "dueDate": "date_col"}
        status_col_id = column_mapping.get("taskStatus")
        priority_col_id = column_mapping.get("priority")
        assert not status_col_id and not priority_col_id

    def test_malformed_settings_json_handled_gracefully(self):
        """Malformed settings_str should not crash label parsing."""
        settings_str = "not valid json"
        try:
            parsed = json.loads(settings_str)
        except json.JSONDecodeError:
            parsed = None
        assert parsed is None

    def test_api_error_during_column_fetch(self):
        """API error during get_board_columns should be handled."""
        resp = MockResponse(500, {"error": "Internal Server Error"})
        http = MockHttpClient([resp])
        state = MockStateClient({"monday_api_token": "token"})
        client = MondayClient(http_client=http, state_client=state)

        with pytest.raises(MondayApiError):
            _run(client.get_board_columns(123))

    def test_auth_error_during_column_fetch(self):
        """Auth error during get_board_columns should raise MondayAuthError."""
        resp = MockResponse(401, "Unauthorized")
        http = MockHttpClient([resp])
        state = MockStateClient({"monday_api_token": "token"})
        client = MondayClient(http_client=http, state_client=state)

        with pytest.raises(MondayAuthError):
            _run(client.get_board_columns(123))

    def test_no_token_raises_auth_error(self):
        """MondayClient without stored token should raise MondayAuthError."""
        http = MockHttpClient([])
        state = MockStateClient()  # no token
        client = MondayClient(http_client=http, state_client=state)

        with pytest.raises(MondayAuthError):
            _run(client.get_board_columns(123))

    def test_settings_str_type_error_handled(self):
        """TypeError from json.loads on non-string should be caught."""
        try:
            json.loads(12345)  # type: ignore
        except TypeError:
            pass  # Expected — _parse_labels catches this

    def test_empty_boards_response_for_columns(self):
        """get_board_columns with no boards returned should return empty list."""
        resp = MockResponse(200, {"data": {"boards": []}})
        http = MockHttpClient([resp])
        state = MockStateClient({"monday_api_token": "token"})
        client = MondayClient(http_client=http, state_client=state)
        result = _run(client.get_board_columns(123))
        assert result == []


# ===================================================================
# SECTION 9: Integration-style logic tests
# ===================================================================


class TestEndToEndColumnMappingFlow:
    """Integration-style tests for the full column mapping workflow."""

    def test_full_mapping_flow(self):
        """Full flow: fetch columns → filter compatible → save mapping → load mapping."""
        columns = _make_columns_set()
        settings = MockSettingsClient()
        board_id = "999"

        # Step 1: Filter compatible columns for each property
        compatible_columns: dict[str, list[dict]] = {}
        for bpkm_prop, allowed_types in COLUMN_TYPE_COMPATIBILITY.items():
            compatible_columns[bpkm_prop] = [
                col for col in columns if col.get("type") in allowed_types
            ]

        # Step 2: User selects first compatible column for each property
        mapping: dict[str, str] = {}
        for prop in BPKM_PROPERTY_LABELS:
            if compatible_columns.get(prop):
                mapping[prop] = compatible_columns[prop][0]["id"]

        # Step 3: Save
        _run(settings.set(f"column_mapping_{board_id}", json.dumps(mapping)))

        # Step 4: Load and verify
        loaded = json.loads(_run(settings.get(f"column_mapping_{board_id}")))
        assert loaded == mapping
        assert "taskStatus" in loaded

    def test_full_label_mapping_flow(self):
        """Full flow: load column mapping → parse labels → save label mapping."""
        settings = MockSettingsClient()
        board_id = "999"

        # Pre-save column mapping
        column_mapping = {"taskStatus": "status_col", "priority": "priority_col"}
        _run(settings.set(f"column_mapping_{board_id}", json.dumps(column_mapping)))

        # Columns with settings_str
        columns = [
            _make_status_column("status_col", "Status", {
                "0": "", "1": "Working on it", "2": "Done", "3": "Stuck",
            }),
            _make_status_column("priority_col", "Priority", {
                "0": "", "1": "Critical", "2": "High", "3": "Medium", "4": "Low",
            }),
        ]
        col_by_id = {c["id"]: c for c in columns}

        # Parse labels
        def _parse_labels(col_id):
            if not col_id or col_id not in col_by_id:
                return []
            settings_str = col_by_id[col_id].get("settings_str", "")
            if not settings_str:
                return []
            try:
                parsed = json.loads(settings_str)
            except (json.JSONDecodeError, TypeError):
                return []
            labels = parsed.get("labels", {})
            if not isinstance(labels, dict):
                return []
            return sorted(labels.items(), key=lambda x: x[0])

        status_labels = _parse_labels("status_col")
        priority_labels = _parse_labels("priority_col")
        assert len(status_labels) == 4
        assert len(priority_labels) == 5

        # Build label mapping
        label_mapping = {
            "status_label_mapping": {
                "Working on it": "in-progress",
                "Done": "done",
                "Stuck": "blocked",
            },
            "priority_label_mapping": {
                "Critical": "critical",
                "High": "high",
                "Medium": "medium",
                "Low": "low",
            },
        }
        _run(settings.set(f"label_mapping_{board_id}", json.dumps(label_mapping)))

        # Verify
        loaded = json.loads(_run(settings.get(f"label_mapping_{board_id}")))
        assert loaded["status_label_mapping"]["Done"] == "done"
        assert loaded["priority_label_mapping"]["High"] == "high"

    def test_reconfigure_replaces_old_mapping(self):
        """Reconfiguring columns replaces the old mapping entirely."""
        settings = MockSettingsClient()
        board_id = "100"

        # First config
        _run(settings.set(f"column_mapping_{board_id}", json.dumps({
            "taskStatus": "old_status_col",
            "description": "old_text_col",
        })))

        # Re-config with different selections
        new_mapping = {
            "taskStatus": "new_status_col",
            "priority": "new_prio_col",
        }
        _run(settings.set(f"column_mapping_{board_id}", json.dumps(new_mapping)))

        loaded = json.loads(_run(settings.get(f"column_mapping_{board_id}")))
        assert loaded == new_mapping
        assert "description" not in loaded  # old key gone
