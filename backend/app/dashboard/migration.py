"""Layout migration utility — converts legacy CSS Grid layouts to GridStack positions.

Maps each of the 5 old CSS Grid layout templates to GridStack ``{x, y, w, h}``
position values based on the block's ``slot`` field.  Blocks that already have
GridStack positions pass through unchanged.

Usage::

    from app.dashboard.migration import migrate_layout_to_gridstack

    blocks = migrate_layout_to_gridstack("grid-2x2", old_blocks)
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Slot → GridStack position mappings for each legacy layout
#
# Each mapping is  slot_name → (x, y, w, h).
# ---------------------------------------------------------------------------

LAYOUT_SLOT_POSITIONS: dict[str, dict[str, tuple[int, int, int, int]]] = {
    "single": {
        # Single-column: all blocks stack vertically, full width.
        # The y-offset is computed dynamically (see _stack_y below).
        "main": (0, 0, 12, 4),
    },
    "sidebar-main": {
        "sidebar": (0, 0, 3, 6),
        "main": (3, 0, 9, 6),
    },
    "grid-2x2": {
        "top-left": (0, 0, 6, 4),
        "top-right": (6, 0, 6, 4),
        "bottom-left": (0, 4, 6, 4),
        "bottom-right": (6, 4, 6, 4),
    },
    "grid-3": {
        "left": (0, 0, 4, 6),
        "center": (4, 0, 4, 6),
        "right": (8, 0, 4, 6),
    },
    "top-bottom": {
        "top": (0, 0, 12, 4),
        "bottom": (0, 4, 12, 4),
    },
}


def migrate_layout_to_gridstack(
    layout: str,
    blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Map blocks from a legacy CSS Grid layout to GridStack positions.

    Each block in *blocks* is shallow-copied and augmented with ``x``, ``y``,
    ``w``, ``h`` fields derived from the layout's slot definitions.

    If a block already carries GridStack position fields (i.e. has ``x``),
    it is returned unchanged — this makes the function idempotent.

    Blocks whose ``slot`` doesn't match any known slot in the layout are
    stacked vertically at the end of the grid at full width.

    Args:
        layout: Legacy layout name (e.g. ``"grid-2x2"``).
        blocks: List of block dicts, each with at least ``type`` and ``config``.

    Returns:
        New list of block dicts, each augmented with ``x, y, w, h``.

    Raises:
        ValueError: If *layout* is not a recognised legacy layout.
    """
    if layout == "gridstack":
        # Already a GridStack layout — pass through (ensure positions exist).
        return [_ensure_position(b) for b in blocks]

    slot_map = LAYOUT_SLOT_POSITIONS.get(layout)
    if slot_map is None:
        raise ValueError(
            f"Unknown legacy layout: '{layout}'. "
            f"Known layouts: {sorted(LAYOUT_SLOT_POSITIONS)}"
        )

    result: list[dict[str, Any]] = []
    # Track the maximum y+h used so we can stack unmatched blocks below.
    max_y_bottom = 0

    # For the "single" layout, all blocks go full-width and stack vertically.
    if layout == "single":
        y_cursor = 0
        for block in blocks:
            out = _copy_block(block)
            if _has_position(out):
                result.append(out)
                max_y_bottom = max(max_y_bottom, out.get("y", 0) + out.get("h", 4))
                continue
            out["x"] = 0
            out["y"] = y_cursor
            out["w"] = 12
            out["h"] = 4
            y_cursor += 4
            max_y_bottom = max(max_y_bottom, y_cursor)
            result.append(out)
        logger.info(
            "Migrated %d blocks from layout '%s' to gridstack (single-column stack)",
            len(blocks), layout,
        )
        return result

    # For multi-slot layouts, assign by slot name.
    for block in blocks:
        out = _copy_block(block)
        if _has_position(out):
            result.append(out)
            max_y_bottom = max(max_y_bottom, out.get("y", 0) + out.get("h", 4))
            continue

        slot = out.get("slot", "")
        pos = slot_map.get(slot)
        if pos is not None:
            out["x"], out["y"], out["w"], out["h"] = pos
            max_y_bottom = max(max_y_bottom, out["y"] + out["h"])
        else:
            # Unmatched slot — stack at the bottom, full width.
            out["x"] = 0
            out["y"] = max_y_bottom
            out["w"] = 12
            out["h"] = 4
            max_y_bottom += 4
            logger.debug(
                "Block slot '%s' not found in layout '%s', stacking at y=%d",
                slot, layout, out["y"],
            )
        result.append(out)

    logger.info(
        "Migrated %d blocks from layout '%s' to gridstack positions",
        len(blocks), layout,
    )
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _copy_block(block: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of a block dict (deep-copy config)."""
    out = dict(block)
    if "config" in out:
        out["config"] = copy.deepcopy(out["config"])
    return out


def _has_position(block: dict[str, Any]) -> bool:
    """Return True if *block* already has GridStack position fields."""
    return "x" in block and "y" in block and "w" in block and "h" in block


def _ensure_position(block: dict[str, Any]) -> dict[str, Any]:
    """Ensure a gridstack block has position fields, adding defaults if missing."""
    out = _copy_block(block)
    if not _has_position(out):
        out.setdefault("x", 0)
        out.setdefault("y", 0)
        out.setdefault("w", 6)
        out.setdefault("h", 4)
    return out
