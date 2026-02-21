"""Archive validation for Mental Model archives.

Validates IRI namespacing (all subject IRIs must use the model's
namespace prefix) and cross-file reference integrity (shapes
reference ontology classes, views reference valid types, seed data
uses defined types).
"""

from dataclasses import dataclass, field

from rdflib import Graph, URIRef, BNode
from rdflib.namespace import RDF, RDFS

from app.models.loader import ModelArchive

# OWL and SHACL namespace URIs
OWL_CLASS = URIRef("http://www.w3.org/2002/07/owl#Class")
SH_NODE_SHAPE = URIRef("http://www.w3.org/ns/shacl#NodeShape")
SH_TARGET_CLASS = URIRef("http://www.w3.org/ns/shacl#targetClass")
SEMPKM_TARGET_CLASS = URIRef("urn:sempkm:targetClass")

# External namespaces that are allowed in model IRIs
ALLOWED_EXTERNAL_NAMESPACES: set[str] = {
    "http://www.w3.org/",
    "http://purl.org/dc/",
    "https://schema.org/",
    "http://xmlns.com/foaf/",
}


@dataclass
class ValidationIssue:
    """A single validation issue found during archive validation."""

    file: str
    subject: str
    rule: str
    message: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class ArchiveValidationReport:
    """Aggregated validation results for a model archive."""

    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Archive is valid if there are no errors (warnings are OK)."""
        return len(self.errors) == 0


def validate_iri_namespacing(
    graph: Graph, model_namespace: str, file_name: str
) -> list[ValidationIssue]:
    """Check that all subject IRIs use the model's namespace.

    Iterates all unique subjects in the graph, skips BNodes, and checks
    that each subject IRI either starts with model_namespace or one of
    the ALLOWED_EXTERNAL_NAMESPACES.

    Args:
        graph: The rdflib Graph to validate.
        model_namespace: The model's namespace prefix (e.g., "urn:sempkm:model:basic-pkm:").
        file_name: Name of the source file for error reporting.

    Returns:
        List of ValidationIssue for any violations.
    """
    issues: list[ValidationIssue] = []

    for s in set(graph.subjects()):
        if isinstance(s, BNode):
            continue
        s_str = str(s)
        if s_str.startswith(model_namespace):
            continue
        if any(s_str.startswith(ns) for ns in ALLOWED_EXTERNAL_NAMESPACES):
            continue
        issues.append(
            ValidationIssue(
                file=file_name,
                subject=s_str,
                rule="iri-namespace",
                message=(
                    f"Subject IRI '{s_str}' does not use model namespace "
                    f"'{model_namespace}'"
                ),
                severity="error",
            )
        )

    return issues


def validate_reference_integrity(
    ontology: Graph,
    shapes: Graph,
    views: Graph,
    seed: Graph | None,
    model_namespace: str,
) -> list[ValidationIssue]:
    """Verify cross-file references between model artifacts.

    Checks that:
    1. SHACL shapes reference classes defined in the ontology
    2. Seed data uses types defined in the ontology
    3. View specs reference classes defined in the ontology

    Args:
        ontology: The ontology graph with OWL class definitions.
        shapes: The SHACL shapes graph.
        views: The view specifications graph.
        seed: The seed data graph (may be None).
        model_namespace: The model's namespace prefix.

    Returns:
        List of ValidationIssue for any integrity violations.
    """
    issues: list[ValidationIssue] = []

    # 1. Collect all OWL classes defined in ontology within model namespace
    ontology_classes: set[str] = set()
    for cls in ontology.subjects(RDF.type, OWL_CLASS):
        cls_str = str(cls)
        if cls_str.startswith(model_namespace):
            ontology_classes.add(cls_str)

    # 2. Check shapes: sh:targetClass must reference ontology classes
    for shape in shapes.subjects(RDF.type, SH_NODE_SHAPE):
        for target_class in shapes.objects(shape, SH_TARGET_CLASS):
            tc_str = str(target_class)
            if tc_str.startswith(model_namespace):
                if tc_str not in ontology_classes:
                    issues.append(
                        ValidationIssue(
                            file="shapes",
                            subject=str(shape),
                            rule="ref-integrity-shape-class",
                            message=(
                                f"Shape targets class '{tc_str}' "
                                "not defined in ontology"
                            ),
                        )
                    )

    # 3. Check seed data: rdf:type must reference ontology classes
    if seed is not None:
        for s, _, o in seed.triples((None, RDF.type, None)):
            o_str = str(o)
            if o_str.startswith(model_namespace):
                if o_str not in ontology_classes:
                    issues.append(
                        ValidationIssue(
                            file="seed",
                            subject=str(s),
                            rule="ref-integrity-seed-type",
                            message=(
                                f"Seed data uses type '{o_str}' "
                                "not defined in ontology"
                            ),
                        )
                    )

    # 4. Check views: sempkm:targetClass must reference ontology classes
    for s, _, o in views.triples((None, SEMPKM_TARGET_CLASS, None)):
        o_str = str(o)
        if o_str.startswith(model_namespace):
            if o_str not in ontology_classes:
                issues.append(
                    ValidationIssue(
                        file="views",
                        subject=str(s),
                        rule="ref-integrity-view-class",
                        message=(
                            f"View targets class '{o_str}' "
                            "not defined in ontology"
                        ),
                    )
                )

    return issues


def validate_archive(archive: ModelArchive) -> ArchiveValidationReport:
    """Run all validation checks on a loaded model archive.

    Performs IRI namespace validation on all graphs and cross-file
    reference integrity checks. Separates issues into errors and
    warnings.

    Args:
        archive: A loaded ModelArchive with all graphs.

    Returns:
        An ArchiveValidationReport with errors and warnings.
    """
    all_issues: list[ValidationIssue] = []
    model_ns = archive.manifest.namespace

    # IRI namespace validation on each graph
    all_issues.extend(
        validate_iri_namespacing(archive.ontology, model_ns, "ontology")
    )
    all_issues.extend(
        validate_iri_namespacing(archive.shapes, model_ns, "shapes")
    )
    all_issues.extend(
        validate_iri_namespacing(archive.views, model_ns, "views")
    )
    if archive.seed is not None:
        all_issues.extend(
            validate_iri_namespacing(archive.seed, model_ns, "seed")
        )

    # Cross-file reference integrity
    all_issues.extend(
        validate_reference_integrity(
            archive.ontology,
            archive.shapes,
            archive.views,
            archive.seed,
            model_ns,
        )
    )

    # Warning: ontology classes missing rdfs:label
    for cls in archive.ontology.subjects(RDF.type, OWL_CLASS):
        cls_str = str(cls)
        if cls_str.startswith(model_ns):
            labels = list(archive.ontology.objects(cls, RDFS.label))
            if not labels:
                all_issues.append(
                    ValidationIssue(
                        file="ontology",
                        subject=cls_str,
                        rule="missing-label",
                        message=(
                            f"OWL class '{cls_str}' has no rdfs:label"
                        ),
                        severity="warning",
                    )
                )

    # Separate into errors and warnings
    errors = [i for i in all_issues if i.severity == "error"]
    warnings = [i for i in all_issues if i.severity == "warning"]

    return ArchiveValidationReport(errors=errors, warnings=warnings)
