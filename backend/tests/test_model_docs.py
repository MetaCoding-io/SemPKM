"""Tests for Mental Model bundled documentation (issue #54).

Covers:
- ``entrypoints.docs`` manifest field: placeholder resolution and validation
- ``load_model_docs`` / ``load_archive``: declared file, README.md fallback,
  missing declared file, path traversal, size cap
- ``validate_archive``: missing-docs warning
- Every bundled model under ``models/`` ships documentation that loads
- ``ModelService.get_model_docs`` reads from the resolved model directory
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from rdflib import Graph

from app.models.loader import (
    MAX_DOCS_BYTES,
    ModelArchive,
    load_archive,
    load_model_docs,
    resolve_docs_path,
)
from app.models.manifest import ManifestEntrypoints, ManifestSchema, parse_manifest
from app.models.validator import validate_archive


MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_DIRS = sorted(
    p for p in MODELS_DIR.iterdir() if p.is_dir() and (p / "manifest.yaml").exists()
)

MINIMAL_ONTOLOGY = """{
  "@context": {"owl": "http://www.w3.org/2002/07/owl#",
               "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
               "t": "urn:sempkm:model:test-docs:"},
  "@graph": [{"@id": "t:Thing", "@type": "owl:Class", "rdfs:label": "Thing"}]
}"""
EMPTY_GRAPH = '{"@context": {}, "@graph": []}'


def _make_manifest(docs: str | None = None, **kwargs) -> ManifestSchema:
    return ManifestSchema(
        modelId="test-docs",
        version="1.0.0",
        name="Test Docs",
        namespace="urn:sempkm:model:test-docs:",
        entrypoints=ManifestEntrypoints(docs=docs, seed=None, **kwargs),
    )


def _write_minimal_archive(model_dir: Path, manifest_extra: str = "") -> None:
    """Create a minimal loadable archive on disk (no docs)."""
    (model_dir / "ontology").mkdir(parents=True)
    (model_dir / "shapes").mkdir()
    (model_dir / "views").mkdir()
    (model_dir / "ontology" / "test-docs.jsonld").write_text(MINIMAL_ONTOLOGY)
    (model_dir / "shapes" / "test-docs.jsonld").write_text(EMPTY_GRAPH)
    (model_dir / "views" / "test-docs.jsonld").write_text(EMPTY_GRAPH)
    (model_dir / "manifest.yaml").write_text(
        "modelId: test-docs\n"
        'version: "1.0.0"\n'
        'name: "Test Docs"\n'
        'namespace: "urn:sempkm:model:test-docs:"\n'
        "entrypoints:\n"
        '  ontology: "ontology/test-docs.jsonld"\n'
        '  shapes: "shapes/test-docs.jsonld"\n'
        '  views: "views/test-docs.jsonld"\n'
        "  seed: null\n" + manifest_extra
    )


# ---------------------------------------------------------------------------
# Manifest schema
# ---------------------------------------------------------------------------


class TestManifestDocsEntrypoint:
    def test_default_is_none(self):
        assert ManifestEntrypoints().docs is None
        assert _make_manifest().entrypoints.docs is None

    def test_placeholder_is_resolved(self):
        m = _make_manifest(docs="docs/{modelId}.md")
        assert m.entrypoints.docs == "docs/test-docs.md"

    def test_readme_declaration(self):
        assert _make_manifest(docs="README.md").entrypoints.docs == "README.md"

    @pytest.mark.parametrize("bad", ["docs.txt", "README", "docs/guide.html"])
    def test_non_markdown_rejected(self, bad):
        with pytest.raises(ValidationError, match="Markdown"):
            _make_manifest(docs=bad)

    @pytest.mark.parametrize("bad", ["/etc/README.md", "../README.md", "docs/../../x.md"])
    def test_absolute_or_traversal_rejected(self, bad):
        with pytest.raises(ValidationError, match="relative path"):
            _make_manifest(docs=bad)

    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="must not be empty"):
            _make_manifest(docs="   ")


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class TestLoadModelDocs:
    def test_no_docs_returns_none(self, tmp_path: Path):
        assert resolve_docs_path(tmp_path, _make_manifest()) is None
        assert load_model_docs(tmp_path, _make_manifest()) is None

    def test_readme_fallback_when_not_declared(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Hello\n\nfallback")
        assert load_model_docs(tmp_path, _make_manifest()) == "# Hello\n\nfallback"

    def test_declared_docs_file_is_read(self, tmp_path: Path):
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "test-docs.md").write_text("declared")
        (tmp_path / "README.md").write_text("ignored fallback")
        text = load_model_docs(tmp_path, _make_manifest(docs="docs/{modelId}.md"))
        assert text == "declared"

    def test_declared_but_missing_raises(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("present but not declared")
        with pytest.raises(FileNotFoundError, match="entrypoints.docs"):
            load_model_docs(tmp_path, _make_manifest(docs="docs/missing.md"))

    def test_symlink_escape_rejected(self, tmp_path: Path):
        outside = tmp_path / "outside.md"
        outside.write_text("secret")
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        try:
            (model_dir / "docs.md").symlink_to(outside)
        except OSError:
            pytest.skip("symlinks not supported")
        with pytest.raises(ValueError, match="escapes"):
            load_model_docs(model_dir, _make_manifest(docs="docs.md"))

    def test_oversized_docs_rejected(self, tmp_path: Path):
        (tmp_path / "README.md").write_bytes(b"x" * (MAX_DOCS_BYTES + 1))
        with pytest.raises(ValueError, match="maximum"):
            load_model_docs(tmp_path, _make_manifest(docs="README.md"))

    def test_load_archive_populates_docs(self, tmp_path: Path):
        model_dir = tmp_path / "test-docs"
        _write_minimal_archive(model_dir, manifest_extra='  docs: "README.md"\n')
        (model_dir / "README.md").write_text("# Test Docs\n")
        manifest = parse_manifest(model_dir)
        archive = load_archive(model_dir, manifest)
        assert archive.docs == "# Test Docs\n"

    def test_load_archive_fails_when_declared_docs_missing(self, tmp_path: Path):
        """Install validation must fail for a declared-but-missing docs file."""
        model_dir = tmp_path / "test-docs"
        _write_minimal_archive(model_dir, manifest_extra='  docs: "README.md"\n')
        manifest = parse_manifest(model_dir)
        with pytest.raises(FileNotFoundError):
            load_archive(model_dir, manifest)

    def test_load_archive_without_docs_is_none(self, tmp_path: Path):
        model_dir = tmp_path / "test-docs"
        _write_minimal_archive(model_dir)
        archive = load_archive(model_dir, parse_manifest(model_dir))
        assert archive.docs is None


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def _archive(docs: str | None) -> ModelArchive:
    g = Graph()
    g.parse(data=MINIMAL_ONTOLOGY, format="json-ld")
    return ModelArchive(
        manifest=_make_manifest(),
        ontology=g,
        shapes=Graph(),
        views=Graph(),
        seed=None,
        rules=None,
        docs=docs,
    )


class TestValidatorDocsWarning:
    def test_missing_docs_is_warning_not_error(self):
        report = validate_archive(_archive(None))
        assert report.is_valid
        rules = [w.rule for w in report.warnings]
        assert "missing-docs" in rules

    def test_blank_docs_is_warning(self):
        report = validate_archive(_archive("   \n"))
        assert "missing-docs" in [w.rule for w in report.warnings]

    def test_present_docs_no_warning(self):
        report = validate_archive(_archive("# Docs"))
        assert "missing-docs" not in [w.rule for w in report.warnings]


# ---------------------------------------------------------------------------
# Bundled models
# ---------------------------------------------------------------------------


class TestBundledModelsShipDocs:
    @pytest.mark.parametrize("model_dir", MODEL_DIRS, ids=[d.name for d in MODEL_DIRS])
    def test_bundled_model_declares_and_ships_docs(self, model_dir: Path):
        manifest = parse_manifest(model_dir)
        assert manifest.entrypoints.docs == "README.md"
        docs = load_model_docs(model_dir, manifest)
        assert docs is not None and docs.strip()
        # Every README opens with a level-1 heading naming the model
        first_line = docs.lstrip().splitlines()[0]
        assert first_line.startswith("# "), f"{model_dir.name}: README must start with an H1"
        assert f"`{manifest.modelId}`" in docs, f"{model_dir.name}: README must mention its model ID"

    @pytest.mark.parametrize("model_dir", MODEL_DIRS, ids=[d.name for d in MODEL_DIRS])
    def test_bundled_archive_loads_with_docs(self, model_dir: Path):
        manifest = parse_manifest(model_dir)
        archive = load_archive(model_dir, manifest)
        assert archive.docs and archive.docs.startswith("# ")
        report = validate_archive(archive)
        assert "missing-docs" not in [w.rule for w in report.warnings]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class TestModelServiceGetDocs:
    def _service(self):
        from app.services.models import ModelService

        return ModelService(
            triplestore_client=MagicMock(),
            event_store=MagicMock(),
            prefix_registry=MagicMock(),
        )

    def test_returns_none_when_dir_missing(self):
        with patch("app.models.paths.resolve_model_dir", return_value=None):
            assert self._service().get_model_docs("nope") is None

    def test_reads_docs_from_resolved_dir(self, tmp_path: Path):
        model_dir = tmp_path / "test-docs"
        _write_minimal_archive(model_dir, manifest_extra='  docs: "README.md"\n')
        (model_dir / "README.md").write_text("# From disk\n")
        with patch("app.models.paths.resolve_model_dir", return_value=model_dir):
            assert self._service().get_model_docs("test-docs") == "# From disk\n"

    def test_broken_docs_declaration_yields_none(self, tmp_path: Path):
        model_dir = tmp_path / "test-docs"
        _write_minimal_archive(model_dir, manifest_extra='  docs: "README.md"\n')
        with patch("app.models.paths.resolve_model_dir", return_value=model_dir):
            assert self._service().get_model_docs("test-docs") is None

    def test_reads_bundled_basic_pkm(self):
        basic = MODELS_DIR / "basic-pkm"
        if not basic.exists():
            pytest.skip("basic-pkm not found")
        with patch("app.models.paths.resolve_model_dir", return_value=basic):
            docs = self._service().get_model_docs("basic-pkm")
        assert docs and docs.startswith("# Basic PKM")


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------


class TestModelDocsEndpoint:
    """GET /api/models/{model_id}/docs serves the bundled Markdown."""

    def _app(self, installed_ids: list[str], docs: str | None):
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        from app.auth.dependencies import get_current_user
        from app.dependencies import get_model_service
        from app.models.router import router as models_router

        service = MagicMock()
        service.list_models = AsyncMock(
            return_value=[SimpleNamespace(model_id=mid) for mid in installed_ids]
        )
        service.get_model_docs = MagicMock(return_value=docs)

        test_app = FastAPI()
        test_app.include_router(models_router)
        test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="u1")
        test_app.dependency_overrides[get_model_service] = lambda: service
        return test_app

    async def test_returns_markdown(self):
        from httpx import ASGITransport, AsyncClient

        app = self._app(["basic-pkm"], "# Basic PKM\n\nHello <b>world</b> & co")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            resp = await c.get("/api/models/basic-pkm/docs")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")
        assert resp.text == "# Basic PKM\n\nHello <b>world</b> & co"

    async def test_404_when_not_installed(self):
        from httpx import ASGITransport, AsyncClient

        app = self._app([], "# x")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            resp = await c.get("/api/models/nope/docs")
        assert resp.status_code == 404

    async def test_404_when_model_has_no_docs(self):
        from httpx import ASGITransport, AsyncClient

        app = self._app(["bare"], None)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            resp = await c.get("/api/models/bare/docs")
        assert resp.status_code == 404
        assert "no documentation" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# User guide mirrors (docs/guide/model-*.md generated by scripts/sync-model-docs.py)
# ---------------------------------------------------------------------------


def _load_sync_script():
    import importlib.util

    script = MODELS_DIR.parent / "scripts" / "sync-model-docs.py"
    spec = importlib.util.spec_from_file_location("sync_model_docs", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestGuideMirrors:
    def test_mirrors_are_in_sync(self):
        """docs/guide/model-*.md must match models/*/README.md exactly."""
        sync = _load_sync_script()
        stale = sync.stale_mirrors()
        assert not stale, (
            "Stale model documentation mirrors: "
            + ", ".join(str(p.relative_to(sync.REPO_ROOT)) for p in stale)
            + " -- run: python3 scripts/sync-model-docs.py"
        )

    def test_every_bundled_model_has_a_mirror(self):
        sync = _load_sync_script()
        for d in MODEL_DIRS:
            mirror = sync.GUIDE_DIR / f"model-{d.name}.md"
            assert mirror.is_file(), f"missing guide mirror for {d.name}"
            text = mirror.read_text(encoding="utf-8")
            assert text.startswith("<!-- GENERATED FILE"), d.name
            assert f"models/{d.name}/README.md" in text
            assert "39-mental-model-catalog.md" in text

    def test_mirrors_are_listed_in_all_chapter_lists(self):
        """Each mirror must appear in the public sidebar, the guide README, and GUIDE_SECTIONS."""
        from app.shell.router import GUIDE_SECTIONS

        root = MODELS_DIR.parent
        sidebar = (root / "docs" / "guide" / "index.html").read_text(encoding="utf-8")
        readme = (root / "docs" / "guide" / "README.md").read_text(encoding="utf-8")
        listed = {
            item["filename"]
            for section in GUIDE_SECTIONS
            if section["type"] == "chapters"
            for item in section["items"]
        }
        for d in MODEL_DIRS:
            fn = f"model-{d.name}.md"
            assert f'data-file="{fn}"' in sidebar, f"{fn} missing from docs/guide/index.html"
            assert f"({fn})" in readme, f"{fn} missing from docs/guide/README.md"
            assert fn in listed, f"{fn} missing from GUIDE_SECTIONS"
