"""Tests for FeedService — JSON Feed parser, feed discovery, content dispatch, HTTP fetching, extraction.

Covers:
- ``parse_json_feed()`` — well-formed, minimal, malformed, content fallbacks, dates
- ``discover_feeds_from_html()`` — RSS/Atom/JSON links, relative URLs, empty
- ``parse_feed_content()`` — XML vs JSON dispatch, fallback for unknown types
- ``fetch_feed()`` — conditional GET headers, 304/200/error handling
- ``extract_article_content()`` — trafilatura extraction, import guard, error handling

Uses ``importlib.util.spec_from_file_location`` to import feed_service.py
from its file path (avoids collision with ``backend/app/`` package).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Module import via file path ──

_svc_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "rss-reader"
    / "services"
    / "feed_service.py"
)
_spec = importlib.util.spec_from_file_location("feed_service_mod", _svc_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["feed_service_mod"] = _mod
_spec.loader.exec_module(_mod)

parse_json_feed = _mod.parse_json_feed
discover_feeds_from_html = _mod.discover_feeds_from_html
parse_feed_content = _mod.parse_feed_content
fetch_feed = _mod.fetch_feed
extract_article_content = _mod.extract_article_content
FeedFetchError = _mod.FeedFetchError
mint_subscription_iri = _mod.mint_subscription_iri
check_subscription_exists = _mod.check_subscription_exists
subscribe = _mod.subscribe
unsubscribe = _mod.unsubscribe
update_subscription_state = _mod.update_subscription_state
SUBSCRIPTIONS_WITH_STATE_SPARQL = _mod.SUBSCRIPTIONS_WITH_STATE_SPARQL
SUBSCRIPTION_TYPE = _mod.SUBSCRIPTION_TYPE
RSS_NS = _mod.RSS_NS


# ── Fixtures: JSON Feed content ──


def _make_json_feed(**overrides) -> str:
    """Build a valid JSON Feed 1.1 string."""
    data = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Test Blog",
        "home_page_url": "https://example.com/",
        "feed_url": "https://example.com/feed.json",
        "items": [
            {
                "id": "article-1",
                "url": "https://example.com/article/1",
                "title": "First Post",
                "content_text": "Hello world!",
                "date_published": "2025-03-15T10:30:00Z",
                "authors": [{"name": "Alice"}],
            },
            {
                "id": "article-2",
                "url": "https://example.com/article/2",
                "title": "Second Post",
                "content_html": "<p>Rich content</p>",
                "date_published": "2025-03-16T12:00:00+00:00",
                "authors": [{"name": "Bob"}, {"name": "Carol"}],
            },
            {
                "id": "article-3",
                "url": "https://example.com/article/3",
                "title": "Third Post",
                "content_text": "Plain text wins",
                "content_html": "<p>HTML alternative</p>",
                "date_published": "2025-03-17T08:00:00Z",
                "authors": [{"name": "Dave"}],
            },
        ],
    }
    data.update(overrides)
    return json.dumps(data)


# ══════════════════════════════════════════════════════════
# JSON Feed tests (≥5)
# ══════════════════════════════════════════════════════════


class TestParseJsonFeed:
    """Tests for parse_json_feed()."""

    def test_well_formed_feed_with_3_items(self):
        """Well-formed JSON Feed 1.1 with 3 items → 3 entries with correct fields."""
        content = _make_json_feed()
        result = parse_json_feed(content)

        assert result["bozo"] is False
        assert len(result["entries"]) == 3

        e0 = result["entries"][0]
        assert e0.id == "article-1"
        assert e0.title == "First Post"
        assert e0.link == "https://example.com/article/1"
        assert e0.author == "Alice"
        assert e0.summary == "Hello world!"

        e1 = result["entries"][1]
        assert e1.id == "article-2"
        assert e1.title == "Second Post"
        assert e1.author == "Bob"  # first author from array

        # Feed-level metadata
        assert result["feed"]["title"] == "Test Blog"
        assert result["feed"]["link"] == "https://example.com/"

    def test_content_text_preferred_over_content_html(self):
        """When both content_text and content_html present, content_text wins."""
        content = _make_json_feed()
        result = parse_json_feed(content)

        # Third item has both content_text and content_html
        e2 = result["entries"][2]
        assert e2.summary == "Plain text wins"
        assert "HTML alternative" not in e2.summary

    def test_content_html_fallback_when_no_text(self):
        """When only content_html present, it is used as summary (truncated)."""
        content = _make_json_feed()
        result = parse_json_feed(content)

        # Second item has only content_html
        e1 = result["entries"][1]
        assert "<p>Rich content</p>" in e1.summary

    def test_date_published_parsed_to_struct_time(self):
        """ISO 8601 date_published parsed to time.struct_time."""
        content = _make_json_feed()
        result = parse_json_feed(content)

        e0 = result["entries"][0]
        assert e0.published_parsed is not None
        assert isinstance(e0.published_parsed, time.struct_time)
        assert e0.published_parsed.tm_year == 2025
        assert e0.published_parsed.tm_mon == 3
        assert e0.published_parsed.tm_mday == 15

    def test_minimal_feed_missing_optional_fields(self):
        """Items with only id and url → entries with empty defaults for missing fields."""
        data = {
            "version": "https://jsonfeed.org/version/1.1",
            "title": "Minimal",
            "items": [
                {"id": "min-1", "url": "https://example.com/min/1"},
                {"id": "min-2"},
            ],
        }
        result = parse_json_feed(json.dumps(data))

        assert result["bozo"] is False
        assert len(result["entries"]) == 2

        e0 = result["entries"][0]
        assert e0.id == "min-1"
        assert e0.link == "https://example.com/min/1"
        assert e0.title == ""
        assert e0.author == ""
        assert e0.summary == ""
        assert e0.published_parsed is None

        e1 = result["entries"][1]
        assert e1.id == "min-2"
        assert e1.link == ""  # no url key

    def test_malformed_json_returns_bozo(self):
        """Invalid JSON string → bozo=True, entries=[], no exception raised."""
        result = parse_json_feed("this is not { valid json")

        assert result["bozo"] is True
        assert result["entries"] == []
        assert result["bozo_exception"] is not None
        assert isinstance(result["feed"], dict)

    def test_missing_items_key_returns_bozo(self):
        """JSON object without 'items' key → bozo=True."""
        result = parse_json_feed(json.dumps({"version": "1.1", "title": "No items"}))

        assert result["bozo"] is True
        assert result["entries"] == []

    def test_bytes_input_decoded(self):
        """bytes input is decoded to UTF-8 before parsing."""
        content = _make_json_feed()
        result = parse_json_feed(content.encode("utf-8"))

        assert result["bozo"] is False
        assert len(result["entries"]) == 3
        assert result["entries"][0].title == "First Post"


# ══════════════════════════════════════════════════════════
# Feed discovery tests (≥4)
# ══════════════════════════════════════════════════════════


class TestDiscoverFeedsFromHtml:
    """Tests for discover_feeds_from_html()."""

    def test_rss_and_atom_links_discovered(self):
        """HTML with RSS + Atom link tags → both discovered."""
        html = """
        <html>
        <head>
            <link rel="alternate" type="application/rss+xml"
                  href="https://example.com/feed.xml" title="RSS Feed">
            <link rel="alternate" type="application/atom+xml"
                  href="https://example.com/atom.xml" title="Atom Feed">
        </head>
        <body>Hello</body>
        </html>
        """
        feeds = discover_feeds_from_html(html, "https://example.com/")

        assert len(feeds) == 2
        assert feeds[0]["url"] == "https://example.com/feed.xml"
        assert feeds[0]["type"] == "application/rss+xml"
        assert feeds[0]["title"] == "RSS Feed"
        assert feeds[1]["url"] == "https://example.com/atom.xml"
        assert feeds[1]["type"] == "application/atom+xml"

    def test_relative_href_resolved(self):
        """Relative feed href resolved against base_url."""
        html = """
        <html><head>
            <link rel="alternate" type="application/rss+xml"
                  href="/blog/feed.xml" title="Blog RSS">
        </head></html>
        """
        feeds = discover_feeds_from_html(html, "https://example.com/page/about")

        assert len(feeds) == 1
        assert feeds[0]["url"] == "https://example.com/blog/feed.xml"

    def test_no_alternate_links_returns_empty(self):
        """HTML with no feed link tags → empty list."""
        html = """
        <html><head>
            <link rel="stylesheet" href="style.css">
            <link rel="icon" href="favicon.ico">
        </head><body>No feeds here</body></html>
        """
        feeds = discover_feeds_from_html(html, "https://example.com/")

        assert feeds == []

    def test_json_feed_type_discovered(self):
        """HTML with application/feed+json type → JSON Feed discovered."""
        html = """
        <html><head>
            <link rel="alternate" type="application/feed+json"
                  href="https://example.com/feed.json" title="JSON Feed">
        </head></html>
        """
        feeds = discover_feeds_from_html(html, "https://example.com/")

        assert len(feeds) == 1
        assert feeds[0]["url"] == "https://example.com/feed.json"
        assert feeds[0]["type"] == "application/feed+json"
        assert feeds[0]["title"] == "JSON Feed"

    def test_application_json_type_discovered(self):
        """HTML with application/json type → feed discovered."""
        html = """
        <html><head>
            <link rel="alternate" type="application/json"
                  href="/api/feed" title="API Feed">
        </head></html>
        """
        feeds = discover_feeds_from_html(html, "https://example.com/")

        assert len(feeds) == 1
        assert feeds[0]["url"] == "https://example.com/api/feed"
        assert feeds[0]["type"] == "application/json"


# ══════════════════════════════════════════════════════════
# Content type dispatch tests (≥3)
# ══════════════════════════════════════════════════════════


class TestParseFeedContent:
    """Tests for parse_feed_content()."""

    def test_xml_content_type_uses_feedparser(self):
        """XML content type → feedparser parses the RSS."""
        rss_xml = b"""<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Test RSS</title>
            <link>https://example.com</link>
            <item>
              <title>XML Article</title>
              <link>https://example.com/xml/1</link>
              <guid>xml-guid-1</guid>
            </item>
          </channel>
        </rss>
        """
        result = parse_feed_content(rss_xml, "application/rss+xml")

        assert len(result["entries"]) == 1
        assert result["entries"][0]["title"] == "XML Article"
        assert result["feed"]["title"] == "Test RSS"

    def test_json_content_type_uses_json_parser(self):
        """JSON content type → parse_json_feed parses the JSON Feed."""
        jf = json.dumps({
            "version": "https://jsonfeed.org/version/1.1",
            "title": "JSON Blog",
            "items": [
                {
                    "id": "jf-1",
                    "url": "https://example.com/jf/1",
                    "title": "JSON Article",
                    "content_text": "Hello from JSON Feed",
                },
            ],
        })
        result = parse_feed_content(jf.encode("utf-8"), "application/feed+json")

        assert len(result["entries"]) == 1
        assert result["entries"][0].title == "JSON Article"
        assert result["entries"][0].summary == "Hello from JSON Feed"
        assert result["feed"]["title"] == "JSON Blog"

    def test_application_json_content_type(self):
        """application/json content type → JSON parser used."""
        jf = json.dumps({
            "version": "https://jsonfeed.org/version/1.1",
            "title": "Plain JSON",
            "items": [{"id": "pj-1", "title": "Item"}],
        })
        result = parse_feed_content(jf.encode("utf-8"), "application/json")

        assert result["bozo"] is False
        assert len(result["entries"]) == 1
        assert result["entries"][0].title == "Item"

    def test_empty_content_type_falls_back_to_feedparser(self):
        """Empty content type → feedparser used (XML fallback)."""
        rss_xml = b"""<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Fallback RSS</title>
            <item>
              <title>Fallback Article</title>
              <link>https://example.com/fb/1</link>
            </item>
          </channel>
        </rss>
        """
        result = parse_feed_content(rss_xml, "")

        assert len(result["entries"]) == 1
        assert result["entries"][0]["title"] == "Fallback Article"

    def test_atom_content_type_uses_feedparser(self):
        """Atom content type → feedparser handles Atom XML."""
        atom_xml = b"""<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Atom Feed</title>
          <link href="https://example.com"/>
          <entry>
            <title>Atom Entry</title>
            <link href="https://example.com/atom/1"/>
            <id>urn:atom:entry:1</id>
            <updated>2025-03-15T10:00:00Z</updated>
          </entry>
        </feed>
        """
        result = parse_feed_content(atom_xml, "application/atom+xml")

        assert len(result["entries"]) == 1
        assert result["entries"][0]["title"] == "Atom Entry"


# ══════════════════════════════════════════════════════════
# Helper: mock httpx-like response
# ══════════════════════════════════════════════════════════


def _mock_response(
    status_code: int = 200,
    content: bytes = b"",
    text: str = "",
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Create a mock httpx.Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.text = text or content.decode("utf-8", errors="replace")
    # httpx.Headers acts like a case-insensitive dict with .get()
    _headers = headers or {}
    resp.headers = MagicMock()
    resp.headers.get = lambda key, default=None: _headers.get(key, default)
    return resp


def _mock_http_client(response: MagicMock) -> AsyncMock:
    """Create a mock http_client whose .get() returns the given response."""
    client = AsyncMock()
    client.get.return_value = response
    return client


# ══════════════════════════════════════════════════════════
# fetch_feed() tests (≥5)
# ══════════════════════════════════════════════════════════


class TestFetchFeed:
    """Tests for fetch_feed() — conditional GET, status handling."""

    @pytest.mark.asyncio
    async def test_sends_etag_header(self):
        """When etag provided, If-None-Match header is sent."""
        resp = _mock_response(200, b"<feed/>", headers={"content-type": "text/xml"})
        client = _mock_http_client(resp)

        await fetch_feed(client, "https://example.com/feed.xml", etag='"abc123"')

        call_kwargs = client.get.call_args
        assert call_kwargs.kwargs["headers"]["If-None-Match"] == '"abc123"'

    @pytest.mark.asyncio
    async def test_sends_last_modified_header(self):
        """When last_modified provided, If-Modified-Since header is sent."""
        resp = _mock_response(200, b"<feed/>", headers={"content-type": "text/xml"})
        client = _mock_http_client(resp)

        await fetch_feed(
            client,
            "https://example.com/feed.xml",
            last_modified="Sat, 01 Jan 2025 00:00:00 GMT",
        )

        call_kwargs = client.get.call_args
        assert (
            call_kwargs.kwargs["headers"]["If-Modified-Since"]
            == "Sat, 01 Jan 2025 00:00:00 GMT"
        )

    @pytest.mark.asyncio
    async def test_304_returns_none_content(self):
        """HTTP 304 → content is None, status is 304."""
        resp = _mock_response(
            304, b"", headers={"etag": '"same"', "content-type": ""}
        )
        client = _mock_http_client(resp)

        content, headers, status = await fetch_feed(
            client, "https://example.com/feed.xml", etag='"same"'
        )

        assert content is None
        assert status == 304
        assert headers["etag"] == '"same"'

    @pytest.mark.asyncio
    async def test_200_returns_content_and_headers(self):
        """HTTP 200 → bytes content returned with extracted headers."""
        resp = _mock_response(
            200,
            b"<rss><channel><title>T</title></channel></rss>",
            headers={
                "etag": '"new-etag"',
                "last-modified": "Sun, 02 Jan 2025 00:00:00 GMT",
                "content-type": "application/rss+xml",
            },
        )
        client = _mock_http_client(resp)

        content, headers, status = await fetch_feed(
            client, "https://example.com/feed.xml"
        )

        assert status == 200
        assert content == b"<rss><channel><title>T</title></channel></rss>"
        assert headers["etag"] == '"new-etag"'
        assert headers["last_modified"] == "Sun, 02 Jan 2025 00:00:00 GMT"
        assert headers["content_type"] == "application/rss+xml"

    @pytest.mark.asyncio
    async def test_error_raises_feed_fetch_error(self):
        """HTTP 404 → FeedFetchError raised with url and status_code."""
        resp = _mock_response(404, b"Not Found")
        client = _mock_http_client(resp)

        with pytest.raises(FeedFetchError) as exc_info:
            await fetch_feed(client, "https://example.com/gone.xml")

        assert exc_info.value.status_code == 404
        assert exc_info.value.url == "https://example.com/gone.xml"

    @pytest.mark.asyncio
    async def test_500_raises_feed_fetch_error(self):
        """HTTP 500 → FeedFetchError raised."""
        resp = _mock_response(500, b"Internal Server Error")
        client = _mock_http_client(resp)

        with pytest.raises(FeedFetchError) as exc_info:
            await fetch_feed(client, "https://example.com/broken.xml")

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_no_conditional_headers_when_none(self):
        """When etag and last_modified are None, no conditional headers sent."""
        resp = _mock_response(200, b"<feed/>", headers={"content-type": "text/xml"})
        client = _mock_http_client(resp)

        await fetch_feed(client, "https://example.com/feed.xml")

        call_kwargs = client.get.call_args
        assert call_kwargs.kwargs["headers"] == {}

    @pytest.mark.asyncio
    async def test_follow_redirects_passed(self):
        """follow_redirects=True is always passed to http_client.get()."""
        resp = _mock_response(200, b"<feed/>", headers={"content-type": "text/xml"})
        client = _mock_http_client(resp)

        await fetch_feed(client, "https://example.com/feed.xml")

        call_kwargs = client.get.call_args
        assert call_kwargs.kwargs["follow_redirects"] is True


# ══════════════════════════════════════════════════════════
# extract_article_content() tests (≥4)
# ══════════════════════════════════════════════════════════


class TestExtractArticleContent:
    """Tests for extract_article_content() — trafilatura integration."""

    @pytest.mark.asyncio
    async def test_success_returns_markdown(self):
        """Successful extraction returns markdown string."""
        html = "<html><body><article><p>Hello world</p></article></body></html>"
        resp = _mock_response(200, html.encode(), text=html)
        client = _mock_http_client(resp)

        with patch.object(_mod, "HAS_TRAFILATURA", True), \
             patch.object(_mod, "trafilatura") as mock_traf:
            mock_traf.extract.return_value = "# Hello world"
            result = await extract_article_content(client, "https://example.com/article")

        assert result == "# Hello world"
        mock_traf.extract.assert_called_once_with(
            html, output_format="markdown", include_links=True
        )

    @pytest.mark.asyncio
    async def test_no_trafilatura_returns_none(self):
        """When trafilatura not installed, returns None without HTTP call."""
        client = AsyncMock()

        with patch.object(_mod, "HAS_TRAFILATURA", False):
            result = await extract_article_content(
                client, "https://example.com/article"
            )

        assert result is None
        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self):
        """When HTTP fetch fails (non-200), returns None."""
        resp = _mock_response(500, b"error")
        client = _mock_http_client(resp)

        with patch.object(_mod, "HAS_TRAFILATURA", True), \
             patch.object(_mod, "trafilatura") as mock_traf:
            result = await extract_article_content(
                client, "https://example.com/article"
            )

        assert result is None
        mock_traf.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_extraction_failure_returns_none(self):
        """When trafilatura.extract returns None, result is None."""
        html = "<html><body>nothing useful</body></html>"
        resp = _mock_response(200, html.encode(), text=html)
        client = _mock_http_client(resp)

        with patch.object(_mod, "HAS_TRAFILATURA", True), \
             patch.object(_mod, "trafilatura") as mock_traf:
            mock_traf.extract.return_value = None
            result = await extract_article_content(
                client, "https://example.com/empty"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_exception_during_fetch_returns_none(self):
        """When http_client.get raises, returns None (no crash)."""
        client = AsyncMock()
        client.get.side_effect = ConnectionError("network down")

        with patch.object(_mod, "HAS_TRAFILATURA", True):
            result = await extract_article_content(
                client, "https://example.com/article"
            )

        assert result is None


# ══════════════════════════════════════════════════════════
# Import app module for poll_feeds integration tests
# ══════════════════════════════════════════════════════════

_app_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "rss-reader"
    / "app.py"
)
_app_spec = importlib.util.spec_from_file_location("rss_reader_app_svc", _app_path)
_app_mod = importlib.util.module_from_spec(_app_spec)
sys.modules["rss_reader_app_svc"] = _app_mod
_app_spec.loader.exec_module(_app_mod)

poll_feeds = _app_mod.poll_feeds
MAX_INITIAL_ARTICLES = _app_mod.MAX_INITIAL_ARTICLES
entry_to_article = _app_mod.entry_to_article


# ══════════════════════════════════════════════════════════
# Subscription management tests (≥5)
# ══════════════════════════════════════════════════════════


class TestMintSubscriptionIri:
    """Tests for mint_subscription_iri()."""

    def test_deterministic_same_url(self):
        """Same URL produces the same IRI every time."""
        url = "https://example.com/feed.xml"
        iri1 = mint_subscription_iri(url)
        iri2 = mint_subscription_iri(url)
        assert iri1 == iri2
        assert iri1.startswith("urn:sempkm:app:rss-reader:sub-")

    def test_different_urls_different_iris(self):
        """Different URLs produce different IRIs."""
        iri1 = mint_subscription_iri("https://example.com/feed.xml")
        iri2 = mint_subscription_iri("https://other.com/feed.xml")
        assert iri1 != iri2


class TestSubscribe:
    """Tests for subscribe()."""

    @pytest.mark.asyncio
    async def test_creates_correct_params(self):
        """subscribe() calls object.create with correct type and properties."""
        mock_ctx = AsyncMock()
        mock_ctx.graph.query.return_value = {"results": {"bindings": []}}
        mock_ctx.commands.execute.return_value = {}

        result = await subscribe(mock_ctx, "https://example.com/rss.xml", title="My Feed")

        assert result["status"] == "created"
        assert result["iri"].startswith("urn:sempkm:app:rss-reader:sub-")

        # Verify object.create was called with correct params
        call_args = mock_ctx.commands.execute.call_args
        assert call_args[0][0] == "object.create"
        params = call_args[0][1]
        assert params["type"] == SUBSCRIPTION_TYPE
        assert params["properties"][f"{RSS_NS}feedUrl"] == "https://example.com/rss.xml"
        assert params["properties"]["dcterms:title"] == "My Feed"
        assert params["properties"][f"{RSS_NS}errorCount"] == 0
        assert params["properties"][f"{RSS_NS}lastError"] == ""

    @pytest.mark.asyncio
    async def test_dedup_returns_existing(self):
        """subscribe() returns duplicate status when subscription exists."""
        existing_iri = "urn:sempkm:app:rss-reader:sub-abc123"
        mock_ctx = AsyncMock()
        mock_ctx.graph.query.return_value = {
            "results": {
                "bindings": [{"sub": {"value": existing_iri}}]
            }
        }

        result = await subscribe(mock_ctx, "https://example.com/rss.xml")

        assert result["status"] == "duplicate"
        assert result["iri"] == existing_iri
        mock_ctx.commands.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_title_defaults_to_url(self):
        """subscribe() defaults title to feed_url when title is None."""
        mock_ctx = AsyncMock()
        mock_ctx.graph.query.return_value = {"results": {"bindings": []}}
        mock_ctx.commands.execute.return_value = {}

        await subscribe(mock_ctx, "https://example.com/rss.xml")

        call_args = mock_ctx.commands.execute.call_args
        params = call_args[0][1]
        assert params["properties"]["dcterms:title"] == "https://example.com/rss.xml"


class TestUnsubscribe:
    """Tests for unsubscribe()."""

    @pytest.mark.asyncio
    async def test_patches_inactive(self):
        """unsubscribe() calls object.patch with isActive=False."""
        mock_ctx = AsyncMock()
        mock_ctx.commands.execute.return_value = {}

        sub_iri = "urn:sempkm:app:rss-reader:sub-abc"
        result = await unsubscribe(mock_ctx, sub_iri)

        assert result["status"] == "unsubscribed"
        assert result["iri"] == sub_iri

        call_args = mock_ctx.commands.execute.call_args
        assert call_args[0][0] == "object.patch"
        params = call_args[0][1]
        assert params["iri"] == sub_iri
        assert params["properties"][f"{RSS_NS}isActive"] is False


# ══════════════════════════════════════════════════════════
# Error tracking tests (≥4)
# ══════════════════════════════════════════════════════════


class TestUpdateSubscriptionState:
    """Tests for update_subscription_state()."""

    @pytest.mark.asyncio
    async def test_success_resets_error(self):
        """Success state: error_count=0, last_error="" produces correct patch."""
        mock_ctx = AsyncMock()
        mock_ctx.commands.execute.return_value = {}

        sub_iri = "urn:sempkm:app:rss-reader:sub-abc"
        await update_subscription_state(
            mock_ctx, sub_iri, error_count=0, last_error=""
        )

        call_args = mock_ctx.commands.execute.call_args
        assert call_args[0][0] == "object.patch"
        params = call_args[0][1]
        assert params["properties"][f"{RSS_NS}errorCount"] == 0
        assert params["properties"][f"{RSS_NS}lastError"] == ""

    @pytest.mark.asyncio
    async def test_failure_increments(self):
        """Failure state: error_count=3, last_error set produces correct patch."""
        mock_ctx = AsyncMock()
        mock_ctx.commands.execute.return_value = {}

        sub_iri = "urn:sempkm:app:rss-reader:sub-abc"
        await update_subscription_state(
            mock_ctx, sub_iri, error_count=3, last_error="404 Not Found"
        )

        call_args = mock_ctx.commands.execute.call_args
        params = call_args[0][1]
        assert params["properties"][f"{RSS_NS}errorCount"] == 3
        assert params["properties"][f"{RSS_NS}lastError"] == "404 Not Found"

    @pytest.mark.asyncio
    async def test_with_etag_and_last_modified(self):
        """etag and last_modified produce rss:etag and rss:lastModifiedHeader."""
        mock_ctx = AsyncMock()
        mock_ctx.commands.execute.return_value = {}

        sub_iri = "urn:sempkm:app:rss-reader:sub-abc"
        await update_subscription_state(
            mock_ctx, sub_iri,
            etag='"abc123"',
            last_modified="Sat, 01 Jan 2025 00:00:00 GMT",
        )

        call_args = mock_ctx.commands.execute.call_args
        params = call_args[0][1]
        assert params["properties"][f"{RSS_NS}etag"] == '"abc123"'
        assert params["properties"][f"{RSS_NS}lastModifiedHeader"] == "Sat, 01 Jan 2025 00:00:00 GMT"

    @pytest.mark.asyncio
    async def test_skips_when_all_none(self):
        """All params None → object.patch is NOT called."""
        mock_ctx = AsyncMock()

        sub_iri = "urn:sempkm:app:rss-reader:sub-abc"
        await update_subscription_state(mock_ctx, sub_iri)

        mock_ctx.commands.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_last_polled_only(self):
        """Only last_polled set → only rss:lastPolled in patch."""
        mock_ctx = AsyncMock()
        mock_ctx.commands.execute.return_value = {}

        sub_iri = "urn:sempkm:app:rss-reader:sub-abc"
        await update_subscription_state(
            mock_ctx, sub_iri, last_polled="2025-03-15T10:00:00+00:00"
        )

        call_args = mock_ctx.commands.execute.call_args
        params = call_args[0][1]
        assert params["properties"][f"{RSS_NS}lastPolled"] == "2025-03-15T10:00:00+00:00"
        assert f"{RSS_NS}etag" not in params["properties"]
        assert f"{RSS_NS}errorCount" not in params["properties"]


# ══════════════════════════════════════════════════════════
# Poll-feeds integration tests (≥3)
# ══════════════════════════════════════════════════════════


def _make_mock_ctx_for_poll(bindings, existing_iris=None):
    """Build a mock AppContext for poll_feeds tests."""
    mock_ctx = AsyncMock()
    mock_ctx.app_id = "rss-reader"

    query_results = [{"results": {"bindings": bindings}}]
    if existing_iris is not None:
        query_results.append({
            "results": {"bindings": [{"article": {"value": iri}} for iri in existing_iris]}
        })
    mock_ctx.graph.query.side_effect = query_results

    # Set up bulk context manager
    mock_batch = MagicMock()
    mock_bulk_cm = MagicMock()
    mock_bulk_cm.__aenter__ = AsyncMock(return_value=mock_batch)
    mock_bulk_cm.__aexit__ = AsyncMock(return_value=False)
    mock_ctx.commands = MagicMock()
    mock_ctx.commands.bulk.return_value = mock_bulk_cm
    mock_ctx.commands.execute = AsyncMock()

    return mock_ctx, mock_batch


class TestPollFeedsIntegration:
    """Integration tests for poll_feeds using FeedService."""

    @pytest.mark.asyncio
    async def test_uses_conditional_get(self):
        """poll_feeds passes etag from SPARQL to fetch_feed."""
        bindings = [
            {
                "sub": {"value": "urn:sempkm:app:rss-reader:sub-1"},
                "feedUrl": {"value": "https://example.com/feed.xml"},
                "etag": {"value": '"etag-abc"'},
                "lastModified": {"value": "Sat, 01 Jan 2025 00:00:00 GMT"},
            }
        ]
        mock_ctx, _ = _make_mock_ctx_for_poll(bindings, existing_iris=set())
        feed_content = {"bozo": False, "entries": []}

        with patch("rss_reader_app_svc.fetch_feed", new_callable=AsyncMock) as mock_fetch, \
             patch("rss_reader_app_svc.parse_feed_content", return_value=feed_content), \
             patch("rss_reader_app_svc.update_subscription_state", new_callable=AsyncMock):
            mock_fetch.return_value = (
                b"<rss/>",
                {"content_type": "application/rss+xml", "etag": '"etag-new"', "last_modified": None},
                200,
            )
            await poll_feeds(mock_ctx)

            # Verify conditional GET headers were forwarded
            call_kwargs = mock_fetch.call_args
            assert call_kwargs.kwargs.get("etag") == '"etag-abc"'
            assert call_kwargs.kwargs.get("last_modified") == "Sat, 01 Jan 2025 00:00:00 GMT"

    @pytest.mark.asyncio
    async def test_handles_304_no_articles_created(self):
        """304 response skips parsing, updates lastPolled, creates no articles."""
        bindings = [
            {
                "sub": {"value": "urn:sempkm:app:rss-reader:sub-1"},
                "feedUrl": {"value": "https://example.com/feed.xml"},
                "etag": {"value": '"etag-same"'},
            }
        ]
        mock_ctx, mock_batch = _make_mock_ctx_for_poll(bindings)

        with patch("rss_reader_app_svc.fetch_feed", new_callable=AsyncMock) as mock_fetch, \
             patch("rss_reader_app_svc.parse_feed_content") as mock_parse, \
             patch("rss_reader_app_svc.update_subscription_state", new_callable=AsyncMock) as mock_update:
            mock_fetch.return_value = (
                None,
                {"content_type": "", "etag": '"etag-same"', "last_modified": None},
                304,
            )
            result = await poll_feeds(mock_ctx)

            # No parsing should happen on 304
            mock_parse.assert_not_called()
            # lastPolled should still be updated
            mock_update.assert_called_once()
            update_kwargs = mock_update.call_args.kwargs
            assert update_kwargs.get("last_polled") is not None
            # Feed counted as polled, but no articles
            assert result["feeds_polled"] == 1
            assert result["articles_created"] == 0

    @pytest.mark.asyncio
    async def test_max_initial_articles_capped(self):
        """When >50 new articles found, only first 50 are created."""
        bindings = [
            {
                "sub": {"value": "urn:sempkm:app:rss-reader:sub-1"},
                "feedUrl": {"value": "https://example.com/feed.xml"},
            }
        ]
        mock_ctx, mock_batch = _make_mock_ctx_for_poll(bindings, existing_iris=set())

        # Generate 100 mock entries
        entries = [
            {
                "title": f"Article {i}",
                "link": f"https://example.com/article/{i}",
                "id": f"guid-{i}",
                "summary": f"Summary {i}",
            }
            for i in range(100)
        ]
        feed_content = {"bozo": False, "entries": entries}

        with patch("rss_reader_app_svc.fetch_feed", new_callable=AsyncMock) as mock_fetch, \
             patch("rss_reader_app_svc.parse_feed_content", return_value=feed_content), \
             patch("rss_reader_app_svc.update_subscription_state", new_callable=AsyncMock):
            mock_fetch.return_value = (
                b"<rss/>",
                {"content_type": "application/rss+xml", "etag": None, "last_modified": None},
                200,
            )
            result = await poll_feeds(mock_ctx)

            assert result["articles_created"] == MAX_INITIAL_ARTICLES
            assert mock_batch.add.call_count == MAX_INITIAL_ARTICLES

    @pytest.mark.asyncio
    async def test_fetch_error_increments_error_count(self):
        """FeedFetchError updates subscription with incremented error count."""
        bindings = [
            {
                "sub": {"value": "urn:sempkm:app:rss-reader:sub-1"},
                "feedUrl": {"value": "https://example.com/feed.xml"},
            }
        ]
        mock_ctx, _ = _make_mock_ctx_for_poll(bindings)

        with patch("rss_reader_app_svc.fetch_feed", new_callable=AsyncMock) as mock_fetch, \
             patch("rss_reader_app_svc.update_subscription_state", new_callable=AsyncMock) as mock_update:
            mock_fetch.side_effect = FeedFetchError("https://example.com/feed.xml", 404)
            await poll_feeds(mock_ctx)

            # Error state should be persisted
            mock_update.assert_called_once()
            update_kwargs = mock_update.call_args.kwargs
            assert update_kwargs["error_count"] == 1
            assert "404" in update_kwargs["last_error"]


# ══════════════════════════════════════════════════════════
# Subscribe route contract tests (≥3)
# ══════════════════════════════════════════════════════════


class TestSubscribeRouteContract:
    """Contract tests for subscribe/discover functions as called by routes."""

    @pytest.mark.asyncio
    async def test_subscribe_new_url_returns_created(self):
        """subscribe() with a new URL returns status=created — the subscribe route's happy path."""
        mock_ctx = AsyncMock()
        mock_ctx.graph.query.return_value = {"results": {"bindings": []}}
        mock_ctx.commands.execute.return_value = {}

        result = await subscribe(mock_ctx, "https://blog.example.com/feed.xml", title="Example Blog")

        assert result["status"] == "created"
        assert result["iri"].startswith("urn:sempkm:app:rss-reader:sub-")

        # Verify the created subscription has correct properties
        call_args = mock_ctx.commands.execute.call_args
        params = call_args[0][1]
        assert params["properties"]["dcterms:title"] == "Example Blog"
        assert params["properties"][f"{RSS_NS}feedUrl"] == "https://blog.example.com/feed.xml"

    @pytest.mark.asyncio
    async def test_subscribe_existing_url_returns_duplicate(self):
        """subscribe() with an existing URL returns status=duplicate — the duplicate detection path."""
        mock_ctx = AsyncMock()
        mock_ctx.graph.query.return_value = {
            "results": {
                "bindings": [{"sub": {"value": "urn:sempkm:app:rss-reader:sub-existing"}}]
            }
        }

        result = await subscribe(mock_ctx, "https://blog.example.com/feed.xml")

        assert result["status"] == "duplicate"
        assert result["iri"] == "urn:sempkm:app:rss-reader:sub-existing"
        mock_ctx.commands.execute.assert_not_called()

    def test_discover_feeds_with_multiple_link_tags(self):
        """discover_feeds_from_html() with realistic multi-feed HTML finds all feeds."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <title>My Blog</title>
            <link rel="alternate" type="application/rss+xml"
                  href="/blog/rss.xml" title="Blog RSS">
            <link rel="alternate" type="application/atom+xml"
                  href="/blog/atom.xml" title="Blog Atom">
            <link rel="alternate" type="application/feed+json"
                  href="/blog/feed.json" title="Blog JSON Feed">
            <link rel="stylesheet" href="/css/style.css">
            <link rel="icon" href="/favicon.ico">
        </head>
        <body>
            <h1>Welcome to my blog</h1>
        </body>
        </html>
        """
        feeds = discover_feeds_from_html(html, "https://myblog.example.com/page/about")

        assert len(feeds) == 3

        # RSS feed — relative URL resolved
        assert feeds[0]["url"] == "https://myblog.example.com/blog/rss.xml"
        assert feeds[0]["type"] == "application/rss+xml"
        assert feeds[0]["title"] == "Blog RSS"

        # Atom feed
        assert feeds[1]["url"] == "https://myblog.example.com/blog/atom.xml"
        assert feeds[1]["type"] == "application/atom+xml"
        assert feeds[1]["title"] == "Blog Atom"

        # JSON Feed
        assert feeds[2]["url"] == "https://myblog.example.com/blog/feed.json"
        assert feeds[2]["type"] == "application/feed+json"
        assert feeds[2]["title"] == "Blog JSON Feed"

    def test_discover_feeds_no_feeds_returns_empty(self):
        """discover_feeds_from_html() on a page with no feeds returns empty list."""
        html = """<html><head><title>No feeds</title></head><body>Just text</body></html>"""
        feeds = discover_feeds_from_html(html, "https://example.com/")
        assert feeds == []
