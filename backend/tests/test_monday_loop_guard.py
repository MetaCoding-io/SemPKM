"""Unit tests for the LoopGuard TTL echo-prevention cache.

Loads the loop_guard module from the apps directory via importlib so the
app does not need to be installed as a package.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Load loop_guard module from apps directory
# ---------------------------------------------------------------------------

_SERVICES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "monday-sync"
    / "services"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_loop_guard_mod = _load_module("loop_guard", _SERVICES_DIR / "loop_guard.py")
LoopGuard = _loop_guard_mod.LoopGuard


# ===================================================================
# Helpers
# ===================================================================

def _make_guard(ttl: float = 30.0) -> LoopGuard:
    """Convenience factory."""
    return LoopGuard(ttl_seconds=ttl)


# ===================================================================
# TestLoopGuardBasic
# ===================================================================


class TestLoopGuardBasic:
    """Core mark / is_echo / len behaviour (no time mocking needed)."""

    def test_mark_and_check(self):
        g = _make_guard()
        g.mark_pushed("100", "status")
        assert g.is_echo("100", "status") is True

    def test_unmarked_item_not_echo(self):
        g = _make_guard()
        assert g.is_echo("999", "status") is False

    def test_mark_overwrites_timestamp(self):
        g = _make_guard()
        g.mark_pushed("100", "status")
        first_ts = g._marks["100:status"]
        # Re-mark — timestamp should be >= first
        g.mark_pushed("100", "status")
        assert g._marks["100:status"] >= first_ts

    def test_different_items_independent(self):
        g = _make_guard()
        g.mark_pushed("100", "status")
        assert g.is_echo("100", "status") is True
        assert g.is_echo("200", "status") is False

    def test_wildcard_column_id(self):
        g = _make_guard()
        g.mark_pushed("100")  # default column_id="*"
        assert g.is_echo("100") is True
        assert g.is_echo("100", "*") is True

    def test_specific_column_ids(self):
        g = _make_guard()
        g.mark_pushed("100", "status")
        g.mark_pushed("100", "priority")
        assert g.is_echo("100", "status") is True
        assert g.is_echo("100", "priority") is True
        assert g.is_echo("100", "date") is False

    def test_len_reflects_mark_count(self):
        g = _make_guard()
        assert len(g) == 0
        g.mark_pushed("a", "x")
        assert len(g) == 1
        g.mark_pushed("b", "y")
        assert len(g) == 2
        # Re-marking same key doesn't increase count
        g.mark_pushed("a", "x")
        assert len(g) == 2

    def test_initial_state_empty(self):
        g = _make_guard()
        assert len(g) == 0
        assert g.is_echo("any") is False


# ===================================================================
# TestLoopGuardTTL — time mocking via unittest.mock.patch
# ===================================================================


class TestLoopGuardTTL:
    """TTL expiry logic tested by mocking ``time.time``."""

    def test_echo_within_ttl(self):
        g = _make_guard(ttl=30.0)
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            g.mark_pushed("100")
        with patch.object(_loop_guard_mod.time, "time", return_value=1010.0):
            assert g.is_echo("100") is True  # 10s < 30s

    def test_echo_expired_beyond_ttl(self):
        g = _make_guard(ttl=30.0)
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            g.mark_pushed("100")
        with patch.object(_loop_guard_mod.time, "time", return_value=1031.0):
            assert g.is_echo("100") is False  # 31s >= 30s

    def test_echo_at_exact_boundary(self):
        g = _make_guard(ttl=30.0)
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            g.mark_pushed("100")
        # age == ttl → NOT an echo (uses strict <)
        with patch.object(_loop_guard_mod.time, "time", return_value=1030.0):
            assert g.is_echo("100") is False

    def test_custom_ttl(self):
        g = _make_guard(ttl=5.0)
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            g.mark_pushed("100")
        with patch.object(_loop_guard_mod.time, "time", return_value=1004.0):
            assert g.is_echo("100") is True
        with patch.object(_loop_guard_mod.time, "time", return_value=1006.0):
            assert g.is_echo("100") is False

    def test_zero_ttl_always_expired(self):
        g = _make_guard(ttl=0.0)
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            g.mark_pushed("100")
        # Even at the same instant, age (0) is NOT < 0 → False
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            assert g.is_echo("100") is False

    def test_cleanup_removes_expired(self):
        g = _make_guard(ttl=10.0)
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            g.mark_pushed("a")
            g.mark_pushed("b")
        with patch.object(_loop_guard_mod.time, "time", return_value=1011.0):
            removed = g.cleanup()
        assert removed == 2
        assert len(g) == 0

    def test_cleanup_preserves_fresh(self):
        g = _make_guard(ttl=10.0)
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            g.mark_pushed("old")
        with patch.object(_loop_guard_mod.time, "time", return_value=1008.0):
            g.mark_pushed("new")
        # At t=1011, "old" is 11s (expired), "new" is 3s (fresh)
        with patch.object(_loop_guard_mod.time, "time", return_value=1011.0):
            removed = g.cleanup()
        assert removed == 1
        assert len(g) == 1
        with patch.object(_loop_guard_mod.time, "time", return_value=1011.0):
            assert g.is_echo("new") is True
            assert g.is_echo("old") is False

    def test_cleanup_returns_count(self):
        g = _make_guard(ttl=5.0)
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            g.mark_pushed("a")
            g.mark_pushed("b")
            g.mark_pushed("c")
        with patch.object(_loop_guard_mod.time, "time", return_value=1006.0):
            assert g.cleanup() == 3


# ===================================================================
# TestLoopGuardEdgeCases
# ===================================================================


class TestLoopGuardEdgeCases:
    """Edge cases — unusual inputs, concurrency, mutation safety."""

    def test_empty_item_id(self):
        g = _make_guard()
        g.mark_pushed("", "col")
        assert g.is_echo("", "col") is True
        assert len(g) == 1

    def test_none_item_id_coerced(self):
        """Passing None as item_id shouldn't crash — str coercion produces 'None:*'."""
        g = _make_guard()
        # The _key helper does f"{item_id}:{column_id}" which will str-coerce None
        g.mark_pushed(None)  # type: ignore[arg-type]
        assert g.is_echo(None) is True  # type: ignore[arg-type]

    def test_numeric_item_id_as_string(self):
        g = _make_guard()
        g.mark_pushed("12345")
        assert g.is_echo("12345") is True

    def test_large_item_id(self):
        big_id = "x" * 10_000
        g = _make_guard()
        g.mark_pushed(big_id)
        assert g.is_echo(big_id) is True

    def test_special_characters_in_id(self):
        g = _make_guard()
        for item_id in ["abc:def", "foo/bar", "a=b&c", "hello world", "日本語"]:
            g.mark_pushed(item_id, "col")
            assert g.is_echo(item_id, "col") is True

    def test_concurrent_marks_different_items(self):
        g = _make_guard()
        for i in range(500):
            g.mark_pushed(str(i))
        assert len(g) == 500
        assert g.is_echo("0") is True
        assert g.is_echo("499") is True

    def test_cleanup_on_empty_guard(self):
        g = _make_guard()
        assert g.cleanup() == 0
        assert len(g) == 0

    def test_mark_after_expiry_refreshes(self):
        g = _make_guard(ttl=10.0)
        with patch.object(_loop_guard_mod.time, "time", return_value=1000.0):
            g.mark_pushed("100")
        with patch.object(_loop_guard_mod.time, "time", return_value=1011.0):
            assert g.is_echo("100") is False  # expired
        # Re-mark at t=1011
        with patch.object(_loop_guard_mod.time, "time", return_value=1011.0):
            g.mark_pushed("100")
        with patch.object(_loop_guard_mod.time, "time", return_value=1015.0):
            assert g.is_echo("100") is True  # fresh again

    def test_is_echo_does_not_mutate(self):
        g = _make_guard()
        g.mark_pushed("100", "col")
        marks_before = dict(g._marks)
        g.is_echo("100", "col")
        g.is_echo("999", "other")
        assert g._marks == marks_before
