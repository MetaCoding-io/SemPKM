"""SPARQL query scoping and prefix injection utilities.

Ensures user SPARQL queries are automatically scoped to the current state
graph (urn:sempkm:current) so event graph data does not leak into results.
Also injects common PREFIX declarations for convenience.

Per research Pitfall 3: without explicit FROM or GRAPH clauses, SPARQL
queries may return results from ALL named graphs including event graphs.
"""

import re

from app.rdf.namespaces import COMMON_PREFIXES, CURRENT_GRAPH_IRI

CURRENT_GRAPH = str(CURRENT_GRAPH_IRI)


def scope_to_current_graph(query: str, all_graphs: bool = False) -> str:
    """Inject FROM <urn:sempkm:current> into SPARQL queries.

    Scopes SELECT and CONSTRUCT queries to the current state graph by
    inserting a FROM clause before the WHERE keyword. Leaves the query
    unchanged if:
    - all_graphs=True (explicit admin/debug bypass)
    - Query already contains a FROM clause
    - Query already contains a GRAPH clause referencing the current graph

    Args:
        query: The SPARQL query string.
        all_graphs: If True, skip scoping (for admin/debug use).

    Returns:
        The query with FROM clause injected, or unchanged if scoping
        is not needed.
    """
    if all_graphs:
        return query

    # Check if query already has FROM or GRAPH clauses
    upper = query.upper()

    # Already has FROM clause -- user is explicitly controlling graph scope
    if re.search(r'\bFROM\s+', upper):
        return query

    # Already has GRAPH clause referencing current graph
    if CURRENT_GRAPH in query:
        return query

    # Inject FROM <current> before WHERE for SELECT and CONSTRUCT queries
    # Match WHERE keyword (case-insensitive) that's not inside a string literal
    from_clause = f"FROM <{CURRENT_GRAPH}>\n"

    # Find WHERE keyword position (case-insensitive, word boundary)
    where_match = re.search(r'\bWHERE\b', query, re.IGNORECASE)
    if where_match:
        insert_pos = where_match.start()
        return query[:insert_pos] + from_clause + query[insert_pos:]

    # No WHERE clause found -- return as-is (unusual but possible for
    # queries like DESCRIBE or ASK without explicit WHERE)
    return query


def inject_prefixes(query: str) -> str:
    """Prepend common PREFIX declarations to the query.

    Adds PREFIX lines for rdf:, rdfs:, xsd:, sempkm:, schema:, dcterms:,
    and skos: unless they are already declared in the query. This enables
    users to write queries using prefixed names without declaring them.

    Args:
        query: The SPARQL query string.

    Returns:
        The query with missing PREFIX declarations prepended.
    """
    prefix_lines = []
    upper = query.upper()

    for prefix, namespace in COMMON_PREFIXES.items():
        # Check if this prefix is already declared (case-insensitive)
        pattern = rf'\bPREFIX\s+{re.escape(prefix)}:'
        if not re.search(pattern, upper, re.IGNORECASE):
            prefix_lines.append(f"PREFIX {prefix}: <{namespace}>")

    if prefix_lines:
        return "\n".join(prefix_lines) + "\n" + query

    return query
