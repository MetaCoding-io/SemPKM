"""Unit tests for Media Scheduler app — manifest validation, IRI minting,
entry-to-media-item conversion, duration parsing, feed fetching,
dedup logic, subscribe/unsubscribe, and poll-sources task handler.

Import pattern follows test_rss_settings.py: loads the app module via
importlib.util.spec_from_file_location to avoid package path conflicts.
feedparser is mocked at sys.modules level before exec_module.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from time import struct_time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Pre-patch feedparser before importing app modules ──

_mock_feedparser = MagicMock()
sys.modules.setdefault("feedparser", _mock_feedparser)

# ── Import podcast_service via file path ──

_svc_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "media-scheduler" / "services" / "podcast_service.py"
)
_svc_spec = importlib.util.spec_from_file_location("podcast_service_test", str(_svc_path))
_svc_mod = importlib.util.module_from_spec(_svc_spec)
_svc_spec.loader.exec_module(_svc_mod)

mint_source_iri = _svc_mod.mint_source_iri
mint_item_iri = _svc_mod.mint_item_iri
parse_duration = _svc_mod.parse_duration
entry_to_media_item = _svc_mod.entry_to_media_item
get_existing_item_iris = _svc_mod.get_existing_item_iris
subscribe_podcast = _svc_mod.subscribe_podcast
unsubscribe_source = _svc_mod.unsubscribe_source
update_source_state = _svc_mod.update_source_state
check_source_exists = _svc_mod.check_source_exists
FeedFetchError = _svc_mod.FeedFetchError
fetch_feed = _svc_mod.fetch_feed
parse_feed_content = _svc_mod.parse_feed_content
MEDIA_SOURCE_TYPE = _svc_mod.MEDIA_SOURCE_TYPE
MEDIA_ITEM_TYPE = _svc_mod.MEDIA_ITEM_TYPE
MS_NS = _svc_mod.MS_NS
_struct_time_to_iso = _svc_mod._struct_time_to_iso

# ── Import app module via file path ──

_app_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "media-scheduler" / "app.py"
)
_app_spec = importlib.util.spec_from_file_location("media_scheduler_app_test", str(_app_path))
_app_mod = importlib.util.module_from_spec(_app_spec)
_app_spec.loader.exec_module(_app_mod)

poll_sources = _app_mod.poll_sources
MAX_INITIAL_ITEMS = _app_mod.MAX_INITIAL_ITEMS
_get_current_error_count = _app_mod._get_current_error_count
_format_date = _app_mod._format_date
_format_duration = _app_mod._format_duration


# ═══════════════════════════════════════════════════════════════════════
# Manifest validation tests
# ═══════════════════════════════════════════════════════════════════════


class TestManifest:
    """Manifest validation via parse_app_manifest."""

    def test_manifest_app_id(self):
        from app.apps.manifest import parse_app_manifest
        m = parse_app_manifest(
            str(Path(__file__).resolve().parent.parent.parent
                / "apps" / "media-scheduler" / "manifest.yaml")
        )
        assert m.appId == "media-scheduler"

    def test_manifest_has_one_task(self):
        from app.apps.manifest import parse_app_manifest
        m = parse_app_manifest(
            str(Path(__file__).resolve().parent.parent.parent
                / "apps" / "media-scheduler" / "manifest.yaml")
        )
        assert len(m.tasks) == 1
        assert m.tasks[0].id == "poll-sources"

    def test_manifest_permissions(self):
        from app.apps.manifest import parse_app_manifest
        m = parse_app_manifest(
            str(Path(__file__).resolve().parent.parent.parent
                / "apps" / "media-scheduler" / "manifest.yaml")
        )
        assert m.permissions.backgroundTasks is True
        assert m.permissions.sparql.read is True
        assert "object.create" in m.permissions.commands
        assert "object.patch" in m.permissions.commands

    def test_manifest_model_dependency(self):
        from app.apps.manifest import parse_app_manifest
        m = parse_app_manifest(
            str(Path(__file__).resolve().parent.parent.parent
                / "apps" / "media-scheduler" / "manifest.yaml")
        )
        assert any(d.id == "media-scheduler" for d in m.dependencies.models)


# ═══════════════════════════════════════════════════════════════════════
# IRI minting tests
# ═══════════════════════════════════════════════════════════════════════


class TestIRIMinting:
    """Test deterministic IRI generation for sources and items."""

    def test_mint_source_iri_deterministic(self):
        url = "https://example.com/podcast.xml"
        iri1 = mint_source_iri(url)
        iri2 = mint_source_iri(url)
        assert iri1 == iri2

    def test_mint_source_iri_different_inputs(self):
        iri1 = mint_source_iri("https://example.com/a.xml")
        iri2 = mint_source_iri("https://example.com/b.xml")
        assert iri1 != iri2

    def test_mint_source_iri_has_correct_prefix(self):
        iri = mint_source_iri("https://example.com/feed.xml")
        assert iri.startswith("urn:sempkm:app:media-scheduler:source-")

    def test_mint_item_iri_deterministic(self):
        source = "urn:sempkm:app:media-scheduler:source-abc123"
        iri1 = mint_item_iri(source, "episode-1")
        iri2 = mint_item_iri(source, "episode-1")
        assert iri1 == iri2

    def test_mint_item_iri_different_episodes(self):
        source = "urn:sempkm:app:media-scheduler:source-abc123"
        iri1 = mint_item_iri(source, "episode-1")
        iri2 = mint_item_iri(source, "episode-2")
        assert iri1 != iri2

    def test_mint_item_iri_different_sources(self):
        src1 = "urn:sempkm:app:media-scheduler:source-aaa"
        src2 = "urn:sempkm:app:media-scheduler:source-bbb"
        iri1 = mint_item_iri(src1, "episode-1")
        iri2 = mint_item_iri(src2, "episode-1")
        assert iri1 != iri2

    def test_mint_item_iri_has_correct_prefix(self):
        source = "urn:sempkm:app:media-scheduler:source-abc123"
        iri = mint_item_iri(source, "episode-1")
        assert iri.startswith("urn:sempkm:app:media-scheduler:item-")


# ═══════════════════════════════════════════════════════════════════════
# Duration parsing tests
# ═══════════════════════════════════════════════════════════════════════


class TestParseDuration:
    """Test iTunes-style duration string parsing."""

    def test_hhmmss(self):
        assert parse_duration("1:23:45") == 5025

    def test_mmss(self):
        assert parse_duration("45:30") == 2730

    def test_bare_seconds(self):
        assert parse_duration("3600") == 3600

    def test_empty_string(self):
        assert parse_duration("") is None

    def test_none_input(self):
        assert parse_duration(None) is None

    def test_invalid_string(self):
        assert parse_duration("invalid") is None

    def test_zero_duration(self):
        assert parse_duration("0:00") == 0

    def test_large_duration(self):
        # 10 hours
        assert parse_duration("10:00:00") == 36000

    def test_padded_whitespace(self):
        assert parse_duration("  3600  ") == 3600


# ═══════════════════════════════════════════════════════════════════════
# entry_to_media_item tests
# ═══════════════════════════════════════════════════════════════════════


class TestEntryToMediaItem:
    """Test feedparser entry → MediaItem conversion."""

    def _make_entry(self, **overrides) -> dict:
        """Create a standard feedparser entry dict with reasonable defaults."""
        base = {
            "id": "https://example.com/ep1",
            "title": "Episode 1: Introduction",
            "link": "https://example.com/ep1",
            "summary": "An introduction to the podcast.",
            "published_parsed": struct_time((2026, 3, 15, 12, 0, 0, 5, 74, 0)),
        }
        base.update(overrides)
        return base

    def test_basic_conversion(self):
        source_iri = "urn:sempkm:app:media-scheduler:source-abc"
        entry = self._make_entry()
        result = entry_to_media_item(entry, source_iri)

        assert result["type"] == MEDIA_ITEM_TYPE
        assert result["iri"].startswith("urn:sempkm:app:media-scheduler:item-")
        assert result["properties"]["dcterms:title"] == "Episode 1: Introduction"
        assert result["properties"][f"{MS_NS}status"] == "queued"
        assert result["properties"][f"{MS_NS}mediaSource"] == source_iri

    def test_external_id_from_entry_id(self):
        entry = self._make_entry(id="guid-123")
        result = entry_to_media_item(entry, "urn:test:source")
        assert result["properties"][f"{MS_NS}externalId"] == "guid-123"

    def test_external_id_falls_back_to_link(self):
        entry = self._make_entry()
        del entry["id"]
        result = entry_to_media_item(entry, "urn:test:source")
        assert result["properties"][f"{MS_NS}externalId"] == "https://example.com/ep1"

    def test_enclosure_url_from_enclosures(self):
        entry = self._make_entry(
            enclosures=[{"href": "https://example.com/ep.mp3", "type": "audio/mpeg"}]
        )
        result = entry_to_media_item(entry, "urn:test:source")
        assert result["properties"][f"{MS_NS}enclosureUrl"] == "https://example.com/ep.mp3"

    def test_enclosure_url_falls_back_to_link(self):
        entry = self._make_entry()
        result = entry_to_media_item(entry, "urn:test:source")
        # No enclosures → falls back to entry.link
        assert result["properties"][f"{MS_NS}enclosureUrl"] == "https://example.com/ep1"

    def test_published_date_conversion(self):
        entry = self._make_entry()
        result = entry_to_media_item(entry, "urn:test:source")
        assert "dcterms:created" in result["properties"]
        # Should be an ISO datetime string
        created = result["properties"]["dcterms:created"]
        assert "2026" in created

    def test_duration_from_itunes(self):
        entry = self._make_entry(itunes_duration="1:30:00")
        result = entry_to_media_item(entry, "urn:test:source")
        assert result["properties"][f"{MS_NS}duration"] == 5400

    def test_no_duration_when_missing(self):
        entry = self._make_entry()
        result = entry_to_media_item(entry, "urn:test:source")
        assert f"{MS_NS}duration" not in result["properties"]

    def test_description_from_summary(self):
        entry = self._make_entry(summary="A test summary.")
        result = entry_to_media_item(entry, "urn:test:source")
        assert result["properties"]["dcterms:description"] == "A test summary."

    def test_thumbnail_from_image(self):
        entry = self._make_entry(image={"href": "https://example.com/thumb.jpg"})
        result = entry_to_media_item(entry, "urn:test:source")
        assert result["properties"][f"{MS_NS}thumbnailUrl"] == "https://example.com/thumb.jpg"

    def test_iri_determinism(self):
        """Same entry + same source → same IRI."""
        entry = self._make_entry()
        source = "urn:test:source"
        iri1 = entry_to_media_item(entry, source)["iri"]
        iri2 = entry_to_media_item(entry, source)["iri"]
        assert iri1 == iri2


# ═══════════════════════════════════════════════════════════════════════
# struct_time conversion
# ═══════════════════════════════════════════════════════════════════════


class TestStructTimeToIso:
    """Test struct_time → ISO 8601 conversion."""

    def test_valid_struct_time(self):
        t = struct_time((2026, 3, 15, 12, 0, 0, 5, 74, 0))
        result = _struct_time_to_iso(t)
        assert result is not None
        assert "2026" in result

    def test_none_returns_none(self):
        assert _struct_time_to_iso(None) is None


# ═══════════════════════════════════════════════════════════════════════
# App helper functions
# ═══════════════════════════════════════════════════════════════════════


class TestAppHelpers:
    """Test helper functions in app.py."""

    def test_get_current_error_count_normal(self):
        binding = {"errorCount": {"value": "3"}}
        assert _get_current_error_count(binding) == 3

    def test_get_current_error_count_missing(self):
        assert _get_current_error_count({}) == 0

    def test_get_current_error_count_invalid(self):
        binding = {"errorCount": {"value": "abc"}}
        assert _get_current_error_count(binding) == 0

    def test_format_date_valid(self):
        result = _format_date("2026-03-15T12:00:00+00:00")
        assert result == "Mar 15, 2026"

    def test_format_date_none(self):
        assert _format_date(None) == ""

    def test_format_date_empty(self):
        assert _format_date("") == ""

    def test_format_date_invalid(self):
        assert _format_date("not-a-date") == ""

    def test_format_duration_hhmmss(self):
        assert _format_duration(5025) == "1:23:45"

    def test_format_duration_mmss(self):
        assert _format_duration(90) == "1:30"

    def test_format_duration_zero(self):
        assert _format_duration(0) == "0:00"

    def test_format_duration_none(self):
        assert _format_duration(None) == ""

    def test_format_duration_negative(self):
        assert _format_duration(-1) == ""

    def test_max_initial_items(self):
        assert MAX_INITIAL_ITEMS == 50


# ═══════════════════════════════════════════════════════════════════════
# Dedup / get_existing_item_iris tests
# ═══════════════════════════════════════════════════════════════════════


class TestDedup:
    """Test deduplication logic."""

    @pytest.mark.asyncio
    async def test_get_existing_item_iris_returns_set(self):
        graph_client = MagicMock()
        graph_client.query = AsyncMock(return_value={
            "results": {"bindings": [
                {"item": {"value": "urn:item:1"}},
                {"item": {"value": "urn:item:2"}},
            ]}
        })
        result = await get_existing_item_iris(graph_client, "urn:test:source")
        assert result == {"urn:item:1", "urn:item:2"}

    @pytest.mark.asyncio
    async def test_get_existing_item_iris_empty(self):
        graph_client = MagicMock()
        graph_client.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        result = await get_existing_item_iris(graph_client, "urn:test:source")
        assert result == set()

    def test_dedup_filtering_logic(self):
        """Simulate the poll-sources dedup: items whose IRIs are already known
        should be excluded from the new_items list."""
        source_iri = "urn:test:source"
        entries = [
            {"id": "ep1", "title": "Episode 1", "link": "https://example.com/ep1"},
            {"id": "ep2", "title": "Episode 2", "link": "https://example.com/ep2"},
            {"id": "ep3", "title": "Episode 3", "link": "https://example.com/ep3"},
        ]
        items = [entry_to_media_item(e, source_iri) for e in entries]
        # Suppose ep1 and ep3 already exist
        existing_iris = {items[0]["iri"], items[2]["iri"]}
        new_items = [it for it in items if it["iri"] not in existing_iris]
        assert len(new_items) == 1
        assert new_items[0]["properties"]["dcterms:title"] == "Episode 2"


# ═══════════════════════════════════════════════════════════════════════
# subscribe_podcast tests
# ═══════════════════════════════════════════════════════════════════════


class TestSubscribePodcast:
    """Test subscribe_podcast with mocked context."""

    @pytest.mark.asyncio
    async def test_subscribe_new(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        ctx.commands.execute = AsyncMock()

        result = await subscribe_podcast(ctx, "https://example.com/feed.xml")
        assert result["status"] == "created"
        assert result["iri"].startswith("urn:sempkm:app:media-scheduler:source-")
        ctx.commands.execute.assert_awaited_once()

        # Verify the object.create params
        call_args = ctx.commands.execute.call_args
        assert call_args[0][0] == "object.create"
        params = call_args[0][1]
        assert params["type"] == MEDIA_SOURCE_TYPE
        assert params["properties"][f"{MS_NS}sourceType"] == "podcast"

    @pytest.mark.asyncio
    async def test_subscribe_duplicate(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": [
                {"source": {"value": "urn:existing:source"}}
            ]}
        })
        ctx.commands.execute = AsyncMock()

        result = await subscribe_podcast(ctx, "https://example.com/feed.xml")
        assert result["status"] == "duplicate"
        assert result["iri"] == "urn:existing:source"
        ctx.commands.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_subscribe_with_custom_title(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        ctx.commands.execute = AsyncMock()

        result = await subscribe_podcast(ctx, "https://example.com/feed.xml", title="My Podcast")
        assert result["status"] == "created"
        params = ctx.commands.execute.call_args[0][1]
        assert params["properties"]["dcterms:title"] == "My Podcast"


# ═══════════════════════════════════════════════════════════════════════
# unsubscribe_source tests
# ═══════════════════════════════════════════════════════════════════════


class TestUnsubscribeSource:
    """Test unsubscribe_source (soft-delete)."""

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        ctx = MagicMock()
        ctx.commands.execute = AsyncMock()

        result = await unsubscribe_source(ctx, "urn:test:source")
        assert result["status"] == "unsubscribed"
        ctx.commands.execute.assert_awaited_once()
        call_args = ctx.commands.execute.call_args
        assert call_args[0][0] == "object.patch"
        props = call_args[0][1]["properties"]
        assert props[f"{MS_NS}sourceType"] == "inactive"


# ═══════════════════════════════════════════════════════════════════════
# update_source_state tests
# ═══════════════════════════════════════════════════════════════════════


class TestUpdateSourceState:
    """Test source state update via object.patch."""

    @pytest.mark.asyncio
    async def test_updates_last_polled(self):
        ctx = MagicMock()
        ctx.commands.execute = AsyncMock()

        await update_source_state(ctx, "urn:test:source", last_polled="2026-03-15T12:00:00Z")
        ctx.commands.execute.assert_awaited_once()
        props = ctx.commands.execute.call_args[0][1]["properties"]
        assert props[f"{MS_NS}lastPolled"] == "2026-03-15T12:00:00Z"

    @pytest.mark.asyncio
    async def test_skips_when_all_none(self):
        ctx = MagicMock()
        ctx.commands.execute = AsyncMock()

        await update_source_state(ctx, "urn:test:source")
        ctx.commands.execute.assert_not_awaited()


# ═══════════════════════════════════════════════════════════════════════
# FeedFetchError tests
# ═══════════════════════════════════════════════════════════════════════


class TestFeedFetchError:
    """Test custom exception."""

    def test_attributes(self):
        err = FeedFetchError("https://example.com/feed", 404)
        assert err.url == "https://example.com/feed"
        assert err.status_code == 404

    def test_str(self):
        err = FeedFetchError("https://example.com/feed", 500)
        assert "500" in str(err)
        assert "https://example.com/feed" in str(err)


# ═══════════════════════════════════════════════════════════════════════
# fetch_feed tests
# ═══════════════════════════════════════════════════════════════════════


class TestFetchFeed:
    """Test fetch_feed with mocked HTTP client."""

    @pytest.mark.asyncio
    async def test_200_response(self):
        response = MagicMock()
        response.status_code = 200
        response.content = b"<rss>...</rss>"
        response.headers = {
            "etag": '"abc123"',
            "last-modified": "Sun, 15 Mar 2026 12:00:00 GMT",
            "content-type": "application/xml",
        }
        http_client = MagicMock()
        http_client.get = AsyncMock(return_value=response)

        content, headers, status = await fetch_feed(http_client, "https://example.com/feed.xml")
        assert status == 200
        assert content == b"<rss>...</rss>"
        assert headers["etag"] == '"abc123"'

    @pytest.mark.asyncio
    async def test_304_response(self):
        response = MagicMock()
        response.status_code = 304
        response.headers = {
            "content-type": "",
        }
        http_client = MagicMock()
        http_client.get = AsyncMock(return_value=response)

        content, headers, status = await fetch_feed(
            http_client, "https://example.com/feed.xml",
            etag='"old"', last_modified="Sun, 01 Mar 2026"
        )
        assert status == 304
        assert content is None

    @pytest.mark.asyncio
    async def test_404_raises(self):
        response = MagicMock()
        response.status_code = 404
        response.headers = {"content-type": "text/html"}
        http_client = MagicMock()
        http_client.get = AsyncMock(return_value=response)

        with pytest.raises(FeedFetchError) as exc_info:
            await fetch_feed(http_client, "https://example.com/missing.xml")
        assert exc_info.value.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# poll_sources task handler tests
# ═══════════════════════════════════════════════════════════════════════


class TestPollSources:
    """Test poll-sources task handler with mocked context."""

    def _make_source_binding(self, feed_url="https://example.com/feed.xml",
                              source_iri="urn:test:source-1",
                              source_type="podcast",
                              etag=None, error_count="0"):
        binding = {
            "source": {"value": source_iri},
            "feedUrl": {"value": feed_url},
            "sourceType": {"value": source_type},
            "errorCount": {"value": error_count},
        }
        if etag:
            binding["etag"] = {"value": etag}
        return binding

    @pytest.mark.asyncio
    async def test_poll_empty_sources(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        result = await poll_sources(ctx)
        assert result == {"feeds_polled": 0, "items_created": 0}

    @pytest.mark.asyncio
    async def test_poll_304_not_modified(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": [self._make_source_binding(etag='"old"')]}
        })
        ctx.commands.execute = AsyncMock()

        # Must patch on _app_mod — poll_sources has its own bound reference
        with patch.object(_app_mod, "fetch_feed", new_callable=AsyncMock) as mock_fetch, \
             patch.object(_app_mod, "update_source_state", new_callable=AsyncMock) as mock_update:
            mock_fetch.return_value = (None, {"etag": '"old"', "last_modified": None, "content_type": ""}, 304)

            result = await poll_sources(ctx)
            assert result["feeds_polled"] == 1
            assert result["items_created"] == 0

    @pytest.mark.asyncio
    async def test_poll_creates_items(self):
        source_iri = "urn:test:source-1"
        ctx = MagicMock()
        ctx.app_id = "media-scheduler"
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": [self._make_source_binding(source_iri=source_iri)]}
        })

        # Build mock entries that feedparser would produce
        mock_entries = [
            {"id": "ep1", "title": "Ep 1", "link": "https://example.com/ep1"},
            {"id": "ep2", "title": "Ep 2", "link": "https://example.com/ep2"},
        ]

        # Mock the batch context manager
        mock_batch = MagicMock()
        mock_batch.add = MagicMock()
        mock_batch_cm = AsyncMock()
        mock_batch_cm.__aenter__ = AsyncMock(return_value=mock_batch)
        mock_batch_cm.__aexit__ = AsyncMock(return_value=False)
        ctx.commands.bulk = MagicMock(return_value=mock_batch_cm)

        # Patch on _app_mod where poll_sources binds its references
        with patch.object(_app_mod, "fetch_feed", new_callable=AsyncMock) as mock_fetch, \
             patch.object(_app_mod, "parse_feed_content") as mock_parse, \
             patch.object(_app_mod, "get_existing_item_iris", new_callable=AsyncMock) as mock_existing, \
             patch.object(_app_mod, "update_source_state", new_callable=AsyncMock):

            mock_fetch.return_value = (
                b"<rss>content</rss>",
                {"etag": '"new"', "last_modified": None, "content_type": "application/xml"},
                200,
            )
            mock_parse.return_value = {"entries": mock_entries, "bozo": False}
            mock_existing.return_value = set()

            result = await poll_sources(ctx)
            assert result["feeds_polled"] == 1
            assert result["items_created"] == 2
            assert mock_batch.add.call_count == 2

    @pytest.mark.asyncio
    async def test_poll_http_error_increments_error_count(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": [self._make_source_binding(error_count="2")]}
        })
        ctx.commands.execute = AsyncMock()

        # Patch on _app_mod where poll_sources binds its references
        with patch.object(_app_mod, "fetch_feed", new_callable=AsyncMock) as mock_fetch, \
             patch.object(_app_mod, "update_source_state", new_callable=AsyncMock) as mock_update:

            mock_fetch.side_effect = FeedFetchError("https://example.com/feed.xml", 500)

            result = await poll_sources(ctx)
            assert result["feeds_polled"] == 0
            assert result["items_created"] == 0

            # Verify error count was incremented (from 2 → 3)
            mock_update.assert_awaited_once()
            call_kwargs = mock_update.call_args
            assert call_kwargs.kwargs.get("error_count") == 3
