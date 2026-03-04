"""Model registry SPARQL operations for Mental Model management.

Provides functions for registering, unregistering, listing, and
querying installed Mental Models in the triplestore. Model metadata
is stored as triples in a dedicated named graph (urn:sempkm:models).
Model artifact data is stored in model-specific named graphs.
"""

from dataclasses import dataclass

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, XSD

from app.models.manifest import ManifestSchema
from app.triplestore.client import TriplestoreClient

# Named graph for model registry metadata
MODELS_GRAPH = "urn:sempkm:models"

# SemPKM vocabulary namespace
SEMPKM_NS = "urn:sempkm:"


@dataclass
class ModelGraphs:
    """Named graph IRIs for a model's artifacts.

    Each installed model's data is stored in separate named graphs
    organized by artifact type, enabling selective querying and
    clean removal.
    """

    model_id: str

    @property
    def ontology(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:ontology"

    @property
    def shapes(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:shapes"

    @property
    def views(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:views"

    @property
    def seed(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:seed"

    @property
    def rules(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:rules"

    @property
    def all_graphs(self) -> list[str]:
        return [self.ontology, self.shapes, self.views, self.seed, self.rules]


@dataclass
class InstalledModel:
    """Metadata for an installed Mental Model."""

    model_id: str
    version: str
    name: str
    description: str
    namespace: str
    installed_at: str


def _rdf_term_to_sparql(term) -> str:
    """Serialize an rdflib term to SPARQL syntax.

    Handles URIRef, Literal (with datatype/language), and BNode.
    Pattern copied from app/services/validation.py for consistency.
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


async def register_model(
    client: TriplestoreClient,
    manifest: ManifestSchema,
    installed_at: str,
) -> None:
    """Register a model in the model registry graph.

    Writes model metadata triples into GRAPH <urn:sempkm:models>.

    Args:
        client: The triplestore client.
        manifest: The validated manifest schema.
        installed_at: ISO 8601 timestamp of installation.
    """
    model_iri = f"urn:sempkm:model:{manifest.modelId}"

    # Escape description for SPARQL literal
    desc_escaped = (
        manifest.description
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )

    sparql = f"""INSERT DATA {{
  GRAPH <{MODELS_GRAPH}> {{
    <{model_iri}> a <{SEMPKM_NS}MentalModel> ;
        <{SEMPKM_NS}modelId> "{manifest.modelId}" ;
        <{SEMPKM_NS}version> "{manifest.version}" ;
        <http://purl.org/dc/terms/title> "{manifest.name}" ;
        <http://purl.org/dc/terms/description> "{desc_escaped}" ;
        <{SEMPKM_NS}namespace> "{manifest.namespace}" ;
        <{SEMPKM_NS}installedAt> "{installed_at}"^^<{XSD.dateTime}> .
  }}
}}"""
    await client.update(sparql)


async def unregister_model(
    client: TriplestoreClient, model_id: str
) -> None:
    """Remove a model's registry entry from the models graph.

    Args:
        client: The triplestore client.
        model_id: The model identifier to remove.
    """
    model_iri = f"urn:sempkm:model:{model_id}"
    sparql = f"""DELETE WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    <{model_iri}> ?p ?o .
  }}
}}"""
    await client.update(sparql)


async def list_models(
    client: TriplestoreClient,
) -> list[InstalledModel]:
    """Query the model registry for all installed models.

    Args:
        client: The triplestore client.

    Returns:
        List of InstalledModel dataclasses with metadata.
    """
    sparql = f"""SELECT ?model ?modelId ?version ?name ?description ?namespace ?installedAt
WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId ;
           <{SEMPKM_NS}version> ?version ;
           <http://purl.org/dc/terms/title> ?name .
    OPTIONAL {{ ?model <http://purl.org/dc/terms/description> ?description }}
    OPTIONAL {{ ?model <{SEMPKM_NS}namespace> ?namespace }}
    OPTIONAL {{ ?model <{SEMPKM_NS}installedAt> ?installedAt }}
  }}
}}
ORDER BY ?name"""
    result = await client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    return [
        InstalledModel(
            model_id=b["modelId"]["value"],
            version=b["version"]["value"],
            name=b["name"]["value"],
            description=b.get("description", {}).get("value", ""),
            namespace=b.get("namespace", {}).get("value", ""),
            installed_at=b.get("installedAt", {}).get("value", ""),
        )
        for b in bindings
    ]


async def is_model_installed(
    client: TriplestoreClient, model_id: str
) -> bool:
    """Check if a model is already installed.

    Args:
        client: The triplestore client.
        model_id: The model identifier to check.

    Returns:
        True if the model exists in the registry.
    """
    model_iri = f"urn:sempkm:model:{model_id}"
    sparql = f"""ASK {{
  GRAPH <{MODELS_GRAPH}> {{
    <{model_iri}> a <{SEMPKM_NS}MentalModel> .
  }}
}}"""
    result = await client.query(sparql)
    return result.get("boolean", False)


async def write_graph_to_named_graph(
    client: TriplestoreClient,
    graph: Graph,
    named_graph_iri: str,
) -> None:
    """Write an rdflib Graph into a named graph via SPARQL INSERT DATA.

    Serializes triple-by-triple using _rdf_term_to_sparql for proper
    escaping (not N-Triples format, per Research Pitfall 2).

    Args:
        client: The triplestore client.
        graph: The rdflib Graph to write.
        named_graph_iri: The target named graph IRI.
    """
    if len(graph) == 0:
        return

    triple_lines = []
    for s, p, o in graph:
        triple_lines.append(
            f"    {_rdf_term_to_sparql(s)} {_rdf_term_to_sparql(p)} {_rdf_term_to_sparql(o)} ."
        )
    triples_str = "\n".join(triple_lines)

    sparql = f"""INSERT DATA {{
  GRAPH <{named_graph_iri}> {{
{triples_str}
  }}
}}"""
    await client.update(sparql)


async def clear_model_graphs(
    client: TriplestoreClient, model_id: str
) -> None:
    """Clear all named graphs for a model.

    Executes CLEAR SILENT GRAPH for each of the model's artifact
    named graphs (ontology, shapes, views, seed).

    Args:
        client: The triplestore client.
        model_id: The model identifier whose graphs to clear.
    """
    graphs = ModelGraphs(model_id)
    for graph_iri in graphs.all_graphs:
        await client.update(f"CLEAR SILENT GRAPH <{graph_iri}>")


async def clear_inferred_graph(
    client: TriplestoreClient,
) -> None:
    """Drop the urn:sempkm:inferred named graph.

    Called during model uninstall to remove all inferred triples.
    Inferred triples may reference multiple models' ontology axioms,
    so selective removal is not feasible. Full recompute after uninstall
    (user clicks Refresh) rebuilds the correct state from remaining models.

    Args:
        client: The triplestore client.
    """
    try:
        await client.update("CLEAR GRAPH <urn:sempkm:inferred>")
    except Exception:
        # Graph may not exist; that's fine
        pass


async def check_user_data_exists(
    client: TriplestoreClient,
    model_namespace: str,
    ontology: Graph,
) -> list[str]:
    """Check if user data exists for types defined by a model.

    For each OWL class in the ontology within the model namespace,
    executes an ASK query against urn:sempkm:current to check if
    any instances exist.

    Args:
        client: The triplestore client.
        model_namespace: The model's namespace prefix.
        ontology: The model's ontology graph.

    Returns:
        List of class IRIs that have user data.
    """
    OWL_CLASS = URIRef("http://www.w3.org/2002/07/owl#Class")
    types_with_data: list[str] = []

    for cls in ontology.subjects(RDF.type, OWL_CLASS):
        cls_str = str(cls)
        if not cls_str.startswith(model_namespace):
            continue

        sparql = f"""ASK {{
  GRAPH <urn:sempkm:current> {{
    ?s a <{cls_str}> .
  }}
}}"""
        result = await client.query(sparql)
        if result.get("boolean", False):
            types_with_data.append(cls_str)

    return types_with_data
