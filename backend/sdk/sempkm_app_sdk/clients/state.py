"""StateClient — app-scoped key-value state stored in the RDF graph."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class StateClient:
    """Key-value state scoped to an app's named graph.

    State is stored as RDF triples in a per-app named graph using SPARQL
    queries routed through the platform's graph API.

    Args:
        client: Shared httpx.AsyncClient with platform base_url and auth.
        app_id: App identifier used to construct the state graph IRI.
    """

    STATE_GRAPH_TEMPLATE = "urn:sempkm:app:{app_id}:state"

    def __init__(self, client: httpx.AsyncClient, app_id: str) -> None:
        self._client = client
        self.app_id = app_id
        self.graph_iri = self.STATE_GRAPH_TEMPLATE.format(app_id=app_id)

    async def get(self, key: str) -> str | None:
        """Retrieve a value by key from the app state graph.

        Args:
            key: State key to look up.

        Returns:
            The value string, or None if the key doesn't exist.
        """
        sparql = (
            f"SELECT ?value WHERE {{ "
            f"GRAPH <{self.graph_iri}> {{ "
            f'<urn:sempkm:state:{key}> <urn:sempkm:state:value> ?value '
            f"}} }}"
        )
        logger.debug("state get key=%s from %s", key, self.graph_iri)
        resp = await self._client.post("/api/sparql", data={"query": sparql})
        resp.raise_for_status()
        data = resp.json()
        bindings = data.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0].get("value", {}).get("value")
        return None

    async def set(self, key: str, value: str) -> None:
        """Set a key-value pair in the app state graph.

        Uses SPARQL UPDATE (DELETE/INSERT) to upsert the value.

        Args:
            key: State key to set.
            value: Value string to store.
        """
        sparql = (
            f"DELETE {{ GRAPH <{self.graph_iri}> {{ "
            f"<urn:sempkm:state:{key}> <urn:sempkm:state:value> ?old }} }} "
            f"WHERE {{ GRAPH <{self.graph_iri}> {{ "
            f"<urn:sempkm:state:{key}> <urn:sempkm:state:value> ?old }} }}; "
            f"INSERT DATA {{ GRAPH <{self.graph_iri}> {{ "
            f'<urn:sempkm:state:{key}> <urn:sempkm:state:value> "{value}" }} }}'
        )
        logger.debug("state set key=%s in %s", key, self.graph_iri)
        resp = await self._client.post("/api/sparql", data={"query": sparql})
        resp.raise_for_status()
