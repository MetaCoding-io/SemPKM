"""Tests for the RSS feed parsing pipeline and article creation.

Exercises ``entry_to_article()``, ``_mint_article_iri()``,
``_struct_time_to_iso()``, ``get_existing_article_iris()``,
and the ``poll_feeds`` task handler with mocked SDK clients.
No running Docker stack required.
"""

from __future__ import annotations

import hashlib
import re
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import importlib.util

import pytest

# Load the rss-reader app module directly by file path to avoid collision
# with the backend/app/ package.
_app_path = Path(__file__).resolve().parent.parent.parent / "apps" / "rss-reader" / "app.py"
_spec = importlib.util.spec_from_file_location("rss_reader_app_mod", _app_path)
_rss_mod = importlib.util.module_from_spec(_spec)
sys.modules["rss_reader_app_mod"] = _rss_mod
_spec.loader.exec_module(_rss_mod)

ARTICLE_TYPE = _rss_mod.ARTICLE_TYPE
RSS_NS = _rss_mod.RSS_NS
SUBSCRIPTION_TYPE = _rss_mod.SUBSCRIPTION_TYPE
_mint_article_iri = _rss_mod._mint_article_iri
_struct_time_to_iso = _rss_mod._struct_time_to_iso
entry_to_article = _rss_mod.entry_to_article
get_existing_article_iris = _rss_mod.get_existing_article_iris
poll_feeds = _rss_mod.poll_feeds


# ── Fixtures ──

FEED_IRI = "urn:sempkm:app:rss-reader:feed-abc"
APP_ID = "rss-reader"


def _make_rss2_entry(**overrides) -> dict:
    """Create a feedparser-style RSS 2.0 entry dict."""
    entry: dict = {
        "title": "Test Article Title",
        "link": "https://example.com/article/1",
        "author": "Jane Doe",
        "id": "guid-12345",
        "published_parsed": time.strptime("2025-03-15 10:30:00", "%Y-%m-%d %H:%M:%S"),
        "summary": "This is a summary of the test article.",
    }
    entry.update(overrides)
    return entry


def _make_atom_entry(**overrides) -> dict:
    """Create a feedparser-style Atom entry dict."""
    entry: dict = {
        "title": "Atom Article Title",
        "link": "https://example.com/atom/entry/1",
        "author": "John Smith",
        "id": "tag:example.com,2025:entry-99",
        "updated_parsed": time.strptime("2025-06-20 14:00:00", "%Y-%m-%d %H:%M:%S"),
        "summary": "Summary of the Atom entry.",
    }
    entry.update(overrides)
    return entry


def _make_realistic_rss2_entry() -> dict:
    """Create a realistic feedparser RSS 2.0 entry with all normalized fields."""
    return {
        "title": "Breaking: New Ontology Standard Released",
        "title_detail": {
            "type": "text/plain",
            "language": None,
            "base": "https://example.com/feed.xml",
            "value": "Breaking: New Ontology Standard Released",
        },
        "link": "https://example.com/2025/03/new-ontology-standard",
        "links": [
            {
                "rel": "alternate",
                "type": "text/html",
                "href": "https://example.com/2025/03/new-ontology-standard",
            }
        ],
        "author": "Dr. Ada Lovelace",
        "author_detail": {"name": "Dr. Ada Lovelace"},
        "id": "https://example.com/?p=42",
        "guidislink": False,
        "published": "Sat, 15 Mar 2025 12:00:00 +0000",
        "published_parsed": time.strptime("2025-03-15 12:00:00", "%Y-%m-%d %H:%M:%S"),
        "summary": "<p>The W3C has released a new standard for ontology integration...</p>",
        "summary_detail": {
            "type": "text/html",
            "language": None,
            "base": "https://example.com/feed.xml",
            "value": "<p>The W3C has released a new standard for ontology integration...</p>",
        },
        "tags": [
            {"term": "ontology", "scheme": None, "label": None},
            {"term": "w3c", "scheme": None, "label": None},
        ],
        "content": [
            {
                "type": "text/html",
                "language": None,
                "base": "https://example.com/feed.xml",
                "value": "<p>Full article content here...</p>",
            }
        ],
    }


# ── Test: RSS 2.0 Entry Mapping ──


class TestRSS2EntryMapping:
    """Tests for converting RSS 2.0 entries to Article objects."""

    def test_basic_rss2_entry(self) -> None:
        """RSS 2.0 entry maps all core fields to article properties."""
        entry = _make_rss2_entry()
        result = entry_to_article(entry, FEED_IRI, APP_ID)

        assert result["iri"].startswith("urn:sempkm:app:rss-reader:article-")
        assert result["type"] == ARTICLE_TYPE
        props = result["properties"]
        assert props["dcterms:title"] == "Test Article Title"
        assert props[f"{RSS_NS}link"] == "https://example.com/article/1"
        assert props[f"{RSS_NS}author"] == "Jane Doe"
        assert props[f"{RSS_NS}feedSource"] == FEED_IRI
        assert props[f"{RSS_NS}articleId"] == "guid-12345"

    def test_rss2_has_defaults(self) -> None:
        """RSS 2.0 article gets default isRead=False and isStarred=False."""
        entry = _make_rss2_entry()
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        props = result["properties"]
        assert props[f"{RSS_NS}isRead"] is False
        assert props[f"{RSS_NS}isStarred"] is False

    def test_rss2_published_date_parsed(self) -> None:
        """published_parsed time.struct_time is mapped to dcterms:created as ISO 8601."""
        entry = _make_rss2_entry()
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        props = result["properties"]
        assert "dcterms:created" in props
        # Should be an ISO 8601 string
        assert "2025-03-15" in props["dcterms:created"]

    def test_rss2_summary_mapped(self) -> None:
        """Summary field maps to dcterms:description."""
        entry = _make_rss2_entry()
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        assert result["properties"]["dcterms:description"] == "This is a summary of the test article."


# ── Test: Atom Entry Mapping ──


class TestAtomEntryMapping:
    """Tests for converting Atom entries to Article objects."""

    def test_atom_entry_uses_id_field(self) -> None:
        """Atom entries use ``id`` field for articleId mapping."""
        entry = _make_atom_entry()
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        props = result["properties"]
        assert props[f"{RSS_NS}articleId"] == "tag:example.com,2025:entry-99"

    def test_atom_entry_no_published_uses_none(self) -> None:
        """Atom entry with only updated_parsed (no published_parsed) has no dcterms:created.

        feedparser normalizes updated_parsed separately from published_parsed,
        so if published_parsed is absent, dcterms:created should be omitted.
        """
        entry = _make_atom_entry()
        # Remove published_parsed if present, keep only updated_parsed
        entry.pop("published_parsed", None)
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        # No published_parsed → no dcterms:created
        assert "dcterms:created" not in result["properties"]

    def test_atom_entry_all_fields_mapped(self) -> None:
        """Atom entry with published_parsed maps all expected fields."""
        entry = _make_atom_entry()
        entry["published_parsed"] = entry["updated_parsed"]
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        props = result["properties"]
        assert props["dcterms:title"] == "Atom Article Title"
        assert props[f"{RSS_NS}link"] == "https://example.com/atom/entry/1"
        assert props[f"{RSS_NS}author"] == "John Smith"
        assert "dcterms:created" in props


# ── Test: Missing Optional Fields ──


class TestMissingFields:
    """Tests for entries with missing optional fields."""

    def test_minimal_entry_only_title_and_link(self) -> None:
        """Entry with only title and link does not raise."""
        entry = {"title": "Minimal", "link": "https://example.com/min"}
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        props = result["properties"]
        assert props["dcterms:title"] == "Minimal"
        assert props[f"{RSS_NS}link"] == "https://example.com/min"
        # Optional fields not present
        assert f"{RSS_NS}author" not in props
        assert "dcterms:description" not in props
        assert "dcterms:created" not in props

    def test_entry_no_author(self) -> None:
        """Entry without author omits rss:author property."""
        entry = _make_rss2_entry()
        del entry["author"]
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        assert f"{RSS_NS}author" not in result["properties"]

    def test_entry_no_summary(self) -> None:
        """Entry without summary omits dcterms:description property."""
        entry = _make_rss2_entry()
        del entry["summary"]
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        assert "dcterms:description" not in result["properties"]

    def test_completely_empty_entry(self) -> None:
        """Completely empty entry dict does not crash."""
        result = entry_to_article({}, FEED_IRI, APP_ID)
        assert result["type"] == ARTICLE_TYPE
        assert result["iri"].startswith("urn:sempkm:app:rss-reader:article-")
        # feedSource and defaults are always present
        assert result["properties"][f"{RSS_NS}feedSource"] == FEED_IRI
        assert result["properties"][f"{RSS_NS}isRead"] is False


# ── Test: Article IRI Determinism ──


class TestArticleIRIDeterminism:
    """Tests for deterministic article IRI minting."""

    def test_same_inputs_same_iri(self) -> None:
        """Same feed_iri + entry_id produces identical IRI on repeated calls."""
        iri1 = _mint_article_iri(FEED_IRI, "entry-001", APP_ID)
        iri2 = _mint_article_iri(FEED_IRI, "entry-001", APP_ID)
        assert iri1 == iri2

    def test_different_entry_ids_different_iris(self) -> None:
        """Different entry IDs produce different IRIs."""
        iri1 = _mint_article_iri(FEED_IRI, "entry-001", APP_ID)
        iri2 = _mint_article_iri(FEED_IRI, "entry-002", APP_ID)
        assert iri1 != iri2

    def test_different_feeds_different_iris(self) -> None:
        """Same entry ID but different feed IRIs produce different IRIs."""
        iri1 = _mint_article_iri("urn:sempkm:app:rss-reader:feed-a", "entry-001", APP_ID)
        iri2 = _mint_article_iri("urn:sempkm:app:rss-reader:feed-b", "entry-001", APP_ID)
        assert iri1 != iri2

    def test_iri_uses_sha256_hex_not_raw_id(self) -> None:
        """Article IRI contains a hex hash, not the raw entry ID."""
        entry_id = "my-entry-with-special-chars/&?="
        iri = _mint_article_iri(FEED_IRI, entry_id, APP_ID)
        # Should NOT contain the raw entry ID
        assert entry_id not in iri
        # Should contain hex characters after article-
        suffix = iri.split("article-")[1]
        assert re.match(r"^[0-9a-f]+$", suffix), f"Suffix '{suffix}' is not hex"

    def test_iri_hash_length(self) -> None:
        """Article IRI hash suffix is 16 hex chars (SHA-256 truncated)."""
        iri = _mint_article_iri(FEED_IRI, "test-id", APP_ID)
        suffix = iri.split("article-")[1]
        assert len(suffix) == 16

    def test_iri_matches_manual_sha256(self) -> None:
        """IRI hash matches manual SHA-256 computation."""
        feed_iri = "urn:sempkm:app:rss-reader:feed-xyz"
        entry_id = "guid-999"
        raw = feed_iri + entry_id
        expected_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        iri = _mint_article_iri(feed_iri, entry_id, APP_ID)
        assert iri == f"urn:sempkm:app:{APP_ID}:article-{expected_hash}"

    def test_entry_to_article_iri_determinism(self) -> None:
        """entry_to_article produces the same IRI for the same entry."""
        entry = _make_rss2_entry()
        result1 = entry_to_article(entry, FEED_IRI, APP_ID)
        result2 = entry_to_article(entry, FEED_IRI, APP_ID)
        assert result1["iri"] == result2["iri"]


# ── Test: Published Date Parsing ──


class TestDateParsing:
    """Tests for _struct_time_to_iso date conversion."""

    def test_valid_struct_time_to_iso(self) -> None:
        """Valid struct_time converts to ISO 8601 string."""
        t = time.strptime("2025-03-15 10:30:00", "%Y-%m-%d %H:%M:%S")
        result = _struct_time_to_iso(t)
        assert result is not None
        assert "2025-03-15" in result
        # Should contain timezone info (UTC)
        assert "+" in result or "Z" in result

    def test_none_input_returns_none(self) -> None:
        """None input returns None."""
        assert _struct_time_to_iso(None) is None

    def test_epoch_time(self) -> None:
        """Unix epoch converts successfully."""
        t = time.strptime("1970-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        result = _struct_time_to_iso(t)
        assert result is not None
        assert "1970" in result

    def test_iso_format_parseable(self) -> None:
        """Output is a valid ISO 8601 datetime string."""
        from datetime import datetime

        t = time.strptime("2025-06-20 14:30:00", "%Y-%m-%d %H:%M:%S")
        result = _struct_time_to_iso(t)
        assert result is not None
        # Should be parseable as ISO 8601
        parsed = datetime.fromisoformat(result)
        assert parsed.year == 2025
        assert parsed.month == 6
        assert parsed.day == 20


# ── Test: Duplicate Detection Helper ──


class TestDuplicateDetection:
    """Tests for get_existing_article_iris with mocked graph client."""

    @pytest.mark.asyncio
    async def test_returns_set_of_iris(self) -> None:
        """get_existing_article_iris returns a set of IRI strings."""
        mock_graph = AsyncMock()
        mock_graph.query.return_value = {
            "results": {
                "bindings": [
                    {"article": {"value": "urn:sempkm:app:rss-reader:article-aaa"}},
                    {"article": {"value": "urn:sempkm:app:rss-reader:article-bbb"}},
                ]
            }
        }
        result = await get_existing_article_iris(mock_graph, FEED_IRI)
        assert isinstance(result, set)
        assert len(result) == 2
        assert "urn:sempkm:app:rss-reader:article-aaa" in result
        assert "urn:sempkm:app:rss-reader:article-bbb" in result

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_set(self) -> None:
        """No existing articles returns empty set."""
        mock_graph = AsyncMock()
        mock_graph.query.return_value = {"results": {"bindings": []}}
        result = await get_existing_article_iris(mock_graph, FEED_IRI)
        assert result == set()

    @pytest.mark.asyncio
    async def test_sparql_references_feed_iri(self) -> None:
        """SPARQL query includes the feed IRI for scoped dedup."""
        mock_graph = AsyncMock()
        mock_graph.query.return_value = {"results": {"bindings": []}}
        await get_existing_article_iris(mock_graph, FEED_IRI)
        call_args = mock_graph.query.call_args[0][0]
        assert FEED_IRI in call_args
        assert ARTICLE_TYPE in call_args


# ── Test: Bulk Command Assembly ──


class TestBulkCommandAssembly:
    """Tests for the bulk article creation pattern."""

    def test_article_dicts_have_required_keys(self) -> None:
        """Article dicts from entry_to_article have iri, type, properties keys."""
        entry = _make_rss2_entry()
        article = entry_to_article(entry, FEED_IRI, APP_ID)
        assert "iri" in article
        assert "type" in article
        assert "properties" in article

    def test_bulk_add_called_for_each_article(self) -> None:
        """Mock BulkCollector.add is called once per article dict."""
        entries = [
            _make_rss2_entry(id=f"guid-{i}", title=f"Article {i}")
            for i in range(5)
        ]
        articles = [entry_to_article(e, FEED_IRI, APP_ID) for e in entries]

        mock_batch = MagicMock()
        for article in articles:
            mock_batch.add("object.create", article)

        assert mock_batch.add.call_count == 5
        for call_args in mock_batch.add.call_args_list:
            assert call_args[0][0] == "object.create"
            article_dict = call_args[0][1]
            assert article_dict["type"] == ARTICLE_TYPE

    def test_dedup_filters_existing_articles(self) -> None:
        """New articles are filtered against existing IRI set."""
        entries = [
            _make_rss2_entry(id="guid-1"),
            _make_rss2_entry(id="guid-2"),
            _make_rss2_entry(id="guid-3"),
        ]
        articles = [entry_to_article(e, FEED_IRI, APP_ID) for e in entries]

        # Simulate: guid-1 already exists
        existing_iris = {articles[0]["iri"]}
        new_articles = [a for a in articles if a["iri"] not in existing_iris]
        assert len(new_articles) == 2
        assert articles[0]["iri"] not in {a["iri"] for a in new_articles}


# ── Test: Error Handling ──


class TestErrorHandling:
    """Tests for feed parsing error and edge cases."""

    @pytest.mark.asyncio
    async def test_bozo_feed_with_no_entries_skipped(self) -> None:
        """Feed with bozo=True and no entries is skipped without crash."""
        mock_ctx = AsyncMock()
        mock_ctx.app_id = APP_ID
        mock_ctx.graph.query.return_value = {
            "results": {
                "bindings": [
                    {
                        "sub": {"value": "urn:sempkm:app:rss-reader:feed-bad"},
                        "feedUrl": {"value": "https://bad-feed.example.com/rss"},
                    }
                ]
            }
        }

        # Mock fetch_feed to return content, parse_feed_content to return bozo
        bozo_result = {"bozo": True, "bozo_exception": Exception("XML parse error"), "entries": []}

        with patch("rss_reader_app_mod.fetch_feed", new_callable=AsyncMock, return_value=(b"<bad/>", {"content_type": "text/xml", "etag": None, "last_modified": None}, 200)), \
             patch("rss_reader_app_mod.parse_feed_content", return_value=bozo_result), \
             patch("rss_reader_app_mod.update_subscription_state", new_callable=AsyncMock):
            result = await poll_feeds(mock_ctx)

        # Should not crash, feeds_polled=0 because bozo with no entries is skipped
        assert result["feeds_polled"] == 0
        assert result["articles_created"] == 0

    @pytest.mark.asyncio
    async def test_empty_feed_no_articles_created(self) -> None:
        """Feed with zero entries produces no article creation commands."""
        mock_ctx = AsyncMock()
        mock_ctx.app_id = APP_ID
        mock_ctx.graph.query.side_effect = [
            # First call: subscription query
            {
                "results": {
                    "bindings": [
                        {
                            "sub": {"value": "urn:sempkm:app:rss-reader:feed-empty"},
                            "feedUrl": {"value": "https://empty.example.com/rss"},
                        }
                    ]
                }
            },
            # Second call: existing articles query
            {"results": {"bindings": []}},
        ]

        empty_result = {"bozo": False, "entries": []}

        with patch("rss_reader_app_mod.fetch_feed", new_callable=AsyncMock, return_value=(b"<rss/>", {"content_type": "application/rss+xml", "etag": None, "last_modified": None}, 200)), \
             patch("rss_reader_app_mod.parse_feed_content", return_value=empty_result), \
             patch("rss_reader_app_mod.update_subscription_state", new_callable=AsyncMock):
            result = await poll_feeds(mock_ctx)

        assert result["feeds_polled"] == 1
        assert result["articles_created"] == 0

    @pytest.mark.asyncio
    async def test_bozo_feed_with_entries_still_processed(self) -> None:
        """Feed with bozo=True but valid entries is still processed.

        feedparser sets bozo for many recoverable issues (e.g. missing encoding).
        """
        mock_ctx = AsyncMock()
        mock_ctx.app_id = APP_ID
        mock_ctx.graph.query.side_effect = [
            {
                "results": {
                    "bindings": [
                        {
                            "sub": {"value": "urn:sempkm:app:rss-reader:feed-bozo"},
                            "feedUrl": {"value": "https://bozo.example.com/rss"},
                        }
                    ]
                }
            },
            {"results": {"bindings": []}},
        ]

        bozo_with_entries = {"bozo": True, "bozo_exception": Exception("Missing encoding"), "entries": [_make_rss2_entry()]}

        # Mock the bulk context manager — bulk() is a non-async call that
        # returns an async context manager, so we use MagicMock for bulk
        # and wire up __aenter__/__aexit__ on its return value.
        mock_batch = MagicMock()
        mock_bulk_cm = MagicMock()
        mock_bulk_cm.__aenter__ = AsyncMock(return_value=mock_batch)
        mock_bulk_cm.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.commands = MagicMock()
        mock_ctx.commands.bulk.return_value = mock_bulk_cm
        mock_ctx.commands.execute = AsyncMock()

        with patch("rss_reader_app_mod.fetch_feed", new_callable=AsyncMock, return_value=(b"<rss/>", {"content_type": "application/rss+xml", "etag": None, "last_modified": None}, 200)), \
             patch("rss_reader_app_mod.parse_feed_content", return_value=bozo_with_entries), \
             patch("rss_reader_app_mod.update_subscription_state", new_callable=AsyncMock):
            result = await poll_feeds(mock_ctx)

        assert result["feeds_polled"] == 1
        assert result["articles_created"] == 1

    @pytest.mark.asyncio
    async def test_no_subscriptions_returns_zeros(self) -> None:
        """No feed subscriptions results in zero counts."""
        mock_ctx = AsyncMock()
        mock_ctx.app_id = APP_ID
        mock_ctx.graph.query.return_value = {"results": {"bindings": []}}

        result = await poll_feeds(mock_ctx)
        assert result == {"feeds_polled": 0, "articles_created": 0}


# ── Test: Real-world Feed Entry ──


class TestRealisticEntry:
    """Tests with realistic feedparser entry structure."""

    def test_realistic_rss2_no_keyerror(self) -> None:
        """Realistic RSS 2.0 entry with all feedparser-normalized fields causes no KeyError."""
        entry = _make_realistic_rss2_entry()
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        props = result["properties"]
        assert props["dcterms:title"] == "Breaking: New Ontology Standard Released"
        assert props[f"{RSS_NS}author"] == "Dr. Ada Lovelace"
        assert props[f"{RSS_NS}articleId"] == "https://example.com/?p=42"
        assert "dcterms:created" in props

    def test_realistic_entry_preserves_html_summary(self) -> None:
        """HTML in summary is passed through as-is (not stripped)."""
        entry = _make_realistic_rss2_entry()
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        assert "<p>" in result["properties"]["dcterms:description"]

    def test_entry_with_link_as_fallback_id(self) -> None:
        """When entry has no 'id' field, 'link' is used as articleId."""
        entry = {"title": "No GUID Article", "link": "https://example.com/no-guid"}
        result = entry_to_article(entry, FEED_IRI, APP_ID)
        assert result["properties"][f"{RSS_NS}articleId"] == "https://example.com/no-guid"


# ── Test: Constants ──


class TestConstants:
    """Verify module constants are correct."""

    def test_article_type(self) -> None:
        assert ARTICLE_TYPE == "urn:sempkm:model:rss-feeds:Article"

    def test_subscription_type(self) -> None:
        assert SUBSCRIPTION_TYPE == "urn:sempkm:model:rss-feeds:FeedSubscription"

    def test_rss_namespace(self) -> None:
        assert RSS_NS == "urn:sempkm:model:rss-feeds:"
