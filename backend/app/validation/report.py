"""SHACL validation report parsing, storage, and summary generation.

Parses W3C SHACL ValidationReport graphs from pyshacl into structured
dataclasses. Generates RDF triples for persistent storage as named
graphs in the triplestore.
"""

from dataclasses import dataclass, field
from typing import Optional

from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, SH, XSD


SEMPKM = Namespace("urn:sempkm:")

# SPARQL query for extracting validation results from pyshacl report graph
REPORT_QUERY = """
SELECT ?result ?severity ?focusNode ?path ?value ?message ?sourceShape ?component
WHERE {
    ?report a sh:ValidationReport ;
            sh:result ?result .
    ?result sh:resultSeverity ?severity ;
            sh:focusNode ?focusNode .
    OPTIONAL { ?result sh:resultPath ?path }
    OPTIONAL { ?result sh:value ?value }
    OPTIONAL { ?result sh:resultMessage ?message }
    OPTIONAL { ?result sh:sourceShape ?sourceShape }
    OPTIONAL { ?result sh:sourceConstraintComponent ?component }
}
"""

# Map SHACL severity URIs to human-readable strings
SEVERITY_MAP = {
    str(SH.Violation): "Violation",
    str(SH.Warning): "Warning",
    str(SH.Info): "Info",
}


@dataclass
class ValidationResult:
    """A single validation result from a SHACL report."""

    focus_node: str
    severity: str  # "Violation", "Warning", or "Info"
    path: Optional[str] = None
    value: Optional[str] = None
    message: str = ""
    source_shape: Optional[str] = None
    constraint_component: Optional[str] = None


@dataclass
class ValidationReportSummary:
    """Lightweight summary of a validation report for fast polling."""

    report_iri: str
    event_iri: str
    conforms: bool
    violation_count: int
    warning_count: int
    info_count: int
    timestamp: str


@dataclass
class ValidationReport:
    """Parsed SHACL validation report with results and summary generation.

    Created from pyshacl output via from_pyshacl() classmethod. Generates
    RDF triples for triplestore persistence via to_summary_triples().
    """

    event_iri: str
    conforms: bool
    results: list[ValidationResult] = field(default_factory=list)
    timestamp: str = ""

    @classmethod
    def from_pyshacl(
        cls,
        event_iri: str,
        results_graph: Graph,
        conforms: bool,
        timestamp: str,
    ) -> "ValidationReport":
        """Parse a pyshacl results_graph into a ValidationReport.

        Extracts individual validation results using SPARQL query against
        the W3C SHACL ValidationReport graph structure.

        Args:
            event_iri: The event IRI this validation is for.
            results_graph: The rdflib Graph returned by pyshacl.validate().
            conforms: Whether the data conforms to the shapes.
            timestamp: ISO 8601 timestamp for the report.

        Returns:
            Parsed ValidationReport with all individual results.
        """
        parsed_results: list[ValidationResult] = []

        for row in results_graph.query(REPORT_QUERY):
            severity_str = SEVERITY_MAP.get(str(row.severity), "Violation")
            path_str = str(row.path) if row.path else None
            value_str = str(row.value) if row.value else None
            source_shape_str = str(row.sourceShape) if row.sourceShape else None
            component_str = str(row.component) if row.component else None

            # Use sh:resultMessage if present, otherwise auto-generate
            if row.message:
                message = str(row.message)
            else:
                # Auto-generate from constraint metadata
                path_label = path_str if path_str else "(unknown path)"
                component_label = (
                    component_str.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
                    if component_str
                    else "constraint"
                )
                message = f"{path_label} {component_label}: constraint violated"

            parsed_results.append(
                ValidationResult(
                    focus_node=str(row.focusNode),
                    severity=severity_str,
                    path=path_str,
                    value=value_str,
                    message=message,
                    source_shape=source_shape_str,
                    constraint_component=component_str,
                )
            )

        return cls(
            event_iri=event_iri,
            conforms=conforms,
            results=parsed_results,
            timestamp=timestamp,
        )

    @property
    def report_iri(self) -> str:
        """Generate report IRI from event IRI.

        Transforms urn:sempkm:event:{uuid} to urn:sempkm:validation:{uuid}.
        """
        # Extract UUID from event IRI pattern
        prefix = "urn:sempkm:event:"
        if self.event_iri.startswith(prefix):
            uuid = self.event_iri[len(prefix):]
            return f"urn:sempkm:validation:{uuid}"
        # Fallback: use event_iri hash
        return f"urn:sempkm:validation:{hash(self.event_iri)}"

    def summary(self) -> ValidationReportSummary:
        """Generate a lightweight summary with counts by severity."""
        violation_count = sum(1 for r in self.results if r.severity == "Violation")
        warning_count = sum(1 for r in self.results if r.severity == "Warning")
        info_count = sum(1 for r in self.results if r.severity == "Info")

        return ValidationReportSummary(
            report_iri=self.report_iri,
            event_iri=self.event_iri,
            conforms=self.conforms,
            violation_count=violation_count,
            warning_count=warning_count,
            info_count=info_count,
            timestamp=self.timestamp,
        )

    def to_summary_triples(self) -> list[tuple]:
        """Generate RDF triples for the summary named graph.

        These triples are stored in <urn:sempkm:validations> for fast
        polling queries (latest report, report by event).

        Returns:
            List of (subject, predicate, object) tuples using rdflib terms.
        """
        report = URIRef(self.report_iri)
        event = URIRef(self.event_iri)

        return [
            (report, RDF.type, SEMPKM.ValidationReport),
            (report, SEMPKM.forEvent, event),
            (report, SEMPKM.conforms, Literal(self.conforms, datatype=XSD.boolean)),
            (
                report,
                SEMPKM.violationCount,
                Literal(
                    sum(1 for r in self.results if r.severity == "Violation"),
                    datatype=XSD.integer,
                ),
            ),
            (
                report,
                SEMPKM.warningCount,
                Literal(
                    sum(1 for r in self.results if r.severity == "Warning"),
                    datatype=XSD.integer,
                ),
            ),
            (
                report,
                SEMPKM.infoCount,
                Literal(
                    sum(1 for r in self.results if r.severity == "Info"),
                    datatype=XSD.integer,
                ),
            ),
            (
                report,
                SEMPKM.timestamp,
                Literal(self.timestamp, datatype=XSD.dateTime),
            ),
        ]
