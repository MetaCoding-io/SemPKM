"""SPARQL query scoping and prefix injection utilities.

Ensures user SPARQL queries are automatically scoped to the current state
graph (urn:sempkm:current) so event graph data does not leak into results.
Also injects common PREFIX declarations for convenience.

Per research Pitfall 3: without explicit FROM or GRAPH clauses, SPARQL
queries may return results from ALL named graphs including event graphs.
"""

import re

from fastapi import HTTPException

from app.rdf.namespaces import COMMON_PREFIXES, CURRENT_GRAPH_IRI, INFERRED_GRAPH_IRI

CURRENT_GRAPH = str(CURRENT_GRAPH_IRI)
INFERRED_GRAPH = str(INFERRED_GRAPH_IRI)

# Regex for SPARQL string literals and comments.
# Order matters: triple-quoted forms must be tried before single-quoted
# to avoid partial matches.  Escaped quotes inside strings are handled
# by the non-greedy interior combined with the escaped-quote alternative.
_SPARQL_STRINGS_RE = re.compile(
    r'"""(?:[^"\\]|\\.|"(?!""))*"""'   # """..."""
    r"|'''(?:[^'\\]|\\.|'(?!''))*'''"  # '''...'''
    r'|"(?:[^"\\]|\\.)*"'             # "..."
    r"|'(?:[^'\\]|\\.)*'"             # '...'
    r"|#[^\n]*",                       # # comment to EOL
    re.DOTALL,
)


def _strip_sparql_strings(query: str) -> str:
    """Blank out SPARQL string literal contents and comments.

    Replaces the *interior* of string literals with spaces (preserving
    delimiters and overall length) and replaces ``#``-comments with
    spaces.  This allows keyword detection (FROM, GRAPH, …) to run on
    the result without false-positives on keywords that appear inside
    strings or comments.

    Handles all four SPARQL string forms (``"…"``, ``'…'``,
    ``\"\"\"…\"\"\"``, ``'''…'''``) plus hash-comments.
    """

    def _blank(m: re.Match) -> str:
        text = m.group()
        if text.startswith("#"):
            # Replace entire comment with spaces
            return " " * len(text)
        # Determine delimiter length (3 for triple-quoted, 1 for single)
        if text.startswith('"""') or text.startswith("'''"):
            dlen = 3
        else:
            dlen = 1
        # Keep delimiters, blank interior with spaces
        interior_len = len(text) - 2 * dlen
        return text[:dlen] + " " * interior_len + text[-dlen:]

    return _SPARQL_STRINGS_RE.sub(_blank, query)


def check_member_query_safety(query: str) -> None:
    """Validate that a SPARQL query is safe for member-role users.

    Members are restricted to the current graph only. Queries containing
    FROM or GRAPH clauses are rejected because they could be used to
    access data outside the scoped current graph.

    Args:
        query: The raw SPARQL query string.

    Raises:
        HTTPException: 403 if FROM or GRAPH clauses are detected.
    """
    upper = _strip_sparql_strings(query).upper()
    if re.search(r'\bFROM\s+', upper):
        raise HTTPException(
            status_code=403,
            detail="FROM/GRAPH clauses not allowed for member role",
        )
    if re.search(r'\bGRAPH\s+', upper):
        raise HTTPException(
            status_code=403,
            detail="FROM/GRAPH clauses not allowed for member role",
        )


def scope_to_current_graph(
    query: str,
    all_graphs: bool = False,
    include_inferred: bool = True,
    shared_graphs: list[str] | None = None,
) -> str:
    """Inject FROM <urn:sempkm:current> into SPARQL queries.

    Scopes SELECT and CONSTRUCT queries to the current state graph by
    inserting a FROM clause before the WHERE keyword. When include_inferred
    is True, also injects FROM <urn:sempkm:inferred> so inferred triples
    are included in query results. When shared_graphs is provided, adds
    FROM clauses for each shared graph so their data is included.

    Leaves the query unchanged if:
    - all_graphs=True (explicit admin/debug bypass)
    - Query already contains a FROM clause
    - Query already contains a GRAPH clause referencing the current graph

    Args:
        query: The SPARQL query string.
        all_graphs: If True, skip scoping (for admin/debug use).
        include_inferred: If True, also include the inferred graph
            (default True). Set to False to query only user-created data.
        shared_graphs: Optional list of shared graph IRIs to include
            in FROM clauses. Default None preserves backward compatibility.

    Returns:
        The query with FROM clause(s) injected, or unchanged if scoping
        is not needed.
    """
    if all_graphs:
        return query

    # Check if query already has FROM or GRAPH clauses.
    # Strip string literals and comments first to avoid false-positives
    # on keywords like FROM/GRAPH that appear inside strings or comments.
    stripped_upper = _strip_sparql_strings(query).upper()

    # Already has FROM clause -- user is explicitly controlling graph scope
    if re.search(r'\bFROM\s+', stripped_upper):
        return query

    # Already has GRAPH clause referencing current graph
    if CURRENT_GRAPH in query:
        return query

    # Inject FROM <current> (and optionally FROM <inferred> and shared graphs) before WHERE
    from_clause = f"FROM <{CURRENT_GRAPH}>\n"
    if include_inferred:
        from_clause += f"FROM <{INFERRED_GRAPH}>\n"
    if shared_graphs:
        for sg in shared_graphs:
            from_clause += f"FROM <{sg}>\n"

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
