"""Spotify service — OAuth 2.0 with PKCE, API client, URL parsing,
track-to-MediaItem conversion, and subscription management.

Pure functions (no SDK dependency):
- ``generate_code_verifier()`` — PKCE code verifier (RFC 7636)
- ``generate_code_challenge(verifier)`` — PKCE code challenge (S256)
- ``build_spotify_authorize_url(...)`` — OAuth authorize URL with PKCE
- ``parse_spotify_url(url)`` — extract playlist ID from Spotify URLs
- ``track_to_media_item(track, source_iri)`` — convert Spotify track to object.create params
- ``mint_source_iri(feed_url)`` — deterministic MediaSource IRI
- ``mint_item_iri(source_iri, track_id)`` — deterministic MediaItem IRI

Async / SDK-dependent:
- ``exchange_spotify_code(...)`` — token exchange with code_verifier
- ``refresh_spotify_token(...)`` — refresh expired access token
- ``refresh_spotify_if_expired(...)`` — check expiry + refresh if needed
- ``store_spotify_tokens(...)`` — persist auth state
- ``get_spotify_connection_status(...)`` — read connection state
- ``clear_spotify_auth(...)`` — wipe auth state
- ``SpotifyClient`` — wraps ``ctx.http`` for Spotify Web API calls
- ``subscribe_spotify(ctx, playlist_id, playlist_name)`` — create MediaSource
- ``check_source_exists_spotify(graph_client, playlist_id)`` — dedup check
- ``get_existing_item_iris(graph_client, source_iri)`` — SPARQL dedup query

Exceptions:
- ``SpotifyAPIError`` — raised on Spotify Web API error responses
- ``SpotifyAuthError`` — raised on OAuth flow failures

Constants:
- Reuses ``MS_NS``, ``APP_NS``, ``MEDIA_SOURCE_TYPE``, ``MEDIA_ITEM_TYPE`` from podcast_service
- ``SPOTIFY_SOURCES_SPARQL`` — query for all active Spotify MediaSource objects
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlparse

# ── Constants (same namespace as podcast_service) ──

MS_NS = "urn:sempkm:model:media-scheduler:"
APP_NS = "urn:sempkm:app:media-scheduler:"
MEDIA_SOURCE_TYPE = f"{MS_NS}MediaSource"
MEDIA_ITEM_TYPE = f"{MS_NS}MediaItem"

SPOTIFY_API_BASE = os.environ.get("SPOTIFY_API_URL", "https://api.spotify.com/v1")
SPOTIFY_AUTHORIZE_URL = os.environ.get("SPOTIFY_AUTHORIZE_URL", "https://accounts.spotify.com/authorize")
SPOTIFY_TOKEN_URL = os.environ.get("SPOTIFY_TOKEN_URL", "https://accounts.spotify.com/api/token")

SPOTIFY_SCOPES = (
    "playlist-read-private playlist-read-collaborative "
    "user-read-playback-state user-read-private"
)

# State keys managed by this module
AUTH_STATE_KEYS = (
    "spotify_access_token",
    "spotify_refresh_token",
    "spotify_token_expiry",
    "spotify_display_name",
    "spotify_product",
    "spotify_code_verifier",
)

SPOTIFY_SOURCES_SPARQL = f"""
SELECT ?source ?feedUrl ?title ?externalId ?errorCount ?lastError WHERE {{
    ?source a <{MEDIA_SOURCE_TYPE}> .
    ?source <{MS_NS}feedUrl> ?feedUrl .
    ?source <{MS_NS}sourceType> ?sourceType .
    FILTER(?sourceType = "spotify")
    OPTIONAL {{ ?source <http://purl.org/dc/terms/title> ?title }}
    OPTIONAL {{ ?source <{MS_NS}externalId> ?externalId }}
    OPTIONAL {{ ?source <{MS_NS}errorCount> ?errorCount }}
    OPTIONAL {{ ?source <{MS_NS}lastError> ?lastError }}
}}
"""

# Loggers — split by concern for structured filtering
logger_auth = logging.getLogger("spotify.auth")
logger_client = logging.getLogger("spotify.client")
logger_poll = logging.getLogger("spotify.poll")


# ── Exceptions ──


class SpotifyAPIError(Exception):
    """Raised by SpotifyClient on API error responses.

    Attributes:
        status_code: HTTP status code from the API response.
        error_type: Error reason string from Spotify (e.g., 'invalid_client').
        message: Human-readable error message.
    """

    def __init__(self, status_code: int, error_type: str, message: str) -> None:
        self.status_code = status_code
        self.error_type = error_type
        self.message = message
        super().__init__(
            f"Spotify API error {status_code} ({error_type}): {message}"
        )


class SpotifyAuthError(Exception):
    """Raised on OAuth flow failures (token exchange, refresh).

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code from the token endpoint.
        response_body: Raw response body for debugging.
    """

    def __init__(
        self, message: str, status_code: int = 0, response_body: str = ""
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


# ── PKCE helpers (RFC 7636) ──


def generate_code_verifier() -> str:
    """Generate a PKCE code_verifier using cryptographic randomness.

    Returns a 43-character URL-safe base64 string (from 32 random bytes).
    """
    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier: str) -> str:
    """Generate a PKCE code_challenge from a code_verifier.

    Uses SHA-256 hash + base64url encoding with padding stripped (S256 method).

    Args:
        verifier: The code_verifier string.

    Returns:
        Base64url-encoded SHA-256 hash without padding.
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return challenge


# ── OAuth functions ──


def build_spotify_authorize_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
) -> str:
    """Build the Spotify OAuth 2.0 + PKCE authorization URL.

    Args:
        client_id: Spotify application client ID.
        redirect_uri: Callback URL after authorization (must be HTTPS in production).
        state: CSRF state parameter.
        code_challenge: PKCE code challenge (S256).

    Returns:
        Full authorization URL with query parameters.
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SPOTIFY_SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }
    return f"{SPOTIFY_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_spotify_code(
    http_client: Any,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict:
    """Exchange an OAuth authorization code for access and refresh tokens.

    Uses PKCE: sends the code_verifier alongside the authorization code.

    Args:
        http_client: Async HTTP client with ``.post()`` method.
        code: Authorization code from OAuth callback.
        client_id: Spotify application client ID.
        client_secret: Spotify application client secret.
        redirect_uri: Same redirect_uri used in the authorize request.
        code_verifier: PKCE code verifier generated during authorize step.

    Returns:
        Dict with ``access_token``, ``refresh_token``, ``expires_in``.

    Raises:
        SpotifyAuthError: On non-200 response from the token endpoint.
    """
    resp = await http_client.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )

    if resp.status_code != 200:
        logger_auth.warning(
            "Spotify token exchange failed: status=%d", resp.status_code
        )
        raise SpotifyAuthError(
            f"Spotify token exchange failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text,
        )

    data = resp.json()
    logger_auth.info("Spotify token exchange succeeded")
    return {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in"),
    }


async def refresh_spotify_token(
    http_client: Any,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Refresh an expired Spotify access token.

    Args:
        http_client: Async HTTP client with ``.post()`` method.
        refresh_token: OAuth refresh token from initial authorization.
        client_id: Spotify application client ID.
        client_secret: Spotify application client secret.

    Returns:
        Dict with ``access_token`` and ``expires_in``.

    Raises:
        SpotifyAuthError: On non-200 response from the token endpoint.
    """
    resp = await http_client.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )

    if resp.status_code != 200:
        logger_auth.warning(
            "Spotify token refresh failed: status=%d", resp.status_code
        )
        raise SpotifyAuthError(
            f"Spotify token refresh failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text,
        )

    data = resp.json()
    logger_auth.info("Spotify token refreshed successfully")
    return {
        "access_token": data.get("access_token", ""),
        "expires_in": data.get("expires_in"),
    }


async def refresh_spotify_if_expired(
    http_client: Any,
    state_client: Any,
    client_id: str,
    client_secret: str,
) -> str:
    """Check token expiry and refresh if needed.

    Reads ``spotify_token_expiry`` from state, compares against now + 5min buffer.
    If expired (or no expiry recorded), refreshes and stores the new token.

    Args:
        http_client: Async HTTP client for making the token request.
        state_client: SDK StateClient for reading/writing auth tokens.
        client_id: Spotify application client ID.
        client_secret: Spotify application client secret.

    Returns:
        Current valid access token.

    Raises:
        SpotifyAuthError: If refresh fails or no refresh token available.
    """
    access_token = await state_client.get("spotify_access_token")
    token_expiry = await state_client.get("spotify_token_expiry")

    # Check if token is still valid (with 5-minute buffer)
    if access_token and token_expiry:
        try:
            expiry_dt = datetime.fromisoformat(token_expiry)
            now = datetime.now(timezone.utc)
            # Ensure timezone-aware comparison (KNOWLEDGE: naive datetime issue)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
            if now + timedelta(minutes=5) < expiry_dt:
                return access_token
        except (ValueError, TypeError):
            pass  # Invalid expiry format — refresh anyway

    # Need to refresh
    refresh_token = await state_client.get("spotify_refresh_token")
    if not refresh_token:
        raise SpotifyAuthError(
            "No Spotify refresh token available",
            status_code=401,
            response_body="",
        )

    result = await refresh_spotify_token(
        http_client, refresh_token, client_id, client_secret
    )

    new_access_token = result["access_token"]
    expires_in = result.get("expires_in")
    await state_client.set("spotify_access_token", new_access_token)
    if expires_in is not None:
        new_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        await state_client.set("spotify_token_expiry", new_expiry.isoformat())

    return new_access_token


async def store_spotify_tokens(
    state_client: Any,
    access_token: str,
    refresh_token: str,
    expires_in: int | None,
    display_name: str,
    product: str,
) -> None:
    """Persist Spotify auth tokens and metadata in the app's state store.

    Computes ``spotify_token_expiry`` as an ISO 8601 timestamp (UTC, timezone-aware)
    from ``expires_in`` seconds.

    Args:
        state_client: SDK StateClient instance.
        access_token: OAuth access token (not logged).
        refresh_token: OAuth refresh token (not logged).
        expires_in: Token lifetime in seconds from Spotify's response.
        display_name: Spotify user's display name.
        product: Spotify product tier (e.g., 'premium', 'free').
    """
    await state_client.set("spotify_access_token", access_token)
    await state_client.set("spotify_refresh_token", refresh_token)
    await state_client.set("spotify_display_name", display_name)
    await state_client.set("spotify_product", product)

    if expires_in is not None:
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        await state_client.set("spotify_token_expiry", token_expiry.isoformat())

    logger_auth.info(
        "Spotify tokens stored for display_name=%s product=%s",
        display_name, product,
    )


async def get_spotify_connection_status(state_client: Any) -> dict:
    """Read current Spotify connection state from the app's state store.

    Returns:
        Dict with keys: ``connected`` (bool), ``display_name`` (str|None),
        ``product`` (str|None), ``token_expiry`` (str|None).
    """
    display_name = await state_client.get("spotify_display_name")
    product = await state_client.get("spotify_product")
    token_expiry = await state_client.get("spotify_token_expiry")
    access_token = await state_client.get("spotify_access_token")

    # Connected if we have a non-empty access token.
    # After clear_spotify_auth, values are "" (empty string) not None,
    # because StateClient has no delete — only set.
    connected = bool(access_token)

    return {
        "connected": connected,
        "display_name": display_name or None,
        "product": product or None,
        "token_expiry": token_expiry or None,
    }


async def clear_spotify_auth(state_client: Any) -> None:
    """Remove all Spotify auth-related state keys.

    Sets each key to an empty string (StateClient.set is the only
    mutation primitive — there's no delete).
    """
    for key in AUTH_STATE_KEYS:
        await state_client.set(key, "")
    logger_auth.info("Spotify auth state cleared")


# ── SpotifyClient class ──


class SpotifyClient:
    """Async client for the Spotify Web API.

    Wraps an HTTP client (e.g., SDK HttpClient or httpx.AsyncClient)
    to call user profile, playlist listing, and track listing endpoints.
    Uses Bearer token authentication.

    Args:
        http_client: Async HTTP client with ``.get()`` method.
        access_token: Valid Spotify OAuth access token.
    """

    def __init__(self, http_client: Any, access_token: str) -> None:
        self.http = http_client
        self.access_token = access_token

    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make an authenticated GET request to the Spotify Web API.

        Args:
            endpoint: API endpoint path (e.g., 'me', 'me/playlists').
            params: Optional query parameters.

        Returns:
            Parsed JSON response dict.

        Raises:
            SpotifyAPIError: On HTTP error responses including 429 rate limiting.
        """
        url = f"{SPOTIFY_API_BASE}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        logger_client.debug(
            "Spotify API request: GET %s params=%s", endpoint, params
        )

        response = await self.http.get(url, headers=headers, params=params or {})

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            logger_client.warning(
                "Spotify rate limited (429): Retry-After=%s endpoint=%s",
                retry_after, endpoint,
            )
            raise SpotifyAPIError(
                429, "rate_limited",
                f"Rate limited. Retry after {retry_after}s",
            )

        if response.status_code >= 400:
            error_type = ""
            message = f"HTTP {response.status_code}"
            try:
                body = response.json()
                error_info = body.get("error", {})
                if isinstance(error_info, dict):
                    error_type = error_info.get("status", "")
                    message = error_info.get("message", message)
            except Exception:
                pass

            logger_client.warning(
                "Spotify API error: %d %s — %s (endpoint=%s)",
                response.status_code, error_type, message, endpoint,
            )
            raise SpotifyAPIError(response.status_code, str(error_type), message)

        return response.json()

    async def get_user_profile(self) -> dict:
        """Get the current user's Spotify profile.

        Returns:
            Dict with user profile fields including ``display_name``,
            ``product`` (e.g., 'premium'), ``id``, ``email``, etc.
        """
        return await self._get("me")

    async def get_playlists(self, limit: int = 50) -> list[dict]:
        """Get the current user's playlists.

        Args:
            limit: Maximum number of playlists to return (max 50).

        Returns:
            List of playlist dicts with ``id``, ``name``, ``tracks``, etc.
        """
        data = await self._get("me/playlists", {"limit": min(limit, 50)})
        items = data.get("items", [])
        logger_client.info("Listed %d playlists", len(items))
        return items

    async def get_playlist_tracks(
        self, playlist_id: str, limit: int = 100
    ) -> list[dict]:
        """Get tracks from a Spotify playlist.

        Args:
            playlist_id: Spotify playlist ID.
            limit: Maximum number of tracks to return (max 100).

        Returns:
            List of track item dicts, each with a ``track`` sub-dict.
        """
        data = await self._get(
            f"playlists/{playlist_id}/tracks",
            {"limit": min(limit, 100)},
        )
        items = data.get("items", [])
        logger_client.info(
            "Listed %d tracks from playlist %s", len(items), playlist_id
        )
        return items


# ── Pure helper functions ──


def mint_source_iri(feed_url: str) -> str:
    """Mint a deterministic MediaSource IRI from a feed URL.

    Uses SHA-256 hash (first 16 hex chars) of the feed URL.
    Same pattern as youtube_service.mint_source_iri.
    """
    digest = hashlib.sha256(feed_url.encode("utf-8")).hexdigest()[:16]
    return f"{APP_NS}source-{digest}"


def mint_item_iri(source_iri: str, track_id: str) -> str:
    """Mint a deterministic MediaItem IRI from source IRI + track ID.

    Uses SHA-256 hash (first 16 hex chars) of the concatenation.
    Same pattern as youtube_service.mint_item_iri.
    """
    raw = source_iri + track_id
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{APP_NS}item-{digest}"


def parse_spotify_url(url: str | None) -> dict | None:
    """Parse a Spotify URL and extract the playlist identifier.

    Supported formats:
    - ``https://open.spotify.com/playlist/{id}`` (web URL, with optional query params)
    - ``spotify:playlist:{id}`` (Spotify URI)

    Args:
        url: Spotify URL or URI string.

    Returns:
        Dict with ``type`` ("playlist") and ``value`` (playlist ID), or None
        if the URL is not a recognized Spotify playlist format.
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()
    if not url:
        return None

    # Spotify URI format: spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
    uri_match = re.match(r"^spotify:playlist:([a-zA-Z0-9]+)$", url)
    if uri_match:
        return {"type": "playlist", "value": uri_match.group(1)}

    # Web URL format: https://open.spotify.com/playlist/{id}
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    host = (parsed.hostname or "").lower()
    if host != "open.spotify.com":
        return None

    path = parsed.path.rstrip("/")
    path_match = re.match(r"^/playlist/([a-zA-Z0-9]+)$", path)
    if path_match:
        return {"type": "playlist", "value": path_match.group(1)}

    return None


def track_to_media_item(track: dict, source_iri: str) -> dict:
    """Convert a Spotify track dict to a MediaItem object.create params dict.

    Expected ``track`` structure (from playlist tracks endpoint):
    - ``track.name`` → dcterms:title
    - ``track.artists[0].name`` → dcterms:description (artist name)
    - ``track.duration_ms`` → ms:duration (converted to seconds)
    - ``track.album.images[0].url`` → ms:thumbnailUrl
    - ``track.external_urls.spotify`` → ms:enclosureUrl
    - ``track.id`` → ms:externalId

    The ``track`` dict is the inner ``track`` object from the playlist items
    response, not the wrapper item. If the input is a playlist item wrapper,
    the caller should pass ``item["track"]``.

    Args:
        track: Spotify track dict with fields listed above.
        source_iri: IRI of the parent MediaSource.

    Returns:
        Dict with ``iri``, ``type``, and ``properties`` keys.
    """
    track_id = track.get("id", "")
    item_iri = mint_item_iri(source_iri, track_id)

    properties: dict[str, Any] = {}

    # Title
    title = track.get("name")
    if title:
        properties["dcterms:title"] = title

    # Description — use artist name(s)
    artists = track.get("artists", [])
    if artists:
        artist_names = ", ".join(a.get("name", "") for a in artists if a.get("name"))
        if artist_names:
            properties["dcterms:description"] = artist_names

    # Duration — Spotify provides duration_ms, convert to seconds
    duration_ms = track.get("duration_ms")
    if duration_ms is not None:
        properties[f"{MS_NS}duration"] = duration_ms // 1000

    # Thumbnail — prefer first album image (largest)
    album = track.get("album", {})
    images = album.get("images", [])
    if images and isinstance(images[0], dict):
        thumb_url = images[0].get("url")
        if thumb_url:
            properties[f"{MS_NS}thumbnailUrl"] = thumb_url

    # External ID
    if track_id:
        properties[f"{MS_NS}externalId"] = track_id

    # Enclosure URL — Spotify track URL
    external_urls = track.get("external_urls", {})
    spotify_url = external_urls.get("spotify")
    if spotify_url:
        properties[f"{MS_NS}enclosureUrl"] = spotify_url

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
    """Query the triplestore for existing MediaItem IRIs from a Spotify source.

    Used for deduplication — same pattern as youtube_service.

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


async def check_source_exists_spotify(
    graph_client: Any, playlist_id: str
) -> str | None:
    """Check if a Spotify MediaSource for the given playlist already exists.

    Searches by externalId (the Spotify playlist ID) rather than feedUrl
    because the canonical URL for a playlist is its Spotify URI.

    Args:
        graph_client: SDK GraphClient instance.
        playlist_id: Spotify playlist ID.

    Returns:
        The source IRI if it exists, None otherwise.
    """
    sparql = f"""
    SELECT ?source WHERE {{
        ?source a <{MEDIA_SOURCE_TYPE}> .
        ?source <{MS_NS}sourceType> "spotify" .
        ?source <{MS_NS}externalId> "{playlist_id}" .
    }} LIMIT 1
    """
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if bindings:
        return bindings[0].get("source", {}).get("value")
    return None


async def subscribe_spotify(
    ctx: Any,
    playlist_id: str,
    playlist_name: str,
) -> dict:
    """Create a Spotify playlist MediaSource subscription.

    Args:
        ctx: SDK AppContext with ``commands`` and ``graph`` clients.
        playlist_id: Spotify playlist ID.
        playlist_name: Display name for the playlist.

    Returns:
        Dict with ``status`` ("created" or "duplicate") and ``iri``.
    """
    # Check for duplicate by playlist ID
    existing = await check_source_exists_spotify(ctx.graph, playlist_id)
    if existing:
        logger_poll.info(
            "Spotify source already exists for playlist %s: %s",
            playlist_id, existing,
        )
        return {"status": "duplicate", "iri": existing}

    # Mint IRI from canonical Spotify URI
    feed_url = f"spotify:playlist:{playlist_id}"
    iri = mint_source_iri(feed_url)

    properties: dict[str, Any] = {
        f"{MS_NS}feedUrl": feed_url,
        "dcterms:title": playlist_name,
        f"{MS_NS}sourceType": "spotify",
        f"{MS_NS}externalId": playlist_id,
        f"{MS_NS}errorCount": 0,
        f"{MS_NS}lastError": "",
    }
    await ctx.commands.execute(
        "object.create",
        {"iri": iri, "type": MEDIA_SOURCE_TYPE, "properties": properties},
    )

    logger_poll.info(
        "Created Spotify source for playlist %s (%s): %s",
        playlist_id, playlist_name, iri,
    )
    return {"status": "created", "iri": iri}
