"""JSON-LD file loading for Mental Model archives.

Loads JSON-LD files from a model archive directory into rdflib
Graphs, with remote @context detection to prevent Docker
environment failures from remote context fetches.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph

from app.models.manifest import ManifestSchema


def load_rdf_file(file_path: Path) -> Graph:
    """Load an RDF file into an rdflib Graph, detecting format by extension.

    Supports Turtle (.ttl, .turtle) and JSON-LD (.jsonld, .json) files.

    Args:
        file_path: Path to the RDF file.

    Returns:
        An rdflib Graph containing the parsed triples.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file extension is not supported, or if a JSON-LD
            file contains remote @context URLs.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"RDF file not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix in (".ttl", ".turtle"):
        g = Graph()
        g.parse(str(file_path), format="turtle")
        return g
    elif suffix in (".jsonld", ".json"):
        return load_jsonld_file(file_path)
    else:
        raise ValueError(
            f"Unsupported RDF file extension '{suffix}' for {file_path}. "
            "Supported: .ttl, .turtle, .jsonld, .json"
        )


def load_jsonld_file(file_path: Path) -> Graph:
    """Load a JSON-LD file into an rdflib Graph.

    Args:
        file_path: Path to a .jsonld file.

    Returns:
        An rdflib Graph containing the parsed triples.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file contains remote @context URLs.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"JSON-LD file not found: {file_path}")

    # Check for remote @context URLs before parsing (Pitfall 1)
    _check_no_remote_context(file_path)

    g = Graph()
    g.parse(str(file_path), format="json-ld")
    return g


def _check_no_remote_context(file_path: Path) -> None:
    """Verify that a JSON-LD file uses only inline @context.

    Remote @context URLs cause rdflib to attempt HTTP fetches during
    parsing, which fails in Docker containers without internet access.

    Args:
        file_path: Path to the JSON-LD file to check.

    Raises:
        ValueError: If any @context value starts with http:// or https://.
    """
    with open(file_path) as f:
        data = json.load(f)

    _check_context_value(data, file_path)


def _check_context_value(data, file_path: Path) -> None:
    """Recursively check @context values for remote URLs."""
    if isinstance(data, dict):
        context = data.get("@context")
        if context is not None:
            _validate_context(context, file_path)
        # Check nested objects (e.g., @graph items)
        for value in data.values():
            if isinstance(value, (dict, list)):
                _check_context_value(value, file_path)
    elif isinstance(data, list):
        for item in data:
            _check_context_value(item, file_path)


def _validate_context(context, file_path: Path) -> None:
    """Validate a single @context value."""
    if isinstance(context, str):
        if context.startswith("http://") or context.startswith("https://"):
            raise ValueError(
                f"Remote @context URL found in {file_path}: '{context}'. "
                "All JSON-LD files must use inline @context only."
            )
    elif isinstance(context, list):
        for item in context:
            _validate_context(item, file_path)
    # dict contexts (inline mappings) are always valid


@dataclass
class ModelArchive:
    """A loaded Mental Model archive with all RDF graphs.

    Holds the parsed manifest and rdflib Graphs for each
    artifact type (ontology, shapes, views, and optionally seed).
    """

    manifest: ManifestSchema
    ontology: Graph
    shapes: Graph
    views: Graph
    seed: Graph | None
    rules: Graph | None


def load_archive(model_dir: Path, manifest: ManifestSchema) -> ModelArchive:
    """Load all JSON-LD files from a model archive into rdflib Graphs.

    Resolves entrypoint paths relative to model_dir and loads each
    JSON-LD file. Seed data is optional -- if the entrypoint is None
    or the file does not exist, seed is set to None.

    Args:
        model_dir: Path to the model archive directory.
        manifest: The validated manifest with resolved entrypoint paths.

    Returns:
        A ModelArchive with all loaded graphs.

    Raises:
        FileNotFoundError: If a required file (ontology, shapes, views)
            does not exist.
        ValueError: If any file contains remote @context URLs.
    """
    ontology = load_jsonld_file(model_dir / manifest.entrypoints.ontology)
    shapes = load_jsonld_file(model_dir / manifest.entrypoints.shapes)
    views = load_jsonld_file(model_dir / manifest.entrypoints.views)

    seed: Graph | None = None
    if manifest.entrypoints.seed is not None:
        seed_path = model_dir / manifest.entrypoints.seed
        if seed_path.exists():
            seed = load_jsonld_file(seed_path)

    rules: Graph | None = None
    if manifest.entrypoints.rules is not None:
        rules_path = model_dir / manifest.entrypoints.rules
        if rules_path.exists():
            rules = load_rdf_file(rules_path)

    return ModelArchive(
        manifest=manifest,
        ontology=ontology,
        shapes=shapes,
        views=views,
        seed=seed,
        rules=rules,
    )
