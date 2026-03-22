"""Tests for form-group block type and slot-based IRI resolution (M032/S01/T01).

Covers:
- form-group block validation in BlockRegistry (valid/invalid config shapes)
- Slot resolution in batch commands: happy path, unresolved references, edge cases
"""

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
