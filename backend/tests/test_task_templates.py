"""Tests for TaskTemplateService — RDF-backed task template CRUD & instantiation."""

import json
from unittest.mock import AsyncMock

import pytest

from app.task_templates.service import (
    TEMPLATE_GRAPH,
    TEMPLATE_IRI_PREFIX,
    TaskTemplateService,
    _safe_json_loads,
)


# ---- helpers ----------------------------------------------------------------


def _sparql_bindings(*rows: dict[str, str]) -> dict:
    """Build a SPARQL JSON result dict from simple key→value rows.

    Mirrors the RDF4J ``application/sparql-results+json`` format.
    Each row is ``{"var_name": "value", ...}`` — all values become
    ``{"type": "literal", "value": ...}`` bindings.
    """
    return {
        "results": {
            "bindings": [
                {k: {"type": "literal", "value": v} for k, v in row.items()}
                for row in rows
            ]
        }
    }


def _empty_bindings() -> dict:
    """SPARQL result with zero bindings."""
    return {"results": {"bindings": []}}


# ---- fixtures ---------------------------------------------------------------


@pytest.fixture
def mock_triplestore():
    """AsyncMock of TriplestoreClient with query/update stubs."""
    client = AsyncMock()
    client.query = AsyncMock(return_value=_empty_bindings())
    client.update = AsyncMock(return_value=None)
    return client


@pytest.fixture
def service(mock_triplestore):
    """TaskTemplateService wired to the mock triplestore."""
    return TaskTemplateService(mock_triplestore)


# ---- create -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_template(service, mock_triplestore):
    """create() inserts triples into the task-templates named graph and
    returns a dict with the generated IRI, title, and parsed properties."""
    result = await service.create(
        title="Sprint Planning",
        target_class="urn:sempkm:model:basic-pkm:Task",
        default_properties={"bpkm:taskStatus": "todo"},
        subtask_definitions=[{"title": "Review backlog"}],
    )

    # Returned dict shape
    assert result["title"] == "Sprint Planning"
    assert result["target_class"] == "urn:sempkm:model:basic-pkm:Task"
    assert result["default_properties"] == {"bpkm:taskStatus": "todo"}
    assert result["subtask_definitions"] == [{"title": "Review backlog"}]
    assert result["id"].startswith(TEMPLATE_IRI_PREFIX)
    assert "created" in result

    # SPARQL update was called once with an INSERT DATA targeting the named graph
    mock_triplestore.update.assert_called_once()
    sparql = mock_triplestore.update.call_args[0][0]
    assert "INSERT DATA" in sparql
    assert f"GRAPH <{TEMPLATE_GRAPH}>" in sparql
    assert "Sprint Planning" in sparql
    assert "urn:sempkm:model:basic-pkm:Task" in sparql

    # JSON blobs are serialised in the SPARQL
    assert '"bpkm:taskStatus"' in sparql or "bpkm:taskStatus" in sparql
    assert "Review backlog" in sparql


@pytest.mark.asyncio
async def test_create_template_defaults(service, mock_triplestore):
    """create() with no properties/subtasks stores empty JSON blobs."""
    result = await service.create(
        title="Bare Template",
        target_class="urn:sempkm:model:basic-pkm:Note",
    )

    assert result["default_properties"] == {}
    assert result["subtask_definitions"] == []

    sparql = mock_triplestore.update.call_args[0][0]
    assert '{}' in sparql   # empty default_properties JSON
    assert '[]' in sparql   # empty subtask_definitions JSON


@pytest.mark.asyncio
async def test_create_template_escapes_special_chars(service, mock_triplestore):
    """create() escapes quotes and newlines in the title for SPARQL safety."""
    await service.create(
        title='Template with "quotes" and\nnewlines',
        target_class="urn:example:Type",
    )

    sparql = mock_triplestore.update.call_args[0][0]
    # Raw double-quotes must be escaped
    assert r'\"quotes\"' in sparql
    # Raw newlines must be escaped
    assert r'\n' in sparql


# ---- list -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_templates(service, mock_triplestore):
    """list_all() parses SPARQL bindings into template dicts."""
    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "id": "urn:sempkm:task-template:aaa",
            "title": "Alpha",
            "target_class": "urn:sempkm:model:basic-pkm:Task",
            "created": "2026-03-22T01:00:00Z",
        },
        {
            "id": "urn:sempkm:task-template:bbb",
            "title": "Beta",
            "target_class": "urn:sempkm:model:basic-pkm:Note",
            "created": "2026-03-22T02:00:00Z",
        },
    )

    result = await service.list_all()

    assert len(result) == 2
    assert result[0]["id"] == "urn:sempkm:task-template:aaa"
    assert result[0]["title"] == "Alpha"
    assert result[1]["title"] == "Beta"

    # Verify SPARQL query targets the named graph
    sparql = mock_triplestore.query.call_args[0][0]
    assert f"GRAPH <{TEMPLATE_GRAPH}>" in sparql


@pytest.mark.asyncio
async def test_list_templates_empty(service, mock_triplestore):
    """list_all() returns an empty list when no templates exist."""
    mock_triplestore.query.return_value = _empty_bindings()
    result = await service.list_all()
    assert result == []


# ---- get --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_template(service, mock_triplestore):
    """get() returns a dict with parsed JSON blobs for properties and subtasks."""
    props = {"bpkm:taskStatus": "todo", "bpkm:priority": "high"}
    subtasks = [
        {"title": "Subtask A", "type": "urn:sempkm:model:basic-pkm:Task"},
        {"title": "Subtask B"},
    ]

    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "Sprint Planning",
            "target_class": "urn:sempkm:model:basic-pkm:Task",
            "props": json.dumps(props),
            "subtasks": json.dumps(subtasks),
            "created": "2026-03-22T01:00:00Z",
        }
    )

    template_id = "urn:sempkm:task-template:test-123"
    result = await service.get(template_id)

    assert result is not None
    assert result["id"] == template_id
    assert result["title"] == "Sprint Planning"
    assert result["target_class"] == "urn:sempkm:model:basic-pkm:Task"

    # JSON blobs are parsed into Python dicts/lists, not raw strings
    assert isinstance(result["default_properties"], dict)
    assert result["default_properties"] == props
    assert isinstance(result["subtask_definitions"], list)
    assert result["subtask_definitions"] == subtasks
    assert len(result["subtask_definitions"]) == 2


@pytest.mark.asyncio
async def test_get_template_not_found(service, mock_triplestore):
    """get() returns None when no bindings are found."""
    mock_triplestore.query.return_value = _empty_bindings()

    result = await service.get("urn:sempkm:task-template:nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_get_template_malformed_json(service, mock_triplestore):
    """get() returns default values when JSON blobs are malformed."""
    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "Broken",
            "target_class": "urn:type:X",
            "props": "not-valid-json",
            "subtasks": "{also broken",
            "created": "2026-01-01T00:00:00Z",
        }
    )

    result = await service.get("urn:sempkm:task-template:broken")

    assert result is not None
    assert result["default_properties"] == {}  # fallback default
    assert result["subtask_definitions"] == []  # fallback default


# ---- update -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_template_title(service, mock_triplestore):
    """update() issues DELETE DATA + INSERT DATA for the changed field."""
    # Mock get() to find the existing template
    existing_props = {"bpkm:taskStatus": "todo"}
    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "Old Title",
            "target_class": "urn:sempkm:model:basic-pkm:Task",
            "props": json.dumps(existing_props),
            "subtasks": "[]",
            "created": "2026-03-22T01:00:00Z",
        }
    )

    template_id = "urn:sempkm:task-template:update-me"
    result = await service.update(template_id, title="New Title")

    assert result is not None
    assert result["title"] == "New Title"

    # update() calls query() first (for get), then update()
    mock_triplestore.update.assert_called_once()
    sparql = mock_triplestore.update.call_args[0][0]
    assert "DELETE DATA" in sparql
    assert "INSERT DATA" in sparql
    assert "Old Title" in sparql
    assert "New Title" in sparql
    assert f"GRAPH <{TEMPLATE_GRAPH}>" in sparql


@pytest.mark.asyncio
async def test_update_template_not_found(service, mock_triplestore):
    """update() returns None if the template doesn't exist."""
    mock_triplestore.query.return_value = _empty_bindings()

    result = await service.update("urn:sempkm:task-template:ghost", title="X")

    assert result is None
    mock_triplestore.update.assert_not_called()


@pytest.mark.asyncio
async def test_update_template_no_changes(service, mock_triplestore):
    """update() with no updatable fields returns existing template unchanged."""
    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "Unchanged",
            "target_class": "urn:type:X",
            "props": "{}",
            "subtasks": "[]",
            "created": "2026-01-01T00:00:00Z",
        }
    )

    result = await service.update("urn:sempkm:task-template:noop")

    assert result is not None
    assert result["title"] == "Unchanged"
    mock_triplestore.update.assert_not_called()


@pytest.mark.asyncio
async def test_update_template_multiple_fields(service, mock_triplestore):
    """update() handles multiple fields in a single call."""
    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "Old",
            "target_class": "urn:type:OldType",
            "props": "{}",
            "subtasks": "[]",
            "created": "2026-01-01T00:00:00Z",
        }
    )

    result = await service.update(
        "urn:sempkm:task-template:multi",
        title="New",
        target_class="urn:type:NewType",
        default_properties={"key": "val"},
    )

    assert result["title"] == "New"
    assert result["target_class"] == "urn:type:NewType"
    assert result["default_properties"] == {"key": "val"}

    sparql = mock_triplestore.update.call_args[0][0]
    assert "dcterms:title" in sparql
    assert "sempkm:targetClass" in sparql
    assert "sempkm:defaultProperties" in sparql


# ---- delete -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_template(service, mock_triplestore):
    """delete() issues DELETE WHERE against the named graph and returns True."""
    # Mock get() to find the template
    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "Doomed",
            "target_class": "urn:type:X",
            "props": "{}",
            "subtasks": "[]",
            "created": "2026-01-01T00:00:00Z",
        }
    )

    template_id = "urn:sempkm:task-template:delete-me"
    result = await service.delete(template_id)

    assert result is True
    mock_triplestore.update.assert_called_once()

    sparql = mock_triplestore.update.call_args[0][0]
    assert "DELETE WHERE" in sparql
    assert f"GRAPH <{TEMPLATE_GRAPH}>" in sparql
    assert template_id in sparql


@pytest.mark.asyncio
async def test_delete_template_not_found(service, mock_triplestore):
    """delete() returns False when the template doesn't exist."""
    mock_triplestore.query.return_value = _empty_bindings()

    result = await service.delete("urn:sempkm:task-template:ghost")

    assert result is False
    mock_triplestore.update.assert_not_called()


# ---- instantiate (no subtasks) ----------------------------------------------


@pytest.mark.asyncio
async def test_instantiate_without_subtasks(service, mock_triplestore):
    """instantiate() with no subtask_definitions returns a single
    object.create command with slot='main' and merged properties."""
    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "Simple Template",
            "target_class": "urn:sempkm:model:basic-pkm:Note",
            "props": json.dumps({"bpkm:priority": "low"}),
            "subtasks": "[]",
            "created": "2026-01-01T00:00:00Z",
        }
    )

    commands = await service.instantiate("urn:sempkm:task-template:simple")

    assert len(commands) == 1
    cmd = commands[0]
    assert cmd["command"] == "object.create"
    assert cmd["slot"] == "main"
    assert cmd["params"]["type"] == "urn:sempkm:model:basic-pkm:Note"
    assert cmd["params"]["properties"] == {"bpkm:priority": "low"}


@pytest.mark.asyncio
async def test_instantiate_with_user_overrides(service, mock_triplestore):
    """instantiate() merges user_overrides on top of template defaults."""
    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "With Defaults",
            "target_class": "urn:type:Task",
            "props": json.dumps({"bpkm:taskStatus": "todo", "bpkm:priority": "low"}),
            "subtasks": "[]",
            "created": "2026-01-01T00:00:00Z",
        }
    )

    commands = await service.instantiate(
        "urn:sempkm:task-template:x",
        user_overrides={"bpkm:priority": "high", "dcterms:title": "My Task"},
    )

    props = commands[0]["params"]["properties"]
    # Override replaces default
    assert props["bpkm:priority"] == "high"
    # Template default survives
    assert props["bpkm:taskStatus"] == "todo"
    # User-provided new property merged in
    assert props["dcterms:title"] == "My Task"


# ---- instantiate (with subtasks) --------------------------------------------


@pytest.mark.asyncio
async def test_instantiate_with_subtasks(service, mock_triplestore):
    """instantiate() with subtask_definitions generates object.create +
    edge.create pairs with correct @slot: references."""
    subtask_defs = [
        {"title": "Review backlog", "type": "urn:type:SubTask"},
        {"title": "Estimate stories", "properties": {"bpkm:priority": "high"}},
    ]

    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "Sprint Planning",
            "target_class": "urn:sempkm:model:basic-pkm:Task",
            "props": json.dumps({"bpkm:taskStatus": "todo"}),
            "subtasks": json.dumps(subtask_defs),
            "created": "2026-01-01T00:00:00Z",
        }
    )

    commands = await service.instantiate("urn:sempkm:task-template:sprint")

    # 1 main + 2 subtask creates + 2 edge creates = 5
    assert len(commands) == 5

    # First command: main object with slot="main"
    main = commands[0]
    assert main["command"] == "object.create"
    assert main["slot"] == "main"
    assert main["params"]["type"] == "urn:sempkm:model:basic-pkm:Task"
    assert main["params"]["properties"] == {"bpkm:taskStatus": "todo"}

    # Second command: first subtask create
    sub1_create = commands[1]
    assert sub1_create["command"] == "object.create"
    assert sub1_create["slot"] == "subtask_0"
    assert sub1_create["params"]["type"] == "urn:type:SubTask"
    assert sub1_create["params"]["properties"]["dcterms:title"] == "Review backlog"

    # Third command: first subtask edge
    sub1_edge = commands[2]
    assert sub1_edge["command"] == "edge.create"
    assert sub1_edge["params"]["source"] == "@slot:subtask_0"
    assert sub1_edge["params"]["target"] == "@slot:main"
    assert sub1_edge["params"]["predicate"] == "sempkm:subtaskOf"

    # Fourth command: second subtask create (inherits parent type)
    sub2_create = commands[3]
    assert sub2_create["command"] == "object.create"
    assert sub2_create["slot"] == "subtask_1"
    assert sub2_create["params"]["type"] == "urn:sempkm:model:basic-pkm:Task"
    assert sub2_create["params"]["properties"]["bpkm:priority"] == "high"
    assert sub2_create["params"]["properties"]["dcterms:title"] == "Estimate stories"

    # Fifth command: second subtask edge
    sub2_edge = commands[4]
    assert sub2_edge["command"] == "edge.create"
    assert sub2_edge["params"]["source"] == "@slot:subtask_1"
    assert sub2_edge["params"]["target"] == "@slot:main"


@pytest.mark.asyncio
async def test_instantiate_custom_predicate(service, mock_triplestore):
    """instantiate() respects custom predicate on subtask definitions."""
    subtask_defs = [
        {"title": "Step 1", "predicate": "bpkm:hasStep"},
    ]

    mock_triplestore.query.return_value = _sparql_bindings(
        {
            "title": "Workflow",
            "target_class": "urn:type:Workflow",
            "props": "{}",
            "subtasks": json.dumps(subtask_defs),
            "created": "2026-01-01T00:00:00Z",
        }
    )

    commands = await service.instantiate("urn:sempkm:task-template:wf")

    edge = commands[2]
    assert edge["command"] == "edge.create"
    assert edge["params"]["predicate"] == "bpkm:hasStep"


# ---- instantiate (error cases) ----------------------------------------------


@pytest.mark.asyncio
async def test_instantiate_not_found_raises(service, mock_triplestore):
    """instantiate() raises ValueError when the template doesn't exist."""
    mock_triplestore.query.return_value = _empty_bindings()

    with pytest.raises(ValueError, match="Template not found"):
        await service.instantiate("urn:sempkm:task-template:nonexistent")


# ---- _safe_json_loads -------------------------------------------------------


def test_safe_json_loads_valid():
    """_safe_json_loads parses valid JSON."""
    assert _safe_json_loads('{"a": 1}', {}) == {"a": 1}
    assert _safe_json_loads("[1, 2]", []) == [1, 2]


def test_safe_json_loads_invalid():
    """_safe_json_loads returns the default on bad input."""
    assert _safe_json_loads("not json", {}) == {}
    assert _safe_json_loads(None, []) == []
    assert _safe_json_loads("", "fallback") == "fallback"
