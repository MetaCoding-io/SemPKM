"""Selective entailment classification for OWL 2 RL inferred triples.

Classifies each inferred triple by which OWL 2 RL entailment type
produced it, using heuristics based on the ontology axioms. This enables
per-type filtering so users can enable/disable specific entailment
categories (e.g., only owl:inverseOf, not rdfs:domain/rdfs:range).
"""

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS
from rdflib.term import Node

# Supported entailment type labels
ENTAILMENT_TYPES = [
    "owl:inverseOf",
    "rdfs:subClassOf",
    "rdfs:subPropertyOf",
    "owl:TransitiveProperty",
    "rdfs:domain/rdfs:range",
    "sh:rule",
]

# Mapping from manifest-style keys to entailment type labels
MANIFEST_KEY_TO_TYPE = {
    "owl_inverseOf": "owl:inverseOf",
    "rdfs_subClassOf": "rdfs:subClassOf",
    "rdfs_subPropertyOf": "rdfs:subPropertyOf",
    "owl_TransitiveProperty": "owl:TransitiveProperty",
    "rdfs_domain_range": "rdfs:domain/rdfs:range",
    "shacl_rules": "sh:rule",
}

TYPE_TO_MANIFEST_KEY = {v: k for k, v in MANIFEST_KEY_TO_TYPE.items()}


def classify_entailment(
    s: Node, p: Node, o: Node, ontology: Graph
) -> str | None:
    """Classify an inferred triple by which entailment type produced it.

    Uses heuristics based on ontology axioms to determine which OWL 2 RL
    rule is responsible for the triple. Returns None for unclassifiable
    triples (which should be filtered out).

    The classification order matters: more specific checks come first.

    Args:
        s: Subject of the inferred triple.
        p: Predicate of the inferred triple.
        o: Object of the inferred triple.
        ontology: The ontology graph containing axiom declarations.

    Returns:
        Entailment type string (e.g., "owl:inverseOf") or None.
    """
    # Check owl:inverseOf: triple ?x ?q ?y where ontology declares
    # ?q owl:inverseOf ?p_other (or ?p_other owl:inverseOf ?q)
    # This means the predicate in the inferred triple is an inverse property.
    if _is_inverse_entailment(p, ontology):
        return "owl:inverseOf"

    # Check rdf:type assertions (could be subClassOf or domain/range)
    if p == RDF.type and isinstance(o, URIRef):
        # Check rdfs:subClassOf: ?x rdf:type ?C where ontology has
        # ?D rdfs:subClassOf ?C for some ?D
        if _is_subclass_entailment(o, ontology):
            return "rdfs:subClassOf"

        # Check rdfs:domain/rdfs:range: ?x rdf:type ?C where ontology has
        # some ?prop with rdfs:domain ?C or rdfs:range ?C
        if _is_domain_range_entailment(o, ontology):
            return "rdfs:domain/rdfs:range"

    # Check rdfs:subPropertyOf: triple uses a super-property
    if _is_subproperty_entailment(p, ontology):
        return "rdfs:subPropertyOf"

    # Check owl:TransitiveProperty: predicate is declared transitive
    if _is_transitive_entailment(p, ontology):
        return "owl:TransitiveProperty"

    return None


def _is_inverse_entailment(predicate: Node, ontology: Graph) -> bool:
    """Check if the predicate is involved in an owl:inverseOf declaration."""
    # predicate owl:inverseOf ?other
    for _ in ontology.objects(predicate, OWL.inverseOf):
        return True
    # ?other owl:inverseOf predicate
    for _ in ontology.subjects(OWL.inverseOf, predicate):
        return True
    return False


def _is_subclass_entailment(class_node: Node, ontology: Graph) -> bool:
    """Check if the class is a superclass in a rdfs:subClassOf chain."""
    # ?subclass rdfs:subClassOf class_node
    for _ in ontology.subjects(RDFS.subClassOf, class_node):
        return True
    return False


def _is_domain_range_entailment(class_node: Node, ontology: Graph) -> bool:
    """Check if the class appears as rdfs:domain or rdfs:range of a property."""
    for _ in ontology.subjects(RDFS.domain, class_node):
        return True
    for _ in ontology.subjects(RDFS.range, class_node):
        return True
    return False


def _is_subproperty_entailment(predicate: Node, ontology: Graph) -> bool:
    """Check if the predicate is a super-property in an rdfs:subPropertyOf chain."""
    # ?subprop rdfs:subPropertyOf predicate
    for _ in ontology.subjects(RDFS.subPropertyOf, predicate):
        return True
    return False


def _is_transitive_entailment(predicate: Node, ontology: Graph) -> bool:
    """Check if the predicate is declared as owl:TransitiveProperty."""
    return (predicate, RDF.type, OWL.TransitiveProperty) in ontology


def filter_by_enabled(
    triples_with_types: list[tuple[tuple, str]],
    enabled_types: set[str],
) -> list[tuple[tuple, str]]:
    """Filter classified triples to only those with enabled entailment types.

    Args:
        triples_with_types: List of ((s, p, o), entailment_type) tuples.
        enabled_types: Set of enabled entailment type labels.

    Returns:
        Filtered list containing only triples whose type is in enabled_types.
    """
    return [
        (triple, etype)
        for triple, etype in triples_with_types
        if etype in enabled_types
    ]
