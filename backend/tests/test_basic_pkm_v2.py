"""Acceptance tests for basic-pkm v2.0.0 (Task & Milestone types).

Exercises the full validation pipeline:
  parse_manifest → load_archive → validate_archive
and proves the overdue-task SPARQLConstraint fires a sh:Warning via pyshacl.

Retires three key risks from the M011 roadmap:
  1. SPARQL-based validation rules with date arithmetic
  2. refresh_artifacts upgrade path (additive types)
  3. sh:severity placement (warning, not error)
"""

from pathlib import Path

import pyshacl
import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, XSD

from app.models.loader import load_archive
from app.models.manifest import parse_manifest
from app.models.validator import validate_archive

# Namespaces
BPKM = Namespace("urn:sempkm:model:basic-pkm:")
SH = Namespace("http://www.w3.org/ns/shacl#")
SEMPKM = Namespace("urn:sempkm:vocab:")

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "basic-pkm"


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def manifest():
    return parse_manifest(MODEL_DIR)


@pytest.fixture(scope="module")
def archive(manifest):
    return load_archive(MODEL_DIR, manifest)


# ── Manifest Tests ──────────────────────────────────────────────────


def test_manifest_parses_v2(manifest):
    """Manifest parses as v2.0.0 with 6 icons including Task and Milestone."""
    assert manifest.version == "2.0.0"
    assert manifest.modelId == "basic-pkm"
    assert len(manifest.icons) == 6
    icon_types = {icon.type for icon in manifest.icons}
    assert "bpkm:Task" in icon_types
    assert "bpkm:Milestone" in icon_types


# ── Archive Loading Tests ───────────────────────────────────────────


def test_archive_loads_all_graphs(archive):
    """All five graphs (ontology, shapes, views, seed, rules) load non-empty."""
    assert archive.ontology is not None and len(archive.ontology) > 0
    assert archive.shapes is not None and len(archive.shapes) > 0
    assert archive.views is not None and len(archive.views) > 0
    assert archive.seed is not None and len(archive.seed) > 0
    assert archive.rules is not None and len(archive.rules) > 0


# ── Validation Tests ────────────────────────────────────────────────


def test_archive_validates_zero_errors(archive):
    """Archive passes offline validation with zero errors (warnings OK)."""
    report = validate_archive(archive)
    assert report.is_valid, (
        f"Archive validation failed with {len(report.errors)} errors: "
        + "; ".join(e.message for e in report.errors)
    )


# ── Ontology Structure ─────────────────────────────────────────────


def test_ontology_has_six_classes(archive):
    """Ontology defines exactly 6 OWL classes in bpkm namespace."""
    bpkm_classes = [
        s
        for s in archive.ontology.subjects(RDF.type, OWL.Class)
        if str(s).startswith(str(BPKM))
    ]
    assert len(bpkm_classes) == 6
    class_names = {str(c).split(":")[-1] for c in bpkm_classes}
    expected = {"Project", "Person", "Note", "Concept", "Task", "Milestone"}
    assert class_names == expected


# ── Shapes Structure ───────────────────────────────────────────────


def test_shapes_has_six_nodeshapes(archive):
    """Shapes file has 6 NodeShapes targeting the 6 OWL classes."""
    node_shapes = [
        s
        for s in archive.shapes.subjects(RDF.type, SH.NodeShape)
        if str(s).startswith(str(BPKM))
    ]
    assert len(node_shapes) == 6

    # Verify TaskShape and MilestoneShape target the right classes
    task_shape = BPKM.TaskShape
    milestone_shape = BPKM.MilestoneShape
    task_targets = list(archive.shapes.objects(task_shape, SH.targetClass))
    milestone_targets = list(
        archive.shapes.objects(milestone_shape, SH.targetClass)
    )
    assert BPKM.Task in task_targets
    assert BPKM.Milestone in milestone_targets


# ── Views Structure ────────────────────────────────────────────────


def test_views_has_all_viewspecs_and_queries(archive):
    """Views file has 18 ViewSpecs (6 types × 3 renderers) and 6 SavedQueries."""
    viewspecs = list(archive.views.subjects(RDF.type, SEMPKM.ViewSpec))
    assert len(viewspecs) == 18

    queries = list(archive.views.subjects(RDF.type, SEMPKM.SavedQuery))
    assert len(queries) == 6


# ── Seed Data ──────────────────────────────────────────────────────


def test_seed_has_task_and_milestone_instances(archive):
    """Seed graph contains 4 Tasks and 2 Milestones with correct data."""
    tasks = list(archive.seed.subjects(RDF.type, BPKM.Task))
    assert len(tasks) == 4

    milestones = list(archive.seed.subjects(RDF.type, BPKM.Milestone))
    assert len(milestones) == 2

    # Verify the overdue task has past dueDate and "todo" status
    overdue = BPKM["seed-task-fix-validation"]
    due_dates = list(archive.seed.objects(overdue, BPKM.dueDate))
    assert len(due_dates) == 1
    assert due_dates[0] == Literal("2026-03-10", datatype=XSD.date)

    statuses = list(archive.seed.objects(overdue, BPKM.taskStatus))
    assert len(statuses) == 1
    assert str(statuses[0]) == "todo"


def test_seed_has_inverse_pairs(archive):
    """Seed pre-populates both sides of inverseOf pairs (D154)."""
    # Project → hasProjectTasks
    project = BPKM["seed-project-sempkm"]
    project_tasks = list(archive.seed.objects(project, BPKM.hasProjectTasks))
    assert len(project_tasks) >= 1, "Project should have hasProjectTasks edges"

    # Person → hasAssignedTask
    alice = BPKM["seed-person-alice"]
    assigned = list(archive.seed.objects(alice, BPKM.hasAssignedTask))
    assert len(assigned) >= 1, "Alice should have hasAssignedTask edges"


# ── pyshacl Overdue Task Warning ───────────────────────────────────


def test_pyshacl_overdue_task_warning(archive):
    """pyshacl fires sh:Warning for the overdue task in seed data.

    This is the key risk-retirement test proving:
    - SPARQL-based validation rules with date arithmetic work
    - sh:severity sh:Warning on the NodeShape produces warnings (not errors)
    - allow_warnings=True keeps conforms=True
    """
    # Data graph = seed (instances) + ontology (class declarations)
    data_graph = archive.seed + archive.ontology
    # Shapes graph = shapes (structure) + rules (inference + validation)
    shapes_graph = archive.shapes + archive.rules

    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=shapes_graph,
        advanced=True,
        allow_infos=True,
        allow_warnings=True,
    )

    # With allow_warnings=True, conforms should be True
    assert conforms, f"Expected conforms=True with allow_warnings=True.\n{results_text}"

    # Find sh:Warning results
    warnings = list(
        results_graph.triples((None, SH.resultSeverity, SH.Warning))
    )
    assert len(warnings) >= 1, (
        f"Expected at least one overdue-task warning, got {len(warnings)}.\n"
        f"{results_text}"
    )

    # Verify warning references the overdue task and contains "overdue"
    warning_node = warnings[0][0]
    messages = [
        str(m) for m in results_graph.objects(warning_node, SH.resultMessage)
    ]
    assert any("overdue" in m.lower() for m in messages), (
        f"Warning message should contain 'overdue', got: {messages}"
    )
    focus_nodes = list(results_graph.objects(warning_node, SH.focusNode))
    assert BPKM["seed-task-fix-validation"] in focus_nodes, (
        f"Warning should focus on seed-task-fix-validation, got: {focus_nodes}"
    )


def test_pyshacl_no_warning_for_done_or_future_tasks():
    """pyshacl does NOT fire warnings for done tasks or future-due tasks.

    Constructs a minimal graph with:
    - A done task with a past dueDate (should not trigger)
    - A todo task with a future dueDate (should not trigger)
    """
    data_graph = Graph()
    data_graph.bind("bpkm", BPKM)
    data_graph.bind("xsd", XSD)

    # Done task with past due date — should NOT trigger
    done_task = BPKM["test-done-task"]
    data_graph.add((done_task, RDF.type, BPKM.Task))
    data_graph.add(
        (done_task, BPKM.dueDate, Literal("2020-01-01", datatype=XSD.date))
    )
    data_graph.add((done_task, BPKM.taskStatus, Literal("done")))

    # Future todo task — should NOT trigger
    future_task = BPKM["test-future-task"]
    data_graph.add((future_task, RDF.type, BPKM.Task))
    data_graph.add(
        (future_task, BPKM.dueDate, Literal("2099-12-31", datatype=XSD.date))
    )
    data_graph.add((future_task, BPKM.taskStatus, Literal("todo")))

    # Load only the rules file as shapes graph (contains the validation shape)
    shapes_graph = Graph()
    rules_path = MODEL_DIR / "rules" / "basic-pkm.ttl"
    shapes_graph.parse(str(rules_path), format="turtle")

    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=shapes_graph,
        advanced=True,
        allow_infos=True,
        allow_warnings=True,
    )

    assert conforms, f"Expected conforms=True.\n{results_text}"

    warnings = list(
        results_graph.triples((None, SH.resultSeverity, SH.Warning))
    )
    assert len(warnings) == 0, (
        f"Expected zero warnings for done/future tasks, got {len(warnings)}.\n"
        f"{results_text}"
    )
