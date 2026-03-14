"""OntologyService for loading and managing upper ontologies in the triplestore.

Handles batched INSERT DATA loading of gist (and future ontologies) with
idempotent version checking. Gist is loaded into its own named graph at
startup so TBox/ABox/RBox queries can traverse cross-graph class hierarchies.

TBox query methods (get_root_classes, get_subclasses) use FROM clause
aggregation across gist + all installed model ontology graphs + user-types
to present a unified class hierarchy.
"""

import logging
import re
import time
import uuid
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD

from app.models.registry import MODELS_GRAPH, SEMPKM_NS
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Named graphs for ontology data
GIST_GRAPH = "urn:sempkm:ontology:gist"
USER_TYPES_GRAPH = "urn:sempkm:user-types"

# Gist IRIs
GIST_ONTOLOGY_IRI = "https://w3id.org/semanticarts/ontology/gistCore"
GIST_NS = "https://w3id.org/semanticarts/ns/ontology/gist/"

# Batch size for INSERT DATA operations (triples per batch)
BATCH_SIZE = 500

# SemPKM predicates for user-type metadata
SEMPKM_TYPE_ICON = URIRef(f"{SEMPKM_NS}typeIcon")
SEMPKM_TYPE_COLOR = URIRef(f"{SEMPKM_NS}typeColor")

# Allowed datatypes for user-defined properties
ALLOWED_DATATYPES = {
    str(XSD.string),
    str(XSD.integer),
    str(XSD.decimal),
    str(XSD.boolean),
    str(XSD.date),
    str(XSD.dateTime),
    str(XSD.anyURI),
}


def _property_source(iri: str) -> str:
    """Determine the source label for a property IRI.

    Returns 'gist' for gist ontology properties, or extracts the model
    name from urn:sempkm:model:{name}: IRIs.  Falls back to 'other'.
    """
    if GIST_NS in iri:
        return "gist"
    if iri.startswith("urn:sempkm:model:"):
        # urn:sempkm:model:basic-pkm:HasNote → basic-pkm
        parts = iri.split(":")
        if len(parts) >= 5:
            return parts[3]
    if iri.startswith(str(SEMPKM_NS)):
        return "sempkm"
    return "other"


def _rdf_term_to_sparql(term) -> str:
    """Serialize an rdflib term to SPARQL syntax.

    Handles URIRef, Literal (with datatype/language), and BNode.
    """
    if isinstance(term, URIRef):
        return f"<{term}>"
    elif isinstance(term, Literal):
        escaped = (
            str(term)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        if term.language:
            return f'"{escaped}"@{term.language}'
        elif term.datatype:
            return f'"{escaped}"^^<{term.datatype}>'
        else:
            return f'"{escaped}"'
    elif isinstance(term, BNode):
        return f"_:{term}"
    else:
        return f"<{term}>"


def _split_triples_into_batches(
    triples: list[tuple], batch_size: int = BATCH_SIZE
) -> list[list[tuple]]:
    """Split a list of triples into batches of at most batch_size."""
    batches = []
    for i in range(0, len(triples), batch_size):
        batches.append(triples[i : i + batch_size])
    return batches


def _build_insert_data_sparql(
    named_graph_iri: str, triples: list[tuple]
) -> str:
    """Build SPARQL INSERT DATA for a batch of triples in a named graph."""
    triple_lines = []
    for s, p, o in triples:
        triple_lines.append(
            f"    {_rdf_term_to_sparql(s)} {_rdf_term_to_sparql(p)} {_rdf_term_to_sparql(o)} ."
        )
    triples_str = "\n".join(triple_lines)
    return f"""INSERT DATA {{
  GRAPH <{named_graph_iri}> {{
{triples_str}
  }}
}}"""


class OntologyService:
    """Manages ontology loading and version checking in the triplestore."""

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    async def is_gist_loaded(self) -> bool:
        """Check whether gist is already loaded via ASK query."""
        sparql = (
            f"ASK {{ GRAPH <{GIST_GRAPH}> {{ "
            f"<{GIST_ONTOLOGY_IRI}> a <http://www.w3.org/2002/07/owl#Ontology> "
            f"}} }}"
        )
        result = await self._client.query(sparql)
        return result.get("boolean", False)

    async def ensure_gist_loaded(self, gist_path: Path) -> None:
        """Load gist ontology into the triplestore if not already present.

        Parses the Turtle file with rdflib, splits triples into batches of
        ≤500, and executes each batch as INSERT DATA within a transaction.
        Skips loading if the version check ASK query returns true.

        Args:
            gist_path: Path to the gistCore Turtle file.
        """
        if await self.is_gist_loaded():
            logger.info("gist already loaded, skipping")
            return

        if not gist_path.exists():
            logger.error("gist ontology file not found: %s", gist_path)
            raise FileNotFoundError(f"gist ontology file not found: {gist_path}")

        start = time.monotonic()
        try:
            # Parse gist Turtle with rdflib
            g = Graph()
            g.parse(gist_path, format="turtle")
            all_triples = list(g)
            triple_count = len(all_triples)

            # Split into batches
            batches = _split_triples_into_batches(all_triples)

            # Execute batches within a transaction
            txn_url = await self._client.begin_transaction()
            try:
                for i, batch in enumerate(batches):
                    sparql = _build_insert_data_sparql(GIST_GRAPH, batch)
                    await self._client.transaction_update(txn_url, sparql)
                    logger.debug(
                        "Inserted batch %d/%d (%d triples)",
                        i + 1,
                        len(batches),
                        len(batch),
                    )
                await self._client.commit_transaction(txn_url)
            except Exception:
                await self._client.rollback_transaction(txn_url)
                raise

            elapsed = time.monotonic() - start
            logger.info(
                "Loaded gist 14.0.0: %d triples in %.1fs", triple_count, elapsed
            )
        except FileNotFoundError:
            raise
        except Exception:
            logger.error("Failed to load gist", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # TBox query methods — cross-graph class hierarchy
    # ------------------------------------------------------------------

    async def get_ontology_graph_iris(self) -> list[str]:
        """Return all ontology graph IRIs for FROM clause aggregation.

        Queries the model registry for installed models and builds the list:
        - urn:sempkm:ontology:gist (always included)
        - urn:sempkm:model:{id}:ontology for each installed model
        - urn:sempkm:user-types (forward-compat for user-defined types)
        """
        sparql = f"""SELECT ?modelId WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId .
  }}
}}"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        graph_iris = [GIST_GRAPH]
        for b in bindings:
            model_id = b["modelId"]["value"]
            graph_iris.append(f"urn:sempkm:model:{model_id}:ontology")
        graph_iris.append(USER_TYPES_GRAPH)
        return graph_iris

    def _build_from_clauses(self, graph_iris: list[str]) -> str:
        """Build FROM clause string for cross-graph SPARQL queries."""
        return "\n".join(f"FROM <{iri}>" for iri in graph_iris)

    async def get_root_classes(self) -> list[dict]:
        """Query root classes across all ontology graphs.

        Root classes are owl:Class instances that have no rdfs:subClassOf
        parent (or only rdfs:subClassOf owl:Thing). Blank nodes are excluded.
        Labels are resolved inline via COALESCE over skos:prefLabel and
        rdfs:label, falling back to local name extraction.

        Returns:
            Sorted list of dicts with keys: iri, label, has_subclasses.
        """
        graph_iris = await self.get_ontology_graph_iris()
        from_clauses = self._build_from_clauses(graph_iris)

        sparql = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?class ?label
{from_clauses}
WHERE {{
  ?class a owl:Class .
  FILTER(isIRI(?class))
  FILTER NOT EXISTS {{
    ?class rdfs:subClassOf ?parent .
    FILTER(isIRI(?parent) && ?parent != owl:Thing)
  }}
  OPTIONAL {{ ?class skos:prefLabel ?skosLabel .
              FILTER(LANG(?skosLabel) = "" || LANG(?skosLabel) = "en") }}
  OPTIONAL {{ ?class rdfs:label ?rdfsLabel .
              FILTER(LANG(?rdfsLabel) = "" || LANG(?rdfsLabel) = "en") }}
  BIND(COALESCE(?skosLabel, ?rdfsLabel,
       REPLACE(STR(?class), "^.*/|^.*#|^.*:", "", "")) AS ?label)
}}
ORDER BY ?label"""

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        classes = []
        class_iris = [b["class"]["value"] for b in bindings]

        # Batch check which classes have subclasses
        has_children = await self._batch_has_subclasses(graph_iris, class_iris)

        for b in bindings:
            iri = b["class"]["value"]
            label = b.get("label", {}).get("value", iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1])
            classes.append({
                "iri": iri,
                "label": label,
                "has_subclasses": has_children.get(iri, False),
            })

        logger.debug(
            "TBox root: %d classes from %d graphs", len(classes), len(graph_iris)
        )
        return classes

    async def get_subclasses(self, parent_iri: str) -> list[dict]:
        """Query direct subclasses of a parent class across all ontology graphs.

        Args:
            parent_iri: IRI of the parent class.

        Returns:
            Sorted list of dicts with keys: iri, label, has_subclasses.
        """
        graph_iris = await self.get_ontology_graph_iris()
        from_clauses = self._build_from_clauses(graph_iris)

        sparql = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?class ?label
{from_clauses}
WHERE {{
  ?class rdfs:subClassOf <{parent_iri}> .
  ?class a owl:Class .
  FILTER(isIRI(?class))
  OPTIONAL {{ ?class skos:prefLabel ?skosLabel .
              FILTER(LANG(?skosLabel) = "" || LANG(?skosLabel) = "en") }}
  OPTIONAL {{ ?class rdfs:label ?rdfsLabel .
              FILTER(LANG(?rdfsLabel) = "" || LANG(?rdfsLabel) = "en") }}
  BIND(COALESCE(?skosLabel, ?rdfsLabel,
       REPLACE(STR(?class), "^.*/|^.*#|^.*:", "", "")) AS ?label)
}}
ORDER BY ?label"""

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        classes = []
        class_iris = [b["class"]["value"] for b in bindings]

        # Batch check which classes have subclasses
        has_children = await self._batch_has_subclasses(graph_iris, class_iris)

        for b in bindings:
            iri = b["class"]["value"]
            label = b.get("label", {}).get("value", iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1])
            classes.append({
                "iri": iri,
                "label": label,
                "has_subclasses": has_children.get(iri, False),
            })

        logger.debug(
            "TBox children of %s: %d subclasses", parent_iri, len(classes)
        )
        return classes

    async def get_class_detail(self, class_iri: str) -> dict:
        """Get detailed metadata for a single class.

        Returns rdfs:comment, parent classes, sibling classes, subclass
        count, instance count, and properties where this class is the
        domain.
        """
        graph_iris = await self.get_ontology_graph_iris()
        from_clauses = self._build_from_clauses(graph_iris)

        # Single query to get comment, parents, subclass count, instance count
        sparql = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?label ?comment ?parentIri ?parentLabel
       (COUNT(DISTINCT ?sub) AS ?subclassCount)
       (COUNT(DISTINCT ?inst) AS ?instanceCount)
{from_clauses}
WHERE {{
  <{class_iri}> a owl:Class .
  OPTIONAL {{ <{class_iri}> skos:prefLabel ?skosLabel .
              FILTER(LANG(?skosLabel) = "" || LANG(?skosLabel) = "en") }}
  OPTIONAL {{ <{class_iri}> rdfs:label ?rdfsLabel .
              FILTER(LANG(?rdfsLabel) = "" || LANG(?rdfsLabel) = "en") }}
  BIND(COALESCE(?skosLabel, ?rdfsLabel,
       REPLACE(STR(<{class_iri}>), "^.*/|^.*#|^.*:", "", "")) AS ?label)
  OPTIONAL {{ <{class_iri}> rdfs:comment ?comment .
              FILTER(LANG(?comment) = "" || LANG(?comment) = "en") }}
  OPTIONAL {{
    <{class_iri}> rdfs:subClassOf ?parentIri .
    FILTER(isIRI(?parentIri) && ?parentIri != owl:Thing)
    OPTIONAL {{ ?parentIri skos:prefLabel ?pSkos .
                FILTER(LANG(?pSkos) = "" || LANG(?pSkos) = "en") }}
    OPTIONAL {{ ?parentIri rdfs:label ?pRdfs .
                FILTER(LANG(?pRdfs) = "" || LANG(?pRdfs) = "en") }}
    BIND(COALESCE(?pSkos, ?pRdfs,
         REPLACE(STR(?parentIri), "^.*/|^.*#|^.*:", "", "")) AS ?parentLabel)
  }}
  OPTIONAL {{ ?sub rdfs:subClassOf <{class_iri}> . FILTER(isIRI(?sub)) }}
  OPTIONAL {{ ?inst a <{class_iri}> . FILTER(isIRI(?inst)) }}
}}
GROUP BY ?label ?comment ?parentIri ?parentLabel"""

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        label = class_iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        comment = ""
        parents = {}
        subclass_count = 0
        instance_count = 0

        for b in bindings:
            if "label" in b:
                label = b["label"]["value"]
            if "comment" in b and b["comment"]["value"]:
                comment = b["comment"]["value"]
            if "parentIri" in b and b["parentIri"]["value"]:
                p_iri = b["parentIri"]["value"]
                p_label = b.get("parentLabel", {}).get(
                    "value", p_iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
                )
                parents[p_iri] = p_label
            sc = b.get("subclassCount", {}).get("value", "0")
            subclass_count = max(subclass_count, int(sc))
            ic = b.get("instanceCount", {}).get("value", "0")
            instance_count = max(instance_count, int(ic))

        parent_classes = [{"iri": k, "label": v} for k, v in parents.items()]

        # Get siblings: classes that share the same parent(s)
        siblings = []
        if parent_classes:
            parent_iri = parent_classes[0]["iri"]
            sib_sparql = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?sib ?sibLabel
{from_clauses}
WHERE {{
  ?sib rdfs:subClassOf <{parent_iri}> .
  ?sib a owl:Class .
  FILTER(isIRI(?sib) && ?sib != <{class_iri}>)
  OPTIONAL {{ ?sib skos:prefLabel ?sSkos .
              FILTER(LANG(?sSkos) = "" || LANG(?sSkos) = "en") }}
  OPTIONAL {{ ?sib rdfs:label ?sRdfs .
              FILTER(LANG(?sRdfs) = "" || LANG(?sRdfs) = "en") }}
  BIND(COALESCE(?sSkos, ?sRdfs,
       REPLACE(STR(?sib), "^.*/|^.*#|^.*:", "", "")) AS ?sibLabel)
}}
ORDER BY ?sibLabel"""
            sib_result = await self._client.query(sib_sparql)
            sib_bindings = sib_result.get("results", {}).get("bindings", [])
            for sb in sib_bindings:
                siblings.append({
                    "iri": sb["sib"]["value"],
                    "label": sb.get("sibLabel", {}).get(
                        "value",
                        sb["sib"]["value"].rsplit("/", 1)[-1].rsplit("#", 1)[-1],
                    ),
                })

        # Get properties where this class is the domain
        prop_sparql = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?prop ?propLabel ?range ?rangeLabel
{from_clauses}
WHERE {{
  ?prop rdfs:domain <{class_iri}> .
  {{ ?prop a owl:ObjectProperty }} UNION {{ ?prop a owl:DatatypeProperty }}
  OPTIONAL {{ ?prop skos:prefLabel ?pSkos .
              FILTER(LANG(?pSkos) = "" || LANG(?pSkos) = "en") }}
  OPTIONAL {{ ?prop rdfs:label ?pRdfs .
              FILTER(LANG(?pRdfs) = "" || LANG(?pRdfs) = "en") }}
  BIND(COALESCE(?pSkos, ?pRdfs,
       REPLACE(STR(?prop), "^.*/|^.*#|^.*:", "", "")) AS ?propLabel)
  OPTIONAL {{
    ?prop rdfs:range ?range .
    OPTIONAL {{ ?range skos:prefLabel ?rSkos .
                FILTER(LANG(?rSkos) = "" || LANG(?rSkos) = "en") }}
    OPTIONAL {{ ?range rdfs:label ?rRdfs .
                FILTER(LANG(?rRdfs) = "" || LANG(?rRdfs) = "en") }}
    BIND(COALESCE(?rSkos, ?rRdfs,
         REPLACE(STR(?range), "^.*/|^.*#|^.*:", "", "")) AS ?rangeLabel)
  }}
}}
ORDER BY ?propLabel"""
        prop_result = await self._client.query(prop_sparql)
        prop_bindings = prop_result.get("results", {}).get("bindings", [])
        properties = []
        for pb in prop_bindings:
            properties.append({
                "iri": pb["prop"]["value"],
                "label": pb.get("propLabel", {}).get("value", ""),
                "range_label": pb.get("rangeLabel", {}).get("value", ""),
            })

        source = _property_source(class_iri)

        return {
            "iri": class_iri,
            "label": label,
            "comment": comment,
            "source": source,
            "parent_classes": parent_classes,
            "sibling_classes": siblings,
            "subclass_count": subclass_count,
            "instance_count": instance_count,
            "properties": properties,
        }

    async def search_classes(self, query: str, limit: int = 20) -> list[dict]:
        """Search classes by label across all ontology graphs.

        Case-insensitive CONTAINS filter on class labels.

        Args:
            query: Search string to match against class labels.
            limit: Maximum number of results.

        Returns:
            List of dicts with keys: iri, label.
        """
        if not query or not query.strip():
            return []

        graph_iris = await self.get_ontology_graph_iris()
        from_clauses = self._build_from_clauses(graph_iris)

        # Escape single quotes in query for SPARQL string literal
        safe_query = query.strip().replace("\\", "\\\\").replace("'", "\\'")

        sparql = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?class ?label
{from_clauses}
WHERE {{
  ?class a owl:Class .
  FILTER(isIRI(?class))
  OPTIONAL {{ ?class skos:prefLabel ?skosLabel .
              FILTER(LANG(?skosLabel) = "" || LANG(?skosLabel) = "en") }}
  OPTIONAL {{ ?class rdfs:label ?rdfsLabel .
              FILTER(LANG(?rdfsLabel) = "" || LANG(?rdfsLabel) = "en") }}
  BIND(COALESCE(?skosLabel, ?rdfsLabel,
       REPLACE(STR(?class), "^.*/|^.*#|^.*:", "", "")) AS ?label)
  FILTER(CONTAINS(LCASE(STR(?label)), LCASE('{safe_query}')))
}}
ORDER BY ?label
LIMIT {limit}"""

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        classes = []
        for b in bindings:
            iri = b["class"]["value"]
            label = b.get("label", {}).get(
                "value", iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
            )
            classes.append({"iri": iri, "label": label})

        logger.debug("TBox search '%s': %d results", query, len(classes))
        return classes

    async def _batch_has_subclasses(
        self, graph_iris: list[str], class_iris: list[str]
    ) -> dict[str, bool]:
        """Check which classes have subclasses, in a single SPARQL query.

        Uses VALUES + EXISTS pattern to batch the check efficiently.

        Returns:
            Dict mapping class IRI to True if it has at least one subclass.
        """
        if not class_iris:
            return {}

        from_clauses = self._build_from_clauses(graph_iris)
        values_clause = " ".join(f"(<{iri}>)" for iri in class_iris)

        sparql = f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?parent
{from_clauses}
WHERE {{
  VALUES (?parent) {{ {values_clause} }}
  FILTER EXISTS {{
    ?child rdfs:subClassOf ?parent .
    ?child a owl:Class .
    FILTER(isIRI(?child))
  }}
}}"""

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        has_children: dict[str, bool] = {}
        for b in bindings:
            has_children[b["parent"]["value"]] = True
        return has_children

    # ------------------------------------------------------------------
    # ABox query methods — instance counts and instance lists
    # ------------------------------------------------------------------

    async def get_type_counts(self) -> list[dict]:
        """Query instance counts per owl:Class across current + inferred graphs.

        Gets all class IRIs from ontology graphs, then counts distinct
        instances in current + inferred. Only returns types with count > 0.

        Returns:
            Sorted list of dicts: {iri, label, count}.
        """
        start = time.monotonic()
        graph_iris = await self.get_ontology_graph_iris()
        from_clauses = self._build_from_clauses(graph_iris)

        # Step 1: Get all owl:Class IRIs and their labels from ontology graphs
        class_sparql = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?class ?label
{from_clauses}
WHERE {{
  ?class a owl:Class .
  FILTER(isIRI(?class))
  OPTIONAL {{ ?class skos:prefLabel ?skosLabel .
              FILTER(LANG(?skosLabel) = "" || LANG(?skosLabel) = "en") }}
  OPTIONAL {{ ?class rdfs:label ?rdfsLabel .
              FILTER(LANG(?rdfsLabel) = "" || LANG(?rdfsLabel) = "en") }}
  BIND(COALESCE(?skosLabel, ?rdfsLabel,
       REPLACE(STR(?class), "^.*/|^.*#|^.*:", "", "")) AS ?label)
}}"""

        result = await self._client.query(class_sparql)
        bindings = result.get("results", {}).get("bindings", [])

        if not bindings:
            logger.debug("ABox: no classes found in ontology graphs")
            return []

        # Build lookup: iri -> label
        class_labels: dict[str, str] = {}
        for b in bindings:
            iri = b["class"]["value"]
            label = b.get("label", {}).get(
                "value", iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
            )
            class_labels[iri] = label

        # Step 2: Batch count instances across current + inferred
        values = " ".join(f"<{iri}>" for iri in class_labels)
        count_sparql = f"""SELECT ?type (COUNT(DISTINCT ?instance) AS ?count) WHERE {{
  {{
    GRAPH <urn:sempkm:current> {{ ?instance a ?type . }}
  }} UNION {{
    GRAPH <urn:sempkm:inferred> {{ ?instance a ?type . }}
  }}
  VALUES ?type {{ {values} }}
}}
GROUP BY ?type
HAVING (COUNT(DISTINCT ?instance) > 0)"""

        count_result = await self._client.query(count_sparql)
        count_bindings = count_result.get("results", {}).get("bindings", [])

        types = []
        for b in count_bindings:
            iri = b["type"]["value"]
            count = int(b["count"]["value"])
            types.append({
                "iri": iri,
                "label": class_labels.get(
                    iri, iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
                ),
                "count": count,
            })

        types.sort(key=lambda t: t["label"].lower())

        elapsed = time.monotonic() - start
        logger.debug(
            "ABox: %d types with instances (%.2fs)", len(types), elapsed
        )
        return types

    async def get_instances(
        self, class_iri: str, limit: int = 50
    ) -> list[dict]:
        """Query instances of a given class from current + inferred graphs.

        Resolves labels via COALESCE across common label predicates.

        Args:
            class_iri: IRI of the class to query instances of.
            limit: Maximum number of instances to return.

        Returns:
            Sorted list of dicts: {iri, label}.
        """
        start = time.monotonic()
        sparql = f"""PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT DISTINCT ?instance ?label WHERE {{
  {{
    GRAPH <urn:sempkm:current> {{ ?instance a <{class_iri}> . }}
  }} UNION {{
    GRAPH <urn:sempkm:inferred> {{ ?instance a <{class_iri}> . }}
  }}
  OPTIONAL {{
    GRAPH <urn:sempkm:current> {{
      OPTIONAL {{ ?instance dcterms:title ?t }}
      OPTIONAL {{ ?instance rdfs:label ?rl }}
      OPTIONAL {{ ?instance skos:prefLabel ?sl }}
      OPTIONAL {{ ?instance foaf:name ?fn }}
    }}
  }}
  BIND(COALESCE(?t, ?rl, ?sl, ?fn,
       REPLACE(STR(?instance), "^.*/", "")) AS ?label)
}}
ORDER BY ?label
LIMIT {limit}"""

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        instances = []
        for b in bindings:
            iri = b["instance"]["value"]
            label = b.get("label", {}).get("value", iri.rsplit("/", 1)[-1])
            instances.append({"iri": iri, "label": label})

        elapsed = time.monotonic() - start
        logger.debug(
            "ABox instances of %s: %d results (%.2fs)",
            class_iri,
            len(instances),
            elapsed,
        )
        return instances

    # ------------------------------------------------------------------
    # RBox query methods — property reference table
    # ------------------------------------------------------------------

    async def get_properties(self) -> dict[str, list[dict]]:
        """Query OWL properties across all ontology graphs.

        Returns object properties and datatype properties with domain/range
        labels resolved inline.

        Returns:
            Dict with keys 'object_properties' and 'datatype_properties',
            each a sorted list of dicts: {iri, label, domain_iri,
            domain_label, range_iri, range_label}.
        """
        start = time.monotonic()
        graph_iris = await self.get_ontology_graph_iris()
        from_clauses = self._build_from_clauses(graph_iris)

        sparql = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?prop ?propType ?label ?domain ?domainLabel ?range ?rangeLabel
{from_clauses}
WHERE {{
  ?prop a ?propType .
  VALUES ?propType {{
    owl:ObjectProperty
    owl:DatatypeProperty
  }}
  FILTER(isIRI(?prop))
  OPTIONAL {{ ?prop skos:prefLabel ?skosLabel .
              FILTER(LANG(?skosLabel) = "" || LANG(?skosLabel) = "en") }}
  OPTIONAL {{ ?prop rdfs:label ?rdfsLabel .
              FILTER(LANG(?rdfsLabel) = "" || LANG(?rdfsLabel) = "en") }}
  BIND(COALESCE(?skosLabel, ?rdfsLabel,
       REPLACE(STR(?prop), "^.*/|^.*#|^.*:", "", "")) AS ?label)
  OPTIONAL {{
    ?prop rdfs:domain ?domain .
    OPTIONAL {{ ?domain skos:prefLabel ?domSkos .
                FILTER(LANG(?domSkos) = "" || LANG(?domSkos) = "en") }}
    OPTIONAL {{ ?domain rdfs:label ?domRdfs .
                FILTER(LANG(?domRdfs) = "" || LANG(?domRdfs) = "en") }}
    BIND(COALESCE(?domSkos, ?domRdfs,
         REPLACE(STR(?domain), "^.*/|^.*#|^.*:", "", "")) AS ?domainLabel)
  }}
  OPTIONAL {{
    ?prop rdfs:range ?range .
    OPTIONAL {{ ?range skos:prefLabel ?rangeSkos .
                FILTER(LANG(?rangeSkos) = "" || LANG(?rangeSkos) = "en") }}
    OPTIONAL {{ ?range rdfs:label ?rangeRdfs .
                FILTER(LANG(?rangeRdfs) = "" || LANG(?rangeRdfs) = "en") }}
    BIND(COALESCE(?rangeSkos, ?rangeRdfs,
         REPLACE(STR(?range), "^.*/|^.*#|^.*:", "", "")) AS ?rangeLabel)
  }}
}}
ORDER BY ?propType ?label"""

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        object_props: list[dict] = []
        datatype_props: list[dict] = []

        for b in bindings:
            prop = {
                "iri": b["prop"]["value"],
                "label": b.get("label", {}).get(
                    "value",
                    b["prop"]["value"].rsplit("/", 1)[-1].rsplit("#", 1)[-1],
                ),
                "domain_iri": b.get("domain", {}).get("value", ""),
                "domain_label": b.get("domainLabel", {}).get("value", ""),
                "range_iri": b.get("range", {}).get("value", ""),
                "range_label": b.get("rangeLabel", {}).get("value", ""),
                "source": _property_source(b["prop"]["value"]),
            }
            if "ObjectProperty" in b["propType"]["value"]:
                object_props.append(prop)
            else:
                datatype_props.append(prop)

        elapsed = time.monotonic() - start
        logger.debug(
            "RBox: %d object properties, %d datatype properties (%.2fs)",
            len(object_props),
            len(datatype_props),
            elapsed,
        )
        return {
            "object_properties": object_props,
            "datatype_properties": datatype_props,
        }

    # ------------------------------------------------------------------
    # User-defined class creation and deletion
    # ------------------------------------------------------------------

    @staticmethod
    def _mint_class_iris(name: str) -> tuple[str, str]:
        """Mint a class IRI and shape IRI with UUID suffix for collision prevention.

        Slugifies the name (alphanumeric only) and appends 8 hex chars from uuid4.

        Returns:
            Tuple of (class_iri, shape_iri).
        """
        slug = re.sub(r"[^A-Za-z0-9]+", "", name.strip())
        if not slug:
            slug = "Class"
        hex_suffix = uuid.uuid4().hex[:8]
        class_iri = f"{USER_TYPES_GRAPH}:{slug}-{hex_suffix}"
        shape_iri = f"{USER_TYPES_GRAPH}:{slug}Shape-{hex_suffix}"
        return class_iri, shape_iri

    @staticmethod
    def _validate_class_input(
        name: str,
        parent_iri: str,
        properties: list[dict],
    ) -> None:
        """Validate inputs for class creation.

        Raises ValueError with a descriptive message on invalid input.
        """
        if not name or not name.strip():
            raise ValueError("Class name must not be empty")

        if not (parent_iri.startswith("http") or parent_iri.startswith("urn:")):
            raise ValueError(
                f"Parent IRI must start with 'http' or 'urn:': {parent_iri}"
            )

        for i, prop in enumerate(properties):
            prop_name = prop.get("name", "")
            if not prop_name or not prop_name.strip():
                raise ValueError(f"Property name at index {i} must not be empty")

            pred_iri = prop.get("predicate_iri", "")
            if not (pred_iri.startswith("http") or pred_iri.startswith("urn:")):
                raise ValueError(
                    f"Property predicate IRI at index {i} is invalid: {pred_iri}"
                )

            dt_iri = prop.get("datatype_iri", "")
            if dt_iri and dt_iri not in ALLOWED_DATATYPES:
                raise ValueError(
                    f"Datatype '{dt_iri}' at index {i} is not in the allowed list. "
                    f"Allowed: {sorted(ALLOWED_DATATYPES)}"
                )

    @staticmethod
    def _generate_class_triples(
        class_iri: str,
        name: str,
        parent_iri: str,
        icon_name: str | None = None,
        icon_color: str | None = None,
    ) -> list[tuple]:
        """Generate OWL class triples for a user-defined class.

        Produces:
        - <classIRI> a owl:Class
        - <classIRI> rdfs:label "name"
        - <classIRI> rdfs:subClassOf <parent>
        - Optionally: sempkm:typeIcon, sempkm:typeColor
        """
        class_uri = URIRef(class_iri)
        triples: list[tuple] = [
            (class_uri, RDF.type, OWL.Class),
            (class_uri, RDFS.label, Literal(name)),
            (class_uri, RDFS.subClassOf, URIRef(parent_iri)),
        ]

        if icon_name:
            triples.append((class_uri, SEMPKM_TYPE_ICON, Literal(icon_name)))
        if icon_color:
            triples.append((class_uri, SEMPKM_TYPE_COLOR, Literal(icon_color)))

        return triples

    @staticmethod
    def _generate_shape_triples(
        class_iri: str,
        shape_iri: str,
        name: str,
        properties: list[dict],
    ) -> list[tuple]:
        """Generate SHACL NodeShape triples for a user-defined class.

        Produces:
        - <shapeIRI> a sh:NodeShape
        - <shapeIRI> sh:targetClass <classIRI>
        - <shapeIRI> rdfs:label "{name} Shape"
        - For each property: blank-node sh:property with sh:path, sh:name,
          sh:datatype, sh:order
        """
        shape_uri = URIRef(shape_iri)
        class_uri = URIRef(class_iri)

        triples: list[tuple] = [
            (shape_uri, RDF.type, SH.NodeShape),
            (shape_uri, SH.targetClass, class_uri),
            (shape_uri, RDFS.label, Literal(f"{name} Shape")),
        ]

        for i, prop in enumerate(properties):
            bnode = BNode()
            triples.append((shape_uri, SH.property, bnode))
            triples.append((bnode, SH.path, URIRef(prop["predicate_iri"])))
            triples.append((bnode, SH.name, Literal(prop["name"])))
            triples.append(
                (bnode, SH.datatype, URIRef(prop["datatype_iri"]))
            )
            triples.append(
                (bnode, SH.order, Literal(i + 1, datatype=XSD.integer))
            )

        return triples

    @staticmethod
    def _build_delete_class_sparql(class_iri: str) -> str:
        """Build SPARQL DELETE WHERE to remove all class triples.

        Removes all triples with the class IRI as subject in the
        user-types graph.
        """
        return (
            f"DELETE WHERE {{ "
            f"GRAPH <{USER_TYPES_GRAPH}> {{ <{class_iri}> ?p ?o . }} "
            f"}}"
        )

    @staticmethod
    def _build_delete_shape_sparql(shape_iri: str) -> tuple[str, str]:
        """Build SPARQL to remove shape triples and their blank-node properties.

        Returns two separate SPARQL UPDATE statements (executed sequentially):
        1. Delete blank-node property shape triples (sh:property → bnode → triples)
        2. Delete the shape node itself
        """
        # Step 1: Delete blank-node property triples reachable via sh:property
        delete_bnodes = (
            f"DELETE WHERE {{ "
            f"GRAPH <{USER_TYPES_GRAPH}> {{ "
            f"<{shape_iri}> <{SH.property}> ?bn . ?bn ?pp ?oo . "
            f"}} "
            f"}}"
        )
        # Step 2: Delete the shape node's own triples
        delete_shape = (
            f"DELETE WHERE {{ "
            f"GRAPH <{USER_TYPES_GRAPH}> {{ "
            f"<{shape_iri}> ?p ?o . "
            f"}} "
            f"}}"
        )
        return (delete_bnodes, delete_shape)

    async def create_class(
        self,
        name: str,
        parent_iri: str,
        properties: list[dict],
        icon_name: str | None = None,
        icon_color: str | None = None,
    ) -> dict:
        """Create a user-defined class with OWL + SHACL triples.

        Validates inputs, mints IRIs, generates triples, and writes them
        to the user-types named graph via batched INSERT DATA.

        Args:
            name: Human-readable class name.
            parent_iri: IRI of the parent class.
            properties: List of property defs, each with name, predicate_iri,
                        datatype_iri.
            icon_name: Optional Lucide icon name.
            icon_color: Optional hex color string.

        Returns:
            Dict with class_iri, shape_iri, triple_count, property_count.

        Raises:
            ValueError: On invalid input.
        """
        self._validate_class_input(name, parent_iri, properties)

        class_iri, shape_iri = self._mint_class_iris(name)

        class_triples = self._generate_class_triples(
            class_iri=class_iri,
            name=name,
            parent_iri=parent_iri,
            icon_name=icon_name,
            icon_color=icon_color,
        )
        shape_triples = self._generate_shape_triples(
            class_iri=class_iri,
            shape_iri=shape_iri,
            name=name,
            properties=properties,
        )

        all_triples = class_triples + shape_triples
        sparql = _build_insert_data_sparql(USER_TYPES_GRAPH, all_triples)
        await self._client.update(sparql)

        logger.info(
            "Created class %s: %d triples, %d properties",
            class_iri,
            len(all_triples),
            len(properties),
        )

        return {
            "class_iri": class_iri,
            "shape_iri": shape_iri,
            "triple_count": len(all_triples),
            "property_count": len(properties),
        }

    async def delete_class(self, class_iri: str) -> dict:
        """Delete a user-defined class and its shape from the triplestore.

        Removes all triples for the class and its shape from the
        user-types named graph.

        Args:
            class_iri: IRI of the class to delete.

        Returns:
            Dict with class_iri and status.
        """
        # Derive shape IRI from class IRI (replace the slug with slugShape)
        # Convention: class = ...:{Slug}-{hex}, shape = ...:{Slug}Shape-{hex}
        parts = class_iri.rsplit("-", 1)
        if len(parts) == 2:
            shape_iri = f"{parts[0]}Shape-{parts[1]}"
        else:
            shape_iri = f"{class_iri}Shape"

        # Delete shape triples (including blank-node property shapes)
        bn_sparql, shape_sparql = self._build_delete_shape_sparql(shape_iri)
        await self._client.update(bn_sparql)
        await self._client.update(shape_sparql)

        # Delete class triples
        class_sparql = self._build_delete_class_sparql(class_iri)
        await self._client.update(class_sparql)

        logger.info("Deleted class %s and shape %s", class_iri, shape_iri)

        return {
            "class_iri": class_iri,
            "shape_iri": shape_iri,
            "status": "deleted",
        }
