"""Explorer configuration model and SPARQL query composition engine.

Builds composable SPARQL queries from filter/group/sort layers for the
workspace explorer tree.  Reuses label resolution patterns from
``app.vfs.strategies`` — never duplicates them.

The composition engine produces two query types:
  1. **Explorer query** — returns individual objects with group/sort bindings
  2. **Group folders query** — returns distinct group values with counts

Both query against ``urn:sempkm:current`` graph.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.rdf.namespaces import CURRENT_GRAPH
from app.sparql.builder import safe_iri
from app.vfs.strategies import _LABEL_COALESCE, _LABEL_OPTIONALS

logger = logging.getLogger(__name__)

# Well-known tag predicates checked when group_by='tag'
_TAG_PREDICATES = [
    "urn:sempkm:vocab:basic-pkm:tags",
    "https://schema.org/keywords",
]

# ── Configuration dataclass ──────────────────────────────────────────


@dataclass
class ExplorerConfig:
    """Declarative explorer configuration for filter/group/sort layers.

    Attributes:
        type_filter: Type IRI to restrict results, or None for all types.
        group_by: Grouping mode — 'type', 'tag', or a property IRI.
            None means flat (no grouping).
        sort_by: Sort mode — 'label', 'created', or a property IRI.
            Defaults to 'label'.
        sort_order: 'asc' or 'desc'. Defaults to 'asc'.
    """

    type_filter: str | None = None
    group_by: str | None = None
    sort_by: str = "label"
    sort_order: str = "asc"

    def __post_init__(self) -> None:
        if self.sort_order not in ("asc", "desc"):
            self.sort_order = "asc"
        # Strip prop: prefix from property IRIs sent by the config builder.
        # The frontend prefixes property IRIs with 'prop:' to distinguish
        # them from built-in options ('type', 'tag', 'label', 'created').
        if self.group_by and self.group_by.startswith("prop:"):
            self.group_by = self.group_by[5:]
        if self.sort_by and self.sort_by.startswith("prop:"):
            self.sort_by = self.sort_by[5:]


# ── Query composition ────────────────────────────────────────────────


def build_explorer_query(config: ExplorerConfig) -> str:
    """Compose a SPARQL SELECT from the explorer configuration layers.

    The query always returns ``?iri``, ``?label``, ``?typeIri``.
    Depending on config, it also binds ``?groupValue``, ``?groupLabel``,
    and ``?sortValue``.

    Layers compose additively:
      - **filter**: constrains ``?iri a <type>``
      - **group**: adds ``?groupValue`` / ``?groupLabel`` bindings
      - **sort**: adds ``ORDER BY`` clause with optional property binding
    """
    where_parts: list[str] = []
    optionals: list[str] = []
    binds: list[str] = []
    order_clause: str

    # ── Base pattern ──
    where_parts.append("?iri a ?typeIri .")

    # ── Filter layer ──
    if config.type_filter:
        type_iri = safe_iri(config.type_filter)
        where_parts.append(f"?iri a {type_iri} .")

    # ── Label resolution (reused from strategies.py) ──
    optionals.append(_LABEL_OPTIONALS)
    binds.append(f"BIND({_LABEL_COALESCE} AS ?label)")

    # ── Group layer ──
    if config.group_by == "type":
        # Group by RDF type — bind typeIri as group value
        binds.append(
            'BIND(?typeIri AS ?groupValue)\n'
            '  BIND(REPLACE(STR(?typeIri), ".*[/:#]", "") AS ?groupLabel)'
        )
    elif config.group_by == "tag":
        # Group by tag — union across known tag predicates
        tag_unions = " UNION ".join(
            f'{{ ?iri <{pred}> ?groupValue }}'
            for pred in _TAG_PREDICATES
        )
        optionals.append(f"OPTIONAL {{ {tag_unions} }}")
        binds.append("BIND(STR(?groupValue) AS ?groupLabel)")
    elif config.group_by:
        # Group by arbitrary property IRI
        group_iri = safe_iri(config.group_by)
        optionals.append(
            f"OPTIONAL {{\n"
            f"    ?iri {group_iri} ?groupValue .\n"
            f"    OPTIONAL {{ ?groupValue <http://purl.org/dc/terms/title> ?_gvt }}\n"
            f"    OPTIONAL {{ ?groupValue <http://www.w3.org/2000/01/rdf-schema#label> ?_gvr }}\n"
            f"  }}"
        )
        binds.append(
            "BIND(\n"
            "    IF(isIRI(?groupValue),\n"
            '       COALESCE(?_gvt, ?_gvr, REPLACE(STR(?groupValue), ".*[/:#]", "")),\n'
            "       STR(?groupValue))\n"
            "    AS ?groupLabel\n"
            "  )"
        )

    # ── Sort layer ──
    if config.sort_by == "label":
        order_clause = f"ORDER BY {'DESC(?label)' if config.sort_order == 'desc' else '?label'}"
    elif config.sort_by == "created":
        optionals.append(
            "OPTIONAL { ?iri <http://purl.org/dc/terms/created> ?sortValue }"
        )
        order_clause = (
            f"ORDER BY {'DESC(?sortValue)' if config.sort_order == 'desc' else '?sortValue'} ?label"
        )
    elif config.sort_by:
        # Sort by arbitrary property IRI
        sort_iri = safe_iri(config.sort_by)
        optionals.append(f"OPTIONAL {{ ?iri {sort_iri} ?sortValue }}")
        order_clause = (
            f"ORDER BY {'DESC(?sortValue)' if config.sort_order == 'desc' else '?sortValue'} ?label"
        )
    else:
        order_clause = "ORDER BY ?label"

    # ── Assemble ──
    where_body = "\n  ".join(where_parts)
    optionals_body = "\n  ".join(optionals)
    binds_body = "\n  ".join(binds)

    return (
        f"SELECT ?iri ?label ?typeIri ?groupValue ?groupLabel ?sortValue\n"
        f"FROM <{CURRENT_GRAPH}>\n"
        f"WHERE {{\n"
        f"  {where_body}\n"
        f"  {optionals_body}\n"
        f"  {binds_body}\n"
        f"  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)\n"
        f"}}\n"
        f"{order_clause}"
    )


def build_group_folders_query(config: ExplorerConfig) -> str | None:
    """Build a SPARQL query for folder-level groups (distinct values + counts).

    Returns None if no grouping is configured.
    """
    if not config.group_by:
        return None

    where_parts: list[str] = []
    binds: list[str] = []

    # Base: we need objects
    where_parts.append("?iri a ?typeIri .")

    # Filter layer
    if config.type_filter:
        type_iri = safe_iri(config.type_filter)
        where_parts.append(f"?iri a {type_iri} .")

    where_parts.append(
        "FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)"
    )

    if config.group_by == "type":
        binds.append(
            'BIND(?typeIri AS ?groupValue)\n'
            '  BIND(REPLACE(STR(?typeIri), ".*[/:#]", "") AS ?groupLabel)'
        )
    elif config.group_by == "tag":
        tag_unions = " UNION ".join(
            f'{{ ?iri <{pred}> ?groupValue }}'
            for pred in _TAG_PREDICATES
        )
        where_parts.append(f"{{ {tag_unions} }}")
        binds.append("BIND(STR(?groupValue) AS ?groupLabel)")
    elif config.group_by:
        group_iri = safe_iri(config.group_by)
        where_parts.append(f"?iri {group_iri} ?groupValue .")
        binds.append(
            "OPTIONAL { ?groupValue <http://purl.org/dc/terms/title> ?_gvt }\n"
            "  OPTIONAL { ?groupValue <http://www.w3.org/2000/01/rdf-schema#label> ?_gvr }\n"
            "  BIND(\n"
            "    IF(isIRI(?groupValue),\n"
            '       COALESCE(?_gvt, ?_gvr, REPLACE(STR(?groupValue), ".*[/:#]", "")),\n'
            "       STR(?groupValue))\n"
            "    AS ?groupLabel\n"
            "  )"
        )

    where_body = "\n  ".join(where_parts)
    binds_body = "\n  ".join(binds)

    return (
        f"SELECT ?groupValue ?groupLabel (COUNT(DISTINCT ?iri) AS ?count)\n"
        f"FROM <{CURRENT_GRAPH}>\n"
        f"WHERE {{\n"
        f"  {where_body}\n"
        f"  {binds_body}\n"
        f"}}\n"
        f"GROUP BY ?groupValue ?groupLabel\n"
        f"ORDER BY ?groupLabel"
    )
