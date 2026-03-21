"""Tests for the OPML parser pure function.

Exercises ``parse_opml()`` with valid OPML, edge cases, error paths, and
encoding scenarios.  No running Docker stack required.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Load the opml_parser module by file path ──
_parser_path = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "rss-reader"
    / "services"
    / "opml_parser.py"
)
_spec = importlib.util.spec_from_file_location("opml_parser", str(_parser_path))
_mod = importlib.util.module_from_spec(_spec)
sys.modules["opml_parser"] = _mod
_spec.loader.exec_module(_mod)
parse_opml = _mod.parse_opml

# ── Load the app module by file path (for process_opml_import + routes) ──
_app_path = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "rss-reader"
    / "app.py"
)
_app_spec = importlib.util.spec_from_file_location("rss_reader_app_mod", str(_app_path))
_app_mod = importlib.util.module_from_spec(_app_spec)
sys.modules["rss_reader_app_mod"] = _app_mod
_app_spec.loader.exec_module(_app_mod)
process_opml_import = _app_mod.process_opml_import


# ── Helpers ──

def _opml(body_inner: str, encoding: str = "utf-8") -> bytes:
    """Wrap *body_inner* in a minimal OPML document and return bytes."""
    xml = (
        f'<?xml version="1.0" encoding="{encoding}"?>'
        f"<opml version=\"2.0\"><head><title>Test</title></head>"
        f"<body>{body_inner}</body></opml>"
    )
    return xml.encode(encoding)


# ═══════════════════════════════════════════════════════════════════════
# Happy-path tests
# ═══════════════════════════════════════════════════════════════════════

class TestFlatFeeds:
    """OPML with no category folders — feeds directly under <body>."""

    def test_single_feed(self):
        data = _opml(
            '<outline text="My Blog" xmlUrl="https://example.com/feed.xml" '
            'htmlUrl="https://example.com"/>'
        )
        result = parse_opml(data)
        assert len(result) == 1
        assert result[0] == {
            "url": "https://example.com/feed.xml",
            "title": "My Blog",
            "html_url": "https://example.com",
            "category": None,
        }

    def test_multiple_flat_feeds(self):
        data = _opml(
            '<outline text="A" xmlUrl="https://a.com/feed"/>'
            '<outline text="B" xmlUrl="https://b.com/feed"/>'
            '<outline text="C" xmlUrl="https://c.com/feed"/>'
        )
        result = parse_opml(data)
        assert len(result) == 3
        assert all(f["category"] is None for f in result)
        assert [f["url"] for f in result] == [
            "https://a.com/feed",
            "https://b.com/feed",
            "https://c.com/feed",
        ]


class TestSingleLevelCategories:
    """OPML with one level of category folders."""

    def test_feeds_in_category(self):
        data = _opml(
            '<outline text="Tech">'
            '  <outline text="Ars" xmlUrl="https://ars.com/feed"/>'
            '  <outline text="HN" xmlUrl="https://hn.com/feed"/>'
            "</outline>"
        )
        result = parse_opml(data)
        assert len(result) == 2
        assert all(f["category"] == "Tech" for f in result)

    def test_multiple_categories(self):
        data = _opml(
            '<outline text="Tech">'
            '  <outline text="Ars" xmlUrl="https://ars.com/feed"/>'
            "</outline>"
            '<outline text="News">'
            '  <outline text="BBC" xmlUrl="https://bbc.com/feed"/>'
            "</outline>"
        )
        result = parse_opml(data)
        assert len(result) == 2
        assert result[0]["category"] == "Tech"
        assert result[1]["category"] == "News"


class TestNestedCategories:
    """OPML with 2+ levels of category nesting."""

    def test_two_level_nesting(self):
        data = _opml(
            '<outline text="Tech">'
            '  <outline text="Blogs">'
            '    <outline text="Daring Fireball" xmlUrl="https://df.com/feed"/>'
            "  </outline>"
            "</outline>"
        )
        result = parse_opml(data)
        assert len(result) == 1
        assert result[0]["category"] == "Tech/Blogs"

    def test_three_level_nesting(self):
        data = _opml(
            '<outline text="Tech">'
            '  <outline text="Blogs">'
            '    <outline text="Python">'
            '      <outline text="PlanetPy" xmlUrl="https://planet.py/rss"/>'
            "    </outline>"
            "  </outline>"
            "</outline>"
        )
        result = parse_opml(data)
        assert len(result) == 1
        assert result[0]["category"] == "Tech/Blogs/Python"


class TestMixedOutlines:
    """Categories and bare feeds at the same level."""

    def test_mixed_feeds_and_categories(self):
        data = _opml(
            '<outline text="Standalone" xmlUrl="https://solo.com/feed"/>'
            '<outline text="Tech">'
            '  <outline text="Wired" xmlUrl="https://wired.com/feed"/>'
            "</outline>"
        )
        result = parse_opml(data)
        assert len(result) == 2
        assert result[0]["category"] is None
        assert result[0]["title"] == "Standalone"
        assert result[1]["category"] == "Tech"


# ═══════════════════════════════════════════════════════════════════════
# Attribute handling
# ═══════════════════════════════════════════════════════════════════════

class TestTitleFallback:
    """Feed title resolution: text > title attr > xmlUrl."""

    def test_uses_text_attribute(self):
        data = _opml(
            '<outline text="My Feed" title="Alternate" xmlUrl="https://x.com/feed"/>'
        )
        result = parse_opml(data)
        assert result[0]["title"] == "My Feed"

    def test_falls_back_to_title_attribute(self):
        data = _opml(
            '<outline title="Title Only" xmlUrl="https://x.com/feed"/>'
        )
        result = parse_opml(data)
        assert result[0]["title"] == "Title Only"

    def test_falls_back_to_url_when_both_missing(self):
        data = _opml(
            '<outline xmlUrl="https://x.com/feed"/>'
        )
        result = parse_opml(data)
        assert result[0]["title"] == "https://x.com/feed"

    def test_falls_back_to_url_when_text_empty(self):
        data = _opml(
            '<outline text="" title="" xmlUrl="https://x.com/feed"/>'
        )
        result = parse_opml(data)
        assert result[0]["title"] == "https://x.com/feed"


class TestHtmlUrl:
    """htmlUrl attribute → html_url field."""

    def test_html_url_populated(self):
        data = _opml(
            '<outline text="F" xmlUrl="https://x.com/feed" htmlUrl="https://x.com"/>'
        )
        assert parse_opml(data)[0]["html_url"] == "https://x.com"

    def test_html_url_none_when_absent(self):
        data = _opml(
            '<outline text="F" xmlUrl="https://x.com/feed"/>'
        )
        assert parse_opml(data)[0]["html_url"] is None

    def test_html_url_none_when_empty(self):
        data = _opml(
            '<outline text="F" xmlUrl="https://x.com/feed" htmlUrl=""/>'
        )
        assert parse_opml(data)[0]["html_url"] is None


# ═══════════════════════════════════════════════════════════════════════
# Error / edge cases
# ═══════════════════════════════════════════════════════════════════════

class TestEmptyBody:
    """OPML with an empty <body> element."""

    def test_empty_body_returns_empty_list(self):
        data = _opml("")
        assert parse_opml(data) == []


class TestMissingBody:
    """OPML with no <body> element at all."""

    def test_no_body_returns_empty_list(self):
        xml = b'<?xml version="1.0"?><opml version="2.0"><head/></opml>'
        assert parse_opml(xml) == []


class TestInvalidXml:
    """Malformed XML must not raise — returns []."""

    def test_not_well_formed(self):
        assert parse_opml(b"<not xml") == []

    def test_completely_garbage(self):
        assert parse_opml(b"\x00\xff\xfe garbage") == []

    def test_empty_bytes(self):
        assert parse_opml(b"") == []


class TestEncoding:
    """OPML with explicit encoding declaration."""

    def test_utf8_with_special_chars(self):
        data = _opml(
            '<outline text="Ünïcödé Fëëd" xmlUrl="https://x.com/feed"/>'
        )
        result = parse_opml(data)
        assert result[0]["title"] == "Ünïcödé Fëëd"

    def test_bytes_with_xml_prolog_encoding(self):
        """Pass bytes with an encoding declaration — the XML parser handles it."""
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<opml version="2.0"><head/><body>'
            '<outline text="Café" xmlUrl="https://cafe.com/rss"/>'
            "</body></opml>"
        ).encode("utf-8")
        result = parse_opml(xml)
        assert len(result) == 1
        assert result[0]["title"] == "Café"


# ═══════════════════════════════════════════════════════════════════════
# Integration tests — process_opml_import()
# ═══════════════════════════════════════════════════════════════════════


def _make_mock_ctx(subscribe_results=None):
    """Build a mock AppContext for import route testing.

    Args:
        subscribe_results: list of dicts that subscribe() should return,
            one per call.  Use None for default (all created).

    Returns:
        (mock_ctx, mock_subscribe) — mock_subscribe is the patched function
        so tests can inspect call counts / args.
    """
    ctx = AsyncMock()
    ctx.commands.execute = AsyncMock()
    ctx.graph.query = AsyncMock(return_value={"results": {"bindings": []}})
    ctx.render_template = MagicMock(return_value="<html>template</html>")
    return ctx


def _three_feed_opml() -> bytes:
    """Return OPML bytes with 3 feeds for integration tests."""
    return _opml(
        '<outline text="Feed A" xmlUrl="https://a.com/feed"/>'
        '<outline text="Feed B" xmlUrl="https://b.com/feed"/>'
        '<outline text="Feed C" xmlUrl="https://c.com/feed"/>'
    )


def _categorized_opml() -> bytes:
    """Return OPML bytes with feeds inside a category."""
    return _opml(
        '<outline text="Tech">'
        '  <outline text="Ars" xmlUrl="https://ars.com/feed"/>'
        '  <outline text="Wired" xmlUrl="https://wired.com/feed"/>'
        "</outline>"
        '<outline text="No Category" xmlUrl="https://solo.com/feed"/>'
    )


class TestProcessOpmlImportSuccess:
    """process_opml_import() with successful subscriptions."""

    @pytest.mark.asyncio
    async def test_three_feeds_all_created(self):
        """All 3 feeds are new — subscribe called 3 times, created=3."""
        ctx = _make_mock_ctx()
        # subscribe() is called via the real code path — mock the underlying
        # ctx.graph.query to return no existing sub, ctx.commands.execute to succeed
        ctx.graph.query.return_value = {"results": {"bindings": []}}
        ctx.commands.execute.return_value = {}

        result = await process_opml_import(ctx, _three_feed_opml())

        assert result["created"] == 3
        assert result["duplicate"] == 0
        assert result["errors"] == 0
        assert len(result["feeds"]) == 3
        assert all(f["status"] == "created" for f in result["feeds"])

    @pytest.mark.asyncio
    async def test_subscribe_called_for_each_feed(self):
        """subscribe() triggers object.create for each feed."""
        ctx = _make_mock_ctx()
        ctx.graph.query.return_value = {"results": {"bindings": []}}
        ctx.commands.execute.return_value = {}

        await process_opml_import(ctx, _three_feed_opml())

        # Each subscribe call: 1 query (check exists) + 1 execute (object.create)
        # 3 feeds → 3 queries + 3 executes
        assert ctx.graph.query.call_count == 3
        assert ctx.commands.execute.call_count == 3


class TestProcessOpmlImportDuplicates:
    """process_opml_import() with duplicate subscriptions."""

    @pytest.mark.asyncio
    async def test_some_duplicates(self):
        """2 feeds already exist, 1 is new — created=1, duplicate=2."""
        ctx = _make_mock_ctx()

        # First two queries return existing subscription, third returns none
        ctx.graph.query.side_effect = [
            {"results": {"bindings": [{"sub": {"value": "urn:existing-1"}}]}},
            {"results": {"bindings": [{"sub": {"value": "urn:existing-2"}}]}},
            {"results": {"bindings": []}},
        ]
        ctx.commands.execute.return_value = {}

        result = await process_opml_import(ctx, _three_feed_opml())

        assert result["created"] == 1
        assert result["duplicate"] == 2
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_all_duplicates(self):
        """All feeds already exist — created=0, duplicate=3."""
        ctx = _make_mock_ctx()
        ctx.graph.query.return_value = {
            "results": {"bindings": [{"sub": {"value": "urn:existing"}}]}
        }

        result = await process_opml_import(ctx, _three_feed_opml())

        assert result["created"] == 0
        assert result["duplicate"] == 3
        assert result["errors"] == 0
        # No object.create calls when all are duplicates
        ctx.commands.execute.assert_not_called()


class TestProcessOpmlImportEmpty:
    """process_opml_import() with empty or invalid content."""

    @pytest.mark.asyncio
    async def test_empty_opml(self):
        """Empty body → created=0, no subscribe calls."""
        ctx = _make_mock_ctx()

        result = await process_opml_import(ctx, _opml(""))

        assert result["created"] == 0
        assert result["duplicate"] == 0
        assert result["errors"] == 0
        assert result["feeds"] == []
        ctx.graph.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_xml(self):
        """Invalid XML → created=0, no subscribe calls."""
        ctx = _make_mock_ctx()

        result = await process_opml_import(ctx, b"<not valid xml")

        assert result["created"] == 0
        assert result["duplicate"] == 0
        assert result["errors"] == 0
        assert result["feeds"] == []


class TestProcessOpmlImportCategories:
    """process_opml_import() preserves OPML categories as bpkm:tags."""

    @pytest.mark.asyncio
    async def test_category_patched_on_created_feeds(self):
        """Feeds with a category get object.patch for bpkm:tags."""
        ctx = _make_mock_ctx()
        ctx.graph.query.return_value = {"results": {"bindings": []}}
        ctx.commands.execute.return_value = {}

        result = await process_opml_import(ctx, _categorized_opml())

        assert result["created"] == 3

        # Count object.patch calls (for tags) vs object.create calls
        execute_calls = ctx.commands.execute.call_args_list
        create_calls = [c for c in execute_calls if c[0][0] == "object.create"]
        patch_calls = [c for c in execute_calls if c[0][0] == "object.patch"]

        assert len(create_calls) == 3
        # Only the 2 feeds inside "Tech" category get patched, not the bare one
        assert len(patch_calls) == 2

        # Verify the patch payload
        for call in patch_calls:
            params = call[0][1]
            assert params["properties"]["https://bpkm.org/ontology/tags"] == "Tech"

    @pytest.mark.asyncio
    async def test_no_patch_for_uncategorized_feeds(self):
        """Feeds without a category do not get object.patch for tags."""
        ctx = _make_mock_ctx()
        ctx.graph.query.return_value = {"results": {"bindings": []}}
        ctx.commands.execute.return_value = {}

        opml_data = _opml(
            '<outline text="Plain" xmlUrl="https://plain.com/feed"/>'
        )
        result = await process_opml_import(ctx, opml_data)

        assert result["created"] == 1
        # Only 1 execute call: object.create — no patch
        assert ctx.commands.execute.call_count == 1
        assert ctx.commands.execute.call_args[0][0] == "object.create"

    @pytest.mark.asyncio
    async def test_no_patch_for_duplicate_feeds_with_category(self):
        """Duplicate feeds with categories do NOT get patched."""
        ctx = _make_mock_ctx()
        ctx.graph.query.return_value = {
            "results": {"bindings": [{"sub": {"value": "urn:existing"}}]}
        }

        result = await process_opml_import(ctx, _categorized_opml())

        assert result["created"] == 0
        assert result["duplicate"] == 3
        ctx.commands.execute.assert_not_called()


class TestProcessOpmlImportErrors:
    """process_opml_import() error handling."""

    @pytest.mark.asyncio
    async def test_subscribe_exception_increments_error_count(self):
        """If subscribe() raises for one feed, error count increments, others succeed."""
        ctx = _make_mock_ctx()

        # First call: raises, second & third: succeed
        call_count = 0

        async def mock_query(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Network timeout")
            return {"results": {"bindings": []}}

        ctx.graph.query.side_effect = mock_query
        ctx.commands.execute.return_value = {}

        result = await process_opml_import(ctx, _three_feed_opml())

        assert result["errors"] == 1
        assert result["created"] == 2
        assert result["duplicate"] == 0
        # Error feed has status "error"
        error_feeds = [f for f in result["feeds"] if f["status"] == "error"]
        assert len(error_feeds) == 1
        assert "Network timeout" in error_feeds[0]["error"]

    @pytest.mark.asyncio
    async def test_tag_patch_failure_does_not_fail_import(self):
        """If tag patching fails, the feed is still counted as created."""
        ctx = _make_mock_ctx()
        ctx.graph.query.return_value = {"results": {"bindings": []}}

        # object.create succeeds; object.patch raises
        call_count = 0

        async def mock_execute(cmd, params):
            nonlocal call_count
            call_count += 1
            if cmd == "object.patch":
                raise RuntimeError("Patch failed")
            return {}

        ctx.commands.execute.side_effect = mock_execute

        opml_data = _opml(
            '<outline text="Tech">'
            '  <outline text="Ars" xmlUrl="https://ars.com/feed"/>'
            "</outline>"
        )

        result = await process_opml_import(ctx, opml_data)

        # Feed is still created despite tag patch failure
        assert result["created"] == 1
        assert result["errors"] == 0

