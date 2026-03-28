"""Directory strategy definitions and SPARQL query builders for mount collections.

Each strategy determines how objects are organized into folders:
  - flat: All objects in a single directory
  - by-type: One folder per rdf:type
  - by-date: Year/Month hierarchy based on a date property
  - by-tag: One folder per distinct value of a tag/keyword property
  - by-property: One folder per distinct value of an arbitrary property

Query builders produce SPARQL strings against urn:sempkm:current graph.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from app.vfs.mount_service import MountDefinition
from app.rdf.namespaces import CURRENT_GRAPH, QUERIES_GRAPH

if TYPE_CHECKING:
    from app.triplestore.sync_client import SyncTriplestoreClient

logger = logging.getLogger(__name__)

# ── Query resolution constants ───────────────────────────────────────
PRED_QUERY_TEXT = "urn:sempkm:vocab:queryText"


class DirectoryStrategy(Enum):
    """Supported directory organization strategies."""

    FLAT = "flat"
    BY_TYPE = "by-type"
    BY_DATE = "by-date"
    BY_TAG = "by-tag"
    BY_PROPERTY = "by-property"


# ── Label resolution COALESCE pattern ────────────────────────────────

_LABEL_OPTIONALS = """
  OPTIONAL { ?iri <http://purl.org/dc/terms/title> ?t }
  OPTIONAL { ?iri <http://www.w3.org/2000/01/rdf-schema#label> ?r }
  OPTIONAL { ?iri <http://www.w3.org/2004/02/skos/core#prefLabel> ?s }
  OPTIONAL { ?iri <https://schema.org/name> ?sn }
  OPTIONAL { ?iri <http://xmlns.com/foaf/0.1/name> ?f }
"""

_LABEL_COALESCE = 'COALESCE(?t, ?r, ?s, ?sn, ?f, REPLACE(STR(?iri), ".*[/:#]", ""))'


# ── Scope filter builder ─────────────────────────────────────────────

def build_scope_filter(
    mount: MountDefinition,
    resolved_query_text: str | None = None,
    sync_client: SyncTriplestoreClient | None = None,
) -> str:
    """Build a SPARQL scope filter fragment from mount definition.

    If resolved_query_text is provided (pre-resolved from scope_query),
    it is used as the scope filter. If not provided but mount.scope_query
    is set and sync_client is available, resolves the query text from the
    triplestore (with caching). Otherwise falls back to sparql_scope.
    Returns an empty string for scope "all" or when no scope is set.

    When mount.type_filter is a non-empty list, generates a VALUES clause
    constraining ?type and a ?iri a ?type binding. This composes with
    scope via AND — both clauses appear in the returned fragment.

    Args:
        mount: The mount definition.
        resolved_query_text: Pre-resolved SPARQL query text from scope_query.
            Caller is responsible for resolving the query IRI to text before calling.
        sync_client: Optional SyncTriplestoreClient for resolving scope_query
            in WebDAV (sync) context. Ignored when resolved_query_text is provided.
    """
    parts: list[str] = []

    # ── Type filter VALUES clause ──
    if mount.type_filter:
        iris = " ".join(f"<{iri}>" for iri in mount.type_filter)
        parts.append(f"VALUES ?type {{ {iris} }}\n  ?iri a ?type .")
        logger.debug("type_filter VALUES clause generated with %d IRIs", len(mount.type_filter))

    # ── Resolve scope_query if needed ──
    if not resolved_query_text and mount.scope_query and sync_client is not None:
        resolved_query_text = _resolve_scope_query_sync(mount.scope_query, sync_client)

    # ── Scope filter (saved query or sparql_scope) ──
    if resolved_query_text:
        parts.append(f"{{ SELECT ?iri WHERE {{ {_extract_where_body(resolved_query_text)} }} }}")
    elif mount.sparql_scope and mount.sparql_scope != "all":
        parts.append(f"{{ SELECT ?iri WHERE {{ {mount.sparql_scope} }} }}")

    return "\n  ".join(parts)


def _resolve_scope_query_sync(scope_query_iri: str, sync_client: SyncTriplestoreClient) -> str | None:
    """Resolve a scope_query IRI to its SPARQL query text via sync client.

    Uses the listing_cache with key ``query_text:{uuid}`` to avoid
    repeated triplestore lookups within the TTL window.

    Returns the query text string, or None if the IRI is not found.
    """
    from app.vfs.cache import listing_cache, _cache_lock

    # Extract UUID from IRI (urn:sempkm:query:{uuid})
    uuid_part = scope_query_iri
    if scope_query_iri.startswith("urn:sempkm:query:"):
        uuid_part = scope_query_iri[len("urn:sempkm:query:"):]

    cache_key = f"query_text:{uuid_part}"

    # Check cache (read outside lock is acceptable — worst case stale miss)
    cached = listing_cache.get(cache_key)
    if cached is not None:
        logger.debug("scope_query %s resolved from cache", scope_query_iri)
        return cached

    logger.debug("Resolving scope_query %s via sync triplestore client", scope_query_iri)
    sparql = (
        f"SELECT ?text FROM <{QUERIES_GRAPH}> WHERE {{\n"
        f"  <{scope_query_iri}> <{PRED_QUERY_TEXT}> ?text\n"
        f"}}"
    )
    result = sync_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])

    if not bindings:
        logger.warning("scope_query %s not found in triplestore — ignoring", scope_query_iri)
        return None

    text = bindings[0]["text"]["value"]

    with _cache_lock:
        listing_cache[cache_key] = text

    return text


def _extract_where_body(query_text: str) -> str:
    """Extract the WHERE clause body from a SPARQL SELECT query.

    For simple queries like:
      SELECT ?s WHERE { ?s a <type> }
    Returns: ?s a <type>

    For queries with ?s or ?iri binding, renames to ?iri if needed.
    Falls back to wrapping the entire query as a sub-select if parsing fails.
    """
    import re
    # Try to find WHERE { ... } block
    match = re.search(r'WHERE\s*\{(.+)\}\s*$', query_text, re.IGNORECASE | re.DOTALL)
    if match:
        body = match.group(1).strip()
        # If the query uses ?s instead of ?iri, we need to check what
        # variable is in the SELECT clause and map it
        select_match = re.search(r'SELECT\s+(\?\w+)', query_text, re.IGNORECASE)
        if select_match:
            select_var = select_match.group(1)
            if select_var != '?iri':
                body = body.replace(select_var, '?iri')
        return body
    # Fallback: use the raw query text as-is (may not work for all queries)
    return query_text


# ── Strategy query builders ──────────────────────────────────────────

def query_flat_objects(scope_filter: str) -> str:
    """List all objects with labels (flat strategy)."""
    return f"""
SELECT ?iri ?label ?typeIri ?created
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri a ?typeIri .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  OPTIONAL {{ ?iri <http://purl.org/dc/terms/created> ?created }}
  {scope_filter}
  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
}}
ORDER BY ?label
"""


def query_type_folders(scope_filter: str) -> str:
    """List distinct types with labels (by-type strategy folders)."""
    return f"""
SELECT DISTINCT ?typeIri ?typeLabel
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri a ?typeIri .
  {scope_filter}
  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
  BIND(REPLACE(STR(?typeIri), ".*[/:#]", "") AS ?typeLabel)
}}
ORDER BY ?typeLabel
"""


def query_objects_by_type(type_iri: str, scope_filter: str) -> str:
    """List objects of a specific type."""
    return f"""
SELECT ?iri ?label ?created
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri a <{type_iri}> .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  OPTIONAL {{ ?iri <http://purl.org/dc/terms/created> ?created }}
  {scope_filter}
}}
ORDER BY ?label
"""


def query_date_year_folders(date_property: str, scope_filter: str) -> str:
    """List distinct years from a date property (by-date strategy top-level)."""
    return f"""
SELECT DISTINCT ?year
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri <{date_property}> ?dateVal .
  {scope_filter}
  BIND(STR(YEAR(?dateVal)) AS ?year)
  FILTER(BOUND(?year))
}}
ORDER BY ?year
"""


def query_date_month_folders(date_property: str, year: str, scope_filter: str) -> str:
    """List distinct months within a year from a date property."""
    return f"""
SELECT DISTINCT ?month ?monthNum
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri <{date_property}> ?dateVal .
  {scope_filter}
  FILTER(STR(YEAR(?dateVal)) = "{year}")
  BIND(MONTH(?dateVal) AS ?monthNum)
  BIND(STR(?monthNum) AS ?month)
  FILTER(BOUND(?monthNum))
}}
ORDER BY ?monthNum
"""


def query_objects_by_date(
    date_property: str, year: str, month: int, scope_filter: str
) -> str:
    """List objects matching a specific year and month."""
    return f"""
SELECT ?iri ?label ?typeIri ?created
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri <{date_property}> ?dateVal ;
       a ?typeIri .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  OPTIONAL {{ ?iri <http://purl.org/dc/terms/created> ?created }}
  {scope_filter}
  FILTER(STR(YEAR(?dateVal)) = "{year}" && MONTH(?dateVal) = {month})
  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
}}
ORDER BY ?label
"""


def query_tag_folders(tag_property: str, scope_filter: str) -> str:
    """List distinct tag values (by-tag strategy folders)."""
    return f"""
SELECT DISTINCT ?tagValue
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri <{tag_property}> ?tagValue .
  {scope_filter}
}}
ORDER BY ?tagValue
"""


def query_objects_by_tag(tag_property: str, tag_value: str, scope_filter: str) -> str:
    """List objects with a specific tag value."""
    return f"""
SELECT ?iri ?label ?typeIri ?created
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri <{tag_property}> ?matchVal ;
       a ?typeIri .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  OPTIONAL {{ ?iri <http://purl.org/dc/terms/created> ?created }}
  {scope_filter}
  FILTER(STR(?matchVal) = "{_escape(tag_value)}")
  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
}}
ORDER BY ?label
"""


def query_property_folders(group_property: str, scope_filter: str) -> str:
    """List distinct values of a grouping property with label resolution."""
    return f"""
SELECT DISTINCT ?groupValue ?groupLabel
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri <{group_property}> ?groupValue .
  {scope_filter}
  OPTIONAL {{
    ?groupValue <http://purl.org/dc/terms/title> ?gt .
  }}
  OPTIONAL {{
    ?groupValue <http://www.w3.org/2000/01/rdf-schema#label> ?gr .
  }}
  BIND(
    IF(isIRI(?groupValue),
       COALESCE(?gt, ?gr, REPLACE(STR(?groupValue), ".*[/:#]", "")),
       STR(?groupValue))
    AS ?groupLabel
  )
}}
ORDER BY ?groupLabel
"""


def query_objects_by_property(
    group_property: str, group_value: str, is_iri: bool, scope_filter: str
) -> str:
    """List objects with a specific property value."""
    if is_iri:
        value_filter = f"FILTER(?matchVal = <{group_value}>)"
    else:
        value_filter = f'FILTER(STR(?matchVal) = "{_escape(group_value)}")'

    return f"""
SELECT ?iri ?label ?typeIri ?created
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri <{group_property}> ?matchVal ;
       a ?typeIri .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  OPTIONAL {{ ?iri <http://purl.org/dc/terms/created> ?created }}
  {scope_filter}
  {value_filter}
  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
}}
ORDER BY ?label
"""


def query_uncategorized_objects(group_property: str, scope_filter: str) -> str:
    """List objects missing the grouping property (_uncategorized folder)."""
    return f"""
SELECT ?iri ?label ?typeIri ?created
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri a ?typeIri .
  FILTER NOT EXISTS {{ ?iri <{group_property}> ?anyVal }}
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  OPTIONAL {{ ?iri <http://purl.org/dc/terms/created> ?created }}
  {scope_filter}
  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
}}
ORDER BY ?label
"""


def query_has_uncategorized(group_property: str, scope_filter: str) -> str:
    """Check if any objects are missing the grouping property."""
    return f"""
ASK
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri a ?anyType .
  FILTER NOT EXISTS {{ ?iri <{group_property}> ?anyVal }}
  {scope_filter}
  FILTER(?anyType != <http://www.w3.org/2000/01/rdf-schema#Resource>)
}}
"""


def _escape(value: str) -> str:
    """Escape special characters for SPARQL string literals."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


# ── Chain scope narrowing ────────────────────────────────────────────

def build_chain_narrowing_filter(
    strategy: str,
    folder_value: str,
    mount: MountDefinition,
    *,
    parent_folder_value: str | None = None,
) -> str:
    """Return a SPARQL WHERE clause fragment narrowing objects to those matching a folder grouping.

    Each chain level calls this to build cumulative scope narrowing from all parent levels.

    Args:
        strategy: The strategy at this chain level (e.g., 'by-type', 'by-tag').
        folder_value: The folder name selected at this level.
        mount: The mount definition (for property IRIs).
        parent_folder_value: For by-date month level, the year value from parent.

    Returns:
        A SPARQL WHERE clause fragment (without outer braces).
    """
    if strategy == "by-type":
        # folder_value is the type local name — need type IRI resolution
        # We generate a FILTER on the type local name since we don't have the sync client here
        escaped = _escape(folder_value)
        return (
            f'?iri a ?_chainType .\n'
            f'  FILTER(REPLACE(STR(?_chainType), ".*[/:#]", "") = "{escaped}")'
        )

    elif strategy == "by-tag":
        if not mount.group_by_property:
            return ""
        escaped = _escape(folder_value)
        return f'?iri <{mount.group_by_property}> ?_chainTag .\n  FILTER(STR(?_chainTag) = "{escaped}")'

    elif strategy == "by-property":
        if not mount.group_by_property:
            return ""
        escaped = _escape(folder_value)
        return (
            f'?iri <{mount.group_by_property}> ?_chainPval .\n'
            f'  FILTER(STR(?_chainPval) = "{escaped}" || '
            f'(isIRI(?_chainPval) && REPLACE(STR(?_chainPval), ".*[/:#]", "") = "{escaped}"))'
        )

    elif strategy == "by-date":
        if not mount.date_property:
            return ""
        # Determine if this is year or month level based on parent_folder_value
        if parent_folder_value is not None:
            # Month level — folder_value is "MM-MonthName", parent is year
            month_num = _parse_month_folder(folder_value)
            if month_num is not None:
                return (
                    f'?iri <{mount.date_property}> ?_chainDate .\n'
                    f'  FILTER(STR(YEAR(?_chainDate)) = "{_escape(parent_folder_value)}" '
                    f'&& MONTH(?_chainDate) = {month_num})'
                )
            # Fallback: just year filter
            return (
                f'?iri <{mount.date_property}> ?_chainDate .\n'
                f'  FILTER(STR(YEAR(?_chainDate)) = "{_escape(parent_folder_value)}")'
            )
        else:
            # Year level — folder_value is "2024"
            escaped = _escape(folder_value)
            return (
                f'?iri <{mount.date_property}> ?_chainDate .\n'
                f'  FILTER(STR(YEAR(?_chainDate)) = "{escaped}")'
            )

    elif strategy == "flat":
        return ""

    return ""


def _parse_month_folder(folder_value: str) -> int | None:
    """Parse month number from 'MM-MonthName' folder format."""
    if "-" in folder_value:
        try:
            return int(folder_value.split("-")[0])
        except ValueError:
            return None
    return None
