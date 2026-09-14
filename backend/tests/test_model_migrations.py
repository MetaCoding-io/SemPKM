"""Unit tests for versioned Mental Model migrations.

Covers the three layers the feature is built from:

1. Parsing and discovery -- a malformed migration must fail loudly at install
   time rather than at the first upgrade, and the chain a version bump selects
   must be exactly the migrations between the two versions.
2. Delta compilation -- each step kind turns into the right concrete triples,
   and compilation never issues anything but a SELECT.
3. Orchestration -- ``ModelService.upgrade`` refreshes artifacts, applies each
   pending migration as an event, records the ledger, and resumes rather than
   repeating work after a partial failure.

Uses a fake triplestore client so the tests run without RDF4J.
"""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from app.models.loader import ModelArchive
from app.models.manifest import ManifestSchema, parse_manifest
from app.models.migrations import (
    MigrationCompiler,
    MigrationError,
    MigrationTooLargeError,
    discover_migrations,
    expand_term,
    parse_migration_spec,
    parse_triple_pattern,
    select_chain,
    validate_fragment,
)
from app.models.registry import ModelGraphs
from app.services.models import ModelService

MODEL_ID = "test-model"
NS = f"urn:sempkm:model:{MODEL_ID}:"
PREFIXES = {"tm": NS}


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def write_manifest(model_dir: Path, version: str, *, migrations: str | None = None):
    """Write a minimal but valid manifest.yaml into a model directory."""
    manifest = {
        "modelId": MODEL_ID,
        "version": version,
        "name": "Test Model",
        "description": "Fixture model",
        "namespace": NS,
        "prefixes": {"tm": NS},
        "entrypoints": {
            "ontology": "ontology/{modelId}.jsonld",
            "shapes": "shapes/{modelId}.jsonld",
            "views": "views/{modelId}.jsonld",
            "seed": None,
        },
    }
    if migrations is not None:
        manifest["entrypoints"]["migrations"] = migrations
    (model_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest))
    return manifest


def write_migration(migrations_dir: Path, version: str, steps: list[dict], **extra):
    """Write one migration file named for its target version."""
    migrations_dir.mkdir(parents=True, exist_ok=True)
    body = {"version": version, "steps": steps}
    body.update(extra)
    path = migrations_dir / f"{version}.yaml"
    path.write_text(yaml.safe_dump(body, sort_keys=False))
    return path


class FakeClient:
    """A triplestore client that answers SELECTs from a canned row table.

    Records every query and update so a test can assert that compilation is
    read-only, and that an upgrade issued the writes it should have.
    """

    def __init__(self, rows: list[list[dict]] | None = None):
        self._rows = list(rows or [])
        self.queries: list[str] = []
        self.updates: list[str] = []
        self.constructs: list[str] = []
        self.construct_result = b""

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        bindings = self._rows.pop(0) if self._rows else []
        return {"results": {"bindings": bindings}}

    async def update(self, sparql: str) -> None:
        self.updates.append(sparql)

    async def construct(self, sparql: str) -> bytes:
        self.constructs.append(sparql)
        return self.construct_result


def uri_row(**bindings) -> dict:
    return {name: {"type": "uri", "value": value} for name, value in bindings.items()}


@pytest.fixture
def model_dir(tmp_path) -> Path:
    directory = tmp_path / MODEL_ID
    directory.mkdir()
    return directory


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestParseMigrationSpec:
    def test_parses_a_well_formed_migration(self, tmp_path):
        path = write_migration(
            tmp_path,
            "2.0.0",
            [{"id": "rename", "kind": "rename_class", "from": "tm:A", "to": "tm:B"}],
            description="Rename A to B",
        )
        spec = parse_migration_spec(path)

        assert spec.version == "2.0.0"
        assert spec.description == "Rename A to B"
        assert len(spec.steps) == 1
        assert spec.steps[0].kind == "rename_class"
        assert spec.steps[0].params == {"from": "tm:A", "to": "tm:B"}

    def test_filename_must_be_a_semver(self, tmp_path):
        path = tmp_path / "add-bookmarks.yaml"
        path.write_text("version: '2.0.0'\nsteps: []\n")
        with pytest.raises(MigrationError, match="semver target version"):
            parse_migration_spec(path)

    def test_declared_version_must_match_the_filename(self, tmp_path):
        path = tmp_path / "2.0.0.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "version": "3.0.0",
                    "steps": [
                        {"id": "x", "kind": "drop_property", "property": "tm:p"}
                    ],
                }
            )
        )
        with pytest.raises(MigrationError, match="must match"):
            parse_migration_spec(path)

    def test_rejects_an_unknown_step_kind(self, tmp_path):
        path = write_migration(tmp_path, "2.0.0", [{"id": "x", "kind": "frobnicate"}])
        with pytest.raises(MigrationError, match="unknown kind"):
            parse_migration_spec(path)

    def test_rejects_a_typo_in_a_step_key(self, tmp_path):
        """A typo must fail loudly, not silently do nothing to user data."""
        path = write_migration(
            tmp_path,
            "2.0.0",
            [{"id": "x", "kind": "rename_class", "from": "tm:A", "too": "tm:B"}],
        )
        with pytest.raises(MigrationError) as exc:
            parse_migration_spec(path)
        assert "missing required keys: to" in str(exc.value)

    def test_rejects_duplicate_step_ids(self, tmp_path):
        path = write_migration(
            tmp_path,
            "2.0.0",
            [
                {"id": "x", "kind": "drop_property", "property": "tm:p"},
                {"id": "x", "kind": "drop_property", "property": "tm:q"},
            ],
        )
        with pytest.raises(MigrationError, match="duplicate step id"):
            parse_migration_spec(path)

    def test_rejects_empty_steps(self, tmp_path):
        path = write_migration(tmp_path, "2.0.0", [])
        with pytest.raises(MigrationError, match="non-empty 'steps'"):
            parse_migration_spec(path)

    def test_set_default_needs_exactly_one_value_form(self, tmp_path):
        both = write_migration(
            tmp_path,
            "2.0.0",
            [
                {
                    "id": "x",
                    "kind": "set_default",
                    "class": "tm:A",
                    "property": "tm:p",
                    "value": "a",
                    "value_iri": "tm:B",
                }
            ],
        )
        with pytest.raises(MigrationError, match="exactly one of"):
            parse_migration_spec(both)

    def test_sparql_step_needs_a_delete_or_insert(self, tmp_path):
        path = write_migration(
            tmp_path, "2.0.0", [{"id": "x", "kind": "sparql", "where": "?s ?p ?o ."}]
        )
        with pytest.raises(MigrationError, match="at least one of"):
            parse_migration_spec(path)


# ---------------------------------------------------------------------------
# Discovery and chain selection
# ---------------------------------------------------------------------------


class TestDiscovery:
    def test_no_migrations_entrypoint_means_no_migrations(self, model_dir):
        write_manifest(model_dir, "1.0.0")
        manifest = parse_manifest(model_dir)
        assert discover_migrations(model_dir, manifest) == []

    def test_discovers_and_orders_by_semver(self, model_dir):
        write_manifest(model_dir, "10.0.0", migrations="migrations")
        for version in ("2.0.0", "10.0.0", "9.0.0"):
            write_migration(
                model_dir / "migrations",
                version,
                [{"id": "x", "kind": "drop_property", "property": "tm:p"}],
            )
        manifest = parse_manifest(model_dir)
        specs = discover_migrations(model_dir, manifest)

        # Semver ordering, not lexicographic: 9.0.0 sorts before 10.0.0.
        assert [s.version for s in specs] == ["2.0.0", "9.0.0", "10.0.0"]

    def test_rejects_a_migration_newer_than_the_manifest(self, model_dir):
        write_manifest(model_dir, "2.0.0", migrations="migrations")
        write_migration(
            model_dir / "migrations",
            "3.0.0",
            [{"id": "x", "kind": "drop_property", "property": "tm:p"}],
        )
        manifest = parse_manifest(model_dir)
        with pytest.raises(MigrationError, match="newer than the manifest"):
            discover_migrations(model_dir, manifest)

    def test_missing_declared_directory_is_an_error(self, model_dir):
        write_manifest(model_dir, "1.0.0", migrations="migrations")
        manifest = parse_manifest(model_dir)
        with pytest.raises(MigrationError, match="not found"):
            discover_migrations(model_dir, manifest)

    def test_ignores_non_yaml_files(self, model_dir):
        write_manifest(model_dir, "2.0.0", migrations="migrations")
        migrations = model_dir / "migrations"
        write_migration(
            migrations,
            "2.0.0",
            [{"id": "x", "kind": "drop_property", "property": "tm:p"}],
        )
        (migrations / "README.md").write_text("notes")
        manifest = parse_manifest(model_dir)
        assert [s.version for s in discover_migrations(model_dir, manifest)] == ["2.0.0"]

    def test_migrations_path_may_not_escape_the_archive(self, model_dir):
        with pytest.raises(ValueError, match="relative path inside the archive"):
            ManifestSchema.model_validate(
                {
                    "modelId": MODEL_ID,
                    "version": "1.0.0",
                    "name": "Test",
                    "namespace": NS,
                    "entrypoints": {"migrations": "../../etc"},
                }
            )


class TestSelectChain:
    @staticmethod
    def _specs(tmp_path, versions):
        specs = []
        for version in versions:
            path = write_migration(
                tmp_path,
                version,
                [{"id": "x", "kind": "drop_property", "property": "tm:p"}],
            )
            specs.append(parse_migration_spec(path))
        return specs

    def test_selects_only_versions_in_the_open_closed_interval(self, tmp_path):
        specs = self._specs(tmp_path, ["1.1.0", "2.0.0", "3.0.0"])
        chain = select_chain(specs, "1.1.0", "3.0.0")
        # 1.1.0 is the version already installed, so it is excluded.
        assert [s.version for s in chain] == ["2.0.0", "3.0.0"]

    def test_a_version_bump_with_no_migrations_is_legitimate(self, tmp_path):
        specs = self._specs(tmp_path, ["2.0.0"])
        assert select_chain(specs, "2.0.0", "2.1.0") == []

    def test_refuses_to_migrate_backwards(self, tmp_path):
        specs = self._specs(tmp_path, ["2.0.0"])
        with pytest.raises(MigrationError, match="backwards"):
            select_chain(specs, "3.0.0", "2.0.0")


# ---------------------------------------------------------------------------
# Term expansion, fragment guards, and pattern parsing
# ---------------------------------------------------------------------------


class TestTerms:
    def test_expands_a_declared_prefix(self):
        assert expand_term("tm:Note", PREFIXES) == URIRef(f"{NS}Note")

    def test_passes_through_an_absolute_iri(self):
        assert expand_term("urn:sempkm:x", {}) == URIRef("urn:sempkm:x")

    def test_rejects_an_undeclared_prefix(self):
        with pytest.raises(MigrationError, match="Unknown prefix"):
            expand_term("nope:Thing", PREFIXES)

    @pytest.mark.parametrize(
        "fragment",
        [
            "GRAPH <urn:other> { ?s ?p ?o }",
            "?s ?p ?o . SERVICE <http://evil> { ?a ?b ?c }",
            "?s ?p ?o } ; DROP GRAPH <urn:sempkm:current> ; SELECT * WHERE {",
        ],
    )
    def test_rejects_fragments_that_escape_scope_or_write(self, fragment):
        with pytest.raises(MigrationError):
            validate_fragment(fragment, field_name="where")

    def test_allows_a_property_whose_name_contains_a_keyword(self):
        """`:dropDate` and `?graph` are data, not SPARQL keywords."""
        fragment = "?s <urn:sempkm:model:crm:dropDate> ?graph . FILTER(?graph > 3)"
        assert validate_fragment(fragment, field_name="where") == fragment

    def test_allows_filter_not_exists(self):
        fragment = "FILTER NOT EXISTS { ?s <urn:x:p> ?v }"
        assert validate_fragment(fragment, field_name="where") == fragment

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("?s <urn:x:p> ?o", None),
            ("?s a tm:Note .", None),
            ('?s <urn:x:p> "hello"', None),
            ('?s <urn:x:p> "hi"@en', None),
        ],
    )
    def test_parses_triple_patterns(self, text, expected):
        triple = parse_triple_pattern(text, PREFIXES)
        assert len(triple) == 3

    def test_resolves_a_as_rdf_type_and_expands_curies(self):
        s, p, o = parse_triple_pattern("?s a tm:Note .", PREFIXES)
        assert p == RDF.type
        assert o == URIRef(f"{NS}Note")

    def test_parses_a_typed_literal(self):
        _s, _p, o = parse_triple_pattern(
            '?s <urn:x:p> "3"^^<http://www.w3.org/2001/XMLSchema#integer>', PREFIXES
        )
        assert o == Literal("3", datatype=XSD.integer)

    def test_rejects_a_pattern_that_is_not_three_terms(self):
        with pytest.raises(MigrationError, match="exactly 3 terms"):
            parse_triple_pattern("?s <urn:x:p>", PREFIXES)


# ---------------------------------------------------------------------------
# Delta compilation
# ---------------------------------------------------------------------------


class TestCompileSteps:
    @staticmethod
    def _step(tmp_path, step: dict):
        path = write_migration(tmp_path, "2.0.0", [step])
        return parse_migration_spec(path).steps[0]

    async def test_rename_class_swaps_the_type_triple(self, tmp_path):
        client = FakeClient([[uri_row(s="urn:o:1"), uri_row(s="urn:o:2")]])
        step = self._step(
            tmp_path,
            {"id": "r", "kind": "rename_class", "from": "tm:Note", "to": "tm:Bookmark"},
        )
        delta = await MigrationCompiler(client, PREFIXES).compile_step(step)

        assert delta.deletes == [
            (URIRef("urn:o:1"), RDF.type, URIRef(f"{NS}Note")),
            (URIRef("urn:o:2"), RDF.type, URIRef(f"{NS}Note")),
        ]
        assert delta.inserts == [
            (URIRef("urn:o:1"), RDF.type, URIRef(f"{NS}Bookmark")),
            (URIRef("urn:o:2"), RDF.type, URIRef(f"{NS}Bookmark")),
        ]

    async def test_compilation_only_reads(self, tmp_path):
        client = FakeClient([[uri_row(s="urn:o:1")]])
        step = self._step(
            tmp_path,
            {"id": "r", "kind": "rename_class", "from": "tm:A", "to": "tm:B"},
        )
        await MigrationCompiler(client, PREFIXES).compile_step(step)

        assert client.updates == []
        assert all(q.lstrip().startswith("SELECT") for q in client.queries)

    async def test_rename_property_preserves_the_value(self, tmp_path):
        client = FakeClient(
            [
                [
                    {
                        "s": {"type": "uri", "value": "urn:o:1"},
                        "o": {"type": "literal", "value": "https://example.com"},
                    }
                ]
            ]
        )
        step = self._step(
            tmp_path,
            {
                "id": "r",
                "kind": "rename_property",
                "from": "tm:noteUrl",
                "to": "tm:bookmarkUrl",
            },
        )
        delta = await MigrationCompiler(client, PREFIXES).compile_step(step)

        assert delta.deletes == [
            (URIRef("urn:o:1"), URIRef(f"{NS}noteUrl"), Literal("https://example.com"))
        ]
        assert delta.inserts == [
            (
                URIRef("urn:o:1"),
                URIRef(f"{NS}bookmarkUrl"),
                Literal("https://example.com"),
            )
        ]

    async def test_drop_property_only_deletes(self, tmp_path):
        client = FakeClient(
            [
                [
                    {
                        "s": {"type": "uri", "value": "urn:o:1"},
                        "o": {"type": "literal", "value": "x"},
                    }
                ]
            ]
        )
        step = self._step(
            tmp_path, {"id": "d", "kind": "drop_property", "property": "tm:legacy"}
        )
        delta = await MigrationCompiler(client, PREFIXES).compile_step(step)

        assert len(delta.deletes) == 1
        assert delta.inserts == []

    async def test_set_default_filters_out_subjects_that_have_a_value(self, tmp_path):
        client = FakeClient([[uri_row(s="urn:o:1")]])
        step = self._step(
            tmp_path,
            {
                "id": "b",
                "kind": "set_default",
                "class": "tm:Task",
                "property": "tm:status",
                "value": "todo",
            },
        )
        delta = await MigrationCompiler(client, PREFIXES).compile_step(step)

        assert delta.deletes == []
        assert delta.inserts == [
            (URIRef("urn:o:1"), URIRef(f"{NS}status"), Literal("todo"))
        ]
        assert "FILTER NOT EXISTS" in client.queries[0]

    async def test_set_default_can_insert_an_iri(self, tmp_path):
        client = FakeClient([[uri_row(s="urn:o:1")]])
        step = self._step(
            tmp_path,
            {
                "id": "b",
                "kind": "set_default",
                "class": "tm:Task",
                "property": "tm:owner",
                "value_iri": "tm:Nobody",
            },
        )
        delta = await MigrationCompiler(client, PREFIXES).compile_step(step)
        assert delta.inserts == [
            (URIRef("urn:o:1"), URIRef(f"{NS}owner"), URIRef(f"{NS}Nobody"))
        ]

    async def test_sparql_escape_hatch_substitutes_bindings(self, tmp_path):
        client = FakeClient(
            [
                [
                    {
                        "s": {"type": "uri", "value": "urn:o:1"},
                        "v": {"type": "literal", "value": "42"},
                    }
                ]
            ]
        )
        step = self._step(
            tmp_path,
            {
                "id": "c",
                "kind": "sparql",
                "where": "?s <urn:x:old> ?v .",
                "delete": ["?s <urn:x:old> ?v"],
                "insert": ["?s <urn:x:new> ?v"],
            },
        )
        delta = await MigrationCompiler(client, PREFIXES).compile_step(step)

        assert delta.deletes == [
            (URIRef("urn:o:1"), URIRef("urn:x:old"), Literal("42"))
        ]
        assert delta.inserts == [
            (URIRef("urn:o:1"), URIRef("urn:x:new"), Literal("42"))
        ]

    async def test_a_step_over_the_row_cap_fails_rather_than_partially_applying(
        self, tmp_path
    ):
        client = FakeClient([[uri_row(s=f"urn:o:{i}") for i in range(4)]])
        step = self._step(
            tmp_path,
            {"id": "r", "kind": "rename_class", "from": "tm:A", "to": "tm:B"},
        )
        compiler = MigrationCompiler(client, PREFIXES, max_step_rows=3)
        with pytest.raises(MigrationTooLargeError, match="MAX_STEP_ROWS"):
            await compiler.compile_step(step)

    async def test_scopes_queries_to_the_current_state_graph(self, tmp_path):
        client = FakeClient([[]])
        step = self._step(
            tmp_path,
            {"id": "r", "kind": "rename_class", "from": "tm:A", "to": "tm:B"},
        )
        await MigrationCompiler(client, PREFIXES).compile_step(step)
        assert "GRAPH <urn:sempkm:current>" in client.queries[0]


# ---------------------------------------------------------------------------
# Registry ledger
# ---------------------------------------------------------------------------


class TestModelGraphs:
    def test_journal_graphs_are_keyed_by_version(self):
        graphs = ModelGraphs(MODEL_ID)
        assert graphs.migration_removed("2.0.0").endswith(":migration:2.0.0:removed")
        assert graphs.migration_added("2.0.0").endswith(":migration:2.0.0:added")
        assert len(graphs.migration_graphs(["2.0.0", "3.0.0"])) == 4


# ---------------------------------------------------------------------------
# Upgrade orchestration
# ---------------------------------------------------------------------------


def _installed(version: str):
    model = MagicMock()
    model.model_id = MODEL_ID
    model.version = version
    return model


def _archive(manifest: ManifestSchema) -> ModelArchive:
    graph = Graph()
    graph.add((URIRef("urn:t:s"), URIRef("urn:t:p"), Literal("v")))
    return ModelArchive(
        manifest=manifest,
        ontology=graph,
        shapes=graph,
        views=graph,
        seed=None,
        rules=None,
    )


class TestUpgrade:
    @pytest.fixture
    def prepared(self, model_dir):
        """A model on disk at 2.0.0 with one migration, installed at 1.0.0."""
        write_manifest(model_dir, "2.0.0", migrations="migrations")
        write_migration(
            model_dir / "migrations",
            "2.0.0",
            [
                {
                    "id": "rename",
                    "kind": "rename_class",
                    "from": "tm:Note",
                    "to": "tm:Bookmark",
                }
            ],
        )
        return model_dir

    @staticmethod
    def _service(client, event_store):
        return ModelService(client, event_store, MagicMock())

    async def test_upgrade_applies_the_migration_as_an_event(self, prepared):
        client = FakeClient([[uri_row(s="urn:o:1")]])
        client.begin_transaction = AsyncMock(return_value="txn")
        client.transaction_update = AsyncMock()
        client.commit_transaction = AsyncMock()
        client.rollback_transaction = AsyncMock()
        event_store = AsyncMock()
        service = self._service(client, event_store)

        with (
            patch.object(
                ModelService, "list_models", AsyncMock(return_value=[_installed("1.0.0")])
            ),
            patch(
                "app.services.models.get_applied_migrations",
                AsyncMock(return_value=set()),
            ),
            patch("app.services.models.is_model_installed", AsyncMock(return_value=True)),
            patch("app.services.models.record_applied_migration", AsyncMock()) as record,
            patch("app.services.models.set_model_version", AsyncMock()) as set_version,
            patch("app.services.models.load_archive") as load,
            patch("app.services.models.validate_archive") as validate,
        ):
            manifest = parse_manifest(prepared)
            load.return_value = _archive(manifest)
            validate.return_value = MagicMock(is_valid=True, warnings=[], errors=[])

            result = await service.upgrade(
                MODEL_ID, uuid.uuid4(), model_dir=prepared
            )

        assert result.success, result.errors
        assert result.migrations_applied == ["2.0.0"]
        assert result.triples_deleted == 1
        assert result.triples_inserted == 1

        event_store.commit.assert_awaited_once()
        operation = event_store.commit.await_args.args[0][0]
        assert operation.operation_type == "model.migrate"
        # Ground deletes go through the batched channel, not the per-pattern one.
        assert operation.materialize_delete_data == [
            (URIRef("urn:o:1"), RDF.type, URIRef(f"{NS}Note"))
        ]
        assert operation.materialize_deletes == []
        assert operation.materialize_inserts == [
            (URIRef("urn:o:1"), RDF.type, URIRef(f"{NS}Bookmark"))
        ]

        record.assert_awaited_once_with(client, MODEL_ID, "2.0.0")
        set_version.assert_awaited_once_with(client, MODEL_ID, "2.0.0")

    async def test_an_already_applied_migration_is_skipped(self, prepared):
        """The ledger is what makes an interrupted upgrade resumable."""
        client = FakeClient()
        client.begin_transaction = AsyncMock(return_value="txn")
        client.transaction_update = AsyncMock()
        client.commit_transaction = AsyncMock()
        client.rollback_transaction = AsyncMock()
        event_store = AsyncMock()
        service = self._service(client, event_store)

        with (
            patch.object(
                ModelService, "list_models", AsyncMock(return_value=[_installed("1.0.0")])
            ),
            patch(
                "app.services.models.get_applied_migrations",
                AsyncMock(return_value={"2.0.0"}),
            ),
            patch("app.services.models.is_model_installed", AsyncMock(return_value=True)),
            patch("app.services.models.record_applied_migration", AsyncMock()) as record,
            patch("app.services.models.set_model_version", AsyncMock()),
            patch("app.services.models.load_archive") as load,
            patch("app.services.models.validate_archive") as validate,
        ):
            load.return_value = _archive(parse_manifest(prepared))
            validate.return_value = MagicMock(is_valid=True, warnings=[], errors=[])
            result = await service.upgrade(MODEL_ID, model_dir=prepared)

        assert result.success, result.errors
        assert result.migrations_applied == []
        assert result.migrations_skipped == ["2.0.0"]
        event_store.commit.assert_not_awaited()
        record.assert_not_awaited()

    async def test_a_broken_archive_stops_before_anything_changes(self, prepared):
        client = FakeClient()
        event_store = AsyncMock()
        service = self._service(client, event_store)

        with (
            patch.object(
                ModelService, "list_models", AsyncMock(return_value=[_installed("1.0.0")])
            ),
            patch(
                "app.services.models.get_applied_migrations",
                AsyncMock(return_value=set()),
            ),
            patch("app.services.models.load_archive") as load,
            patch("app.services.models.validate_archive") as validate,
        ):
            load.return_value = _archive(parse_manifest(prepared))
            issue = MagicMock(file="ontology.jsonld", rule="parse", message="bad")
            validate.return_value = MagicMock(
                is_valid=False, errors=[issue], warnings=[]
            )
            result = await service.upgrade(MODEL_ID, model_dir=prepared)

        assert not result.success
        assert "bad" in result.errors[0]
        assert client.updates == []
        event_store.commit.assert_not_awaited()

    async def test_upgrade_refuses_when_the_model_is_not_installed(self, prepared):
        service = self._service(FakeClient(), AsyncMock())
        with patch.object(ModelService, "list_models", AsyncMock(return_value=[])):
            result = await service.upgrade(MODEL_ID, model_dir=prepared)
        assert not result.success
        assert "not installed" in result.errors[0]

    async def test_same_version_is_a_no_op(self, prepared):
        service = self._service(FakeClient(), AsyncMock())
        with (
            patch.object(
                ModelService, "list_models", AsyncMock(return_value=[_installed("2.0.0")])
            ),
            patch(
                "app.services.models.get_applied_migrations",
                AsyncMock(return_value=set()),
            ),
        ):
            result = await service.upgrade(MODEL_ID, model_dir=prepared)

        assert result.success
        assert result.migrations_applied == []
        assert "already at version" in result.warnings[0]


class TestPlanUpgrade:
    async def test_plan_reports_counts_without_writing(self, model_dir):
        write_manifest(model_dir, "2.0.0", migrations="migrations")
        write_migration(
            model_dir / "migrations",
            "2.0.0",
            [
                {
                    "id": "rename",
                    "kind": "rename_class",
                    "from": "tm:Note",
                    "to": "tm:Bookmark",
                }
            ],
        )
        client = FakeClient([[uri_row(s="urn:o:1"), uri_row(s="urn:o:2")]])
        service = ModelService(client, AsyncMock(), MagicMock())

        with (
            patch.object(
                ModelService, "list_models", AsyncMock(return_value=[_installed("1.0.0")])
            ),
            patch(
                "app.services.models.get_applied_migrations",
                AsyncMock(return_value=set()),
            ),
        ):
            plan = await service.plan_upgrade(MODEL_ID, model_dir=model_dir)

        assert plan.success, plan.errors
        assert plan.from_version == "1.0.0"
        assert plan.to_version == "2.0.0"
        assert plan.delete_count == 2
        assert plan.insert_count == 2
        assert not plan.is_noop
        assert plan.migrations[0].steps[0]["deletes"] == 2
        assert client.updates == []

    async def test_plan_flags_a_version_bump_with_no_migrations(self, model_dir):
        write_manifest(model_dir, "2.0.0")
        service = ModelService(FakeClient(), AsyncMock(), MagicMock())

        with (
            patch.object(
                ModelService, "list_models", AsyncMock(return_value=[_installed("1.0.0")])
            ),
            patch(
                "app.services.models.get_applied_migrations",
                AsyncMock(return_value=set()),
            ),
        ):
            plan = await service.plan_upgrade(MODEL_ID, model_dir=model_dir)

        assert plan.success
        assert plan.is_noop
        assert "ships no migrations" in plan.warnings[0]

    async def test_plan_warns_that_later_migrations_are_estimates(self, model_dir):
        write_manifest(model_dir, "3.0.0", migrations="migrations")
        for version in ("2.0.0", "3.0.0"):
            write_migration(
                model_dir / "migrations",
                version,
                [{"id": "d", "kind": "drop_property", "property": "tm:p"}],
            )
        client = FakeClient([[], []])
        service = ModelService(client, AsyncMock(), MagicMock())

        with (
            patch.object(
                ModelService, "list_models", AsyncMock(return_value=[_installed("1.0.0")])
            ),
            patch(
                "app.services.models.get_applied_migrations",
                AsyncMock(return_value=set()),
            ),
        ):
            plan = await service.plan_upgrade(MODEL_ID, model_dir=model_dir)

        assert plan.success
        assert any("estimates" in w for w in plan.warnings)


class TestRollback:
    async def test_rollback_reverses_the_journalled_delta(self):
        client = FakeClient()
        removed = Graph()
        removed.add((URIRef("urn:o:1"), RDF.type, URIRef(f"{NS}Note")))
        added = Graph()
        added.add((URIRef("urn:o:1"), RDF.type, URIRef(f"{NS}Bookmark")))
        event_store = AsyncMock()
        service = ModelService(client, event_store, MagicMock())

        journals = iter(
            [removed.serialize(format="turtle"), added.serialize(format="turtle")]
        )

        async def fake_construct(_sparql):
            return next(journals)

        client.construct = fake_construct

        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value={"2.0.0"}),
        ):
            result = await service.rollback_migration(MODEL_ID, "2.0.0")

        assert result.success, result.errors
        assert result.triples_restored == 1
        assert result.triples_removed == 1

        operation = event_store.commit.await_args.args[0][0]
        assert operation.operation_type == "model.migrate.rollback"
        assert operation.materialize_inserts == list(removed)
        assert operation.materialize_delete_data == list(added)

    async def test_rollback_refuses_an_unapplied_migration(self):
        service = ModelService(FakeClient(), AsyncMock(), MagicMock())
        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value=set()),
        ):
            result = await service.rollback_migration(MODEL_ID, "2.0.0")
        assert not result.success
        assert "not recorded as applied" in result.errors[0]

    async def test_rollback_refuses_an_out_of_order_migration(self):
        """A later migration invalidates an earlier one's journal.

        If 2.0.0 retyped A to B and 3.0.0 then retyped B to C, reversing
        2.0.0 alone would delete a type triple that is no longer there and
        leave the object typed as both A and C.
        """
        event_store = AsyncMock()
        service = ModelService(FakeClient(), event_store, MagicMock())

        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value={"2.0.0", "3.0.0"}),
        ):
            result = await service.rollback_migration(MODEL_ID, "2.0.0")

        assert not result.success
        assert "not the most recent" in result.errors[0]
        assert "3.0.0" in result.errors[0]
        event_store.commit.assert_not_awaited()

    async def test_newest_is_chosen_by_semver_not_string_order(self):
        """10.0.0 is newer than 9.0.0, though it sorts earlier as a string."""
        event_store = AsyncMock()
        service = ModelService(FakeClient(), event_store, MagicMock())

        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value={"9.0.0", "10.0.0"}),
        ):
            result = await service.rollback_migration(MODEL_ID, "9.0.0")

        assert not result.success
        assert "10.0.0" in result.errors[0]
        event_store.commit.assert_not_awaited()

    async def test_rollback_refuses_when_the_journal_is_gone(self):
        client = FakeClient()
        client.construct_result = b""
        event_store = AsyncMock()
        service = ModelService(client, event_store, MagicMock())

        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value={"2.0.0"}),
        ):
            result = await service.rollback_migration(MODEL_ID, "2.0.0")

        assert not result.success
        assert "No journal found" in result.errors[0]
        event_store.commit.assert_not_awaited()

    async def test_rollback_clears_the_ledger_entry_and_journal(self):
        client = FakeClient()
        removed = Graph()
        removed.add((URIRef("urn:o:1"), RDF.type, URIRef(f"{NS}Note")))
        added = Graph()
        added.add((URIRef("urn:o:1"), RDF.type, URIRef(f"{NS}Bookmark")))
        journals = iter(
            [removed.serialize(format="turtle"), added.serialize(format="turtle")]
        )

        async def fake_construct(_sparql):
            return next(journals)

        client.construct = fake_construct
        service = ModelService(client, AsyncMock(), MagicMock())

        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value={"2.0.0"}),
        ):
            result = await service.rollback_migration(MODEL_ID, "2.0.0")

        assert result.success, result.errors
        writes = "\n".join(client.updates)
        assert "appliedMigration" in writes and "DELETE DATA" in writes
        assert "migration:2.0.0:removed" in writes
        assert "migration:2.0.0:added" in writes


class TestAppliedMigrationLedger:
    async def test_lists_newest_first_with_journal_sizes(self):
        client = FakeClient(
            [
                [{"count": {"value": "3"}}],  # 2.0.0 removed
                [{"count": {"value": "4"}}],  # 2.0.0 added
                [{"count": {"value": "1"}}],  # 10.0.0 removed
                [{"count": {"value": "2"}}],  # 10.0.0 added
            ]
        )
        service = ModelService(client, AsyncMock(), MagicMock())

        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value=["2.0.0", "10.0.0"]),
        ):
            entries = await service.list_applied_migrations(MODEL_ID)

        assert [e.version for e in entries] == ["10.0.0", "2.0.0"]
        assert entries[0].is_latest is True
        assert entries[1].is_latest is False
        assert entries[1].removed_count == 3
        assert entries[1].added_count == 4
        assert all(e.reversible for e in entries)

    async def test_a_migration_that_moved_nothing_is_not_reversible(self):
        client = FakeClient(
            [[{"count": {"value": "0"}}], [{"count": {"value": "0"}}]]
        )
        service = ModelService(client, AsyncMock(), MagicMock())

        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value=["2.0.0"]),
        ):
            entries = await service.list_applied_migrations(MODEL_ID)

        assert entries[0].reversible is False
        assert entries[0].is_noop is True

    async def test_empty_ledger_returns_nothing(self):
        service = ModelService(FakeClient(), AsyncMock(), MagicMock())
        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value=set()),
        ):
            assert await service.list_applied_migrations(MODEL_ID) == []

    async def test_listing_only_reads(self):
        client = FakeClient(
            [[{"count": {"value": "1"}}], [{"count": {"value": "1"}}]]
        )
        service = ModelService(client, AsyncMock(), MagicMock())
        with patch(
            "app.services.models.get_applied_migrations",
            AsyncMock(return_value=["2.0.0"]),
        ):
            await service.list_applied_migrations(MODEL_ID)
        assert client.updates == []


# ---------------------------------------------------------------------------
# Migrations tab rendering
# ---------------------------------------------------------------------------


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "app" / "templates"


def _template_env():
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    # Registered by the app at startup; stubbed so templates compile here.
    env.filters.setdefault("asset_url", lambda name: f"/static/{name}")
    return env


def _entry(version, removed, added, reversible, is_latest):
    from app.services.models import MigrationLedgerEntry

    return MigrationLedgerEntry(
        version=version,
        removed_count=removed,
        added_count=added,
        reversible=reversible,
        is_latest=is_latest,
    )


def _info():
    info = MagicMock()
    info.model_id = MODEL_ID
    info.name = "Test Model"
    return info


class TestMigrationsTabTemplate:
    """The rollback button is the guard users actually see, so gate it here."""

    @staticmethod
    def _render(migrations, **extra):
        template = _template_env().get_template("admin/model_migrations.html")
        return template.render(request=None, info=_info(), migrations=migrations, **extra)

    def test_empty_ledger_renders_an_empty_state(self):
        out = self._render([])
        assert "No migrations recorded" in out
        assert "/rollback" not in out

    def test_only_the_newest_migration_offers_rollback(self):
        out = self._render(
            [
                _entry("10.0.0", 1, 2, True, True),
                _entry("2.0.0", 3, 4, True, False),
            ]
        )
        assert out.count("/rollback") == 1
        assert f"/admin/models/{MODEL_ID}/migrations/10.0.0/rollback" in out
        assert "Roll back v10.0.0 first" in out

    def test_a_migration_that_changed_nothing_offers_no_rollback(self):
        out = self._render([_entry("2.0.0", 0, 0, False, True)])
        assert "/rollback" not in out
        assert "No data changed" in out

    def test_a_missing_journal_offers_no_rollback(self):
        out = self._render([_entry("2.0.0", 5, 5, False, True)])
        assert "/rollback" not in out
        assert "Journal missing" in out

    def test_messages_render(self):
        assert "boom" in self._render([], error="boom")
        assert "restored" in self._render([], success="3 triples restored")

    def test_detail_page_wires_the_migrations_tab(self):
        source = (TEMPLATE_DIR / "admin" / "model_detail.html").read_text()
        assert 'data-tab="migrations"' in source
        assert 'hx-target="#migrations-content"' in source
        assert 'id="migrations-panel"' in source
        # The tab must compile, not just contain the right strings.
        _template_env().get_template("admin/model_detail.html")
