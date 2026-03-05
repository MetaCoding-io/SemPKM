"""Pydantic response models and RDF schema constants for the lint API.

Defines the response shapes for /api/lint/results, /api/lint/status,
and /api/lint/diff endpoints. Also declares RDF namespace constants
used when storing and querying structured lint result triples.
"""

from pydantic import BaseModel


# RDF schema constants for structured lint result triples
LINT_RUN_PREFIX = "urn:sempkm:lint-run:"
LINT_RESULT_PREFIX = "urn:sempkm:lint-result:"
LINT_LATEST_SUBJECT = "urn:sempkm:lint-latest"

# Allowlist for severity filter validation (prevents SPARQL injection)
SEVERITY_ALLOWLIST = {"Violation", "Warning", "Info"}


class LintResultItem(BaseModel):
    """A single lint result with human-readable labels.

    Default fields are always present. Optional fields (source_shape,
    constraint_component, source_model, orphaned) are only populated
    when ?detail=full is requested.
    """

    focus_node: str
    object_label: str
    object_type_label: str | None
    severity: str
    message: str
    path_label: str | None
    # Only included when ?detail=full
    source_shape: str | None = None
    constraint_component: str | None = None
    source_model: str | None = None
    orphaned: bool = False


class LintResultsResponse(BaseModel):
    """Paginated envelope for lint results."""

    results: list[LintResultItem]
    page: int
    per_page: int
    total: int
    total_pages: int
    run_id: str
    run_timestamp: str
    conforms: bool


class LintStatusResponse(BaseModel):
    """Lightweight summary for polling the current lint status."""

    conforms: bool | None
    violation_count: int
    warning_count: int
    info_count: int
    run_id: str | None
    run_timestamp: str | None
    trigger_source: str | None


class LintDiffResponse(BaseModel):
    """Diff between latest and previous validation runs."""

    new_issues: list[LintResultItem]
    resolved_issues: list[LintResultItem]
    latest_run_id: str
    previous_run_id: str | None
