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
from datetime import date, datetime, timezone
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
    from services.plan_service import (
        DAILY_MEDIA_PLAN_TYPE,
        PLAN_ENTRY_TYPE,
        fetch_context,
        generate_plan,
    )
except ModuleNotFoundError:
    import importlib.util as _ilu2
    import pathlib as _pl2

    _plan_svc = _pl2.Path(__file__).resolve().parent / "services" / "plan_service.py"
    _plan_sp = _ilu2.spec_from_file_location("_plan_service_fallback", _plan_svc)
    _plan_fm = _ilu2.module_from_spec(_plan_sp)
    _plan_sp.loader.exec_module(_plan_fm)
    DAILY_MEDIA_PLAN_TYPE = _plan_fm.DAILY_MEDIA_PLAN_TYPE
    PLAN_ENTRY_TYPE = _plan_fm.PLAN_ENTRY_TYPE
    fetch_context = _plan_fm.fetch_context
    generate_plan = _plan_fm.generate_plan

try:
    from services.rules_service import (
        add_rule,
        delete_rule,
        load_rules,
        toggle_rule,
        validate_rule,
    )
except ModuleNotFoundError:
    import importlib.util as _ilu3
    import pathlib as _pl3

    _rules_svc = _pl3.Path(__file__).resolve().parent / "services" / "rules_service.py"
    _rules_sp = _ilu3.spec_from_file_location("_rules_service_fallback", _rules_svc)
    _rules_fm = _ilu3.module_from_spec(_rules_sp)
    _rules_sp.loader.exec_module(_rules_fm)
    add_rule = _rules_fm.add_rule
    delete_rule = _rules_fm.delete_rule
    load_rules = _rules_fm.load_rules
    toggle_rule = _rules_fm.toggle_rule
    validate_rule = _rules_fm.validate_rule

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


# ── Today / Rules / Plan routes ──

TODAY_PLAN_SPARQL = f"""
SELECT ?entry ?title ?slotStart ?slotEnd ?slotOrder ?entryStatus
       ?mediaItem ?enclosureUrl ?sourceTitle ?duration ?sourceType
WHERE {{
    ?entry a <{PLAN_ENTRY_TYPE}> .
    ?entry <{MS_NS}plan> ?plan .
    ?plan a <{DAILY_MEDIA_PLAN_TYPE}> .
    ?plan <http://purl.org/dc/terms/title> ?planTitle .
    FILTER(CONTAINS(?planTitle, "{{date_str}}"))
    OPTIONAL {{ ?entry <http://purl.org/dc/terms/title> ?title }}
    OPTIONAL {{ ?entry <{MS_NS}slotStart> ?slotStart }}
    OPTIONAL {{ ?entry <{MS_NS}slotEnd> ?slotEnd }}
    OPTIONAL {{ ?entry <{MS_NS}slotOrder> ?slotOrder }}
    OPTIONAL {{ ?entry <{MS_NS}entryStatus> ?entryStatus }}
    OPTIONAL {{
        ?entry <{MS_NS}mediaItem> ?mediaItem .
        OPTIONAL {{ ?mediaItem <{MS_NS}enclosureUrl> ?enclosureUrl }}
        OPTIONAL {{ ?mediaItem <{MS_NS}duration> ?duration }}
        OPTIONAL {{
            ?mediaItem <{MS_NS}mediaSource> ?source .
            OPTIONAL {{ ?source <http://purl.org/dc/terms/title> ?sourceTitle }}
            OPTIONAL {{ ?source <{MS_NS}sourceType> ?sourceType }}
        }}
    }}
    FILTER(!BOUND(?entryStatus) || ?entryStatus != "replaced")
}} ORDER BY ?slotOrder
"""


def _current_time_str() -> str:
    """Return current local time as HH:MM string."""
    return datetime.now().strftime("%H:%M")


@media_scheduler_app.route("/_fragments/today")
async def today_fragment(request: Request):
    """Today's plan fragment — agenda-style daily plan view.

    Queries PlanEntry objects for today's date, renders as time-slotted cards.
    Marks the entry whose time slot contains the current time as "now playing".
    """
    ctx = request.app.state.ctx
    today_str = date.today().isoformat()
    now_time = _current_time_str()

    sparql = TODAY_PLAN_SPARQL.replace("{date_str}", today_str)

    entries = []
    has_plan = False

    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        has_plan = len(bindings) > 0

        for b in bindings:
            slot_start = b.get("slotStart", {}).get("value", "")
            slot_end = b.get("slotEnd", {}).get("value", "")
            status = b.get("entryStatus", {}).get("value", "pending")
            title = b.get("title", {}).get("value", "")
            enclosure_url = b.get("enclosureUrl", {}).get("value", "")
            source_title = b.get("sourceTitle", {}).get("value", "")
            duration_raw = b.get("duration", {}).get("value", "")

            duration_seconds = None
            if duration_raw:
                try:
                    duration_seconds = int(duration_raw)
                except (ValueError, TypeError):
                    pass

            # Determine "now playing" based on time slot containing current time
            now_playing = False
            if slot_start and slot_end and status != "completed" and status != "skipped":
                if slot_start <= now_time <= slot_end:
                    now_playing = True

            entries.append({
                "title": title or "Untitled",
                "slot_start": slot_start,
                "slot_end": slot_end,
                "status": status,
                "now_playing": now_playing,
                "enclosure_url": enclosure_url,
                "source_title": source_title,
                "duration_display": _format_duration(duration_seconds),
            })

    except Exception as exc:
        logger.warning("today-plan SPARQL failed: %s", exc)
        return HTMLResponse(
            '<div class="ms-error">Failed to load today\'s plan</div>'
        )

    return HTMLResponse(ctx.render_template(
        "today.html",
        entries=entries,
        plan_date=today_str,
        has_plan=has_plan,
    ))


@media_scheduler_app.route("/_fragments/rules")
async def rules_fragment(request: Request):
    """Rules list fragment — shows all schedule rules with controls."""
    ctx = request.app.state.ctx

    try:
        rules = await load_rules(ctx.state)
    except Exception as exc:
        logger.warning("rules load failed: %s", exc)
        return HTMLResponse(
            '<div class="ms-error">Failed to load rules</div>'
        )

    return HTMLResponse(ctx.render_template("rules.html", rules=rules))


@media_scheduler_app.route("/_fragments/rules/add")
async def rule_add_form_fragment(request: Request):
    """Empty rule form fragment for adding a new rule."""
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template(
        "rule-form.html", rule=None, editing=False
    ))


@media_scheduler_app.route("/_fragments/rules", methods=["POST"])
async def rules_save_fragment(request: Request):
    """Save a new or updated rule from form data, return refreshed rules list."""
    ctx = request.app.state.ctx
    form = await request.form()

    name = form.get("name", "").strip()
    if not name:
        return HTMLResponse(
            '<div class="ms-error">Rule name is required</div>',
            status_code=400,
        )

    # Build conditions from form
    conditions: dict[str, Any] = {}
    activity = form.get("activity", "").strip()
    location_zone = form.get("location_zone", "").strip()
    time_period = form.get("time_period", "").strip()

    if activity:
        conditions["activity"] = activity
    if location_zone:
        conditions["location_zone"] = location_zone
    if time_period:
        conditions["time_period"] = time_period

    # Time range
    if form.get("use_time_range"):
        time_start = form.get("time_start", "").strip()
        time_end = form.get("time_end", "").strip()
        if time_start and time_end:
            conditions["time_range"] = {"start": time_start, "end": time_end}

    # Build action from form
    action_type = form.get("action_type", "source_type").strip()
    action_value = ""
    if action_type == "source_type":
        action_value = form.get("action_source_type", "podcast").strip()
    elif action_type == "source_iri":
        action_value = form.get("action_source_iri", "").strip()
    elif action_type == "category":
        action_value = form.get("action_category", "").strip()

    priority_raw = form.get("priority", "10").strip()
    try:
        priority = int(priority_raw)
    except (ValueError, TypeError):
        priority = 10

    rule_dict: dict[str, Any] = {
        "name": name,
        "priority": priority,
        "conditions": conditions,
        "action": {"type": action_type, "value": action_value},
    }

    # If editing, preserve the ID
    rule_id = form.get("rule_id", "").strip()
    if rule_id:
        rule_dict["id"] = rule_id

    try:
        await add_rule(ctx.state, rule_dict)
    except ValueError as exc:
        logger.warning("rule validation failed: %s", exc)
        return HTMLResponse(
            f'<div class="ms-error">Invalid rule: {exc}</div>',
            status_code=400,
        )
    except Exception as exc:
        logger.warning("rule save failed: %s", exc)
        return HTMLResponse(
            f'<div class="ms-error">Failed to save rule: {exc}</div>',
        )

    # Return refreshed rules list
    rules = await load_rules(ctx.state)
    return HTMLResponse(ctx.render_template("rules-list.html", rules=rules))


@media_scheduler_app.route("/_fragments/rules/{rule_id}/toggle", methods=["POST"])
async def rule_toggle_fragment(request: Request):
    """Toggle a rule's enabled state and return refreshed rules list."""
    ctx = request.app.state.ctx
    rule_id = request.path_params.get("rule_id", "")

    if not rule_id:
        return HTMLResponse(
            '<div class="ms-error">Missing rule_id</div>', status_code=400
        )

    try:
        result = await toggle_rule(ctx.state, rule_id)
        if result is None:
            return HTMLResponse(
                '<div class="ms-error">Rule not found</div>', status_code=404
            )
    except Exception as exc:
        logger.warning("rule toggle failed for %s: %s", rule_id, exc)
        return HTMLResponse(
            f'<div class="ms-error">Failed to toggle rule: {exc}</div>'
        )

    rules = await load_rules(ctx.state)
    return HTMLResponse(ctx.render_template("rules-list.html", rules=rules))


@media_scheduler_app.route("/_fragments/rules/{rule_id}/delete", methods=["POST"])
async def rule_delete_fragment(request: Request):
    """Delete a rule and return refreshed rules list."""
    ctx = request.app.state.ctx
    rule_id = request.path_params.get("rule_id", "")

    if not rule_id:
        return HTMLResponse(
            '<div class="ms-error">Missing rule_id</div>', status_code=400
        )

    try:
        deleted = await delete_rule(ctx.state, rule_id)
        if not deleted:
            return HTMLResponse(
                '<div class="ms-error">Rule not found</div>', status_code=404
            )
    except Exception as exc:
        logger.warning("rule delete failed for %s: %s", rule_id, exc)
        return HTMLResponse(
            f'<div class="ms-error">Failed to delete rule: {exc}</div>'
        )

    rules = await load_rules(ctx.state)
    return HTMLResponse(ctx.render_template("rules-list.html", rules=rules))


@media_scheduler_app.route("/_fragments/plan/generate", methods=["POST"])
async def plan_generate_fragment(request: Request):
    """Trigger plan generation and return refreshed today view."""
    ctx = request.app.state.ctx
    today_str = date.today().isoformat()

    try:
        summary = await generate_plan(ctx, date_str=today_str)
        logger.info(
            "Plan generated via UI: %d rules matched, %d entries created",
            summary.get("rules_matched", 0),
            summary.get("entries_created", 0),
        )
    except Exception as exc:
        logger.warning("plan generation failed: %s", exc)
        return HTMLResponse(
            f'<div class="ms-error">Plan generation failed: {exc}</div>'
        )

    # Re-render the today view with the new plan
    now_time = _current_time_str()
    sparql = TODAY_PLAN_SPARQL.replace("{date_str}", today_str)

    entries = []
    has_plan = False

    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        has_plan = len(bindings) > 0

        for b in bindings:
            slot_start = b.get("slotStart", {}).get("value", "")
            slot_end = b.get("slotEnd", {}).get("value", "")
            status = b.get("entryStatus", {}).get("value", "pending")
            title = b.get("title", {}).get("value", "")
            enclosure_url = b.get("enclosureUrl", {}).get("value", "")
            source_title = b.get("sourceTitle", {}).get("value", "")
            duration_raw = b.get("duration", {}).get("value", "")

            duration_seconds = None
            if duration_raw:
                try:
                    duration_seconds = int(duration_raw)
                except (ValueError, TypeError):
                    pass

            now_playing = False
            if slot_start and slot_end and status not in ("completed", "skipped"):
                if slot_start <= now_time <= slot_end:
                    now_playing = True

            entries.append({
                "title": title or "Untitled",
                "slot_start": slot_start,
                "slot_end": slot_end,
                "status": status,
                "now_playing": now_playing,
                "enclosure_url": enclosure_url,
                "source_title": source_title,
                "duration_display": _format_duration(duration_seconds),
            })

    except Exception as exc:
        logger.warning("today-plan SPARQL after generate failed: %s", exc)

    return HTMLResponse(ctx.render_template(
        "today.html",
        entries=entries,
        plan_date=today_str,
        has_plan=has_plan,
    ))


@media_scheduler_app.route("/_fragments/current-suggestion")
async def current_suggestion_fragment(request: Request):
    """Minimal HTML fragment showing the current or next plan entry.

    For S05 mobile widget use. Returns a compact card with the entry
    whose time slot contains the current time, or the next upcoming entry.
    """
    ctx = request.app.state.ctx
    today_str = date.today().isoformat()
    now_time = _current_time_str()

    sparql = TODAY_PLAN_SPARQL.replace("{date_str}", today_str)

    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("current-suggestion SPARQL failed: %s", exc)
        return HTMLResponse('<div class="ms-empty-state">No suggestion</div>')

    current_entry = None
    next_entry = None

    for b in bindings:
        slot_start = b.get("slotStart", {}).get("value", "")
        slot_end = b.get("slotEnd", {}).get("value", "")
        status = b.get("entryStatus", {}).get("value", "pending")
        title = b.get("title", {}).get("value", "Untitled")

        if status in ("completed", "skipped", "replaced"):
            continue

        if slot_start and slot_end:
            if slot_start <= now_time <= slot_end:
                current_entry = {"title": title, "slot_start": slot_start, "slot_end": slot_end, "status": "now"}
                break
            elif slot_start > now_time and next_entry is None:
                next_entry = {"title": title, "slot_start": slot_start, "slot_end": slot_end, "status": "next"}

    entry = current_entry or next_entry

    if not entry:
        return HTMLResponse('<div class="ms-empty-state">No upcoming items</div>')

    label = "Now playing" if entry["status"] == "now" else f"Up next at {entry['slot_start']}"
    return HTMLResponse(
        f'<div class="ms-suggestion">'
        f'<span class="ms-suggestion-label">{label}</span>'
        f'<span class="ms-suggestion-title">{entry["title"]}</span>'
        f'</div>'
    )


# ── Lifecycle hooks ──


@media_scheduler_app.on_startup
def on_startup(ctx: AppContext):
    """Log app startup."""
    logger.info("Media Scheduler app started: %s", ctx.app_id)


@media_scheduler_app.on_shutdown
def on_shutdown(ctx: AppContext):
    """Log app shutdown."""
    logger.info("Media Scheduler app stopped: %s", ctx.app_id)
