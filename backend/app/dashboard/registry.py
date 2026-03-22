"""BlockRegistry — typed declarations for all dashboard block types.

Each block type is described by a ``BlockTypeSpec`` dataclass that captures
its display metadata (label, icon, category), expected config shape, and
default GridStack cell dimensions.  The singleton ``BLOCK_REGISTRY`` is the
single source of truth for which block types are valid and how they should
be validated.

Usage::

    from app.dashboard.registry import BLOCK_REGISTRY

    spec = BLOCK_REGISTRY.get("markdown")
    BLOCK_REGISTRY.validate_block({"type": "markdown", "config": {"content": "hi"}})
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlockTypeSpec:
    """Specification for a single dashboard block type.

    Attributes:
        type_name: Machine-readable identifier (e.g. ``"markdown"``).
        label: Human-readable display name.
        icon: Lucide icon name for the palette / UI.
        category: Grouping key (``"content"``, ``"data"``, ``"layout"``).
        config_schema: Dict mapping config key names to expected Python types
            (used for lightweight validation, not JSON Schema).
        default_w: Default GridStack width in columns (1-12).
        default_h: Default GridStack height in rows (≥ 1).
    """

    type_name: str
    label: str
    icon: str
    category: str
    config_schema: dict[str, type] = field(default_factory=dict)
    default_w: int = 6
    default_h: int = 4


class BlockRegistry:
    """Registry of all known dashboard block types.

    Provides lookup, validation, and categorisation helpers that the
    service layer and UI templates consume.
    """

    def __init__(self) -> None:
        self._specs: dict[str, BlockTypeSpec] = {}

    # -- registration -------------------------------------------------------

    def register(self, spec: BlockTypeSpec) -> None:
        """Register a block type specification."""
        if spec.type_name in self._specs:
            raise ValueError(
                f"Duplicate block type registration: '{spec.type_name}'"
            )
        self._specs[spec.type_name] = spec

    # -- lookup -------------------------------------------------------------

    def get(self, type_name: str) -> BlockTypeSpec:
        """Return the spec for *type_name*, or raise ``KeyError``."""
        try:
            return self._specs[type_name]
        except KeyError:
            raise KeyError(
                f"Unknown block type: '{type_name}'. "
                f"Valid types: {sorted(self._specs)}"
            )

    def all_types(self) -> list[str]:
        """Return a sorted list of all registered type names."""
        return sorted(self._specs)

    def all_specs(self) -> list[BlockTypeSpec]:
        """Return all registered specs, sorted by type name."""
        return [self._specs[t] for t in sorted(self._specs)]

    def by_category(self) -> dict[str, list[BlockTypeSpec]]:
        """Return specs grouped by category."""
        groups: dict[str, list[BlockTypeSpec]] = defaultdict(list)
        for spec in self.all_specs():
            groups[spec.category].append(spec)
        return dict(groups)

    # -- validation ---------------------------------------------------------

    def validate_block(self, block: dict[str, Any]) -> None:
        """Validate a single block dict against the registry.

        Checks:
        1. ``type`` field exists and is a known block type.
        2. ``config`` field is a dict.
        3. Required config keys (those declared in the spec's
           ``config_schema``) are present and have the expected type.

        Raises:
            ValueError: With a descriptive message on validation failure.
        """
        block_type = block.get("type")
        if not block_type:
            raise ValueError("Block is missing required 'type' field")

        if block_type not in self._specs:
            raise ValueError(
                f"Invalid block type: '{block_type}'. "
                f"Must be one of {sorted(self._specs)}"
            )

        config = block.get("config")
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise ValueError(
                f"Block config must be a dict, got {type(config).__name__}"
            )

        spec = self._specs[block_type]
        for key, expected_type in spec.config_schema.items():
            if key in config:
                value = config[key]
                if not isinstance(value, expected_type):
                    raise ValueError(
                        f"Block '{block_type}' config key '{key}' must be "
                        f"{expected_type.__name__}, got {type(value).__name__}"
                    )

    def validate_position(self, block: dict[str, Any]) -> None:
        """Validate GridStack position fields on a block dict.

        Checks ``x``, ``y``, ``w``, ``h`` are present, are ints, and
        fall within GridStack bounds (12-column grid).

        Raises:
            ValueError: If any position field is missing or out of bounds.
        """
        for field_name in ("x", "y", "w", "h"):
            val = block.get(field_name)
            if val is None:
                raise ValueError(
                    f"Block is missing required GridStack position field '{field_name}'"
                )
            if not isinstance(val, int):
                raise ValueError(
                    f"Block position field '{field_name}' must be int, "
                    f"got {type(val).__name__}"
                )

        x, y, w, h = block["x"], block["y"], block["w"], block["h"]
        if not (0 <= x <= 11):
            raise ValueError(f"Block 'x' must be 0-11, got {x}")
        if y < 0:
            raise ValueError(f"Block 'y' must be >= 0, got {y}")
        if not (1 <= w <= 12):
            raise ValueError(f"Block 'w' must be 1-12, got {w}")
        if h < 1:
            raise ValueError(f"Block 'h' must be >= 1, got {h}")
        if x + w > 12:
            raise ValueError(
                f"Block extends beyond grid: x={x} + w={w} = {x + w} > 12"
            )


def _build_default_registry() -> BlockRegistry:
    """Construct the default registry with all 7 built-in block types."""
    registry = BlockRegistry()

    registry.register(BlockTypeSpec(
        type_name="view-embed",
        label="View Embed",
        icon="table",
        category="data",
        config_schema={
            "spec_iri": str,
            "height": str,
            "renderer_type": str,
            "emits_context": bool,
            "listens_to_context": str,
        },
        default_w=6,
        default_h=4,
    ))

    registry.register(BlockTypeSpec(
        type_name="markdown",
        label="Markdown",
        icon="file-text",
        category="content",
        config_schema={"content": str},
        default_w=6,
        default_h=4,
    ))

    registry.register(BlockTypeSpec(
        type_name="object-embed",
        label="Object Embed",
        icon="box",
        category="data",
        config_schema={"object_iri": str, "mode": str},
        default_w=6,
        default_h=4,
    ))

    registry.register(BlockTypeSpec(
        type_name="create-form",
        label="Create Form",
        icon="plus-circle",
        category="data",
        config_schema={"target_class": str, "defaults": dict},
        default_w=6,
        default_h=6,
    ))

    registry.register(BlockTypeSpec(
        type_name="sparql-result",
        label="SPARQL Result",
        icon="database",
        category="data",
        config_schema={"query": str, "label": str},
        default_w=4,
        default_h=3,
    ))

    registry.register(BlockTypeSpec(
        type_name="divider",
        label="Divider",
        icon="minus",
        category="layout",
        config_schema={},
        default_w=12,
        default_h=1,
    ))

    registry.register(BlockTypeSpec(
        type_name="form-group",
        label="Form Group",
        icon="layers",
        category="data",
        config_schema={"slots": list, "edges": list},
        default_w=12,
        default_h=8,
    ))

    return registry


#: Module-level singleton — import this from other modules.
BLOCK_REGISTRY = _build_default_registry()
