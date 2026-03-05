"""Lint service for querying structured SHACL validation results.

Provides paginated, filterable access to validation results stored as
structured triples in per-run named graphs. Supports severity and
object type filtering, detail levels, status polling, and diff between
consecutive runs.
"""

import logging
import math
from typing import Optional

from app.lint.models import (
    LINT_LATEST_SUBJECT,
    SEVERITY_ALLOWLIST,
    LintDiffResponse,
    LintResultItem,
    LintResultsResponse,
    LintStatusResponse,
)
from app.services.labels import LabelService
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Named graph for validation report summaries and run pointers
VALIDATIONS_GRAPH = "urn:sempkm:validations"


class LintService:
    """Query and paginate structured SHACL validation results.

    Reads from per-run named graphs written by ValidationService._store_report().
    Uses LabelService for inline label resolution so API consumers get
    human-readable labels alongside IRIs.
    """

    def __init__(self, triplestore_client: TriplestoreClient, label_service: LabelService) -> None:
        self._client = triplestore_client
        self._labels = label_service

    async def get_latest_run_iri(self) -> Optional[str]:
        """Query the latest lint run IRI from the validations graph.

        Returns:
            The latest run IRI string, or None if no runs exist.
        """
        query = f"""
        SELECT ?run WHERE {{
          GRAPH <{VALIDATIONS_GRAPH}> {{
            <{LINT_LATEST_SUBJECT}> <urn:sempkm:latestRun> ?run .
          }}
        }} LIMIT 1
        """
        result = await self._client.query(query)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None
        return bindings[0]["run"]["value"]

    async def _get_previous_run_iri(self) -> Optional[str]:
        """Query the previous lint run IRI from the validations graph."""
        query = f"""
        SELECT ?run WHERE {{
          GRAPH <{VALIDATIONS_GRAPH}> {{
            <{LINT_LATEST_SUBJECT}> <urn:sempkm:previousRun> ?run .
          }}
        }} LIMIT 1
        """
        result = await self._client.query(query)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None
        return bindings[0]["run"]["value"]

    async def get_results_for_object(self, object_iri: str) -> list[dict]:
        """Query structured lint results filtered by focus_node for one object.

        Returns results from the latest run matching the given object IRI.
        Used by the per-object lint panel in the browser.

        Returns:
            List of dicts with keys: severity, message, path, source_shape.
        """
        run_iri = await self.get_latest_run_iri()
        if not run_iri:
            return []

        query = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        PREFIX sempkm: <urn:sempkm:>
        SELECT ?severity ?message ?path ?sourceShape WHERE {{
          GRAPH <{run_iri}> {{
            ?result a sempkm:LintResult ;
                    sh:focusNode <{object_iri}> ;
                    sh:resultSeverity ?severity .
            OPTIONAL {{ ?result sh:resultMessage ?message }}
            OPTIONAL {{ ?result sh:resultPath ?path }}
            OPTIONAL {{ ?result sh:sourceShape ?sourceShape }}
          }}
        }}
        """
        try:
            result = await self._client.query(query)
            bindings = result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning(
                "Failed to query lint results for object %s", object_iri, exc_info=True
            )
            return []

        # Resolve path labels
        path_iris: set[str] = set()
        for row in bindings:
            if "path" in row:
                path_iris.add(row["path"]["value"])
        labels = await self._labels.resolve_batch(list(path_iris)) if path_iris else {}

        items: list[dict] = []
        for row in bindings:
            path_iri = row.get("path", {}).get("value", "")
            items.append({
                "severity": row["severity"]["value"],
                "message": row.get("message", {}).get("value", "Constraint violated"),
                "path": labels.get(path_iri, _local_name(path_iri)) if path_iri else "",
                "source_shape": row.get("sourceShape", {}).get("value", ""),
            })

        return items

    async def get_results(
        self,
        page: int = 1,
        per_page: int = 50,
        severity: Optional[str] = None,
        object_type: Optional[str] = None,
        run_id: Optional[str] = None,
        detail: bool = False,
        search: Optional[str] = None,
        sort: str = "severity",
    ) -> LintResultsResponse:
        """Query paginated lint results from a run's named graph.

        Args:
            page: Page number (1-indexed).
            per_page: Results per page (max 200).
            severity: Filter by severity (Violation, Warning, Info).
            object_type: Filter by RDF type IRI of the focus node.
            run_id: Specific run IRI to query (defaults to latest).
            detail: If True, include source_shape, constraint_component, source_model.

        Returns:
            Paginated LintResultsResponse with resolved labels.
        """
        # Clamp pagination
        page = max(1, page)
        per_page = max(1, min(200, per_page))

        # Resolve run IRI
        target_run = run_id or await self.get_latest_run_iri()
        if not target_run:
            return LintResultsResponse(
                results=[], page=page, per_page=per_page,
                total=0, total_pages=0, run_id="", run_timestamp="", conforms=True,
            )

        # Validate severity filter
        if severity and severity not in SEVERITY_ALLOWLIST:
            return LintResultsResponse(
                results=[], page=page, per_page=per_page,
                total=0, total_pages=0, run_id=target_run, run_timestamp="", conforms=True,
            )

        # Validate object_type filter
        if object_type and not (object_type.startswith("http://") or object_type.startswith("https://") or object_type.startswith("urn:")):
            return LintResultsResponse(
                results=[], page=page, per_page=per_page,
                total=0, total_pages=0, run_id=target_run, run_timestamp="", conforms=True,
            )

        # Build filter clauses
        severity_filter = ""
        if severity:
            severity_uri = _severity_string_to_uri(severity)
            severity_filter = f"FILTER(?severity = <{severity_uri}>)"

        object_type_filter = ""
        if object_type:
            object_type_filter = f"""
            GRAPH <urn:sempkm:current> {{
              ?focusNode a <{object_type}> .
            }}
            """

        # Search filter: match across message, focusNode IRI, and path
        search_filter = ""
        if search:
            # Sanitize search string to prevent SPARQL injection
            escaped = search.replace("\\", "\\\\").replace('"', '\\"')
            search_filter = f'FILTER(CONTAINS(LCASE(?message), LCASE("{escaped}")) || CONTAINS(LCASE(STR(?focusNode)), LCASE("{escaped}")) || (BOUND(?path) && CONTAINS(LCASE(STR(?path)), LCASE("{escaped}"))))'

        # Sort order: allowlist to prevent injection
        sort_allowlist = {
            "severity": "ORDER BY ?severity ?focusNode",
            "object": "ORDER BY ?focusNode ?severity",
            "path": "ORDER BY ?path ?focusNode",
        }
        order_clause = sort_allowlist.get(sort, sort_allowlist["severity"])

        # Count query
        count_query = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        PREFIX sempkm: <urn:sempkm:>
        SELECT (COUNT(?result) AS ?total) WHERE {{
          GRAPH <{target_run}> {{
            ?result a sempkm:LintResult ;
                    sh:focusNode ?focusNode ;
                    sh:resultSeverity ?severity ;
                    sh:resultMessage ?message .
            OPTIONAL {{ ?result sh:resultPath ?path }}
            {severity_filter}
            {search_filter}
          }}
          {object_type_filter}
        }}
        """
        count_result = await self._client.query(count_query)
        count_bindings = count_result.get("results", {}).get("bindings", [])
        total = int(count_bindings[0]["total"]["value"]) if count_bindings else 0
        total_pages = math.ceil(total / per_page) if total > 0 else 0
        offset = (page - 1) * per_page

        # Get run metadata
        run_meta = await self._get_run_metadata(target_run)
        run_timestamp = run_meta.get("timestamp", "")
        conforms = run_meta.get("conforms", True)

        if total == 0:
            return LintResultsResponse(
                results=[], page=page, per_page=per_page,
                total=0, total_pages=0, run_id=target_run,
                run_timestamp=run_timestamp, conforms=conforms,
            )

        # Results query
        results_query = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        PREFIX sempkm: <urn:sempkm:>
        SELECT ?result ?focusNode ?severity ?message ?path ?sourceShape ?component ?sourceModel ?orphaned
        WHERE {{
          GRAPH <{target_run}> {{
            ?result a sempkm:LintResult ;
                    sh:focusNode ?focusNode ;
                    sh:resultSeverity ?severity ;
                    sh:resultMessage ?message .
            OPTIONAL {{ ?result sh:resultPath ?path }}
            OPTIONAL {{ ?result sh:sourceShape ?sourceShape }}
            OPTIONAL {{ ?result sh:sourceConstraintComponent ?component }}
            OPTIONAL {{ ?result sempkm:sourceModel ?sourceModel }}
            OPTIONAL {{ ?result sempkm:orphaned ?orphaned }}
            {severity_filter}
            {search_filter}
          }}
          {object_type_filter}
        }}
        {order_clause}
        OFFSET {offset} LIMIT {per_page}
        """
        result = await self._client.query(results_query)
        bindings = result.get("results", {}).get("bindings", [])

        # Collect IRIs for batch label resolution
        iris_to_resolve: set[str] = set()
        for row in bindings:
            iris_to_resolve.add(row["focusNode"]["value"])
            if "path" in row:
                iris_to_resolve.add(row["path"]["value"])

        # Also resolve object types for focus nodes
        focus_nodes = [row["focusNode"]["value"] for row in bindings]
        type_map = await self._resolve_types(focus_nodes)
        for type_iri in type_map.values():
            if type_iri:
                iris_to_resolve.add(type_iri)

        labels = await self._labels.resolve_batch(list(iris_to_resolve)) if iris_to_resolve else {}

        # Build result items
        items: list[LintResultItem] = []
        for row in bindings:
            focus_node = row["focusNode"]["value"]
            severity_uri = row["severity"]["value"]
            severity_label = _severity_uri_to_string(severity_uri)
            path_iri = row.get("path", {}).get("value")
            obj_type_iri = type_map.get(focus_node)

            item = LintResultItem(
                focus_node=focus_node,
                object_label=labels.get(focus_node, _local_name(focus_node)),
                object_type_label=labels.get(obj_type_iri, _local_name(obj_type_iri)) if obj_type_iri else None,
                severity=severity_label,
                message=row["message"]["value"],
                path_label=labels.get(path_iri, _local_name(path_iri)) if path_iri else None,
            )

            if detail:
                item.source_shape = row.get("sourceShape", {}).get("value")
                item.constraint_component = row.get("component", {}).get("value")
                item.source_model = row.get("sourceModel", {}).get("value")
                orphaned_val = row.get("orphaned", {}).get("value", "false")
                item.orphaned = orphaned_val.lower() == "true"

            items.append(item)

        return LintResultsResponse(
            results=items,
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            run_id=target_run,
            run_timestamp=run_timestamp,
            conforms=conforms,
        )

    async def get_status(self) -> LintStatusResponse:
        """Get lightweight summary of the latest lint run.

        Returns:
            LintStatusResponse with counts and metadata.
        """
        run_iri = await self.get_latest_run_iri()
        if not run_iri:
            return LintStatusResponse(
                conforms=None, violation_count=0, warning_count=0, info_count=0,
                run_id=None, run_timestamp=None, trigger_source=None,
            )

        meta = await self._get_run_metadata(run_iri)
        return LintStatusResponse(
            conforms=meta.get("conforms", True),
            violation_count=meta.get("violation_count", 0),
            warning_count=meta.get("warning_count", 0),
            info_count=meta.get("info_count", 0),
            run_id=run_iri,
            run_timestamp=meta.get("timestamp"),
            trigger_source=meta.get("trigger_source"),
        )

    async def get_diff(self) -> LintDiffResponse:
        """Compare latest and previous runs to find new and resolved issues.

        Uses a fingerprint tuple of (focus_node, severity, source_shape,
        constraint_component, path) to match results across runs.

        Returns:
            LintDiffResponse with new_issues and resolved_issues.
        """
        latest_run = await self.get_latest_run_iri()
        previous_run = await self._get_previous_run_iri()

        if not latest_run:
            return LintDiffResponse(
                new_issues=[], resolved_issues=[],
                latest_run_id="", previous_run_id=None,
            )

        latest_results = await self._get_run_fingerprints(latest_run)
        previous_results = await self._get_run_fingerprints(previous_run) if previous_run else {}

        latest_keys = set(latest_results.keys())
        previous_keys = set(previous_results.keys())

        new_keys = latest_keys - previous_keys
        resolved_keys = previous_keys - latest_keys

        # Resolve labels for new and resolved issues
        iris_to_resolve: set[str] = set()
        for key in new_keys | resolved_keys:
            iris_to_resolve.add(key[0])  # focus_node
            if key[4]:  # path
                iris_to_resolve.add(key[4])

        # Resolve types
        all_focus = [k[0] for k in new_keys | resolved_keys]
        type_map = await self._resolve_types(all_focus) if all_focus else {}
        for t in type_map.values():
            if t:
                iris_to_resolve.add(t)

        labels = await self._labels.resolve_batch(list(iris_to_resolve)) if iris_to_resolve else {}

        def _make_item(key: tuple, data: dict) -> LintResultItem:
            focus_node, severity_uri, _, _, path = key
            obj_type = type_map.get(focus_node)
            return LintResultItem(
                focus_node=focus_node,
                object_label=labels.get(focus_node, _local_name(focus_node)),
                object_type_label=labels.get(obj_type, _local_name(obj_type)) if obj_type else None,
                severity=_severity_uri_to_string(severity_uri),
                message=data.get("message", ""),
                path_label=labels.get(path, _local_name(path)) if path else None,
            )

        new_issues = [_make_item(k, latest_results[k]) for k in new_keys]
        resolved_issues = [_make_item(k, previous_results[k]) for k in resolved_keys]

        return LintDiffResponse(
            new_issues=new_issues,
            resolved_issues=resolved_issues,
            latest_run_id=latest_run,
            previous_run_id=previous_run,
        )

    async def _get_run_metadata(self, run_iri: str) -> dict:
        """Query run metadata from its named graph."""
        query = f"""
        PREFIX sempkm: <urn:sempkm:>
        SELECT ?timestamp ?conforms ?triggerSource ?violations ?warnings ?infos
        WHERE {{
          GRAPH <{run_iri}> {{
            <{run_iri}> a sempkm:LintRun ;
                        sempkm:timestamp ?timestamp ;
                        sempkm:conforms ?conforms .
            OPTIONAL {{ <{run_iri}> sempkm:triggerSource ?triggerSource }}
            OPTIONAL {{ <{run_iri}> sempkm:violationCount ?violations }}
            OPTIONAL {{ <{run_iri}> sempkm:warningCount ?warnings }}
            OPTIONAL {{ <{run_iri}> sempkm:infoCount ?infos }}
          }}
        }} LIMIT 1
        """
        result = await self._client.query(query)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return {}
        row = bindings[0]
        return {
            "timestamp": row.get("timestamp", {}).get("value"),
            "conforms": row.get("conforms", {}).get("value", "true").lower() == "true",
            "trigger_source": row.get("triggerSource", {}).get("value"),
            "violation_count": int(row.get("violations", {}).get("value", "0")),
            "warning_count": int(row.get("warnings", {}).get("value", "0")),
            "info_count": int(row.get("infos", {}).get("value", "0")),
        }

    async def _get_run_fingerprints(self, run_iri: str) -> dict[tuple, dict]:
        """Get fingerprint tuples for all results in a run.

        Fingerprint = (focus_node, severity, source_shape, constraint_component, path).
        Returns a dict mapping fingerprint -> {message: str} for building diff items.
        """
        query = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        PREFIX sempkm: <urn:sempkm:>
        SELECT ?focusNode ?severity ?sourceShape ?component ?path ?message
        WHERE {{
          GRAPH <{run_iri}> {{
            ?result a sempkm:LintResult ;
                    sh:focusNode ?focusNode ;
                    sh:resultSeverity ?severity ;
                    sh:resultMessage ?message .
            OPTIONAL {{ ?result sh:resultPath ?path }}
            OPTIONAL {{ ?result sh:sourceShape ?sourceShape }}
            OPTIONAL {{ ?result sh:sourceConstraintComponent ?component }}
          }}
        }}
        """
        result = await self._client.query(query)
        bindings = result.get("results", {}).get("bindings", [])

        fingerprints: dict[tuple, dict] = {}
        for row in bindings:
            key = (
                row["focusNode"]["value"],
                row["severity"]["value"],
                row.get("sourceShape", {}).get("value", ""),
                row.get("component", {}).get("value", ""),
                row.get("path", {}).get("value", ""),
            )
            fingerprints[key] = {"message": row["message"]["value"]}

        return fingerprints

    async def _resolve_types(self, iris: list[str]) -> dict[str, Optional[str]]:
        """Resolve RDF types for a list of focus node IRIs.

        Queries the current state graph for rdf:type of each IRI.

        Returns:
            Dict mapping IRI -> type IRI (or None if not found).
        """
        if not iris:
            return {}

        unique_iris = list(set(iris))
        values_clause = " ".join(f"<{iri}>" for iri in unique_iris)
        query = f"""
        SELECT ?s ?type WHERE {{
          GRAPH <urn:sempkm:current> {{
            VALUES ?s {{ {values_clause} }}
            ?s a ?type .
          }}
        }}
        """
        result = await self._client.query(query)
        bindings = result.get("results", {}).get("bindings", [])

        type_map: dict[str, Optional[str]] = {iri: None for iri in unique_iris}
        for row in bindings:
            s = row["s"]["value"]
            t = row["type"]["value"]
            # Take the first type found (skip owl/rdfs meta-types)
            if type_map[s] is None and not t.startswith("http://www.w3.org/2002/07/owl#"):
                type_map[s] = t

        return type_map


def _severity_string_to_uri(severity: str) -> str:
    """Convert severity string to SHACL URI string."""
    mapping = {
        "Violation": "http://www.w3.org/ns/shacl#Violation",
        "Warning": "http://www.w3.org/ns/shacl#Warning",
        "Info": "http://www.w3.org/ns/shacl#Info",
    }
    return mapping.get(severity, "http://www.w3.org/ns/shacl#Violation")


def _severity_uri_to_string(uri: str) -> str:
    """Convert SHACL severity URI to human-readable string."""
    mapping = {
        "http://www.w3.org/ns/shacl#Violation": "Violation",
        "http://www.w3.org/ns/shacl#Warning": "Warning",
        "http://www.w3.org/ns/shacl#Info": "Info",
    }
    return mapping.get(uri, "Violation")


def _local_name(iri: Optional[str]) -> str:
    """Extract local name from an IRI as a fallback label."""
    if not iri:
        return ""
    for sep in ("#", "/", ":"):
        idx = iri.rfind(sep)
        if 0 <= idx < len(iri) - 1:
            return iri[idx + 1:]
    return iri
