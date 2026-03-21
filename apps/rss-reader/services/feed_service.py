"""Feed service — feed parsing, discovery, dispatch, HTTP fetching, content extraction, and subscription management.

Pure functions (no SDK dependency):
- ``parse_json_feed(content)`` — JSON Feed 1.1 → feedparser-compatible dict
- ``discover_feeds_from_html(html, base_url)`` — extract ``<link rel="alternate">`` feed URLs
- ``parse_feed_content(raw_bytes, content_type)`` — dispatch XML/JSON to the right parser
- ``mint_subscription_iri(feed_url)`` — deterministic IRI from feed URL

I/O boundary functions (require an http_client):
- ``fetch_feed(http_client, url, ...)`` — conditional GET with ETag/Last-Modified
- ``extract_article_content(http_client, url)`` — full article extraction via trafilatura

Subscription management (require SDK ctx):
- ``check_subscription_exists(graph_client, feed_url)`` — SPARQL check for existing sub
- ``subscribe(ctx, feed_url, title)`` — create FeedSubscription via object.create
- ``unsubscribe(ctx, subscription_iri)`` — soft-delete via object.patch
- ``update_subscription_state(ctx, sub_iri, ...)`` — persist poll state (etag, errors, etc.)

Exception:
- ``FeedFetchError`` — raised by ``fetch_feed()`` on HTTP 4xx/5xx responses
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import time
from html.parser import HTMLParser
from types import SimpleNamespace
from typing import Any
from urllib.parse import urljoin

import feedparser

try:
    import trafilatura

    HAS_TRAFILATURA = True
except ImportError:
    trafilatura = None  # type: ignore[assignment]
    HAS_TRAFILATURA = False

logger = logging.getLogger(__name__)

# ── Constants ──

SUBSCRIPTION_TYPE = "urn:sempkm:model:rss-feeds:FeedSubscription"
RSS_NS = "urn:sempkm:model:rss-feeds:"

# ── SPARQL queries ──

SUBSCRIPTIONS_WITH_STATE_SPARQL = f"""
SELECT ?sub ?feedUrl ?title ?etag ?lastModified WHERE {{
    ?sub a <{SUBSCRIPTION_TYPE}> .
    ?sub <{RSS_NS}feedUrl> ?feedUrl .
    OPTIONAL {{ ?sub <http://purl.org/dc/terms/title> ?title }}
    OPTIONAL {{ ?sub <{RSS_NS}etag> ?etag }}
    OPTIONAL {{ ?sub <{RSS_NS}lastModifiedHeader> ?lastModified }}
}}
"""


# ── Subscription management ──


def mint_subscription_iri(feed_url: str) -> str:
    """Mint a deterministic subscription IRI from a feed URL.

    Uses SHA-256 hash of the feed URL for dedup-friendly, deterministic IRIs.

    Args:
        feed_url: The feed URL to generate an IRI for.

    Returns:
        IRI string like ``urn:sempkm:app:rss-reader:sub-{hash}``.
    """
    digest = hashlib.sha256(feed_url.encode("utf-8")).hexdigest()
    return f"urn:sempkm:app:rss-reader:sub-{digest}"


async def check_subscription_exists(graph_client: Any, feed_url: str) -> str | None:
    """Check if a subscription for the given feed URL already exists.

    Args:
        graph_client: SDK GraphClient instance with SPARQL read access.
        feed_url: The feed URL to check.

    Returns:
        The subscription IRI if it exists, None otherwise.
    """
    sparql = f"""
    SELECT ?sub WHERE {{
        ?sub a <{SUBSCRIPTION_TYPE}> .
        ?sub <{RSS_NS}feedUrl> "{feed_url}" .
    }} LIMIT 1
    """
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if bindings:
        return bindings[0].get("sub", {}).get("value")
    return None


async def subscribe(ctx: Any, feed_url: str, title: str | None = None) -> dict:
    """Create a FeedSubscription for the given feed URL.

    Checks for duplicates first via SPARQL. If the subscription already
    exists, returns ``{"status": "duplicate", "iri": existing_iri}``.

    Args:
        ctx: SDK AppContext with ``commands`` and ``graph`` clients.
        feed_url: The feed URL to subscribe to.
        title: Optional human-readable title. Defaults to feed_url.

    Returns:
        Dict with ``status`` ("created" or "duplicate") and ``iri``.
    """
    existing = await check_subscription_exists(ctx.graph, feed_url)
    if existing:
        logger.info("Subscription already exists for %s: %s", feed_url, existing)
        return {"status": "duplicate", "iri": existing}

    iri = mint_subscription_iri(feed_url)
    properties = {
        f"{RSS_NS}feedUrl": feed_url,
        "dcterms:title": title or feed_url,
        f"{RSS_NS}errorCount": 0,
        f"{RSS_NS}lastError": "",
    }
    await ctx.commands.execute(
        "object.create",
        {"iri": iri, "type": SUBSCRIPTION_TYPE, "properties": properties},
    )
    logger.info("Created subscription for %s: %s", feed_url, iri)
    return {"status": "created", "iri": iri}


async def unsubscribe(ctx: Any, subscription_iri: str) -> dict:
    """Soft-delete a subscription by marking it inactive.

    Args:
        ctx: SDK AppContext with ``commands`` client.
        subscription_iri: IRI of the FeedSubscription to deactivate.

    Returns:
        Dict with ``status`` ("unsubscribed") and ``iri``.
    """
    await ctx.commands.execute(
        "object.patch",
        {"iri": subscription_iri, "properties": {f"{RSS_NS}isActive": False}},
    )
    logger.info("Unsubscribed (soft-delete): %s", subscription_iri)
    return {"status": "unsubscribed", "iri": subscription_iri}


async def update_subscription_state(
    ctx: Any,
    sub_iri: str,
    last_polled: str | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
    error_count: int | None = None,
    last_error: str | None = None,
) -> None:
    """Update subscription poll state (etag, lastPolled, error tracking).

    Builds an ``object.patch`` payload from non-None arguments. Skips the
    HTTP call entirely if all params are None.

    Args:
        ctx: SDK AppContext with ``commands`` client.
        sub_iri: IRI of the FeedSubscription to update.
        last_polled: ISO 8601 timestamp of last poll attempt.
        etag: ETag header value from the most recent fetch.
        last_modified: Last-Modified header value from the most recent fetch.
        error_count: Number of consecutive errors (0 on success).
        last_error: Error message string (empty string on success).
    """
    properties: dict[str, Any] = {}
    if last_polled is not None:
        properties[f"{RSS_NS}lastPolled"] = last_polled
    if etag is not None:
        properties[f"{RSS_NS}etag"] = etag
    if last_modified is not None:
        properties[f"{RSS_NS}lastModifiedHeader"] = last_modified
    if error_count is not None:
        properties[f"{RSS_NS}errorCount"] = error_count
    if last_error is not None:
        properties[f"{RSS_NS}lastError"] = last_error

    if not properties:
        logger.debug("update_subscription_state: all params None, skipping for %s", sub_iri)
        return

    await ctx.commands.execute(
        "object.patch",
        {"iri": sub_iri, "properties": properties},
    )
    logger.debug("Updated subscription state for %s: %s", sub_iri, list(properties.keys()))


# ── JSON Feed 1.1 parser ──


def parse_json_feed(content: str | bytes) -> dict:
    """Parse a JSON Feed 1.1 string into a feedparser-compatible dict.

    JSON Feed spec: top-level ``version``, ``title``, ``home_page_url``,
    ``feed_url``, ``items[]``.  Each item has ``id``, ``url``, ``title``,
    ``content_text``, ``content_html``, ``date_published``,
    ``authors[]`` (array of ``{name, url}``).

    Returns a dict with ``feed`` (title, link) and ``entries`` list.
    Each entry is a :class:`types.SimpleNamespace` with: ``id``,
    ``title``, ``link``, ``author``, ``summary``, ``published_parsed``.

    On invalid JSON or missing ``items``, returns ``bozo=True`` with an
    empty entries list — matching feedparser's error convention.
    """
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            return {
                "feed": {},
                "entries": [],
                "bozo": True,
                "bozo_exception": exc,
            }

    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        return {
            "feed": {},
            "entries": [],
            "bozo": True,
            "bozo_exception": exc,
        }

    if not isinstance(data, dict) or "items" not in data:
        return {
            "feed": {},
            "entries": [],
            "bozo": True,
            "bozo_exception": ValueError("Missing 'items' key in JSON Feed"),
        }

    # Build the feed-level metadata
    feed_meta: dict[str, Any] = {}
    if "title" in data:
        feed_meta["title"] = data["title"]
    if "home_page_url" in data:
        feed_meta["link"] = data["home_page_url"]
    if "feed_url" in data:
        feed_meta["href"] = data["feed_url"]

    entries: list[SimpleNamespace] = []
    for item in data["items"]:
        entry = SimpleNamespace()

        entry.id = item.get("id", "")
        entry.title = item.get("title", "")
        entry.link = item.get("url", "")

        # Author: JSON Feed uses authors[] array of {name, url}
        authors = item.get("authors", [])
        if authors and isinstance(authors, list) and len(authors) > 0:
            entry.author = authors[0].get("name", "")
        elif "author" in item and isinstance(item["author"], dict):
            # Legacy JSON Feed 1.0 single author object
            entry.author = item["author"].get("name", "")
        else:
            entry.author = ""

        # Summary: prefer content_text, fall back to content_html truncated
        content_text = item.get("content_text", "")
        content_html = item.get("content_html", "")
        summary_field = item.get("summary", "")

        if content_text:
            entry.summary = content_text
        elif summary_field:
            entry.summary = summary_field
        elif content_html:
            # Truncate HTML to 500 chars for summary purposes
            entry.summary = content_html[:500]
        else:
            entry.summary = ""

        # Parse date_published (ISO 8601) to time.struct_time
        date_str = item.get("date_published", "")
        entry.published_parsed = _parse_iso8601_to_struct_time(date_str)

        entries.append(entry)

    return {
        "feed": feed_meta,
        "entries": entries,
        "bozo": False,
        "bozo_exception": None,
    }


def _parse_iso8601_to_struct_time(date_str: str) -> time.struct_time | None:
    """Parse an ISO 8601 date string to a ``time.struct_time``.

    Handles common ISO 8601 formats:
    - ``2025-03-15T10:30:00Z``
    - ``2025-03-15T10:30:00+00:00``
    - ``2025-03-15T10:30:00``

    Returns ``None`` if parsing fails or the input is empty.
    """
    if not date_str:
        return None

    # Normalize: strip trailing 'Z' → '+00:00'
    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"

    # Try multiple format patterns
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",       # with timezone offset
        "%Y-%m-%dT%H:%M:%S.%f%z",    # with fractional seconds + tz
        "%Y-%m-%dT%H:%M:%S",         # naive (no tz)
        "%Y-%m-%dT%H:%M:%S.%f",      # fractional seconds, no tz
    ]
    for fmt in formats:
        try:
            dt = time.strptime(date_str, fmt)
            return dt
        except ValueError:
            continue

    return None


# ── Feed discovery from HTML ──


class _FeedLinkParser(HTMLParser):
    """HTMLParser subclass that extracts ``<link rel="alternate">`` feed tags."""

    FEED_TYPES = frozenset({
        "application/rss+xml",
        "application/atom+xml",
        "application/feed+json",
        "application/json",
    })

    def __init__(self) -> None:
        super().__init__()
        self.feeds: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return

        attr_dict: dict[str, str] = {}
        for name, value in attrs:
            if value is not None:
                attr_dict[name.lower()] = value

        rel = attr_dict.get("rel", "").lower()
        link_type = attr_dict.get("type", "").lower()
        href = attr_dict.get("href", "")

        if rel == "alternate" and link_type in self.FEED_TYPES and href:
            self.feeds.append({
                "url": href,
                "title": attr_dict.get("title", ""),
                "type": link_type,
            })


def discover_feeds_from_html(html: str, base_url: str) -> list[dict]:
    """Extract feed URLs from ``<link rel="alternate">`` tags in HTML.

    Parses HTML looking for ``<link rel="alternate" type="..." href="...">``
    tags where type is one of: ``application/rss+xml``,
    ``application/atom+xml``, ``application/feed+json``,
    ``application/json``.

    Relative hrefs are resolved against *base_url* using
    :func:`urllib.parse.urljoin`.

    Args:
        html: Raw HTML string to parse.
        base_url: Base URL for resolving relative hrefs.

    Returns:
        List of dicts ``[{"url": ..., "title": ..., "type": ...}]``.
        Empty list if no feeds found.
    """
    parser = _FeedLinkParser()
    try:
        parser.feed(html)
    except Exception:
        return []

    # Resolve relative URLs
    for feed in parser.feeds:
        feed["url"] = urljoin(base_url, feed["url"])

    return parser.feeds


# ── Content-type dispatch ──


def parse_feed_content(raw_bytes: bytes, content_type: str) -> dict:
    """Parse feed content, dispatching by content type.

    If *content_type* contains ``json`` (e.g. ``application/json``,
    ``application/feed+json``), decodes and passes to
    :func:`parse_json_feed`.

    Otherwise (XML-based content types like ``application/rss+xml``,
    ``application/atom+xml``, ``text/xml``, or anything else), passes
    to ``feedparser.parse(io.BytesIO(raw_bytes))``.

    Args:
        raw_bytes: Raw bytes of the feed content.
        content_type: HTTP Content-Type header value.

    Returns:
        Normalized feedparser-compatible dict with ``feed``, ``entries``,
        ``bozo``, and ``bozo_exception`` keys.
    """
    ct_lower = content_type.lower() if content_type else ""

    if "json" in ct_lower:
        return parse_json_feed(raw_bytes)
    else:
        return feedparser.parse(io.BytesIO(raw_bytes))


# ── Exceptions ──


class FeedFetchError(Exception):
    """Raised by :func:`fetch_feed` on HTTP error responses (4xx/5xx).

    Attributes:
        url: The feed URL that returned an error.
        status_code: The HTTP status code received.
    """

    def __init__(self, url: str, status_code: int) -> None:
        self.url = url
        self.status_code = status_code
        super().__init__(f"Feed fetch failed: HTTP {status_code} for {url}")


# ── HTTP fetching with conditional GET ──


async def fetch_feed(
    http_client: Any,
    url: str,
    etag: str | None = None,
    last_modified: str | None = None,
) -> tuple[bytes | None, dict, int]:
    """Fetch a feed URL using conditional GET (ETag / Last-Modified).

    Sends ``If-None-Match`` and ``If-Modified-Since`` headers when the
    caller provides cached *etag* / *last_modified* values.

    Args:
        http_client: An object with an async ``.get(url, **kwargs)`` method
            returning an httpx-compatible response (e.g. SDK HttpClient).
        url: Feed URL to fetch.
        etag: Previously received ``ETag`` header value.
        last_modified: Previously received ``Last-Modified`` header value.

    Returns:
        A 3-tuple ``(content, headers, status_code)`` where:

        - *content* is ``bytes`` on HTTP 200, or ``None`` on HTTP 304
          (not modified — caller should skip parsing).
        - *headers* is a plain dict with keys ``etag``, ``last_modified``,
          ``content_type`` extracted from the response.
        - *status_code* is the integer HTTP status.

    Raises:
        FeedFetchError: On HTTP 4xx/5xx error responses.
    """
    headers: dict[str, str] = {}
    if etag is not None:
        headers["If-None-Match"] = etag
    if last_modified is not None:
        headers["If-Modified-Since"] = last_modified

    response = await http_client.get(url, headers=headers, follow_redirects=True)

    # Extract relevant response headers into a clean dict
    resp_headers = {
        "etag": response.headers.get("etag"),
        "last_modified": response.headers.get("last-modified"),
        "content_type": response.headers.get("content-type", ""),
    }

    if response.status_code == 304:
        logger.info("Conditional GET hit (304 Not Modified): %s", url)
        return (None, resp_headers, 304)

    if response.status_code >= 400:
        logger.warning(
            "Feed fetch error: HTTP %d for %s", response.status_code, url
        )
        raise FeedFetchError(url, response.status_code)

    logger.info("Feed fetched (HTTP %d): %s", response.status_code, url)
    return (response.content, resp_headers, response.status_code)


# ── Article content extraction via trafilatura ──


async def extract_article_content(http_client: Any, url: str) -> str | None:
    """Extract article body as markdown using trafilatura.

    Fetches the article URL and extracts the main content as markdown
    with links preserved.  Returns ``None`` gracefully if trafilatura
    is not installed, the HTTP fetch fails, or extraction produces no
    output.

    Args:
        http_client: An object with an async ``.get(url, **kwargs)`` method.
        url: Article URL to fetch and extract.

    Returns:
        Extracted markdown string, or ``None`` on any failure.
    """
    if not HAS_TRAFILATURA:
        logger.debug("trafilatura not installed — skipping extraction for %s", url)
        return None

    try:
        response = await http_client.get(url, follow_redirects=True)
        if response.status_code != 200:
            logger.warning(
                "Article fetch failed (HTTP %d): %s", response.status_code, url
            )
            return None

        result = trafilatura.extract(
            response.text, output_format="markdown", include_links=True
        )
        if result:
            logger.debug(
                "Extracted %d chars from %s", len(result), url
            )
        else:
            logger.warning("trafilatura extraction returned None for %s", url)
        return result
    except Exception as exc:
        logger.warning(
            "Article extraction failed for %s: %s", url, type(exc).__name__
        )
        return None
