"""Unit tests for Media Scheduler app — manifest validation, IRI minting,
entry-to-media-item conversion, duration parsing, feed fetching,
dedup logic, subscribe/unsubscribe, and poll-sources task handler.

Import pattern follows test_rss_settings.py: loads the app module via
importlib.util.spec_from_file_location to avoid package path conflicts.
feedparser is mocked at sys.modules level before exec_module.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import uuid
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
generate_plan_task = _app_mod.generate_plan_task
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

    def test_manifest_has_tasks(self):
        from app.apps.manifest import parse_app_manifest
        m = parse_app_manifest(
            str(Path(__file__).resolve().parent.parent.parent
                / "apps" / "media-scheduler" / "manifest.yaml")
        )
        assert len(m.tasks) == 2
        assert m.tasks[0].id == "poll-sources"
        assert m.tasks[1].id == "generate-plan"

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


# ── Import rules_service via file path ──

_rules_svc_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "media-scheduler" / "services" / "rules_service.py"
)
_rules_svc_spec = importlib.util.spec_from_file_location("rules_service_test", str(_rules_svc_path))
_rules_svc_mod = importlib.util.module_from_spec(_rules_svc_spec)
_rules_svc_spec.loader.exec_module(_rules_svc_mod)

validate_rule = _rules_svc_mod.validate_rule
load_rules = _rules_svc_mod.load_rules
save_rules = _rules_svc_mod.save_rules
add_rule = _rules_svc_mod.add_rule
update_rule = _rules_svc_mod.update_rule
delete_rule = _rules_svc_mod.delete_rule
toggle_rule = _rules_svc_mod.toggle_rule
evaluate_rules = _rules_svc_mod.evaluate_rules
_matches_condition = _rules_svc_mod._matches_condition
RULES_STATE_KEY = _rules_svc_mod.RULES_STATE_KEY
DEFAULT_DURATIONS = _rules_svc_mod.DEFAULT_DURATIONS


# ═══════════════════════════════════════════════════════════════════════
# Rule validation tests
# ═══════════════════════════════════════════════════════════════════════


class TestRuleValidation:
    """Test validate_rule with various inputs."""

    def test_valid_rule_returns_complete_dict(self):
        rule = validate_rule({"name": "Commute podcasts", "priority": 5})
        assert rule["name"] == "Commute podcasts"
        assert rule["priority"] == 5
        assert rule["enabled"] is True
        assert "id" in rule
        assert isinstance(rule["conditions"], dict)
        assert isinstance(rule["action"], dict)

    def test_generates_uuid_when_missing(self):
        rule = validate_rule({"name": "Test rule"})
        assert len(rule["id"]) == 36  # UUID format

    def test_preserves_existing_id(self):
        rule = validate_rule({"name": "Test", "id": "my-custom-id"})
        assert rule["id"] == "my-custom-id"

    def test_missing_name_raises_value_error(self):
        with pytest.raises(ValueError, match="name"):
            validate_rule({"priority": 1})

    def test_empty_name_raises_value_error(self):
        with pytest.raises(ValueError, match="name"):
            validate_rule({"name": ""})

    def test_whitespace_name_raises_value_error(self):
        with pytest.raises(ValueError, match="name"):
            validate_rule({"name": "   "})

    def test_non_dict_raises_value_error(self):
        with pytest.raises(ValueError, match="dict"):
            validate_rule("not a dict")

    def test_defaults_priority_to_zero(self):
        rule = validate_rule({"name": "Test"})
        assert rule["priority"] == 0

    def test_defaults_enabled_to_true(self):
        rule = validate_rule({"name": "Test"})
        assert rule["enabled"] is True

    def test_invalid_priority_type_raises(self):
        with pytest.raises(ValueError, match="priority"):
            validate_rule({"name": "Test", "priority": "not-a-number"})

    def test_string_priority_coerced_to_int(self):
        rule = validate_rule({"name": "Test", "priority": "5"})
        assert rule["priority"] == 5

    def test_name_stripped(self):
        rule = validate_rule({"name": "  spaced out  "})
        assert rule["name"] == "spaced out"


# ═══════════════════════════════════════════════════════════════════════
# Rule CRUD tests
# ═══════════════════════════════════════════════════════════════════════


class TestRuleCRUD:
    """Test rule CRUD operations with AsyncMock StateClient."""

    def _make_state_client(self, initial_rules=None):
        """Create a mock StateClient with get/set methods."""
        import json as _json
        stored = {"value": _json.dumps(initial_rules) if initial_rules is not None else None}

        async def mock_get(key):
            return stored["value"]

        async def mock_set(key, value):
            stored["value"] = value

        client = AsyncMock()
        client.get = AsyncMock(side_effect=mock_get)
        client.set = AsyncMock(side_effect=mock_set)
        client._stored = stored  # for test inspection
        return client

    @pytest.mark.asyncio
    async def test_load_rules_empty(self):
        client = self._make_state_client()
        rules = await load_rules(client)
        assert rules == []

    @pytest.mark.asyncio
    async def test_load_rules_with_data(self):
        client = self._make_state_client([
            {"id": "r1", "name": "Rule 1", "priority": 1, "enabled": True,
             "conditions": {}, "action": {}}
        ])
        rules = await load_rules(client)
        assert len(rules) == 1
        assert rules[0]["id"] == "r1"

    @pytest.mark.asyncio
    async def test_load_rules_invalid_json(self):
        client = AsyncMock()
        client.get = AsyncMock(return_value="not valid json{{{")
        rules = await load_rules(client)
        assert rules == []

    @pytest.mark.asyncio
    async def test_load_rules_non_list_json(self):
        client = AsyncMock()
        client.get = AsyncMock(return_value='{"not": "a list"}')
        rules = await load_rules(client)
        assert rules == []

    @pytest.mark.asyncio
    async def test_add_rule(self):
        client = self._make_state_client()
        rule = await add_rule(client, {"name": "Morning music", "priority": 3})
        assert rule["name"] == "Morning music"
        assert rule["priority"] == 3
        # Verify persisted
        import json as _json
        saved = _json.loads(client._stored["value"])
        assert len(saved) == 1
        assert saved[0]["name"] == "Morning music"

    @pytest.mark.asyncio
    async def test_add_rule_appends_to_existing(self):
        client = self._make_state_client([
            {"id": "existing", "name": "Old rule", "priority": 1, "enabled": True,
             "conditions": {}, "action": {}}
        ])
        await add_rule(client, {"name": "New rule"})
        import json as _json
        saved = _json.loads(client._stored["value"])
        assert len(saved) == 2

    @pytest.mark.asyncio
    async def test_update_rule_success(self):
        client = self._make_state_client([
            {"id": "r1", "name": "Old name", "priority": 1, "enabled": True,
             "conditions": {}, "action": {}}
        ])
        result = await update_rule(client, "r1", {"name": "New name", "priority": 5})
        assert result is not None
        assert result["name"] == "New name"
        assert result["priority"] == 5

    @pytest.mark.asyncio
    async def test_update_rule_not_found(self):
        client = self._make_state_client([])
        result = await update_rule(client, "nonexistent", {"name": "X"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_rule_success(self):
        client = self._make_state_client([
            {"id": "r1", "name": "Rule 1", "priority": 1, "enabled": True,
             "conditions": {}, "action": {}},
            {"id": "r2", "name": "Rule 2", "priority": 2, "enabled": True,
             "conditions": {}, "action": {}}
        ])
        result = await delete_rule(client, "r1")
        assert result is True
        import json as _json
        saved = _json.loads(client._stored["value"])
        assert len(saved) == 1
        assert saved[0]["id"] == "r2"

    @pytest.mark.asyncio
    async def test_delete_rule_not_found(self):
        client = self._make_state_client([])
        result = await delete_rule(client, "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_toggle_rule_enables(self):
        client = self._make_state_client([
            {"id": "r1", "name": "Disabled rule", "priority": 1, "enabled": False,
             "conditions": {}, "action": {}}
        ])
        result = await toggle_rule(client, "r1")
        assert result is not None
        assert result["enabled"] is True

    @pytest.mark.asyncio
    async def test_toggle_rule_disables(self):
        client = self._make_state_client([
            {"id": "r1", "name": "Enabled rule", "priority": 1, "enabled": True,
             "conditions": {}, "action": {}}
        ])
        result = await toggle_rule(client, "r1")
        assert result is not None
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_toggle_rule_not_found(self):
        client = self._make_state_client([])
        result = await toggle_rule(client, "nonexistent")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# Rule evaluation tests
# ═══════════════════════════════════════════════════════════════════════


class TestRuleEvaluation:
    """Test rule evaluation and condition matching."""

    def _make_rule(self, **overrides):
        """Create a standard enabled rule with optional overrides."""
        base = {
            "id": str(uuid.uuid4()) if "id" not in overrides else overrides.pop("id"),
            "name": "Test Rule",
            "priority": 0,
            "enabled": True,
            "conditions": {},
            "action": {"type": "source_type", "value": "podcast"},
        }
        base.update(overrides)
        return base

    def test_wildcard_conditions_match_any_context(self):
        """Rule with all-null conditions matches any context."""
        rules = [self._make_rule(conditions={})]
        context = {"location_zone": "office", "activity": "working"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 1

    def test_exact_location_match(self):
        rules = [self._make_rule(conditions={"location_zone": "commute"})]
        context = {"location_zone": "commute", "activity": "transit"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 1

    def test_location_no_match(self):
        rules = [self._make_rule(conditions={"location_zone": "office"})]
        context = {"location_zone": "home"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 0

    def test_multiple_conditions_and_match(self):
        """All non-null conditions must match (AND logic)."""
        rules = [self._make_rule(conditions={
            "location_zone": "home",
            "activity": "relaxing",
        })]
        context = {"location_zone": "home", "activity": "relaxing"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 1

    def test_partial_condition_mismatch(self):
        """If one condition doesn't match, rule doesn't fire."""
        rules = [self._make_rule(conditions={
            "location_zone": "home",
            "activity": "exercising",
        })]
        context = {"location_zone": "home", "activity": "relaxing"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 0

    def test_null_condition_is_wildcard(self):
        """Explicitly null condition values act as wildcards."""
        rules = [self._make_rule(conditions={
            "location_zone": None,
            "activity": "working",
        })]
        context = {"location_zone": "office", "activity": "working"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 1

    def test_disabled_rules_filtered_out(self):
        rules = [
            self._make_rule(id="r1", enabled=False, conditions={}),
            self._make_rule(id="r2", enabled=True, conditions={}),
        ]
        matched = evaluate_rules(rules, {})
        assert len(matched) == 1
        assert matched[0]["id"] == "r2"

    def test_priority_ordering_descending(self):
        rules = [
            self._make_rule(id="low", priority=1, conditions={}),
            self._make_rule(id="high", priority=10, conditions={}),
            self._make_rule(id="mid", priority=5, conditions={}),
        ]
        matched = evaluate_rules(rules, {})
        assert [r["id"] for r in matched] == ["high", "mid", "low"]

    def test_priority_ties_preserve_array_order(self):
        """Same priority → stable sort preserves insertion order."""
        rules = [
            self._make_rule(id="first", priority=5, conditions={}),
            self._make_rule(id="second", priority=5, conditions={}),
            self._make_rule(id="third", priority=5, conditions={}),
        ]
        matched = evaluate_rules(rules, {})
        assert [r["id"] for r in matched] == ["first", "second", "third"]

    def test_empty_rules_returns_empty(self):
        matched = evaluate_rules([], {"location_zone": "home"})
        assert matched == []

    def test_no_matching_rules(self):
        rules = [self._make_rule(conditions={"location_zone": "mars"})]
        matched = evaluate_rules(rules, {"location_zone": "earth"})
        assert matched == []

    def test_time_range_within_range(self):
        rules = [self._make_rule(conditions={
            "time_range": {"start": "08:00", "end": "17:00"}
        })]
        context = {"current_time": "12:00"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 1

    def test_time_range_outside_range(self):
        rules = [self._make_rule(conditions={
            "time_range": {"start": "08:00", "end": "17:00"}
        })]
        context = {"current_time": "20:00"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 0

    def test_time_range_at_boundary_start(self):
        rules = [self._make_rule(conditions={
            "time_range": {"start": "08:00", "end": "17:00"}
        })]
        context = {"current_time": "08:00"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 1

    def test_time_range_at_boundary_end(self):
        rules = [self._make_rule(conditions={
            "time_range": {"start": "08:00", "end": "17:00"}
        })]
        context = {"current_time": "17:00"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 1

    def test_time_range_wrapping_midnight(self):
        """Time range crossing midnight: 22:00 → 06:00."""
        rules = [self._make_rule(conditions={
            "time_range": {"start": "22:00", "end": "06:00"}
        })]
        # 23:00 is within the late-night range
        assert len(evaluate_rules(rules, {"current_time": "23:00"})) == 1
        # 03:00 is within the early-morning range
        assert len(evaluate_rules(rules, {"current_time": "03:00"})) == 1
        # 12:00 is outside the range
        assert len(evaluate_rules(rules, {"current_time": "12:00"})) == 0

    def test_time_range_missing_current_time_in_context(self):
        """If current_time not in context but time_range specified, rule still matches
        (empty string comparison — no time_range check fires for empty start/end)."""
        rules = [self._make_rule(conditions={
            "time_range": {"start": "08:00", "end": "17:00"}
        })]
        # No current_time in context → start and end are both truthy but
        # current_time is "" which is < "08:00", so this should NOT match
        context = {}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 0

    def test_time_period_condition(self):
        rules = [self._make_rule(conditions={"time_period": "morning"})]
        context = {"time_period": "morning"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 1

    def test_multiple_rules_mixed_matching(self):
        """Multiple rules, some match and some don't."""
        rules = [
            self._make_rule(id="r1", priority=10, conditions={"location_zone": "home"}),
            self._make_rule(id="r2", priority=5, conditions={"location_zone": "office"}),
            self._make_rule(id="r3", priority=1, conditions={}),  # wildcard
        ]
        context = {"location_zone": "home"}
        matched = evaluate_rules(rules, context)
        assert len(matched) == 2
        assert matched[0]["id"] == "r1"
        assert matched[1]["id"] == "r3"

    def test_matches_condition_with_all_fields(self):
        """Direct test of _matches_condition with all condition types."""
        conditions = {
            "location_zone": "commute",
            "activity": "transit",
            "time_period": "morning",
            "time_range": {"start": "07:00", "end": "09:00"},
        }
        context = {
            "location_zone": "commute",
            "activity": "transit",
            "time_period": "morning",
            "current_time": "08:00",
        }
        assert _matches_condition(conditions, context) is True

    def test_matches_condition_fails_on_activity_mismatch(self):
        conditions = {"activity": "exercising"}
        context = {"activity": "sleeping"}
        assert _matches_condition(conditions, context) is False

    def test_default_durations_present(self):
        """Verify DEFAULT_DURATIONS has expected media types."""
        assert DEFAULT_DURATIONS["podcast"] == 1800
        assert DEFAULT_DURATIONS["video"] == 900
        assert DEFAULT_DURATIONS["track"] == 240

    def test_rules_state_key_is_string(self):
        assert isinstance(RULES_STATE_KEY, str)
        assert RULES_STATE_KEY == "schedule_rules"


# ── Import plan_service via file path ──

_plan_svc_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "media-scheduler" / "services" / "plan_service.py"
)
_plan_svc_spec = importlib.util.spec_from_file_location("plan_service_test", str(_plan_svc_path))
_plan_svc_mod = importlib.util.module_from_spec(_plan_svc_spec)
_plan_svc_spec.loader.exec_module(_plan_svc_mod)

mint_plan_iri = _plan_svc_mod.mint_plan_iri
mint_entry_iri = _plan_svc_mod.mint_entry_iri
build_item_query = _plan_svc_mod.build_item_query
allocate_slots = _plan_svc_mod.allocate_slots
fetch_context = _plan_svc_mod.fetch_context
get_existing_plan_entries = _plan_svc_mod.get_existing_plan_entries
generate_plan = _plan_svc_mod.generate_plan
PLAN_START_HOUR = _plan_svc_mod.PLAN_START_HOUR
MAX_ITEMS_PER_RULE = _plan_svc_mod.MAX_ITEMS_PER_RULE
DAILY_MEDIA_PLAN_TYPE = _plan_svc_mod.DAILY_MEDIA_PLAN_TYPE
PLAN_ENTRY_TYPE = _plan_svc_mod.PLAN_ENTRY_TYPE
PLAN_DEFAULT_DURATIONS = _plan_svc_mod.DEFAULT_DURATIONS


# ═══════════════════════════════════════════════════════════════════════
# Plan IRI minting tests
# ═══════════════════════════════════════════════════════════════════════


class TestPlanIriMinting:
    """Test deterministic IRI generation for plans and entries."""

    def test_mint_plan_iri_format(self):
        iri = mint_plan_iri("2026-03-23")
        assert iri == "urn:sempkm:app:media-scheduler:plan-2026-03-23"

    def test_mint_plan_iri_different_dates(self):
        iri1 = mint_plan_iri("2026-01-01")
        iri2 = mint_plan_iri("2026-12-31")
        assert iri1 != iri2

    def test_mint_plan_iri_deterministic(self):
        iri1 = mint_plan_iri("2026-06-15")
        iri2 = mint_plan_iri("2026-06-15")
        assert iri1 == iri2

    def test_mint_entry_iri_format(self):
        iri = mint_entry_iri("2026-03-23", 0)
        assert iri == "urn:sempkm:app:media-scheduler:entry-2026-03-23-000"

    def test_mint_entry_iri_order_padding(self):
        iri = mint_entry_iri("2026-03-23", 5)
        assert iri.endswith("-005")

    def test_mint_entry_iri_different_orders(self):
        iri1 = mint_entry_iri("2026-03-23", 0)
        iri2 = mint_entry_iri("2026-03-23", 1)
        assert iri1 != iri2

    def test_mint_entry_iri_different_dates(self):
        iri1 = mint_entry_iri("2026-03-01", 0)
        iri2 = mint_entry_iri("2026-03-02", 0)
        assert iri1 != iri2

    def test_mint_entry_iri_large_order(self):
        iri = mint_entry_iri("2026-03-23", 100)
        assert iri.endswith("-100")


# ═══════════════════════════════════════════════════════════════════════
# Build item query tests
# ═══════════════════════════════════════════════════════════════════════


class TestBuildItemQuery:
    """Test SPARQL query construction for different action types."""

    def test_source_type_action(self):
        action = {"type": "source_type", "value": "podcast"}
        sparql = build_item_query(action)
        assert 'FILTER(?sourceType = "podcast")' in sparql
        assert '"queued"' in sparql
        assert "LIMIT 5" in sparql

    def test_source_iri_action(self):
        action = {"type": "source_iri", "value": "urn:sempkm:app:media-scheduler:source-abc"}
        sparql = build_item_query(action)
        assert "FILTER(?source = <urn:sempkm:app:media-scheduler:source-abc>)" in sparql
        assert '"queued"' in sparql

    def test_category_action(self):
        action = {"type": "category", "value": "urn:sempkm:app:media-scheduler:cat-news"}
        sparql = build_item_query(action)
        assert "category" in sparql.lower()
        assert "FILTER(?category = <urn:sempkm:app:media-scheduler:cat-news>)" in sparql
        assert '"queued"' in sparql

    def test_custom_limit(self):
        action = {"type": "source_type", "value": "podcast"}
        sparql = build_item_query(action, limit=10)
        assert "LIMIT 10" in sparql

    def test_empty_action_raises(self):
        with pytest.raises(ValueError):
            build_item_query({})

    def test_unknown_action_type_raises(self):
        with pytest.raises(ValueError, match="Unknown action type"):
            build_item_query({"type": "invalid_type", "value": "something"})

    def test_missing_value_raises(self):
        with pytest.raises(ValueError):
            build_item_query({"type": "source_type", "value": ""})

    def test_query_has_media_item_type(self):
        action = {"type": "source_type", "value": "podcast"}
        sparql = build_item_query(action)
        assert "MediaItem" in sparql

    def test_query_orders_by_title(self):
        action = {"type": "source_type", "value": "podcast"}
        sparql = build_item_query(action)
        assert "ORDER BY" in sparql


# ═══════════════════════════════════════════════════════════════════════
# Slot allocation tests
# ═══════════════════════════════════════════════════════════════════════


class TestAllocateSlots:
    """Test time-slot allocation logic."""

    def test_empty_items(self):
        slots = allocate_slots([])
        assert slots == []

    def test_single_item_with_duration(self):
        items = [{
            "item_iri": "urn:item-1",
            "title": "Episode 1",
            "source_type": "podcast",
            "duration": 600,
            "rule_id": "r1",
        }]
        slots = allocate_slots(items)
        assert len(slots) == 1
        assert slots[0]["slot_start"] == "08:00"
        assert slots[0]["slot_end"] == "08:10"  # 600s = 10min
        assert slots[0]["slot_order"] == 0
        assert slots[0]["duration"] == 600

    def test_multiple_items_sequential(self):
        items = [
            {"item_iri": "urn:item-1", "title": "Ep1", "source_type": "podcast", "duration": 1800, "rule_id": "r1"},
            {"item_iri": "urn:item-2", "title": "Ep2", "source_type": "podcast", "duration": 1800, "rule_id": "r1"},
        ]
        slots = allocate_slots(items)
        assert len(slots) == 2
        assert slots[0]["slot_start"] == "08:00"
        assert slots[0]["slot_end"] == "08:30"
        assert slots[1]["slot_start"] == "08:30"
        assert slots[1]["slot_end"] == "09:00"

    def test_default_duration_podcast(self):
        items = [{"item_iri": "urn:item-1", "title": "Ep1", "source_type": "podcast", "rule_id": "r1"}]
        slots = allocate_slots(items)
        assert slots[0]["duration"] == 1800

    def test_default_duration_youtube(self):
        items = [{"item_iri": "urn:item-1", "title": "Vid1", "source_type": "youtube", "rule_id": "r1"}]
        slots = allocate_slots(items)
        assert slots[0]["duration"] == 900

    def test_default_duration_spotify(self):
        items = [{"item_iri": "urn:item-1", "title": "Track1", "source_type": "spotify", "rule_id": "r1"}]
        slots = allocate_slots(items)
        assert slots[0]["duration"] == 240

    def test_default_duration_unknown_type(self):
        """Unknown source types fall back to 1800s."""
        items = [{"item_iri": "urn:item-1", "title": "X", "source_type": "unknown", "rule_id": "r1"}]
        slots = allocate_slots(items)
        assert slots[0]["duration"] == 1800

    def test_zero_duration_uses_default(self):
        items = [{"item_iri": "urn:item-1", "title": "Ep1", "source_type": "podcast", "duration": 0, "rule_id": "r1"}]
        slots = allocate_slots(items)
        assert slots[0]["duration"] == 1800

    def test_negative_duration_uses_default(self):
        items = [{"item_iri": "urn:item-1", "title": "Ep1", "source_type": "youtube", "duration": -100, "rule_id": "r1"}]
        slots = allocate_slots(items)
        assert slots[0]["duration"] == 900

    def test_custom_start_hour(self):
        items = [{"item_iri": "urn:item-1", "title": "Ep1", "source_type": "podcast", "duration": 600, "rule_id": "r1"}]
        slots = allocate_slots(items, start_hour=14)
        assert slots[0]["slot_start"] == "14:00"
        assert slots[0]["slot_end"] == "14:10"

    def test_mixed_source_types(self):
        items = [
            {"item_iri": "urn:item-1", "title": "Pod1", "source_type": "podcast", "rule_id": "r1"},
            {"item_iri": "urn:item-2", "title": "Vid1", "source_type": "youtube", "rule_id": "r2"},
            {"item_iri": "urn:item-3", "title": "Track1", "source_type": "spotify", "rule_id": "r3"},
        ]
        slots = allocate_slots(items)
        assert len(slots) == 3
        # Podcast: 1800s = 30min → 08:00-08:30
        assert slots[0]["slot_start"] == "08:00"
        assert slots[0]["slot_end"] == "08:30"
        # YouTube: 900s = 15min → 08:30-08:45
        assert slots[1]["slot_start"] == "08:30"
        assert slots[1]["slot_end"] == "08:45"
        # Spotify: 240s = 4min → 08:45-08:49
        assert slots[2]["slot_start"] == "08:45"
        assert slots[2]["slot_end"] == "08:49"

    def test_slot_order_is_sequential(self):
        items = [
            {"item_iri": f"urn:item-{i}", "title": f"Item {i}", "source_type": "podcast", "duration": 600, "rule_id": "r1"}
            for i in range(5)
        ]
        slots = allocate_slots(items)
        for i, slot in enumerate(slots):
            assert slot["slot_order"] == i

    def test_preserves_item_fields(self):
        items = [{"item_iri": "urn:item-1", "title": "My Title", "source_type": "podcast", "duration": 600, "rule_id": "rule-abc"}]
        slots = allocate_slots(items)
        assert slots[0]["item_iri"] == "urn:item-1"
        assert slots[0]["title"] == "My Title"
        assert slots[0]["source_type"] == "podcast"
        assert slots[0]["rule_id"] == "rule-abc"

    def test_none_duration_uses_default(self):
        items = [{"item_iri": "urn:item-1", "title": "Ep1", "source_type": "spotify", "duration": None, "rule_id": "r1"}]
        slots = allocate_slots(items)
        assert slots[0]["duration"] == 240


# ═══════════════════════════════════════════════════════════════════════
# Context fetching tests
# ═══════════════════════════════════════════════════════════════════════


class TestFetchContext:
    """Test context fetch from platform API."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"location_zone": "home", "activity": "working"}
        http = AsyncMock()
        http.get = AsyncMock(return_value=mock_response)
        result = await fetch_context(http)
        assert result == {"location_zone": "home", "activity": "working"}

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        http = AsyncMock()
        http.get = AsyncMock(return_value=mock_response)
        result = await fetch_context(http)
        assert result == {}

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self):
        http = AsyncMock()
        http.get = AsyncMock(side_effect=ConnectionError("timeout"))
        result = await fetch_context(http)
        assert result == {}

    @pytest.mark.asyncio
    async def test_non_dict_response_returns_empty(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["not", "a", "dict"]
        http = AsyncMock()
        http.get = AsyncMock(return_value=mock_response)
        result = await fetch_context(http)
        assert result == {}


# ═══════════════════════════════════════════════════════════════════════
# Existing plan entries query tests
# ═══════════════════════════════════════════════════════════════════════


class TestGetExistingPlanEntries:
    """Test SPARQL query for existing plan entries."""

    @pytest.mark.asyncio
    async def test_returns_entry_iris(self):
        graph = AsyncMock()
        graph.query = AsyncMock(return_value={
            "results": {"bindings": [
                {"entry": {"value": "urn:entry-1"}},
                {"entry": {"value": "urn:entry-2"}},
            ]}
        })
        entries = await get_existing_plan_entries(graph, "urn:plan-2026-03-23")
        assert entries == ["urn:entry-1", "urn:entry-2"]

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_results(self):
        graph = AsyncMock()
        graph.query = AsyncMock(return_value={"results": {"bindings": []}})
        entries = await get_existing_plan_entries(graph, "urn:plan-2026-03-23")
        assert entries == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        graph = AsyncMock()
        graph.query = AsyncMock(side_effect=Exception("SPARQL error"))
        entries = await get_existing_plan_entries(graph, "urn:plan-2026-03-23")
        assert entries == []


# ═══════════════════════════════════════════════════════════════════════
# Plan generation tests
# ═══════════════════════════════════════════════════════════════════════


class TestGeneratePlan:
    """Test the full plan generation orchestration."""

    def _make_ctx(self, context_response=None, rules=None, query_results=None, existing_entries=None):
        """Build a mock AppContext for plan generation tests."""
        ctx = MagicMock()

        # HTTP client for context fetch
        mock_response = MagicMock()
        mock_response.status_code = 200
        if context_response is not None:
            mock_response.json.return_value = context_response
        else:
            mock_response.json.return_value = {"location_zone": "home", "activity": "working"}
        ctx.http = AsyncMock()
        ctx.http.get = AsyncMock(return_value=mock_response)

        # State client for rules
        rules_data = rules if rules is not None else []
        ctx.state = AsyncMock()
        ctx.state.get = AsyncMock(return_value=json.dumps(rules_data))

        # Graph client for item queries + existing entries
        query_results = query_results or {"results": {"bindings": []}}
        existing_entries = existing_entries or {"results": {"bindings": []}}

        async def _mock_query(sparql):
            if "PlanEntry" in sparql:
                return existing_entries
            return query_results

        ctx.graph = AsyncMock()
        ctx.graph.query = AsyncMock(side_effect=_mock_query)

        # Commands client
        ctx.commands = AsyncMock()
        ctx.commands.execute = AsyncMock()

        return ctx

    @pytest.mark.asyncio
    async def test_empty_context_returns_empty_plan(self):
        ctx = self._make_ctx()
        ctx.http.get = AsyncMock(side_effect=ConnectionError("no context"))
        result = await generate_plan(ctx, date_str="2026-03-23")
        assert result["entries_created"] == 0
        assert result["rules_matched"] == 0

    @pytest.mark.asyncio
    async def test_no_rules_returns_empty_plan(self):
        ctx = self._make_ctx(rules=[])
        result = await generate_plan(ctx, date_str="2026-03-23",
                                     context_override={"location_zone": "home"})
        assert result["entries_created"] == 0
        assert result["rules_matched"] == 0

    @pytest.mark.asyncio
    async def test_no_matching_rules_returns_empty_plan(self):
        rules = [{
            "id": "r1", "name": "Office rule", "priority": 1, "enabled": True,
            "conditions": {"location_zone": "office"},
            "action": {"type": "source_type", "value": "podcast"},
        }]
        ctx = self._make_ctx(rules=rules)
        result = await generate_plan(ctx, date_str="2026-03-23",
                                     context_override={"location_zone": "home"})
        assert result["entries_created"] == 0
        assert result["rules_matched"] == 0

    @pytest.mark.asyncio
    async def test_matched_rule_no_items_returns_zero_entries(self):
        rules = [{
            "id": "r1", "name": "Home podcasts", "priority": 1, "enabled": True,
            "conditions": {"location_zone": "home"},
            "action": {"type": "source_type", "value": "podcast"},
        }]
        ctx = self._make_ctx(rules=rules)
        result = await generate_plan(ctx, date_str="2026-03-23",
                                     context_override={"location_zone": "home"})
        assert result["rules_matched"] == 1
        assert result["entries_created"] == 0

    @pytest.mark.asyncio
    async def test_successful_plan_generation(self):
        rules = [{
            "id": "r1", "name": "Home podcasts", "priority": 1, "enabled": True,
            "conditions": {"location_zone": "home"},
            "action": {"type": "source_type", "value": "podcast"},
        }]
        items = {"results": {"bindings": [
            {"item": {"value": "urn:item-1"}, "title": {"value": "Episode 1"},
             "sourceType": {"value": "podcast"}, "duration": {"value": "1800"}},
            {"item": {"value": "urn:item-2"}, "title": {"value": "Episode 2"},
             "sourceType": {"value": "podcast"}, "duration": {"value": "900"}},
        ]}}
        ctx = self._make_ctx(rules=rules, query_results=items)
        result = await generate_plan(ctx, date_str="2026-03-23",
                                     context_override={"location_zone": "home"})
        assert result["plan_iri"] == "urn:sempkm:app:media-scheduler:plan-2026-03-23"
        assert result["date"] == "2026-03-23"
        assert result["rules_matched"] == 1
        assert result["entries_created"] == 2

    @pytest.mark.asyncio
    async def test_plan_creates_correct_objects(self):
        """Verify the plan + entries are created via CommandClient."""
        rules = [{
            "id": "r1", "name": "Test", "priority": 1, "enabled": True,
            "conditions": {},
            "action": {"type": "source_type", "value": "podcast"},
        }]
        items = {"results": {"bindings": [
            {"item": {"value": "urn:item-1"}, "title": {"value": "Ep1"},
             "sourceType": {"value": "podcast"}, "duration": {"value": "600"}},
        ]}}
        ctx = self._make_ctx(rules=rules, query_results=items)
        await generate_plan(ctx, date_str="2026-03-23",
                            context_override={"location_zone": "home"})

        calls = ctx.commands.execute.call_args_list
        # First call: plan creation
        assert calls[0].args[0] == "object.create"
        plan_params = calls[0].args[1]
        assert plan_params["iri"] == "urn:sempkm:app:media-scheduler:plan-2026-03-23"
        assert "DailyMediaPlan" in plan_params["type"]

        # Second call: entry creation
        assert calls[1].args[0] == "object.create"
        entry_params = calls[1].args[1]
        assert entry_params["iri"] == "urn:sempkm:app:media-scheduler:entry-2026-03-23-000"
        assert "PlanEntry" in entry_params["type"]

    @pytest.mark.asyncio
    async def test_dedup_items_across_rules(self):
        """Items appearing in multiple rules are only included once."""
        rules = [
            {"id": "r1", "name": "Rule 1", "priority": 2, "enabled": True,
             "conditions": {}, "action": {"type": "source_type", "value": "podcast"}},
            {"id": "r2", "name": "Rule 2", "priority": 1, "enabled": True,
             "conditions": {}, "action": {"type": "source_type", "value": "podcast"}},
        ]
        # Both rules return the same item
        items = {"results": {"bindings": [
            {"item": {"value": "urn:item-1"}, "title": {"value": "Ep1"},
             "sourceType": {"value": "podcast"}, "duration": {"value": "1800"}},
        ]}}
        ctx = self._make_ctx(rules=rules, query_results=items)
        result = await generate_plan(ctx, date_str="2026-03-23",
                                     context_override={"activity": "any"})
        assert result["entries_created"] == 1  # deduped

    @pytest.mark.asyncio
    async def test_existing_entries_patched_to_replaced(self):
        """Old plan entries are patched to 'replaced' status."""
        rules = [{
            "id": "r1", "name": "Test", "priority": 1, "enabled": True,
            "conditions": {},
            "action": {"type": "source_type", "value": "podcast"},
        }]
        items = {"results": {"bindings": [
            {"item": {"value": "urn:item-1"}, "title": {"value": "Ep1"},
             "sourceType": {"value": "podcast"}, "duration": {"value": "600"}},
        ]}}
        existing = {"results": {"bindings": [
            {"entry": {"value": "urn:old-entry-1"}},
            {"entry": {"value": "urn:old-entry-2"}},
        ]}}
        ctx = self._make_ctx(rules=rules, query_results=items, existing_entries=existing)
        await generate_plan(ctx, date_str="2026-03-23",
                            context_override={"location_zone": "home"})

        # First two calls should be patches to "replaced"
        calls = ctx.commands.execute.call_args_list
        assert calls[0].args[0] == "object.patch"
        assert "replaced" in str(calls[0].args[1])
        assert calls[1].args[0] == "object.patch"
        assert "replaced" in str(calls[1].args[1])
        # Then plan + entry creation
        assert calls[2].args[0] == "object.create"

    @pytest.mark.asyncio
    async def test_context_override_skips_fetch(self):
        """When context_override is provided, fetch_context is not called."""
        rules = [{
            "id": "r1", "name": "Test", "priority": 1, "enabled": True,
            "conditions": {"location_zone": "commute"},
            "action": {"type": "source_type", "value": "podcast"},
        }]
        ctx = self._make_ctx(rules=rules)
        result = await generate_plan(ctx, date_str="2026-03-23",
                                     context_override={"location_zone": "commute"})
        # http.get should not have been called (context_override used)
        ctx.http.get.assert_not_called()
        assert result["rules_matched"] == 1

    @pytest.mark.asyncio
    async def test_rule_with_invalid_action_skipped(self):
        """Rules with empty actions are skipped gracefully."""
        rules = [
            {"id": "r1", "name": "Bad rule", "priority": 2, "enabled": True,
             "conditions": {}, "action": {}},
            {"id": "r2", "name": "Good rule", "priority": 1, "enabled": True,
             "conditions": {}, "action": {"type": "source_type", "value": "podcast"}},
        ]
        items = {"results": {"bindings": [
            {"item": {"value": "urn:item-1"}, "title": {"value": "Ep1"},
             "sourceType": {"value": "podcast"}, "duration": {"value": "600"}},
        ]}}
        ctx = self._make_ctx(rules=rules, query_results=items)
        result = await generate_plan(ctx, date_str="2026-03-23",
                                     context_override={"activity": "any"})
        # Both match but one has invalid action — still creates entries from good rule
        assert result["entries_created"] == 1

    @pytest.mark.asyncio
    async def test_plan_iri_in_result(self):
        ctx = self._make_ctx()
        result = await generate_plan(ctx, date_str="2026-03-23",
                                     context_override={"location_zone": "home"})
        assert result["plan_iri"] == "urn:sempkm:app:media-scheduler:plan-2026-03-23"

    @pytest.mark.asyncio
    async def test_date_defaults_to_today(self):
        ctx = self._make_ctx()
        result = await generate_plan(ctx, context_override={"location_zone": "home"})
        from datetime import date
        assert result["date"] == date.today().isoformat()

    @pytest.mark.asyncio
    async def test_plan_constants(self):
        """Verify plan constants are set correctly."""
        assert PLAN_DEFAULT_DURATIONS["podcast"] == 1800
        assert PLAN_DEFAULT_DURATIONS["youtube"] == 900
        assert PLAN_DEFAULT_DURATIONS["spotify"] == 240
        assert PLAN_START_HOUR == 8
        assert MAX_ITEMS_PER_RULE == 5


# ═══════════════════════════════════════════════════════════════════════
# Generate-plan task handler tests
# ═══════════════════════════════════════════════════════════════════════


class TestGeneratePlanTask:
    """Test the generate-plan task handler in app.py."""

    @pytest.mark.asyncio
    async def test_task_handler_delegates_to_generate_plan(self):
        """The task handler should call generate_plan and return its result."""
        ctx = MagicMock()
        ctx.http = AsyncMock()
        ctx.http.get = AsyncMock(side_effect=ConnectionError("skip"))
        ctx.state = AsyncMock()
        ctx.state.get = AsyncMock(return_value="[]")
        ctx.graph = AsyncMock()
        ctx.commands = AsyncMock()

        result = await generate_plan_task(ctx)
        assert "plan_iri" in result
        assert "entries_created" in result

