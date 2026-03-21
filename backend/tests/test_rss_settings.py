"""Unit tests for RSS Reader app settings — manifest validation, settings
helpers (get_settings_context, save_settings), and route behavior.

Tests validate:
- Manifest declares 2 settings with correct metadata
- GET settings returns defaults when no saved values
- GET settings returns saved values when present
- POST settings saves correct key/value pairs
- POST settings handles checkbox checked/unchecked
- POST settings clamps articlesPerPage to valid range
- POST settings handles non-integer articlesPerPage gracefully
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Import app module from file path (avoids backend/app collision) ──

_app_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "rss-reader" / "app.py"
)

_spec = importlib.util.spec_from_file_location("rss_app", str(_app_path))
_app_mod = importlib.util.module_from_spec(_spec)

# Patch feedparser before exec_module (it's imported at module top-level)
import sys
if "feedparser" not in sys.modules:
    sys.modules["feedparser"] = MagicMock()

_spec.loader.exec_module(_app_mod)

get_settings_context = _app_mod.get_settings_context
save_settings = _app_mod.save_settings
SETTINGS_DEFAULTS = _app_mod.SETTINGS_DEFAULTS


# ── Fixtures ──


def _make_mock_ctx(get_side_effects=None):
    """Create a mock ctx with settings.get (AsyncMock) and settings.set (AsyncMock).

    Args:
        get_side_effects: dict mapping key -> return value for settings.get.
                         If None, settings.get returns None for all keys.
    """
    ctx = MagicMock()
    settings = MagicMock()

    if get_side_effects is not None:
        async def _get(key):
            return get_side_effects.get(key)
        settings.get = AsyncMock(side_effect=_get)
    else:
        settings.get = AsyncMock(return_value=None)

    settings.set = AsyncMock()
    ctx.settings = settings
    return ctx


# ═══════════════════════════════════════════════════════════════════════
# Manifest validation tests
# ═══════════════════════════════════════════════════════════════════════


class TestManifestSettings:
    """Test that manifest.yaml declares settings correctly."""

    def test_manifest_has_two_settings(self):
        from app.apps.manifest import parse_app_manifest
        m = parse_app_manifest(
            str(Path(__file__).resolve().parent.parent.parent / "apps" / "rss-reader" / "manifest.yaml")
        )
        assert len(m.settings) == 2

    def test_manifest_permissions_settings_true(self):
        from app.apps.manifest import parse_app_manifest
        m = parse_app_manifest(
            str(Path(__file__).resolve().parent.parent.parent / "apps" / "rss-reader" / "manifest.yaml")
        )
        assert m.permissions.settings is True

    def test_manifest_settings_keys_and_types(self):
        from app.apps.manifest import parse_app_manifest
        m = parse_app_manifest(
            str(Path(__file__).resolve().parent.parent.parent / "apps" / "rss-reader" / "manifest.yaml")
        )
        settings_by_key = {s.key: s for s in m.settings}
        assert "articlesPerPage" in settings_by_key
        assert "markReadOnOpen" in settings_by_key

        app = settings_by_key["articlesPerPage"]
        assert app.label == "Articles per page"
        assert app.inputType == "number"
        assert app.default == "50"

        mro = settings_by_key["markReadOnOpen"]
        assert mro.label == "Mark read on open"
        assert mro.inputType == "toggle"
        assert mro.default == "true"


# ═══════════════════════════════════════════════════════════════════════
# get_settings_context tests
# ═══════════════════════════════════════════════════════════════════════


class TestGetSettingsContext:
    """Test get_settings_context helper."""

    @pytest.mark.asyncio
    async def test_returns_defaults_when_no_saved_values(self):
        ctx = _make_mock_ctx()
        result = await get_settings_context(ctx)
        assert result["articles_per_page"] == "50"
        assert result["mark_read_on_open"] == "true"

    @pytest.mark.asyncio
    async def test_returns_saved_values_when_present(self):
        ctx = _make_mock_ctx(get_side_effects={
            "articlesPerPage": "25",
            "markReadOnOpen": "false",
        })
        result = await get_settings_context(ctx)
        assert result["articles_per_page"] == "25"
        assert result["mark_read_on_open"] == "false"

    @pytest.mark.asyncio
    async def test_mixed_saved_and_default(self):
        ctx = _make_mock_ctx(get_side_effects={
            "articlesPerPage": "100",
            # markReadOnOpen not set → None → default
        })
        result = await get_settings_context(ctx)
        assert result["articles_per_page"] == "100"
        assert result["mark_read_on_open"] == "true"


# ═══════════════════════════════════════════════════════════════════════
# save_settings tests
# ═══════════════════════════════════════════════════════════════════════


class TestSaveSettings:
    """Test save_settings helper."""

    @pytest.mark.asyncio
    async def test_saves_correct_values(self):
        ctx = _make_mock_ctx()
        await save_settings(ctx, {"articlesPerPage": "75", "markReadOnOpen": "on"})
        ctx.settings.set.assert_any_await("articlesPerPage", "75")
        ctx.settings.set.assert_any_await("markReadOnOpen", "true")

    @pytest.mark.asyncio
    async def test_checkbox_unchecked_saves_false(self):
        ctx = _make_mock_ctx()
        # When checkbox is unchecked, the key is absent from form data
        await save_settings(ctx, {"articlesPerPage": "50"})
        ctx.settings.set.assert_any_await("markReadOnOpen", "false")

    @pytest.mark.asyncio
    async def test_checkbox_checked_saves_true(self):
        ctx = _make_mock_ctx()
        await save_settings(ctx, {"articlesPerPage": "50", "markReadOnOpen": "on"})
        ctx.settings.set.assert_any_await("markReadOnOpen", "true")

    @pytest.mark.asyncio
    async def test_clamps_articles_per_page_too_low(self):
        ctx = _make_mock_ctx()
        await save_settings(ctx, {"articlesPerPage": "3"})
        ctx.settings.set.assert_any_await("articlesPerPage", "10")

    @pytest.mark.asyncio
    async def test_clamps_articles_per_page_too_high(self):
        ctx = _make_mock_ctx()
        await save_settings(ctx, {"articlesPerPage": "999"})
        ctx.settings.set.assert_any_await("articlesPerPage", "200")

    @pytest.mark.asyncio
    async def test_handles_non_integer_articles_per_page(self):
        ctx = _make_mock_ctx()
        await save_settings(ctx, {"articlesPerPage": "abc"})
        # Falls back to 50 (default) which is within range
        ctx.settings.set.assert_any_await("articlesPerPage", "50")

    @pytest.mark.asyncio
    async def test_handles_negative_articles_per_page(self):
        ctx = _make_mock_ctx()
        await save_settings(ctx, {"articlesPerPage": "-10"})
        # Clamps to minimum of 10
        ctx.settings.set.assert_any_await("articlesPerPage", "10")

    @pytest.mark.asyncio
    async def test_returns_success_message(self):
        ctx = _make_mock_ctx()
        msg = await save_settings(ctx, {"articlesPerPage": "50"})
        assert msg == "Settings saved"
