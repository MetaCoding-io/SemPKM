"""Tests for BlockRegistry (M032/S01/T01).

Verifies block type declarations, lookup, validation, categorisation,
and position validation.
"""

import pytest

from app.dashboard.registry import BLOCK_REGISTRY, BlockTypeSpec, BlockRegistry


# ---------------------------------------------------------------------------
# Registration & lookup
# ---------------------------------------------------------------------------


class TestRegistration:
    """All 6 built-in block types are registered correctly."""

    EXPECTED_TYPES = {
        "view-embed",
        "markdown",
        "object-embed",
        "create-form",
        "sparql-result",
        "divider",
        "form-group",
        "stat-card",
        "chart",
        "heading",
    }

    def test_all_ten_types_registered(self):
        assert set(BLOCK_REGISTRY.all_types()) == self.EXPECTED_TYPES

    def test_all_types_returns_sorted(self):
        types = BLOCK_REGISTRY.all_types()
        assert types == sorted(types)

    def test_get_returns_correct_spec(self):
        spec = BLOCK_REGISTRY.get("markdown")
        assert spec.type_name == "markdown"
        assert spec.label == "Markdown"
        assert spec.icon == "file-text"
        assert spec.category == "content"

    def test_form_group_spec_correct(self):
        spec = BLOCK_REGISTRY.get("form-group")
        assert spec.type_name == "form-group"
        assert spec.label == "Form Group"
        assert spec.icon == "layers"
        assert spec.category == "data"
        assert spec.config_schema == {"slots": list, "edges": list}
        assert spec.default_w == 12
        assert spec.default_h == 8

    def test_get_unknown_type_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown block type: 'bogus'"):
            BLOCK_REGISTRY.get("bogus")

    @pytest.mark.parametrize("type_name", EXPECTED_TYPES)
    def test_each_type_has_required_fields(self, type_name):
        spec = BLOCK_REGISTRY.get(type_name)
        assert spec.type_name == type_name
        assert spec.label  # non-empty
        assert spec.icon  # non-empty
        assert spec.category in ("content", "data", "layout")
        assert isinstance(spec.config_schema, dict)
        assert 1 <= spec.default_w <= 12
        assert spec.default_h >= 1

    def test_all_specs_returns_all(self):
        specs = BLOCK_REGISTRY.all_specs()
        assert len(specs) == 10
        assert all(isinstance(s, BlockTypeSpec) for s in specs)

    def test_stat_card_spec(self):
        spec = BLOCK_REGISTRY.get("stat-card")
        assert spec.label == "Stat Card"
        assert spec.icon == "hash"
        assert spec.category == "data"
        assert set(spec.config_schema.keys()) == {"query", "label", "icon", "color"}
        assert spec.default_w == 3
        assert spec.default_h == 2

    def test_chart_spec(self):
        spec = BLOCK_REGISTRY.get("chart")
        assert spec.label == "Chart"
        assert spec.icon == "bar-chart-3"
        assert spec.category == "data"
        assert set(spec.config_schema.keys()) == {"query", "chart_type", "label"}
        assert spec.default_w == 6
        assert spec.default_h == 4

    def test_heading_spec(self):
        spec = BLOCK_REGISTRY.get("heading")
        assert spec.label == "Heading"
        assert spec.icon == "heading"
        assert spec.category == "content"
        assert set(spec.config_schema.keys()) == {"text", "level", "subtitle", "align"}
        assert spec.default_w == 12
        assert spec.default_h == 2


# ---------------------------------------------------------------------------
# Categorisation
# ---------------------------------------------------------------------------


class TestByCategory:
    def test_groups_have_expected_categories(self):
        groups = BLOCK_REGISTRY.by_category()
        assert "content" in groups
        assert "data" in groups
        assert "layout" in groups

    def test_content_category_contains_markdown(self):
        groups = BLOCK_REGISTRY.by_category()
        type_names = [s.type_name for s in groups["content"]]
        assert "markdown" in type_names

    def test_data_category_contains_view_embed(self):
        groups = BLOCK_REGISTRY.by_category()
        type_names = [s.type_name for s in groups["data"]]
        assert "view-embed" in type_names

    def test_layout_category_contains_divider(self):
        groups = BLOCK_REGISTRY.by_category()
        type_names = [s.type_name for s in groups["layout"]]
        assert "divider" in type_names


# ---------------------------------------------------------------------------
# Block validation
# ---------------------------------------------------------------------------


class TestValidateBlock:
    def test_valid_markdown_block(self):
        """No exception for a well-formed markdown block."""
        BLOCK_REGISTRY.validate_block({
            "type": "markdown",
            "config": {"content": "Hello world"},
        })

    def test_valid_divider_block(self):
        """Divider has an empty config — should pass."""
        BLOCK_REGISTRY.validate_block({
            "type": "divider",
            "config": {},
        })

    def test_valid_block_missing_config_key(self):
        """Config keys are optional — missing ones don't fail."""
        BLOCK_REGISTRY.validate_block({
            "type": "view-embed",
            "config": {},
        })

    def test_rejects_unknown_type(self):
        with pytest.raises(ValueError, match="Invalid block type: 'nope'"):
            BLOCK_REGISTRY.validate_block({"type": "nope", "config": {}})

    def test_rejects_missing_type(self):
        with pytest.raises(ValueError, match="missing required 'type' field"):
            BLOCK_REGISTRY.validate_block({"config": {}})

    def test_rejects_non_dict_config(self):
        with pytest.raises(ValueError, match="Block config must be a dict"):
            BLOCK_REGISTRY.validate_block({"type": "markdown", "config": "oops"})

    def test_rejects_wrong_config_value_type(self):
        with pytest.raises(ValueError, match="must be str"):
            BLOCK_REGISTRY.validate_block({
                "type": "markdown",
                "config": {"content": 42},
            })

    def test_accepts_block_without_config_key(self):
        """Block with no 'config' key at all — defaults to empty dict."""
        BLOCK_REGISTRY.validate_block({"type": "divider"})


# ---------------------------------------------------------------------------
# Position validation
# ---------------------------------------------------------------------------


class TestValidatePosition:
    def test_valid_position(self):
        BLOCK_REGISTRY.validate_position({
            "type": "markdown", "x": 0, "y": 0, "w": 6, "h": 4,
        })

    def test_missing_x_raises(self):
        with pytest.raises(ValueError, match="missing required.*'x'"):
            BLOCK_REGISTRY.validate_position({"y": 0, "w": 6, "h": 4})

    def test_x_out_of_bounds(self):
        with pytest.raises(ValueError, match="'x' must be 0-11"):
            BLOCK_REGISTRY.validate_position({"x": 12, "y": 0, "w": 1, "h": 1})

    def test_negative_y(self):
        with pytest.raises(ValueError, match="'y' must be >= 0"):
            BLOCK_REGISTRY.validate_position({"x": 0, "y": -1, "w": 6, "h": 4})

    def test_w_zero(self):
        with pytest.raises(ValueError, match="'w' must be 1-12"):
            BLOCK_REGISTRY.validate_position({"x": 0, "y": 0, "w": 0, "h": 4})

    def test_extends_beyond_grid(self):
        with pytest.raises(ValueError, match="extends beyond grid"):
            BLOCK_REGISTRY.validate_position({"x": 7, "y": 0, "w": 6, "h": 4})


# ---------------------------------------------------------------------------
# Duplicate registration guard
# ---------------------------------------------------------------------------


class TestDuplicateRegistration:
    def test_duplicate_raises_value_error(self):
        reg = BlockRegistry()
        spec = BlockTypeSpec(
            type_name="test-block", label="Test", icon="test",
            category="test", default_w=6, default_h=4,
        )
        reg.register(spec)
        with pytest.raises(ValueError, match="Duplicate block type"):
            reg.register(spec)
