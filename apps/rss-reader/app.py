"""RSS Reader application — polls RSS/Atom feeds and creates Article objects.

Registers:
- 4 fragment routes (reader page, unread view, starred view, subscribe dialog)
- 1 scheduled task (poll-feeds)
- 2 lifecycle hooks (startup, shutdown)

Helper functions (entry_to_article, parse_feed, get_existing_article_iris)
are standalone and importable by test files.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from time import mktime, struct_time
from typing import Any
from urllib.parse import quote

import feedparser

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse

try:
    from services.feed_service import (
        FeedFetchError,
        SUBSCRIPTIONS_WITH_STATE_SPARQL,
        discover_feeds_from_html,
        fetch_feed,
        parse_feed_content,
        subscribe,
        unsubscribe,
        update_subscription_state,
    )
except ModuleNotFoundError:
    # When loaded via importlib.util.spec_from_file_location (test context),
    # the relative 'services' package isn't on sys.path.  Fall back to
    # resolving the file path relative to this module's location.
    import importlib.util as _ilu
    import pathlib as _pl

    _svc = _pl.Path(__file__).resolve().parent / "services" / "feed_service.py"
    _sp = _ilu.spec_from_file_location("_feed_service_fallback", _svc)
    _fm = _ilu.module_from_spec(_sp)
    _sp.loader.exec_module(_fm)
    FeedFetchError = _fm.FeedFetchError
    SUBSCRIPTIONS_WITH_STATE_SPARQL = _fm.SUBSCRIPTIONS_WITH_STATE_SPARQL
    discover_feeds_from_html = _fm.discover_feeds_from_html
    fetch_feed = _fm.fetch_feed
    parse_feed_content = _fm.parse_feed_content
    subscribe = _fm.subscribe
    unsubscribe = _fm.unsubscribe
    update_subscription_state = _fm.update_subscription_state

try:
    from services.opml_parser import parse_opml
except (ModuleNotFoundError, ImportError):
    import importlib.util as _ilu2
    import pathlib as _pl2

    _op_path = _pl2.Path(__file__).resolve().parent / "services" / "opml_parser.py"
    _op_spec = _ilu2.spec_from_file_location("_opml_parser_fallback", str(_op_path))
    _op_mod = _ilu2.module_from_spec(_op_spec)
    _op_spec.loader.exec_module(_op_mod)
    parse_opml = _op_mod.parse_opml

logger = logging.getLogger(__name__)

# ── Constants ──

ARTICLE_TYPE = "urn:sempkm:model:rss-feeds:Article"
SUBSCRIPTION_TYPE = "urn:sempkm:model:rss-feeds:FeedSubscription"
RSS_NS = "urn:sempkm:model:rss-feeds:"

MAX_INITIAL_ARTICLES = 50
"""Cap on articles created per feed per poll cycle.

Prevents a first-time import of a prolific feed from flooding the store.
Feeds are typically reverse-chronological, so the first 50 entries are
the most recent.
"""

rss_reader_app = App("rss-reader")


# ── Pure helper functions (importable by tests) ──


def parse_feed(feed_url: str) -> dict:
    """Parse an RSS/Atom feed URL and return the feedparser result dict.

    .. deprecated::
        Use ``services.feed_service.fetch_feed()`` + ``parse_feed_content()``
        instead.  Kept for backward compatibility with S01 tests.

    Args:
        feed_url: URL of the RSS or Atom feed.

    Returns:
        feedparser result dict with 'entries', 'feed', 'bozo', etc.
    """
    return feedparser.parse(feed_url)


def _struct_time_to_iso(t: struct_time | None) -> str | None:
    """Convert a feedparser struct_time to an ISO 8601 datetime string.

    Returns None if the input is None or conversion fails.
    """
    if t is None:
        return None
    try:
        dt = datetime.fromtimestamp(mktime(t), tz=timezone.utc)
        return dt.isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def _mint_article_iri(feed_url: str, entry_id: str, app_id: str = "rss-reader") -> str:
    """Mint a deterministic article IRI from feed URL + entry ID.

    Uses SHA-256 hash of (feed_url + entry_id) for dedup-friendly,
    deterministic IRIs scoped to the app namespace.

    Args:
        feed_url: The source feed URL.
        entry_id: The entry's unique identifier (entry.id or entry.link).
        app_id: Application ID for the IRI namespace.

    Returns:
        IRI string like ``urn:sempkm:app:rss-reader:article-{hash}``.
    """
    raw = feed_url + entry_id
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"urn:sempkm:app:{app_id}:article-{digest}"


def entry_to_article(entry: dict, feed_iri: str, app_id: str = "rss-reader") -> dict:
    """Convert a feedparser entry to an article params dict for object.create.

    This is a pure function with no SDK dependency — suitable for unit testing.

    Args:
        entry: A single feedparser entry dict.
        feed_iri: IRI of the source FeedSubscription object.
        app_id: Application ID for IRI minting.

    Returns:
        Dict with ``iri``, ``type``, and ``properties`` keys suitable
        for passing to ``CommandClient.execute("object.create", ...)``.
    """
    # Determine unique entry ID (prefer entry.id, fall back to entry.link)
    entry_id = entry.get("id") or entry.get("link") or ""
    feed_url = entry.get("link", "")  # used as part of hash input if no id

    # For hash: use the source feed IRI + entry_id for stable dedup
    article_iri = _mint_article_iri(feed_iri, entry_id, app_id)

    # Map feedparser fields to RDF properties
    properties: dict[str, Any] = {}

    title = entry.get("title")
    if title:
        properties["dcterms:title"] = title

    link = entry.get("link")
    if link:
        properties[f"{RSS_NS}link"] = link

    author = entry.get("author")
    if author:
        properties[f"{RSS_NS}author"] = author

    published = _struct_time_to_iso(entry.get("published_parsed"))
    if published:
        properties["dcterms:created"] = published

    summary = entry.get("summary")
    if summary:
        properties["dcterms:description"] = summary

    # Link to source feed subscription
    properties[f"{RSS_NS}feedSource"] = feed_iri

    # Store entry ID for dedup reference
    raw_entry_id = entry.get("id") or entry.get("link")
    if raw_entry_id:
        properties[f"{RSS_NS}articleId"] = raw_entry_id

    # Default read status
    properties[f"{RSS_NS}isRead"] = False
    properties[f"{RSS_NS}isStarred"] = False

    return {
        "iri": article_iri,
        "type": ARTICLE_TYPE,
        "properties": properties,
    }


async def get_existing_article_iris(graph_client: Any, feed_iri: str) -> set[str]:
    """Query the triplestore for existing article IRIs from a given feed.

    Used for deduplication — returns the set of article IRIs already
    created for this feed subscription so we can skip them.

    Args:
        graph_client: SDK GraphClient instance with SPARQL read access.
        feed_iri: IRI of the FeedSubscription to check articles for.

    Returns:
        Set of article IRI strings already in the triplestore.
    """
    sparql = f"""
        SELECT ?article WHERE {{
            ?article a <{ARTICLE_TYPE}> .
            ?article <{RSS_NS}feedSource> <{feed_iri}> .
        }}
    """
    result = await graph_client.query(sparql)

    iris: set[str] = set()
    bindings = result.get("results", {}).get("bindings", [])
    for binding in bindings:
        article = binding.get("article", {})
        value = article.get("value")
        if value:
            iris.add(value)
    return iris


# ── Task handler ──


@rss_reader_app.task("poll-feeds")
async def poll_feeds(ctx: AppContext) -> dict:
    """Poll all subscribed RSS/Atom feeds and create new Article objects.

    Uses ``FeedService.fetch_feed()`` with conditional GET (ETag/Last-Modified)
    and ``parse_feed_content()`` for format dispatch. Updates subscription
    state (lastPolled, etag, errorCount, lastError) after each feed.

    Returns:
        Summary dict with feeds_polled and articles_created counts.
    """
    # Query all FeedSubscription objects with conditional GET state
    result = await ctx.graph.query(SUBSCRIPTIONS_WITH_STATE_SPARQL)
    bindings = result.get("results", {}).get("bindings", [])

    feeds_polled = 0
    articles_created = 0

    for binding in bindings:
        sub_iri = binding.get("sub", {}).get("value", "")
        feed_url = binding.get("feedUrl", {}).get("value", "")

        if not feed_url:
            logger.warning("FeedSubscription %s has no feedUrl, skipping", sub_iri)
            continue

        # Extract conditional GET headers from SPARQL results
        etag = binding.get("etag", {}).get("value") if "etag" in binding else None
        last_mod = binding.get("lastModified", {}).get("value") if "lastModified" in binding else None

        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            # Fetch via FeedService with conditional GET
            content, headers, status = await fetch_feed(
                ctx.http, feed_url, etag=etag, last_modified=last_mod
            )

            if status == 304:
                logger.info("304 Not Modified: %s", feed_url)
                await update_subscription_state(ctx, sub_iri, last_polled=now_iso)
                feeds_polled += 1
                continue

            logger.info("Fetched %s: %d bytes", feed_url, len(content) if content else 0)

            # Parse the feed content using format dispatch
            parsed = parse_feed_content(content, headers.get("content_type", ""))
            if parsed.get("bozo") and not parsed.get("entries"):
                logger.warning(
                    "Feed parse error for %s: %s",
                    feed_url,
                    parsed.get("bozo_exception"),
                )
                await update_subscription_state(
                    ctx, sub_iri,
                    last_polled=now_iso,
                    error_count=1,
                    last_error=str(parsed.get("bozo_exception", "Parse error")),
                )
                continue

            # Get existing articles for dedup
            existing_iris = await get_existing_article_iris(ctx.graph, sub_iri)

            # Build list of new articles — attach _feed_url for downstream use
            new_articles = []
            for entry in parsed.get("entries", []):
                # Convert SimpleNamespace entries (JSON Feed) to dict for entry_to_article
                if hasattr(entry, "__dict__") and not isinstance(entry, dict):
                    entry_dict = vars(entry)
                else:
                    entry_dict = entry
                article = entry_to_article(entry_dict, sub_iri, ctx.app_id)
                if article["iri"] not in existing_iris:
                    new_articles.append(article)

            # Cap initial imports to MAX_INITIAL_ARTICLES
            if len(new_articles) > MAX_INITIAL_ARTICLES:
                logger.info(
                    "Capping %d new articles to %d for %s",
                    len(new_articles), MAX_INITIAL_ARTICLES, feed_url,
                )
                new_articles = new_articles[:MAX_INITIAL_ARTICLES]

            # Bulk-create new articles
            if new_articles:
                async with ctx.commands.bulk(
                    summary=f"Poll feed: {feed_url}",
                    source=ctx.app_id,
                ) as batch:
                    for article in new_articles:
                        batch.add("object.create", article)

            feeds_polled += 1
            created_count = len(new_articles)
            articles_created += created_count
            logger.info(
                "Polled %s: %d new articles (skipped %d existing)",
                feed_url,
                created_count,
                len(parsed.get("entries", [])) - created_count,
            )

            # Success: reset error state, persist etag + lastPolled
            await update_subscription_state(
                ctx, sub_iri,
                last_polled=now_iso,
                etag=headers.get("etag"),
                last_modified=headers.get("last_modified"),
                error_count=0,
                last_error="",
            )

        except FeedFetchError as e:
            logger.warning("Feed error for %s: %s", feed_url, e)
            # Increment error count
            current_error_count = _get_current_error_count(binding)
            await update_subscription_state(
                ctx, sub_iri,
                last_polled=now_iso,
                error_count=current_error_count + 1,
                last_error=str(e),
            )
        except Exception as e:
            logger.exception("Error polling feed %s", feed_url)
            current_error_count = _get_current_error_count(binding)
            await update_subscription_state(
                ctx, sub_iri,
                last_polled=now_iso,
                error_count=current_error_count + 1,
                last_error=str(e),
            )

    logger.info(
        "poll-feeds complete: %d feeds polled, %d articles created",
        feeds_polled,
        articles_created,
    )
    return {"feeds_polled": feeds_polled, "articles_created": articles_created}


def _get_current_error_count(binding: dict) -> int:
    """Extract errorCount from a SPARQL binding, defaulting to 0."""
    try:
        return int(binding.get("errorCount", {}).get("value", 0))
    except (ValueError, TypeError, AttributeError):
        return 0


# ── Fragment routes (stubs — S03 builds the real UI) ──


@rss_reader_app.route("/_fragments/reader")
async def reader_fragment(request: Request):
    """Main reader page fragment."""
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("reader.html"))


@rss_reader_app.route("/_fragments/unread-view")
async def unread_view_fragment(request: Request):
    """Unread articles view fragment."""
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("unread-view.html"))


@rss_reader_app.route("/_fragments/starred-view")
async def starred_view_fragment(request: Request):
    """Starred articles view fragment."""
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("starred-view.html"))


@rss_reader_app.route("/_fragments/subscribe", methods=["POST"])
async def subscribe_route(request: Request):
    """Create a feed subscription from form data.

    Reads ``feed_url`` and optional ``title`` from the POST body.
    Returns an HTML fragment indicating success, duplicate, or error.
    On success, emits an ``HX-Trigger: feedsChanged`` header so the
    reader UI can refresh its feed list.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    feed_url = form.get("feed_url", "").strip()
    title = form.get("title", "").strip() or None

    if not feed_url:
        return HTMLResponse('<div class="rss-error">Please enter a feed URL</div>')

    try:
        result = await subscribe(ctx, feed_url, title=title)
    except Exception as exc:
        logger.warning("Subscribe failed for %s: %s", feed_url, exc)
        return HTMLResponse(
            f'<div class="rss-error">Failed: {exc}</div>'
        )

    if result["status"] == "duplicate":
        return HTMLResponse(
            '<div class="rss-info">Already subscribed to this feed</div>'
        )

    # status == "created"
    response = HTMLResponse(
        '<div class="rss-success">Subscribed to feed!</div>'
    )
    response.headers["HX-Trigger"] = "feedsChanged"
    return response


# ── OPML import ──


async def process_opml_import(ctx: AppContext, xml_bytes: bytes) -> dict:
    """Process OPML import: parse feeds and subscribe to each one.

    Returns a dict with counts and feed details:
        created, duplicate, errors — integer counts
        feeds — list of per-feed result dicts
    """
    feeds = parse_opml(xml_bytes)
    if not feeds:
        return {"created": 0, "duplicate": 0, "errors": 0, "feeds": []}

    created = 0
    duplicate = 0
    errors = 0
    results = []

    for entry in feeds:
        try:
            result = await subscribe(ctx, entry["url"], title=entry.get("title"))
            status = result["status"]

            if status == "created":
                created += 1
                # Patch bpkm:tags if the feed has a category
                if entry.get("category"):
                    try:
                        await ctx.commands.execute(
                            "object.patch",
                            {
                                "iri": result["iri"],
                                "properties": {
                                    "https://bpkm.org/ontology/tags": entry["category"],
                                },
                            },
                        )
                    except Exception as exc:
                        logger.warning(
                            "Failed to patch tags for %s: %s", entry["url"], exc
                        )
            elif status == "duplicate":
                duplicate += 1

            results.append({"url": entry["url"], "status": status})

        except Exception as exc:
            logger.warning("OPML import subscribe error for %s: %s", entry["url"], exc)
            errors += 1
            results.append({"url": entry["url"], "status": "error", "error": str(exc)})

    return {"created": created, "duplicate": duplicate, "errors": errors, "feeds": results}


@rss_reader_app.route("/_fragments/opml-import-dialog")
async def opml_import_dialog_fragment(request: Request):
    """OPML import dialog — file upload form."""
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("opml-import.html"))


@rss_reader_app.route("/_fragments/import-opml", methods=["POST"])
async def import_opml_route(request: Request):
    """Import feeds from an uploaded OPML file.

    Reads the multipart file upload, parses OPML, subscribes to each feed
    sequentially, and returns an HTML summary fragment.  Emits
    ``HX-Trigger: feedsChanged`` on success so the sidebar refreshes.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    opml_file = form.get("opml_file")

    if not opml_file or not hasattr(opml_file, "read"):
        return HTMLResponse('<div class="rss-error">No OPML file uploaded</div>')

    content = await opml_file.read()

    if not content:
        return HTMLResponse('<div class="rss-error">No OPML file uploaded</div>')

    result = await process_opml_import(ctx, content)

    total = result["created"] + result["duplicate"] + result["errors"]
    if total == 0:
        return HTMLResponse(
            '<div class="rss-error">No feeds found in OPML file</div>'
        )

    msg = (
        f'Imported {result["created"]} feed{"s" if result["created"] != 1 else ""}'
        f' ({result["duplicate"]} already subscribed, {result["errors"]} error{"s" if result["errors"] != 1 else ""})'
    )
    html = (
        f'<div class="rss-success"'
        f' data-created="{result["created"]}"'
        f' data-duplicates="{result["duplicate"]}"'
        f' data-errors="{result["errors"]}">'
        f'{msg}</div>'
    )
    response = HTMLResponse(html)
    if result["created"] > 0 or result["duplicate"] > 0:
        response.headers["HX-Trigger"] = "feedsChanged"
    return response


@rss_reader_app.route("/_fragments/discover-feeds")
async def discover_feeds_route(request: Request):
    """Discover feeds from a website URL via HTML link tags.

    Reads ``url`` from the query string, fetches the page, and extracts
    ``<link rel="alternate">`` feed URLs.  Returns an HTML list of
    discovered feeds or an error/info fragment.
    """
    ctx = request.app.state.ctx
    url = (request.query_params.get("url") or request.query_params.get("feed_url") or "").strip()

    if not url:
        return HTMLResponse(
            '<div class="rss-error">Please enter a URL to discover feeds</div>'
        )

    try:
        response = await ctx.http.get(url, follow_redirects=True)
    except Exception as exc:
        logger.warning("Feed discovery fetch failed for %s: %s", url, exc)
        return HTMLResponse(
            f'<div class="rss-error">Could not fetch URL: {exc}</div>'
        )

    feeds = discover_feeds_from_html(response.text, url)

    if not feeds:
        return HTMLResponse(
            '<div class="rss-info">No feeds found at that URL</div>'
        )

    # Render discovered feeds as a list with pre-fill buttons
    items = []
    for feed in feeds:
        feed_title = feed.get("title") or feed["url"]
        feed_type = feed.get("type", "")
        items.append(
            f'<li>'
            f'<span class="rss-discovered-feed-title">{feed_title}</span> '
            f'<span class="rss-discovered-feed-type">({feed_type})</span> '
            f'<button type="button" class="btn btn-sm"'
            f' onclick="document.getElementById(\'feed-url-input\').value=\'{feed["url"]}\'">'
            f'Use this feed</button>'
            f'</li>'
        )
    html = (
        '<div class="rss-discovered-feeds">'
        f'<p>Found {len(feeds)} feed(s):</p>'
        f'<ul>{"".join(items)}</ul>'
        '</div>'
    )
    return HTMLResponse(html)


@rss_reader_app.route("/_fragments/subscribe-dialog")
async def subscribe_dialog_fragment(request: Request):
    """Subscribe to feed dialog fragment."""
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("subscribe-dialog.html"))


# ── Date formatting helper ──


def _format_date(iso_str: str | None) -> str:
    """Format an ISO 8601 datetime string to a human-readable date.

    Returns a string like "Mar 17, 2026" or empty string on failure.
    """
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return ""


# ── Reader navigation fragments ──


FEED_SIDEBAR_SPARQL = f"""
SELECT ?sub ?feedUrl ?title ?errorCount ?lastError (COUNT(?unread) AS ?unreadCount) WHERE {{
  ?sub a <{SUBSCRIPTION_TYPE}> .
  ?sub <{RSS_NS}feedUrl> ?feedUrl .
  OPTIONAL {{ ?sub <http://purl.org/dc/terms/title> ?title }}
  OPTIONAL {{ ?sub <{RSS_NS}errorCount> ?errorCount }}
  OPTIONAL {{ ?sub <{RSS_NS}lastError> ?lastError }}
  OPTIONAL {{
    ?unread a <{ARTICLE_TYPE}> .
    ?unread <{RSS_NS}feedSource> ?sub .
    ?unread <{RSS_NS}isRead> false .
  }}
}} GROUP BY ?sub ?feedUrl ?title ?errorCount ?lastError
"""


@rss_reader_app.route("/_fragments/feed-sidebar")
async def feed_sidebar_fragment(request: Request):
    """Feed sidebar fragment — lists subscriptions with unread counts.

    SPARQL query fetches all FeedSubscription objects and counts their
    unread articles via a GROUP BY / COUNT pattern.  Returns an HTML
    fragment rendered from ``feed-sidebar.html``.
    """
    ctx = request.app.state.ctx
    try:
        result = await ctx.graph.query(FEED_SIDEBAR_SPARQL)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("feed-sidebar SPARQL failed: %s", exc)
        return HTMLResponse(
            '<div class="rss-error">Failed to load feeds</div>'
        )

    feeds = []
    for b in bindings:
        sub_iri = b.get("sub", {}).get("value", "")
        feed_url = b.get("feedUrl", {}).get("value", "")
        title = b.get("title", {}).get("value", "")
        error_count_raw = b.get("errorCount", {}).get("value", "0")
        last_error = b.get("lastError", {}).get("value", "")
        unread_raw = b.get("unreadCount", {}).get("value", "0")

        try:
            error_count = int(error_count_raw)
        except (ValueError, TypeError):
            error_count = 0
        try:
            unread_count = int(unread_raw)
        except (ValueError, TypeError):
            unread_count = 0

        feeds.append({
            "iri": sub_iri,
            "url": feed_url,
            "title": title or feed_url,
            "unread_count": unread_count,
            "error_count": error_count,
            "last_error": last_error,
        })

    return HTMLResponse(ctx.render_template(
        "feed-sidebar.html",
        feeds=feeds,
    ))


def _build_article_list_sparql(feed_iri: str | None, filter_mode: str) -> str:
    """Build a SPARQL query for the article list with optional filters.

    Args:
        feed_iri: If set, restrict to articles from this feed subscription.
        filter_mode: One of "all", "unread", "starred".

    Returns:
        SPARQL SELECT query string.
    """
    # Required filter triples injected into the WHERE body
    filter_clauses: list[str] = []
    if feed_iri:
        # Validate IRI to prevent injection — only allow URN/URL characters
        safe_iri = feed_iri.replace("\\", "").replace(">", "").replace("<", "")
        filter_clauses.append(f"FILTER(?sub = <{safe_iri}>)")
    if filter_mode == "unread":
        filter_clauses.append(
            f"?article <{RSS_NS}isRead> false ."
        )
    elif filter_mode == "starred":
        filter_clauses.append(
            f"?article <{RSS_NS}isStarred> true ."
        )

    filters_block = "\n      ".join(filter_clauses)

    return f"""
SELECT ?article ?title ?created ?isRead ?isStarred ?author ?feedTitle WHERE {{
  ?article a <{ARTICLE_TYPE}> .
  ?article <{RSS_NS}feedSource> ?sub .
  OPTIONAL {{ ?article <http://purl.org/dc/terms/title> ?title }}
  OPTIONAL {{ ?article <http://purl.org/dc/terms/created> ?created }}
  OPTIONAL {{ ?article <{RSS_NS}isRead> ?isRead }}
  OPTIONAL {{ ?article <{RSS_NS}isStarred> ?isStarred }}
  OPTIONAL {{ ?article <{RSS_NS}author> ?author }}
  OPTIONAL {{ ?sub <http://purl.org/dc/terms/title> ?feedTitle }}
  {filters_block}
}} ORDER BY DESC(?created) LIMIT 100
"""


@rss_reader_app.route("/_fragments/article-list")
async def article_list_fragment(request: Request):
    """Article list fragment — shows articles with optional feed/state filtering.

    Query params:
        feed_iri: Restrict to articles from a specific feed subscription.
        filter: One of "all" (default), "unread", "starred".

    Returns an HTML fragment rendered from ``article-list.html``.
    """
    ctx = request.app.state.ctx
    feed_iri = request.query_params.get("feed_iri", "").strip() or None
    filter_mode = request.query_params.get("filter", "all").strip()
    if filter_mode not in ("all", "unread", "starred"):
        filter_mode = "all"

    sparql = _build_article_list_sparql(feed_iri, filter_mode)

    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("article-list SPARQL failed: %s", exc)
        return HTMLResponse(
            '<div class="rss-error">Failed to load articles</div>'
        )

    articles = []
    for b in bindings:
        article_iri = b.get("article", {}).get("value", "")
        title = b.get("title", {}).get("value", "")
        created_raw = b.get("created", {}).get("value", "")
        is_read = b.get("isRead", {}).get("value", "false") == "true"
        is_starred = b.get("isStarred", {}).get("value", "false") == "true"
        author = b.get("author", {}).get("value", "")
        feed_title = b.get("feedTitle", {}).get("value", "")

        articles.append({
            "iri": article_iri,
            "title": title or "Untitled",
            "date": _format_date(created_raw),
            "is_read": is_read,
            "is_starred": is_starred,
            "author": author,
            "feed_title": feed_title,
        })

    return HTMLResponse(ctx.render_template(
        "article-list.html",
        articles=articles,
        active_feed=feed_iri,
        active_filter=filter_mode,
    ))


# ── Reading pane + action handlers ──


def _sanitize_iri(raw: str) -> str:
    """Strip angle brackets and backslashes from IRI to prevent SPARQL injection."""
    return raw.replace("\\", "").replace(">", "").replace("<", "")


@rss_reader_app.route("/_fragments/article-reading-pane")
async def article_reading_pane_fragment(request: Request):
    """Reading pane fragment — shows a single article with markdown body.

    Query params:
        article_iri: IRI of the article to display.

    Returns the empty-state placeholder if no article_iri is provided,
    or the full article reading pane with markdown body and fire-and-forget
    mark-read trigger.
    """
    ctx = request.app.state.ctx
    article_iri = request.query_params.get("article_iri", "").strip()

    if not article_iri:
        return HTMLResponse(
            '<div class="rss-reading-pane-empty"><p>Select an article to read</p></div>'
        )

    safe_iri = _sanitize_iri(article_iri)

    sparql = f"""
SELECT ?title ?link ?author ?created ?isStarred ?isRead ?body ?feedTitle ?description WHERE {{
  <{safe_iri}> a <{ARTICLE_TYPE}> .
  OPTIONAL {{ <{safe_iri}> <http://purl.org/dc/terms/title> ?title }}
  OPTIONAL {{ <{safe_iri}> <{RSS_NS}link> ?link }}
  OPTIONAL {{ <{safe_iri}> <{RSS_NS}author> ?author }}
  OPTIONAL {{ <{safe_iri}> <http://purl.org/dc/terms/created> ?created }}
  OPTIONAL {{ <{safe_iri}> <{RSS_NS}isStarred> ?isStarred }}
  OPTIONAL {{ <{safe_iri}> <{RSS_NS}isRead> ?isRead }}
  OPTIONAL {{ <{safe_iri}> <urn:sempkm:body> ?body }}
  OPTIONAL {{ <{safe_iri}> <http://purl.org/dc/terms/description> ?description }}
  OPTIONAL {{
    <{safe_iri}> <{RSS_NS}feedSource> ?sub .
    ?sub <http://purl.org/dc/terms/title> ?feedTitle .
  }}
}}
"""
    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("article-reading-pane SPARQL failed: %s", exc)
        return HTMLResponse(
            f'<div class="rss-error">Failed to load article: {exc}</div>'
        )

    if not bindings:
        return HTMLResponse(
            '<div class="rss-error">Article not found</div>'
        )

    b = bindings[0]
    is_starred = b.get("isStarred", {}).get("value", "false") == "true"
    is_read = b.get("isRead", {}).get("value", "false") == "true"
    body_raw = b.get("body", {}).get("value", "")
    description = b.get("description", {}).get("value", "")

    article = {
        "iri": safe_iri,
        "title": b.get("title", {}).get("value", ""),
        "link": b.get("link", {}).get("value", ""),
        "author": b.get("author", {}).get("value", ""),
        "date": _format_date(b.get("created", {}).get("value", "")),
        "feed_title": b.get("feedTitle", {}).get("value", ""),
        "is_starred": is_starred,
        "is_read": is_read,
    }

    # Determine body content: prefer full body, fall back to description
    body = body_raw or description or None

    # Generate a stable, short ID suffix for markdown source/target elements
    md_id = hashlib.sha256(safe_iri.encode("utf-8")).hexdigest()[:8]

    return HTMLResponse(ctx.render_template(
        "article-reading-pane.html",
        article=article,
        body=body,
        md_id=md_id,
        article_iri=safe_iri,
        is_starred=is_starred,
    ))


@rss_reader_app.route("/_fragments/toggle-star", methods=["POST"])
async def toggle_star_fragment(request: Request):
    """Toggle the starred state of an article.

    Reads ``article_iri`` from the POST body, queries the current isStarred
    value, flips it, and patches the object. Returns the updated star button
    HTML fragment for htmx outerHTML swap.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    article_iri = form.get("article_iri", "").strip()

    if not article_iri:
        return HTMLResponse(
            '<div class="rss-error">Missing article_iri</div>', status_code=400
        )

    safe_iri = _sanitize_iri(article_iri)

    # Query current star state
    sparql = f"""
SELECT ?val WHERE {{
  <{safe_iri}> <{RSS_NS}isStarred> ?val .
}}
"""
    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        current = bindings[0].get("val", {}).get("value", "false") if bindings else "false"
        new_value = current != "true"  # flip: "true" → False, anything else → True
    except Exception as exc:
        logger.warning("toggle-star SPARQL query failed: %s", exc)
        return HTMLResponse(
            f'<div class="rss-error">Failed to toggle star: {exc}</div>'
        )

    try:
        await ctx.commands.execute(
            "object.patch",
            {"iri": safe_iri, "properties": {f"{RSS_NS}isStarred": new_value}},
        )
    except Exception as exc:
        logger.warning("toggle-star patch failed: %s", exc)
        return HTMLResponse(
            f'<div class="rss-error">Failed to update star: {exc}</div>'
        )

    response = HTMLResponse(ctx.render_template(
        "star-button.html",
        article_iri=safe_iri,
        is_starred=new_value,
    ))
    response.headers["HX-Trigger"] = "articleStateChanged"
    return response


@rss_reader_app.route("/_fragments/toggle-read", methods=["POST"])
async def toggle_read_fragment(request: Request):
    """Mark an article as read (or toggle read state if ``toggle=true``).

    By default, sets isRead to true (fire-and-forget on article open).
    If the ``toggle`` form param is present and truthy, queries the
    current value and flips it.

    Returns empty body with ``HX-Trigger: articleStateChanged`` header.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    article_iri = form.get("article_iri", "").strip()

    if not article_iri:
        return HTMLResponse("", status_code=400)

    safe_iri = _sanitize_iri(article_iri)
    toggle = form.get("toggle", "").strip().lower() in ("true", "1", "yes")

    if toggle:
        # Query current read state and flip
        sparql = f"""
SELECT ?val WHERE {{
  <{safe_iri}> <{RSS_NS}isRead> ?val .
}}
"""
        try:
            result = await ctx.graph.query(sparql)
            bindings = result.get("results", {}).get("bindings", [])
            current = bindings[0].get("val", {}).get("value", "false") if bindings else "false"
            new_value = current != "true"
        except Exception as exc:
            logger.warning("toggle-read SPARQL query failed: %s", exc)
            return HTMLResponse("", status_code=500)
    else:
        new_value = True  # mark-as-read on article open

    try:
        await ctx.commands.execute(
            "object.patch",
            {"iri": safe_iri, "properties": {f"{RSS_NS}isRead": new_value}},
        )
    except Exception as exc:
        logger.warning("toggle-read patch failed: %s", exc)
        return HTMLResponse("", status_code=500)

    response = HTMLResponse("")
    response.headers["HX-Trigger"] = "articleStateChanged"
    return response


@rss_reader_app.route("/_fragments/mark-all-read", methods=["POST"])
async def mark_all_read_fragment(request: Request):
    """Mark all unread articles as read, optionally scoped to a feed.

    Reads ``feed_iri`` from the POST body (optional). If provided, only
    marks articles from that feed subscription. Otherwise marks all
    unread articles across all feeds.

    When called from the command palette (HX-Target: #modal-container),
    returns a confirmation message. Otherwise returns the updated feed
    sidebar fragment.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    feed_iri = form.get("feed_iri", "").strip() or None
    from_command_palette = request.headers.get("HX-Target") == "#modal-container"

    # Build SPARQL to find all unread article IRIs
    feed_filter = ""
    if feed_iri:
        safe_feed = _sanitize_iri(feed_iri)
        feed_filter = f"?article <{RSS_NS}feedSource> <{safe_feed}> ."

    sparql = f"""
SELECT ?article WHERE {{
  ?article a <{ARTICLE_TYPE}> .
  ?article <{RSS_NS}isRead> false .
  {feed_filter}
}}
"""
    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("mark-all-read SPARQL query failed: %s", exc)
        html = f'<div class="rss-error">Failed to find unread articles: {exc}</div>'
        return HTMLResponse(html)

    # Patch each unread article to isRead=true
    patched = 0
    for b in bindings:
        art_iri = b.get("article", {}).get("value", "")
        if not art_iri:
            continue
        try:
            await ctx.commands.execute(
                "object.patch",
                {"iri": art_iri, "properties": {f"{RSS_NS}isRead": True}},
            )
            patched += 1
        except Exception as exc:
            logger.warning("mark-all-read: failed to patch %s: %s", art_iri, exc)
            # Continue best-effort

    logger.info("mark-all-read: patched %d/%d articles", patched, len(bindings))

    # Command palette context: return confirmation message
    if from_command_palette:
        response = HTMLResponse(
            f'<div class="rss-success">Marked {patched} articles as read</div>'
        )
        response.headers["HX-Trigger"] = "articleStateChanged, feedsChanged"
        return response

    # Reader UI context: return updated feed sidebar
    try:
        sidebar_result = await ctx.graph.query(FEED_SIDEBAR_SPARQL)
        sidebar_bindings = sidebar_result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("mark-all-read: sidebar refresh SPARQL failed: %s", exc)
        return HTMLResponse(
            '<div class="rss-error">Articles marked read but sidebar refresh failed</div>'
        )

    feeds = []
    for sb in sidebar_bindings:
        sub_iri = sb.get("sub", {}).get("value", "")
        feed_url = sb.get("feedUrl", {}).get("value", "")
        title = sb.get("title", {}).get("value", "")
        error_count_raw = sb.get("errorCount", {}).get("value", "0")
        last_error = sb.get("lastError", {}).get("value", "")
        unread_raw = sb.get("unreadCount", {}).get("value", "0")
        try:
            error_count = int(error_count_raw)
        except (ValueError, TypeError):
            error_count = 0
        try:
            unread_count = int(unread_raw)
        except (ValueError, TypeError):
            unread_count = 0
        feeds.append({
            "iri": sub_iri,
            "url": feed_url,
            "title": title or feed_url,
            "unread_count": unread_count,
            "error_count": error_count,
            "last_error": last_error,
        })

    response = HTMLResponse(ctx.render_template("feed-sidebar.html", feeds=feeds))
    response.headers["HX-Trigger"] = "articleStateChanged"
    return response


@rss_reader_app.route("/_fragments/unsubscribe", methods=["POST"])
async def unsubscribe_fragment(request: Request):
    """Unsubscribe from a feed (soft-delete).

    Reads ``feed_iri`` from the POST body and calls
    ``feed_service.unsubscribe()`` to set isActive=False.

    Returns the updated feed sidebar fragment with ``HX-Trigger: feedsChanged``.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    feed_iri = form.get("feed_iri", "").strip()

    if not feed_iri:
        return HTMLResponse(
            '<div class="rss-error">Missing feed_iri</div>', status_code=400
        )

    try:
        await unsubscribe(ctx, feed_iri)
    except Exception as exc:
        logger.warning("Unsubscribe failed for %s: %s", feed_iri, exc)
        return HTMLResponse(
            f'<div class="rss-error">Failed to unsubscribe: {exc}</div>'
        )

    # Return updated feed sidebar
    try:
        sidebar_result = await ctx.graph.query(FEED_SIDEBAR_SPARQL)
        sidebar_bindings = sidebar_result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("unsubscribe: sidebar refresh SPARQL failed: %s", exc)
        return HTMLResponse(
            '<div class="rss-success">Unsubscribed, but sidebar refresh failed</div>'
        )

    feeds = []
    for sb in sidebar_bindings:
        sub_iri = sb.get("sub", {}).get("value", "")
        feed_url = sb.get("feedUrl", {}).get("value", "")
        title = sb.get("title", {}).get("value", "")
        error_count_raw = sb.get("errorCount", {}).get("value", "0")
        last_error = sb.get("lastError", {}).get("value", "")
        unread_raw = sb.get("unreadCount", {}).get("value", "0")
        try:
            error_count = int(error_count_raw)
        except (ValueError, TypeError):
            error_count = 0
        try:
            unread_count = int(unread_raw)
        except (ValueError, TypeError):
            unread_count = 0
        feeds.append({
            "iri": sub_iri,
            "url": feed_url,
            "title": title or feed_url,
            "unread_count": unread_count,
            "error_count": error_count,
            "last_error": last_error,
        })

    response = HTMLResponse(ctx.render_template("feed-sidebar.html", feeds=feeds))
    response.headers["HX-Trigger"] = "feedsChanged"
    return response


# ── Settings helpers (pure, testable) ──

SETTINGS_DEFAULTS = {
    "articlesPerPage": "50",
    "markReadOnOpen": "true",
}


async def get_settings_context(ctx: AppContext) -> dict:
    """Read current settings from ctx.settings, falling back to defaults.

    Returns:
        Dict with 'articles_per_page' and 'mark_read_on_open' string values.
    """
    articles_per_page = await ctx.settings.get("articlesPerPage")
    mark_read_on_open = await ctx.settings.get("markReadOnOpen")
    return {
        "articles_per_page": articles_per_page or SETTINGS_DEFAULTS["articlesPerPage"],
        "mark_read_on_open": mark_read_on_open or SETTINGS_DEFAULTS["markReadOnOpen"],
    }


def validate_articles_per_page(raw: str) -> str:
    """Validate and clamp articlesPerPage to [10, 200].

    Returns:
        A string representation of the clamped integer.
    """
    try:
        value = int(raw)
    except (ValueError, TypeError):
        return SETTINGS_DEFAULTS["articlesPerPage"]
    return str(max(10, min(200, value)))


async def save_settings(ctx: AppContext, form_data: dict) -> None:
    """Save settings from form data to ctx.settings.

    Args:
        form_data: Dict-like with 'articlesPerPage' and 'markReadOnOpen' keys.
    """
    articles_per_page = validate_articles_per_page(
        form_data.get("articlesPerPage", SETTINGS_DEFAULTS["articlesPerPage"])
    )
    mark_read_on_open = "true" if form_data.get("markReadOnOpen") else "false"
    await ctx.settings.set("articlesPerPage", articles_per_page)
    await ctx.settings.set("markReadOnOpen", mark_read_on_open)


@rss_reader_app.route("/_fragments/settings")
async def settings_get_fragment(request: Request):
    """Settings page — renders form with current or default values."""
    ctx = request.app.state.ctx
    try:
        settings_ctx = await get_settings_context(ctx)
    except Exception as exc:
        logger.warning("Settings read error: %s", exc)
        return HTMLResponse(
            f'<div class="rss-error">Failed to load settings: {exc}</div>'
        )
    return HTMLResponse(ctx.render_template("settings.html", **settings_ctx))


@rss_reader_app.route("/_fragments/settings", methods=["POST"])
async def settings_post_fragment(request: Request):
    """Save settings from form submission."""
    ctx = request.app.state.ctx
    form = await request.form()

    try:
        await save_settings(ctx, dict(form))
    except Exception as exc:
        logger.warning("Settings save error: %s", exc)
        return HTMLResponse(
            f'<div class="rss-error">Failed to save settings: {exc}</div>'
        )
    return HTMLResponse('<div class="rss-success">Settings saved</div>')


# ── Workspace contribution fragments ──

BPKM_TAGS = "urn:sempkm:model:basic-pkm:tags"


@rss_reader_app.route("/_fragments/related-articles")
async def related_articles_fragment(request: Request):
    """Right pane fragment — shows articles related to the focused object.

    Finds articles sharing the same feedSource or bpkm:tags as the focused IRI.
    Returns an HTML fragment rendered from ``related-articles.html``.

    Query params:
        iri: URL-encoded IRI of the focused object.
    """
    ctx = request.app.state.ctx
    iri = request.query_params.get("iri", "").strip()

    if not iri:
        return HTMLResponse(
            '<div class="rss-empty-state">No related articles found</div>'
        )

    safe_iri = _sanitize_iri(iri)

    # Find articles sharing the same feedSource or tags as the focused IRI,
    # excluding the focused IRI itself, limited to 10, newest first.
    sparql = f"""
SELECT DISTINCT ?article ?title ?created ?feedTitle WHERE {{
  {{
    # Same feed source
    <{safe_iri}> <{RSS_NS}feedSource> ?feed .
    ?article a <{ARTICLE_TYPE}> .
    ?article <{RSS_NS}feedSource> ?feed .
    FILTER(?article != <{safe_iri}>)
  }} UNION {{
    # Shared tags
    <{safe_iri}> <{BPKM_TAGS}> ?tag .
    ?article a <{ARTICLE_TYPE}> .
    ?article <{BPKM_TAGS}> ?tag .
    FILTER(?article != <{safe_iri}>)
  }}
  OPTIONAL {{ ?article <http://purl.org/dc/terms/title> ?title }}
  OPTIONAL {{ ?article <http://purl.org/dc/terms/created> ?created }}
  OPTIONAL {{
    ?article <{RSS_NS}feedSource> ?sub .
    ?sub <http://purl.org/dc/terms/title> ?feedTitle .
  }}
}} ORDER BY DESC(?created) LIMIT 10
"""

    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("related-articles SPARQL failed: %s", exc)
        return HTMLResponse(
            f'<div class="rss-error">Failed to load related articles: {exc}</div>'
        )

    articles = []
    for b in bindings:
        articles.append({
            "iri": b.get("article", {}).get("value", ""),
            "title": b.get("title", {}).get("value", "") or "Untitled",
            "date": _format_date(b.get("created", {}).get("value", "")),
            "feed_title": b.get("feedTitle", {}).get("value", ""),
        })

    return HTMLResponse(ctx.render_template(
        "related-articles.html",
        articles=articles,
    ))


@rss_reader_app.route("/_fragments/article-read-renderer")
async def article_read_renderer_fragment(request: Request):
    """Custom read renderer for rss:Article objects in the object browser.

    Reuses the same SPARQL query pattern as article_reading_pane_fragment()
    but does NOT include the fire-and-forget mark-read trigger (this is for
    the object browser, not the reader UI).

    Query params:
        iri: URL-encoded IRI of the Article to render.
    """
    ctx = request.app.state.ctx
    iri = request.query_params.get("iri", "").strip()

    if not iri:
        return HTMLResponse(
            '<div class="rss-reading-pane-empty"><p>No article specified</p></div>'
        )

    safe_iri = _sanitize_iri(iri)

    sparql = f"""
SELECT ?title ?link ?author ?created ?isStarred ?body ?feedTitle ?description WHERE {{
  <{safe_iri}> a <{ARTICLE_TYPE}> .
  OPTIONAL {{ <{safe_iri}> <http://purl.org/dc/terms/title> ?title }}
  OPTIONAL {{ <{safe_iri}> <{RSS_NS}link> ?link }}
  OPTIONAL {{ <{safe_iri}> <{RSS_NS}author> ?author }}
  OPTIONAL {{ <{safe_iri}> <http://purl.org/dc/terms/created> ?created }}
  OPTIONAL {{ <{safe_iri}> <{RSS_NS}isStarred> ?isStarred }}
  OPTIONAL {{ <{safe_iri}> <urn:sempkm:body> ?body }}
  OPTIONAL {{ <{safe_iri}> <http://purl.org/dc/terms/description> ?description }}
  OPTIONAL {{
    <{safe_iri}> <{RSS_NS}feedSource> ?sub .
    ?sub <http://purl.org/dc/terms/title> ?feedTitle .
  }}
}}
"""
    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("article-read-renderer SPARQL failed: %s", exc)
        return HTMLResponse(
            f'<div class="rss-error">Failed to load article: {exc}</div>'
        )

    if not bindings:
        return HTMLResponse(
            '<div class="rss-reading-pane-empty"><p>Article not found</p></div>'
        )

    b = bindings[0]
    is_starred = b.get("isStarred", {}).get("value", "false") == "true"
    body_raw = b.get("body", {}).get("value", "")
    description = b.get("description", {}).get("value", "")

    article = {
        "iri": safe_iri,
        "title": b.get("title", {}).get("value", ""),
        "link": b.get("link", {}).get("value", ""),
        "author": b.get("author", {}).get("value", ""),
        "date": _format_date(b.get("created", {}).get("value", "")),
        "feed_title": b.get("feedTitle", {}).get("value", ""),
        "is_starred": is_starred,
    }

    body = body_raw or description or None
    md_id = hashlib.sha256(safe_iri.encode("utf-8")).hexdigest()[:8]

    return HTMLResponse(ctx.render_template(
        "article-read-renderer.html",
        article=article,
        body=body,
        md_id=md_id,
        article_iri=safe_iri,
        is_starred=is_starred,
    ))


# ── Lifecycle hooks ──


@rss_reader_app.on_startup
def on_startup(ctx: AppContext):
    """Log app startup."""
    logger.info("RSS Reader app started: %s", ctx.app_id)


@rss_reader_app.on_shutdown
def on_shutdown(ctx: AppContext):
    """Log app shutdown."""
    logger.info("RSS Reader app stopped: %s", ctx.app_id)
