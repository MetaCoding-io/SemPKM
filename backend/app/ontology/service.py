"""OntologyService for loading and managing upper ontologies in the triplestore.

Handles batched INSERT DATA loading of gist (and future ontologies) with
idempotent version checking. Gist is loaded into its own named graph at
startup so TBox/ABox/RBox queries can traverse cross-graph class hierarchies.

TBox query methods (get_root_classes, get_subclasses) use FROM clause
aggregation across gist + all installed model ontology graphs + user-types
to present a unified class hierarchy.
"""

import logging
import time
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef

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
