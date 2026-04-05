"""Tests for save diff logic: _normalize_value_for_compare and _compute_changed_properties.

These helpers live in app.browser.objects and filter form-submitted properties
against current triplestore values so that only truly changed properties
produce events.
"""

import pytest

from app.browser.objects import _compute_changed_properties, _normalize_value_for_compare


# ---------------------------------------------------------------------------
# _normalize_value_for_compare
# ---------------------------------------------------------------------------

class TestNormalizeValueForCompare:
    """Verify datetime normalization and pass-through of non-datetime strings."""

    def test_full_iso_datetime_with_timezone(self):
        """Full ISO datetime with microseconds and UTC offset → minute precision."""
        result = _normalize_value_for_compare("2026-04-05T12:30:45.123456+00:00")
        assert result == "2026-04-05T12:30"

    def test_datetime_with_z_suffix(self):
        """Datetime ending in Z → minute precision, Z stripped."""
        result = _normalize_value_for_compare("2026-04-05T12:30:45Z")
        assert result == "2026-04-05T12:30"

    def test_datetime_local_already_truncated(self):
        """Datetime-local format (no seconds) → unchanged."""
        result = _normalize_value_for_compare("2026-04-05T12:30")
        assert result == "2026-04-05T12:30"

    def test_datetime_with_seconds_no_tz(self):
        """Datetime with seconds but no timezone → truncated to minutes."""
        result = _normalize_value_for_compare("2026-04-05T12:30:45")
        assert result == "2026-04-05T12:30"

    def test_datetime_positive_offset(self):
        """Datetime with positive timezone offset → stripped and truncated."""
        result = _normalize_value_for_compare("2026-04-05T14:00:00+05:30")
        assert result == "2026-04-05T14:00"

    def test_datetime_negative_offset(self):
        """Datetime with negative timezone offset → stripped and truncated."""
        result = _normalize_value_for_compare("2026-04-05T08:00:00-04:00")
        assert result == "2026-04-05T08:00"

    def test_plain_date_passthrough(self):
        """Plain date string (no T) → returned as-is."""
        result = _normalize_value_for_compare("2026-04-05")
        assert result == "2026-04-05"

    def test_non_datetime_string_passthrough(self):
        """Non-datetime string → returned as-is."""
        result = _normalize_value_for_compare("hello world")
        assert result == "hello world"

    def test_uri_passthrough(self):
        """URI string → returned as-is."""
        result = _normalize_value_for_compare("http://example.org/thing")
        assert result == "http://example.org/thing"

    def test_empty_string_passthrough(self):
        """Empty string → returned as-is."""
        result = _normalize_value_for_compare("")
        assert result == ""


# ---------------------------------------------------------------------------
# _compute_changed_properties
# ---------------------------------------------------------------------------

class TestComputeChangedProperties:
    """Verify diff logic between form and triplestore values."""

    def test_unchanged_properties_empty_result(self):
        """Identical values → no properties in changed dict."""
        form = {
            "http://purl.org/dc/terms/title": ["My Note"],
            "http://www.w3.org/2000/01/rdf-schema#label": ["A label"],
        }
        current = {
            "http://purl.org/dc/terms/title": ["My Note"],
            "http://www.w3.org/2000/01/rdf-schema#label": ["A label"],
        }
        result = _compute_changed_properties(form, current)
        assert result == {}

    def test_one_property_changed(self):
        """One value differs → only that property in result."""
        form = {
            "http://purl.org/dc/terms/title": ["Updated Title"],
            "http://www.w3.org/2000/01/rdf-schema#label": ["Same"],
        }
        current = {
            "http://purl.org/dc/terms/title": ["Old Title"],
            "http://www.w3.org/2000/01/rdf-schema#label": ["Same"],
        }
        result = _compute_changed_properties(form, current)
        assert result == {"http://purl.org/dc/terms/title": ["Updated Title"]}

    def test_datetime_unchanged_different_format(self):
        """Same datetime in different formats → not in changed dict."""
        form = {
            "http://purl.org/dc/terms/created": ["2026-04-05T12:30"],
        }
        current = {
            "http://purl.org/dc/terms/created": ["2026-04-05T12:30:45.123456+00:00"],
        }
        result = _compute_changed_properties(form, current)
        assert result == {}

    def test_datetime_with_z_vs_local(self):
        """Datetime with Z suffix vs datetime-local → equal after normalization."""
        form = {
            "http://purl.org/dc/terms/modified": ["2026-04-05T12:30"],
        }
        current = {
            "http://purl.org/dc/terms/modified": ["2026-04-05T12:30:00Z"],
        }
        result = _compute_changed_properties(form, current)
        assert result == {}

    def test_multi_value_same_different_order(self):
        """Multi-valued property with same values in different order → not changed."""
        form = {
            "http://www.w3.org/2004/02/skos/core#altLabel": ["beta", "alpha", "gamma"],
        }
        current = {
            "http://www.w3.org/2004/02/skos/core#altLabel": ["gamma", "alpha", "beta"],
        }
        result = _compute_changed_properties(form, current)
        assert result == {}

    def test_multi_value_actually_changed(self):
        """Multi-valued property with different values → in changed dict."""
        form = {
            "http://www.w3.org/2004/02/skos/core#altLabel": ["alpha", "delta"],
        }
        current = {
            "http://www.w3.org/2004/02/skos/core#altLabel": ["alpha", "beta"],
        }
        result = _compute_changed_properties(form, current)
        assert result == {
            "http://www.w3.org/2004/02/skos/core#altLabel": ["alpha", "delta"]
        }

    def test_new_property_in_form(self):
        """Property in form but not in current → in changed dict."""
        form = {
            "http://purl.org/dc/terms/description": ["A description"],
        }
        current = {}
        result = _compute_changed_properties(form, current)
        assert result == {
            "http://purl.org/dc/terms/description": ["A description"]
        }

    def test_property_deleted_in_form(self):
        """Property with empty value in form but present in current → in changed dict."""
        form = {
            "http://purl.org/dc/terms/title": [""],
        }
        current = {
            "http://purl.org/dc/terms/title": ["Old Title"],
        }
        result = _compute_changed_properties(form, current)
        assert result == {"http://purl.org/dc/terms/title": [""]}

    def test_empty_form_empty_current(self):
        """Both empty → empty result."""
        result = _compute_changed_properties({}, {})
        assert result == {}

    def test_preserves_original_form_values(self):
        """Changed dict must use original (non-normalized) form values."""
        form = {
            "http://purl.org/dc/terms/created": ["2026-04-05T15:00:00+00:00"],
        }
        current = {
            "http://purl.org/dc/terms/created": ["2026-04-05T12:00:00+00:00"],
        }
        result = _compute_changed_properties(form, current)
        # The returned value should be the original form value, not normalized
        assert result == {
            "http://purl.org/dc/terms/created": ["2026-04-05T15:00:00+00:00"]
        }


class TestDctermsModifiedIntegration:
    """Verify that dcterms:modified only appears when other changes exist.

    This tests the pattern used in save_object(): inject dcterms:modified
    into changed_properties only when the dict is non-empty.
    """

    def test_no_changes_no_modified(self):
        """When nothing changed, dcterms:modified should not be injected."""
        form = {"http://purl.org/dc/terms/title": ["Same"]}
        current = {"http://purl.org/dc/terms/title": ["Same"]}
        changed = _compute_changed_properties(form, current)
        # Simulate the save_object() pattern: only add modified if changed is non-empty
        if changed:
            changed["http://purl.org/dc/terms/modified"] = ["2026-04-05T12:30"]
        assert "http://purl.org/dc/terms/modified" not in changed

    def test_real_changes_get_modified(self):
        """When something changed, dcterms:modified should be present."""
        form = {"http://purl.org/dc/terms/title": ["New Title"]}
        current = {"http://purl.org/dc/terms/title": ["Old Title"]}
        changed = _compute_changed_properties(form, current)
        if changed:
            changed["http://purl.org/dc/terms/modified"] = ["2026-04-05T12:30"]
        assert "http://purl.org/dc/terms/modified" in changed
        assert changed["http://purl.org/dc/terms/title"] == ["New Title"]
