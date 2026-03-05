"""Label resolution service with SPARQL COALESCE batch queries and TTL caching.

Resolves IRIs to human-readable labels using the precedence chain:
dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name > QName fallback > truncated IRI.

Supports configurable language preferences, batch resolution in a single SPARQL
query, and TTL-based caching with explicit invalidation.
"""

import logging
from typing import Optional

from cachetools import TTLCache

from app.services.prefixes import PrefixRegistry
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)


class LabelService:
    """Resolve IRIs to human-readable labels with caching.

    Uses SPARQL COALESCE for precedence-based label resolution and
    VALUES for batch queries. Results are cached with TTL expiry.
    """

    def __init__(
        self,
        triplestore_client: TriplestoreClient,
        prefix_registry: PrefixRegistry,
        ttl: int = 300,
        maxsize: int = 4096,
    ) -> None:
        self._client = triplestore_client
        self._prefixes = prefix_registry
        self._cache: TTLCache[str, str] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._language_prefs: list[str] = ["en"]

    async def resolve(self, iri: str) -> str:
        """Resolve a single IRI to its best human-readable label.

        Checks cache first, then falls back to batch resolution.
        """
        if iri in self._cache:
            return self._cache[iri]
        results = await self.resolve_batch([iri])
        return results.get(iri, self._iri_fallback(iri))

    async def resolve_batch(self, iris: list[str]) -> dict[str, str]:
        """Resolve multiple IRIs in a single SPARQL query.

        Checks cache for each IRI, collects misses, runs a single
        VALUES-based SPARQL query with COALESCE for the precedence chain,
        and caches all results.
        """
        results: dict[str, str] = {}
        misses: list[str] = []

        for iri in iris:
            if iri in self._cache:
                results[iri] = self._cache[iri]
            else:
                misses.append(iri)

        if not misses:
            return results

        # Build VALUES clause for batch query
        values_clause = " ".join(f"(<{iri}>)" for iri in misses)
        lang = self._language_prefs[0] if self._language_prefs else "en"

        query = f"""
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX schema: <https://schema.org/>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>

        SELECT ?iri ?label
        FROM <urn:sempkm:current>
        FROM <urn:sempkm:inferred>
        WHERE {{
          VALUES (?iri) {{ {values_clause} }}
          OPTIONAL {{ ?iri dcterms:title ?t . {self._build_lang_filter("?t", lang)} }}
          OPTIONAL {{ ?iri rdfs:label ?r . {self._build_lang_filter("?r", lang)} }}
          OPTIONAL {{ ?iri skos:prefLabel ?s . {self._build_lang_filter("?s", lang)} }}
          OPTIONAL {{ ?iri schema:name ?n . {self._build_lang_filter("?n", lang)} }}
          OPTIONAL {{ ?iri foaf:name ?f . {self._build_lang_filter("?f", lang)} }}
          BIND(COALESCE(?t, ?r, ?s, ?n, ?f) AS ?label)
        }}
        """

        try:
            sparql_results = await self._client.query(query)
        except Exception:
            logger.warning("SPARQL label query failed", exc_info=True)
            # Fall back to IRI fallbacks for all misses
            for iri in misses:
                fallback = self._iri_fallback(iri)
                self._cache[iri] = fallback
                results[iri] = fallback
            return results

        # Track which IRIs got results from SPARQL
        resolved_iris: set[str] = set()

        for binding in sparql_results.get("results", {}).get("bindings", []):
            iri_val = binding["iri"]["value"]
            resolved_iris.add(iri_val)
            if "label" in binding and binding["label"].get("value"):
                label = binding["label"]["value"]
                self._cache[iri_val] = label
                results[iri_val] = label
            else:
                fallback = self._iri_fallback(iri_val)
                self._cache[iri_val] = fallback
                results[iri_val] = fallback

        # Handle IRIs that weren't in SPARQL results at all
        for iri in misses:
            if iri not in resolved_iris:
                fallback = self._iri_fallback(iri)
                self._cache[iri] = fallback
                results[iri] = fallback

        return results

    def invalidate(self, iris: list[str]) -> None:
        """Remove specific IRIs from cache after writes.

        Called after EventStore commits to ensure write-your-own-read
        consistency for label changes.
        """
        for iri in iris:
            self._cache.pop(iri, None)

    def set_language_prefs(self, langs: list[str]) -> None:
        """Set language preferences and clear entire cache.

        Language change invalidates all cached labels since resolution
        results depend on the language filter.
        """
        self._language_prefs = langs
        self._cache.clear()

    def _iri_fallback(self, iri: str) -> str:
        """Generate fallback label for an IRI.

        Precedence:
        1. QName via PrefixRegistry.compact() (e.g., dcterms:title)
        2. Truncated IRI with local name (e.g., .../localName)
        3. Full IRI if no local name extractable
        """
        qname = self._prefixes.compact(iri)
        if qname != iri:
            return qname
        # Extract local name: split on last "#" then last "/"
        local = iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1]
        if local and local != iri:
            return f".../{local}"
        return iri

    @staticmethod
    def _build_lang_filter(var: str, lang: str) -> str:
        """Build SPARQL FILTER clause for language preference.

        Accepts both untagged literals (LANG() = "") and language-matched
        literals per research Pitfall 6.
        """
        return f'FILTER(LANG({var}) = "" || LANG({var}) = "{lang}")'
