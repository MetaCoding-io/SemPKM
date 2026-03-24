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

import json
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import unquote

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

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

try:
    from services.youtube_service import (
        YOUTUBE_SOURCES_SPARQL,
        YouTubeAPIError,
        YouTubeClient,
        check_quota,
        get_existing_item_iris as yt_get_existing_item_iris,
        increment_quota,
        mint_item_iri as yt_mint_item_iri,
        parse_youtube_url,
        subscribe_youtube,
        video_to_media_item,
    )
except ModuleNotFoundError:
    import importlib.util as _ilu4
    import pathlib as _pl4

    _yt_svc = _pl4.Path(__file__).resolve().parent / "services" / "youtube_service.py"
    _yt_sp = _ilu4.spec_from_file_location("_youtube_service_fallback", _yt_svc)
    _yt_fm = _ilu4.module_from_spec(_yt_sp)
    _yt_sp.loader.exec_module(_yt_fm)
    YOUTUBE_SOURCES_SPARQL = _yt_fm.YOUTUBE_SOURCES_SPARQL
    YouTubeAPIError = _yt_fm.YouTubeAPIError
    YouTubeClient = _yt_fm.YouTubeClient
    check_quota = _yt_fm.check_quota
    yt_get_existing_item_iris = _yt_fm.get_existing_item_iris
    yt_mint_item_iri = _yt_fm.mint_item_iri
    increment_quota = _yt_fm.increment_quota
    parse_youtube_url = _yt_fm.parse_youtube_url
    subscribe_youtube = _yt_fm.subscribe_youtube
    video_to_media_item = _yt_fm.video_to_media_item

try:
    from services.spotify_service import (
        SPOTIFY_SOURCES_SPARQL,
        SpotifyAPIError,
        SpotifyAuthError,
        SpotifyClient,
        build_spotify_authorize_url,
        clear_spotify_auth,
        exchange_spotify_code,
        generate_code_challenge,
        generate_code_verifier,
        get_existing_item_iris as sp_get_existing_item_iris,
        get_spotify_connection_status,
        mint_item_iri as sp_mint_item_iri,
        parse_spotify_url,
        refresh_spotify_if_expired,
        store_spotify_tokens,
        subscribe_spotify,
        track_to_media_item,
    )
except ModuleNotFoundError:
    import importlib.util as _ilu5
    import pathlib as _pl5

    _sp_svc = _pl5.Path(__file__).resolve().parent / "services" / "spotify_service.py"
    _sp_sp = _ilu5.spec_from_file_location("_spotify_service_fallback", _sp_svc)
    _sp_fm = _ilu5.module_from_spec(_sp_sp)
    _sp_sp.loader.exec_module(_sp_fm)
    SPOTIFY_SOURCES_SPARQL = _sp_fm.SPOTIFY_SOURCES_SPARQL
    SpotifyAPIError = _sp_fm.SpotifyAPIError
    SpotifyAuthError = _sp_fm.SpotifyAuthError
    SpotifyClient = _sp_fm.SpotifyClient
    build_spotify_authorize_url = _sp_fm.build_spotify_authorize_url
    clear_spotify_auth = _sp_fm.clear_spotify_auth
    exchange_spotify_code = _sp_fm.exchange_spotify_code
    generate_code_challenge = _sp_fm.generate_code_challenge
    generate_code_verifier = _sp_fm.generate_code_verifier
    sp_get_existing_item_iris = _sp_fm.get_existing_item_iris
    get_spotify_connection_status = _sp_fm.get_spotify_connection_status
    sp_mint_item_iri = _sp_fm.mint_item_iri
    parse_spotify_url = _sp_fm.parse_spotify_url
    refresh_spotify_if_expired = _sp_fm.refresh_spotify_if_expired
    store_spotify_tokens = _sp_fm.store_spotify_tokens
    subscribe_spotify = _sp_fm.subscribe_spotify
    track_to_media_item = _sp_fm.track_to_media_item

try:
    from services.stats_service import (
        get_hours_by_source_type,
        get_top_sources,
        get_weekly_trends,
    )
except ModuleNotFoundError:
    import importlib.util as _ilu_stats
    import pathlib as _pl_stats

    _stats_svc = _pl_stats.Path(__file__).resolve().parent / "services" / "stats_service.py"
    _stats_sp = _ilu_stats.spec_from_file_location("_stats_service_fallback", _stats_svc)
    _stats_fm = _ilu_stats.module_from_spec(_stats_sp)
    _stats_sp.loader.exec_module(_stats_fm)
    get_hours_by_source_type = _stats_fm.get_hours_by_source_type
    get_top_sources = _stats_fm.get_top_sources
    get_weekly_trends = _stats_fm.get_weekly_trends

try:
    from services.context_service import (
        get_context_subscription_status,
        start_context_listener,
        stop_context_listener,
    )
except ModuleNotFoundError:
    import importlib.util as _ilu6
    import pathlib as _pl6

    _ctx_svc = _pl6.Path(__file__).resolve().parent / "services" / "context_service.py"
    _ctx_sp = _ilu6.spec_from_file_location("_context_service_fallback", _ctx_svc)
    _ctx_fm = _ilu6.module_from_spec(_ctx_sp)
    _ctx_sp.loader.exec_module(_ctx_fm)
    get_context_subscription_status = _ctx_fm.get_context_subscription_status
    start_context_listener = _ctx_fm.start_context_listener
    stop_context_listener = _ctx_fm.stop_context_listener

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


@media_scheduler_app.task("poll-youtube")
async def poll_youtube(ctx: AppContext) -> dict:
    """Poll all YouTube MediaSource objects and create new MediaItem objects.

    Queries sources with sourceType="youtube", resolves each to a playlist ID,
    fetches recent videos via YouTube Data API v3, deduplicates against existing
    items, fetches video durations in a batch call, and bulk-creates new
    MediaItems.

    Respects daily API quota limits tracked via StateClient. On quota exceeded
    from the API, stops polling remaining sources. On other API errors,
    increments the source's error count and continues.

    Returns:
        Summary dict with sources_polled and items_created counts.
    """
    # Require API key
    api_key = await ctx.state.get("youtube_api_key")
    if not api_key:
        logger.warning("poll-youtube: no youtube_api_key configured, skipping")
        return {"skipped": "no_api_key"}

    # Check daily quota
    under_quota = await check_quota(ctx.state)
    if not under_quota:
        logger.warning("poll-youtube: daily quota exceeded, skipping")
        return {"skipped": "quota_exceeded"}

    # Query YouTube-type sources
    result = await ctx.graph.query(YOUTUBE_SOURCES_SPARQL)
    bindings = result.get("results", {}).get("bindings", [])

    sources_polled = 0
    items_created = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for binding in bindings:
        source_iri = binding.get("source", {}).get("value", "")
        feed_url = binding.get("feedUrl", {}).get("value", "")
        external_id = binding.get("externalId", {}).get("value", "")

        if not feed_url:
            logger.warning("YouTube source %s has no feedUrl, skipping", source_iri)
            continue

        # Use pre-resolved playlist ID if available, otherwise skip
        playlist_id = external_id
        if not playlist_id:
            logger.warning(
                "YouTube source %s has no externalId (playlist ID), skipping",
                source_iri,
            )
            continue

        try:
            client = YouTubeClient(ctx.http, api_key)

            # Fetch recent playlist items (quota cost: 1 unit)
            playlist_items = await client.list_playlist_items(playlist_id)
            await increment_quota(ctx.state, 1)

            # Deduplicate against existing items
            existing_iris = await yt_get_existing_item_iris(ctx.graph, source_iri)

            new_videos = []
            for item in playlist_items:
                snippet = item.get("snippet", {})
                video_id = snippet.get("resourceId", {}).get("videoId", "")
                if not video_id:
                    continue
                # Build a temp item to check IRI
                    candidate_iri = yt_mint_item_iri(source_iri, video_id)
                if candidate_iri not in existing_iris:
                    new_videos.append(item)

            if not new_videos:
                logger.info(
                    "Polled %s: 0 new items (all %d existing)",
                    feed_url, len(playlist_items),
                )
                sources_polled += 1
                await _update_youtube_source_state(ctx, source_iri, now_iso)
                continue

            # Cap imports
            if len(new_videos) > MAX_INITIAL_ITEMS:
                logger.info(
                    "Capping %d new YouTube items to %d for %s",
                    len(new_videos), MAX_INITIAL_ITEMS, feed_url,
                )
                new_videos = new_videos[:MAX_INITIAL_ITEMS]

            # Get durations for new videos in a batch call (quota cost: 1 unit)
            video_ids = []
            for v in new_videos:
                vid = v.get("snippet", {}).get("resourceId", {}).get("videoId", "")
                if vid:
                    video_ids.append(vid)

            durations = {}
            if video_ids:
                durations = await client.get_video_durations(video_ids)
                await increment_quota(ctx.state, 1)

            # Convert to MediaItem objects
            media_items = []
            for v in new_videos:
                vid = v.get("snippet", {}).get("resourceId", {}).get("videoId", "")
                if vid and vid in durations:
                    v["duration_seconds"] = durations[vid]
                media_items.append(video_to_media_item(v, source_iri))

            # Bulk-create
            if media_items:
                async with ctx.commands.bulk(
                    summary=f"Poll YouTube: {feed_url}",
                    source=ctx.app_id,
                ) as batch:
                    for item in media_items:
                        batch.add("object.create", item)

            created_count = len(media_items)
            items_created += created_count
            sources_polled += 1

            logger.info(
                "Polled %s: %d new items (skipped %d existing, quota +2 units)",
                feed_url, created_count,
                len(playlist_items) - len(new_videos),
            )

            # Success: reset error state
            await _update_youtube_source_state(
                ctx, source_iri, now_iso, error_count=0, last_error=""
            )

        except YouTubeAPIError as e:
            if e.error_type == "quotaExceeded":
                logger.warning(
                    "YouTube quota exceeded during poll of %s — stopping",
                    feed_url,
                )
                break
            else:
                current_error_count = _get_current_error_count(binding)
                logger.warning(
                    "YouTube API error polling %s: %s", feed_url, e,
                )
                await _update_youtube_source_state(
                    ctx, source_iri, now_iso,
                    error_count=current_error_count + 1,
                    last_error=str(e),
                )
        except Exception as e:
            current_error_count = _get_current_error_count(binding)
            logger.exception("Error polling YouTube source %s", feed_url)
            await _update_youtube_source_state(
                ctx, source_iri, now_iso,
                error_count=current_error_count + 1,
                last_error=str(e),
            )

    logger.info(
        "poll-youtube complete: %d sources polled, %d items created",
        sources_polled, items_created,
    )
    return {"sources_polled": sources_polled, "items_created": items_created}


async def _update_youtube_source_state(
    ctx: AppContext,
    source_iri: str,
    last_polled: str,
    error_count: int | None = None,
    last_error: str | None = None,
) -> None:
    """Update a YouTube source's poll state via SPARQL."""
    await update_source_state(
        ctx,
        source_iri,
        last_polled=last_polled,
        error_count=error_count if error_count is not None else 0,
        last_error=last_error if last_error is not None else "",
    )


@media_scheduler_app.task("poll-spotify")
async def poll_spotify(ctx: AppContext) -> dict:
    """Poll all Spotify MediaSource objects and create new MediaItem objects.

    Checks Spotify connection status, refreshes the access token if expired,
    then for each Spotify playlist source: fetches tracks, deduplicates
    against existing items, caps at MAX_INITIAL_ITEMS, and bulk-creates.

    SpotifyAPIError is caught per-source (increments errorCount).
    SpotifyAuthError breaks the loop (auth is shared across all sources).

    Returns:
        Summary dict with sources_polled and items_created counts.
    """
    import logging as _log
    _spotify_poll_log = _log.getLogger("spotify.poll")

    # Check connection before any API calls
    status = await get_spotify_connection_status(ctx.state)
    if not status["connected"]:
        _spotify_poll_log.info("poll-spotify: not connected, skipping")
        return {"skipped": "not_connected"}

    # Read credentials from state
    client_id = await ctx.state.get("spotify_client_id") or ""
    client_secret = await ctx.state.get("spotify_client_secret") or ""

    if not client_id or not client_secret:
        _spotify_poll_log.warning("poll-spotify: no credentials configured, skipping")
        return {"skipped": "no_credentials"}

    # Refresh token if expired
    try:
        access_token = await refresh_spotify_if_expired(
            ctx.http, ctx.state, client_id, client_secret
        )
    except SpotifyAuthError as e:
        _spotify_poll_log.warning("poll-spotify: auth refresh failed: %s", e)
        return {"skipped": "auth_refresh_failed", "error": str(e)}

    # Query Spotify-type sources
    result = await ctx.graph.query(SPOTIFY_SOURCES_SPARQL)
    bindings = result.get("results", {}).get("bindings", [])

    sources_polled = 0
    items_created = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for binding in bindings:
        source_iri = binding.get("source", {}).get("value", "")
        feed_url = binding.get("feedUrl", {}).get("value", "")
        external_id = binding.get("externalId", {}).get("value", "")

        if not external_id:
            _spotify_poll_log.warning(
                "Spotify source %s has no externalId, skipping", source_iri
            )
            continue

        try:
            client = SpotifyClient(ctx.http, access_token)

            # Fetch playlist tracks
            playlist_items = await client.get_playlist_tracks(external_id)

            # Deduplicate against existing items
            existing_iris = await sp_get_existing_item_iris(ctx.graph, source_iri)

            new_items = []
            for item in playlist_items:
                inner_track = item.get("track")
                if not inner_track or not isinstance(inner_track, dict):
                    continue
                track_id = inner_track.get("id", "")
                if not track_id:
                    continue
                candidate_iri = sp_mint_item_iri(source_iri, track_id)
                if candidate_iri not in existing_iris:
                    media_item = track_to_media_item(inner_track, source_iri)
                    new_items.append(media_item)

            # Cap imports
            if len(new_items) > MAX_INITIAL_ITEMS:
                _spotify_poll_log.info(
                    "Capping %d new Spotify items to %d for %s",
                    len(new_items), MAX_INITIAL_ITEMS, feed_url,
                )
                new_items = new_items[:MAX_INITIAL_ITEMS]

            # Bulk-create new items
            if new_items:
                async with ctx.commands.bulk(
                    summary=f"Poll Spotify: {feed_url}",
                    source=ctx.app_id,
                ) as batch:
                    for media_item in new_items:
                        batch.add("object.create", media_item)

            created_count = len(new_items)
            items_created += created_count
            sources_polled += 1

            _spotify_poll_log.info(
                "Polled %s: %d new items (skipped %d existing)",
                feed_url, created_count,
                len(playlist_items) - len(new_items),
            )

            # Success: reset error state
            await _update_spotify_source_state(
                ctx, source_iri, now_iso, error_count=0, last_error=""
            )

        except SpotifyAuthError as e:
            _spotify_poll_log.warning(
                "Spotify auth error during poll — stopping: %s", e
            )
            break

        except SpotifyAPIError as e:
            current_error_count = _get_current_error_count(binding)
            _spotify_poll_log.warning(
                "Spotify API error polling %s: %s", feed_url, e
            )
            await _update_spotify_source_state(
                ctx, source_iri, now_iso,
                error_count=current_error_count + 1,
                last_error=str(e),
            )

        except Exception as e:
            current_error_count = _get_current_error_count(binding)
            _spotify_poll_log.exception("Error polling Spotify source %s", feed_url)
            await _update_spotify_source_state(
                ctx, source_iri, now_iso,
                error_count=current_error_count + 1,
                last_error=str(e),
            )

    _spotify_poll_log.info(
        "poll-spotify complete: %d sources polled, %d items created",
        sources_polled, items_created,
    )
    return {"sources_polled": sources_polled, "items_created": items_created}


async def _update_spotify_source_state(
    ctx: AppContext,
    source_iri: str,
    last_polled: str,
    error_count: int | None = None,
    last_error: str | None = None,
) -> None:
    """Update a Spotify source's poll state via SPARQL."""
    await update_source_state(
        ctx,
        source_iri,
        last_polled=last_polled,
        error_count=error_count if error_count is not None else 0,
        last_error=last_error if last_error is not None else "",
    )


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
    spotify_status = await get_spotify_connection_status(ctx.state)
    return HTMLResponse(ctx.render_template(
        "add-source.html",
        spotify_connected=spotify_status["connected"],
        spotify_status=spotify_status,
    ))


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


@media_scheduler_app.route("/_fragments/sources/add-youtube", methods=["POST"])
async def add_youtube_fragment(request: Request):
    """Add a YouTube channel or playlist subscription from form data.

    Reads ``youtube_url`` and ``api_key`` from the POST body.
    Validates the URL via ``parse_youtube_url()``, then calls
    ``subscribe_youtube()`` which validates the API key via a test API
    call, resolves channel → uploads playlist, and creates the
    MediaSource.

    Returns an HTML fragment indicating success, duplicate, or error.
    Emits ``HX-Trigger: sourcesChanged`` on success so the sources
    list refreshes.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    youtube_url = form.get("youtube_url", "").strip()
    api_key = form.get("api_key", "").strip()

    if not youtube_url:
        return HTMLResponse(
            '<div class="ms-error">Please enter a YouTube URL</div>'
        )

    if not api_key:
        return HTMLResponse(
            '<div class="ms-error">Please enter a YouTube Data API key</div>'
        )

    # Validate URL format first
    parsed = parse_youtube_url(youtube_url)
    if parsed is None:
        logger.warning("add-youtube: invalid URL format: %s", youtube_url)
        return HTMLResponse(
            '<div class="ms-error">Not a recognized YouTube channel or playlist URL</div>'
        )

    try:
        result = await subscribe_youtube(ctx, youtube_url, api_key)
    except YouTubeAPIError as e:
        logger.warning(
            "add-youtube API error for %s: %s (type=%s)",
            youtube_url, e.message, e.error_type,
        )
        return HTMLResponse(
            f'<div class="ms-error">YouTube API error: {e.message}</div>'
        )
    except ValueError as e:
        logger.warning("add-youtube validation error: %s", e)
        return HTMLResponse(
            f'<div class="ms-error">{e}</div>'
        )
    except Exception as exc:
        logger.warning("subscribe_youtube failed for %s: %s", youtube_url, exc)
        return HTMLResponse(
            f'<div class="ms-error">Failed to subscribe: {exc}</div>'
        )

    if result["status"] == "duplicate":
        return HTMLResponse(
            '<div class="ms-info">Already subscribed to this YouTube source</div>'
        )

    response = HTMLResponse(
        '<div class="ms-success">Subscribed to YouTube source!</div>'
    )
    response.headers["HX-Trigger"] = "sourcesChanged"
    return response


# ── Spotify OAuth + subscription routes ──


def _spotify_oauth_result_page(success: bool, message: str) -> str:
    """Generate a minimal HTML page for the Spotify OAuth callback result.

    On success, auto-redirects to the workspace after 2 seconds.
    Same pattern as Google Calendar's ``_oauth_result_page``.
    """
    status_class = "success" if success else "error"
    redirect_script = ""
    if success:
        redirect_script = (
            '<script>setTimeout(function() { '
            'window.location.href = "/browser/"; '
            '}, 2000);</script>'
        )
    return f"""<!DOCTYPE html>
<html>
<head><title>Spotify — {'Connected' if success else 'Error'}</title></head>
<body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #1a1a1a; color: #eee;">
  <div style="text-align: center; max-width: 400px;">
    <h2 class="{status_class}">{message}</h2>
    {'<p>Redirecting to workspace…</p>' if success else '<p><a href="/browser/">Return to workspace</a></p>'}
  </div>
  {redirect_script}
</body>
</html>"""


@media_scheduler_app.route("/_fragments/spotify/connect", methods=["POST"])
async def spotify_connect_fragment(request: Request):
    """Save Spotify credentials, generate PKCE pair, redirect to Spotify OAuth.

    Reads client_id, client_secret, redirect_uri from the form. Stores
    credentials and the PKCE code_verifier in state, then 303-redirects
    the user's browser to Spotify's authorization page.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    client_id = form.get("client_id", "").strip()
    client_secret = form.get("client_secret", "").strip()
    redirect_uri = form.get("redirect_uri", "").strip()

    if not client_id or not client_secret or not redirect_uri:
        return HTMLResponse(
            '<div class="ms-error">Client ID, Client Secret, and Redirect URI are all required</div>'
        )

    # Store credentials for later use (token exchange, refresh)
    await ctx.state.set("spotify_client_id", client_id)
    await ctx.state.set("spotify_client_secret", client_secret)
    await ctx.state.set("spotify_redirect_uri", redirect_uri)

    # Generate PKCE verifier + challenge
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    await ctx.state.set("spotify_code_verifier", code_verifier)

    # Generate CSRF state parameter
    oauth_state = str(uuid.uuid4())
    await ctx.state.set("spotify_oauth_state", oauth_state)

    authorize_url = build_spotify_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=oauth_state,
        code_challenge=code_challenge,
    )

    logger.info("Redirecting to Spotify OAuth consent screen")
    return RedirectResponse(url=authorize_url, status_code=303)


@media_scheduler_app.route("/_fragments/spotify/callback")
async def spotify_callback_fragment(request: Request):
    """Handle Spotify OAuth callback — CSRF validation, PKCE code exchange, store tokens.

    Validates the state parameter, reads the stored code_verifier, exchanges
    the authorization code for tokens, fetches the user profile, and stores
    everything in state. Returns a standalone HTML result page.
    """
    ctx = request.app.state.ctx
    code = request.query_params.get("code")
    state_param = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        logger.warning("Spotify OAuth callback error: %s", error)
        return HTMLResponse(
            _spotify_oauth_result_page(
                success=False,
                message=f"Spotify denied access: {error}",
            )
        )

    if not code:
        return HTMLResponse(
            _spotify_oauth_result_page(
                success=False,
                message="Missing authorization code.",
            )
        )

    # Validate CSRF state parameter
    expected_state = await ctx.state.get("spotify_oauth_state")
    if not expected_state or state_param != expected_state:
        logger.warning(
            "Spotify OAuth state mismatch: expected=%s got=%s",
            expected_state, state_param,
        )
        return HTMLResponse(
            _spotify_oauth_result_page(
                success=False,
                message="OAuth state mismatch — possible CSRF attack. Please try again.",
            )
        )

    try:
        client_id = await ctx.state.get("spotify_client_id") or ""
        client_secret = await ctx.state.get("spotify_client_secret") or ""
        redirect_uri = await ctx.state.get("spotify_redirect_uri") or ""
        code_verifier = await ctx.state.get("spotify_code_verifier") or ""

        # Exchange code with PKCE code_verifier
        tokens = await exchange_spotify_code(
            ctx.http,
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

        # Fetch user profile for display name and product tier
        client = SpotifyClient(ctx.http, tokens["access_token"])
        profile = await client.get_user_profile()
        display_name = profile.get("display_name", "")
        product = profile.get("product", "")

        # Store tokens and profile metadata
        await store_spotify_tokens(
            ctx.state,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", ""),
            expires_in=tokens.get("expires_in"),
            display_name=display_name,
            product=product,
        )

        # Clear one-time PKCE/CSRF state
        await ctx.state.set("spotify_oauth_state", "")
        await ctx.state.set("spotify_code_verifier", "")

        logger.info("Spotify OAuth connection established for %s", display_name)
        return HTMLResponse(
            _spotify_oauth_result_page(
                success=True,
                message=f"Connected to Spotify ({display_name})!",
            )
        )

    except (SpotifyAuthError, SpotifyAPIError) as exc:
        logger.warning("Spotify OAuth callback failed: %s", exc)
        return HTMLResponse(
            _spotify_oauth_result_page(
                success=False,
                message=f"Authentication failed: {exc}",
            )
        )
    except Exception as exc:
        logger.error("Unexpected error in Spotify OAuth callback: %s", exc)
        return HTMLResponse(
            _spotify_oauth_result_page(
                success=False,
                message=f"Unexpected error: {exc}",
            )
        )


@media_scheduler_app.route("/_fragments/spotify/disconnect", methods=["POST"])
async def spotify_disconnect_fragment(request: Request):
    """Disconnect from Spotify — clear all auth state, re-render add-source form."""
    ctx = request.app.state.ctx
    await clear_spotify_auth(ctx.state)
    # Also clear stored credentials
    await ctx.state.set("spotify_client_id", "")
    await ctx.state.set("spotify_client_secret", "")
    await ctx.state.set("spotify_redirect_uri", "")
    logger.info("Disconnected from Spotify")
    spotify_status = await get_spotify_connection_status(ctx.state)
    return HTMLResponse(ctx.render_template(
        "add-source.html",
        spotify_connected=spotify_status["connected"],
        spotify_status=spotify_status,
    ))


@media_scheduler_app.route("/_fragments/spotify/status")
async def spotify_status_fragment(request: Request):
    """Return Spotify connection status as an HTML fragment."""
    ctx = request.app.state.ctx
    status = await get_spotify_connection_status(ctx.state)
    connected = status["connected"]
    if connected:
        display_name = status.get("display_name") or "Unknown"
        product = status.get("product") or "free"
        return HTMLResponse(
            f'<div class="ms-info">Connected as {display_name} ({product})</div>'
        )
    return HTMLResponse('<div class="ms-info">Not connected to Spotify</div>')


@media_scheduler_app.route("/_fragments/spotify/playlists")
async def spotify_playlists_fragment(request: Request):
    """Fetch and render the user's Spotify playlists for the subscription selector.

    Requires an active Spotify connection. Refreshes the token if needed.
    Returns HTML <option> elements for a <select> dropdown.
    """
    ctx = request.app.state.ctx
    status = await get_spotify_connection_status(ctx.state)
    if not status["connected"]:
        return HTMLResponse('<option value="">Not connected</option>')

    client_id = await ctx.state.get("spotify_client_id") or ""
    client_secret = await ctx.state.get("spotify_client_secret") or ""

    try:
        access_token = await refresh_spotify_if_expired(
            ctx.http, ctx.state, client_id, client_secret
        )
        client = SpotifyClient(ctx.http, access_token)
        playlists = await client.get_playlists()
    except (SpotifyAuthError, SpotifyAPIError) as exc:
        logger.warning("Failed to fetch Spotify playlists: %s", exc)
        return HTMLResponse(f'<option value="">Error: {exc}</option>')

    if not playlists:
        return HTMLResponse('<option value="">No playlists found</option>')

    options_html = '<option value="">Select a playlist…</option>'
    for pl in playlists:
        pl_id = pl.get("id", "")
        pl_name = pl.get("name", "Untitled")
        track_count = pl.get("tracks", {}).get("total", 0)
        options_html += (
            f'<option value="{pl_id}" data-name="{pl_name}">'
            f'{pl_name} ({track_count} tracks)</option>'
        )
    return HTMLResponse(options_html)


@media_scheduler_app.route("/_fragments/sources/add-spotify", methods=["POST"])
async def add_spotify_fragment(request: Request):
    """Add a Spotify playlist subscription from form data.

    Reads ``playlist_id`` and ``playlist_name`` from the POST body.
    Returns an HTML fragment indicating success, duplicate, or error.
    Emits ``HX-Trigger: sourcesChanged`` on success.
    """
    ctx = request.app.state.ctx
    form = await request.form()
    playlist_id = form.get("playlist_id", "").strip()
    playlist_name = form.get("playlist_name", "").strip() or "Untitled Playlist"

    if not playlist_id:
        return HTMLResponse(
            '<div class="ms-error">Please select a playlist</div>'
        )

    try:
        result = await subscribe_spotify(ctx, playlist_id, playlist_name)
    except Exception as exc:
        logger.warning("subscribe_spotify failed for %s: %s", playlist_id, exc)
        return HTMLResponse(
            f'<div class="ms-error">Failed to subscribe: {exc}</div>'
        )

    if result["status"] == "duplicate":
        return HTMLResponse(
            '<div class="ms-info">Already subscribed to this Spotify playlist</div>'
        )

    response = HTMLResponse(
        '<div class="ms-success">Subscribed to Spotify playlist!</div>'
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
            entry_iri = b.get("entry", {}).get("value", "")
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
                "iri": entry_iri,
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
            entry_iri = b.get("entry", {}).get("value", "")
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
                "iri": entry_iri,
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


# ── Entry status route ──

VALID_ENTRY_STATUSES = {"completed", "skipped", "saved"}


@media_scheduler_app.route("/_fragments/entry/{entry_iri:path}/status", methods=["POST"])
async def entry_status_fragment(request: Request):
    """Update a plan entry's status (completed/skipped/saved).

    Accepts ``status`` form field.  Returns an HTML fragment with
    the updated status badge + action buttons for htmx swap.
    """
    ctx = request.app.state.ctx
    entry_iri_raw = request.path_params.get("entry_iri", "")
    entry_iri = unquote(entry_iri_raw)

    if not entry_iri:
        return HTMLResponse(
            '<div class="ms-error">Missing entry IRI</div>', status_code=400
        )

    form = await request.form()
    status = form.get("status", "").strip()

    if status not in VALID_ENTRY_STATUSES:
        return HTMLResponse(
            f'<div class="ms-error">Invalid status: {status}. '
            f'Must be one of: {", ".join(sorted(VALID_ENTRY_STATUSES))}</div>',
            status_code=400,
        )

    try:
        await ctx.commands.execute(
            "object.patch",
            {"iri": entry_iri, "properties": {f"{MS_NS}entryStatus": status}},
        )
        logger.info("entry_status.updated iri=%s status=%s", entry_iri, status)
    except Exception as exc:
        logger.warning("entry_status.patch_failed iri=%s error=%s", entry_iri, exc)
        return HTMLResponse(
            f'<div class="ms-error">Failed to update status: {exc}</div>',
            status_code=500,
        )

    # Return updated action area fragment
    return HTMLResponse(
        f'<div class="ms-entry-actions ms-entry-done">'
        f'<span class="ms-status-badge ms-status-{status}">{status}</span>'
        f'</div>'
    )


# ── Stats route ──


@media_scheduler_app.route("/_fragments/stats")
async def stats_fragment(request: Request):
    """Stats dashboard fragment — Chart.js charts of listening activity.

    Calls three stats service queries and injects the combined result
    as JSON into the stats.html template for client-side rendering.
    """
    ctx = request.app.state.ctx

    hours_data = await get_hours_by_source_type(ctx)
    top_data = await get_top_sources(ctx, limit=10)
    weekly_data = await get_weekly_trends(ctx, days=7)

    stats = {
        "hours_by_source_type": hours_data,
        "top_sources": top_data,
        "weekly_trends": weekly_data,
    }

    stats_json = json.dumps(stats)
    logger.info(
        "stats.rendered hours=%d top=%d weekly=%d",
        len(hours_data), len(top_data), len(weekly_data),
    )

    return HTMLResponse(ctx.render_template("stats.html", stats_json=stats_json))


# ── JSON suggestion endpoint (mobile) ──


@media_scheduler_app.route("/_fragments/current-suggestion/json")
async def current_suggestion_json(request: Request):
    """JSON endpoint for the current/next media suggestion.

    Returns structured JSON for mobile app consumption:
    ``{title, slot_start, slot_end, status, source_type, source_title,
    enclosure_url, duration_seconds}``.

    Returns ``{"status": "none"}`` when no current/next entry exists.
    """
    ctx = request.app.state.ctx
    today_str = date.today().isoformat()
    now_time = _current_time_str()

    sparql = TODAY_PLAN_SPARQL.replace("{date_str}", today_str)

    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("current-suggestion-json SPARQL failed: %s", exc)
        return JSONResponse({"status": "none", "error": str(exc)})

    current_entry = None
    next_entry = None

    for b in bindings:
        slot_start = b.get("slotStart", {}).get("value", "")
        slot_end = b.get("slotEnd", {}).get("value", "")
        entry_status = b.get("entryStatus", {}).get("value", "pending")
        title = b.get("title", {}).get("value", "Untitled")
        enclosure_url = b.get("enclosureUrl", {}).get("value", "")
        source_title = b.get("sourceTitle", {}).get("value", "")
        source_type = b.get("sourceType", {}).get("value", "")
        duration_raw = b.get("duration", {}).get("value", "")

        if entry_status in ("completed", "skipped", "replaced"):
            continue

        duration_seconds = None
        if duration_raw:
            try:
                duration_seconds = int(duration_raw)
            except (ValueError, TypeError):
                pass

        entry_data = {
            "title": title,
            "slot_start": slot_start,
            "slot_end": slot_end,
            "source_type": source_type,
            "source_title": source_title,
            "enclosure_url": enclosure_url,
            "duration_seconds": duration_seconds,
        }

        if slot_start and slot_end:
            if slot_start <= now_time <= slot_end:
                current_entry = {**entry_data, "status": "now"}
                break
            elif slot_start > now_time and next_entry is None:
                next_entry = {**entry_data, "status": "next"}

    entry = current_entry or next_entry

    if not entry:
        return JSONResponse({"status": "none"})

    return JSONResponse(entry)


# ── Lifecycle hooks ──


@media_scheduler_app.on_startup
async def on_startup(ctx: AppContext):
    """Start context SSE listener on app startup."""
    start_context_listener(ctx)
    logger.info("Media Scheduler app started (context listener spawned): %s", ctx.app_id)


@media_scheduler_app.on_shutdown
async def on_shutdown(ctx: AppContext):
    """Stop context SSE listener on app shutdown."""
    stop_context_listener()
    logger.info("Media Scheduler app stopped (context listener cancelled): %s", ctx.app_id)
