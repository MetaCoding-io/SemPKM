"""Mirror service for storing federated SPARQL results locally.

Stores triples from external SPARQL endpoints in urn:sempkm:mirrored
with per-batch provenance metadata in urn:sempkm:mirror-prov:{uuid} graphs.
Validates endpoints against a configurable allowlist.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.rdf.namespaces import MIRRORED_GRAPH_IRI
from app.sparql.federation_config import get_merged_endpoints
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

MIRROR_PROV_PREFIX = "urn:sempkm:mirror-prov:"


@dataclass
class MirrorResult:
    """Result of a mirror operation."""

    triple_count: int
    provenance_graph: str
    endpoint: str


class MirrorService:
    """Stores federated SPARQL query results in urn:sempkm:mirrored.

    Each mirror operation creates a provenance graph recording the source
    endpoint and timestamp. Endpoint access is controlled by the
    federation_allowed_endpoints setting.
    """

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    def validate_endpoint(self, url: str) -> bool:
        """Check if the URL is in the merged allowlist (env + admin).

        Returns True if the endpoint is allowed, False otherwise.
        An empty allowlist means no endpoints are permitted.
        """
        merged = get_merged_endpoints()
        if not merged:
            return False
        allowed_urls = {entry["url"] for entry in merged}
        return url.strip() in allowed_urls

    async def mirror_results(
        self,
        bindings: list[dict],
        vars: list[str],
        endpoint_url: str,
    ) -> MirrorResult:
        """Convert SPARQL JSON result bindings to triples and store in mirrored graph.

        For each binding row, looks for URI-typed values and constructs triples
        from consecutive variable pairs (subject-predicate-object pattern).
        If exactly 3 URI variables exist, they form one triple. If 2 variables
        exist (subject, object), a generic link predicate is used.

        Args:
            bindings: Parsed SPARQL JSON result bindings (list of dicts).
            vars: Variable names from the query results.
            endpoint_url: The source SPARQL endpoint URL.

        Returns:
            MirrorResult with the count of stored triples and provenance graph IRI.
        """
        prov_id = str(uuid.uuid4())
        prov_graph = f"{MIRROR_PROV_PREFIX}{prov_id}"

        # Extract triples from bindings
        triples = self._extract_triples(bindings, vars)

        if not triples:
            logger.info(
                "Mirror: no triples extracted from %d bindings (endpoint: %s)",
                len(bindings),
                endpoint_url,
            )
            # Still create provenance record for the empty mirror operation
            await self._store_provenance(prov_graph, endpoint_url, 0)
            return MirrorResult(
                triple_count=0,
                provenance_graph=prov_graph,
                endpoint=endpoint_url,
            )

        # Store triples in mirrored graph
        await self._store_triples(triples)

        # Store provenance metadata
        await self._store_provenance(prov_graph, endpoint_url, len(triples))

        logger.info(
            "Mirror: stored %d triples from %s (provenance: %s)",
            len(triples),
            endpoint_url,
            prov_graph,
        )

        return MirrorResult(
            triple_count=len(triples),
            provenance_graph=prov_graph,
            endpoint=endpoint_url,
        )

    async def clear_mirrored(self) -> int:
        """Drop urn:sempkm:mirrored and all mirror-prov graphs.

        Returns the count of triples that were in the mirrored graph.
        """
        # Count triples before clearing
        count = await self._count_mirrored_triples()

        # Clear the mirrored data graph
        try:
            await self._client.update(f"CLEAR GRAPH <{MIRRORED_GRAPH_IRI}>")
        except Exception as e:
            logger.debug("Clear mirrored graph: %s", e)

        # Find and clear all provenance graphs
        prov_graphs = await self._list_provenance_graphs()
        for graph_iri in prov_graphs:
            try:
                await self._client.update(f"CLEAR GRAPH <{graph_iri}>")
            except Exception as e:
                logger.debug("Clear provenance graph %s: %s", graph_iri, e)

        logger.info(
            "Mirror: cleared %d triples and %d provenance graphs",
            count,
            len(prov_graphs),
        )

        return count

    async def get_mirror_stats(self) -> dict:
        """Return statistics about mirrored data.

        Returns dict with triple_count and source_endpoints list.
        """
        count = await self._count_mirrored_triples()
        endpoints = await self._list_source_endpoints()

        return {
            "triple_count": count,
            "source_endpoints": endpoints,
        }

    def _extract_triples(
        self, bindings: list[dict], vars: list[str]
    ) -> list[tuple[str, str, str]]:
        """Extract (s, p, o) triples from SPARQL JSON result bindings.

        Strategy:
        - If vars has exactly 3 entries and all are URI-typed in a binding,
          treat them as (subject, predicate, object).
        - Otherwise, look for URI values and pair them:
          if 2 URIs found, use a generic predicate.
        - Skip bindings that don't produce valid triples.
        """
        triples: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str, str]] = set()

        for binding in bindings:
            uris = []
            for var in vars:
                val = binding.get(var, {})
                if val.get("type") == "uri":
                    uris.append(val["value"])

            if len(uris) >= 3:
                # First three URIs form s, p, o
                triple = (uris[0], uris[1], uris[2])
                if triple not in seen:
                    seen.add(triple)
                    triples.append(triple)
            elif len(uris) == 2:
                # Two URIs: use rdfs:seeAlso as generic link predicate
                triple = (
                    uris[0],
                    "http://www.w3.org/2000/01/rdf-schema#seeAlso",
                    uris[1],
                )
                if triple not in seen:
                    seen.add(triple)
                    triples.append(triple)

        return triples

    async def _store_triples(self, triples: list[tuple[str, str, str]]) -> None:
        """Store triples in urn:sempkm:mirrored via SPARQL INSERT DATA."""
        batch_size = 500
        for i in range(0, len(triples), batch_size):
            batch = triples[i : i + batch_size]
            triple_lines = [f"  <{s}> <{p}> <{o}> ." for s, p, o in batch]
            triples_str = "\n".join(triple_lines)
            sparql = (
                f"INSERT DATA {{\n"
                f"  GRAPH <{MIRRORED_GRAPH_IRI}> {{\n"
                f"{triples_str}\n"
                f"  }}\n"
                f"}}"
            )
            await self._client.update(sparql)

    async def _store_provenance(
        self, prov_graph: str, endpoint_url: str, triple_count: int
    ) -> None:
        """Store provenance metadata in a named graph."""
        now = datetime.now(timezone.utc).isoformat()
        sparql = (
            f"INSERT DATA {{\n"
            f"  GRAPH <{prov_graph}> {{\n"
            f"    <{prov_graph}> <http://www.w3.org/ns/prov#wasAttributedTo> <{endpoint_url}> .\n"
            f"    <{prov_graph}> <http://www.w3.org/ns/prov#generatedAtTime> \"{now}\"^^<http://www.w3.org/2001/XMLSchema#dateTime> .\n"
            f"    <{prov_graph}> <urn:sempkm:mirrorTripleCount> \"{triple_count}\"^^<http://www.w3.org/2001/XMLSchema#integer> .\n"
            f"  }}\n"
            f"}}"
        )
        await self._client.update(sparql)

    async def _count_mirrored_triples(self) -> int:
        """Count triples in urn:sempkm:mirrored."""
        sparql = (
            f"SELECT (COUNT(*) AS ?count) WHERE {{\n"
            f"  GRAPH <{MIRRORED_GRAPH_IRI}> {{ ?s ?p ?o }}\n"
            f"}}"
        )
        try:
            result = await self._client.query(sparql)
            bindings = result.get("results", {}).get("bindings", [])
            if bindings:
                return int(bindings[0]["count"]["value"])
        except Exception as e:
            logger.debug("Count mirrored triples: %s", e)
        return 0

    async def _list_provenance_graphs(self) -> list[str]:
        """List all mirror-prov named graphs."""
        sparql = (
            "SELECT DISTINCT ?g WHERE {\n"
            "  GRAPH ?g { ?s ?p ?o }\n"
            f"  FILTER(STRSTARTS(STR(?g), \"{MIRROR_PROV_PREFIX}\"))\n"
            "}"
        )
        try:
            result = await self._client.query(sparql)
            bindings = result.get("results", {}).get("bindings", [])
            return [b["g"]["value"] for b in bindings]
        except Exception as e:
            logger.debug("List provenance graphs: %s", e)
            return []

    async def _list_source_endpoints(self) -> list[str]:
        """List unique source endpoints from provenance graphs."""
        sparql = (
            "SELECT DISTINCT ?endpoint WHERE {\n"
            "  GRAPH ?g {\n"
            "    ?s <http://www.w3.org/ns/prov#wasAttributedTo> ?endpoint\n"
            "  }\n"
            f"  FILTER(STRSTARTS(STR(?g), \"{MIRROR_PROV_PREFIX}\"))\n"
            "}"
        )
        try:
            result = await self._client.query(sparql)
            bindings = result.get("results", {}).get("bindings", [])
            return [b["endpoint"]["value"] for b in bindings]
        except Exception as e:
            logger.debug("List source endpoints: %s", e)
            return []
