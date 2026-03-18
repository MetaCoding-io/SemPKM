"""HttpClient — external HTTP access (not the platform client).

This client is for apps that need to make external HTTP calls (e.g. RSS
feeds, webhooks). It is NOT the platform API client — that's wired
separately via AppContext._get_platform_client().

Domain enforcement: hostname extracted from URL is matched against the
allowed_domains list using fnmatch glob patterns. Empty list = all blocked.
``["*"]`` = unrestricted.
"""

from __future__ import annotations

import fnmatch
import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class HttpClient:
    """Thin wrapper around httpx.AsyncClient for external HTTP calls.

    Creates its own httpx client (not shared with platform client).

    Args:
        client: Optional pre-configured httpx.AsyncClient.
        allowed_domains: Domain glob patterns. Empty list blocks all requests.
            ``["*"]`` allows any domain.
    """

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        allowed_domains: list[str] | None = None,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._allowed_domains = allowed_domains if allowed_domains is not None else []

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
            self._owns_client = True
        return self._client

    def _check_domain(self, url: str) -> None:
        """Validate that the URL's hostname matches an allowed domain pattern.

        Raises:
            PermissionError: If hostname doesn't match any allowed pattern.
        """
        hostname = urlparse(url).hostname or ""
        for pattern in self._allowed_domains:
            if fnmatch.fnmatch(hostname, pattern):
                return
        raise PermissionError(
            f"HTTP request to domain {hostname!r} is not permitted. "
            f"Allowed domains: {self._allowed_domains}"
        )

    async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Send an HTTP request to an external URL.

        Args:
            method: HTTP method (GET, POST, PUT, etc.).
            url: Full URL to request.
            **kwargs: Additional httpx request kwargs.

        Returns:
            httpx.Response object.

        Raises:
            PermissionError: If the URL's domain is not in allowed_domains.
        """
        self._check_domain(url)
        logger.debug("external %s %s", method, url)
        return await self._get_client().request(method, url, **kwargs)

    async def get(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a GET request to an external URL."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a POST request to an external URL."""
        return await self.request("POST", url, **kwargs)

    async def close(self) -> None:
        """Close the underlying httpx client if we own it."""
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None
