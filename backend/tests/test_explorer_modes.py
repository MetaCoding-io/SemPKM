"""Tests for the explorer mode registry and handler dispatch.

Validates:
- EXPLORER_MODES contains exactly the expected mode keys
- All handlers are async callables
- Registry lookup returns the correct handler per mode
- Unknown modes are not in the registry (validates 400 path logic)
"""

import asyncio
import inspect

import pytest

from app.browser.workspace import (
    EXPLORER_MODES,
    _handle_by_tag,
    _handle_by_type,
    _handle_hierarchy,
)


class TestExplorerModeRegistry:
    """Unit tests for the EXPLORER_MODES registry."""

    def test_registry_contains_expected_modes(self):
        """Registry has exactly by-type, hierarchy, and by-tag."""
        assert set(EXPLORER_MODES.keys()) == {"by-type", "hierarchy", "by-tag"}

    def test_registry_has_three_entries(self):
        """Registry has exactly 3 entries."""
        assert len(EXPLORER_MODES) == 3

    def test_all_handlers_are_callable(self):
        """Every handler in the registry is callable."""
        for mode, handler in EXPLORER_MODES.items():
            assert callable(handler), f"Handler for mode '{mode}' is not callable"

    def test_all_handlers_are_async(self):
        """Every handler is an async (coroutine) function."""
        for mode, handler in EXPLORER_MODES.items():
            assert inspect.iscoroutinefunction(handler), (
                f"Handler for mode '{mode}' is not an async function"
            )

    def test_by_type_maps_to_correct_handler(self):
        """by-type mode maps to _handle_by_type."""
        assert EXPLORER_MODES["by-type"] is _handle_by_type

    def test_hierarchy_maps_to_correct_handler(self):
        """hierarchy mode maps to _handle_hierarchy."""
        assert EXPLORER_MODES["hierarchy"] is _handle_hierarchy

    def test_by_tag_maps_to_correct_handler(self):
        """by-tag mode maps to _handle_by_tag."""
        assert EXPLORER_MODES["by-tag"] is _handle_by_tag

    def test_unknown_mode_not_in_registry(self):
        """Unknown mode key is not in registry — validates 400 path."""
        assert "invalid" not in EXPLORER_MODES
        assert "unknown" not in EXPLORER_MODES
        assert "" not in EXPLORER_MODES
        assert EXPLORER_MODES.get("nonexistent") is None
