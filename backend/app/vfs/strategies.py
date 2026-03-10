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

from enum import Enum

from app.vfs.mount_service import MountDefinition


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

def build_scope_filter(mount: MountDefinition) -> str:
    """Build a SPARQL scope filter fragment from mount definition.

    Returns an empty string for scope "all", otherwise wraps the scope
    as a sub-select that binds ?iri.
    """
    if not mount.sparql_scope or mount.sparql_scope == "all":
        return ""
    # Treat sparql_scope as a WHERE clause fragment binding ?iri
    return f"{{ SELECT ?iri WHERE {{ {mount.sparql_scope} }} }}"


# ── Strategy query builders ──────────────────────────────────────────

def query_flat_objects(scope_filter: str) -> str:
    """List all objects with labels (flat strategy)."""
    return f"""
SELECT ?iri ?label ?typeIri
FROM <urn:sempkm:current>
WHERE {{
  ?iri a ?typeIri .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  {scope_filter}
  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
}}
ORDER BY ?label
"""


def query_type_folders(scope_filter: str) -> str:
    """List distinct types with labels (by-type strategy folders)."""
    return f"""
SELECT DISTINCT ?typeIri ?typeLabel
FROM <urn:sempkm:current>
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
SELECT ?iri ?label
FROM <urn:sempkm:current>
WHERE {{
  ?iri a <{type_iri}> .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  {scope_filter}
}}
ORDER BY ?label
"""


def query_date_year_folders(date_property: str, scope_filter: str) -> str:
    """List distinct years from a date property (by-date strategy top-level)."""
    return f"""
SELECT DISTINCT ?year
FROM <urn:sempkm:current>
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
FROM <urn:sempkm:current>
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
SELECT ?iri ?label ?typeIri
FROM <urn:sempkm:current>
WHERE {{
  ?iri <{date_property}> ?dateVal ;
       a ?typeIri .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
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
FROM <urn:sempkm:current>
WHERE {{
  ?iri <{tag_property}> ?tagValue .
  {scope_filter}
}}
ORDER BY ?tagValue
"""


def query_objects_by_tag(tag_property: str, tag_value: str, scope_filter: str) -> str:
    """List objects with a specific tag value."""
    return f"""
SELECT ?iri ?label ?typeIri
FROM <urn:sempkm:current>
WHERE {{
  ?iri <{tag_property}> ?matchVal ;
       a ?typeIri .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
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
FROM <urn:sempkm:current>
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
SELECT ?iri ?label ?typeIri
FROM <urn:sempkm:current>
WHERE {{
  ?iri <{group_property}> ?matchVal ;
       a ?typeIri .
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  {scope_filter}
  {value_filter}
  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
}}
ORDER BY ?label
"""


def query_uncategorized_objects(group_property: str, scope_filter: str) -> str:
    """List objects missing the grouping property (_uncategorized folder)."""
    return f"""
SELECT ?iri ?label ?typeIri
FROM <urn:sempkm:current>
WHERE {{
  ?iri a ?typeIri .
  FILTER NOT EXISTS {{ ?iri <{group_property}> ?anyVal }}
  {_LABEL_OPTIONALS}
  BIND({_LABEL_COALESCE} AS ?label)
  {scope_filter}
  FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
}}
ORDER BY ?label
"""


def query_has_uncategorized(group_property: str, scope_filter: str) -> str:
    """Check if any objects are missing the grouping property."""
    return f"""
ASK
FROM <urn:sempkm:current>
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
