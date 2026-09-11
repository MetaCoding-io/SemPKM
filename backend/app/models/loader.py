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


# Conventional documentation file when the manifest declares no docs entrypoint.
DEFAULT_DOCS_FILENAME = "README.md"

# Upper bound on the documentation file size (bytes). Docs are embedded in
# admin pages and rendered client-side, so keep them reasonably small.
MAX_DOCS_BYTES = 1024 * 1024


def resolve_docs_path(model_dir: Path, manifest: ManifestSchema) -> Path | None:
    """Locate the Markdown documentation file for a model archive.

    Resolution order:

    1. ``entrypoints.docs`` from the manifest, when declared. The file
       **must** exist -- a declared-but-missing docs file is an error so
       that install validation catches broken archives.
    2. A conventional ``README.md`` at the archive root, when present.
    3. ``None`` when the archive ships no documentation.

    Args:
        model_dir: Path to the model archive directory.
        manifest: The validated manifest with resolved entrypoint paths.

    Returns:
        Path to the documentation file, or None if the archive has none.

    Raises:
        FileNotFoundError: If ``entrypoints.docs`` is declared but missing.
        ValueError: If the declared path escapes the archive directory.
    """
    declared = manifest.entrypoints.docs
    if declared is not None:
        docs_path = (model_dir / declared)
        root = model_dir.resolve()
        try:
            docs_path.resolve().relative_to(root)
        except ValueError:
            raise ValueError(
                f"Documentation path '{declared}' escapes the model directory"
            ) from None
        if not docs_path.is_file():
            raise FileNotFoundError(
                f"Documentation file not found: {docs_path} "
                f"(declared as entrypoints.docs in manifest.yaml)"
            )
        return docs_path

    fallback = model_dir / DEFAULT_DOCS_FILENAME
    if fallback.is_file():
        return fallback
    return None


def load_model_docs(model_dir: Path, manifest: ManifestSchema) -> str | None:
    """Read the Markdown documentation for a model archive.

    See :func:`resolve_docs_path` for the resolution rules.

    Args:
        model_dir: Path to the model archive directory.
        manifest: The validated manifest with resolved entrypoint paths.

    Returns:
        The Markdown text, or None if the archive has no documentation.

    Raises:
        FileNotFoundError: If ``entrypoints.docs`` is declared but missing.
        ValueError: If the file escapes the archive or exceeds MAX_DOCS_BYTES.
    """
    docs_path = resolve_docs_path(model_dir, manifest)
    if docs_path is None:
        return None
    size = docs_path.stat().st_size
    if size > MAX_DOCS_BYTES:
        raise ValueError(
            f"Documentation file {docs_path.name} is {size} bytes; "
            f"the maximum is {MAX_DOCS_BYTES} bytes"
        )
    return docs_path.read_text(encoding="utf-8", errors="replace")


@dataclass
class ModelArchive:
    """A loaded Mental Model archive with all RDF graphs.

    Holds the parsed manifest and rdflib Graphs for each
    artifact type (ontology, shapes, views, and optionally seed),
    plus the optional Markdown documentation text.
    """

    manifest: ManifestSchema
    ontology: Graph
    shapes: Graph
    views: Graph
    seed: Graph | None
    rules: Graph | None
    docs: str | None = None


def load_archive(model_dir: Path, manifest: ManifestSchema) -> ModelArchive:
    """Load all JSON-LD files from a model archive into rdflib Graphs.

    Resolves entrypoint paths relative to model_dir and loads each
    JSON-LD file. Seed data is optional -- if the entrypoint is None
    or the file does not exist, seed is set to None. Markdown
    documentation is loaded from ``entrypoints.docs`` (required to
    exist when declared) or a root ``README.md`` when present.

    Args:
        model_dir: Path to the model archive directory.
        manifest: The validated manifest with resolved entrypoint paths.

    Returns:
        A ModelArchive with all loaded graphs.

    Raises:
        FileNotFoundError: If a required file (ontology, shapes, views)
            or a declared documentation file does not exist.
        ValueError: If any file contains remote @context URLs, or the
            documentation file is invalid.
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

    docs = load_model_docs(model_dir, manifest)

    return ModelArchive(
        manifest=manifest,
        ontology=ontology,
        shapes=shapes,
        views=views,
        seed=seed,
        rules=rules,
        docs=docs,
    )
