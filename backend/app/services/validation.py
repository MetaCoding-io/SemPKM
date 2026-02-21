"""SHACL validation service orchestrating data fetch, validation, and report storage.

Fetches the current state graph from the triplestore via SPARQL CONSTRUCT,
runs pyshacl.validate() against loaded SHACL shapes, parses the results
into a ValidationReport, and stores the report as named graphs.
"""

import asyncio
import logging
from typing import Awaitable, Callable, Optional

import pyshacl
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import XSD

from app.triplestore.client import TriplestoreClient
from app.validation.report import ValidationReport, ValidationReportSummary

logger = logging.getLogger(__name__)

# Named graph for validation report summaries
VALIDATIONS_GRAPH = "urn:sempkm:validations"


async def empty_shapes_loader() -> Graph:
    """Default shapes loader returning an empty graph.

    Used until Phase 3 provides real SHACL shapes from Mental Models.
    An empty shapes graph means no constraints to validate against,
    so validation always conforms.
    """
    return Graph()


class ValidationService:
    """Orchestrates SHACL validation: fetch data, validate, store reports.

    Takes a triplestore client for data access and a shapes loader callable
    that returns an rdflib Graph of SHACL shapes. The shapes loader is
    async to support loading from triplestore or filesystem.
    """

    def __init__(
        self,
        triplestore_client: TriplestoreClient,
        shapes_loader: Callable[[], Awaitable[Graph]],
    ) -> None:
        self._client = triplestore_client
        self._shapes_loader = shapes_loader

    async def validate(self, event_iri: str, timestamp: str) -> ValidationReport:
        """Run full SHACL validation of current state against shapes.

        1. Fetch current state graph via SPARQL CONSTRUCT
        2. Load shapes graph
        3. Run pyshacl.validate() in thread (CPU-bound)
        4. Parse results into ValidationReport
        5. Store report as named graphs in triplestore

        Args:
            event_iri: The event IRI that triggered this validation.
            timestamp: ISO 8601 timestamp for the report.

        Returns:
            Parsed ValidationReport with results and summary.
        """
        # 1. Fetch current state graph
        turtle_bytes = await self._client.construct(
            "CONSTRUCT { ?s ?p ?o } FROM <urn:sempkm:current> WHERE { ?s ?p ?o }"
        )
        data_graph = Graph()
        if turtle_bytes.strip():
            data_graph.parse(data=turtle_bytes, format="turtle")

        # 2. Load shapes
        shapes_graph = await self._shapes_loader()

        # If no shapes installed, return synthetic conforms=True report
        if len(shapes_graph) == 0:
            logger.info(
                "No SHACL shapes loaded, returning synthetic conforms=True for %s",
                event_iri,
            )
            report = ValidationReport(
                event_iri=event_iri,
                conforms=True,
                results=[],
                timestamp=timestamp,
            )
            # Store the synthetic report
            await self._store_report(report, results_graph=None)
            return report

        # 3. Run pyshacl in thread (CPU-bound work)
        conforms, results_graph, _results_text = await asyncio.to_thread(
            pyshacl.validate,
            data_graph,
            shacl_graph=shapes_graph,
            allow_infos=True,
            allow_warnings=True,
        )

        # 4. Parse results
        report = ValidationReport.from_pyshacl(
            event_iri=event_iri,
            results_graph=results_graph,
            conforms=conforms,
            timestamp=timestamp,
        )

        # 5. Store report
        await self._store_report(report, results_graph=results_graph)

        return report

    async def _store_report(
        self,
        report: ValidationReport,
        results_graph: Optional[Graph],
    ) -> None:
        """Store validation report as named graphs in the triplestore.

        Stores the full pyshacl results_graph (if any) into a named graph
        keyed by the report IRI, and inserts summary triples into the
        shared validations graph for fast polling.

        Args:
            report: The parsed ValidationReport.
            results_graph: The raw pyshacl results graph (None for synthetic reports).
        """
        report_iri = report.report_iri

        # Store full report graph if available
        if results_graph and len(results_graph) > 0:
            report_turtle = results_graph.serialize(format="turtle")
            # Insert the full report into its own named graph
            # Escape the turtle for SPARQL INSERT DATA
            await self._client.update(
                f"INSERT DATA {{ GRAPH <{report_iri}> {{ {_turtle_to_ntriples(results_graph)} }} }}"
            )

        # Store summary triples in the shared validations graph
        summary_triples = report.to_summary_triples()
        if summary_triples:
            triple_lines = []
            for s, p, o in summary_triples:
                triple_lines.append(f"  {_rdf_term_to_sparql(s)} {_rdf_term_to_sparql(p)} {_rdf_term_to_sparql(o)} .")
            triples_str = "\n".join(triple_lines)
            await self._client.update(
                f"INSERT DATA {{ GRAPH <{VALIDATIONS_GRAPH}> {{\n{triples_str}\n}} }}"
            )

    async def get_latest_summary(self) -> Optional[ValidationReportSummary]:
        """Query the triplestore for the most recent validation report summary.

        Returns:
            The latest ValidationReportSummary, or None if no reports exist.
        """
        query = """
        SELECT ?report ?event ?conforms ?violations ?warnings ?infos ?ts
        WHERE {
          GRAPH <urn:sempkm:validations> {
            ?report a <urn:sempkm:ValidationReport> ;
                    <urn:sempkm:forEvent> ?event ;
                    <urn:sempkm:conforms> ?conforms ;
                    <urn:sempkm:violationCount> ?violations ;
                    <urn:sempkm:warningCount> ?warnings ;
                    <urn:sempkm:infoCount> ?infos ;
                    <urn:sempkm:timestamp> ?ts .
          }
        }
        ORDER BY DESC(?ts) LIMIT 1
        """
        result = await self._client.query(query)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        row = bindings[0]
        return ValidationReportSummary(
            report_iri=row["report"]["value"],
            event_iri=row["event"]["value"],
            conforms=row["conforms"]["value"].lower() == "true",
            violation_count=int(row["violations"]["value"]),
            warning_count=int(row["warnings"]["value"]),
            info_count=int(row["infos"]["value"]),
            timestamp=row["ts"]["value"],
        )

    async def get_report_by_event(
        self, event_iri: str
    ) -> Optional[ValidationReportSummary]:
        """Query the triplestore for a validation report by event IRI.

        Args:
            event_iri: The event IRI to find a report for.

        Returns:
            ValidationReportSummary for the event, or None if not found.
        """
        query = f"""
        SELECT ?report ?conforms ?violations ?warnings ?infos ?ts
        WHERE {{
          GRAPH <urn:sempkm:validations> {{
            ?report a <urn:sempkm:ValidationReport> ;
                    <urn:sempkm:forEvent> <{event_iri}> ;
                    <urn:sempkm:conforms> ?conforms ;
                    <urn:sempkm:violationCount> ?violations ;
                    <urn:sempkm:warningCount> ?warnings ;
                    <urn:sempkm:infoCount> ?infos ;
                    <urn:sempkm:timestamp> ?ts .
          }}
        }}
        LIMIT 1
        """
        result = await self._client.query(query)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        row = bindings[0]
        return ValidationReportSummary(
            report_iri=row["report"]["value"],
            event_iri=event_iri,
            conforms=row["conforms"]["value"].lower() == "true",
            violation_count=int(row["violations"]["value"]),
            warning_count=int(row["warnings"]["value"]),
            info_count=int(row["infos"]["value"]),
            timestamp=row["ts"]["value"],
        )


def _rdf_term_to_sparql(term) -> str:
    """Serialize an rdflib term to SPARQL syntax."""
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
    else:
        return f"<{term}>"


def _turtle_to_ntriples(graph: Graph) -> str:
    """Serialize a graph to N-Triples format for SPARQL INSERT DATA.

    N-Triples format works directly in SPARQL INSERT DATA blocks
    since each line is a complete triple statement.
    """
    return graph.serialize(format="nt")
