"""RDF4J triplestore client wrapper using httpx.AsyncClient.

Provides async methods for SPARQL query/update, health checks, and
transaction management against an RDF4J REST API endpoint.

Uses application/x-www-form-urlencoded for SPARQL operations per RDF4J
protocol requirements (not raw SPARQL body).
"""

import httpx


class TriplestoreClient:
    """Async client for RDF4J triplestore operations."""

    def __init__(self, base_url: str, repository_id: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.repository_id = repository_id
        self._repo_url = f"{self.base_url}/repositories/{self.repository_id}"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def is_healthy(self) -> bool:
        """Check if the triplestore repository is reachable.

        GET {base_url}/repositories/{repo_id}/size returns 200 if the
        repository exists and is operational.
        """
        try:
            resp = await self._client.get(f"{self._repo_url}/size")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def query(self, sparql: str) -> dict:
        """Execute a SPARQL SELECT/ASK query and return parsed JSON results.

        POST to {base_url}/repositories/{repo_id} with form-encoded query.
        """
        resp = await self._client.post(
            self._repo_url,
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
        )
        resp.raise_for_status()
        return resp.json()

    async def update(self, sparql: str) -> None:
        """Execute a SPARQL UPDATE (INSERT/DELETE).

        POST to {base_url}/repositories/{repo_id}/statements with
        form-encoded update.
        """
        resp = await self._client.post(
            f"{self._repo_url}/statements",
            data={"update": sparql},
        )
        resp.raise_for_status()

    async def begin_transaction(self) -> str:
        """Begin an RDF4J transaction.

        POST to {base_url}/repositories/{repo_id}/transactions.
        Returns the transaction URL from the Location header.
        """
        resp = await self._client.post(
            f"{self._repo_url}/transactions",
        )
        resp.raise_for_status()
        txn_url = resp.headers.get("Location") or str(resp.url)
        return txn_url

    async def commit_transaction(self, txn_url: str) -> None:
        """Commit an RDF4J transaction.

        PUT to the transaction URL with action=COMMIT.
        """
        resp = await self._client.put(
            txn_url,
            params={"action": "COMMIT"},
        )
        resp.raise_for_status()

    async def rollback_transaction(self, txn_url: str) -> None:
        """Rollback an RDF4J transaction.

        DELETE the transaction URL.
        """
        resp = await self._client.delete(txn_url)
        resp.raise_for_status()

    async def transaction_update(self, txn_url: str, sparql: str) -> None:
        """Execute a SPARQL UPDATE within a transaction.

        PUT to the transaction URL with raw SPARQL body and
        Content-Type: application/sparql-update. RDF4J transaction
        endpoints require raw SPARQL (not form-encoded) for updates.
        """
        resp = await self._client.put(
            txn_url,
            content=sparql,
            params={"action": "UPDATE"},
            headers={"Content-Type": "application/sparql-update"},
        )
        resp.raise_for_status()

    async def transaction_query(self, txn_url: str, sparql: str) -> dict:
        """Execute a SPARQL query within a transaction.

        POST to the transaction URL with form-encoded query and action=QUERY.
        """
        resp = await self._client.post(
            txn_url,
            data={"query": sparql},
            params={"action": "QUERY"},
            headers={"Accept": "application/sparql-results+json"},
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()
