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

    def _normalize_query(self, query: str, fuzzy: bool = False) -> str:
        """Normalize a user query string for LuceneSail.

        In fuzzy mode, appends ~1 (edit distance 1) to tokens with 5+ characters.
        Tokens shorter than 5 characters always use exact match to avoid
        dictionary-scan noise from fuzzy expansion.

        Args:
            query: Raw user query string.
            fuzzy: Whether to apply fuzzy expansion.

        Returns:
            Normalized Lucene query string.
        """
        q = query.strip()
        if not fuzzy:
            return q
        tokens = q.split()
        normalized = []
        for token in tokens:
            # Skip tokens that already have an operator suffix (~, *, ?)
            if len(token) >= 5 and token[-1] not in ('~', '*', '?'):
                normalized.append(token + '~1')
            else:
                normalized.append(token)
        return ' '.join(normalized)

    async def search(
        self,
        query: str,
        limit: int = 20,
        fuzzy: bool = False,
    ) -> list[SearchResult]:
        """Search all literal values in urn:sempkm:current for the given query.

        Args:
            query: Lucene query string (e.g. "knowledge base", "knowl*")
            limit: Maximum number of results to return (default 20)
            fuzzy: If True, applies ~1 fuzzy expansion to tokens with 5+ characters
                   to tolerate typos. Short tokens (<5 chars) stay exact to avoid
                   dictionary-scan noise. Default False (exact match).

        Returns:
            List of SearchResult ordered by relevance score descending.
        """
        if not query or not query.strip():
            return []

        normalized = self._normalize_query(query, fuzzy)
        sparql = FTS_QUERY.format(query=normalized, limit=limit)
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
