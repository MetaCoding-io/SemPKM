"""Tests for the Notion import executor.

Covers ImportResult serialization, two-pass import (objects + relations),
body file matching with stripped Notion IDs, per-row error isolation,
standalone page import, multi-value relation cells, unresolved relations,
and SSE broadcast events.
"""

import asyncio
import csv
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.notion.models import (
    DetectedRelation,
    ImportResult,
    MappingConfig,
    NotionColumn,
    NotionDatabase,
    NotionPage,
    NotionScanResult,
    PropertyMapping,
    RelationMapping,
    TypeMapping,
)


# ────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────


def _make_broadcast() -> MagicMock:
    """Return a mock ScanBroadcast that silently accepts publish() calls."""
    bc = MagicMock()
    bc.publish = MagicMock()
    return bc


def _make_user() -> MagicMock:
    """Return a mock User with id and role."""
    user = MagicMock()
    user.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.role = "admin"
    return user


def _make_event_store() -> AsyncMock:
    """Return a mock EventStore with async commit."""
    es = AsyncMock()
    es.commit = AsyncMock()
    return es


def _make_triplestore_client() -> AsyncMock:
    """Return a mock TriplestoreClient."""
    return AsyncMock()


@dataclass
class FakeOperation:
    """Minimal Operation-like object for mocking handle_object_create."""

    operation_type: str = "object.create"
    affected_iris: list[str] = field(default_factory=lambda: ["urn:test:obj1"])
    description: str = "test"
    data_triples: list = field(default_factory=list)
    materialize_inserts: list = field(default_factory=list)
    materialize_deletes: list = field(default_factory=list)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write a CSV file from a list of dicts."""
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _make_scan_result(
    extract_path: str,
    databases: list[NotionDatabase] | None = None,
    standalone_pages: list[NotionPage] | None = None,
    detected_relations: list[DetectedRelation] | None = None,
) -> NotionScanResult:
    """Build a NotionScanResult with defaults."""
    return NotionScanResult(
        workspace_name="TestWorkspace",
        import_id="test-import-001",
        extract_path=extract_path,
        databases=databases or [],
        standalone_pages=standalone_pages or [],
        detected_relations=detected_relations or [],
    )


def _make_mapping_config(
    type_mappings: dict | None = None,
    property_mappings: dict | None = None,
    relation_mappings: dict | None = None,
    standalone_page_type_iri: str | None = None,
) -> MappingConfig:
    """Build a MappingConfig with defaults."""
    return MappingConfig(
        type_mappings=type_mappings or {},
        property_mappings=property_mappings or {},
        relation_mappings=relation_mappings or {},
        standalone_page_type_iri=standalone_page_type_iri,
    )


# Counter for generating unique IRIs per mock call
_iri_counter = 0


def _reset_counter():
    global _iri_counter
    _iri_counter = 0


def _make_object_op(iri: str | None = None) -> FakeOperation:
    """Create a fake Operation with a unique IRI."""
    global _iri_counter
    _iri_counter += 1
    return FakeOperation(
        affected_iris=[iri or f"urn:test:obj{_iri_counter}"],
    )


def _make_edge_op() -> FakeOperation:
    """Create a fake edge Operation."""
    return FakeOperation(operation_type="edge.create", affected_iris=["urn:test:edge1"])


def _make_body_op() -> FakeOperation:
    """Create a fake body.set Operation."""
    return FakeOperation(operation_type="body.set", affected_iris=["urn:test:obj1"])


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ────────────────────────────────────────────────────────────────
#  ImportResult serialization tests
# ────────────────────────────────────────────────────────────────


class TestImportResultSerialization:
    """Test ImportResult to_dict/from_dict round-trip."""

    def test_round_trip_full(self):
        """Full ImportResult serializes and deserializes correctly."""
        result = ImportResult(
            created=5,
            skipped=2,
            edges_created=3,
            unresolved_relations=[
                ("urn:obj:1", "Tasks|Project", "Missing Project"),
                ("urn:obj:2", "Tasks|Assignee", "Unknown Person"),
            ],
            errors=[
                ("Tasks.csv", "Row parse error"),
                ("Notes.csv", "Encoding issue"),
            ],
            duration_seconds=1.23,
        )
        d = result.to_dict()
        restored = ImportResult.from_dict(d)

        assert restored.created == 5
        assert restored.skipped == 2
        assert restored.edges_created == 3
        assert len(restored.unresolved_relations) == 2
        assert restored.unresolved_relations[0] == (
            "urn:obj:1",
            "Tasks|Project",
            "Missing Project",
        )
        assert len(restored.errors) == 2
        assert restored.errors[0] == ("Tasks.csv", "Row parse error")
        assert restored.duration_seconds == 1.23

    def test_round_trip_empty(self):
        """Empty ImportResult round-trips correctly."""
        result = ImportResult()
        d = result.to_dict()
        restored = ImportResult.from_dict(d)

        assert restored.created == 0
        assert restored.skipped == 0
        assert restored.edges_created == 0
        assert restored.unresolved_relations == []
        assert restored.errors == []
        assert restored.duration_seconds == 0.0

    def test_to_dict_structure(self):
        """to_dict produces correct dict shapes for tuple fields."""
        result = ImportResult(
            unresolved_relations=[("urn:s", "key", "val")],
            errors=[("path.csv", "msg")],
        )
        d = result.to_dict()

        assert d["unresolved_relations"] == [
            {"source": "urn:s", "relation": "key", "value": "val"}
        ]
        assert d["errors"] == [{"path": "path.csv", "message": "msg"}]

    def test_json_serializable(self):
        """to_dict output is JSON-serializable."""
        result = ImportResult(
            created=1,
            unresolved_relations=[("urn:a", "k", "v")],
            errors=[("f", "e")],
        )
        text = json.dumps(result.to_dict())
        assert isinstance(text, str)


# ────────────────────────────────────────────────────────────────
#  Executor Pass 1 tests
# ────────────────────────────────────────────────────────────────


class TestExecutorPass1:
    """Test Pass 1: object creation from CSV rows."""

    def _setup_db(self, tmp_path):
        """Set up a simple database with CSV and mapping."""
        db_folder = tmp_path / "Tasks"
        db_folder.mkdir()
        csv_path = db_folder / "Tasks.csv"
        _write_csv(
            csv_path,
            [
                {"Name": "Task Alpha", "Status": "Open", "Priority": "High"},
                {"Name": "Task Beta", "Status": "Done", "Priority": "Low"},
                {"Name": "Task Gamma", "Status": "Open", "Priority": "Medium"},
            ],
        )

        db = NotionDatabase(
            name="Tasks",
            folder_path="Tasks",
            csv_path="Tasks/Tasks.csv",
            columns=[
                NotionColumn(name="Name", inferred_type="text"),
                NotionColumn(name="Status", inferred_type="select"),
                NotionColumn(name="Priority", inferred_type="select"),
            ],
            row_count=3,
        )
        type_iri = "urn:sempkm:model:basic-pkm:Task"
        mapping = _make_mapping_config(
            type_mappings={"Tasks": TypeMapping(type_iri, "Task")},
            property_mappings={
                type_iri: {
                    "Status": PropertyMapping(
                        "schema:status", "Status", "shacl"
                    ),
                    "Priority": PropertyMapping(
                        "schema:priority", "Priority", "custom"
                    ),
                }
            },
        )
        scan = _make_scan_result(str(tmp_path), databases=[db])
        return tmp_path, scan, mapping

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_creates_objects_from_csv_rows(self, mock_create, mock_body, tmp_path):
        """Pass 1 creates one object per CSV row."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        tmp_path_setup, scan, mapping = self._setup_db(tmp_path)
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        mock_create.side_effect = lambda params, ns: _make_object_op()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert result.created == 3
        assert mock_create.call_count == 3

        # Verify properties on first call
        first_call_params = mock_create.call_args_list[0][0][0]
        assert first_call_params.type == "urn:sempkm:model:basic-pkm:Task"
        assert first_call_params.properties["dcterms:title"] == "Task Alpha"
        assert first_call_params.properties["schema:status"] == "Open"
        assert first_call_params.properties["schema:priority"] == "High"
        assert "sempkm:importSource" in first_call_params.properties

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_sets_body_from_md_file(self, mock_create, mock_body, tmp_path):
        """Pass 1 reads markdown body files matched by stripped title."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        _, scan, mapping = self._setup_db(tmp_path)
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        # Create body file for "Task Alpha" with Notion ID suffix
        body_file = tmp_path / "Tasks" / "Task Alpha abc123def456abc123def456abc12345.md"
        body_file.write_text("# Task Alpha\nThis is the body content.")

        mock_create.side_effect = lambda params, ns: _make_object_op()
        mock_body.side_effect = lambda params, ns: _make_body_op()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        # body_set called once (only Task Alpha has a body file)
        assert mock_body.call_count == 1
        body_call_params = mock_body.call_args_list[0][0][0]
        assert "Task Alpha" in body_call_params.body

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_skips_unmapped_databases(self, mock_create, mock_body, tmp_path):
        """Databases not in type_mappings are skipped entirely."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        db_folder = tmp_path / "Skipped"
        db_folder.mkdir()
        _write_csv(db_folder / "Skipped.csv", [{"Name": "X"}])

        db = NotionDatabase(
            name="Skipped", folder_path="Skipped", csv_path="Skipped/Skipped.csv",
            row_count=1,
        )
        scan = _make_scan_result(str(tmp_path), databases=[db])
        mapping = _make_mapping_config()  # no type mappings at all
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert result.created == 0
        assert mock_create.call_count == 0

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_skips_empty_title_rows(self, mock_create, mock_body, tmp_path):
        """Rows with empty title column are skipped."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        db_folder = tmp_path / "Tasks"
        db_folder.mkdir()
        _write_csv(
            db_folder / "Tasks.csv",
            [
                {"Name": "Good Row", "Status": "Open"},
                {"Name": "", "Status": "Done"},
                {"Name": "  ", "Status": "Pending"},
            ],
        )
        db = NotionDatabase(
            name="Tasks", folder_path="Tasks", csv_path="Tasks/Tasks.csv",
            row_count=3,
        )
        scan = _make_scan_result(str(tmp_path), databases=[db])
        type_iri = "urn:type:Task"
        mapping = _make_mapping_config(
            type_mappings={"Tasks": TypeMapping(type_iri, "Task")},
        )
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        mock_create.side_effect = lambda params, ns: _make_object_op()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert result.created == 1
        assert result.skipped == 2

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_persists_import_result_json(self, mock_create, mock_body, tmp_path):
        """import_result.json is written to import_dir."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        _, scan, mapping = self._setup_db(tmp_path)
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        mock_create.side_effect = lambda params, ns: _make_object_op()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        result_file = import_dir / "import_result.json"
        assert result_file.exists()
        data = json.loads(result_file.read_text())
        assert data["created"] == 3
        assert data["duration_seconds"] >= 0


# ────────────────────────────────────────────────────────────────
#  Executor Pass 2 tests
# ────────────────────────────────────────────────────────────────


class TestExecutorPass2:
    """Test Pass 2: relation resolution."""

    def _setup_relations(self, tmp_path):
        """Set up two databases with a cross-relation."""
        # Tasks DB
        tasks_folder = tmp_path / "Tasks"
        tasks_folder.mkdir()
        _write_csv(
            tasks_folder / "Tasks.csv",
            [
                {"Name": "Task A", "Project": "Project X"},
                {"Name": "Task B", "Project": "Project Y"},
            ],
        )

        # Projects DB
        projects_folder = tmp_path / "Projects"
        projects_folder.mkdir()
        _write_csv(
            projects_folder / "Projects.csv",
            [
                {"Name": "Project X", "Status": "Active"},
                {"Name": "Project Y", "Status": "Done"},
            ],
        )

        tasks_db = NotionDatabase(
            name="Tasks",
            folder_path="Tasks",
            csv_path="Tasks/Tasks.csv",
            row_count=2,
        )
        projects_db = NotionDatabase(
            name="Projects",
            folder_path="Projects",
            csv_path="Projects/Projects.csv",
            row_count=2,
        )

        detected_rel = DetectedRelation(
            source_db_name="Tasks",
            source_column="Project",
            target_db_name="Projects",
            match_ratio=1.0,
        )

        type_iri_task = "urn:type:Task"
        type_iri_project = "urn:type:Project"

        mapping = _make_mapping_config(
            type_mappings={
                "Tasks": TypeMapping(type_iri_task, "Task"),
                "Projects": TypeMapping(type_iri_project, "Project"),
            },
            relation_mappings={
                "Tasks|Project": RelationMapping(
                    target_predicate_iri="schema:isPartOf",
                    target_predicate_label="Part Of",
                    target_type_iri=type_iri_project,
                    target_type_label="Project",
                ),
            },
        )

        scan = _make_scan_result(
            str(tmp_path),
            databases=[tasks_db, projects_db],
            detected_relations=[detected_rel],
        )
        return tmp_path, scan, mapping

    @patch("app.notion.executor.handle_edge_create", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_resolves_relations_by_title(
        self, mock_create, mock_body, mock_edge, tmp_path
    ):
        """Pass 2 creates edges for matching relation values."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        _, scan, mapping = self._setup_relations(tmp_path)
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        # Map: Tasks get task IRIs, Projects get project IRIs
        iri_map = {
            "Task A": "urn:obj:task-a",
            "Task B": "urn:obj:task-b",
            "Project X": "urn:obj:proj-x",
            "Project Y": "urn:obj:proj-y",
        }

        def create_side_effect(params, ns):
            title = params.properties.get("dcterms:title", "")
            iri = iri_map.get(title, f"urn:obj:{title.lower().replace(' ', '-')}")
            return FakeOperation(affected_iris=[iri])

        mock_create.side_effect = create_side_effect
        mock_edge.side_effect = lambda params, ns: _make_edge_op()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert result.created == 4  # 2 tasks + 2 projects
        assert mock_edge.call_count == 2

        # Verify edge calls have correct source/target
        edge_calls = [c[0][0] for c in mock_edge.call_args_list]
        sources = {c.source for c in edge_calls}
        targets = {c.target for c in edge_calls}
        assert "urn:obj:task-a" in sources
        assert "urn:obj:task-b" in sources
        assert "urn:obj:proj-x" in targets
        assert "urn:obj:proj-y" in targets
        # All edges use the mapped predicate
        for call_params in edge_calls:
            assert call_params.predicate == "schema:isPartOf"

    @patch("app.notion.executor.handle_edge_create", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_multi_value_relation_cells(
        self, mock_create, mock_body, mock_edge, tmp_path
    ):
        """Comma-separated relation values produce separate edge_create calls."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        tasks_folder = tmp_path / "Tasks"
        tasks_folder.mkdir()
        _write_csv(
            tasks_folder / "Tasks.csv",
            [{"Name": "Task Multi", "Tags": "Tag A, Tag B"}],
        )
        tags_folder = tmp_path / "Tags"
        tags_folder.mkdir()
        _write_csv(
            tags_folder / "Tags.csv",
            [
                {"Name": "Tag A"},
                {"Name": "Tag B"},
            ],
        )

        tasks_db = NotionDatabase(
            name="Tasks", folder_path="Tasks", csv_path="Tasks/Tasks.csv",
            row_count=1,
        )
        tags_db = NotionDatabase(
            name="Tags", folder_path="Tags", csv_path="Tags/Tags.csv",
            row_count=2,
        )
        detected_rel = DetectedRelation(
            source_db_name="Tasks",
            source_column="Tags",
            target_db_name="Tags",
            match_ratio=1.0,
        )

        type_iri_task = "urn:type:Task"
        type_iri_tag = "urn:type:Tag"
        mapping = _make_mapping_config(
            type_mappings={
                "Tasks": TypeMapping(type_iri_task, "Task"),
                "Tags": TypeMapping(type_iri_tag, "Tag"),
            },
            relation_mappings={
                "Tasks|Tags": RelationMapping(
                    target_predicate_iri="schema:about",
                    target_predicate_label="About",
                    target_type_iri=type_iri_tag,
                    target_type_label="Tag",
                ),
            },
        )
        scan = _make_scan_result(
            str(tmp_path),
            databases=[tasks_db, tags_db],
            detected_relations=[detected_rel],
        )

        iri_map = {
            "Task Multi": "urn:obj:task-multi",
            "Tag A": "urn:obj:tag-a",
            "Tag B": "urn:obj:tag-b",
        }

        def create_side_effect(params, ns):
            title = params.properties.get("dcterms:title", "")
            iri = iri_map.get(title, f"urn:obj:{title}")
            return FakeOperation(affected_iris=[iri])

        mock_create.side_effect = create_side_effect
        mock_edge.side_effect = lambda params, ns: _make_edge_op()

        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        # Two edges: Task Multi -> Tag A and Task Multi -> Tag B
        assert mock_edge.call_count == 2
        edge_calls = [c[0][0] for c in mock_edge.call_args_list]
        assert all(c.source == "urn:obj:task-multi" for c in edge_calls)
        targets = {c.target for c in edge_calls}
        assert targets == {"urn:obj:tag-a", "urn:obj:tag-b"}

    @patch("app.notion.executor.handle_edge_create", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_unresolved_relations(
        self, mock_create, mock_body, mock_edge, tmp_path
    ):
        """Relations pointing to non-existent titles go into unresolved_relations."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        tasks_folder = tmp_path / "Tasks"
        tasks_folder.mkdir()
        _write_csv(
            tasks_folder / "Tasks.csv",
            [{"Name": "Task X", "Project": "NonExistent Project"}],
        )
        projects_folder = tmp_path / "Projects"
        projects_folder.mkdir()
        _write_csv(
            projects_folder / "Projects.csv",
            [{"Name": "Real Project"}],
        )

        tasks_db = NotionDatabase(
            name="Tasks", folder_path="Tasks", csv_path="Tasks/Tasks.csv",
            row_count=1,
        )
        projects_db = NotionDatabase(
            name="Projects", folder_path="Projects",
            csv_path="Projects/Projects.csv", row_count=1,
        )
        detected_rel = DetectedRelation(
            source_db_name="Tasks", source_column="Project",
            target_db_name="Projects", match_ratio=0.0,
        )

        type_iri_task = "urn:type:Task"
        type_iri_project = "urn:type:Project"
        mapping = _make_mapping_config(
            type_mappings={
                "Tasks": TypeMapping(type_iri_task, "Task"),
                "Projects": TypeMapping(type_iri_project, "Project"),
            },
            relation_mappings={
                "Tasks|Project": RelationMapping(
                    target_predicate_iri="schema:isPartOf",
                    target_predicate_label="Part Of",
                    target_type_iri=type_iri_project,
                    target_type_label="Project",
                ),
            },
        )
        scan = _make_scan_result(
            str(tmp_path),
            databases=[tasks_db, projects_db],
            detected_relations=[detected_rel],
        )

        iri_map = {
            "Task X": "urn:obj:task-x",
            "Real Project": "urn:obj:real-proj",
        }

        def create_side_effect(params, ns):
            title = params.properties.get("dcterms:title", "")
            return FakeOperation(affected_iris=[iri_map.get(title, f"urn:obj:{title}")])

        mock_create.side_effect = create_side_effect
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert result.created == 2
        assert mock_edge.call_count == 0
        assert len(result.unresolved_relations) == 1
        src, rel_key, val = result.unresolved_relations[0]
        assert src == "urn:obj:task-x"
        assert rel_key == "Tasks|Project"
        assert val == "NonExistent Project"


# ────────────────────────────────────────────────────────────────
#  Error isolation tests
# ────────────────────────────────────────────────────────────────


class TestExecutorErrorIsolation:
    """Test per-row error isolation."""

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_one_bad_row_doesnt_abort(self, mock_create, mock_body, tmp_path):
        """A failing row doesn't prevent other rows from being imported."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        db_folder = tmp_path / "Items"
        db_folder.mkdir()
        _write_csv(
            db_folder / "Items.csv",
            [
                {"Name": "Good 1"},
                {"Name": "Bad Row"},
                {"Name": "Good 2"},
            ],
        )
        db = NotionDatabase(
            name="Items", folder_path="Items", csv_path="Items/Items.csv",
            row_count=3,
        )
        scan = _make_scan_result(str(tmp_path), databases=[db])
        mapping = _make_mapping_config(
            type_mappings={"Items": TypeMapping("urn:type:Item", "Item")},
        )

        call_count = 0

        def create_side_effect(params, ns):
            nonlocal call_count
            call_count += 1
            if params.properties.get("dcterms:title") == "Bad Row":
                raise ValueError("Simulated error for Bad Row")
            return _make_object_op()

        mock_create.side_effect = create_side_effect
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert result.created == 2
        assert len(result.errors) == 1
        assert "Bad Row" in result.errors[0][1] or result.errors[0][0] == "Items/Items.csv"
        assert call_count == 3  # all 3 rows attempted


# ────────────────────────────────────────────────────────────────
#  Standalone page tests
# ────────────────────────────────────────────────────────────────


class TestExecutorStandalonePages:
    """Test standalone page import."""

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_imports_standalone_pages(self, mock_create, mock_body, tmp_path):
        """Standalone pages are imported when standalone_page_type_iri is set."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        # Create standalone page file
        page_file = tmp_path / "My Notes.md"
        page_file.write_text("# My Notes\nSome standalone content.")

        page = NotionPage(
            title="My Notes", file_path="My Notes.md", has_body=True
        )
        scan = _make_scan_result(str(tmp_path), standalone_pages=[page])
        mapping = _make_mapping_config(
            standalone_page_type_iri="urn:type:Page",
        )

        mock_create.side_effect = lambda params, ns: _make_object_op()
        mock_body.side_effect = lambda params, ns: _make_body_op()

        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert result.created == 1
        assert mock_create.call_count == 1

        # Verify type and title
        call_params = mock_create.call_args_list[0][0][0]
        assert call_params.type == "urn:type:Page"
        assert call_params.properties["dcterms:title"] == "My Notes"

        # Body was set
        assert mock_body.call_count == 1
        body_params = mock_body.call_args_list[0][0][0]
        assert "standalone content" in body_params.body

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_skips_standalone_when_no_type_configured(
        self, mock_create, mock_body, tmp_path
    ):
        """Standalone pages skipped when standalone_page_type_iri is None."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        page = NotionPage(title="Orphan", file_path="Orphan.md")
        scan = _make_scan_result(str(tmp_path), standalone_pages=[page])
        mapping = _make_mapping_config()  # no standalone_page_type_iri

        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert result.created == 0
        assert mock_create.call_count == 0


# ────────────────────────────────────────────────────────────────
#  Body file matching tests
# ────────────────────────────────────────────────────────────────


class TestExecutorBodyFileMatching:
    """Test body file matching with stripped Notion IDs."""

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_body_file_with_notion_id_matches_csv_title(
        self, mock_create, mock_body, tmp_path
    ):
        """A .md file with a 32-hex Notion ID suffix matches the clean CSV title."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        db_folder = tmp_path / "Notes"
        db_folder.mkdir()
        _write_csv(
            db_folder / "Notes.csv",
            [{"Name": "My Page"}],
        )
        # Body file with Notion ID suffix (32 hex chars)
        body_file = db_folder / "My Page abc123def456abc123def456abc12345.md"
        body_file.write_text("Body of My Page")

        db = NotionDatabase(
            name="Notes", folder_path="Notes", csv_path="Notes/Notes.csv",
            row_count=1,
        )
        scan = _make_scan_result(str(tmp_path), databases=[db])
        mapping = _make_mapping_config(
            type_mappings={"Notes": TypeMapping("urn:type:Note", "Note")},
        )

        mock_create.side_effect = lambda params, ns: _make_object_op()
        mock_body.side_effect = lambda params, ns: _make_body_op()

        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert mock_body.call_count == 1
        assert "Body of My Page" in mock_body.call_args_list[0][0][0].body

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_case_insensitive_body_matching(
        self, mock_create, mock_body, tmp_path
    ):
        """Body file matching is case-insensitive."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        db_folder = tmp_path / "Notes"
        db_folder.mkdir()
        _write_csv(
            db_folder / "Notes.csv",
            [{"Name": "My UPPERCASE Page"}],
        )
        # Body file with different case
        body_file = db_folder / "my uppercase page abc123def456abc123def456abc12345.md"
        body_file.write_text("Found it!")

        db = NotionDatabase(
            name="Notes", folder_path="Notes", csv_path="Notes/Notes.csv",
            row_count=1,
        )
        scan = _make_scan_result(str(tmp_path), databases=[db])
        mapping = _make_mapping_config(
            type_mappings={"Notes": TypeMapping("urn:type:Note", "Note")},
        )

        mock_create.side_effect = lambda params, ns: _make_object_op()
        mock_body.side_effect = lambda params, ns: _make_body_op()

        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=_make_broadcast(),
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        assert mock_body.call_count == 1


# ────────────────────────────────────────────────────────────────
#  Broadcast event tests
# ────────────────────────────────────────────────────────────────


class TestExecutorBroadcast:
    """Test SSE broadcast events."""

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_broadcasts_object_progress_and_completion(
        self, mock_create, mock_body, tmp_path
    ):
        """Broadcast fires import_progress for objects and import_complete."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        db_folder = tmp_path / "Items"
        db_folder.mkdir()
        _write_csv(
            db_folder / "Items.csv",
            [{"Name": "A"}, {"Name": "B"}],
        )
        db = NotionDatabase(
            name="Items", folder_path="Items", csv_path="Items/Items.csv",
            row_count=2,
        )
        scan = _make_scan_result(str(tmp_path), databases=[db])
        mapping = _make_mapping_config(
            type_mappings={"Items": TypeMapping("urn:type:Item", "Item")},
        )

        mock_create.side_effect = lambda params, ns: _make_object_op()
        broadcast = _make_broadcast()
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=broadcast,
            import_dir=import_dir,
        )
        _run(executor.execute())

        # Collect published events
        events = [call[0][0] for call in broadcast.publish.call_args_list]
        event_types = [e.event for e in events]

        assert "import_progress" in event_types
        assert "import_complete" in event_types

        # Check progress events have correct phase
        progress_events = [e for e in events if e.event == "import_progress"]
        assert any(e.data["phase"] == "objects" for e in progress_events)

    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_broadcasts_error_on_catastrophic_failure(
        self, mock_create, mock_body, tmp_path
    ):
        """Catastrophic failure broadcasts import_error."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        # Cause catastrophic error by making scan_result.databases iteration fail
        scan = _make_scan_result(str(tmp_path))
        # Patch databases to raise on iteration
        scan.databases = MagicMock()
        scan.databases.__iter__ = MagicMock(
            side_effect=RuntimeError("Catastrophic!")
        )

        mapping = _make_mapping_config()
        broadcast = _make_broadcast()
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=broadcast,
            import_dir=import_dir,
        )
        result = _run(executor.execute())

        events = [call[0][0] for call in broadcast.publish.call_args_list]
        event_types = [e.event for e in events]
        assert "import_error" in event_types

    @patch("app.notion.executor.handle_edge_create", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_body_set", new_callable=AsyncMock)
    @patch("app.notion.executor.handle_object_create", new_callable=AsyncMock)
    def test_broadcasts_edge_progress(
        self, mock_create, mock_body, mock_edge, tmp_path
    ):
        """Pass 2 broadcasts import_progress with phase=edges."""
        from app.notion.executor import NotionImportExecutor

        _reset_counter()
        tasks_folder = tmp_path / "Tasks"
        tasks_folder.mkdir()
        _write_csv(
            tasks_folder / "Tasks.csv",
            [{"Name": "Task A", "Related": "Target A"}],
        )
        targets_folder = tmp_path / "Targets"
        targets_folder.mkdir()
        _write_csv(
            targets_folder / "Targets.csv",
            [{"Name": "Target A"}],
        )

        tasks_db = NotionDatabase(
            name="Tasks", folder_path="Tasks", csv_path="Tasks/Tasks.csv",
            row_count=1,
        )
        targets_db = NotionDatabase(
            name="Targets", folder_path="Targets",
            csv_path="Targets/Targets.csv", row_count=1,
        )
        detected_rel = DetectedRelation(
            source_db_name="Tasks", source_column="Related",
            target_db_name="Targets", match_ratio=1.0,
        )

        mapping = _make_mapping_config(
            type_mappings={
                "Tasks": TypeMapping("urn:type:Task", "Task"),
                "Targets": TypeMapping("urn:type:Target", "Target"),
            },
            relation_mappings={
                "Tasks|Related": RelationMapping(
                    target_predicate_iri="schema:relatedTo",
                    target_predicate_label="Related To",
                    target_type_iri="urn:type:Target",
                    target_type_label="Target",
                ),
            },
        )
        scan = _make_scan_result(
            str(tmp_path),
            databases=[tasks_db, targets_db],
            detected_relations=[detected_rel],
        )

        iri_map = {"Task A": "urn:obj:task-a", "Target A": "urn:obj:target-a"}

        def create_side_effect(params, ns):
            title = params.properties.get("dcterms:title", "")
            return FakeOperation(
                affected_iris=[iri_map.get(title, f"urn:obj:{title}")]
            )

        mock_create.side_effect = create_side_effect
        mock_edge.side_effect = lambda params, ns: _make_edge_op()

        broadcast = _make_broadcast()
        import_dir = tmp_path / "import"
        import_dir.mkdir()

        executor = NotionImportExecutor(
            scan_result=scan,
            mapping_config=mapping,
            extract_path=tmp_path,
            event_store=_make_event_store(),
            triplestore_client=_make_triplestore_client(),
            user=_make_user(),
            broadcast=broadcast,
            import_dir=import_dir,
        )
        _run(executor.execute())

        events = [call[0][0] for call in broadcast.publish.call_args_list]
        edge_progress = [
            e for e in events
            if e.event == "import_progress" and e.data.get("phase") == "edges"
        ]
        assert len(edge_progress) >= 1
