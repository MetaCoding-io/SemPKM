"""Media Scheduler application — podcast/YouTube/Spotify content scheduling.

Registers:
- 5 fragment routes (main page, sources list, add-podcast, remove source, items list)
- 1 scheduled task (poll-sources)
- Lifecycle hooks (startup, shutdown)

The poll-sources task handler queries all podcast MediaSource objects,
fetches their RSS feeds with conditional GET, parses episodes via
feedparser, deduplicates against existing MediaItems, and bulk-creates
new items. Source poll state (etag, errorCount, lastError) is updated
after each feed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse

try:
    from services.podcast_service import (
        MEDIA_ITEM_TYPE,
        MEDIA_SOURCE_TYPE,
        MS_NS,
        SOURCES_WITH_STATE_SPARQL,
        FeedFetchError,
        entry_to_media_item,
        fetch_feed,
        get_existing_item_iris,
        parse_feed_content,
        subscribe_podcast,
        unsubscribe_source,
        update_source_state,
    )
except ModuleNotFoundError:
    # When loaded via importlib.util.spec_from_file_location (test context),
    # the relative 'services' package isn't on sys.path.  Fall back to
    # resolving the file path relative to this module's location.
    import importlib.util as _ilu
    import pathlib as _pl

    _svc = _pl.Path(__file__).resolve().parent / "services" / "podcast_service.py"
    _sp = _ilu.spec_from_file_location("_podcast_service_fallback", _svc)
    _fm = _ilu.module_from_spec(_sp)
    _sp.loader.exec_module(_fm)
    MEDIA_ITEM_TYPE = _fm.MEDIA_ITEM_TYPE
    MEDIA_SOURCE_TYPE = _fm.MEDIA_SOURCE_TYPE
    MS_NS = _fm.MS_NS
    SOURCES_WITH_STATE_SPARQL = _fm.SOURCES_WITH_STATE_SPARQL
    FeedFetchError = _fm.FeedFetchError
    entry_to_media_item = _fm.entry_to_media_item
    fetch_feed = _fm.fetch_feed
    get_existing_item_iris = _fm.get_existing_item_iris
    parse_feed_content = _fm.parse_feed_content
    subscribe_podcast = _fm.subscribe_podcast
    unsubscribe_source = _fm.unsubscribe_source
    update_source_state = _fm.update_source_state

try:
    from services.plan_service import fetch_context, generate_plan
except ModuleNotFoundError:
    import importlib.util as _ilu2
    import pathlib as _pl2

    _plan_svc = _pl2.Path(__file__).resolve().parent / "services" / "plan_service.py"
    _plan_sp = _ilu2.spec_from_file_location("_plan_service_fallback", _plan_svc)
    _plan_fm = _ilu2.module_from_spec(_plan_sp)
    _plan_sp.loader.exec_module(_plan_fm)
    fetch_context = _plan_fm.fetch_context
    generate_plan = _plan_fm.generate_plan

logger = logging.getLogger(__name__)

media_scheduler_app = App("media-scheduler")

MAX_INITIAL_ITEMS = 50
"""Cap on MediaItems created per source per poll cycle.

Prevents a first-time import of a prolific podcast from flooding the store.
Podcast feeds are typically reverse-chronological, so the first 50 entries
are the most recent.
"""


# ── Task handler ──


def _get_current_error_count(binding: dict) -> int:
    """Extract errorCount from a SPARQL binding, defaulting to 0."""
    try:
        return int(binding.get("errorCount", {}).get("value", 0))
    except (ValueError, TypeError, AttributeError):
        return 0


@media_scheduler_app.task("poll-sources")
async def poll_sources(ctx: AppContext) -> dict:
    """Poll all podcast MediaSource objects and create new MediaItem objects.

    Uses conditional GET (ETag/Last-Modified) for efficient polling.
    Parses RSS feeds via feedparser (which handles iTunes namespace
    extensions for duration, enclosure, etc.). Deduplicates against
    existing MediaItems per source. Bulk-creates new items atomically.

    Updates source state (lastPolled, etag, errorCount, lastError) after
    every poll attempt. Feed-level errors don't block other feeds.

    Returns:
        Summary dict with feeds_polled and items_created counts,
        logged by the AppScheduler.
    """
    # Query all podcast-type MediaSource objects with conditional GET state
    result = await ctx.graph.query(SOURCES_WITH_STATE_SPARQL)
    bindings = result.get("results", {}).get("bindings", [])

    feeds_polled = 0
    items_created = 0

    for binding in bindings:
        source_iri = binding.get("source", {}).get("value", "")
        feed_url = binding.get("feedUrl", {}).get("value", "")

        if not feed_url:
            logger.warning("MediaSource %s has no feedUrl, skipping", source_iri)
            continue

        # Extract conditional GET headers from SPARQL results
        etag = binding.get("etag", {}).get("value") if "etag" in binding else None
        last_mod = (
            binding.get("lastModified", {}).get("value")
            if "lastModified" in binding
            else None
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            # Fetch via conditional GET
            content, headers, status = await fetch_feed(
                ctx.http, feed_url, etag=etag, last_modified=last_mod
            )

            if status == 304:
                logger.info("304 Not Modified: %s", feed_url)
                await update_source_state(ctx, source_iri, last_polled=now_iso)
                feeds_polled += 1
                continue

            logger.info(
                "Fetched %s: %d bytes",
                feed_url,
                len(content) if content else 0,
            )

            # Parse the feed content
            parsed = parse_feed_content(
                content, headers.get("content_type", "")
            )
            if parsed.get("bozo") and not parsed.get("entries"):
                logger.warning(
                    "Feed parse error for %s: %s",
                    feed_url,
                    parsed.get("bozo_exception"),
                )
                current_error_count = _get_current_error_count(binding)
                await update_source_state(
                    ctx,
                    source_iri,
                    last_polled=now_iso,
                    error_count=current_error_count + 1,
                    last_error=str(
                        parsed.get("bozo_exception", "Parse error")
                    ),
                )
                continue

            # Get existing item IRIs for dedup
            existing_iris = await get_existing_item_iris(
                ctx.graph, source_iri
            )

            # Build list of new MediaItems
            new_items = []
            for entry in parsed.get("entries", []):
                # Convert SimpleNamespace entries to dict if needed
                if hasattr(entry, "__dict__") and not isinstance(entry, dict):
                    entry_dict = vars(entry)
                else:
                    entry_dict = entry
                item = entry_to_media_item(entry_dict, source_iri)
                if item["iri"] not in existing_iris:
                    new_items.append(item)

            # Cap initial imports
            if len(new_items) > MAX_INITIAL_ITEMS:
                logger.info(
                    "Capping %d new items to %d for %s",
                    len(new_items),
                    MAX_INITIAL_ITEMS,
                    feed_url,
                )
                new_items = new_items[:MAX_INITIAL_ITEMS]

            # Bulk-create new items
            if new_items:
                async with ctx.commands.bulk(
                    summary=f"Poll podcast: {feed_url}",
                    source=ctx.app_id,
                ) as batch:
                    for item in new_items:
                        batch.add("object.create", item)

            feeds_polled += 1
            created_count = len(new_items)
            items_created += created_count
            logger.info(
                "Polled %s: %d new items (skipped %d existing)",
                feed_url,
                created_count,
                len(parsed.get("entries", [])) - created_count,
            )

            # Success: reset error state, persist etag + lastPolled
            await update_source_state(
                ctx,
                source_iri,
                last_polled=now_iso,
                etag=headers.get("etag"),
                last_modified=headers.get("last_modified"),
                error_count=0,
                last_error="",
            )

        except FeedFetchError as e:
            logger.warning("Feed error for %s: %s", feed_url, e)
            current_error_count = _get_current_error_count(binding)
            await update_source_state(
                ctx,
                source_iri,
                last_polled=now_iso,
                error_count=current_error_count + 1,
                last_error=str(e),
            )
        except Exception as e:
            logger.exception("Error polling feed %s", feed_url)
            current_error_count = _get_current_error_count(binding)
            await update_source_state(
                ctx,
                source_iri,
                last_polled=now_iso,
                error_count=current_error_count + 1,
                last_error=str(e),
            )

    logger.info(
        "poll-sources complete: %d feeds polled, %d items created",
        feeds_polled,
        items_created,
    )
    return {"feeds_polled": feeds_polled, "items_created": items_created}


@media_scheduler_app.task("generate-plan")
async def generate_plan_task(ctx: AppContext) -> dict:
    """Generate a daily media plan based on schedule rules and current context.

    Delegates to ``plan_service.generate_plan()`` which orchestrates:
    rules evaluation → item selection → slot allocation → RDF creation.

    Returns:
        Summary dict with plan_iri, date, rules_matched, entries_created.
    """
    return await generate_plan(ctx)


# ── Helper ──


def _sanitize_iri(raw: str) -> str:
    """Strip angle brackets and backslashes from IRI to prevent SPARQL injection."""
    return raw.replace("\\", "").replace(">", "").replace("<", "")


def _format_date(iso_str: str | None) -> str:
    """Format an ISO 8601 datetime string to a human-readable date.

    Returns a string like "Mar 17, 2026" or empty string on failure.
    """
    if not iso_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return ""


def _format_duration(seconds: int | None) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS string."""
    if seconds is None or seconds < 0:
        return ""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ── Fragment routes ──


@media_scheduler_app.route("/_fragments/main")
async def main_fragment(request: Request):
    """Main app page fragment — entry point for the Media Scheduler UI."""
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("main.html"))


@media_scheduler_app.route("/_fragments/add-source")
async def add_source_fragment(request: Request):
    """Add-source form fragment — rendered inline in the sidebar."""
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("add-source.html"))


@media_scheduler_app.route("/_fragments/sources")
async def sources_list_fragment(request: Request):
    """Sources list fragment — lists all MediaSource objects with poll state.

    Returns an HTML fragment with active podcast sources, their last poll
    timestamps, and error indicators.
    """
    ctx = request.app.state.ctx

    try:
        result = await ctx.graph.query(SOURCES_WITH_STATE_SPARQL)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("sources-list SPARQL failed: %s", exc)
        return HTMLResponse(
            '<div class="ms-error">Failed to load sources</div>'
        )

    sources = []
    for b in bindings:
        source_iri = b.get("source", {}).get("value", "")
        feed_url = b.get("feedUrl", {}).get("value", "")
        title = b.get("title", {}).get("value", "")
        source_type = b.get("sourceType", {}).get("value", "")
        error_count_raw = b.get("errorCount", {}).get("value", "0")
        last_error = b.get("lastError", {}).get("value", "")

        try:
            error_count = int(error_count_raw)
        except (ValueError, TypeError):
            error_count = 0

        sources.append({
            "iri": source_iri,
            "url": feed_url,
            "title": title or feed_url,
            "source_type": source_type,
            "error_count": error_count,
            "last_error": last_error,
        })

    return HTMLResponse(ctx.render_template(
        "sources-list.html",
        sources=sources,
    ))


@media_scheduler_app.route("/_fragments/sources/add-podcast", methods=["POST"])
async def add_podcast_fragment(request: Request):
    """Add a podcast subscription from form data.

    Reads ``feed_url`` and optional ``title`` from the POST body.
    Returns an HTML fragment indicating success, duplicate, or error.
    Emits ``HX-Trigger: sourcesChanged`` on success so the sources
    list refreshes.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    feed_url = form.get("feed_url", "").strip()
    title = form.get("title", "").strip() or None

    if not feed_url:
        return HTMLResponse(
            '<div class="ms-error">Please enter a podcast feed URL</div>'
        )

    try:
        result = await subscribe_podcast(ctx, feed_url, title=title)
    except Exception as exc:
        logger.warning("subscribe_podcast failed for %s: %s", feed_url, exc)
        return HTMLResponse(
            f'<div class="ms-error">Failed to subscribe: {exc}</div>'
        )

    if result["status"] == "duplicate":
        return HTMLResponse(
            '<div class="ms-info">Already subscribed to this feed</div>'
        )

    response = HTMLResponse(
        '<div class="ms-success">Subscribed to podcast!</div>'
    )
    response.headers["HX-Trigger"] = "sourcesChanged"
    return response


@media_scheduler_app.route("/_fragments/sources/remove", methods=["POST"])
async def remove_source_fragment(request: Request):
    """Remove a media source subscription.

    Reads ``source_iri`` from the POST body and calls
    ``unsubscribe_source()`` to soft-delete.

    Returns the updated sources list with ``HX-Trigger: sourcesChanged``.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    source_iri = form.get("source_iri", "").strip()

    if not source_iri:
        return HTMLResponse(
            '<div class="ms-error">Missing source_iri</div>', status_code=400
        )

    try:
        await unsubscribe_source(ctx, source_iri)
    except Exception as exc:
        logger.warning("unsubscribe_source failed for %s: %s", source_iri, exc)
        return HTMLResponse(
            f'<div class="ms-error">Failed to remove source: {exc}</div>'
        )

    # Return updated sources list
    try:
        result = await ctx.graph.query(SOURCES_WITH_STATE_SPARQL)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("sources refresh SPARQL failed after remove: %s", exc)
        return HTMLResponse(
            '<div class="ms-success">Source removed, but list refresh failed</div>'
        )

    sources = []
    for b in bindings:
        source_iri_val = b.get("source", {}).get("value", "")
        feed_url = b.get("feedUrl", {}).get("value", "")
        title_val = b.get("title", {}).get("value", "")
        source_type = b.get("sourceType", {}).get("value", "")
        error_count_raw = b.get("errorCount", {}).get("value", "0")
        last_error = b.get("lastError", {}).get("value", "")
        try:
            error_count = int(error_count_raw)
        except (ValueError, TypeError):
            error_count = 0
        sources.append({
            "iri": source_iri_val,
            "url": feed_url,
            "title": title_val or feed_url,
            "source_type": source_type,
            "error_count": error_count,
            "last_error": last_error,
        })

    response = HTMLResponse(ctx.render_template(
        "sources-list.html",
        sources=sources,
    ))
    response.headers["HX-Trigger"] = "sourcesChanged"
    return response


# ── Items list SPARQL ──

ITEMS_LIST_SPARQL = f"""
SELECT ?item ?title ?created ?status ?duration ?enclosureUrl ?sourceTitle WHERE {{
    ?item a <{MEDIA_ITEM_TYPE}> .
    OPTIONAL {{ ?item <http://purl.org/dc/terms/title> ?title }}
    OPTIONAL {{ ?item <http://purl.org/dc/terms/created> ?created }}
    OPTIONAL {{ ?item <{MS_NS}status> ?status }}
    OPTIONAL {{ ?item <{MS_NS}duration> ?duration }}
    OPTIONAL {{ ?item <{MS_NS}enclosureUrl> ?enclosureUrl }}
    OPTIONAL {{
        ?item <{MS_NS}mediaSource> ?source .
        ?source <http://purl.org/dc/terms/title> ?sourceTitle .
    }}
    {{filter_clause}}
}} ORDER BY DESC(?created) LIMIT 100
"""

ITEMS_BY_SOURCE_FILTER = f'?item <{MS_NS}mediaSource> <{{source_iri}}> .'


@media_scheduler_app.route("/_fragments/items")
async def items_list_fragment(request: Request):
    """Items list fragment — shows discovered MediaItem objects.

    Query params:
        source_iri: Optional — restrict to items from a specific source.

    Returns an HTML fragment with episode titles, dates, durations, and sources.
    """
    ctx = request.app.state.ctx
    source_iri = request.query_params.get("source_iri", "").strip() or None

    filter_clause = ""
    if source_iri:
        safe_iri = _sanitize_iri(source_iri)
        filter_clause = f'?item <{MS_NS}mediaSource> <{safe_iri}> .'

    sparql = ITEMS_LIST_SPARQL.replace("{filter_clause}", filter_clause)

    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("items-list SPARQL failed: %s", exc)
        return HTMLResponse(
            '<div class="ms-error">Failed to load items</div>'
        )

    items = []
    for b in bindings:
        item_iri = b.get("item", {}).get("value", "")
        title = b.get("title", {}).get("value", "")
        created_raw = b.get("created", {}).get("value", "")
        status = b.get("status", {}).get("value", "")
        duration_raw = b.get("duration", {}).get("value", "")
        enclosure_url = b.get("enclosureUrl", {}).get("value", "")
        source_title = b.get("sourceTitle", {}).get("value", "")

        try:
            duration_seconds = int(duration_raw) if duration_raw else None
        except (ValueError, TypeError):
            duration_seconds = None

        items.append({
            "iri": item_iri,
            "title": title or "Untitled",
            "date": _format_date(created_raw),
            "status": status,
            "duration": _format_duration(duration_seconds),
            "enclosure_url": enclosure_url,
            "source_title": source_title,
        })

    return HTMLResponse(ctx.render_template(
        "items-list.html",
        items=items,
        active_source=source_iri,
    ))


# ── Lifecycle hooks ──


@media_scheduler_app.on_startup
def on_startup(ctx: AppContext):
    """Log app startup."""
    logger.info("Media Scheduler app started: %s", ctx.app_id)


@media_scheduler_app.on_shutdown
def on_shutdown(ctx: AppContext):
    """Log app shutdown."""
    logger.info("Media Scheduler app stopped: %s", ctx.app_id)
