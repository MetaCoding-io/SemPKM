"""Tests for layout migration utility (M032/S01/T01).

Verifies that each of the 5 legacy CSS Grid layouts maps correctly to
GridStack ``{x, y, w, h}`` positions, that unmatched slots get default
positions, and that already-gridstack blocks pass through unchanged.
"""

import pytest

from app.dashboard.migration import migrate_layout_to_gridstack


# ---------------------------------------------------------------------------
# single layout
# ---------------------------------------------------------------------------


class TestSingleLayout:
    def test_single_block_full_width(self):
        blocks = [{"type": "markdown", "slot": "main", "config": {"content": "hi"}}]
        result = migrate_layout_to_gridstack("single", blocks)
        assert len(result) == 1
        assert result[0]["x"] == 0
        assert result[0]["y"] == 0
        assert result[0]["w"] == 12
        assert result[0]["h"] == 4

    def test_multiple_blocks_stack_vertically(self):
        blocks = [
            {"type": "markdown", "slot": "main", "config": {"content": "A"}},
            {"type": "divider", "slot": "main", "config": {}},
            {"type": "markdown", "slot": "main", "config": {"content": "B"}},
        ]
        result = migrate_layout_to_gridstack("single", blocks)
        assert result[0]["y"] == 0
        assert result[1]["y"] == 4
        assert result[2]["y"] == 8
        for b in result:
            assert b["x"] == 0
            assert b["w"] == 12
            assert b["h"] == 4


# ---------------------------------------------------------------------------
# sidebar-main layout
# ---------------------------------------------------------------------------


class TestSidebarMainLayout:
    def test_sidebar_and_main_positions(self):
        blocks = [
            {"type": "markdown", "slot": "sidebar", "config": {"content": "nav"}},
            {"type": "view-embed", "slot": "main", "config": {"spec_iri": "urn:x"}},
        ]
        result = migrate_layout_to_gridstack("sidebar-main", blocks)
        sidebar = result[0]
        main = result[1]
        assert sidebar["x"] == 0
        assert sidebar["w"] == 3
        assert sidebar["h"] == 6
        assert main["x"] == 3
        assert main["w"] == 9
        assert main["h"] == 6


# ---------------------------------------------------------------------------
# grid-2x2 layout
# ---------------------------------------------------------------------------


class TestGrid2x2Layout:
    def test_four_quadrants(self):
        blocks = [
            {"type": "markdown", "slot": "top-left", "config": {"content": "TL"}},
            {"type": "markdown", "slot": "top-right", "config": {"content": "TR"}},
            {"type": "markdown", "slot": "bottom-left", "config": {"content": "BL"}},
            {"type": "divider", "slot": "bottom-right", "config": {}},
        ]
        result = migrate_layout_to_gridstack("grid-2x2", blocks)
        assert (result[0]["x"], result[0]["y"], result[0]["w"], result[0]["h"]) == (0, 0, 6, 4)
        assert (result[1]["x"], result[1]["y"], result[1]["w"], result[1]["h"]) == (6, 0, 6, 4)
        assert (result[2]["x"], result[2]["y"], result[2]["w"], result[2]["h"]) == (0, 4, 6, 4)
        assert (result[3]["x"], result[3]["y"], result[3]["w"], result[3]["h"]) == (6, 4, 6, 4)


# ---------------------------------------------------------------------------
# grid-3 layout
# ---------------------------------------------------------------------------


class TestGrid3Layout:
    def test_three_columns(self):
        blocks = [
            {"type": "markdown", "slot": "left", "config": {"content": "L"}},
            {"type": "markdown", "slot": "center", "config": {"content": "C"}},
            {"type": "markdown", "slot": "right", "config": {"content": "R"}},
        ]
        result = migrate_layout_to_gridstack("grid-3", blocks)
        assert (result[0]["x"], result[0]["y"], result[0]["w"], result[0]["h"]) == (0, 0, 4, 6)
        assert (result[1]["x"], result[1]["y"], result[1]["w"], result[1]["h"]) == (4, 0, 4, 6)
        assert (result[2]["x"], result[2]["y"], result[2]["w"], result[2]["h"]) == (8, 0, 4, 6)


# ---------------------------------------------------------------------------
# top-bottom layout
# ---------------------------------------------------------------------------


class TestTopBottomLayout:
    def test_two_rows(self):
        blocks = [
            {"type": "markdown", "slot": "top", "config": {"content": "T"}},
            {"type": "markdown", "slot": "bottom", "config": {"content": "B"}},
        ]
        result = migrate_layout_to_gridstack("top-bottom", blocks)
        assert (result[0]["x"], result[0]["y"], result[0]["w"], result[0]["h"]) == (0, 0, 12, 4)
        assert (result[1]["x"], result[1]["y"], result[1]["w"], result[1]["h"]) == (0, 4, 12, 4)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_unmatched_slot_stacks_at_bottom(self):
        """Block with unknown slot goes full-width below known slots."""
        blocks = [
            {"type": "markdown", "slot": "top-left", "config": {"content": "TL"}},
            {"type": "divider", "slot": "mystery", "config": {}},
        ]
        result = migrate_layout_to_gridstack("grid-2x2", blocks)
        # First block at (0,0,6,4) — known slot
        assert result[0]["x"] == 0
        assert result[0]["y"] == 0
        # Unknown slot stacks below the highest occupied row
        assert result[1]["x"] == 0
        assert result[1]["y"] == 4  # max_y_bottom after first block = 0+4 = 4
        assert result[1]["w"] == 12
        assert result[1]["h"] == 4

    def test_already_gridstack_passes_through(self):
        """Blocks that already have x,y,w,h are returned as-is."""
        blocks = [
            {"type": "markdown", "config": {"content": "hi"}, "x": 2, "y": 3, "w": 4, "h": 5},
        ]
        result = migrate_layout_to_gridstack("gridstack", blocks)
        assert result[0]["x"] == 2
        assert result[0]["y"] == 3
        assert result[0]["w"] == 4
        assert result[0]["h"] == 5

    def test_gridstack_layout_adds_defaults_for_missing_positions(self):
        """Blocks in a gridstack layout without positions get defaults."""
        blocks = [{"type": "divider", "config": {}}]
        result = migrate_layout_to_gridstack("gridstack", blocks)
        assert "x" in result[0]
        assert "y" in result[0]
        assert "w" in result[0]
        assert "h" in result[0]

    def test_empty_blocks_list(self):
        result = migrate_layout_to_gridstack("single", [])
        assert result == []

    def test_unknown_layout_raises(self):
        with pytest.raises(ValueError, match="Unknown legacy layout: 'nope'"):
            migrate_layout_to_gridstack("nope", [])

    def test_original_blocks_not_mutated(self):
        """Migration returns copies — original list/dicts are untouched."""
        blocks = [
            {"type": "markdown", "slot": "main", "config": {"content": "hi"}},
        ]
        result = migrate_layout_to_gridstack("single", blocks)
        assert "x" in result[0]
        assert "x" not in blocks[0]  # Original unchanged

    def test_blocks_without_slot_in_multi_slot_layout(self):
        """Blocks missing slot field in a multi-slot layout stack at end."""
        blocks = [
            {"type": "markdown", "config": {"content": "no slot"}},
        ]
        result = migrate_layout_to_gridstack("grid-2x2", blocks)
        # No slot → stacked at bottom (y=0 since nothing above)
        assert result[0]["x"] == 0
        assert result[0]["y"] == 0
        assert result[0]["w"] == 12
        assert result[0]["h"] == 4

    def test_config_deep_copied(self):
        """Config dict inside block should be deep-copied, not shared."""
        blocks = [
            {"type": "markdown", "slot": "main", "config": {"content": "hi"}},
        ]
        result = migrate_layout_to_gridstack("single", blocks)
        result[0]["config"]["content"] = "mutated"
        assert blocks[0]["config"]["content"] == "hi"
