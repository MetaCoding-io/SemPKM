"""YouTube service — URL parsing, Data API v3 client, response-to-MediaItem conversion,
quota tracking, and subscription management.

Pure functions (no SDK dependency):
- ``parse_youtube_url(url)`` — classify and extract identifiers from YouTube URLs
- ``parse_iso8601_duration(raw)`` — convert ISO 8601 duration (PT4M13S) to seconds
- ``video_to_media_item(video, source_iri)`` — convert YouTube API snippet to object.create params

Async / SDK-dependent:
- ``YouTubeClient`` — wraps ``ctx.http`` for YouTube Data API v3 calls
- ``check_quota(state_client, threshold)`` — daily quota tracking
- ``increment_quota(state_client, units)`` — record API usage
- ``reset_quota_if_new_day(state_client)`` — midnight reset
- ``subscribe_youtube(ctx, url, api_key)`` — create YouTube MediaSource
- ``get_existing_item_iris(graph_client, source_iri)`` — SPARQL dedup query

Exception:
- ``YouTubeAPIError`` — raised on YouTube Data API error responses

Constants:
- Reuses ``MS_NS``, ``APP_NS``, ``MEDIA_SOURCE_TYPE``, ``MEDIA_ITEM_TYPE`` from podcast_service
- ``YOUTUBE_SOURCES_SPARQL`` — query for all active YouTube MediaSource objects
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

# ── Constants (same namespace as podcast_service) ──

MS_NS = "urn:sempkm:model:media-scheduler:"
APP_NS = "urn:sempkm:app:media-scheduler:"
MEDIA_SOURCE_TYPE = f"{MS_NS}MediaSource"
MEDIA_ITEM_TYPE = f"{MS_NS}MediaItem"

YOUTUBE_API_BASE = os.environ.get("YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3")

YOUTUBE_SOURCES_SPARQL = f"""
SELECT ?source ?feedUrl ?title ?externalId ?errorCount ?lastError WHERE {{
    ?source a <{MEDIA_SOURCE_TYPE}> .
    ?source <{MS_NS}feedUrl> ?feedUrl .
    ?source <{MS_NS}sourceType> ?sourceType .
    FILTER(?sourceType = "youtube")
    OPTIONAL {{ ?source <http://purl.org/dc/terms/title> ?title }}
    OPTIONAL {{ ?source <{MS_NS}externalId> ?externalId }}
    OPTIONAL {{ ?source <{MS_NS}errorCount> ?errorCount }}
    OPTIONAL {{ ?source <{MS_NS}lastError> ?lastError }}
}}
"""

# ISO 8601 duration regex — matches PT[nH][nM][nS]
_ISO8601_DURATION_RE = re.compile(
    r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", re.IGNORECASE
)


# ── Exceptions ──


class YouTubeAPIError(Exception):
    """Raised by YouTubeClient on API error responses.

    Attributes:
        status_code: HTTP status code from the API response.
        error_type: Error reason string from the API (e.g., 'quotaExceeded',
            'notFound'). May be empty if the response body wasn't parseable.
        message: Human-readable error message.
    """

    def __init__(self, status_code: int, error_type: str, message: str) -> None:
        self.status_code = status_code
        self.error_type = error_type
        self.message = message
        super().__init__(
            f"YouTube API error {status_code} ({error_type}): {message}"
        )


# ── Pure helper functions ──


def mint_source_iri(feed_url: str) -> str:
    """Mint a deterministic MediaSource IRI from a feed URL.

    Uses SHA-256 hash (first 16 hex chars) of the feed URL.
    """
    digest = hashlib.sha256(feed_url.encode("utf-8")).hexdigest()[:16]
    return f"{APP_NS}source-{digest}"


def mint_item_iri(source_iri: str, video_id: str) -> str:
    """Mint a deterministic MediaItem IRI from source IRI + video ID.

    Uses SHA-256 hash (first 16 hex chars) of the concatenation.
    """
    raw = source_iri + video_id
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{APP_NS}item-{digest}"


def parse_youtube_url(url: str | None) -> dict | None:
    """Parse a YouTube URL and classify its type.

    Supported formats:
    - ``https://www.youtube.com/channel/UCxxxxxx`` → channel_id
    - ``https://www.youtube.com/@handlename`` → handle
    - ``https://www.youtube.com/playlist?list=PLxxxxxx`` → playlist
    - ``https://www.youtube.com/c/ChannelName`` → custom
    - Raw ``UC...`` string → raw_channel
    - Raw ``PL...`` string → raw_playlist

    Args:
        url: YouTube URL or raw ID string.

    Returns:
        Dict with ``type`` and ``value`` keys, or None if unrecognized.
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()
    if not url:
        return None

    # Raw channel ID (starts with UC, typically 24 chars)
    if re.match(r"^UC[\w-]{10,}$", url):
        return {"type": "raw_channel", "value": url}

    # Raw playlist ID (starts with PL, UU, FL, etc.)
    if re.match(r"^(?:PL|UU|FL|LL|RD)[\w-]{10,}$", url):
        return {"type": "raw_playlist", "value": url}

    # Try parsing as URL
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    # Must be a YouTube domain
    host = (parsed.hostname or "").lower()
    if host not in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        return None

    path = parsed.path.rstrip("/")

    # /channel/UCxxxxxx
    match = re.match(r"^/channel/(UC[\w-]+)$", path)
    if match:
        return {"type": "channel_id", "value": match.group(1)}

    # /@handlename
    match = re.match(r"^/@([\w.-]+)$", path)
    if match:
        return {"type": "handle", "value": match.group(1)}

    # /c/ChannelName (legacy custom URL)
    match = re.match(r"^/c/([\w.-]+)$", path)
    if match:
        return {"type": "custom", "value": match.group(1)}

    # /playlist?list=PLxxxxxx
    if path in ("/playlist", "/watch"):
        qs = parse_qs(parsed.query)
        list_id = qs.get("list", [None])[0]
        if list_id:
            return {"type": "playlist", "value": list_id}

    return None


def parse_iso8601_duration(raw: str | None) -> int | None:
    """Parse an ISO 8601 duration string to seconds.

    Handles YouTube's format: ``PT4M13S``, ``PT1H2M30S``, ``PT45S``, ``PT1H``.

    Args:
        raw: ISO 8601 duration string, or None.

    Returns:
        Duration in seconds as integer, or None if parsing fails.
    """
    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    match = _ISO8601_DURATION_RE.match(raw)
    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    total = hours * 3600 + minutes * 60 + seconds
    return total


def video_to_media_item(video: dict, source_iri: str) -> dict:
    """Convert a YouTube API video snippet to a MediaItem object.create params dict.

    Expected ``video`` structure (from playlistItems.list snippet):
    - ``snippet.title`` → dcterms:title
    - ``snippet.description`` → dcterms:description
    - ``snippet.publishedAt`` → dcterms:created
    - ``snippet.thumbnails.medium.url`` → ms:thumbnailUrl
    - ``snippet.resourceId.videoId`` → ms:externalId + watch URL
    - ``duration_seconds`` (injected after videos.list call) → ms:duration

    Args:
        video: Dict with at least ``snippet`` and optionally ``duration_seconds``.
        source_iri: IRI of the parent MediaSource.

    Returns:
        Dict with ``iri``, ``type``, and ``properties`` keys.
    """
    snippet = video.get("snippet", {})
    video_id = snippet.get("resourceId", {}).get("videoId", "")

    # Fall back to top-level id if resourceId is missing (direct videos.list response)
    if not video_id:
        video_id = video.get("id", "")

    item_iri = mint_item_iri(source_iri, video_id)

    properties: dict[str, Any] = {}

    # Title
    title = snippet.get("title")
    if title:
        properties["dcterms:title"] = title

    # Description
    description = snippet.get("description")
    if description:
        properties["dcterms:description"] = description

    # Published date
    published_at = snippet.get("publishedAt")
    if published_at:
        properties["dcterms:created"] = published_at

    # Thumbnail — prefer medium, fall back to default
    thumbnails = snippet.get("thumbnails", {})
    thumb_url = None
    for size in ("medium", "high", "default"):
        thumb = thumbnails.get(size)
        if isinstance(thumb, dict) and thumb.get("url"):
            thumb_url = thumb["url"]
            break
    if thumb_url:
        properties[f"{MS_NS}thumbnailUrl"] = thumb_url

    # External ID
    if video_id:
        properties[f"{MS_NS}externalId"] = video_id

    # Watch URL
    if video_id:
        properties[f"{MS_NS}enclosureUrl"] = f"https://www.youtube.com/watch?v={video_id}"

    # Duration (injected separately after videos.list batch call)
    duration_seconds = video.get("duration_seconds")
    if duration_seconds is not None:
        properties[f"{MS_NS}duration"] = duration_seconds

    # Fixed properties
    properties[f"{MS_NS}status"] = "queued"
    properties[f"{MS_NS}mediaSource"] = source_iri

    return {
        "iri": item_iri,
        "type": MEDIA_ITEM_TYPE,
        "properties": properties,
    }


# ── YouTubeClient class ──


class YouTubeClient:
    """Async client for YouTube Data API v3.

    Wraps an HTTP client (e.g., SDK HttpClient or httpx.AsyncClient)
    to call channels.list, playlistItems.list, and videos.list.

    Args:
        http_client: Async HTTP client with ``.get()`` method.
        api_key: Google API key with YouTube Data API v3 enabled.
    """

    def __init__(self, http_client: Any, api_key: str) -> None:
        self.http = http_client
        self.api_key = api_key

    async def _get(self, endpoint: str, params: dict) -> dict:
        """Make an authenticated GET request to the YouTube API.

        Args:
            endpoint: API endpoint path (e.g., 'channels').
            params: Query parameters (api_key added automatically).

        Returns:
            Parsed JSON response dict.

        Raises:
            YouTubeAPIError: On HTTP error responses.
        """
        params["key"] = self.api_key
        url = f"{YOUTUBE_API_BASE}/{endpoint}"

        logger.debug("YouTube API request: GET %s params=%s", endpoint, {
            k: v for k, v in params.items() if k != "key"
        })

        response = await self.http.get(url, params=params)

        if response.status_code >= 400:
            # Try to extract error details from response body
            error_type = ""
            message = f"HTTP {response.status_code}"
            try:
                body = response.json()
                error_info = body.get("error", {})
                errors = error_info.get("errors", [])
                if errors:
                    error_type = errors[0].get("reason", "")
                message = error_info.get("message", message)
            except Exception:
                pass

            logger.warning(
                "YouTube API error: %d %s — %s (endpoint=%s)",
                response.status_code, error_type, message, endpoint,
            )
            raise YouTubeAPIError(response.status_code, error_type, message)

        return response.json()

    async def resolve_channel(
        self,
        channel_id: str | None = None,
        handle: str | None = None,
        username: str | None = None,
    ) -> str:
        """Resolve a channel identifier to its uploads playlist ID.

        Exactly one of ``channel_id``, ``handle``, or ``username`` must be
        provided.

        Args:
            channel_id: YouTube channel ID (e.g., ``UCxxxxxx``).
            handle: YouTube handle (e.g., ``@handlename`` without the @).
            username: Legacy custom URL username (from /c/ URLs).

        Returns:
            The uploads playlist ID (e.g., ``UUxxxxxx``).

        Raises:
            YouTubeAPIError: On API errors or if no channel is found.
        """
        params: dict[str, str] = {"part": "contentDetails"}

        if channel_id:
            params["id"] = channel_id
        elif handle:
            params["forHandle"] = handle
        elif username:
            params["forUsername"] = username
        else:
            raise ValueError("One of channel_id, handle, or username is required")

        data = await self._get("channels", params)

        items = data.get("items", [])
        if not items:
            identifier = channel_id or handle or username
            raise YouTubeAPIError(
                404, "notFound",
                f"No channel found for identifier: {identifier}",
            )

        uploads_playlist = (
            items[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads_playlist:
            raise YouTubeAPIError(
                404, "notFound",
                "Channel found but no uploads playlist available",
            )

        logger.info(
            "Resolved channel → uploads playlist: %s",
            uploads_playlist,
        )
        return uploads_playlist

    async def list_playlist_items(
        self, playlist_id: str, max_results: int = 50
    ) -> list[dict]:
        """List video snippets from a YouTube playlist.

        Args:
            playlist_id: YouTube playlist ID.
            max_results: Maximum items to return (capped at 50 by API).

        Returns:
            List of item dicts with ``snippet`` and ``contentDetails`` keys.
        """
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": str(min(max_results, 50)),
        }

        data = await self._get("playlistItems", params)

        items = data.get("items", [])
        logger.info(
            "Listed %d items from playlist %s (quota cost: 1 unit)",
            len(items), playlist_id,
        )
        return items

    async def get_video_durations(self, video_ids: list[str]) -> dict[str, int]:
        """Get video durations in a batch call.

        Args:
            video_ids: List of YouTube video IDs (max 50 per call).

        Returns:
            Dict mapping video_id → duration in seconds.
        """
        if not video_ids:
            return {}

        # YouTube API accepts comma-separated IDs, max 50
        batch_ids = video_ids[:50]
        params = {
            "part": "contentDetails",
            "id": ",".join(batch_ids),
        }

        data = await self._get("videos", params)

        durations: dict[str, int] = {}
        for item in data.get("items", []):
            vid_id = item.get("id", "")
            raw_duration = item.get("contentDetails", {}).get("duration", "")
            seconds = parse_iso8601_duration(raw_duration)
            if seconds is not None:
                durations[vid_id] = seconds

        logger.info(
            "Fetched durations for %d/%d videos (quota cost: 1 unit)",
            len(durations), len(batch_ids),
        )
        return durations


# ── Quota tracking helpers ──


async def reset_quota_if_new_day(state_client: Any) -> None:
    """Reset YouTube API quota counter if the calendar day has changed.

    Compares ``youtube_quota_reset_date`` in StateClient against today's
    date (UTC). If different or missing, resets ``youtube_quota_used`` to 0
    and updates the reset date.
    """
    today = date.today().isoformat()
    stored_date = await state_client.get("youtube_quota_reset_date")

    if stored_date != today:
        await state_client.set("youtube_quota_used", "0")
        await state_client.set("youtube_quota_reset_date", today)
        logger.info("YouTube quota reset for new day: %s", today)


async def check_quota(state_client: Any, threshold: int = 8000) -> bool:
    """Check if YouTube API quota usage is under the threshold.

    Calls ``reset_quota_if_new_day()`` first to handle midnight rollover.

    Args:
        state_client: SDK StateClient instance.
        threshold: Maximum units allowed per day (default 8000 of 10000 limit).

    Returns:
        True if usage is under threshold and API calls are safe.
    """
    await reset_quota_if_new_day(state_client)

    raw = await state_client.get("youtube_quota_used")
    used = int(raw) if raw and raw.isdigit() else 0

    under = used < threshold
    if not under:
        logger.warning(
            "YouTube quota limit reached: %d/%d used (threshold=%d)",
            used, threshold, threshold,
        )
    return under


async def increment_quota(state_client: Any, units: int) -> None:
    """Add units to the daily YouTube API quota counter.

    Args:
        state_client: SDK StateClient instance.
        units: Number of quota units consumed.
    """
    raw = await state_client.get("youtube_quota_used")
    current = int(raw) if raw and raw.isdigit() else 0
    new_total = current + units
    await state_client.set("youtube_quota_used", str(new_total))
    logger.debug("YouTube quota: +%d units → %d total", units, new_total)


# ── Async / SDK-dependent functions ──


async def get_existing_item_iris(graph_client: Any, source_iri: str) -> set[str]:
    """Query the triplestore for existing MediaItem IRIs from a given source.

    Used for deduplication — same pattern as podcast_service.

    Args:
        graph_client: SDK GraphClient instance with SPARQL read access.
        source_iri: IRI of the MediaSource to check items for.

    Returns:
        Set of MediaItem IRI strings already in the triplestore.
    """
    sparql = f"""
        SELECT ?item WHERE {{
            ?item a <{MEDIA_ITEM_TYPE}> .
            ?item <{MS_NS}mediaSource> <{source_iri}> .
        }}
    """
    result = await graph_client.query(sparql)

    iris: set[str] = set()
    bindings = result.get("results", {}).get("bindings", [])
    for binding in bindings:
        item = binding.get("item", {})
        value = item.get("value")
        if value:
            iris.add(value)
    return iris


async def check_source_exists(graph_client: Any, feed_url: str) -> str | None:
    """Check if a MediaSource for the given feed URL already exists.

    Args:
        graph_client: SDK GraphClient instance.
        feed_url: The feed URL to check.

    Returns:
        The source IRI if it exists, None otherwise.
    """
    sparql = f"""
    SELECT ?source WHERE {{
        ?source a <{MEDIA_SOURCE_TYPE}> .
        ?source <{MS_NS}feedUrl> "{feed_url}" .
    }} LIMIT 1
    """
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if bindings:
        return bindings[0].get("source", {}).get("value")
    return None


async def subscribe_youtube(
    ctx: Any, url: str, api_key: str
) -> dict:
    """Create a YouTube MediaSource subscription.

    Validates both the URL format and the API key by making a test API
    call to resolve the channel/playlist. If the URL points to a channel
    (any format), resolves it to the uploads playlist ID for efficient
    polling.

    Args:
        ctx: SDK AppContext with ``commands``, ``graph``, ``state``,
            and ``http`` clients.
        url: YouTube channel or playlist URL.
        api_key: Google API key with YouTube Data API v3 enabled.

    Returns:
        Dict with ``status`` ("created" or "duplicate"), ``iri``, and
        ``playlist_id`` (the resolved uploads/playlist ID for polling).

    Raises:
        ValueError: If the URL format is not recognized.
        YouTubeAPIError: If the API key is invalid or the channel/playlist
            is not found.
    """
    parsed = parse_youtube_url(url)
    if parsed is None:
        raise ValueError(f"Unrecognized YouTube URL: {url}")

    # Check for duplicate
    existing = await check_source_exists(ctx.graph, url)
    if existing:
        logger.info("YouTube source already exists for %s: %s", url, existing)
        return {"status": "duplicate", "iri": existing, "playlist_id": ""}

    # Create client and resolve to playlist ID
    client = YouTubeClient(ctx.http, api_key)
    playlist_id: str

    url_type = parsed["type"]
    value = parsed["value"]

    if url_type == "playlist":
        # Direct playlist URL — validate by listing 1 item
        playlist_id = value
        await client.list_playlist_items(playlist_id, max_results=1)
        logger.info("Validated playlist: %s", playlist_id)

    elif url_type == "raw_playlist":
        playlist_id = value
        await client.list_playlist_items(playlist_id, max_results=1)
        logger.info("Validated raw playlist: %s", playlist_id)

    elif url_type == "channel_id" or url_type == "raw_channel":
        playlist_id = await client.resolve_channel(channel_id=value)

    elif url_type == "handle":
        playlist_id = await client.resolve_channel(handle=value)

    elif url_type == "custom":
        playlist_id = await client.resolve_channel(username=value)

    else:
        raise ValueError(f"Unsupported URL type: {url_type}")

    # Save API key to StateClient (idempotent — overwrite is fine)
    await ctx.state.set("youtube_api_key", api_key)

    # Create MediaSource
    iri = mint_source_iri(url)
    properties: dict[str, Any] = {
        f"{MS_NS}feedUrl": url,
        "dcterms:title": url,
        f"{MS_NS}sourceType": "youtube",
        f"{MS_NS}externalId": playlist_id,
        f"{MS_NS}errorCount": 0,
        f"{MS_NS}lastError": "",
    }
    await ctx.commands.execute(
        "object.create",
        {"iri": iri, "type": MEDIA_SOURCE_TYPE, "properties": properties},
    )

    logger.info(
        "Created YouTube source for %s (playlist=%s): %s",
        url, playlist_id, iri,
    )
    return {"status": "created", "iri": iri, "playlist_id": playlist_id}
