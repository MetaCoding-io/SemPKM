"""SHACL validation report parsing, storage, and summary generation.

Parses W3C SHACL ValidationReport graphs from pyshacl into structured
dataclasses. Generates RDF triples for persistent storage as named
graphs in the triplestore.
"""

import hashlib
import uuid
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

# Reverse map: human-readable severity string to SHACL URI
_SEVERITY_URI_MAP = {
    "Violation": SH.Violation,
    "Warning": SH.Warning,
    "Info": SH.Info,
}


def _severity_uri(severity: str) -> URIRef:
    """Map a human-readable severity string to its W3C SHACL URI.

    Args:
        severity: One of "Violation", "Warning", "Info".

    Returns:
        The corresponding sh:Violation, sh:Warning, or sh:Info URI.
    """
    return _SEVERITY_URI_MAP.get(severity, SH.Violation)


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
        # Fallback: use deterministic SHA-256 hex digest of event IRI
        digest = hashlib.sha256(self.event_iri.encode()).hexdigest()
        return f"urn:sempkm:validation:{digest}"

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

    def to_structured_triples(
        self,
        run_iri: str,
        trigger_source: str = "user_edit",
        source_model_map: dict[str, str] | None = None,
    ) -> list[tuple]:
        """Generate structured result triples for queryable storage.

        Each ValidationResult becomes an individual resource with its own IRI,
        linked to the run via sempkm:inRun. Run metadata triples are also
        generated for the run resource itself.

        Args:
            run_iri: The IRI for this lint run (e.g. urn:sempkm:lint-run:{uuid}).
            trigger_source: What triggered this run (user_edit, inference, manual).
            source_model_map: Optional mapping from shape IRI to model IRI.

        Returns:
            List of (subject, predicate, object) tuples using rdflib terms.
        """
        triples: list[tuple] = []
        run = URIRef(run_iri)

        # Count severities
        violation_count = sum(1 for r in self.results if r.severity == "Violation")
        warning_count = sum(1 for r in self.results if r.severity == "Warning")
        info_count = sum(1 for r in self.results if r.severity == "Info")

        # Run metadata triples
        triples.extend([
            (run, RDF.type, SEMPKM.LintRun),
            (run, SEMPKM.timestamp, Literal(self.timestamp, datatype=XSD.dateTime)),
            (run, SEMPKM.conforms, Literal(self.conforms, datatype=XSD.boolean)),
            (run, SEMPKM.triggerSource, Literal(trigger_source)),
            (run, SEMPKM.violationCount, Literal(violation_count, datatype=XSD.integer)),
            (run, SEMPKM.warningCount, Literal(warning_count, datatype=XSD.integer)),
            (run, SEMPKM.infoCount, Literal(info_count, datatype=XSD.integer)),
        ])

        # Per-result triples
        for result in self.results:
            result_iri = URIRef(f"urn:sempkm:lint-result:{uuid.uuid4()}")
            triples.extend([
                (result_iri, RDF.type, SEMPKM.LintResult),
                (result_iri, SEMPKM.inRun, run),
                (result_iri, SH.focusNode, URIRef(result.focus_node)),
                (result_iri, SH.resultSeverity, _severity_uri(result.severity)),
                (result_iri, SH.resultMessage, Literal(result.message)),
                (result_iri, SEMPKM.orphaned, Literal(False, datatype=XSD.boolean)),
            ])
            if result.path:
                triples.append((result_iri, SH.resultPath, URIRef(result.path)))
            if result.source_shape:
                triples.append((result_iri, SH.sourceShape, URIRef(result.source_shape)))
            if result.constraint_component:
                triples.append((result_iri, SH.sourceConstraintComponent, URIRef(result.constraint_component)))
            # Source model lookup
            if source_model_map and result.source_shape:
                model_iri = source_model_map.get(result.source_shape)
                if model_iri:
                    triples.append((result_iri, SEMPKM.sourceModel, URIRef(model_iri)))

        return triples

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
