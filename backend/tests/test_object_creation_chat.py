"""Tests for object creation extraction from LLM responses —
_detect_create_object_blocks() and system prompt integration.

Covers: JSON fence detection, malformed input handling, missing fields,
command payload shape, system prompt content, and edge cases.
"""

import json

import pytest

from app.api.copilot import _detect_create_object_blocks
from app.copilot.service import _build_system_prompt


# ---------------------------------------------------------------------------
# _detect_create_object_blocks — extraction tests
# ---------------------------------------------------------------------------


class TestDetectCreateObjectBlocks:
    """Tests for _detect_create_object_blocks() helper."""

    def test_empty_text_returns_empty(self):
        """Plain text with no fences returns empty list."""
        assert _detect_create_object_blocks("Hello, no JSON here.") == []

    def test_no_json_fences_returns_empty(self):
        """Text with sparql fences but no json fences returns empty."""
        text = "```sparql\nSELECT ?s WHERE { ?s a ex:Foo }\n```"
        assert _detect_create_object_blocks(text) == []

    def test_single_create_object_block(self):
        """Detects a single valid create_object JSON block."""
        payload = {
            "action": "create_object",
            "type": "http://example.org/Task",
            "label": "Review Q1 goals",
            "properties": {"http://example.org/dueDate": "2026-03-28"},
        }
        text = f"Sure, I'll create that.\n```json\n{json.dumps(payload)}\n```\nDone!"
        blocks = _detect_create_object_blocks(text)
        assert len(blocks) == 1
        parsed, start, end = blocks[0]
        assert parsed["action"] == "create_object"
        assert parsed["type"] == "http://example.org/Task"
        assert parsed["label"] == "Review Q1 goals"
        assert parsed["properties"]["http://example.org/dueDate"] == "2026-03-28"
        assert start >= 0
        assert end > start

    def test_multiple_json_blocks_only_create_object(self):
        """Only blocks with action=create_object are returned; others are ignored."""
        create_payload = {
            "action": "create_object",
            "type": "http://example.org/Note",
            "label": "Meeting notes",
            "properties": {},
        }
        other_payload = {
            "action": "something_else",
            "data": "irrelevant",
        }
        text = (
            f"```json\n{json.dumps(other_payload)}\n```\n"
            f"And also:\n```json\n{json.dumps(create_payload)}\n```"
        )
        blocks = _detect_create_object_blocks(text)
        assert len(blocks) == 1
        assert blocks[0][0]["type"] == "http://example.org/Note"

    def test_multiple_create_object_blocks(self):
        """Detects multiple create_object blocks in a single response."""
        p1 = {"action": "create_object", "type": "http://ex.org/Task", "label": "A", "properties": {}}
        p2 = {"action": "create_object", "type": "http://ex.org/Note", "label": "B", "properties": {}}
        text = f"```json\n{json.dumps(p1)}\n```\nand\n```json\n{json.dumps(p2)}\n```"
        blocks = _detect_create_object_blocks(text)
        assert len(blocks) == 2
        assert blocks[0][0]["label"] == "A"
        assert blocks[1][0]["label"] == "B"

    def test_malformed_json_returns_empty(self):
        """Malformed JSON (missing closing brace) is skipped gracefully."""
        text = '```json\n{"action": "create_object", "type": "http://ex.org/Task"\n```'
        blocks = _detect_create_object_blocks(text)
        assert blocks == []

    def test_invalid_json_syntax_returns_empty(self):
        """Completely invalid JSON syntax is skipped gracefully."""
        text = "```json\nthis is not json at all\n```"
        blocks = _detect_create_object_blocks(text)
        assert blocks == []

    def test_json_without_action_field_returns_empty(self):
        """Valid JSON missing the 'action' key is not returned."""
        payload = {"type": "http://ex.org/Task", "label": "No action"}
        text = f"```json\n{json.dumps(payload)}\n```"
        blocks = _detect_create_object_blocks(text)
        assert blocks == []

    def test_json_with_wrong_action_returns_empty(self):
        """Valid JSON with action != 'create_object' is not returned."""
        payload = {"action": "delete_object", "type": "http://ex.org/Task"}
        text = f"```json\n{json.dumps(payload)}\n```"
        blocks = _detect_create_object_blocks(text)
        assert blocks == []

    def test_json_array_returns_empty(self):
        """A JSON array (not an object) is not returned."""
        text = '```json\n[{"action": "create_object"}]\n```'
        blocks = _detect_create_object_blocks(text)
        assert blocks == []

    def test_mixed_prose_and_json_isolates_block(self):
        """JSON block is correctly isolated from surrounding prose."""
        payload = {
            "action": "create_object",
            "type": "http://example.org/Project",
            "label": "Q2 Planning",
            "properties": {
                "http://example.org/description": "Quarterly planning project",
            },
        }
        text = (
            "I'll create a new project for you. Here's the structured data:\n\n"
            f"```json\n{json.dumps(payload, indent=2)}\n```\n\n"
            "The project has been prepared. Click Create to confirm."
        )
        blocks = _detect_create_object_blocks(text)
        assert len(blocks) == 1
        assert blocks[0][0]["label"] == "Q2 Planning"
        assert blocks[0][0]["properties"]["http://example.org/description"] == "Quarterly planning project"

    def test_incomplete_fence_returns_empty(self):
        """An unclosed JSON fence (no closing ```) returns empty — block not yet complete."""
        text = '```json\n{"action": "create_object", "type": "http://ex.org/Task"}'
        blocks = _detect_create_object_blocks(text)
        assert blocks == []

    def test_empty_properties_is_valid(self):
        """A create_object with empty properties dict is still detected."""
        payload = {"action": "create_object", "type": "http://ex.org/Task", "label": "Empty", "properties": {}}
        text = f"```json\n{json.dumps(payload)}\n```"
        blocks = _detect_create_object_blocks(text)
        assert len(blocks) == 1
        assert blocks[0][0]["properties"] == {}

    def test_no_label_field_still_detected(self):
        """A create_object without a 'label' field is still detected (label is optional in JSON)."""
        payload = {"action": "create_object", "type": "http://ex.org/Task", "properties": {"a": "b"}}
        text = f"```json\n{json.dumps(payload)}\n```"
        blocks = _detect_create_object_blocks(text)
        assert len(blocks) == 1
        assert "label" not in blocks[0][0]

    def test_positions_are_correct(self):
        """start and end positions span the full fenced block including backtick lines."""
        payload = {"action": "create_object", "type": "http://ex.org/X", "properties": {}}
        json_str = json.dumps(payload)
        prefix = "Before text\n"
        fence_block = f"```json\n{json_str}\n```"
        suffix = "\nAfter text"
        text = prefix + fence_block + suffix
        blocks = _detect_create_object_blocks(text)
        assert len(blocks) == 1
        _, start, end = blocks[0]
        assert text[start:end] == fence_block


# ---------------------------------------------------------------------------
# Command payload shape
# ---------------------------------------------------------------------------


class TestCommandPayloadShape:
    """Tests verifying the expected shape of object.create command payloads
    generated from detected blocks."""

    def test_command_shape_from_detected_block(self):
        """Detected block can be mapped to a valid object.create command."""
        payload = {
            "action": "create_object",
            "type": "http://example.org/Task",
            "label": "Review Q1 goals",
            "properties": {
                "http://example.org/dueDate": "2026-03-28",
                "http://purl.org/dc/terms/description": "Review quarterly goals",
            },
        }
        text = f"```json\n{json.dumps(payload)}\n```"
        blocks = _detect_create_object_blocks(text)
        assert len(blocks) == 1

        detected = blocks[0][0]
        # Build the command payload as the frontend would
        command = {
            "command": "object.create",
            "params": {
                "type": detected["type"],
                "properties": detected.get("properties", {}),
            },
        }
        if detected.get("label"):
            command["params"]["properties"]["http://purl.org/dc/terms/title"] = detected["label"]

        assert command["command"] == "object.create"
        assert command["params"]["type"] == "http://example.org/Task"
        assert "http://example.org/dueDate" in command["params"]["properties"]
        assert command["params"]["properties"]["http://purl.org/dc/terms/title"] == "Review Q1 goals"

    def test_command_shape_minimal(self):
        """Minimal create_object (type only, empty properties) produces valid command."""
        payload = {"action": "create_object", "type": "http://ex.org/Note", "properties": {}}
        text = f"```json\n{json.dumps(payload)}\n```"
        blocks = _detect_create_object_blocks(text)
        detected = blocks[0][0]

        command = {
            "command": "object.create",
            "params": {
                "type": detected["type"],
                "properties": detected.get("properties", {}),
            },
        }
        assert command["command"] == "object.create"
        assert command["params"]["type"] == "http://ex.org/Note"
        assert command["params"]["properties"] == {}


# ---------------------------------------------------------------------------
# System prompt content
# ---------------------------------------------------------------------------


class TestSystemPromptObjectCreation:
    """Tests that _build_system_prompt() includes object creation instructions."""

    def test_system_prompt_contains_create_object(self):
        """System prompt includes 'create_object' instructions."""
        prompt = _build_system_prompt("schema context here")
        assert "create_object" in prompt

    def test_system_prompt_contains_object_creation_section(self):
        """System prompt includes the Object Creation section header."""
        prompt = _build_system_prompt("schema context here")
        assert "Object Creation" in prompt

    def test_system_prompt_json_fence_instruction(self):
        """System prompt tells the LLM to use ```json fence for object creation."""
        prompt = _build_system_prompt("schema context here")
        assert "```json" in prompt

    def test_system_prompt_mentions_type_iri(self):
        """System prompt instructs to use full type IRI."""
        prompt = _build_system_prompt("schema context here")
        assert "full IRI" in prompt or "type_IRI" in prompt or "full_type_IRI" in prompt

    def test_system_prompt_mentions_iso_dates(self):
        """System prompt instructs ISO 8601 date format."""
        prompt = _build_system_prompt("schema context here")
        assert "ISO 8601" in prompt

    def test_system_prompt_with_persona_still_has_create_object(self):
        """Object creation instructions remain even when persona prompt is prepended."""
        prompt = _build_system_prompt(
            "schema context", persona_prompt="You are a research assistant."
        )
        assert "create_object" in prompt
        assert "research assistant" in prompt
