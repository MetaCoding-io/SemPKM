"""SearchService: full-text keyword search using RDF4J LuceneSail.

Uses the search:matches SPARQL magic predicate to query the Lucene index.
Results are scoped to urn:sempkm:current to exclude event graph subjects.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

SEARCH_NS = "http://www.openrdf.org/contrib/lucenesail#"

FTS_QUERY = """\
PREFIX search: <http://www.openrdf.org/contrib/lucenesail#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <http://schema.org/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?iri ?type ?label ?snippet ?score WHERE {{
  GRAPH <urn:sempkm:current> {{
    ?iri search:matches [
      search:query {query!r} ;
      search:score ?score ;
      search:snippet ?snippet
    ] .
    OPTIONAL {{ ?iri rdf:type ?type }}
    OPTIONAL {{
      ?iri dcterms:title ?label .
    }}
    OPTIONAL {{
      ?iri rdfs:label ?label .
    }}
    OPTIONAL {{
      ?iri skos:prefLabel ?label .
    }}
    OPTIONAL {{
      ?iri schema:name ?label .
    }}
    OPTIONAL {{
      ?iri foaf:name ?label .
    }}
  }}
}}
ORDER BY DESC(?score)
LIMIT {limit}
"""


@dataclass
class SearchResult:
    iri: str
    type: str | None
    label: str
    snippet: str
    score: float


class SearchService:
    """Executes full-text searches against the LuceneSail index."""

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search all literal values in urn:sempkm:current for the given query.

        Args:
            query: Lucene query string (e.g. "knowledge base", "knowl*")
            limit: Maximum number of results to return (default 20)

        Returns:
            List of SearchResult ordered by relevance score descending.
        """
        if not query or not query.strip():
            return []

        sparql = FTS_QUERY.format(query=query.strip(), limit=limit)
        try:
            result = await self._client.query(sparql)
        except Exception:
            logger.exception("FTS query failed for query=%r", query)
            return []

        bindings = result.get("results", {}).get("bindings", [])
        seen: set[str] = set()
        results: list[SearchResult] = []
        for row in bindings:
            iri = row.get("iri", {}).get("value", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)
            results.append(SearchResult(
                iri=iri,
                type=row.get("type", {}).get("value"),
                label=row.get("label", {}).get("value") or iri,
                snippet=row.get("snippet", {}).get("value") or "",
                score=float(row.get("score", {}).get("value") or 0),
            ))
        return results
