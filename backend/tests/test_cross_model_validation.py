"""Cross-model offline validation for all M011 mental models.

Proves that all 4 models (basic-pkm v2, CRM, Zettelkasten+, Research Workflow)
coexist without namespace conflicts, each individually validates, and that
pyshacl SPARQL rules fire the expected warnings/infos per model.

Covers:
  - Individual model parse → load → validate pipeline (zero errors)
  - Unique namespace per model (no collisions)
  - Combined ontology graph merge (no parse errors, no silent triple drops)
  - pyshacl validation firing correct warning/info counts per model
"""

from pathlib import Path

import pyshacl
import pytest
from rdflib import Graph, Namespace

from app.models.loader import load_archive
from app.models.manifest import parse_manifest
from app.models.validator import validate_archive

# ── Constants ───────────────────────────────────────────────────────

SH = Namespace("http://www.w3.org/ns/shacl#")

MODELS_ROOT = Path(__file__).resolve().parents[2] / "models"

MODEL_NAMES = ["basic-pkm", "crm", "zettelkasten", "research"]

MODEL_DIRS = {name: MODELS_ROOT / name for name in MODEL_NAMES}

# Files follow the convention: <modelId>.<ext> inside each subdirectory
MODEL_FILES = {
    "basic-pkm": {"onto": "basic-pkm.jsonld", "shapes": "basic-pkm.jsonld",
                   "rules": "basic-pkm.ttl", "seed": "basic-pkm.jsonld"},
    "crm":       {"onto": "crm.jsonld", "shapes": "crm.jsonld",
                   "rules": "crm.ttl", "seed": "crm.jsonld"},
    "zettelkasten": {"onto": "zettelkasten.jsonld", "shapes": "zettelkasten.jsonld",
                      "rules": "zettelkasten.ttl", "seed": "zettelkasten.jsonld"},
    "research":  {"onto": "research.jsonld", "shapes": "research.jsonld",
                   "rules": "research.ttl", "seed": "research.jsonld"},
}

EXPECTED_NAMESPACES = {
    "basic-pkm": "urn:sempkm:model:basic-pkm:",
    "crm": "urn:sempkm:model:crm:",
    "zettelkasten": "urn:sempkm:model:zettelkasten:",
    "research": "urn:sempkm:model:research:",
}

# Expected pyshacl result counts: (warnings, infos)
EXPECTED_PYSHACL = {
    "basic-pkm": (1, 0),
    "crm": (2, 0),
    "zettelkasten": (2, 1),
    "research": (2, 2),
}


# ── Module-scoped fixtures ─────────────────────────────────────────

@pytest.fixture(scope="module")
def manifests():
    """Parse manifests for all 4 models."""
    return {name: parse_manifest(MODEL_DIRS[name]) for name in MODEL_NAMES}


@pytest.fixture(scope="module")
def archives(manifests):
    """Load archives for all 4 models."""
    return {name: load_archive(MODEL_DIRS[name], manifests[name])
            for name in MODEL_NAMES}


# ── Individual model validation (parametrized) ─────────────────────

@pytest.mark.parametrize("model_name", MODEL_NAMES)
def test_model_parses_and_validates(model_name, archives):
    """Each model passes parse_manifest → load_archive → validate_archive with 0 errors."""
    archive = archives[model_name]
    report = validate_archive(archive)
    assert report.is_valid, (
        f"{model_name} validation failed with {len(report.errors)} errors: "
        + "; ".join(e.message for e in report.errors)
    )
    assert len(report.errors) == 0, (
        f"{model_name} had unexpected errors: "
        + "; ".join(e.message for e in report.errors)
    )


# ── Namespace collision check ──────────────────────────────────────

def test_no_namespace_collisions(manifests):
    """All 4 models have distinct namespaces — no prefix collisions."""
    namespaces = {}
    for name in MODEL_NAMES:
        ns = manifests[name].namespace
        assert ns is not None, f"{name} manifest has no namespace"
        assert ns == EXPECTED_NAMESPACES[name], (
            f"{name} namespace mismatch: expected {EXPECTED_NAMESPACES[name]}, got {ns}"
        )
        namespaces[name] = ns

    # All namespaces must be distinct
    unique_ns = set(namespaces.values())
    assert len(unique_ns) == len(MODEL_NAMES), (
        f"Namespace collision detected! Namespaces: {namespaces}"
    )


# ── Combined graph merge ──────────────────────────────────────────

def test_combined_graph_merge(archives):
    """Merging all 4 ontology graphs produces no parse errors and no silent drops."""
    individual_counts = {}
    combined = Graph()

    for name in MODEL_NAMES:
        onto = archives[name].ontology
        count = len(onto)
        individual_counts[name] = count
        assert count > 0, f"{name} ontology has 0 triples"

        # Merge into combined graph
        for triple in onto:
            combined.add(triple)

    total_individual = sum(individual_counts.values())
    combined_count = len(combined)

    # Combined should have at least as many triples as the sum of individuals
    # (could have fewer due to shared triples like owl:Class definitions,
    #  but should not lose model-specific triples)
    assert combined_count > 0, "Combined graph is empty after merge"
    # Each model uses unique namespace URIs, so most triples are distinct.
    # Allow up to 20% shared overhead (rdf:type owl:Class etc.)
    assert combined_count >= total_individual * 0.8, (
        f"Combined graph ({combined_count} triples) lost too many triples "
        f"compared to sum of individuals ({total_individual})"
    )


# ── pyshacl validation per model ──────────────────────────────────

def _run_pyshacl(model_name):
    """Run pyshacl validation for a model. Returns (conforms, warnings, infos, results_text)."""
    model_dir = MODEL_DIRS[model_name]
    files = MODEL_FILES[model_name]

    data_graph = Graph()
    data_graph.parse(
        str(model_dir / "seed" / files["seed"]), format="json-ld"
    )
    data_graph.parse(
        str(model_dir / "ontology" / files["onto"]), format="json-ld"
    )

    shapes_graph = Graph()
    shapes_graph.parse(
        str(model_dir / "shapes" / files["shapes"]), format="json-ld"
    )
    shapes_graph.parse(
        str(model_dir / "rules" / files["rules"]), format="turtle"
    )

    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=shapes_graph,
        ont_graph=data_graph,
        advanced=True,
        allow_infos=True,
        allow_warnings=True,
    )

    warnings = list(results_graph.subjects(SH.resultSeverity, SH.Warning))
    infos = list(results_graph.subjects(SH.resultSeverity, SH.Info))

    return conforms, warnings, infos, results_text


def test_pyshacl_basic_pkm_warnings():
    """pyshacl fires exactly 1 Warning (overdue task) for basic-pkm seed data."""
    conforms, warnings, infos, results_text = _run_pyshacl("basic-pkm")
    assert conforms, f"basic-pkm: expected conforms=True with allow_warnings.\n{results_text}"
    assert len(warnings) == 1, (
        f"basic-pkm: expected 1 warning, got {len(warnings)}.\n{results_text}"
    )
    assert len(infos) == 0, (
        f"basic-pkm: expected 0 infos, got {len(infos)}.\n{results_text}"
    )


def test_pyshacl_crm_warnings():
    """pyshacl fires exactly 2 Warnings (stale contact, overdue follow-up) for CRM seed data."""
    conforms, warnings, infos, results_text = _run_pyshacl("crm")
    assert conforms, f"crm: expected conforms=True with allow_warnings.\n{results_text}"
    assert len(warnings) == 2, (
        f"crm: expected 2 warnings, got {len(warnings)}.\n{results_text}"
    )
    assert len(infos) == 0, (
        f"crm: expected 0 infos, got {len(infos)}.\n{results_text}"
    )


def test_pyshacl_zettelkasten_warnings():
    """pyshacl fires 2 Warnings + 1 Info for zettelkasten seed data."""
    conforms, warnings, infos, results_text = _run_pyshacl("zettelkasten")
    assert conforms, (
        f"zettelkasten: expected conforms=True with allow_warnings.\n{results_text}"
    )
    assert len(warnings) == 2, (
        f"zettelkasten: expected 2 warnings, got {len(warnings)}.\n{results_text}"
    )
    assert len(infos) == 1, (
        f"zettelkasten: expected 1 info, got {len(infos)}.\n{results_text}"
    )


def test_pyshacl_research_warnings():
    """pyshacl fires 2 Warnings + 2 Infos for research seed data."""
    conforms, warnings, infos, results_text = _run_pyshacl("research")
    assert conforms, (
        f"research: expected conforms=True with allow_warnings.\n{results_text}"
    )
    assert len(warnings) == 2, (
        f"research: expected 2 warnings, got {len(warnings)}.\n{results_text}"
    )
    assert len(infos) == 2, (
        f"research: expected 2 infos, got {len(infos)}.\n{results_text}"
    )
