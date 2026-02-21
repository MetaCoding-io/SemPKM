"""Three-layer prefix registry with bidirectional expansion/compaction.

Provides prefix-to-namespace (expand) and namespace-to-prefix (compact) lookup
across three layers: built-in, model-provided, LOV-imported, and user-overrides.
Precedence: user > model > LOV > built-in.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class PrefixRegistry:
    """Three-layer prefix registry with bidirectional lookup.

    Layers (highest to lowest precedence):
    1. User overrides (_user_prefixes) - persisted in triplestore in Phase 3+
    2. Model-provided (_model_prefixes) - populated by Mental Model install in Phase 3
    3. LOV-imported (_lov_prefixes) - populated by LOV API import
    4. Built-in (BUILTIN) - hardcoded standard vocabularies
    """

    BUILTIN: dict[str, str] = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "sh": "http://www.w3.org/ns/shacl#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "dcterms": "http://purl.org/dc/terms/",
        "schema": "https://schema.org/",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "prov": "http://www.w3.org/ns/prov#",
        "sempkm": "urn:sempkm:",
    }

    def __init__(self) -> None:
        self._model_prefixes: dict[str, str] = {}
        self._user_prefixes: dict[str, str] = {}
        self._lov_prefixes: dict[str, str] = {}
        self._reverse_cache: Optional[dict[str, str]] = None

    def expand(self, qname: str) -> Optional[str]:
        """Expand prefix:localName to full IRI.

        Splits on the first colon and looks up the prefix through all layers.
        Returns the full IRI or None if the prefix is unknown.
        """
        if ":" not in qname:
            return None
        prefix, local = qname.split(":", 1)
        ns = self._lookup_prefix(prefix)
        return f"{ns}{local}" if ns else None

    def compact(self, iri: str) -> str:
        """Compact full IRI to prefix:localName.

        Finds the longest matching namespace across all layers and returns
        the QName. Returns the original IRI if no prefix matches.
        """
        reverse = self._get_reverse_map()
        best_prefix: Optional[str] = None
        best_ns_len = 0
        for ns, prefix in reverse.items():
            if iri.startswith(ns) and len(ns) > best_ns_len:
                best_prefix = prefix
                best_ns_len = len(ns)
        if best_prefix is not None:
            return f"{best_prefix}:{iri[best_ns_len:]}"
        return iri

    def register_model_prefixes(self, prefixes: dict[str, str]) -> None:
        """Merge prefixes from an installed Mental Model into the model layer.

        Invalidates the reverse map cache.
        """
        self._model_prefixes.update(prefixes)
        self._reverse_cache = None

    def register_user_prefix(self, prefix: str, namespace: str) -> None:
        """Add a user override prefix. Highest precedence layer.

        Invalidates the reverse map cache.
        """
        self._user_prefixes[prefix] = namespace
        self._reverse_cache = None

    def get_all_prefixes(self) -> dict[str, str]:
        """Return merged dict of all prefixes. Later layers override earlier.

        Order: built-in, then LOV, then model, then user.
        """
        merged: dict[str, str] = {}
        merged.update(self.BUILTIN)
        merged.update(self._lov_prefixes)
        merged.update(self._model_prefixes)
        merged.update(self._user_prefixes)
        return merged

    async def import_lov_prefixes(self, http_client: httpx.AsyncClient) -> int:
        """Fetch vocabulary prefixes from LOV (Linked Open Vocabularies).

        Fetches from the LOV REST API, parses the JSON response, and stores
        prefix/namespace pairs in the LOV layer. Returns the count of imported
        prefixes. Handles errors gracefully (logs warning, returns 0 on failure).
        """
        url = "https://lov.linkeddata.es/dataset/lov/api/v2/vocabulary/list"
        try:
            resp = await http_client.get(url, timeout=30.0)
            resp.raise_for_status()
            vocabs = resp.json()
        except Exception:
            logger.warning("Failed to fetch LOV vocabulary list", exc_info=True)
            return 0

        count = 0
        for entry in vocabs:
            prefix = entry.get("prefix")
            nsp = entry.get("nsp")
            if prefix and nsp:
                self._lov_prefixes[prefix] = nsp
                count += 1

        if count > 0:
            self._reverse_cache = None
            logger.info("Imported %d prefixes from LOV", count)

        return count

    def _lookup_prefix(self, prefix: str) -> Optional[str]:
        """Look up namespace by prefix. User > Model > LOV > Built-in."""
        return (
            self._user_prefixes.get(prefix)
            or self._model_prefixes.get(prefix)
            or self._lov_prefixes.get(prefix)
            or self.BUILTIN.get(prefix)
        )

    def _get_reverse_map(self) -> dict[str, str]:
        """Build or return cached reverse map (namespace -> prefix).

        Built from all layers respecting precedence: user overrides win.
        The map is invalidated (set to None) whenever any layer changes.
        """
        if self._reverse_cache is not None:
            return self._reverse_cache

        # Build reverse map: later layers override earlier (higher precedence)
        reverse: dict[str, str] = {}
        for prefix, ns in self.BUILTIN.items():
            reverse[ns] = prefix
        for prefix, ns in self._lov_prefixes.items():
            reverse[ns] = prefix
        for prefix, ns in self._model_prefixes.items():
            reverse[ns] = prefix
        for prefix, ns in self._user_prefixes.items():
            reverse[ns] = prefix

        self._reverse_cache = reverse
        return reverse
