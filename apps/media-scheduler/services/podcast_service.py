"""Podcast service — subscription management, IRI minting, and feedparser-to-RDF conversion.

Pure functions (no SDK dependency):
- ``mint_source_iri(feed_url)`` — deterministic IRI from feed URL
- ``mint_item_iri(source_iri, episode_id)`` — deterministic IRI from source + episode ID
- ``entry_to_media_item(entry, source_iri)`` — convert feedparser entry to object.create params
- ``parse_duration(raw)`` — parse iTunes-style duration string to seconds

Async / SDK-dependent:
- ``get_existing_item_iris(graph_client, source_iri)`` — SPARQL dedup query
- ``subscribe_podcast(ctx, feed_url, title)`` — create MediaSource via object.create
- ``unsubscribe_source(ctx, source_iri)`` — soft-delete via object.patch
- ``update_source_state(ctx, source_iri, ...)`` — persist poll state

Constants:
- ``SOURCES_WITH_STATE_SPARQL`` — query for all active MediaSource objects with polling state
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from time import mktime, struct_time
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ──

MS_NS = "urn:sempkm:model:media-scheduler:"
APP_NS = "urn:sempkm:app:media-scheduler:"
MEDIA_SOURCE_TYPE = f"{MS_NS}MediaSource"
MEDIA_ITEM_TYPE = f"{MS_NS}MediaItem"

# ── SPARQL queries ──

SOURCES_WITH_STATE_SPARQL = f"""
SELECT ?source ?feedUrl ?title ?sourceType ?etag ?lastModified ?errorCount ?lastError WHERE {{
    ?source a <{MEDIA_SOURCE_TYPE}> .
    ?source <{MS_NS}feedUrl> ?feedUrl .
    ?source <{MS_NS}sourceType> ?sourceType .
    OPTIONAL {{ ?source <http://purl.org/dc/terms/title> ?title }}
    OPTIONAL {{ ?source <{MS_NS}etag> ?etag }}
    OPTIONAL {{ ?source <{MS_NS}lastModifiedHeader> ?lastModified }}
    OPTIONAL {{ ?source <{MS_NS}errorCount> ?errorCount }}
    OPTIONAL {{ ?source <{MS_NS}lastError> ?lastError }}
}}
"""


# ── Pure helper functions ──


def mint_source_iri(feed_url: str) -> str:
    """Mint a deterministic MediaSource IRI from a feed URL.

    Uses SHA-256 hash (first 16 hex chars) of the feed URL for
    dedup-friendly, deterministic IRIs.

    Args:
        feed_url: The podcast RSS feed URL.

    Returns:
        IRI string like ``urn:sempkm:app:media-scheduler:source-{hash}``.
    """
    digest = hashlib.sha256(feed_url.encode("utf-8")).hexdigest()[:16]
    return f"{APP_NS}source-{digest}"


def mint_item_iri(source_iri: str, episode_id: str) -> str:
    """Mint a deterministic MediaItem IRI from source IRI + episode ID.

    Uses SHA-256 hash (first 16 hex chars) of the concatenated
    source_iri + episode_id.

    Args:
        source_iri: IRI of the parent MediaSource.
        episode_id: Unique episode identifier (GUID, entry.id, or entry.link).

    Returns:
        IRI string like ``urn:sempkm:app:media-scheduler:item-{hash}``.
    """
    raw = source_iri + episode_id
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{APP_NS}item-{digest}"


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


def parse_duration(raw: str | None) -> int | None:
    """Parse an iTunes-style duration string to seconds.

    Supports formats:
    - ``HH:MM:SS`` → hours * 3600 + minutes * 60 + seconds
    - ``MM:SS`` → minutes * 60 + seconds
    - ``SSSS`` (bare integer) → seconds

    Args:
        raw: Duration string, or None.

    Returns:
        Duration in seconds as integer, or None if parsing fails.
    """
    if not raw:
        return None

    raw = raw.strip()

    # Try bare integer first
    try:
        return int(raw)
    except ValueError:
        pass

    # Try HH:MM:SS or MM:SS
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        pass

    return None


def entry_to_media_item(entry: dict, source_iri: str) -> dict:
    """Convert a feedparser entry to a MediaItem object.create params dict.

    Maps feedparser fields to RDF properties using the media-scheduler
    ontology namespace. This is a pure function with no SDK dependency.

    Field mapping:
    - ``entry.title`` → ``dcterms:title``
    - ``entry.enclosures[0].href`` (preferred) or ``entry.link`` → ``ms:enclosureUrl``
    - ``entry.published_parsed`` → ``dcterms:created``
    - ``entry.summary`` → ``dcterms:description``
    - ``entry.id`` or ``entry.link`` → ``ms:externalId``
    - ``entry.itunes_duration`` → ``ms:duration`` (parsed to seconds)
    - ``entry.image.href`` → ``ms:thumbnailUrl``
    - Fixed: ``ms:status`` = "queued"
    - Fixed: ``ms:mediaSource`` = source_iri

    Args:
        entry: A single feedparser entry dict.
        source_iri: IRI of the parent MediaSource object.

    Returns:
        Dict with ``iri``, ``type``, and ``properties`` keys suitable
        for passing to ``CommandClient.execute("object.create", ...)``.
    """
    # Determine unique entry ID (prefer entry.id, fall back to entry.link)
    entry_id = entry.get("id") or entry.get("link") or ""
    item_iri = mint_item_iri(source_iri, entry_id)

    properties: dict[str, Any] = {}

    # Title
    title = entry.get("title")
    if title:
        properties["dcterms:title"] = title

    # Enclosure URL — prefer enclosures[0].href, fall back to entry.link
    enclosures = entry.get("enclosures", [])
    if enclosures and isinstance(enclosures, list) and len(enclosures) > 0:
        enc = enclosures[0]
        href = enc.get("href") if isinstance(enc, dict) else getattr(enc, "href", None)
        if href:
            properties[f"{MS_NS}enclosureUrl"] = href
    if f"{MS_NS}enclosureUrl" not in properties:
        link = entry.get("link")
        if link:
            properties[f"{MS_NS}enclosureUrl"] = link

    # Published date
    published = _struct_time_to_iso(entry.get("published_parsed"))
    if published:
        properties["dcterms:created"] = published

    # Description / summary
    summary = entry.get("summary")
    if summary:
        properties["dcterms:description"] = summary

    # External ID for dedup reference
    raw_entry_id = entry.get("id") or entry.get("link")
    if raw_entry_id:
        properties[f"{MS_NS}externalId"] = raw_entry_id

    # Duration (iTunes extension)
    itunes_duration = entry.get("itunes_duration")
    duration_seconds = parse_duration(itunes_duration)
    if duration_seconds is not None:
        properties[f"{MS_NS}duration"] = duration_seconds

    # Thumbnail
    image = entry.get("image")
    if isinstance(image, dict) and image.get("href"):
        properties[f"{MS_NS}thumbnailUrl"] = image["href"]

    # Fixed properties
    properties[f"{MS_NS}status"] = "queued"
    properties[f"{MS_NS}mediaSource"] = source_iri

    return {
        "iri": item_iri,
        "type": MEDIA_ITEM_TYPE,
        "properties": properties,
    }


# ── Async / SDK-dependent functions ──


async def get_existing_item_iris(graph_client: Any, source_iri: str) -> set[str]:
    """Query the triplestore for existing MediaItem IRIs from a given source.

    Used for deduplication — returns the set of item IRIs already
    created for this media source so we can skip them.

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
        graph_client: SDK GraphClient instance with SPARQL read access.
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


async def subscribe_podcast(
    ctx: Any, feed_url: str, title: str | None = None
) -> dict:
    """Create a MediaSource subscription for the given podcast feed URL.

    Checks for duplicates first via SPARQL. If the source already
    exists, returns ``{"status": "duplicate", "iri": existing_iri}``.

    Args:
        ctx: SDK AppContext with ``commands`` and ``graph`` clients.
        feed_url: The podcast RSS feed URL.
        title: Optional human-readable title. Defaults to feed_url.

    Returns:
        Dict with ``status`` ("created" or "duplicate") and ``iri``.
    """
    existing = await check_source_exists(ctx.graph, feed_url)
    if existing:
        logger.info("Source already exists for %s: %s", feed_url, existing)
        return {"status": "duplicate", "iri": existing}

    iri = mint_source_iri(feed_url)
    properties: dict[str, Any] = {
        f"{MS_NS}feedUrl": feed_url,
        "dcterms:title": title or feed_url,
        f"{MS_NS}sourceType": "podcast",
        f"{MS_NS}errorCount": 0,
        f"{MS_NS}lastError": "",
    }
    await ctx.commands.execute(
        "object.create",
        {"iri": iri, "type": MEDIA_SOURCE_TYPE, "properties": properties},
    )
    logger.info("Created podcast source for %s: %s", feed_url, iri)
    return {"status": "created", "iri": iri}


async def unsubscribe_source(ctx: Any, source_iri: str) -> dict:
    """Remove a media source by patching its status to inactive.

    Uses object.patch to set a flag rather than deleting, preserving
    the source and its discovered items for reference.

    Args:
        ctx: SDK AppContext with ``commands`` client.
        source_iri: IRI of the MediaSource to deactivate.

    Returns:
        Dict with ``status`` ("unsubscribed") and ``iri``.
    """
    await ctx.commands.execute(
        "object.patch",
        {"iri": source_iri, "properties": {f"{MS_NS}sourceType": "inactive"}},
    )
    logger.info("Unsubscribed (soft-delete): %s", source_iri)
    return {"status": "unsubscribed", "iri": source_iri}


async def update_source_state(
    ctx: Any,
    source_iri: str,
    last_polled: str | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
    error_count: int | None = None,
    last_error: str | None = None,
) -> None:
    """Update source poll state (etag, lastPolled, error tracking).

    Builds an ``object.patch`` payload from non-None arguments. Skips the
    call entirely if all params are None.

    Args:
        ctx: SDK AppContext with ``commands`` client.
        source_iri: IRI of the MediaSource to update.
        last_polled: ISO 8601 timestamp of last poll attempt.
        etag: ETag header value from the most recent fetch.
        last_modified: Last-Modified header value from the most recent fetch.
        error_count: Number of consecutive errors (0 on success).
        last_error: Error message string (empty string on success).
    """
    properties: dict[str, Any] = {}
    if last_polled is not None:
        properties[f"{MS_NS}lastPolled"] = last_polled
    if etag is not None:
        properties[f"{MS_NS}etag"] = etag
    if last_modified is not None:
        properties[f"{MS_NS}lastModifiedHeader"] = last_modified
    if error_count is not None:
        properties[f"{MS_NS}errorCount"] = error_count
    if last_error is not None:
        properties[f"{MS_NS}lastError"] = last_error

    if not properties:
        logger.debug(
            "update_source_state: all params None, skipping for %s", source_iri
        )
        return

    await ctx.commands.execute(
        "object.patch",
        {"iri": source_iri, "properties": properties},
    )
    logger.debug(
        "Updated source state for %s: %s", source_iri, list(properties.keys())
    )
