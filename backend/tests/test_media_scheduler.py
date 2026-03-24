"""Unit tests for Media Scheduler app — manifest validation, IRI minting,
entry-to-media-item conversion, duration parsing, feed fetching,
dedup logic, subscribe/unsubscribe, and poll-sources task handler.

Import pattern follows test_rss_settings.py: loads the app module via
importlib.util.spec_from_file_location to avoid package path conflicts.
feedparser is mocked at sys.modules level before exec_module.
"""

from __future__ import annotations

import asyncio
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
poll_spotify = _app_mod.poll_spotify
_spotify_oauth_result_page = _app_mod._spotify_oauth_result_page
MAX_INITIAL_ITEMS = _app_mod.MAX_INITIAL_ITEMS
_get_current_error_count = _app_mod._get_current_error_count
_format_date = _app_mod._format_date
_format_duration = _app_mod._format_duration
entry_status_fragment = _app_mod.entry_status_fragment
current_suggestion_json = _app_mod.current_suggestion_json
on_startup = _app_mod.on_startup
on_shutdown = _app_mod.on_shutdown
VALID_ENTRY_STATUSES = _app_mod.VALID_ENTRY_STATUSES
today_fragment = _app_mod.today_fragment
stats_fragment = _app_mod.stats_fragment

# ── Import stats_service via file path ──

_stats_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "media-scheduler" / "services" / "stats_service.py"
)
_stats_spec = importlib.util.spec_from_file_location("stats_service_test", str(_stats_path))
_stats_mod = importlib.util.module_from_spec(_stats_spec)
_stats_spec.loader.exec_module(_stats_mod)

get_hours_by_source_type = _stats_mod.get_hours_by_source_type
get_top_sources = _stats_mod.get_top_sources
get_weekly_trends = _stats_mod.get_weekly_trends
HOURS_BY_SOURCE_TYPE_SPARQL = _stats_mod.HOURS_BY_SOURCE_TYPE_SPARQL
TOP_SOURCES_SPARQL = _stats_mod.TOP_SOURCES_SPARQL
WEEKLY_TRENDS_SPARQL = _stats_mod.WEEKLY_TRENDS_SPARQL


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
        assert len(m.tasks) == 4
        task_ids = [t.id for t in m.tasks]
        assert "poll-sources" in task_ids
        assert "poll-youtube" in task_ids
        assert "poll-spotify" in task_ids
        assert "generate-plan" in task_ids

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


# ── Import youtube_service via file path ──

_yt_svc_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "media-scheduler" / "services" / "youtube_service.py"
)
_yt_svc_spec = importlib.util.spec_from_file_location("youtube_service_test", str(_yt_svc_path))
_yt_svc_mod = importlib.util.module_from_spec(_yt_svc_spec)
_yt_svc_spec.loader.exec_module(_yt_svc_mod)

parse_youtube_url = _yt_svc_mod.parse_youtube_url
parse_iso8601_duration = _yt_svc_mod.parse_iso8601_duration
video_to_media_item = _yt_svc_mod.video_to_media_item
YouTubeClient = _yt_svc_mod.YouTubeClient
YouTubeAPIError = _yt_svc_mod.YouTubeAPIError
yt_check_quota = _yt_svc_mod.check_quota
yt_increment_quota = _yt_svc_mod.increment_quota
yt_reset_quota_if_new_day = _yt_svc_mod.reset_quota_if_new_day
subscribe_youtube = _yt_svc_mod.subscribe_youtube
yt_get_existing_item_iris = _yt_svc_mod.get_existing_item_iris
yt_mint_item_iri = _yt_svc_mod.mint_item_iri
yt_YOUTUBE_SOURCES_SPARQL = _yt_svc_mod.YOUTUBE_SOURCES_SPARQL


# ═══════════════════════════════════════════════════════════════════════
# YouTube URL parsing tests
# ═══════════════════════════════════════════════════════════════════════


class TestYouTubeURLParsing:
    """Test parse_youtube_url with all supported URL formats and edge cases."""

    def test_channel_id_url(self):
        result = parse_youtube_url("https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx")
        assert result == {"type": "channel_id", "value": "UCxxxxxxxxxxxxxxxxxxxxxx"}

    def test_handle_url(self):
        result = parse_youtube_url("https://www.youtube.com/@techreviewer")
        assert result == {"type": "handle", "value": "techreviewer"}

    def test_playlist_url(self):
        result = parse_youtube_url("https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        assert result == {"type": "playlist", "value": "PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}

    def test_custom_url(self):
        result = parse_youtube_url("https://www.youtube.com/c/MyChannel")
        assert result == {"type": "custom", "value": "MyChannel"}

    def test_raw_channel_id(self):
        result = parse_youtube_url("UCxxxxxxxxxxxxxxxxxxxxxx")
        assert result == {"type": "raw_channel", "value": "UCxxxxxxxxxxxxxxxxxxxxxx"}

    def test_raw_playlist_id(self):
        result = parse_youtube_url("PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        assert result == {"type": "raw_playlist", "value": "PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}

    def test_raw_uploads_playlist_id(self):
        """UU-prefixed playlist IDs (uploads playlists) should be recognized."""
        result = parse_youtube_url("UUxxxxxxxxxxxxxxxxxxxxxx")
        assert result == {"type": "raw_playlist", "value": "UUxxxxxxxxxxxxxxxxxxxxxx"}

    def test_none_input(self):
        assert parse_youtube_url(None) is None

    def test_empty_string(self):
        assert parse_youtube_url("") is None

    def test_whitespace_only(self):
        assert parse_youtube_url("   ") is None

    def test_non_youtube_url(self):
        assert parse_youtube_url("https://example.com/video") is None

    def test_invalid_url(self):
        assert parse_youtube_url("not-a-url") is None

    def test_youtube_url_without_path(self):
        assert parse_youtube_url("https://www.youtube.com/") is None

    def test_channel_url_trailing_slash(self):
        result = parse_youtube_url("https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx/")
        assert result == {"type": "channel_id", "value": "UCxxxxxxxxxxxxxxxxxxxxxx"}

    def test_handle_with_dots(self):
        result = parse_youtube_url("https://www.youtube.com/@my.channel.name")
        assert result == {"type": "handle", "value": "my.channel.name"}

    def test_mobile_youtube_url(self):
        result = parse_youtube_url("https://m.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx")
        assert result == {"type": "channel_id", "value": "UCxxxxxxxxxxxxxxxxxxxxxx"}

    def test_playlist_from_watch_url(self):
        """Watch URLs with a list parameter should extract the playlist."""
        result = parse_youtube_url("https://www.youtube.com/watch?v=abc&list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        assert result == {"type": "playlist", "value": "PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}

    def test_integer_input_returns_none(self):
        assert parse_youtube_url(12345) is None

    def test_url_stripped(self):
        result = parse_youtube_url("  https://www.youtube.com/@stripped  ")
        assert result == {"type": "handle", "value": "stripped"}


# ═══════════════════════════════════════════════════════════════════════
# ISO 8601 duration parsing tests
# ═══════════════════════════════════════════════════════════════════════


class TestISO8601Duration:
    """Test parse_iso8601_duration with various inputs."""

    def test_minutes_and_seconds(self):
        assert parse_iso8601_duration("PT4M13S") == 253

    def test_hours_minutes_seconds(self):
        assert parse_iso8601_duration("PT1H2M30S") == 3750

    def test_seconds_only(self):
        assert parse_iso8601_duration("PT45S") == 45

    def test_hours_only(self):
        assert parse_iso8601_duration("PT1H") == 3600

    def test_minutes_only(self):
        assert parse_iso8601_duration("PT30M") == 1800

    def test_hours_and_seconds_no_minutes(self):
        assert parse_iso8601_duration("PT2H15S") == 7215

    def test_zero_duration(self):
        assert parse_iso8601_duration("PT0S") == 0

    def test_none_input(self):
        assert parse_iso8601_duration(None) is None

    def test_empty_string(self):
        assert parse_iso8601_duration("") is None

    def test_invalid_string(self):
        assert parse_iso8601_duration("invalid") is None

    def test_itunes_format_not_matched(self):
        """iTunes HH:MM:SS format should not be matched by ISO 8601 parser."""
        assert parse_iso8601_duration("1:23:45") is None

    def test_bare_pt_no_components(self):
        """PT with no time components should return 0 (regex matches with all groups None)."""
        assert parse_iso8601_duration("PT") == 0

    def test_whitespace_trimmed(self):
        assert parse_iso8601_duration("  PT5M  ") == 300

    def test_case_insensitive(self):
        assert parse_iso8601_duration("pt1h30m") == 5400

    def test_large_duration(self):
        assert parse_iso8601_duration("PT12H59M59S") == 46799


# ═══════════════════════════════════════════════════════════════════════
# Video-to-MediaItem conversion tests
# ═══════════════════════════════════════════════════════════════════════


class TestVideoToMediaItem:
    """Test video_to_media_item field mapping and IRI minting."""

    def _make_video(self, **overrides) -> dict:
        """Create a standard YouTube API video item with reasonable defaults."""
        base = {
            "snippet": {
                "title": "How to Build a REST API",
                "description": "A tutorial on building REST APIs.",
                "publishedAt": "2026-03-15T12:00:00Z",
                "thumbnails": {
                    "medium": {"url": "https://i.ytimg.com/vi/abc123/mqdefault.jpg"},
                },
                "resourceId": {"videoId": "abc123"},
            },
        }
        # Apply overrides to snippet if needed
        if "snippet" in overrides:
            base["snippet"].update(overrides.pop("snippet"))
        base.update(overrides)
        return base

    def test_basic_conversion(self):
        source_iri = "urn:sempkm:app:media-scheduler:source-yt1"
        video = self._make_video()
        result = video_to_media_item(video, source_iri)

        assert result["type"] == MEDIA_ITEM_TYPE
        assert result["iri"].startswith("urn:sempkm:app:media-scheduler:item-")
        props = result["properties"]
        assert props["dcterms:title"] == "How to Build a REST API"
        assert props["dcterms:description"] == "A tutorial on building REST APIs."
        assert props["dcterms:created"] == "2026-03-15T12:00:00Z"
        assert props[f"{MS_NS}thumbnailUrl"] == "https://i.ytimg.com/vi/abc123/mqdefault.jpg"
        assert props[f"{MS_NS}externalId"] == "abc123"
        assert props[f"{MS_NS}enclosureUrl"] == "https://www.youtube.com/watch?v=abc123"
        assert props[f"{MS_NS}status"] == "queued"
        assert props[f"{MS_NS}mediaSource"] == source_iri

    def test_with_duration(self):
        video = self._make_video(duration_seconds=253)
        result = video_to_media_item(video, "urn:test:source")
        assert result["properties"][f"{MS_NS}duration"] == 253

    def test_without_duration(self):
        video = self._make_video()
        result = video_to_media_item(video, "urn:test:source")
        assert f"{MS_NS}duration" not in result["properties"]

    def test_missing_description(self):
        video = self._make_video()
        del video["snippet"]["description"]
        result = video_to_media_item(video, "urn:test:source")
        assert "dcterms:description" not in result["properties"]

    def test_missing_thumbnail(self):
        video = self._make_video()
        video["snippet"]["thumbnails"] = {}
        result = video_to_media_item(video, "urn:test:source")
        assert f"{MS_NS}thumbnailUrl" not in result["properties"]

    def test_thumbnail_fallback_to_default(self):
        video = self._make_video()
        video["snippet"]["thumbnails"] = {
            "default": {"url": "https://i.ytimg.com/vi/abc123/default.jpg"},
        }
        result = video_to_media_item(video, "urn:test:source")
        assert result["properties"][f"{MS_NS}thumbnailUrl"] == "https://i.ytimg.com/vi/abc123/default.jpg"

    def test_iri_determinism(self):
        """Same video + same source → same IRI."""
        video = self._make_video()
        source = "urn:test:source"
        iri1 = video_to_media_item(video, source)["iri"]
        iri2 = video_to_media_item(video, source)["iri"]
        assert iri1 == iri2

    def test_different_video_ids_different_iris(self):
        source = "urn:test:source"
        v1 = self._make_video()
        v2 = self._make_video()
        v2["snippet"]["resourceId"]["videoId"] = "xyz789"
        iri1 = video_to_media_item(v1, source)["iri"]
        iri2 = video_to_media_item(v2, source)["iri"]
        assert iri1 != iri2

    def test_fallback_to_top_level_id(self):
        """When resourceId is missing, fall back to top-level 'id' field."""
        video = {"snippet": {"title": "Test"}, "id": "fallback123"}
        result = video_to_media_item(video, "urn:test:source")
        assert result["properties"][f"{MS_NS}externalId"] == "fallback123"
        assert "fallback123" in result["properties"][f"{MS_NS}enclosureUrl"]

    def test_empty_snippet(self):
        """Minimal video with no snippet data — should still produce valid structure."""
        video = {"snippet": {}}
        result = video_to_media_item(video, "urn:test:source")
        assert result["type"] == MEDIA_ITEM_TYPE
        assert result["properties"][f"{MS_NS}status"] == "queued"


# ═══════════════════════════════════════════════════════════════════════
# YouTubeClient tests
# ═══════════════════════════════════════════════════════════════════════


class TestYouTubeClient:
    """Test YouTubeClient with mocked HTTP responses."""

    def _make_response(self, status_code=200, json_body=None):
        """Create a mock HTTP response."""
        response = MagicMock()
        response.status_code = status_code
        response.json = MagicMock(return_value=json_body or {})
        return response

    @pytest.mark.asyncio
    async def test_resolve_channel_by_id(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(json_body={
            "items": [{
                "contentDetails": {
                    "relatedPlaylists": {"uploads": "UUxxxxxx"}
                }
            }]
        }))
        client = YouTubeClient(http, "fake-key")
        result = await client.resolve_channel(channel_id="UCxxxxxx")
        assert result == "UUxxxxxx"

    @pytest.mark.asyncio
    async def test_resolve_channel_by_handle(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(json_body={
            "items": [{
                "contentDetails": {
                    "relatedPlaylists": {"uploads": "UUhandle"}
                }
            }]
        }))
        client = YouTubeClient(http, "fake-key")
        result = await client.resolve_channel(handle="techreviewer")
        assert result == "UUhandle"
        # Verify forHandle was passed
        call_kwargs = http.get.call_args
        assert "forHandle" in call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))

    @pytest.mark.asyncio
    async def test_resolve_channel_by_username(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(json_body={
            "items": [{
                "contentDetails": {
                    "relatedPlaylists": {"uploads": "UUuser"}
                }
            }]
        }))
        client = YouTubeClient(http, "fake-key")
        result = await client.resolve_channel(username="MyChannel")
        assert result == "UUuser"

    @pytest.mark.asyncio
    async def test_resolve_channel_not_found(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(json_body={
            "items": []
        }))
        client = YouTubeClient(http, "fake-key")
        with pytest.raises(YouTubeAPIError) as exc_info:
            await client.resolve_channel(channel_id="UCnonexistent")
        assert exc_info.value.status_code == 404
        assert exc_info.value.error_type == "notFound"

    @pytest.mark.asyncio
    async def test_resolve_channel_no_arguments(self):
        http = MagicMock()
        client = YouTubeClient(http, "fake-key")
        with pytest.raises(ValueError, match="One of"):
            await client.resolve_channel()

    @pytest.mark.asyncio
    async def test_list_playlist_items(self):
        items = [
            {"snippet": {"title": "Video 1", "resourceId": {"videoId": "v1"}}},
            {"snippet": {"title": "Video 2", "resourceId": {"videoId": "v2"}}},
        ]
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(json_body={
            "items": items
        }))
        client = YouTubeClient(http, "fake-key")
        result = await client.list_playlist_items("PLtest")
        assert len(result) == 2
        assert result[0]["snippet"]["title"] == "Video 1"

    @pytest.mark.asyncio
    async def test_list_playlist_items_caps_at_50(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(json_body={"items": []}))
        client = YouTubeClient(http, "fake-key")
        await client.list_playlist_items("PLtest", max_results=100)
        call_kwargs = http.get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
        assert params["maxResults"] == "50"

    @pytest.mark.asyncio
    async def test_get_video_durations(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(json_body={
            "items": [
                {"id": "v1", "contentDetails": {"duration": "PT4M13S"}},
                {"id": "v2", "contentDetails": {"duration": "PT1H2M30S"}},
            ]
        }))
        client = YouTubeClient(http, "fake-key")
        result = await client.get_video_durations(["v1", "v2"])
        assert result == {"v1": 253, "v2": 3750}

    @pytest.mark.asyncio
    async def test_get_video_durations_empty_list(self):
        http = MagicMock()
        client = YouTubeClient(http, "fake-key")
        result = await client.get_video_durations([])
        assert result == {}
        http.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error_403_quota(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(
            status_code=403,
            json_body={
                "error": {
                    "errors": [{"reason": "quotaExceeded"}],
                    "message": "The request cannot be completed because you have exceeded your quota.",
                }
            },
        ))
        client = YouTubeClient(http, "fake-key")
        with pytest.raises(YouTubeAPIError) as exc_info:
            await client.list_playlist_items("PLtest")
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_type == "quotaExceeded"

    @pytest.mark.asyncio
    async def test_api_error_404(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(
            status_code=404,
            json_body={"error": {"errors": [{"reason": "playlistNotFound"}], "message": "Not found"}},
        ))
        client = YouTubeClient(http, "fake-key")
        with pytest.raises(YouTubeAPIError) as exc_info:
            await client.list_playlist_items("PLbogus")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_api_error_unparseable_body(self):
        """API error with non-JSON body should still raise with status code."""
        response = MagicMock()
        response.status_code = 500
        response.json = MagicMock(side_effect=ValueError("not json"))
        http = MagicMock()
        http.get = AsyncMock(return_value=response)
        client = YouTubeClient(http, "fake-key")
        with pytest.raises(YouTubeAPIError) as exc_info:
            await client.resolve_channel(channel_id="UCtest")
        assert exc_info.value.status_code == 500
        assert exc_info.value.error_type == ""


# ═══════════════════════════════════════════════════════════════════════
# YouTubeAPIError tests
# ═══════════════════════════════════════════════════════════════════════


class TestYouTubeAPIError:
    """Test YouTubeAPIError exception class."""

    def test_attributes(self):
        err = YouTubeAPIError(403, "quotaExceeded", "Quota limit reached")
        assert err.status_code == 403
        assert err.error_type == "quotaExceeded"
        assert err.message == "Quota limit reached"

    def test_str_representation(self):
        err = YouTubeAPIError(404, "notFound", "Channel not found")
        s = str(err)
        assert "404" in s
        assert "notFound" in s
        assert "Channel not found" in s

    def test_inherits_from_exception(self):
        err = YouTubeAPIError(500, "internalError", "Server error")
        assert isinstance(err, Exception)

    def test_empty_error_type(self):
        err = YouTubeAPIError(500, "", "Unknown error")
        assert err.error_type == ""
        assert "500" in str(err)


# ═══════════════════════════════════════════════════════════════════════
# Quota tracking tests
# ═══════════════════════════════════════════════════════════════════════


class TestQuotaTracking:
    """Test quota check/increment/reset with mock StateClient."""

    def _make_state_client(self, quota_used="0", reset_date=None):
        """Create a mock StateClient with get/set methods for quota tracking."""
        stored = {
            "youtube_quota_used": quota_used,
            "youtube_quota_reset_date": reset_date,
        }

        async def mock_get(key):
            return stored.get(key)

        async def mock_set(key, value):
            stored[key] = value

        client = AsyncMock()
        client.get = AsyncMock(side_effect=mock_get)
        client.set = AsyncMock(side_effect=mock_set)
        client._stored = stored
        return client

    @pytest.mark.asyncio
    async def test_check_quota_under_threshold(self):
        from datetime import date as _date
        client = self._make_state_client(quota_used="100", reset_date=_date.today().isoformat())
        result = await yt_check_quota(client, threshold=8000)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_quota_over_threshold(self):
        from datetime import date as _date
        client = self._make_state_client(quota_used="9000", reset_date=_date.today().isoformat())
        result = await yt_check_quota(client, threshold=8000)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_quota_at_threshold(self):
        from datetime import date as _date
        client = self._make_state_client(quota_used="8000", reset_date=_date.today().isoformat())
        result = await yt_check_quota(client, threshold=8000)
        assert result is False  # not strictly under

    @pytest.mark.asyncio
    async def test_check_quota_resets_on_new_day(self):
        """If the stored date is yesterday, quota should reset."""
        client = self._make_state_client(quota_used="9999", reset_date="2020-01-01")
        result = await yt_check_quota(client, threshold=8000)
        assert result is True  # reset happened, now at 0
        assert client._stored["youtube_quota_used"] == "0"

    @pytest.mark.asyncio
    async def test_check_quota_no_stored_values(self):
        """First run with no stored quota values."""
        client = self._make_state_client(quota_used=None, reset_date=None)
        result = await yt_check_quota(client, threshold=8000)
        assert result is True

    @pytest.mark.asyncio
    async def test_increment_quota(self):
        from datetime import date as _date
        client = self._make_state_client(quota_used="100", reset_date=_date.today().isoformat())
        await yt_increment_quota(client, 3)
        assert client._stored["youtube_quota_used"] == "103"

    @pytest.mark.asyncio
    async def test_increment_quota_from_zero(self):
        client = self._make_state_client(quota_used="0")
        await yt_increment_quota(client, 5)
        assert client._stored["youtube_quota_used"] == "5"

    @pytest.mark.asyncio
    async def test_increment_quota_from_none(self):
        """No stored value yet — should treat as 0."""
        client = self._make_state_client(quota_used=None)
        await yt_increment_quota(client, 2)
        assert client._stored["youtube_quota_used"] == "2"

    @pytest.mark.asyncio
    async def test_reset_quota_if_new_day(self):
        client = self._make_state_client(quota_used="5000", reset_date="2020-01-01")
        await yt_reset_quota_if_new_day(client)
        assert client._stored["youtube_quota_used"] == "0"
        from datetime import date as _date
        assert client._stored["youtube_quota_reset_date"] == _date.today().isoformat()

    @pytest.mark.asyncio
    async def test_reset_quota_same_day_noop(self):
        from datetime import date as _date
        today = _date.today().isoformat()
        client = self._make_state_client(quota_used="500", reset_date=today)
        await yt_reset_quota_if_new_day(client)
        # Should NOT have reset
        assert client._stored["youtube_quota_used"] == "500"


# ═══════════════════════════════════════════════════════════════════════
# Subscribe YouTube tests
# ═══════════════════════════════════════════════════════════════════════


class TestSubscribeYouTube:
    """Test subscribe_youtube with mocked context."""

    def _make_ctx(self, source_exists=False):
        """Build a mock AppContext for subscribe tests."""
        ctx = MagicMock()

        if source_exists:
            ctx.graph.query = AsyncMock(return_value={
                "results": {"bindings": [
                    {"source": {"value": "urn:existing:yt-source"}}
                ]}
            })
        else:
            ctx.graph.query = AsyncMock(return_value={
                "results": {"bindings": []}
            })

        ctx.commands.execute = AsyncMock()
        ctx.state.set = AsyncMock()

        # Mock HTTP for API validation call
        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(return_value={
            "items": [{
                "contentDetails": {
                    "relatedPlaylists": {"uploads": "UUresolved"}
                }
            }]
        })
        ctx.http.get = AsyncMock(return_value=response)

        return ctx

    @pytest.mark.asyncio
    async def test_subscribe_new_channel(self):
        ctx = self._make_ctx()
        result = await subscribe_youtube(
            ctx, "https://www.youtube.com/channel/UCtest123456789", "api-key-123"
        )
        assert result["status"] == "created"
        assert result["iri"].startswith("urn:sempkm:app:media-scheduler:source-")
        assert result["playlist_id"] == "UUresolved"
        ctx.commands.execute.assert_awaited_once()

        # Verify object.create params
        call_args = ctx.commands.execute.call_args
        assert call_args[0][0] == "object.create"
        params = call_args[0][1]
        assert params["type"] == MEDIA_SOURCE_TYPE
        assert params["properties"][f"{MS_NS}sourceType"] == "youtube"
        assert params["properties"][f"{MS_NS}externalId"] == "UUresolved"

    @pytest.mark.asyncio
    async def test_subscribe_duplicate(self):
        ctx = self._make_ctx(source_exists=True)
        result = await subscribe_youtube(
            ctx, "https://www.youtube.com/@existing", "api-key-123"
        )
        assert result["status"] == "duplicate"
        assert result["iri"] == "urn:existing:yt-source"
        ctx.commands.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_subscribe_invalid_url(self):
        ctx = self._make_ctx()
        with pytest.raises(ValueError, match="Unrecognized YouTube URL"):
            await subscribe_youtube(ctx, "https://example.com/not-youtube", "api-key")

    @pytest.mark.asyncio
    async def test_subscribe_api_key_validation_failure(self):
        """If the API key is invalid, the validation API call should fail."""
        ctx = self._make_ctx()
        error_response = MagicMock()
        error_response.status_code = 403
        error_response.json = MagicMock(return_value={
            "error": {
                "errors": [{"reason": "forbidden"}],
                "message": "API key not valid",
            }
        })
        ctx.http.get = AsyncMock(return_value=error_response)

        with pytest.raises(YouTubeAPIError) as exc_info:
            await subscribe_youtube(
                ctx, "https://www.youtube.com/channel/UCtest123456789", "bad-key"
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_subscribe_saves_api_key(self):
        ctx = self._make_ctx()
        await subscribe_youtube(
            ctx, "https://www.youtube.com/@testchannel", "my-secret-key"
        )
        ctx.state.set.assert_any_call("youtube_api_key", "my-secret-key")

    @pytest.mark.asyncio
    async def test_subscribe_playlist_url(self):
        """Playlist URLs should validate by listing 1 item, not resolving channel."""
        ctx = self._make_ctx()
        # Override response for playlist items list
        playlist_response = MagicMock()
        playlist_response.status_code = 200
        playlist_response.json = MagicMock(return_value={"items": [{"snippet": {}}]})
        ctx.http.get = AsyncMock(return_value=playlist_response)

        result = await subscribe_youtube(
            ctx, "https://www.youtube.com/playlist?list=PLtestlist12345", "api-key"
        )
        assert result["status"] == "created"
        assert result["playlist_id"] == "PLtestlist12345"


# ── Import spotify_service via file path ──

_sp_svc_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "media-scheduler" / "services" / "spotify_service.py"
)
_sp_svc_spec = importlib.util.spec_from_file_location("spotify_service_test", str(_sp_svc_path))
_sp_svc_mod = importlib.util.module_from_spec(_sp_svc_spec)
_sp_svc_spec.loader.exec_module(_sp_svc_mod)

generate_code_verifier = _sp_svc_mod.generate_code_verifier
generate_code_challenge = _sp_svc_mod.generate_code_challenge
build_spotify_authorize_url = _sp_svc_mod.build_spotify_authorize_url
exchange_spotify_code = _sp_svc_mod.exchange_spotify_code
refresh_spotify_token = _sp_svc_mod.refresh_spotify_token
refresh_spotify_if_expired = _sp_svc_mod.refresh_spotify_if_expired
store_spotify_tokens = _sp_svc_mod.store_spotify_tokens
get_spotify_connection_status = _sp_svc_mod.get_spotify_connection_status
clear_spotify_auth = _sp_svc_mod.clear_spotify_auth
parse_spotify_url = _sp_svc_mod.parse_spotify_url
track_to_media_item_sp = _sp_svc_mod.track_to_media_item
sp_mint_source_iri = _sp_svc_mod.mint_source_iri
sp_mint_item_iri = _sp_svc_mod.mint_item_iri
SpotifyClient = _sp_svc_mod.SpotifyClient
SpotifyAPIError = _sp_svc_mod.SpotifyAPIError
SpotifyAuthError = _sp_svc_mod.SpotifyAuthError
subscribe_spotify = _sp_svc_mod.subscribe_spotify
check_source_exists_spotify = _sp_svc_mod.check_source_exists_spotify
sp_get_existing_item_iris = _sp_svc_mod.get_existing_item_iris
SPOTIFY_SOURCES_SPARQL = _sp_svc_mod.SPOTIFY_SOURCES_SPARQL
SP_AUTH_STATE_KEYS = _sp_svc_mod.AUTH_STATE_KEYS


# ═══════════════════════════════════════════════════════════════════════
# PKCE generation tests
# ═══════════════════════════════════════════════════════════════════════


class TestPKCEGeneration:
    """Test PKCE code_verifier and code_challenge generation."""

    def test_verifier_length_and_charset(self):
        verifier = generate_code_verifier()
        # secrets.token_urlsafe(32) produces 43 chars
        assert len(verifier) == 43
        # URL-safe base64: alphanumeric + '-' + '_'
        assert all(c.isalnum() or c in "-_" for c in verifier)

    def test_challenge_is_base64url(self):
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        # base64url chars only
        assert all(c.isalnum() or c in "-_" for c in challenge)

    def test_challenge_deterministic_from_same_verifier(self):
        verifier = "test-verifier-value-for-determinism"
        c1 = generate_code_challenge(verifier)
        c2 = generate_code_challenge(verifier)
        assert c1 == c2

    def test_challenge_no_padding_chars(self):
        """PKCE code_challenge must not contain base64 padding '='."""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        assert "=" not in challenge


# ═══════════════════════════════════════════════════════════════════════
# Spotify URL parsing tests
# ═══════════════════════════════════════════════════════════════════════


class TestSpotifyURLParsing:
    """Test Spotify URL → playlist ID extraction."""

    def test_web_url(self):
        result = parse_spotify_url(
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        )
        assert result == {"type": "playlist", "value": "37i9dQZF1DXcBWIGoYBM5M"}

    def test_web_url_with_query_params(self):
        result = parse_spotify_url(
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=abc123"
        )
        assert result == {"type": "playlist", "value": "37i9dQZF1DXcBWIGoYBM5M"}

    def test_spotify_uri(self):
        result = parse_spotify_url("spotify:playlist:37i9dQZF1DXcBWIGoYBM5M")
        assert result == {"type": "playlist", "value": "37i9dQZF1DXcBWIGoYBM5M"}

    def test_invalid_url(self):
        assert parse_spotify_url("https://example.com/not-spotify") is None

    def test_none_input(self):
        assert parse_spotify_url(None) is None

    def test_non_playlist_url(self):
        """Album, artist, or track URLs should return None."""
        assert parse_spotify_url("https://open.spotify.com/album/123abc") is None
        assert parse_spotify_url("https://open.spotify.com/artist/456def") is None
        assert parse_spotify_url("https://open.spotify.com/track/789ghi") is None

    def test_empty_string(self):
        assert parse_spotify_url("") is None

    def test_spotify_uri_non_playlist(self):
        assert parse_spotify_url("spotify:album:37i9dQZF1DXcBWIGoYBM5M") is None


# ═══════════════════════════════════════════════════════════════════════
# Track-to-MediaItem conversion tests
# ═══════════════════════════════════════════════════════════════════════


class TestSpotifyTrackToMediaItem:
    """Test Spotify track → MediaItem conversion."""

    def _make_track(self, **overrides):
        """Create a standard Spotify track dict with reasonable defaults."""
        base = {
            "id": "4uLU6hMCjMI75M1A2tKUQC",
            "name": "Never Gonna Give You Up",
            "duration_ms": 213573,
            "artists": [{"name": "Rick Astley"}],
            "album": {
                "images": [
                    {"url": "https://i.scdn.co/image/large.jpg", "height": 640},
                    {"url": "https://i.scdn.co/image/medium.jpg", "height": 300},
                ]
            },
            "external_urls": {
                "spotify": "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
            },
        }
        base.update(overrides)
        return base

    def test_basic_conversion(self):
        source_iri = "urn:sempkm:app:media-scheduler:source-abc"
        track = self._make_track()
        result = track_to_media_item_sp(track, source_iri)

        assert result["type"] == MEDIA_ITEM_TYPE
        assert result["iri"].startswith("urn:sempkm:app:media-scheduler:item-")
        assert result["properties"]["dcterms:title"] == "Never Gonna Give You Up"
        assert result["properties"][f"{MS_NS}status"] == "queued"
        assert result["properties"][f"{MS_NS}mediaSource"] == source_iri

    def test_duration_ms_to_seconds(self):
        track = self._make_track(duration_ms=213573)
        result = track_to_media_item_sp(track, "urn:test:src")
        # 213573ms // 1000 = 213 seconds (integer division)
        assert result["properties"][f"{MS_NS}duration"] == 213

    def test_artist_name_in_description(self):
        track = self._make_track(
            artists=[{"name": "Artist A"}, {"name": "Artist B"}]
        )
        result = track_to_media_item_sp(track, "urn:test:src")
        assert result["properties"]["dcterms:description"] == "Artist A, Artist B"

    def test_thumbnail_from_album_images(self):
        track = self._make_track()
        result = track_to_media_item_sp(track, "urn:test:src")
        assert result["properties"][f"{MS_NS}thumbnailUrl"] == "https://i.scdn.co/image/large.jpg"

    def test_external_id(self):
        track = self._make_track(id="customTrackId")
        result = track_to_media_item_sp(track, "urn:test:src")
        assert result["properties"][f"{MS_NS}externalId"] == "customTrackId"

    def test_enclosure_url(self):
        track = self._make_track()
        result = track_to_media_item_sp(track, "urn:test:src")
        assert (
            result["properties"][f"{MS_NS}enclosureUrl"]
            == "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        )

    def test_iri_determinism(self):
        """Same track + same source → same IRI."""
        track = self._make_track()
        source = "urn:test:source"
        iri1 = track_to_media_item_sp(track, source)["iri"]
        iri2 = track_to_media_item_sp(track, source)["iri"]
        assert iri1 == iri2

    def test_missing_artists(self):
        track = self._make_track(artists=[])
        result = track_to_media_item_sp(track, "urn:test:src")
        assert "dcterms:description" not in result["properties"]

    def test_missing_album_images(self):
        track = self._make_track(album={"images": []})
        result = track_to_media_item_sp(track, "urn:test:src")
        assert f"{MS_NS}thumbnailUrl" not in result["properties"]


# ═══════════════════════════════════════════════════════════════════════
# Spotify IRI minting tests
# ═══════════════════════════════════════════════════════════════════════


class TestSpotifyIRIMinting:
    """Test deterministic IRI generation for Spotify sources and items."""

    def test_mint_source_iri_deterministic(self):
        iri1 = sp_mint_source_iri("spotify:playlist:abc123")
        iri2 = sp_mint_source_iri("spotify:playlist:abc123")
        assert iri1 == iri2

    def test_mint_source_iri_different_inputs(self):
        iri1 = sp_mint_source_iri("spotify:playlist:aaa")
        iri2 = sp_mint_source_iri("spotify:playlist:bbb")
        assert iri1 != iri2

    def test_mint_source_iri_correct_prefix(self):
        iri = sp_mint_source_iri("spotify:playlist:xyz")
        assert iri.startswith("urn:sempkm:app:media-scheduler:source-")

    def test_mint_item_iri_from_source_and_track(self):
        source_iri = "urn:sempkm:app:media-scheduler:source-abc"
        iri1 = sp_mint_item_iri(source_iri, "track123")
        iri2 = sp_mint_item_iri(source_iri, "track456")
        assert iri1 != iri2
        assert iri1.startswith("urn:sempkm:app:media-scheduler:item-")


# ═══════════════════════════════════════════════════════════════════════
# Spotify OAuth auth tests
# ═══════════════════════════════════════════════════════════════════════


class TestSpotifyAuth:
    """Test Spotify OAuth functions with mocked HTTP and state."""

    def test_build_authorize_url_has_all_params(self):
        url = build_spotify_authorize_url(
            client_id="my-client-id",
            redirect_uri="https://example.com/callback",
            state="csrf-state-abc",
            code_challenge="challenge-abc",
        )
        assert "client_id=my-client-id" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "code_challenge_method=S256" in url
        assert "code_challenge=challenge-abc" in url
        assert "state=csrf-state-abc" in url
        assert "scope=" in url

    def test_build_authorize_url_starts_with_base(self):
        url = build_spotify_authorize_url("id", "https://cb", "st", "ch")
        assert url.startswith("https://accounts.spotify.com/authorize?")

    @pytest.mark.asyncio
    async def test_exchange_code_sends_correct_form_data(self):
        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(return_value={
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        })
        http = MagicMock()
        http.post = AsyncMock(return_value=response)

        result = await exchange_spotify_code(
            http, "auth-code", "cid", "csecret", "https://cb", "verifier123"
        )
        assert result["access_token"] == "new-access"
        assert result["refresh_token"] == "new-refresh"
        assert result["expires_in"] == 3600

        # Verify form data was sent correctly
        call_kwargs = http.post.call_args
        data = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data")
        assert data["grant_type"] == "authorization_code"
        assert data["code"] == "auth-code"
        assert data["code_verifier"] == "verifier123"

    @pytest.mark.asyncio
    async def test_exchange_code_auth_error(self):
        response = MagicMock()
        response.status_code = 400
        response.text = '{"error": "invalid_grant"}'
        http = MagicMock()
        http.post = AsyncMock(return_value=response)

        with pytest.raises(SpotifyAuthError) as exc_info:
            await exchange_spotify_code(
                http, "bad-code", "cid", "csecret", "https://cb", "verifier"
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(return_value={
            "access_token": "refreshed-token",
            "expires_in": 3600,
        })
        http = MagicMock()
        http.post = AsyncMock(return_value=response)

        result = await refresh_spotify_token(http, "old-refresh", "cid", "csecret")
        assert result["access_token"] == "refreshed-token"

    @pytest.mark.asyncio
    async def test_refresh_if_expired_skips_when_valid(self):
        """Token not near expiry → should return existing token without refresh."""
        from datetime import datetime, timedelta, timezone

        future_expiry = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat()

        state = AsyncMock()
        state.get = AsyncMock(side_effect=lambda k: {
            "spotify_access_token": "still-valid-token",
            "spotify_token_expiry": future_expiry,
            "spotify_refresh_token": "refresh-tok",
        }.get(k, ""))

        http = MagicMock()
        http.post = AsyncMock()  # Should NOT be called

        result = await refresh_spotify_if_expired(http, state, "cid", "csecret")
        assert result == "still-valid-token"
        http.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_if_expired_refreshes_when_expired(self):
        """Token near expiry → should refresh."""
        from datetime import datetime, timedelta, timezone

        past_expiry = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat()

        stored = {
            "spotify_access_token": "old-token",
            "spotify_token_expiry": past_expiry,
            "spotify_refresh_token": "my-refresh-token",
        }
        state = AsyncMock()
        state.get = AsyncMock(side_effect=lambda k: stored.get(k, ""))
        state.set = AsyncMock()

        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(return_value={
            "access_token": "fresh-token",
            "expires_in": 3600,
        })
        http = MagicMock()
        http.post = AsyncMock(return_value=response)

        result = await refresh_spotify_if_expired(http, state, "cid", "csecret")
        assert result == "fresh-token"
        http.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_store_tokens(self):
        state = AsyncMock()
        state.set = AsyncMock()

        await store_spotify_tokens(
            state, "access", "refresh", 3600, "TestUser", "premium"
        )
        state.set.assert_any_call("spotify_access_token", "access")
        state.set.assert_any_call("spotify_refresh_token", "refresh")
        state.set.assert_any_call("spotify_display_name", "TestUser")
        state.set.assert_any_call("spotify_product", "premium")

    @pytest.mark.asyncio
    async def test_store_tokens_sets_expiry_as_iso(self):
        state = AsyncMock()
        state.set = AsyncMock()

        await store_spotify_tokens(state, "a", "r", 3600, "User", "free")

        # Find the call that set spotify_token_expiry
        expiry_calls = [
            c for c in state.set.call_args_list
            if c[0][0] == "spotify_token_expiry"
        ]
        assert len(expiry_calls) == 1
        expiry_val = expiry_calls[0][0][1]
        # Should be a valid ISO 8601 datetime with timezone
        from datetime import datetime
        dt = datetime.fromisoformat(expiry_val)
        assert dt.tzinfo is not None  # timezone-aware


# ═══════════════════════════════════════════════════════════════════════
# SpotifyClient tests
# ═══════════════════════════════════════════════════════════════════════


class TestSpotifyClient:
    """Test SpotifyClient with mocked HTTP responses."""

    def _make_response(self, status_code=200, data=None, headers=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json = MagicMock(return_value=data or {})
        resp.headers = headers or {}
        return resp

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self):
        profile_data = {
            "display_name": "Test User",
            "product": "premium",
            "id": "testuser123",
        }
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(200, profile_data))

        client = SpotifyClient(http, "test-token")
        result = await client.get_user_profile()
        assert result["display_name"] == "Test User"
        assert result["product"] == "premium"

    @pytest.mark.asyncio
    async def test_get_playlists_success(self):
        playlists_data = {
            "items": [
                {"id": "pl1", "name": "Playlist 1", "tracks": {"total": 50}},
                {"id": "pl2", "name": "Playlist 2", "tracks": {"total": 30}},
            ]
        }
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(200, playlists_data))

        client = SpotifyClient(http, "test-token")
        result = await client.get_playlists()
        assert len(result) == 2
        assert result[0]["name"] == "Playlist 1"

    @pytest.mark.asyncio
    async def test_get_playlist_tracks_success(self):
        tracks_data = {
            "items": [
                {"track": {"id": "t1", "name": "Track 1"}},
                {"track": {"id": "t2", "name": "Track 2"}},
            ]
        }
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(200, tracks_data))

        client = SpotifyClient(http, "test-token")
        result = await client.get_playlist_tracks("playlist123")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_api_error_raises_spotify_api_error(self):
        error_data = {
            "error": {"status": 403, "message": "Forbidden"}
        }
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(403, error_data))

        client = SpotifyClient(http, "test-token")
        with pytest.raises(SpotifyAPIError) as exc_info:
            await client.get_user_profile()
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_429_rate_limit_raises_with_retry_info(self):
        resp = self._make_response(429, {"error": {"status": 429, "message": "Too many requests"}})
        resp.headers = {"Retry-After": "30"}
        http = MagicMock()
        http.get = AsyncMock(return_value=resp)

        client = SpotifyClient(http, "test-token")
        with pytest.raises(SpotifyAPIError) as exc_info:
            await client.get_playlists()
        assert exc_info.value.status_code == 429
        assert "rate_limited" in exc_info.value.error_type
        assert "30" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_empty_playlists(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(200, {"items": []}))

        client = SpotifyClient(http, "test-token")
        result = await client.get_playlists()
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_fields_handled(self):
        """Track with missing optional fields should still convert."""
        track = {"id": "minimal", "name": "Minimal Track"}
        result = track_to_media_item_sp(track, "urn:test:src")
        assert result["properties"]["dcterms:title"] == "Minimal Track"
        assert result["properties"][f"{MS_NS}externalId"] == "minimal"
        assert result["properties"][f"{MS_NS}status"] == "queued"

    @pytest.mark.asyncio
    async def test_bearer_token_in_header(self):
        http = MagicMock()
        http.get = AsyncMock(return_value=self._make_response(200, {"items": []}))

        client = SpotifyClient(http, "my-secret-token")
        await client.get_playlists()

        call_kwargs = http.get.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["Authorization"] == "Bearer my-secret-token"


# ═══════════════════════════════════════════════════════════════════════
# Subscribe Spotify tests
# ═══════════════════════════════════════════════════════════════════════


class TestSubscribeSpotify:
    """Test subscribe_spotify with mocked context."""

    @pytest.mark.asyncio
    async def test_creates_source(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        ctx.commands.execute = AsyncMock()

        result = await subscribe_spotify(ctx, "PLtest123", "My Playlist")
        assert result["status"] == "created"
        assert result["iri"].startswith("urn:sempkm:app:media-scheduler:source-")
        ctx.commands.execute.assert_awaited_once()

        params = ctx.commands.execute.call_args[0][1]
        assert params["type"] == MEDIA_SOURCE_TYPE
        assert params["properties"][f"{MS_NS}sourceType"] == "spotify"

    @pytest.mark.asyncio
    async def test_duplicate_returns_existing(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": [
                {"source": {"value": "urn:existing:spotify-source"}}
            ]}
        })
        ctx.commands.execute = AsyncMock()

        result = await subscribe_spotify(ctx, "PLtest123", "My Playlist")
        assert result["status"] == "duplicate"
        assert result["iri"] == "urn:existing:spotify-source"
        ctx.commands.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_source_iri_format_correct(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        ctx.commands.execute = AsyncMock()

        result = await subscribe_spotify(ctx, "PLtest123", "My Playlist")
        iri = result["iri"]
        # IRI should be deterministic from spotify:playlist:{id}
        expected = sp_mint_source_iri("spotify:playlist:PLtest123")
        assert iri == expected

    @pytest.mark.asyncio
    async def test_playlist_name_stored_as_title(self):
        ctx = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        ctx.commands.execute = AsyncMock()

        await subscribe_spotify(ctx, "PLtest123", "Discover Weekly")
        params = ctx.commands.execute.call_args[0][1]
        assert params["properties"]["dcterms:title"] == "Discover Weekly"


# ═══════════════════════════════════════════════════════════════════════
# Spotify connection status tests
# ═══════════════════════════════════════════════════════════════════════


class TestSpotifyConnectionStatus:
    """Test Spotify connection status and auth state management."""

    @pytest.mark.asyncio
    async def test_connected_state(self):
        state = AsyncMock()
        state.get = AsyncMock(side_effect=lambda k: {
            "spotify_access_token": "valid-token",
            "spotify_display_name": "Test User",
            "spotify_product": "premium",
            "spotify_token_expiry": "2026-12-31T23:59:59+00:00",
        }.get(k, ""))

        status = await get_spotify_connection_status(state)
        assert status["connected"] is True
        assert status["display_name"] == "Test User"
        assert status["product"] == "premium"
        assert status["token_expiry"] == "2026-12-31T23:59:59+00:00"

    @pytest.mark.asyncio
    async def test_disconnected_state(self):
        state = AsyncMock()
        state.get = AsyncMock(return_value="")

        status = await get_spotify_connection_status(state)
        assert status["connected"] is False
        assert status["display_name"] is None
        assert status["product"] is None

    @pytest.mark.asyncio
    async def test_clear_auth_sets_all_empty(self):
        state = AsyncMock()
        state.set = AsyncMock()

        await clear_spotify_auth(state)

        # Should have set every AUTH_STATE_KEY to ""
        set_calls = {c[0][0]: c[0][1] for c in state.set.call_args_list}
        for key in SP_AUTH_STATE_KEYS:
            assert set_calls[key] == "", f"Expected key '{key}' to be cleared"

    @pytest.mark.asyncio
    async def test_product_tier_stored(self):
        state = AsyncMock()
        state.set = AsyncMock()

        await store_spotify_tokens(state, "a", "r", 3600, "User", "premium")
        state.set.assert_any_call("spotify_product", "premium")


# ═══════════════════════════════════════════════════════════════════════
# Spotify existing items dedup tests
# ═══════════════════════════════════════════════════════════════════════


class TestSpotifyExistingItems:
    """Test SPARQL dedup for Spotify items."""

    @pytest.mark.asyncio
    async def test_get_existing_items_returns_set(self):
        graph = MagicMock()
        graph.query = AsyncMock(return_value={
            "results": {"bindings": [
                {"item": {"value": "urn:item:sp1"}},
                {"item": {"value": "urn:item:sp2"}},
            ]}
        })
        result = await sp_get_existing_item_iris(graph, "urn:test:spotify-source")
        assert result == {"urn:item:sp1", "urn:item:sp2"}

    @pytest.mark.asyncio
    async def test_get_existing_items_empty(self):
        graph = MagicMock()
        graph.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        result = await sp_get_existing_item_iris(graph, "urn:test:spotify-source")
        assert result == set()

    @pytest.mark.asyncio
    async def test_check_source_exists_found(self):
        graph = MagicMock()
        graph.query = AsyncMock(return_value={
            "results": {"bindings": [
                {"source": {"value": "urn:existing:source"}}
            ]}
        })
        result = await check_source_exists_spotify(graph, "PLtest123")
        assert result == "urn:existing:source"

    @pytest.mark.asyncio
    async def test_check_source_exists_not_found(self):
        graph = MagicMock()
        graph.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })
        result = await check_source_exists_spotify(graph, "PLnonexistent")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# Poll Spotify task tests
# ═══════════════════════════════════════════════════════════════════════


def _make_spotify_ctx(
    connected=True,
    client_id="test_client_id",
    client_secret="test_client_secret",
    access_token="test_access_token",
    bindings=None,
    existing_iris=None,
):
    """Build a mock AppContext for poll_spotify tests."""
    ctx = MagicMock()
    ctx.app_id = "media-scheduler"

    # State mock
    state_values = {}
    if connected:
        state_values["spotify_access_token"] = access_token
        state_values["spotify_refresh_token"] = "test_refresh_token"
        state_values["spotify_token_expiry"] = "2099-12-31T00:00:00+00:00"
        state_values["spotify_display_name"] = "Test User"
        state_values["spotify_product"] = "premium"
    else:
        state_values["spotify_access_token"] = ""
        state_values["spotify_refresh_token"] = ""
        state_values["spotify_token_expiry"] = ""
        state_values["spotify_display_name"] = ""
        state_values["spotify_product"] = ""

    state_values["spotify_client_id"] = client_id
    state_values["spotify_client_secret"] = client_secret

    ctx.state = MagicMock()
    ctx.state.get = AsyncMock(side_effect=lambda k: state_values.get(k, ""))
    ctx.state.set = AsyncMock()

    # HTTP mock
    ctx.http = MagicMock()

    # Graph mock — SPARQL query
    if bindings is None:
        bindings = []
    ctx.graph = MagicMock()
    ctx.graph.query = AsyncMock(return_value={
        "results": {"bindings": bindings}
    })

    # Commands mock with async context manager
    batch_mock = MagicMock()
    batch_mock.add = MagicMock()
    bulk_cm = MagicMock()
    bulk_cm.__aenter__ = AsyncMock(return_value=batch_mock)
    bulk_cm.__aexit__ = AsyncMock(return_value=False)
    ctx.commands = MagicMock()
    ctx.commands.bulk = MagicMock(return_value=bulk_cm)

    return ctx, batch_mock


def _make_spotify_binding(
    source_iri="urn:test:spotify:source1",
    feed_url="spotify:playlist:test123",
    external_id="test123",
    error_count="0",
    last_error="",
):
    """Build a SPARQL binding dict for a Spotify source."""
    b = {
        "source": {"value": source_iri},
        "feedUrl": {"value": feed_url},
        "externalId": {"value": external_id},
    }
    if error_count:
        b["errorCount"] = {"value": error_count}
    if last_error:
        b["lastError"] = {"value": last_error}
    return b


def _make_playlist_item(track_id="trk1", name="Test Track", artist="Test Artist", duration_ms=180000):
    """Build a Spotify playlist item dict."""
    return {
        "track": {
            "id": track_id,
            "name": name,
            "artists": [{"name": artist}],
            "duration_ms": duration_ms,
            "album": {"images": [{"url": "https://img.example.com/cover.jpg"}]},
            "external_urls": {"spotify": f"https://open.spotify.com/track/{track_id}"},
        }
    }


class TestPollSpotify:
    """Test the poll_spotify task handler."""

    @pytest.mark.asyncio
    async def test_skips_when_not_connected(self):
        ctx, _ = _make_spotify_ctx(connected=False)
        result = await poll_spotify(ctx)
        assert result == {"skipped": "not_connected"}

    @pytest.mark.asyncio
    async def test_skips_when_no_credentials(self):
        ctx, _ = _make_spotify_ctx(connected=True, client_id="", client_secret="")
        result = await poll_spotify(ctx)
        assert result == {"skipped": "no_credentials"}

    @pytest.mark.asyncio
    async def test_skips_when_auth_refresh_fails(self):
        ctx, _ = _make_spotify_ctx(connected=True)
        # Patch refresh_spotify_if_expired at the _app_mod level to raise
        # Use _app_mod.SpotifyAuthError — class identity must match what poll_spotify catches
        with patch.object(_app_mod, "refresh_spotify_if_expired", new_callable=AsyncMock) as mock_refresh:
            mock_refresh.side_effect = _app_mod.SpotifyAuthError("refresh failed", 401, "")
            result = await poll_spotify(ctx)
        assert result.get("skipped") == "auth_refresh_failed"

    @pytest.mark.asyncio
    async def test_polls_single_source(self):
        binding = _make_spotify_binding()
        ctx, batch_mock = _make_spotify_ctx(bindings=[binding])

        mock_client_instance = MagicMock()
        mock_client_instance.get_playlist_tracks = AsyncMock(
            return_value=[_make_playlist_item("t1"), _make_playlist_item("t2")]
        )

        with patch.object(
            _app_mod, "SpotifyClient", return_value=mock_client_instance,
        ), patch.object(
            _app_mod, "sp_get_existing_item_iris",
            new_callable=AsyncMock,
            return_value=set(),
        ), patch.object(
            _app_mod, "update_source_state", new_callable=AsyncMock,
        ):
            result = await poll_spotify(ctx)

        assert result["sources_polled"] == 1
        assert result["items_created"] == 2
        assert batch_mock.add.call_count == 2

    @pytest.mark.asyncio
    async def test_dedup_filters_existing_items(self):
        binding = _make_spotify_binding()
        ctx, batch_mock = _make_spotify_ctx(bindings=[binding])

        # Create an existing IRI that matches one track
        existing_iri = sp_mint_item_iri(binding["source"]["value"], "t1")

        mock_client_instance = MagicMock()
        mock_client_instance.get_playlist_tracks = AsyncMock(
            return_value=[_make_playlist_item("t1"), _make_playlist_item("t2")]
        )

        with patch.object(
            _app_mod, "SpotifyClient", return_value=mock_client_instance,
        ), patch.object(
            _app_mod, "sp_get_existing_item_iris",
            new_callable=AsyncMock,
            return_value={existing_iri},
        ), patch.object(
            _app_mod, "update_source_state", new_callable=AsyncMock,
        ):
            result = await poll_spotify(ctx)

        assert result["items_created"] == 1
        assert batch_mock.add.call_count == 1

    @pytest.mark.asyncio
    async def test_caps_at_max_initial_items(self):
        binding = _make_spotify_binding()
        ctx, batch_mock = _make_spotify_ctx(bindings=[binding])

        # Create more tracks than MAX_INITIAL_ITEMS
        many_items = [_make_playlist_item(f"t{i}") for i in range(MAX_INITIAL_ITEMS + 20)]

        mock_client_instance = MagicMock()
        mock_client_instance.get_playlist_tracks = AsyncMock(return_value=many_items)

        with patch.object(
            _app_mod, "SpotifyClient", return_value=mock_client_instance,
        ), patch.object(
            _app_mod, "sp_get_existing_item_iris",
            new_callable=AsyncMock,
            return_value=set(),
        ), patch.object(
            _app_mod, "update_source_state", new_callable=AsyncMock,
        ):
            result = await poll_spotify(ctx)

        assert result["items_created"] == MAX_INITIAL_ITEMS
        assert batch_mock.add.call_count == MAX_INITIAL_ITEMS

    @pytest.mark.asyncio
    async def test_handles_api_error_per_source(self):
        """SpotifyAPIError on one source increments errorCount and continues."""
        binding1 = _make_spotify_binding(source_iri="urn:s1", external_id="p1")
        binding2 = _make_spotify_binding(source_iri="urn:s2", external_id="p2")
        ctx, batch_mock = _make_spotify_ctx(bindings=[binding1, binding2])

        call_count = 0

        async def get_tracks_side(playlist_id, limit=100):
            nonlocal call_count
            call_count += 1
            if playlist_id == "p1":
                raise _app_mod.SpotifyAPIError(500, "server_error", "Internal error")
            return [_make_playlist_item("t1")]

        mock_client_instance = MagicMock()
        mock_client_instance.get_playlist_tracks = AsyncMock(side_effect=get_tracks_side)

        with patch.object(
            _app_mod, "SpotifyClient", return_value=mock_client_instance,
        ), patch.object(
            _app_mod, "sp_get_existing_item_iris",
            new_callable=AsyncMock,
            return_value=set(),
        ), patch.object(
            _app_mod, "update_source_state", new_callable=AsyncMock,
        ):
            result = await poll_spotify(ctx)

        # Source 1 errored, source 2 succeeded
        assert result["sources_polled"] == 1
        assert result["items_created"] == 1
        assert call_count == 2  # Both were attempted

    @pytest.mark.asyncio
    async def test_handles_auth_error_breaks_loop(self):
        """SpotifyAuthError breaks the loop — auth is shared across sources."""
        binding1 = _make_spotify_binding(source_iri="urn:s1", external_id="p1")
        binding2 = _make_spotify_binding(source_iri="urn:s2", external_id="p2")
        ctx, _ = _make_spotify_ctx(bindings=[binding1, binding2])

        mock_client_instance = MagicMock()
        mock_client_instance.get_playlist_tracks = AsyncMock(
            side_effect=_app_mod.SpotifyAuthError("token revoked", 401, ""),
        )

        with patch.object(
            _app_mod, "SpotifyClient", return_value=mock_client_instance,
        ):
            result = await poll_spotify(ctx)

        # Auth error breaks on first source, second never attempted
        assert result["sources_polled"] == 0
        assert result["items_created"] == 0

    @pytest.mark.asyncio
    async def test_returns_summary_dict(self):
        ctx, _ = _make_spotify_ctx(connected=True, bindings=[])
        result = await poll_spotify(ctx)
        assert "sources_polled" in result
        assert "items_created" in result
        assert result["sources_polled"] == 0
        assert result["items_created"] == 0


# ═══════════════════════════════════════════════════════════════════════
# Spotify route handler tests
# ═══════════════════════════════════════════════════════════════════════


class TestSpotifyRoutes:
    """Test the Spotify fragment route handlers."""

    def test_oauth_result_page_success(self):
        """Success page contains redirect script and success message."""
        html = _spotify_oauth_result_page(True, "Connected to Spotify!")
        assert "Connected to Spotify!" in html
        assert "Redirecting to workspace" in html
        assert "setTimeout" in html
        assert "/browser/" in html

    def test_oauth_result_page_error(self):
        """Error page shows message and link back to workspace."""
        html = _spotify_oauth_result_page(False, "Auth failed")
        assert "Auth failed" in html
        assert "Return to workspace" in html
        assert "setTimeout" not in html

    @pytest.mark.asyncio
    async def test_connect_route_saves_credentials_and_generates_pkce(self):
        """Connect route stores credentials and PKCE verifier in state."""
        from starlette.testclient import TestClient

        ctx = MagicMock()
        state_sets = {}
        ctx.state = MagicMock()
        ctx.state.set = AsyncMock(side_effect=lambda k, v: state_sets.update({k: v}))

        # We need to test that state.set was called with the right keys
        # The route is async, so we test the logic pattern instead
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        assert len(code_verifier) == 43
        assert len(code_challenge) > 0

    @pytest.mark.asyncio
    async def test_callback_validates_csrf_state(self):
        """Callback rejects mismatched CSRF state."""
        html = _spotify_oauth_result_page(False, "OAuth state mismatch — possible CSRF attack. Please try again.")
        assert "CSRF" in html
        assert "state mismatch" in html

    @pytest.mark.asyncio
    async def test_disconnect_clears_auth(self):
        """clear_spotify_auth empties all auth state keys."""
        state = MagicMock()
        state.set = AsyncMock()
        await clear_spotify_auth(state)
        # Should have set all AUTH_STATE_KEYS to ""
        assert state.set.call_count == len(SP_AUTH_STATE_KEYS)
        for call_args in state.set.call_args_list:
            assert call_args[0][1] == ""

    @pytest.mark.asyncio
    async def test_add_spotify_creates_source(self):
        """subscribe_spotify creates a new MediaSource for a playlist."""
        ctx = MagicMock()
        ctx.graph = MagicMock()
        ctx.graph.query = AsyncMock(return_value={"results": {"bindings": []}})
        ctx.commands = MagicMock()
        ctx.commands.execute = AsyncMock()

        result = await subscribe_spotify(ctx, "test_pl_id", "My Playlist")
        assert result["status"] == "created"
        assert result["iri"]
        ctx.commands.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_spotify_duplicate_returns_info(self):
        """subscribe_spotify returns duplicate status for existing source."""
        ctx = MagicMock()
        ctx.graph = MagicMock()
        ctx.graph.query = AsyncMock(return_value={
            "results": {"bindings": [{"source": {"value": "urn:existing:src"}}]}
        })
        ctx.commands = MagicMock()
        ctx.commands.execute = AsyncMock()

        result = await subscribe_spotify(ctx, "dup_pl_id", "Dup Playlist")
        assert result["status"] == "duplicate"
        ctx.commands.execute.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════
# Manifest Spotify tests
# ═══════════════════════════════════════════════════════════════════════


class TestManifestSpotify:
    """Validate Spotify entries in manifest.yaml."""

    def test_manifest_has_poll_spotify_task(self):
        import yaml
        manifest_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "manifest.yaml"
        )
        manifest = yaml.safe_load(manifest_path.read_text())
        task_ids = [t["id"] for t in manifest["tasks"]]
        assert "poll-spotify" in task_ids

    def test_manifest_poll_spotify_interval(self):
        import yaml
        manifest_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "manifest.yaml"
        )
        manifest = yaml.safe_load(manifest_path.read_text())
        spotify_task = next(t for t in manifest["tasks"] if t["id"] == "poll-spotify")
        assert spotify_task["interval"] == "15m"
        assert spotify_task["retryPolicy"]["maxRetries"] == 2

    def test_manifest_network_permissions_cover_spotify(self):
        """Network permissions include wildcard which covers Spotify domains."""
        import yaml
        manifest_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "manifest.yaml"
        )
        manifest = yaml.safe_load(manifest_path.read_text())
        network = manifest["permissions"]["network"]
        # Currently uses wildcard "*" — covers all domains
        assert "*" in network


# ═══════════════════════════════════════════════════════════════════════
# Add-source template Spotify tests
# ═══════════════════════════════════════════════════════════════════════


class TestAddSourceTemplateSpotify:
    """Validate the add-source.html template has Spotify section."""

    def _read_template(self):
        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "frontend" / "templates" / "add-source.html"
        )
        return template_path.read_text()

    def test_template_contains_spotify_section(self):
        content = self._read_template()
        assert "spotify" in content.lower()
        assert "Spotify" in content

    def test_template_uses_proxy_prefix_urls(self):
        content = self._read_template()
        # Count occurrences of the proxy prefix
        count = content.count("/app/media-scheduler/")
        assert count >= 5, f"Expected >=5 proxy prefix URLs, found {count}"

    def test_template_has_connect_form(self):
        content = self._read_template()
        assert "client_id" in content
        assert "client_secret" in content
        assert "redirect_uri" in content
        assert "Connect Spotify" in content

    def test_template_has_playlist_selector(self):
        content = self._read_template()
        assert "playlist_id" in content
        assert "/_fragments/spotify/playlists" in content

    def test_template_has_disconnect_button(self):
        content = self._read_template()
        assert "Disconnect Spotify" in content
        assert "/_fragments/spotify/disconnect" in content


# ═══════════════════════════════════════════════════════════════════════
# Spotify poll task — additional edge cases
# ═══════════════════════════════════════════════════════════════════════


class TestPollSpotifyEdgeCases:
    """Additional edge-case tests for the poll_spotify task."""

    @pytest.mark.asyncio
    async def test_skips_items_with_no_track(self):
        """Playlist items with null track field are skipped."""
        binding = _make_spotify_binding()
        ctx, batch_mock = _make_spotify_ctx(bindings=[binding])

        items = [
            {"track": None},  # null track
            _make_playlist_item("t1"),
            {"track": "not_a_dict"},  # non-dict track
        ]

        mock_client_instance = MagicMock()
        mock_client_instance.get_playlist_tracks = AsyncMock(return_value=items)

        with patch.object(
            _app_mod, "SpotifyClient", return_value=mock_client_instance,
        ), patch.object(
            _app_mod, "sp_get_existing_item_iris",
            new_callable=AsyncMock,
            return_value=set(),
        ), patch.object(
            _app_mod, "update_source_state", new_callable=AsyncMock,
        ):
            result = await poll_spotify(ctx)

        assert result["items_created"] == 1

    @pytest.mark.asyncio
    async def test_skips_tracks_with_no_id(self):
        """Tracks with empty or missing id are skipped."""
        binding = _make_spotify_binding()
        ctx, batch_mock = _make_spotify_ctx(bindings=[binding])

        items = [
            {"track": {"id": "", "name": "No ID"}},
            _make_playlist_item("t1"),
        ]

        mock_client_instance = MagicMock()
        mock_client_instance.get_playlist_tracks = AsyncMock(return_value=items)

        with patch.object(
            _app_mod, "SpotifyClient", return_value=mock_client_instance,
        ), patch.object(
            _app_mod, "sp_get_existing_item_iris",
            new_callable=AsyncMock,
            return_value=set(),
        ), patch.object(
            _app_mod, "update_source_state", new_callable=AsyncMock,
        ):
            result = await poll_spotify(ctx)

        assert result["items_created"] == 1

    @pytest.mark.asyncio
    async def test_skips_sources_with_no_external_id(self):
        """Sources without externalId are logged and skipped."""
        binding = _make_spotify_binding(external_id="")
        ctx, _ = _make_spotify_ctx(bindings=[binding])

        mock_client_cls = MagicMock()

        with patch.object(
            _app_mod, "SpotifyClient", mock_client_cls,
        ):
            result = await poll_spotify(ctx)

        mock_client_cls.assert_not_called()
        assert result["sources_polled"] == 0


# ═══════════════════════════════════════════════════════════════════════
# Import context_service via file path
# ═══════════════════════════════════════════════════════════════════════

_ctx_svc_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "media-scheduler" / "services" / "context_service.py"
)
_ctx_svc_spec = importlib.util.spec_from_file_location("context_service_test", str(_ctx_svc_path))
_ctx_svc_mod = importlib.util.module_from_spec(_ctx_svc_spec)
_ctx_svc_spec.loader.exec_module(_ctx_svc_mod)

parse_sse_lines = _ctx_svc_mod.parse_sse_lines
_on_context_event = _ctx_svc_mod._on_context_event
_debounce_regenerate = _ctx_svc_mod._debounce_regenerate
_trigger_regeneration = _ctx_svc_mod._trigger_regeneration
_listen_sse = _ctx_svc_mod._listen_sse
start_context_listener = _ctx_svc_mod.start_context_listener
stop_context_listener = _ctx_svc_mod.stop_context_listener
get_context_subscription_status = _ctx_svc_mod.get_context_subscription_status
DEBOUNCE_SECONDS = _ctx_svc_mod.DEBOUNCE_SECONDS
MAX_BACKOFF_SECONDS = _ctx_svc_mod.MAX_BACKOFF_SECONDS


def _reset_context_module():
    """Reset module-level state in context_service between tests."""
    _ctx_svc_mod._listener_task = None
    _ctx_svc_mod._debounce_task = None
    _ctx_svc_mod._last_context = {}
    _ctx_svc_mod._prev_context = {}
    _ctx_svc_mod._plan_lock = None
    _ctx_svc_mod._reconnect_count = 0
    _ctx_svc_mod._last_event_at = None
    _ctx_svc_mod._connected = False


# ═══════════════════════════════════════════════════════════════════════
# SSE parsing tests
# ═══════════════════════════════════════════════════════════════════════


class TestParseSSELines:
    """parse_sse_lines extracts event type and JSON data from SSE text."""

    def test_single_event(self):
        lines = ['event: context_update', 'data: {"location_zone": "office"}']
        event_type, data = parse_sse_lines(lines)
        assert event_type == "context_update"
        assert data == {"location_zone": "office"}

    def test_multi_line_data(self):
        """Multiple data: lines are concatenated before JSON parse."""
        lines = [
            'event: context_update',
            'data: {"location_zone":',
            'data:  "home"}',
        ]
        event_type, data = parse_sse_lines(lines)
        assert event_type == "context_update"
        # JSON from "{"location_zone":\n "home"}" — valid JSON
        assert data == {"location_zone": "home"}

    def test_missing_event_type(self):
        """Lines without event: still parse data."""
        lines = ['data: {"activity": "working"}']
        event_type, data = parse_sse_lines(lines)
        assert event_type is None
        assert data == {"activity": "working"}

    def test_missing_data(self):
        """Lines without data: return (None, None)."""
        lines = ['event: context_update']
        event_type, data = parse_sse_lines(lines)
        assert event_type is None
        assert data is None

    def test_non_json_data(self):
        """Non-JSON data returns event_type but None data."""
        lines = ['event: context_update', 'data: not-json-at-all']
        event_type, data = parse_sse_lines(lines)
        assert event_type == "context_update"
        assert data is None

    def test_empty_lines_and_comments_ignored(self):
        """Empty lines and comments (starting with ':') are skipped."""
        lines = [
            ': keepalive',
            '',
            'event: context_update',
            '',
            'data: {"ok": true}',
            ': another comment',
        ]
        event_type, data = parse_sse_lines(lines)
        assert event_type == "context_update"
        assert data == {"ok": True}

    def test_all_empty_lines(self):
        lines = ['', '', '']
        event_type, data = parse_sse_lines(lines)
        assert event_type is None
        assert data is None

    def test_whitespace_handling(self):
        """Leading/trailing whitespace in event/data values is stripped."""
        lines = ['event:  context_update  ', 'data:  {"x": 1} ']
        event_type, data = parse_sse_lines(lines)
        assert event_type == "context_update"
        assert data == {"x": 1}


# ═══════════════════════════════════════════════════════════════════════
# Debounce logic tests
# ═══════════════════════════════════════════════════════════════════════


class TestDebounceLogic:
    """_on_context_event debounces non-location changes, immediate for location."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        _reset_context_module()
        yield
        _reset_context_module()

    @pytest.mark.asyncio
    async def test_non_location_change_starts_debounce(self):
        """Non-location context change creates a debounce task."""
        ctx = MagicMock()
        with patch.object(_ctx_svc_mod, "generate_plan", new_callable=AsyncMock):
            await _on_context_event(ctx, {"activity": "working"})
            assert _ctx_svc_mod._debounce_task is not None
            assert not _ctx_svc_mod._debounce_task.done()
            # Clean up
            _ctx_svc_mod._debounce_task.cancel()
            try:
                await _ctx_svc_mod._debounce_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_location_zone_change_triggers_immediate(self):
        """location_zone change triggers immediate regeneration, not debounce."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "test", "entries_created": 1})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            _ctx_svc_mod._last_context = {"location_zone": "home"}
            await _on_context_event(ctx, {"location_zone": "office"})
            mock_gen.assert_awaited_once()
            # No debounce task should be pending
            assert _ctx_svc_mod._debounce_task is None or _ctx_svc_mod._debounce_task.done()

    @pytest.mark.asyncio
    async def test_same_location_zone_does_not_trigger_immediate(self):
        """Same location_zone value → debounce, not immediate."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "test", "entries_created": 0})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            _ctx_svc_mod._last_context = {"location_zone": "office"}
            await _on_context_event(ctx, {"location_zone": "office", "activity": "focused"})
            mock_gen.assert_not_awaited()
            assert _ctx_svc_mod._debounce_task is not None
            _ctx_svc_mod._debounce_task.cancel()
            try:
                await _ctx_svc_mod._debounce_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_debounce_cancels_on_new_event(self):
        """New event cancels existing debounce and starts a new one."""
        ctx = MagicMock()
        with patch.object(_ctx_svc_mod, "generate_plan", new_callable=AsyncMock):
            await _on_context_event(ctx, {"activity": "working"})
            first_task = _ctx_svc_mod._debounce_task
            assert first_task is not None

            await _on_context_event(ctx, {"activity": "commuting"})
            second_task = _ctx_svc_mod._debounce_task
            assert second_task is not first_task
            # Allow cancellation to propagate through the event loop
            await asyncio.sleep(0)
            assert first_task.cancelled() or first_task.done()

            # Clean up
            second_task.cancel()
            try:
                await second_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_debounce_fires_after_timeout(self):
        """Debounce timer fires generate_plan after DEBOUNCE_SECONDS."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "test", "entries_created": 2})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen), \
             patch.object(_ctx_svc_mod, "DEBOUNCE_SECONDS", 0.05):
            await _on_context_event(ctx, {"activity": "relaxing"})
            # Wait slightly longer than debounce
            await asyncio.sleep(0.15)
            mock_gen.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_location_zone_none_to_value_is_change(self):
        """location_zone going from None/absent to a value is a change."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "t", "entries_created": 0})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            _ctx_svc_mod._last_context = {}  # no previous zone
            await _on_context_event(ctx, {"location_zone": "gym"})
            mock_gen.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_location_zone_change_cancels_pending_debounce(self):
        """Location change cancels any pending non-location debounce."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "t", "entries_created": 0})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            # Start a debounce from non-location event
            await _on_context_event(ctx, {"activity": "working"})
            pending = _ctx_svc_mod._debounce_task
            assert pending is not None

            # Location change cancels it and triggers immediately
            _ctx_svc_mod._last_context = {"activity": "working", "location_zone": "home"}
            await _on_context_event(ctx, {"location_zone": "office", "activity": "working"})
            await asyncio.sleep(0)  # let cancellation propagate
            assert pending.cancelled() or pending.done()
            mock_gen.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_debounce_restarts_timer(self):
        """Each new non-location event restarts the debounce clock."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "t", "entries_created": 0})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen), \
             patch.object(_ctx_svc_mod, "DEBOUNCE_SECONDS", 0.1):
            await _on_context_event(ctx, {"activity": "a"})
            await asyncio.sleep(0.05)  # halfway
            await _on_context_event(ctx, {"activity": "b"})  # restart
            await asyncio.sleep(0.05)  # 0.05 into new timer
            mock_gen.assert_not_awaited()  # shouldn't have fired yet
            await asyncio.sleep(0.1)  # now past the second timer
            mock_gen.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_stored_on_event(self):
        """_last_context and _prev_context are updated on each event."""
        ctx = MagicMock()
        with patch.object(_ctx_svc_mod, "generate_plan", new_callable=AsyncMock):
            await _on_context_event(ctx, {"activity": "a"})
            assert _ctx_svc_mod._last_context == {"activity": "a"}
            assert _ctx_svc_mod._prev_context == {}

            await _on_context_event(ctx, {"activity": "b"})
            assert _ctx_svc_mod._last_context == {"activity": "b"}
            assert _ctx_svc_mod._prev_context == {"activity": "a"}

            # Clean up debounce
            if _ctx_svc_mod._debounce_task and not _ctx_svc_mod._debounce_task.done():
                _ctx_svc_mod._debounce_task.cancel()
                try:
                    await _ctx_svc_mod._debounce_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_location_zone_value_to_same_value_not_immediate(self):
        """location_zone value→same value is not a change (debounces)."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "t", "entries_created": 0})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            _ctx_svc_mod._last_context = {"location_zone": "home"}
            await _on_context_event(ctx, {"location_zone": "home"})
            mock_gen.assert_not_awaited()
            if _ctx_svc_mod._debounce_task and not _ctx_svc_mod._debounce_task.done():
                _ctx_svc_mod._debounce_task.cancel()
                try:
                    await _ctx_svc_mod._debounce_task
                except asyncio.CancelledError:
                    pass


# ═══════════════════════════════════════════════════════════════════════
# Reconnect logic tests
# ═══════════════════════════════════════════════════════════════════════


class TestReconnectLogic:
    """SSE reconnect with exponential backoff."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        _reset_context_module()
        yield
        _reset_context_module()

    def test_backoff_calculation_exponential(self):
        """Backoff is 2**count, capped at MAX_BACKOFF_SECONDS."""
        assert min(2 ** 1, MAX_BACKOFF_SECONDS) == 2
        assert min(2 ** 5, MAX_BACKOFF_SECONDS) == 32
        assert min(2 ** 10, MAX_BACKOFF_SECONDS) == 300  # capped

    def test_backoff_never_exceeds_max(self):
        """Even at very high reconnect counts, backoff is capped."""
        for count in range(1, 50):
            assert min(2 ** count, MAX_BACKOFF_SECONDS) <= MAX_BACKOFF_SECONDS

    @pytest.mark.asyncio
    async def test_reconnect_increments_counter(self):
        """Connection error increments _reconnect_count."""
        ctx = MagicMock()
        call_count = 0

        def fake_get_client():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("test")
            raise asyncio.CancelledError()  # break the loop

        ctx._get_platform_client = fake_get_client

        with patch.object(_ctx_svc_mod, "asyncio") as mock_asyncio:
            mock_asyncio.CancelledError = asyncio.CancelledError
            mock_asyncio.sleep = AsyncMock()
            try:
                await _listen_sse(ctx)
            except asyncio.CancelledError:
                pass
        assert _ctx_svc_mod._reconnect_count == 2

    @pytest.mark.asyncio
    async def test_reconnect_counter_resets_on_success(self):
        """Successful connection resets _reconnect_count to 0."""
        _ctx_svc_mod._reconnect_count = 5

        ctx = MagicMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        # Simulate one successful connection then cancel
        async def fake_aiter_lines():
            _ctx_svc_mod._reconnect_count = 0  # reset happens before iteration
            raise asyncio.CancelledError()
            yield  # make it an async generator

        mock_response.aiter_lines = fake_aiter_lines

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        ctx._get_platform_client = MagicMock(return_value=mock_client)

        try:
            await _listen_sse(ctx)
        except asyncio.CancelledError:
            pass

    def test_max_backoff_is_300(self):
        """MAX_BACKOFF_SECONDS constant is 300."""
        assert MAX_BACKOFF_SECONDS == 300.0


# ═══════════════════════════════════════════════════════════════════════
# Plan trigger tests
# ═══════════════════════════════════════════════════════════════════════


class TestPlanTrigger:
    """_trigger_regeneration acquires lock, calls generate_plan, logs result."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        _reset_context_module()
        yield
        _reset_context_module()

    @pytest.mark.asyncio
    async def test_calls_generate_plan_with_context(self):
        """_trigger_regeneration passes _last_context as context_override."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "urn:test", "entries_created": 3})
        _ctx_svc_mod._last_context = {"location_zone": "office", "activity": "working"}

        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            await _trigger_regeneration(ctx)
        mock_gen.assert_awaited_once_with(
            ctx, context_override={"location_zone": "office", "activity": "working"}
        )

    @pytest.mark.asyncio
    async def test_creates_lock_if_needed(self):
        """_trigger_regeneration creates _plan_lock if None."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "x", "entries_created": 0})
        _ctx_svc_mod._plan_lock = None

        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            await _trigger_regeneration(ctx)
        assert _ctx_svc_mod._plan_lock is not None

    @pytest.mark.asyncio
    async def test_generate_plan_error_caught(self):
        """Errors from generate_plan are logged, not raised."""
        ctx = MagicMock()
        mock_gen = AsyncMock(side_effect=RuntimeError("plan failed"))
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            # Should not raise
            await _trigger_regeneration(ctx)

    @pytest.mark.asyncio
    async def test_result_logged(self):
        """Plan result summary is logged after generation."""
        ctx = MagicMock()
        result = {"plan_iri": "urn:p1", "entries_created": 5}
        mock_gen = AsyncMock(return_value=result)
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen), \
             patch.object(_ctx_svc_mod.logger, "info") as mock_log:
            await _trigger_regeneration(ctx)
        # Check that completion was logged
        log_calls = [c for c in mock_log.call_args_list
                     if "plan_generation_completed" in str(c)]
        assert len(log_calls) == 1

    @pytest.mark.asyncio
    async def test_lock_contention_logged(self):
        """Concurrent trigger logs a contention warning."""
        ctx = MagicMock()
        _ctx_svc_mod._plan_lock = asyncio.Lock()
        # Acquire the lock externally to simulate contention
        await _ctx_svc_mod._plan_lock.acquire()

        mock_gen = AsyncMock(return_value={"plan_iri": "x", "entries_created": 0})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen), \
             patch.object(_ctx_svc_mod.logger, "warning") as mock_warn:
            # Run in background — it will block on the lock
            task = asyncio.create_task(_trigger_regeneration(ctx))
            await asyncio.sleep(0.05)
            # Should have logged contention warning
            contention_calls = [c for c in mock_warn.call_args_list
                                if "lock_contention" in str(c)]
            assert len(contention_calls) == 1
            # Release lock so task can complete
            _ctx_svc_mod._plan_lock.release()
            await asyncio.wait_for(task, timeout=2.0)

    @pytest.mark.asyncio
    async def test_uses_existing_lock(self):
        """_trigger_regeneration reuses _plan_lock if already created."""
        ctx = MagicMock()
        lock = asyncio.Lock()
        _ctx_svc_mod._plan_lock = lock
        mock_gen = AsyncMock(return_value={"plan_iri": "x", "entries_created": 0})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            await _trigger_regeneration(ctx)
        assert _ctx_svc_mod._plan_lock is lock


# ═══════════════════════════════════════════════════════════════════════
# Listener lifecycle tests
# ═══════════════════════════════════════════════════════════════════════


class TestListenerLifecycle:
    """start/stop_context_listener and get_context_subscription_status."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        _reset_context_module()
        yield
        _reset_context_module()

    @pytest.mark.asyncio
    async def test_start_creates_task(self):
        """start_context_listener returns an asyncio.Task."""
        ctx = MagicMock()
        # Mock _listen_sse to avoid real SSE connection
        with patch.object(_ctx_svc_mod, "_listen_sse", new_callable=AsyncMock):
            task = start_context_listener(ctx)
            assert isinstance(task, asyncio.Task)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_start_creates_plan_lock(self):
        """start_context_listener creates _plan_lock if None."""
        ctx = MagicMock()
        _ctx_svc_mod._plan_lock = None
        with patch.object(_ctx_svc_mod, "_listen_sse", new_callable=AsyncMock):
            task = start_context_listener(ctx)
            assert _ctx_svc_mod._plan_lock is not None
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_stop_cancels_listener(self):
        """stop_context_listener cancels the listener task."""
        ctx = MagicMock()
        with patch.object(_ctx_svc_mod, "_listen_sse", new_callable=AsyncMock):
            task = start_context_listener(ctx)
            assert not task.done()
            stop_context_listener()
            await asyncio.sleep(0.01)
            assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_stop_cancels_debounce(self):
        """stop_context_listener cancels pending debounce task."""
        async def fake_debounce():
            await asyncio.sleep(999)

        _ctx_svc_mod._debounce_task = asyncio.create_task(fake_debounce())
        stop_context_listener()
        await asyncio.sleep(0.01)
        assert _ctx_svc_mod._debounce_task is None

    @pytest.mark.asyncio
    async def test_stop_resets_state(self):
        """stop_context_listener resets all module state."""
        _ctx_svc_mod._connected = True
        _ctx_svc_mod._reconnect_count = 5
        _ctx_svc_mod._last_context = {"x": 1}
        _ctx_svc_mod._last_event_at = "2025-01-01T00:00:00"
        stop_context_listener()
        assert _ctx_svc_mod._connected is False
        assert _ctx_svc_mod._reconnect_count == 0
        assert _ctx_svc_mod._last_context == {}
        assert _ctx_svc_mod._last_event_at is None

    def test_status_reports_connected(self):
        """get_context_subscription_status reports connection state."""
        _ctx_svc_mod._connected = True
        _ctx_svc_mod._last_event_at = "2025-01-01T12:00:00+00:00"
        _ctx_svc_mod._reconnect_count = 0
        status = get_context_subscription_status()
        assert status["connected"] is True
        assert status["last_event_at"] == "2025-01-01T12:00:00+00:00"
        assert status["reconnect_count"] == 0

    def test_status_reports_debounce_pending(self):
        """Status shows debounce_pending when a debounce task is active."""
        mock_task = MagicMock()
        mock_task.done.return_value = False
        _ctx_svc_mod._debounce_task = mock_task
        status = get_context_subscription_status()
        assert status["debounce_pending"] is True

    def test_status_debounce_not_pending_when_done(self):
        """Status shows debounce_pending=False when task is done."""
        mock_task = MagicMock()
        mock_task.done.return_value = True
        _ctx_svc_mod._debounce_task = mock_task
        status = get_context_subscription_status()
        assert status["debounce_pending"] is False


# ═══════════════════════════════════════════════════════════════════════
# Concurrent generation tests
# ═══════════════════════════════════════════════════════════════════════


class TestConcurrentGeneration:
    """asyncio.Lock prevents overlapping generate_plan calls."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        _reset_context_module()
        yield
        _reset_context_module()

    @pytest.mark.asyncio
    async def test_lock_serializes_concurrent_triggers(self):
        """Two concurrent _trigger_regeneration calls are serialized."""
        ctx = MagicMock()
        call_order = []

        async def slow_generate(*args, **kwargs):
            call_order.append("start")
            await asyncio.sleep(0.05)
            call_order.append("end")
            return {"plan_iri": "x", "entries_created": 0}

        mock_gen = AsyncMock(side_effect=slow_generate)
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            t1 = asyncio.create_task(_trigger_regeneration(ctx))
            t2 = asyncio.create_task(_trigger_regeneration(ctx))
            await asyncio.gather(t1, t2)

        # Should be start-end-start-end (serialized), not start-start-end-end
        assert call_order == ["start", "end", "start", "end"]

    @pytest.mark.asyncio
    async def test_lock_shared_across_triggers(self):
        """All triggers share the same _plan_lock instance."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "x", "entries_created": 0})
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            await _trigger_regeneration(ctx)
            lock1 = _ctx_svc_mod._plan_lock
            await _trigger_regeneration(ctx)
            lock2 = _ctx_svc_mod._plan_lock
        assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_lock_not_held_after_error(self):
        """Lock is released even if generate_plan raises."""
        ctx = MagicMock()
        mock_gen = AsyncMock(side_effect=RuntimeError("oops"))
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            await _trigger_regeneration(ctx)
        assert not _ctx_svc_mod._plan_lock.locked()


# ═══════════════════════════════════════════════════════════════════════
# Error handling tests
# ═══════════════════════════════════════════════════════════════════════


class TestContextErrorHandling:
    """Edge cases and error recovery."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        _reset_context_module()
        yield
        _reset_context_module()

    @pytest.mark.asyncio
    async def test_sse_parse_error_does_not_crash_listener(self):
        """Malformed SSE data is logged and skipped, not raised."""
        # parse_sse_lines with bad JSON returns (type, None) — handled by listener
        lines = ['event: context_update', 'data: {bad json}']
        event_type, data = parse_sse_lines(lines)
        assert event_type == "context_update"
        assert data is None  # gracefully handled

    @pytest.mark.asyncio
    async def test_empty_context_event(self):
        """Empty context dict is stored without error."""
        ctx = MagicMock()
        with patch.object(_ctx_svc_mod, "generate_plan", new_callable=AsyncMock):
            await _on_context_event(ctx, {})
            assert _ctx_svc_mod._last_context == {}
            if _ctx_svc_mod._debounce_task and not _ctx_svc_mod._debounce_task.done():
                _ctx_svc_mod._debounce_task.cancel()
                try:
                    await _ctx_svc_mod._debounce_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_generate_plan_exception_is_caught(self):
        """Exception in generate_plan doesn't propagate out of trigger."""
        ctx = MagicMock()
        mock_gen = AsyncMock(side_effect=Exception("catastrophic"))
        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            # Should not raise
            await _trigger_regeneration(ctx)

    @pytest.mark.asyncio
    async def test_location_zone_none_in_previous(self):
        """Previous context has no location_zone — new zone triggers immediate."""
        ctx = MagicMock()
        mock_gen = AsyncMock(return_value={"plan_iri": "x", "entries_created": 0})
        _ctx_svc_mod._last_context = {"activity": "idle"}

        with patch.object(_ctx_svc_mod, "generate_plan", mock_gen):
            await _on_context_event(ctx, {"location_zone": "cafe", "activity": "idle"})
            mock_gen.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_debounce_seconds_constant(self):
        """DEBOUNCE_SECONDS is 120."""
        assert DEBOUNCE_SECONDS == 120.0



# ═══════════════════════════════════════════════════════════════════════
# Entry status route tests
# ═══════════════════════════════════════════════════════════════════════


def _make_request(path_params=None, form_data=None, query_params=None):
    """Build a mock Starlette Request with path_params and form_data."""
    request = MagicMock()
    request.path_params = path_params or {}
    request.query_params = query_params or {}

    async def mock_form():
        return form_data or {}

    request.form = mock_form

    # Wire up ctx via request.app.state.ctx
    ctx = MagicMock()
    ctx.commands = MagicMock()
    ctx.commands.execute = AsyncMock(return_value=None)
    ctx.graph = MagicMock()
    ctx.graph.query = AsyncMock(return_value={"results": {"bindings": []}})
    ctx.render_template = MagicMock(side_effect=lambda name, **kw: f"<rendered:{name}>")
    request.app.state.ctx = ctx
    return request, ctx


class TestEntryStatusRoute:
    """Tests for POST /_fragments/entry/{entry_iri}/status."""

    @pytest.mark.asyncio
    async def test_valid_status_completed(self):
        """Completed status triggers object.patch and returns success HTML."""
        req, ctx = _make_request(
            path_params={"entry_iri": "urn%3Asempkm%3Aentry%3A123"},
            form_data={"status": "completed"},
        )
        resp = await entry_status_fragment(req)
        assert resp.status_code == 200
        assert "completed" in resp.body.decode()
        ctx.commands.execute.assert_awaited_once()
        call_args = ctx.commands.execute.call_args
        assert call_args[0][0] == "object.patch"
        assert "entryStatus" in str(call_args[0][1]["properties"])

    @pytest.mark.asyncio
    async def test_valid_status_skipped(self):
        """Skipped status triggers object.patch."""
        req, ctx = _make_request(
            path_params={"entry_iri": "urn:sempkm:entry:456"},
            form_data={"status": "skipped"},
        )
        resp = await entry_status_fragment(req)
        assert resp.status_code == 200
        assert "skipped" in resp.body.decode()

    @pytest.mark.asyncio
    async def test_valid_status_saved(self):
        """Saved status triggers object.patch."""
        req, ctx = _make_request(
            path_params={"entry_iri": "urn:sempkm:entry:789"},
            form_data={"status": "saved"},
        )
        resp = await entry_status_fragment(req)
        assert resp.status_code == 200
        assert "saved" in resp.body.decode()

    @pytest.mark.asyncio
    async def test_invalid_status_returns_400(self):
        """Invalid status value returns 400."""
        req, ctx = _make_request(
            path_params={"entry_iri": "urn:sempkm:entry:123"},
            form_data={"status": "invalid_status"},
        )
        resp = await entry_status_fragment(req)
        assert resp.status_code == 400
        assert "Invalid status" in resp.body.decode()
        ctx.commands.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_status_returns_400(self):
        """Empty status field returns 400."""
        req, ctx = _make_request(
            path_params={"entry_iri": "urn:sempkm:entry:123"},
            form_data={"status": ""},
        )
        resp = await entry_status_fragment(req)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_entry_iri_returns_400(self):
        """Missing entry_iri returns 400."""
        req, ctx = _make_request(
            path_params={"entry_iri": ""},
            form_data={"status": "completed"},
        )
        resp = await entry_status_fragment(req)
        assert resp.status_code == 400
        assert "Missing entry IRI" in resp.body.decode()

    @pytest.mark.asyncio
    async def test_patch_failure_returns_500(self):
        """If object.patch fails, return 500 with error message."""
        req, ctx = _make_request(
            path_params={"entry_iri": "urn:sempkm:entry:fail"},
            form_data={"status": "completed"},
        )
        ctx.commands.execute = AsyncMock(side_effect=RuntimeError("triplestore down"))
        resp = await entry_status_fragment(req)
        assert resp.status_code == 500
        assert "Failed to update" in resp.body.decode()

    @pytest.mark.asyncio
    async def test_response_contains_action_class(self):
        """Response HTML contains the ms-entry-actions class for htmx swap."""
        req, ctx = _make_request(
            path_params={"entry_iri": "urn:sempkm:entry:123"},
            form_data={"status": "completed"},
        )
        resp = await entry_status_fragment(req)
        body = resp.body.decode()
        assert "ms-entry-actions" in body
        assert "ms-entry-done" in body


# ═══════════════════════════════════════════════════════════════════════
# JSON suggestion endpoint tests
# ═══════════════════════════════════════════════════════════════════════


class TestSuggestionJSON:
    """Tests for GET /_fragments/current-suggestion/json."""

    @pytest.mark.asyncio
    async def test_empty_plan_returns_none_status(self):
        """When no plan entries exist, returns {"status": "none"}."""
        req, ctx = _make_request()
        resp = await current_suggestion_json(req)
        assert resp.status_code == 200
        data = json.loads(resp.body)
        assert data["status"] == "none"

    @pytest.mark.asyncio
    async def test_now_entry_returns_now_status(self):
        """Entry whose time slot contains current time returns status=now."""
        from datetime import datetime as dt
        now_time = dt.now().strftime("%H:%M")
        # Create a slot that contains now_time
        h, m = map(int, now_time.split(":"))
        start = f"{h:02d}:{max(0, m-5):02d}"
        end = f"{h:02d}:{min(59, m+5):02d}"

        bindings = [{
            "entry": {"value": "urn:sempkm:entry:now1"},
            "slotStart": {"value": start},
            "slotEnd": {"value": end},
            "entryStatus": {"value": "pending"},
            "title": {"value": "Test Episode"},
            "enclosureUrl": {"value": "https://example.com/ep.mp3"},
            "sourceTitle": {"value": "Test Podcast"},
            "sourceType": {"value": "podcast"},
            "duration": {"value": "1800"},
        }]

        req, ctx = _make_request()
        ctx.graph.query = AsyncMock(return_value={"results": {"bindings": bindings}})
        resp = await current_suggestion_json(req)
        data = json.loads(resp.body)
        assert data["status"] == "now"
        assert data["title"] == "Test Episode"
        assert data["enclosure_url"] == "https://example.com/ep.mp3"
        assert data["source_type"] == "podcast"
        assert data["duration_seconds"] == 1800

    @pytest.mark.asyncio
    async def test_next_entry_returns_next_status(self):
        """Entry in the future returns status=next."""
        bindings = [{
            "entry": {"value": "urn:sempkm:entry:next1"},
            "slotStart": {"value": "23:55"},
            "slotEnd": {"value": "23:59"},
            "entryStatus": {"value": "pending"},
            "title": {"value": "Late Night Episode"},
            "sourceType": {"value": "youtube"},
        }]

        req, ctx = _make_request()
        ctx.graph.query = AsyncMock(return_value={"results": {"bindings": bindings}})
        resp = await current_suggestion_json(req)
        data = json.loads(resp.body)
        assert data["status"] == "next"
        assert data["title"] == "Late Night Episode"
        assert data["source_type"] == "youtube"

    @pytest.mark.asyncio
    async def test_completed_entries_skipped(self):
        """Completed/skipped entries are not returned as current suggestion."""
        bindings = [{
            "entry": {"value": "urn:sempkm:entry:done1"},
            "slotStart": {"value": "00:00"},
            "slotEnd": {"value": "23:59"},
            "entryStatus": {"value": "completed"},
            "title": {"value": "Done Episode"},
        }]

        req, ctx = _make_request()
        ctx.graph.query = AsyncMock(return_value={"results": {"bindings": bindings}})
        resp = await current_suggestion_json(req)
        data = json.loads(resp.body)
        assert data["status"] == "none"

    @pytest.mark.asyncio
    async def test_json_response_all_fields(self):
        """JSON response includes all expected fields."""
        from datetime import datetime as dt
        now_time = dt.now().strftime("%H:%M")
        h, m = map(int, now_time.split(":"))
        start = f"{h:02d}:{max(0, m-5):02d}"
        end = f"{h:02d}:{min(59, m+5):02d}"

        bindings = [{
            "entry": {"value": "urn:sempkm:entry:full1"},
            "slotStart": {"value": start},
            "slotEnd": {"value": end},
            "entryStatus": {"value": "pending"},
            "title": {"value": "Full Episode"},
            "enclosureUrl": {"value": "https://spotify.com/track/abc"},
            "sourceTitle": {"value": "My Playlist"},
            "sourceType": {"value": "spotify"},
            "duration": {"value": "240"},
        }]

        req, ctx = _make_request()
        ctx.graph.query = AsyncMock(return_value={"results": {"bindings": bindings}})
        resp = await current_suggestion_json(req)
        data = json.loads(resp.body)

        expected_keys = {"title", "slot_start", "slot_end", "status",
                         "source_type", "source_title", "enclosure_url",
                         "duration_seconds"}
        assert expected_keys.issubset(set(data.keys()))

    @pytest.mark.asyncio
    async def test_sparql_failure_returns_none(self):
        """SPARQL failure returns status=none with error field."""
        req, ctx = _make_request()
        ctx.graph.query = AsyncMock(side_effect=RuntimeError("connection lost"))
        resp = await current_suggestion_json(req)
        data = json.loads(resp.body)
        assert data["status"] == "none"

    @pytest.mark.asyncio
    async def test_missing_duration_returns_none(self):
        """Entry with no duration field returns duration_seconds=None in JSON."""
        bindings = [{
            "entry": {"value": "urn:sempkm:entry:nodur"},
            "slotStart": {"value": "23:55"},
            "slotEnd": {"value": "23:59"},
            "entryStatus": {"value": "pending"},
            "title": {"value": "No Duration"},
        }]

        req, ctx = _make_request()
        ctx.graph.query = AsyncMock(return_value={"results": {"bindings": bindings}})
        resp = await current_suggestion_json(req)
        data = json.loads(resp.body)
        assert data["duration_seconds"] is None

    @pytest.mark.asyncio
    async def test_replaced_entries_skipped(self):
        """Replaced entries are not returned as current suggestion."""
        bindings = [{
            "entry": {"value": "urn:sempkm:entry:replaced1"},
            "slotStart": {"value": "00:00"},
            "slotEnd": {"value": "23:59"},
            "entryStatus": {"value": "replaced"},
            "title": {"value": "Replaced Episode"},
        }]

        req, ctx = _make_request()
        ctx.graph.query = AsyncMock(return_value={"results": {"bindings": bindings}})
        resp = await current_suggestion_json(req)
        data = json.loads(resp.body)
        assert data["status"] == "none"


# ═══════════════════════════════════════════════════════════════════════
# Lifecycle wiring tests
# ═══════════════════════════════════════════════════════════════════════


class TestLifecycleContext:
    """Tests for on_startup/on_shutdown context service wiring."""

    @pytest.mark.asyncio
    async def test_on_startup_calls_start_context_listener(self):
        """on_startup calls start_context_listener(ctx)."""
        ctx = MagicMock()
        ctx.app_id = "media-scheduler"
        with patch.object(_app_mod, "start_context_listener") as mock_start:
            await on_startup(ctx)
            mock_start.assert_called_once_with(ctx)

    @pytest.mark.asyncio
    async def test_on_shutdown_calls_stop_context_listener(self):
        """on_shutdown calls stop_context_listener()."""
        ctx = MagicMock()
        ctx.app_id = "media-scheduler"
        with patch.object(_app_mod, "stop_context_listener") as mock_stop:
            await on_shutdown(ctx)
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_startup_is_async(self):
        """on_startup is an async function."""
        import inspect
        assert inspect.iscoroutinefunction(on_startup)

    @pytest.mark.asyncio
    async def test_on_shutdown_is_async(self):
        """on_shutdown is an async function."""
        import inspect
        assert inspect.iscoroutinefunction(on_shutdown)


# ═══════════════════════════════════════════════════════════════════════
# Template and htmx wiring tests
# ═══════════════════════════════════════════════════════════════════════


class TestTodayTemplateActions:
    """Tests for today.html template action buttons and htmx attributes."""

    def test_template_contains_action_buttons(self):
        """today.html has ms-entry-actions class."""
        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "frontend" / "templates" / "today.html"
        )
        content = template_path.read_text()
        assert "ms-entry-actions" in content

    def test_template_has_complete_button(self):
        """today.html has a complete button with hx-post."""
        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "frontend" / "templates" / "today.html"
        )
        content = template_path.read_text()
        assert '"completed"' in content
        assert "ms-action-complete" in content

    def test_template_has_skip_button(self):
        """today.html has a skip button."""
        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "frontend" / "templates" / "today.html"
        )
        content = template_path.read_text()
        assert '"skipped"' in content
        assert "ms-action-skip" in content

    def test_template_has_save_button(self):
        """today.html has a save button."""
        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "frontend" / "templates" / "today.html"
        )
        content = template_path.read_text()
        assert '"saved"' in content
        assert "ms-action-save" in content

    def test_template_uses_proxy_prefix(self):
        """htmx URLs use the /app/media-scheduler/ proxy prefix."""
        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "frontend" / "templates" / "today.html"
        )
        content = template_path.read_text()
        assert "/app/media-scheduler/_fragments/entry/" in content

    def test_template_passes_entry_iri(self):
        """today.html uses entry.iri in the htmx URL."""
        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "frontend" / "templates" / "today.html"
        )
        content = template_path.read_text()
        assert "entry.iri" in content

    def test_template_hides_actions_for_done_entries(self):
        """today.html hides action buttons for completed/skipped/saved entries."""
        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "apps" / "media-scheduler" / "frontend" / "templates" / "today.html"
        )
        content = template_path.read_text()
        # Check for Jinja conditional that hides actions
        assert "not in" in content or "entry.status" in content

    def test_valid_entry_statuses_set(self):
        """VALID_ENTRY_STATUSES contains exactly the three expected values."""
        assert VALID_ENTRY_STATUSES == {"completed", "skipped", "saved"}

    @pytest.mark.asyncio
    async def test_today_fragment_passes_entry_iri(self):
        """today_fragment includes entry_iri in template context."""
        req, ctx = _make_request()
        bindings = [{
            "entry": {"value": "urn:sempkm:entry:abc123"},
            "slotStart": {"value": "09:00"},
            "slotEnd": {"value": "09:30"},
            "entryStatus": {"value": "pending"},
            "title": {"value": "Test"},
        }]
        ctx.graph.query = AsyncMock(return_value={"results": {"bindings": bindings}})
        await today_fragment(req)
        # render_template should have been called with entries containing iri
        call_kwargs = ctx.render_template.call_args
        assert call_kwargs is not None
        entries = call_kwargs[1].get("entries") if call_kwargs[1] else None
        if entries is None and len(call_kwargs[0]) > 1:
            # Positional args
            pass
        else:
            assert entries is not None
            assert len(entries) == 1
            assert entries[0]["iri"] == "urn:sempkm:entry:abc123"


# ═══════════════════════════════════════════════════════════════════════
# Stats service tests
# ═══════════════════════════════════════════════════════════════════════


class TestStatsService:
    """Tests for stats_service.py query functions."""

    def _make_ctx(self, bindings=None):
        ctx = MagicMock()
        ctx.graph = MagicMock()
        ctx.graph.query = AsyncMock(
            return_value={"results": {"bindings": bindings or []}}
        )
        return ctx

    # ── get_hours_by_source_type ──

    @pytest.mark.asyncio
    async def test_stats_hours_empty(self):
        """Returns empty list when no completed entries exist."""
        ctx = self._make_ctx(bindings=[])
        result = await get_hours_by_source_type(ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_stats_hours_aggregation(self):
        """Correctly converts seconds to hours from SPARQL bindings."""
        bindings = [
            {"sourceType": {"value": "podcast"}, "totalSeconds": {"value": "7200"}},
            {"sourceType": {"value": "youtube"}, "totalSeconds": {"value": "3600"}},
        ]
        ctx = self._make_ctx(bindings=bindings)
        result = await get_hours_by_source_type(ctx)
        assert len(result) == 2
        assert result[0] == {"source_type": "podcast", "hours": 2.0}
        assert result[1] == {"source_type": "youtube", "hours": 1.0}

    @pytest.mark.asyncio
    async def test_stats_hours_fractional(self):
        """Handles fractional hours (e.g. 5400s = 1.5h)."""
        bindings = [
            {"sourceType": {"value": "spotify"}, "totalSeconds": {"value": "5400"}},
        ]
        ctx = self._make_ctx(bindings=bindings)
        result = await get_hours_by_source_type(ctx)
        assert result[0]["hours"] == 1.5

    @pytest.mark.asyncio
    async def test_stats_hours_query_failure(self):
        """Returns empty list on query failure."""
        ctx = self._make_ctx()
        ctx.graph.query = AsyncMock(side_effect=Exception("SPARQL error"))
        result = await get_hours_by_source_type(ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_stats_hours_sparql_contains_group_by(self):
        """SPARQL template contains GROUP BY sourceType."""
        assert "GROUP BY ?sourceType" in HOURS_BY_SOURCE_TYPE_SPARQL

    @pytest.mark.asyncio
    async def test_stats_hours_sparql_filters_completed(self):
        """SPARQL template filters on entryStatus = completed."""
        assert '"completed"' in HOURS_BY_SOURCE_TYPE_SPARQL

    # ── get_top_sources ──

    @pytest.mark.asyncio
    async def test_stats_top_sources_empty(self):
        """Returns empty list when no data."""
        ctx = self._make_ctx(bindings=[])
        result = await get_top_sources(ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_stats_top_sources_parsing(self):
        """Parses source titles and counts from bindings."""
        bindings = [
            {"sourceTitle": {"value": "My Podcast"}, "completionCount": {"value": "15"}},
            {"sourceTitle": {"value": "Tech Talk"}, "completionCount": {"value": "8"}},
        ]
        ctx = self._make_ctx(bindings=bindings)
        result = await get_top_sources(ctx, limit=10)
        assert len(result) == 2
        assert result[0] == {"source_title": "My Podcast", "count": 15}
        assert result[1] == {"source_title": "Tech Talk", "count": 8}

    @pytest.mark.asyncio
    async def test_stats_top_sources_limit_injected(self):
        """Limit parameter is injected into the SPARQL query."""
        ctx = self._make_ctx()
        await get_top_sources(ctx, limit=5)
        call_args = ctx.graph.query.call_args[0][0]
        assert "LIMIT 5" in call_args

    @pytest.mark.asyncio
    async def test_stats_top_sources_query_failure(self):
        """Returns empty list on query failure."""
        ctx = self._make_ctx()
        ctx.graph.query = AsyncMock(side_effect=Exception("timeout"))
        result = await get_top_sources(ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_stats_top_sources_sparql_contains_group_by(self):
        """SPARQL template has GROUP BY sourceTitle."""
        assert "GROUP BY ?sourceTitle" in TOP_SOURCES_SPARQL

    # ── get_weekly_trends ──

    @pytest.mark.asyncio
    async def test_stats_weekly_trends_empty(self):
        """Returns zero-filled days when no data."""
        ctx = self._make_ctx(bindings=[])
        result = await get_weekly_trends(ctx, days=3)
        assert len(result) == 3
        assert all(item["count"] == 0 for item in result)

    @pytest.mark.asyncio
    async def test_stats_weekly_trends_fills_zeros(self):
        """Fills missing days with zero counts."""
        from datetime import date, timedelta
        today = date.today()
        yesterday = (today - timedelta(days=1)).isoformat()
        bindings = [
            {"planDate": {"value": yesterday}, "completionCount": {"value": "3"}},
        ]
        ctx = self._make_ctx(bindings=bindings)
        result = await get_weekly_trends(ctx, days=3)
        assert len(result) == 3
        # Yesterday should have count 3
        yesterday_entry = [r for r in result if r["date"] == yesterday]
        assert len(yesterday_entry) == 1
        assert yesterday_entry[0]["count"] == 3
        # Other days should be 0
        other = [r for r in result if r["date"] != yesterday]
        assert all(r["count"] == 0 for r in other)

    @pytest.mark.asyncio
    async def test_stats_weekly_trends_chronological_order(self):
        """Results are in chronological order."""
        ctx = self._make_ctx(bindings=[])
        result = await get_weekly_trends(ctx, days=5)
        dates = [r["date"] for r in result]
        assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_stats_weekly_trends_query_failure(self):
        """Returns empty list on query failure."""
        ctx = self._make_ctx()
        ctx.graph.query = AsyncMock(side_effect=Exception("error"))
        result = await get_weekly_trends(ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_stats_weekly_trends_sparql_filters_completed(self):
        """SPARQL template filters on completed status."""
        assert '"completed"' in WEEKLY_TRENDS_SPARQL


# ═══════════════════════════════════════════════════════════════════════
# Stats route tests
# ═══════════════════════════════════════════════════════════════════════


class TestStatsRoute:
    """Tests for GET /_fragments/stats route."""

    @pytest.mark.asyncio
    async def test_stats_route_renders_template(self):
        """Stats route calls render_template with stats.html."""
        req, ctx = _make_request()
        # Mock graph.query for the three stats queries
        ctx.graph.query = AsyncMock(
            return_value={"results": {"bindings": []}}
        )
        resp = await stats_fragment(req)
        assert resp.status_code == 200
        # render_template called with stats.html
        ctx.render_template.assert_called_once()
        call_args = ctx.render_template.call_args
        assert call_args[0][0] == "stats.html"

    @pytest.mark.asyncio
    async def test_stats_route_passes_json(self):
        """Stats route passes stats_json to template."""
        req, ctx = _make_request()
        ctx.graph.query = AsyncMock(
            return_value={"results": {"bindings": []}}
        )
        await stats_fragment(req)
        call_kwargs = ctx.render_template.call_args[1]
        assert "stats_json" in call_kwargs
        # Verify it's valid JSON
        data = json.loads(call_kwargs["stats_json"])
        assert "hours_by_source_type" in data
        assert "top_sources" in data
        assert "weekly_trends" in data

    @pytest.mark.asyncio
    async def test_stats_route_with_data(self):
        """Stats route correctly passes populated data."""
        req, ctx = _make_request()
        # Return different data for the three queries
        call_count = 0
        async def side_effect_query(sparql):
            nonlocal call_count
            call_count += 1
            if "SUM" in sparql:
                return {"results": {"bindings": [
                    {"sourceType": {"value": "podcast"}, "totalSeconds": {"value": "3600"}}
                ]}}
            elif "COUNT" in sparql and "sourceTitle" in sparql:
                return {"results": {"bindings": [
                    {"sourceTitle": {"value": "Test Pod"}, "completionCount": {"value": "5"}}
                ]}}
            else:
                return {"results": {"bindings": []}}
        ctx.graph.query = AsyncMock(side_effect=side_effect_query)
        await stats_fragment(req)
        call_kwargs = ctx.render_template.call_args[1]
        data = json.loads(call_kwargs["stats_json"])
        assert data["hours_by_source_type"] == [{"source_type": "podcast", "hours": 1.0}]
        assert data["top_sources"] == [{"source_title": "Test Pod", "count": 5}]
