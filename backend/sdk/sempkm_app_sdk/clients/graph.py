"""GraphClient — SPARQL queries against the platform's graph API."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class GraphClient:
    """Query the platform's RDF graph via SPARQL.

    Args:
        client: Shared httpx.AsyncClient with platform base_url and auth.
        sparql_read: Whether SPARQL read access is permitted.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        sparql_read: bool = False,
    ) -> None:
        self._client = client
        self._sparql_read = sparql_read

    async def query(self, sparql: str) -> dict:
        """Execute a SPARQL query.

        Args:
            sparql: SPARQL query string.

        Returns:
            Response JSON as a dict (SPARQL results format).

        Raises:
            PermissionError: If sparql_read is False.
        """
        if not self._sparql_read:
            raise PermissionError(
                "SPARQL read access is not permitted for this app. "
                "Add 'sparql_read: true' to the manifest permissions section."
            )
        logger.debug("executing SPARQL query (%d chars)", len(sparql))
        resp = await self._client.post(
            "/api/sparql",
            data={"query": sparql},
        )
        resp.raise_for_status()
        return resp.json()
