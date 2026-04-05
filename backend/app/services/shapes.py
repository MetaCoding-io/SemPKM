"""SHACL shape extraction service for form metadata generation.

Queries installed model shapes graphs from the triplestore via SPARQL CONSTRUCT,
parses the resulting rdflib Graph to extract sh:NodeShape and sh:PropertyShape
metadata, and returns structured Python dataclasses suitable for Jinja2 form
template rendering.

Uses rdflib Python API for graph traversal (not complex SPARQL) per Research
Pitfall 2: sh:in RDF lists are traversed via rdflib.Collection, not SPARQL
property paths.
"""

import logging
from dataclasses import dataclass, field

from cachetools import TTLCache
from rdflib import Graph, URIRef, Literal
from rdflib.collection import Collection
from rdflib.namespace import RDF, RDFS, SH, XSD

from app.models.registry import MODELS_GRAPH, SEMPKM_NS
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

SEMPKM_EDIT_HELPTEXT = URIRef("urn:sempkm:editHelpText")


@dataclass
class PropertyShape:
    """Metadata for a single SHACL property shape (form field)."""

    path: str
    name: str
    datatype: str | None = None
    target_class: str | None = None
    order: float = 0.0
    group: str | None = None
    min_count: int = 0
    max_count: int | None = None
    in_values: list[str] = field(default_factory=list)
    default_value: str | None = None
    description: str | None = None
    helptext: str | None = None


@dataclass
class PropertyGroup:
    """Metadata for a SHACL property group (form section)."""

    iri: str
    label: str
    order: float = 0.0


@dataclass
class NodeShapeForm:
    """Complete form metadata for a SHACL NodeShape (one object type)."""

    shape_iri: str
    target_class: str
    label: str
    groups: list[PropertyGroup] = field(default_factory=list)
    properties: list[PropertyShape] = field(default_factory=list)
    helptext: str | None = None


class ShapesService:
    """Extract SHACL shape metadata from installed model shapes graphs.

    Uses SPARQL CONSTRUCT to fetch the complete shapes graph into an rdflib
    Graph, then traverses with the Python API to extract NodeShape forms
    with all property shape attributes needed for form generation.
    """

    def __init__(self, client: TriplestoreClient, ttl: int = 600) -> None:
        self._client = client
        self._shapes_graph_cache: TTLCache[str, Graph] = TTLCache(
            maxsize=1, ttl=ttl
        )
        self._form_cache: TTLCache[str, NodeShapeForm | None] = TTLCache(
            maxsize=64, ttl=ttl
        )

    def clear_cache(self) -> None:
        """Clear both the shapes graph and per-type form caches.

        Call after model install/uninstall to force a fresh fetch on
        the next request.  In normal operation the TTL (default 600s)
        handles staleness automatically.
        """
        self._shapes_graph_cache.clear()
        self._form_cache.clear()
        logger.debug("shapes caches cleared")

    async def _fetch_shapes_graph(self) -> Graph:
        """Fetch the combined shapes graph from all installed models.

        Uses a TTL cache (default 600s) to avoid repeated SPARQL
        round-trips.  Shapes only change when a Mental Model is
        installed/uninstalled — well within the TTL window.

        Queries the model registry for installed model IDs, then builds
        a SPARQL CONSTRUCT with FROM clauses for each model's shapes
        named graph. Returns the merged rdflib Graph.
        """
        _CACHE_KEY = "shapes"

        cached = self._shapes_graph_cache.get(_CACHE_KEY)
        if cached is not None:
            logger.debug("shapes graph cache HIT")
            return cached

        logger.debug("shapes graph cache MISS — fetching from triplestore")

        # 1. List installed model IDs
        sparql = f"""SELECT ?modelId WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId .
  }}
}}"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        if not bindings:
            logger.info("No installed models found for shapes extraction")
            graph = Graph()
            self._shapes_graph_cache[_CACHE_KEY] = graph
            return graph

        # 2. Build CONSTRUCT with FROM clauses for each model's shapes graph
        #    + user-types graph for user-created class shapes
        from_clauses = []
        for b in bindings:
            model_id = b["modelId"]["value"]
            shapes_iri = f"urn:sempkm:model:{model_id}:shapes"
            from_clauses.append(f"FROM <{shapes_iri}>")
        from_clauses.append("FROM <urn:sempkm:user-types>")

        from_str = "\n".join(from_clauses)
        construct_sparql = f"""CONSTRUCT {{ ?s ?p ?o }}
{from_str}
WHERE {{ ?s ?p ?o }}"""

        turtle_bytes = await self._client.construct(construct_sparql)
        shapes_graph = Graph()
        if turtle_bytes.strip():
            shapes_graph.parse(data=turtle_bytes, format="turtle")

        logger.info(
            "Fetched %d shapes triples from %d model(s)",
            len(shapes_graph),
            len(bindings),
        )
        self._shapes_graph_cache[_CACHE_KEY] = shapes_graph
        return shapes_graph

    def _extract_node_shape(
        self, graph: Graph, shape_node: URIRef
    ) -> NodeShapeForm | None:
        """Extract a single NodeShapeForm from the shapes graph.

        Traverses the graph to find the targetClass, label, property shapes,
        and property groups for the given sh:NodeShape node.
        """
        # Get target class
        target_classes = list(graph.objects(shape_node, SH.targetClass))
        if not target_classes:
            return None
        target_class = str(target_classes[0])

        # Get label: sh:name first, then rdfs:label, then local name
        label = self._resolve_label(graph, shape_node)

        # Extract property groups referenced by this shape's properties
        groups_map: dict[str, PropertyGroup] = {}

        # Extract property shapes
        properties: list[PropertyShape] = []
        for prop_node in graph.objects(shape_node, SH.property):
            prop_shape = self._extract_property_shape(graph, prop_node)
            if prop_shape is not None:
                properties.append(prop_shape)

                # Resolve property group if referenced
                if prop_shape.group and prop_shape.group not in groups_map:
                    group = self._extract_property_group(
                        graph, URIRef(prop_shape.group)
                    )
                    if group is not None:
                        groups_map[group.iri] = group

        # Sort properties: by order ascending, required (minCount > 0) before optional
        properties.sort(key=lambda p: (p.order, -p.min_count))

        # Sort groups by order
        groups = sorted(groups_map.values(), key=lambda g: g.order)

        # sempkm:editHelpText (form-level)
        helptexts = list(graph.objects(shape_node, SEMPKM_EDIT_HELPTEXT))
        helptext = str(helptexts[0]) if helptexts else None

        return NodeShapeForm(
            shape_iri=str(shape_node),
            target_class=target_class,
            label=label,
            groups=groups,
            properties=properties,
            helptext=helptext,
        )

    def _extract_property_shape(
        self, graph: Graph, prop_node
    ) -> PropertyShape | None:
        """Extract a PropertyShape from a property shape node."""
        # sh:path is required
        paths = list(graph.objects(prop_node, SH.path))
        if not paths:
            return None
        path = str(paths[0])

        # sh:name for human-readable label
        name = self._resolve_property_name(graph, prop_node, paths[0])

        # sh:datatype
        datatypes = list(graph.objects(prop_node, SH.datatype))
        datatype = str(datatypes[0]) if datatypes else None

        # sh:class (target class for object references)
        classes = list(graph.objects(prop_node, SH["class"]))
        target_class = str(classes[0]) if classes else None

        # sh:order
        orders = list(graph.objects(prop_node, SH.order))
        order = float(orders[0]) if orders else 0.0

        # sh:group
        groups = list(graph.objects(prop_node, SH.group))
        group = str(groups[0]) if groups else None

        # sh:minCount
        min_counts = list(graph.objects(prop_node, SH.minCount))
        min_count = int(min_counts[0]) if min_counts else 0

        # sh:maxCount
        max_counts = list(graph.objects(prop_node, SH.maxCount))
        max_count = int(max_counts[0]) if max_counts else None

        # sh:in (RDF list) -- use rdflib Collection to traverse
        in_values = self._extract_in_values(graph, prop_node)

        # sh:defaultValue
        defaults = list(graph.objects(prop_node, SH.defaultValue))
        default_value = str(defaults[0]) if defaults else None

        # sh:description
        descriptions = list(graph.objects(prop_node, SH.description))
        description = str(descriptions[0]) if descriptions else None

        # sempkm:editHelpText
        helptexts = list(graph.objects(prop_node, SEMPKM_EDIT_HELPTEXT))
        helptext = str(helptexts[0]) if helptexts else None

        return PropertyShape(
            path=path,
            name=name,
            datatype=datatype,
            target_class=target_class,
            order=order,
            group=group,
            min_count=min_count,
            max_count=max_count,
            in_values=in_values,
            default_value=default_value,
            description=description,
            helptext=helptext,
        )

    def _extract_in_values(self, graph: Graph, prop_node) -> list[str]:
        """Extract sh:in list values using rdflib Collection.

        sh:in uses an RDF list (rdf:first/rdf:rest chain). rdflib's
        Collection class handles traversal correctly per Research Pitfall 2.
        """
        in_list_heads = list(graph.objects(prop_node, SH["in"]))
        if not in_list_heads:
            return []
        try:
            collection = Collection(graph, in_list_heads[0])
            return [str(item) for item in collection]
        except Exception:
            logger.warning(
                "Failed to extract sh:in values for %s", prop_node, exc_info=True
            )
            return []

    def _extract_property_group(
        self, graph: Graph, group_node: URIRef
    ) -> PropertyGroup | None:
        """Extract a PropertyGroup from a group node."""
        label = self._resolve_label(graph, group_node)
        orders = list(graph.objects(group_node, SH.order))
        order = float(orders[0]) if orders else 0.0
        return PropertyGroup(iri=str(group_node), label=label, order=order)

    def _resolve_label(self, graph: Graph, node) -> str:
        """Resolve a human-readable label for a node.

        Precedence: sh:name > rdfs:label > local name from IRI.
        """
        # sh:name
        names = list(graph.objects(node, SH.name))
        if names:
            return str(names[0])

        # rdfs:label
        labels = list(graph.objects(node, RDFS.label))
        if labels:
            return str(labels[0])

        # Fall back to local name extraction from IRI
        return self._local_name(str(node))

    def _resolve_property_name(self, graph: Graph, prop_node, path_node) -> str:
        """Resolve a human-readable name for a property shape.

        Precedence: sh:name on the property shape > rdfs:label on the
        sh:path target > local name from the path IRI.
        """
        # sh:name on the property shape
        names = list(graph.objects(prop_node, SH.name))
        if names:
            return str(names[0])

        # rdfs:label on the sh:path target
        labels = list(graph.objects(path_node, RDFS.label))
        if labels:
            return str(labels[0])

        # Fall back to local name from the path IRI
        return self._local_name(str(path_node))

    @staticmethod
    def _local_name(iri: str) -> str:
        """Extract the local name from an IRI.

        Splits on '#' then '/' and returns the last segment.
        """
        if "#" in iri:
            return iri.rsplit("#", 1)[-1]
        if "/" in iri:
            return iri.rsplit("/", 1)[-1]
        return iri

    async def get_node_shapes(self) -> list[NodeShapeForm]:
        """Query all NodeShapes from installed model shapes graphs.

        Fetches the complete shapes graph via SPARQL CONSTRUCT, then
        traverses it with rdflib to extract NodeShapeForm metadata
        for each sh:NodeShape with sh:targetClass.

        Returns:
            List of NodeShapeForm dataclasses, one per shape.
        """
        graph = await self._fetch_shapes_graph()
        if len(graph) == 0:
            return []

        forms: list[NodeShapeForm] = []
        for shape_node in graph.subjects(RDF.type, SH.NodeShape):
            if not isinstance(shape_node, URIRef):
                continue
            form = self._extract_node_shape(graph, shape_node)
            if form is not None:
                forms.append(form)

        logger.info("Extracted %d node shape forms", len(forms))
        return forms

    async def get_form_for_type(self, type_iri: str) -> NodeShapeForm | None:
        """Get form metadata for a specific target class.

        Results are cached per type_iri with the same TTL as the shapes
        graph cache.  Cache misses fetch all shapes and find the one
        whose sh:targetClass matches the given type IRI.

        If the shape has no properties (e.g. a custom class with a bare
        SHACL shape), injects default Title and Description fields so
        the create form is always usable.

        Args:
            type_iri: The target class IRI to find a form for.

        Returns:
            NodeShapeForm for the type, or None if not found.
        """
        cached = self._form_cache.get(type_iri)
        if cached is not None:
            logger.debug("form cache HIT for %s", type_iri)
            return cached

        logger.debug("form cache MISS for %s", type_iri)

        forms = await self.get_node_shapes()
        for form in forms:
            if form.target_class == type_iri:
                if not form.properties:
                    form.properties = self._default_properties()
                self._form_cache[type_iri] = form
                return form

        # Cache the miss too so we don't re-query for unknown types
        # Use a sentinel: store None is not possible with TTLCache get(),
        # so we don't cache misses — they'll re-query each time.
        return None

    @staticmethod
    def _default_properties() -> list[PropertyShape]:
        """Return minimal Title + Description fields for bare shapes."""
        return [
            PropertyShape(
                path="http://purl.org/dc/terms/title",
                name="Title",
                description="The display name for this object.",
                datatype="http://www.w3.org/2001/XMLSchema#string",
                order=1.0,
                min_count=1,
                max_count=1,
            ),
            PropertyShape(
                path="http://www.w3.org/2000/01/rdf-schema#comment",
                name="Description",
                description="A short description of what this object is about.",
                datatype="http://www.w3.org/2001/XMLSchema#string",
                order=2.0,
                min_count=0,
                max_count=1,
            ),
        ]

    async def get_labels_for_predicates(
        self, predicate_iris: list[str]
    ) -> dict[str, str]:
        """Resolve human-readable labels for predicate IRIs via SHACL shapes.

        Iterates all ``sh:PropertyShape`` nodes in the shapes graph. For each
        whose ``sh:path`` matches a requested IRI, extracts ``sh:name`` first,
        then ``rdfs:label`` on the path node, then falls back to the IRI local
        name.

        This is the correct resolution path for **vocabulary terms** like
        ``dcterms:title`` — they live in shapes/ontology graphs, not in
        ``urn:sempkm:current``, so ``LabelService.resolve_batch()`` will not
        find them.

        Returns:
            ``{predicate_iri: human_label}`` for every requested IRI that
            could be resolved to something other than the raw IRI.
        """
        if not predicate_iris:
            return {}
        try:
            graph = await self._fetch_shapes_graph()
            if len(graph) == 0:
                return {}

            wanted = set(predicate_iris)
            labels: dict[str, str] = {}

            # Collect all property shape nodes: explicitly typed AND inline
            # via sh:property (blank nodes may lack rdf:type sh:PropertyShape)
            prop_nodes: set = set(graph.subjects(RDF.type, SH.PropertyShape))
            for obj in graph.objects(predicate=SH.property):
                prop_nodes.add(obj)

            for prop_node in prop_nodes:
                paths = list(graph.objects(prop_node, SH.path))
                if not paths:
                    continue
                path_iri = str(paths[0])
                if path_iri not in wanted or path_iri in labels:
                    continue

                label = self._resolve_property_name(graph, prop_node, paths[0])
                # Only include if we resolved something beyond the raw IRI
                if label and label != path_iri:
                    labels[path_iri] = label

            return labels
        except Exception:
            logger.warning(
                "Failed to resolve predicate labels from shapes graph",
                exc_info=True,
            )
            return {}

    async def get_helptext_for_predicates(
        self, predicate_iris: list[str]
    ) -> dict[str, str]:
        """Extract helptext for predicate IRIs from SHACL property shapes.

        For each ``sh:PropertyShape`` whose ``sh:path`` matches a requested
        IRI, returns ``sempkm:editHelpText`` (preferred) or ``sh:description``
        as the helptext string.

        Returns:
            ``{predicate_iri: helptext}`` — only includes predicates that
            have helptext in the shapes graph.
        """
        if not predicate_iris:
            return {}
        try:
            graph = await self._fetch_shapes_graph()
            if len(graph) == 0:
                return {}

            wanted = set(predicate_iris)
            helptext_map: dict[str, str] = {}

            # Collect all property shape nodes: explicitly typed AND inline
            # via sh:property (blank nodes may lack rdf:type sh:PropertyShape)
            prop_nodes: set = set(graph.subjects(RDF.type, SH.PropertyShape))
            for obj in graph.objects(predicate=SH.property):
                prop_nodes.add(obj)

            for prop_node in prop_nodes:
                paths = list(graph.objects(prop_node, SH.path))
                if not paths:
                    continue
                path_iri = str(paths[0])
                if path_iri not in wanted or path_iri in helptext_map:
                    continue

                # Prefer sempkm:editHelpText, fall back to sh:description
                helptexts = list(
                    graph.objects(prop_node, SEMPKM_EDIT_HELPTEXT)
                )
                if helptexts:
                    helptext_map[path_iri] = str(helptexts[0])
                    continue
                descriptions = list(
                    graph.objects(prop_node, SH.description)
                )
                if descriptions:
                    helptext_map[path_iri] = str(descriptions[0])

            return helptext_map
        except Exception:
            logger.warning(
                "Failed to resolve predicate helptext from shapes graph",
                exc_info=True,
            )
            return {}

    async def get_types(self, exclude_iris: set[str] | None = None) -> list[dict]:
        """Return list of available types for the type picker.

        Each entry contains the targetClass IRI and a human-readable label.

        Args:
            exclude_iris: Optional set of type IRIs to omit from results
                (used to hide internal/bookkeeping types from the browser).

        Returns:
            List of dicts with 'iri' and 'label' keys.
        """
        forms = await self.get_node_shapes()
        types = [
            {"iri": form.target_class, "label": form.label}
            for form in forms
        ]
        if exclude_iris:
            types = [t for t in types if t["iri"] not in exclude_iris]
        return types
