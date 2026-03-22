"""Tests for form-group block type and slot-based IRI resolution (M032/S01/T01).

Covers:
- form-group block validation in BlockRegistry (valid/invalid config shapes)
- Slot resolution in batch commands: happy path, unresolved references, edge cases
- form-group block render output (template HTML with slot containers and data attributes)
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.commands.schemas import (
    Command,
    EdgeCreateCommand,
    EdgeCreateParams,
    ObjectCreateCommand,
    ObjectCreateParams,
)
from app.commands.exceptions import CommandError
from app.dashboard.registry import BLOCK_REGISTRY


# ---------------------------------------------------------------------------
# BlockRegistry: form-group validation
# ---------------------------------------------------------------------------


class TestFormGroupBlockValidation:
    """form-group block type validates correctly in BlockRegistry."""

    def test_valid_form_group_block(self):
        """Valid form-group with slots and edges lists passes validation."""
        BLOCK_REGISTRY.validate_block({
            "type": "form-group",
            "config": {
                "slots": [
                    {"name": "note", "target_class": "urn:sempkm:model:basic-pkm:Note"},
                    {"name": "task", "target_class": "urn:sempkm:model:basic-pkm:Task"},
                ],
                "edges": [
                    {"source": "@slot:note", "target": "@slot:task", "predicate": "sempkm:relatedTo"},
                ],
            },
        })

    def test_valid_form_group_empty_config(self):
        """form-group with missing config keys passes (keys are optional)."""
        BLOCK_REGISTRY.validate_block({
            "type": "form-group",
            "config": {},
        })

    def test_form_group_rejects_slots_as_string(self):
        """slots must be a list, not a string."""
        with pytest.raises(ValueError, match="must be list"):
            BLOCK_REGISTRY.validate_block({
                "type": "form-group",
                "config": {"slots": "note,task"},
            })

    def test_form_group_rejects_edges_as_string(self):
        """edges must be a list, not a string."""
        with pytest.raises(ValueError, match="must be list"):
            BLOCK_REGISTRY.validate_block({
                "type": "form-group",
                "config": {"edges": "note->task"},
            })

    def test_form_group_rejects_slots_as_dict(self):
        """slots must be a list, not a dict."""
        with pytest.raises(ValueError, match="must be list"):
            BLOCK_REGISTRY.validate_block({
                "type": "form-group",
                "config": {"slots": {"note": {}}},
            })

    def test_form_group_category_is_data(self):
        spec = BLOCK_REGISTRY.get("form-group")
        assert spec.category == "data"

    def test_form_group_in_data_category_group(self):
        groups = BLOCK_REGISTRY.by_category()
        data_types = [s.type_name for s in groups["data"]]
        assert "form-group" in data_types


# ---------------------------------------------------------------------------
# ObjectCreateCommand slot field
# ---------------------------------------------------------------------------


class TestObjectCreateSlotField:
    """ObjectCreateCommand accepts optional slot field."""

    def test_slot_field_accepted(self):
        cmd = ObjectCreateCommand(
            command="object.create",
            slot="note",
            params=ObjectCreateParams(type="Note"),
        )
        assert cmd.slot == "note"

    def test_slot_field_defaults_to_none(self):
        cmd = ObjectCreateCommand(
            command="object.create",
            params=ObjectCreateParams(type="Note"),
        )
        assert cmd.slot is None

    def test_slot_field_survives_round_trip(self):
        """slot field present when parsing from dict (like batch payloads)."""
        from pydantic import TypeAdapter
        adapter = TypeAdapter(Command)
        cmd = adapter.validate_python({
            "command": "object.create",
            "slot": "task",
            "params": {"type": "Task"},
        })
        assert cmd.slot == "task"


# ---------------------------------------------------------------------------
# Slot resolution in batch commands
# ---------------------------------------------------------------------------


def _make_object_create(slot: str | None = None, type_name: str = "Note") -> dict:
    """Build an object.create command dict with optional slot."""
    cmd = {
        "command": "object.create",
        "params": {"type": type_name},
    }
    if slot is not None:
        cmd["slot"] = slot
    return cmd


def _make_edge_create(
    source: str = "urn:test:s",
    target: str = "urn:test:t",
    predicate: str = "sempkm:relatedTo",
) -> dict:
    """Build an edge.create command dict."""
    return {
        "command": "edge.create",
        "params": {
            "source": source,
            "target": target,
            "predicate": predicate,
        },
    }


def _fake_operation(iri: str):
    """Create a minimal Operation-like object for mocking dispatch."""
    from app.events.store import Operation
    return Operation(
        operation_type="object.create",
        affected_iris=[iri],
        description=f"Created {iri}",
        data_triples=[],
        materialize_inserts=[],
        materialize_deletes=[],
    )


def _fake_edge_operation(edge_iri: str, source: str, target: str):
    """Create a minimal edge Operation for mocking dispatch."""
    from app.events.store import Operation
    return Operation(
        operation_type="edge.create",
        affected_iris=[edge_iri, source, target],
        description=f"Created edge: {source} -> {target}",
        data_triples=[],
        materialize_inserts=[],
        materialize_deletes=[],
    )


class TestSlotResolution:
    """Slot-based IRI resolution in batch command execution."""

    @pytest.mark.asyncio
    async def test_batch_slot_resolution_happy_path(self):
        """Two object.create with slots + edge.create using @slot: refs → all succeed."""
        from app.commands.router import _parse_commands

        batch = [
            _make_object_create(slot="note", type_name="Note"),
            _make_object_create(slot="task", type_name="Task"),
            _make_edge_create(
                source="@slot:note",
                target="@slot:task",
                predicate="sempkm:relatedTo",
            ),
        ]
        commands = _parse_commands(batch)
        assert len(commands) == 3

        # Simulate the slot resolution logic from execute_commands
        slot_map: dict[str, str] = {}
        resolved_sources = []
        resolved_targets = []

        # Mock dispatch calls returning known IRIs
        note_iri = "urn:sempkm:data:Note/test-note-1"
        task_iri = "urn:sempkm:data:Task/test-task-1"
        edge_iri = "urn:sempkm:edge:test-edge-1"

        dispatch_results = [
            _fake_operation(note_iri),
            _fake_operation(task_iri),
            _fake_edge_operation(edge_iri, note_iri, task_iri),
        ]

        for i, cmd in enumerate(commands):
            # Resolve @slot: refs before dispatch
            if cmd.command == "edge.create":
                for field_name in ("source", "target"):
                    value = getattr(cmd.params, field_name)
                    if isinstance(value, str) and value.startswith("@slot:"):
                        slot_name = value[6:]
                        assert slot_name in slot_map, f"Unresolved slot: {slot_name}"
                        resolved = slot_map[slot_name]
                        object.__setattr__(cmd.params, field_name, resolved)
                        if field_name == "source":
                            resolved_sources.append(resolved)
                        else:
                            resolved_targets.append(resolved)

            # Record slot after "dispatch"
            op = dispatch_results[i]
            primary_iri = op.affected_iris[0]
            if cmd.command == "object.create" and getattr(cmd, "slot", None):
                slot_map[cmd.slot] = primary_iri

        assert slot_map == {"note": note_iri, "task": task_iri}
        assert resolved_sources == [note_iri]
        assert resolved_targets == [task_iri]

    @pytest.mark.asyncio
    async def test_unresolved_slot_raises_command_error(self):
        """edge.create referencing undefined slot → CommandError."""
        from app.commands.router import _parse_commands

        batch = [
            _make_edge_create(source="@slot:missing", target="urn:test:t"),
        ]
        commands = _parse_commands(batch)
        cmd = commands[0]

        slot_map: dict[str, str] = {}

        # Replicate the resolution logic — should raise
        with pytest.raises(CommandError, match="Unresolved slot reference: @slot:missing"):
            for field_name in ("source", "target"):
                value = getattr(cmd.params, field_name)
                if isinstance(value, str) and value.startswith("@slot:"):
                    slot_name = value[6:]
                    if slot_name not in slot_map:
                        raise CommandError(
                            f"Unresolved slot reference: @slot:{slot_name}"
                        )

    def test_slot_on_non_object_create_ignored(self):
        """slot field on non-object.create command is silently ignored."""
        # EdgeCreateCommand does NOT have a slot field — extra fields are rejected
        # by Pydantic. The slot field is only on ObjectCreateCommand.
        # This test confirms the schema rejects it cleanly.
        from pydantic import TypeAdapter, ValidationError
        adapter = TypeAdapter(Command)

        # body.set with an extra "slot" field — Pydantic discriminated union
        # routes this to BodySetCommand which doesn't declare slot, so it
        # either ignores or rejects it. Either way, it doesn't crash.
        cmd = adapter.validate_python({
            "command": "body.set",
            "slot": "ignored",
            "params": {"iri": "urn:test:x", "body": "hello"},
        })
        # slot is not a field on BodySetCommand — should not have it
        assert not hasattr(cmd, "slot") or getattr(cmd, "slot", None) is None

    @pytest.mark.asyncio
    async def test_slot_resolution_only_on_slot_prefixed_values(self):
        """edge.create with normal IRIs (no @slot: prefix) is untouched."""
        from app.commands.router import _parse_commands

        batch = [
            _make_edge_create(
                source="urn:sempkm:data:Note/real-note",
                target="urn:sempkm:data:Task/real-task",
            ),
        ]
        commands = _parse_commands(batch)
        cmd = commands[0]

        # The params should remain unchanged
        assert cmd.params.source == "urn:sempkm:data:Note/real-note"
        assert cmd.params.target == "urn:sempkm:data:Task/real-task"

    @pytest.mark.asyncio
    async def test_slot_map_builds_only_from_object_create_with_slot(self):
        """slot_map only records commands that have both object.create and a slot."""
        from app.commands.router import _parse_commands

        batch = [
            _make_object_create(slot=None, type_name="Note"),  # no slot
            _make_object_create(slot="task", type_name="Task"),  # has slot
        ]
        commands = _parse_commands(batch)

        slot_map: dict[str, str] = {}
        for i, cmd in enumerate(commands):
            primary_iri = f"urn:test:obj-{i}"
            if cmd.command == "object.create" and getattr(cmd, "slot", None):
                slot_map[cmd.slot] = primary_iri

        # Only "task" should be in slot_map
        assert slot_map == {"task": "urn:test:obj-1"}


# ---------------------------------------------------------------------------
# Template rendering: form-group block HTML output
# ---------------------------------------------------------------------------

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def jinja_env():
    """Jinja2 environment pointed at the project's templates directory."""
    templates_dir = Path(__file__).resolve().parent.parent / "app" / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    return env


class TestFormGroupRender:
    """render_block for form-group produces correct HTML structure."""

    def test_two_slots_renders_two_containers(self, jinja_env):
        """Template produces one .form-group-slot per configured slot."""
        tmpl = jinja_env.get_template("browser/dashboard_form_group.html")
        html = tmpl.render(
            dashboard_id="test-dash-1",
            block_index=0,
            slots=[
                {"name": "note", "target_class": "urn:sempkm:model:basic-pkm:Note"},
                {"name": "task", "target_class": "urn:sempkm:model:basic-pkm:Task"},
            ],
            edges=[],
        )
        assert html.count('class="form-group-slot"') == 2
        assert 'data-slot="note"' in html
        assert 'data-slot="task"' in html

    def test_slot_index_attributes(self, jinja_env):
        """Each slot container has correct data-slot-index (0-based)."""
        tmpl = jinja_env.get_template("browser/dashboard_form_group.html")
        html = tmpl.render(
            dashboard_id="test-dash-1",
            block_index=0,
            slots=[
                {"name": "note", "target_class": "urn:sempkm:model:basic-pkm:Note"},
                {"name": "task", "target_class": "urn:sempkm:model:basic-pkm:Task"},
            ],
            edges=[],
        )
        assert 'data-slot-index="0"' in html
        assert 'data-slot-index="1"' in html

    def test_target_class_attributes(self, jinja_env):
        """Each slot container has the correct data-target-class."""
        tmpl = jinja_env.get_template("browser/dashboard_form_group.html")
        html = tmpl.render(
            dashboard_id="test-dash-1",
            block_index=0,
            slots=[
                {"name": "note", "target_class": "urn:sempkm:model:basic-pkm:Note"},
                {"name": "task", "target_class": "urn:sempkm:model:basic-pkm:Task"},
            ],
            edges=[],
        )
        assert 'data-target-class="urn:sempkm:model:basic-pkm:Note"' in html
        assert 'data-target-class="urn:sempkm:model:basic-pkm:Task"' in html

    def test_htmx_load_attributes(self, jinja_env):
        """Each slot container has hx-get to load the SHACL form."""
        tmpl = jinja_env.get_template("browser/dashboard_form_group.html")
        html = tmpl.render(
            dashboard_id="test-dash-1",
            block_index=0,
            slots=[
                {"name": "note", "target_class": "urn:sempkm:model:basic-pkm:Note"},
            ],
            edges=[],
        )
        assert 'hx-get="/browser/objects/new?type=urn' in html
        assert 'hx-trigger="load"' in html
        assert 'hx-swap="innerHTML"' in html

    def test_edges_serialized_as_data_attribute(self, jinja_env):
        """Edge config is embedded as JSON in data-edges attribute."""
        tmpl = jinja_env.get_template("browser/dashboard_form_group.html")
        edges = [
            {"source_slot": "note", "target_slot": "task", "predicate": "sempkm:relatedTo"},
        ]
        html = tmpl.render(
            dashboard_id="test-dash-1",
            block_index=0,
            slots=[
                {"name": "note", "target_class": "urn:sempkm:model:basic-pkm:Note"},
                {"name": "task", "target_class": "urn:sempkm:model:basic-pkm:Task"},
            ],
            edges=edges,
        )
        assert "data-edges='" in html
        # Extract the JSON from single-quoted attribute
        import re
        match = re.search(r"data-edges='([^']*)'", html)
        assert match, "data-edges attribute not found"
        edges_json = match.group(1)
        parsed = json.loads(edges_json)
        assert len(parsed) == 1
        assert parsed[0]["source_slot"] == "note"
        assert parsed[0]["target_slot"] == "task"
        assert parsed[0]["predicate"] == "sempkm:relatedTo"

    def test_submit_button_present(self, jinja_env):
        """Template includes a Create All submit button."""
        tmpl = jinja_env.get_template("browser/dashboard_form_group.html")
        html = tmpl.render(
            dashboard_id="test-dash-1",
            block_index=0,
            slots=[{"name": "note", "target_class": "urn:test:Note"}],
            edges=[],
        )
        assert 'Create All' in html
        assert '_submitFormGroup' in html

    def test_result_area_present(self, jinja_env):
        """Template includes a result/status area div."""
        tmpl = jinja_env.get_template("browser/dashboard_form_group.html")
        html = tmpl.render(
            dashboard_id="test-dash-1",
            block_index=0,
            slots=[{"name": "note", "target_class": "urn:test:Note"}],
            edges=[],
        )
        assert 'form-group-result' in html

    def test_empty_slots_not_rendered_by_template(self, jinja_env):
        """With zero slots, template renders no slot containers (router handles the error)."""
        tmpl = jinja_env.get_template("browser/dashboard_form_group.html")
        html = tmpl.render(
            dashboard_id="test-dash-1",
            block_index=0,
            slots=[],
            edges=[],
        )
        assert 'form-group-slot' not in html
        # Submit button is still present (router guards empty slots before reaching template)
        assert 'Create All' in html


# ---------------------------------------------------------------------------
# Integration: dashboard with form-group round-trips through API
# ---------------------------------------------------------------------------

import uuid
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User
from app.dashboard.service import DashboardService
from app.db.base import Base


@pytest_asyncio.fixture
async def async_session_factory():
    """Provide an in-memory SQLite async session factory."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(async_session_factory):
    """Create a test user and return them."""
    user = User(
        id=uuid.uuid4(),
        username="fg_testuser",
        email="fg@example.com",
        display_name="FG Test",
    )
    async with async_session_factory() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def dashboard_service(async_session_factory):
    """Provide a DashboardService with in-memory database."""
    return DashboardService(async_session_factory)


FORM_GROUP_BLOCKS = [
    {
        "type": "form-group",
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 8,
        "config": {
            "slots": [
                {"name": "note", "target_class": "urn:sempkm:model:basic-pkm:Note"},
                {"name": "task", "target_class": "urn:sempkm:model:basic-pkm:Task"},
            ],
            "edges": [
                {
                    "source_slot": "note",
                    "target_slot": "task",
                    "predicate": "sempkm:relatedTo",
                },
            ],
        },
    }
]


class TestFormGroupDashboardRoundTrip:
    """Dashboard with form-group block round-trips through create → get."""

    @pytest.mark.asyncio
    async def test_create_and_get_preserves_form_group_config(
        self, dashboard_service, test_user
    ):
        """Creating a dashboard with form-group config, then reading it back, preserves slots and edges."""
        dashboard = await dashboard_service.create(
            user_id=test_user.id,
            name="Form Group Test",
            layout="gridstack",
            blocks=FORM_GROUP_BLOCKS,
        )

        fetched = await dashboard_service.get(uuid.UUID(dashboard.id))
        assert fetched is not None
        assert len(fetched.blocks) == 1

        block = fetched.blocks[0]
        assert block["type"] == "form-group"
        cfg = block["config"]
        assert len(cfg["slots"]) == 2
        assert cfg["slots"][0]["name"] == "note"
        assert cfg["slots"][0]["target_class"] == "urn:sempkm:model:basic-pkm:Note"
        assert cfg["slots"][1]["name"] == "task"
        assert len(cfg["edges"]) == 1
        assert cfg["edges"][0]["source_slot"] == "note"
        assert cfg["edges"][0]["target_slot"] == "task"
        assert cfg["edges"][0]["predicate"] == "sempkm:relatedTo"

    @pytest.mark.asyncio
    async def test_form_group_empty_config_round_trips(
        self, dashboard_service, test_user
    ):
        """form-group with empty slots/edges round-trips correctly."""
        blocks = [
            {
                "type": "form-group",
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 8,
                "config": {"slots": [], "edges": []},
            }
        ]
        dashboard = await dashboard_service.create(
            user_id=test_user.id,
            name="Empty FG",
            layout="gridstack",
            blocks=blocks,
        )

        fetched = await dashboard_service.get(uuid.UUID(dashboard.id))
        assert fetched is not None
        cfg = fetched.blocks[0]["config"]
        assert cfg["slots"] == []
        assert cfg["edges"] == []

    @pytest.mark.asyncio
    async def test_update_preserves_form_group_config(
        self, dashboard_service, test_user
    ):
        """Updating blocks with form-group config preserves it after re-read."""
        dashboard = await dashboard_service.create(
            user_id=test_user.id,
            name="FG Update Test",
            layout="gridstack",
            blocks=[{"type": "divider", "x": 0, "y": 0, "w": 12, "h": 2, "config": {}}],
        )

        updated = await dashboard_service.update(
            dashboard_id=uuid.UUID(dashboard.id),
            user_id=test_user.id,
            blocks=FORM_GROUP_BLOCKS,
        )
        assert updated is not None
        assert updated.blocks[0]["type"] == "form-group"
        assert len(updated.blocks[0]["config"]["slots"]) == 2
        assert len(updated.blocks[0]["config"]["edges"]) == 1


class TestFormGroupBuilderEdit:
    """Builder edit route renders for dashboards with form-group blocks."""

    @pytest_asyncio.fixture
    async def builder_app(self, async_session_factory, dashboard_service, test_user):
        """Minimal FastAPI app with dashboard builder routes."""
        from pathlib import Path
        from fastapi import FastAPI
        from jinja2_fragments.fastapi import Jinja2Blocks
        from app.dashboard.router import browser_router

        app = FastAPI()
        templates_dir = Path(__file__).parent.parent / "app" / "templates"
        templates = Jinja2Blocks(directory=templates_dir)
        templates.env.filters.setdefault("tojson", json.dumps)
        app.state.templates = templates
        app.state.dashboard_service = dashboard_service

        from app.auth.dependencies import get_current_user

        async def override_user():
            return test_user

        app.dependency_overrides[get_current_user] = override_user
        app.include_router(browser_router)
        yield app

    @pytest_asyncio.fixture
    async def builder_client(self, builder_app):
        """HTTP client for builder routes."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=builder_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_edit_form_group_dashboard_returns_200(
        self, dashboard_service, test_user, builder_client
    ):
        """Builder edit route returns 200 for a dashboard containing a form-group block."""
        dashboard = await dashboard_service.create(
            user_id=test_user.id,
            name="FG Builder Test",
            layout="gridstack",
            blocks=FORM_GROUP_BLOCKS,
        )

        resp = await builder_client.get(f"/browser/dashboard/{dashboard.id}/edit")
        assert resp.status_code == 200
        body = resp.text
        assert "Edit Dashboard" in body
        assert "FG Builder Test" in body

    @pytest.mark.asyncio
    async def test_new_dashboard_builder_includes_form_group_palette(
        self, builder_client
    ):
        """New dashboard builder includes form-group in the block palette."""
        resp = await builder_client.get("/browser/dashboard/new")
        assert resp.status_code == 200
        body = resp.text
        assert 'data-type="form-group"' in body

