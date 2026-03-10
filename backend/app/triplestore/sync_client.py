"""Synchronous RDF4J triplestore client for WSGI thread pool use.

Mirrors TriplestoreClient's API but uses httpx.Client (sync) instead of
httpx.AsyncClient. Designed exclusively for wsgidav's WSGI threads --
never call from the async event loop.
"""

import httpx


class SyncTriplestoreClient:
    """Synchronous client for RDF4J triplestore operations.

    Used by the WebDAV provider which runs in WSGI threads (via a2wsgi),
    where async calls are not available.
    """

    def __init__(self, base_url: str, repository_id: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.repository_id = repository_id
        self._repo_url = f"{self.base_url}/repositories/{self.repository_id}"
        self._client = httpx.Client(timeout=30.0)

    def query(self, sparql: str) -> dict:
        """Execute a SPARQL SELECT/ASK query synchronously, return JSON results dict."""
        resp = self._client.post(
            self._repo_url,
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
        )
        resp.raise_for_status()
        return resp.json()

    def update(self, sparql: str) -> None:
        """Execute a SPARQL UPDATE (INSERT/DELETE) synchronously."""
        resp = self._client.post(
            f"{self._repo_url}/statements",
            data={"update": sparql},
        )
        resp.raise_for_status()

    def close(self) -> None:
        """Close the underlying httpx client."""
        self._client.close()
