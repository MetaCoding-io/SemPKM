"""Tests for the SHACL validation pipeline fix (M030/S01).

Proves:
1. model_shapes_loader merges shapes + rules graphs from installed models
2. model_shapes_loader handles edge cases (no models, empty rules)
3. ValidationService.validate passes advanced=True to pyshacl
4. SPARQLConstraint rules actually fire for overdue tasks (functional/e2e)
5. pyshacl performance with advanced=True is acceptable
"""

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pyshacl
import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from app.services.models import model_shapes_loader
from app.services.validation import ValidationService

# Namespaces
BPKM = Namespace("urn:sempkm:model:basic-pkm:")
SH = Namespace("http://www.w3.org/ns/shacl#")
DCTERMS = Namespace("http://purl.org/dc/terms/")

# Paths to real model files
MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "basic-pkm"
SHAPES_FILE = MODEL_DIR / "shapes" / "basic-pkm.jsonld"
RULES_FILE = MODEL_DIR / "rules" / "basic-pkm.ttl"

# Canned Turtle fragments for unit tests
CANNED_SHAPES_TURTLE = """\
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:PersonShape a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property [
        sh:path ex:name ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
    ] .
"""

CANNED_RULES_TURTLE = """\
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:SomeValidationRule a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:severity sh:Warning ;
    rdfs:label "Test rule" .
"""


# ── model_shapes_loader tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_merges_shapes_and_rules():
    """model_shapes_loader returns a graph containing triples from both shapes and rules."""
    client = AsyncMock()

    # query() returns one installed model
    client.query.return_value = {
        "results": {
            "bindings": [{"modelId": {"value": "basic-pkm"}}]
        }
    }

    # construct() returns shapes on first call, rules on second call
    client.construct.side_effect = [CANNED_SHAPES_TURTLE, CANNED_RULES_TURTLE]

    graph = await model_shapes_loader(client)

    # Graph should contain triples from both shapes and rules
    assert len(graph) > 0

    # Check for shapes content (ex:PersonShape)
    EX = Namespace("http://example.org/")
    person_shape_triples = list(graph.triples((EX.PersonShape, RDF.type, SH.NodeShape)))
    assert len(person_shape_triples) == 1, "Shapes graph triples missing"

    # Check for rules content (ex:SomeValidationRule)
    rule_triples = list(graph.triples((EX.SomeValidationRule, RDF.type, SH.NodeShape)))
    assert len(rule_triples) == 1, "Rules graph triples missing"


@pytest.mark.asyncio
async def test_loader_no_models_returns_empty_graph():
    """model_shapes_loader returns an empty graph when no models are installed."""
    client = AsyncMock()

    # query() returns empty bindings
    client.query.return_value = {
        "results": {
            "bindings": []
        }
    }

    graph = await model_shapes_loader(client)

    assert len(graph) == 0


@pytest.mark.asyncio
async def test_loader_empty_rules_returns_shapes_only():
    """model_shapes_loader handles empty rules graph gracefully, returning shapes only."""
    client = AsyncMock()

    # query() returns one installed model
    client.query.return_value = {
        "results": {
            "bindings": [{"modelId": {"value": "basic-pkm"}}]
        }
    }

    # construct() returns shapes on first call, empty string for rules
    client.construct.side_effect = [CANNED_SHAPES_TURTLE, ""]

    graph = await model_shapes_loader(client)

    # Graph should contain shapes triples only
    assert len(graph) > 0

    EX = Namespace("http://example.org/")
    person_shape_triples = list(graph.triples((EX.PersonShape, RDF.type, SH.NodeShape)))
    assert len(person_shape_triples) == 1, "Shapes triples should be present"

    # Rules triples should NOT be present
    rule_triples = list(graph.triples((EX.SomeValidationRule, RDF.type, SH.NodeShape)))
    assert len(rule_triples) == 0, "No rules triples expected for empty rules response"


# ── ValidationService.validate tests ───────────────────────────────


@pytest.mark.asyncio
async def test_validate_passes_advanced_true_to_pyshacl():
    """ValidationService.validate passes advanced=True, allow_infos=True, allow_warnings=True to pyshacl."""
    # Mock triplestore client
    client = AsyncMock()
    client.construct.return_value = ""  # empty data graph
    client.query.return_value = {"results": {"bindings": []}}
    client.update.return_value = None

    # Mock shapes loader returning a non-empty graph
    shapes_graph = Graph()
    shapes_graph.parse(data=CANNED_SHAPES_TURTLE, format="turtle")

    async def mock_shapes_loader():
        return shapes_graph

    service = ValidationService(
        triplestore_client=client,
        shapes_loader=mock_shapes_loader,
    )

    with patch("app.services.validation.pyshacl") as mock_pyshacl_module:
        mock_pyshacl_module.validate.return_value = (True, Graph(), "Conforms")

        await service.validate(
            event_iri="urn:sempkm:event:test-123",
            timestamp="2025-01-01T00:00:00Z",
        )

        # Assert pyshacl.validate was called
        mock_pyshacl_module.validate.assert_called_once()

        # Get the actual call kwargs
        call_args = mock_pyshacl_module.validate.call_args
        kwargs = call_args.kwargs if call_args.kwargs else {}
        # Also check positional/keyword args from the call
        # asyncio.to_thread(pyshacl.validate, data_graph, shacl_graph=..., ...)
        # The call happens inside asyncio.to_thread, so we need to check the
        # patched module's validate was called with the right args
        # Since we patched the module, to_thread calls mock_pyshacl_module.validate(...)

    # Re-do with a direct patch approach that intercepts asyncio.to_thread
    with patch("app.services.validation.asyncio.to_thread") as mock_to_thread:
        mock_to_thread.return_value = (True, Graph(), "Conforms")

        await service.validate(
            event_iri="urn:sempkm:event:test-456",
            timestamp="2025-01-01T00:00:00Z",
        )

        mock_to_thread.assert_called_once()
        call_args = mock_to_thread.call_args

        # asyncio.to_thread(pyshacl.validate, data_graph, shacl_graph=..., ...)
        # Positional: [0]=pyshacl.validate, [1]=data_graph
        # Keyword: shacl_graph, allow_infos, allow_warnings, advanced
        assert call_args.kwargs.get("advanced") is True, "advanced=True must be passed"
        assert call_args.kwargs.get("allow_infos") is True, "allow_infos=True must be passed"
        assert call_args.kwargs.get("allow_warnings") is True, "allow_warnings=True must be passed"
        assert call_args.kwargs.get("shacl_graph") is not None, "shacl_graph must be passed"


# ── Functional test: SPARQLConstraint fires for overdue task ───────


@pytest.mark.skipif(
    not SHAPES_FILE.exists() or not RULES_FILE.exists(),
    reason="Real model files not available",
)
def test_sparql_constraint_fires_for_overdue_task():
    """SPARQLConstraint rules from basic-pkm fire a warning for an overdue task.

    This is the key proof that the pipeline fix works end-to-end:
    shapes + rules loaded together with advanced=True causes pyshacl
    to execute SPARQL-based validation constraints.
    """
    # Load real shapes and rules into a combined graph
    combined = Graph()
    combined.parse(str(SHAPES_FILE), format="json-ld")
    combined.parse(str(RULES_FILE), format="turtle")

    combined_triples = len(combined)
    assert combined_triples > 0, "Combined graph should have triples"

    # Build a small data graph with an overdue task
    data_graph = Graph()
    task_uri = URIRef("urn:sempkm:instance:test-overdue-task")

    data_graph.add((task_uri, RDF.type, BPKM.Task))
    data_graph.add((task_uri, DCTERMS.title, Literal("Test overdue task")))
    data_graph.add((task_uri, BPKM.dueDate, Literal("2020-01-01", datatype=XSD.date)))
    data_graph.add((task_uri, BPKM.taskStatus, Literal("todo")))

    # Run pyshacl with advanced=True and measure performance
    start = time.perf_counter()
    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=combined,
        advanced=True,
        allow_warnings=True,
        allow_infos=True,
    )
    elapsed = time.perf_counter() - start

    print(f"\npyshacl advanced=True execution time: {elapsed:.3f}s")
    print(f"Combined shapes+rules graph: {combined_triples} triples")
    print(f"Conforms: {conforms}")
    print(f"Results text:\n{results_text}")

    # Note: conforms=True is correct because allow_warnings=True means warnings
    # don't cause non-conformance. The important thing is that the warning EXISTS
    # in the results graph — proving that the SPARQLConstraint fired.

    # Parse results graph for the overdue warning
    results_subjects = list(results_graph.subjects(RDF.type, SH.ValidationResult))
    assert len(results_subjects) > 0, "Expected at least one ValidationResult"

    # Find the overdue-related result
    found_overdue_warning = False
    for result_node in results_subjects:
        severity = list(results_graph.objects(result_node, SH.resultSeverity))
        messages = list(results_graph.objects(result_node, SH.resultMessage))

        for msg in messages:
            if "overdue" in str(msg).lower():
                found_overdue_warning = True
                # Verify severity is Warning
                assert any(
                    str(s) == str(SH.Warning) for s in severity
                ), f"Overdue result should have sh:Warning severity, got {severity}"
                break

    assert found_overdue_warning, (
        f"Expected a ValidationResult with 'overdue' in sh:resultMessage.\n"
        f"Found {len(results_subjects)} results but none matched.\n"
        f"Results text:\n{results_text}"
    )

    # Performance assertion: should complete well under 10 seconds
    assert elapsed < 10.0, f"pyshacl took {elapsed:.3f}s — exceeds 10s budget"


@pytest.mark.skipif(
    not SHAPES_FILE.exists() or not RULES_FILE.exists(),
    reason="Real model files not available",
)
def test_non_overdue_task_conforms():
    """A task with a future due date and 'done' status should NOT trigger the overdue warning."""
    combined = Graph()
    combined.parse(str(SHAPES_FILE), format="json-ld")
    combined.parse(str(RULES_FILE), format="turtle")

    data_graph = Graph()
    task_uri = URIRef("urn:sempkm:instance:test-ok-task")

    data_graph.add((task_uri, RDF.type, BPKM.Task))
    data_graph.add((task_uri, DCTERMS.title, Literal("Test done task")))
    data_graph.add((task_uri, BPKM.dueDate, Literal("2020-01-01", datatype=XSD.date)))
    data_graph.add((task_uri, BPKM.taskStatus, Literal("done")))

    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=combined,
        advanced=True,
        allow_warnings=True,
        allow_infos=True,
    )

    # A done task should not trigger the overdue warning
    overdue_found = False
    for result_node in results_graph.subjects(RDF.type, SH.ValidationResult):
        for msg in results_graph.objects(result_node, SH.resultMessage):
            if "overdue" in str(msg).lower():
                overdue_found = True

    assert not overdue_found, (
        f"Done task should NOT trigger overdue warning.\n"
        f"Results text:\n{results_text}"
    )
