"""Media Scheduler application — podcast/YouTube/Spotify content scheduling.

Registers:
- 5 fragment routes (main page, sources list, add-podcast, remove source, items list)
- Lifecycle hooks (startup, shutdown)

The poll-sources task handler is implemented in T03 and registered here
once that task completes. This module establishes the app scaffold and
CRUD routes.
"""

from __future__ import annotations

import logging
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
        subscribe_podcast,
        unsubscribe_source,
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
    subscribe_podcast = _fm.subscribe_podcast
    unsubscribe_source = _fm.unsubscribe_source

logger = logging.getLogger(__name__)

media_scheduler_app = App("media-scheduler")


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
