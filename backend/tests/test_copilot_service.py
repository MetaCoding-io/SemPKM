"""Unit tests for CopilotService — schema context, SPARQL validation,
self-correction loop, and query execution/formatting.

Uses mocked TriplestoreClient, ShapesService, LabelService, and
PrefixRegistry to test the service in isolation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.copilot.schemas import (
    CopilotChatRequest,
    CopilotMessage,
    QueryExecutionResult,
    SparqlGenerationResult,
)
from app.copilot.service import (
    CopilotService,
    _extract_sparql_from_response,
    _build_system_prompt,
    MAX_RETRIES,
)
from app.services.shapes import NodeShapeForm, PropertyShape


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_shapes_service():
    svc = AsyncMock()
    svc.get_node_shapes.return_value = [
        NodeShapeForm(
            shape_iri="urn:shapes:ProjectShape",
            target_class="https://example.org/ontology/Project",
            label="Project",
            properties=[
                PropertyShape(
                    path="http://purl.org/dc/terms/title",
                    name="Title",
                    datatype="http://www.w3.org/2001/XMLSchema#string",
                    order=1.0,
                ),
                PropertyShape(
                    path="http://purl.org/dc/terms/description",
                    name="Description",
                    datatype="http://www.w3.org/2001/XMLSchema#string",
                    order=2.0,
                ),
            ],
        ),
        NodeShapeForm(
            shape_iri="urn:shapes:NoteShape",
            target_class="https://example.org/ontology/Note",
            label="Note",
            properties=[
                PropertyShape(
                    path="http://purl.org/dc/terms/title",
                    name="Title",
                    datatype="http://www.w3.org/2001/XMLSchema#string",
                    order=1.0,
                ),
            ],
        ),
    ]
    svc.get_labels_for_predicates.return_value = {
        "http://purl.org/dc/terms/title": "Title",
        "http://purl.org/dc/terms/description": "Description",
    }
    return svc


@pytest.fixture
def mock_triplestore():
    client = AsyncMock()
    client.query.return_value = {
        "results": {
            "bindings": [
                {
                    "count": {"type": "literal", "value": "3"},
                }
            ]
        }
    }
    return client


@pytest.fixture
def mock_label_service():
    svc = AsyncMock()
    svc.resolve_batch.return_value = {
        "https://example.org/data/p1": "Project Alpha",
        "https://example.org/data/p2": "Project Beta",
    }
    return svc


@pytest.fixture
def mock_prefix_registry():
    reg = MagicMock()
    reg.get_all_prefixes.return_value = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "dcterms": "http://purl.org/dc/terms/",
        "schema": "https://schema.org/",
    }
    reg.compact.side_effect = lambda iri: {
        "http://www.w3.org/2001/XMLSchema#string": "xsd:string",
        "http://purl.org/dc/terms/title": "dcterms:title",
        "http://purl.org/dc/terms/description": "dcterms:description",
    }.get(iri, iri)
    reg.expand.side_effect = lambda qname: {
        "dcterms:title": "http://purl.org/dc/terms/title",
        "rdf:type": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    }.get(qname)
    return reg


@pytest.fixture
def service(mock_triplestore, mock_shapes_service, mock_label_service, mock_prefix_registry):
    return CopilotService(
        triplestore_client=mock_triplestore,
        shapes_service=mock_shapes_service,
        label_service=mock_label_service,
        prefix_registry=mock_prefix_registry,
    )


# ---------------------------------------------------------------------------
# Schema context tests
# ---------------------------------------------------------------------------


class TestBuildSchemaContext:
    @pytest.mark.asyncio
    async def test_produces_readable_text_with_types_and_properties(self, service):
        """build_schema_context returns text with type names, property paths, datatypes."""
        ctx = await service.build_schema_context()

        assert "Project" in ctx
        assert "Note" in ctx
        assert "dcterms:title" in ctx
        assert "xsd:string" in ctx
        assert "Prefix Table" in ctx

    @pytest.mark.asyncio
    async def test_includes_prefix_table(self, service):
        ctx = await service.build_schema_context()
        assert "rdf:" in ctx
        assert "dcterms:" in ctx

    @pytest.mark.asyncio
    async def test_truncates_at_token_budget(self, service):
        """With a very small budget, text is truncated."""
        ctx = await service.build_schema_context(token_budget=10)
        # 10 tokens * 4 chars = 40 chars max before truncation marker
        assert "truncated" in ctx

    @pytest.mark.asyncio
    async def test_empty_shapes_returns_prefix_table_only(
        self, mock_triplestore, mock_label_service, mock_prefix_registry
    ):
        empty_shapes = AsyncMock()
        empty_shapes.get_node_shapes.return_value = []
        svc = CopilotService(mock_triplestore, empty_shapes, mock_label_service, mock_prefix_registry)
        ctx = await svc.build_schema_context()
        assert "Prefix Table" in ctx
        assert "Knowledge Graph Types" in ctx


# ---------------------------------------------------------------------------
# SPARQL validation tests
# ---------------------------------------------------------------------------


class TestValidateQuery:
    @pytest.mark.asyncio
    async def test_accepts_valid_select(self, service):
        valid, error = await service.validate_query(
            "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"
        )
        assert valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_accepts_valid_ask(self, service):
        valid, error = await service.validate_query(
            "ASK { ?s a <https://example.org/ontology/Project> }"
        )
        assert valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_accepts_valid_construct(self, service):
        valid, error = await service.validate_query(
            "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
        )
        assert valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_rejects_insert(self, service):
        valid, error = await service.validate_query(
            "INSERT DATA { <s> <p> <o> }"
        )
        assert valid is False
        assert "INSERT" in error

    @pytest.mark.asyncio
    async def test_rejects_delete(self, service):
        valid, error = await service.validate_query(
            "DELETE WHERE { ?s ?p ?o }"
        )
        assert valid is False
        assert "DELETE" in error

    @pytest.mark.asyncio
    async def test_rejects_drop(self, service):
        valid, error = await service.validate_query("DROP GRAPH <urn:test>")
        assert valid is False
        assert "DROP" in error

    @pytest.mark.asyncio
    async def test_rejects_clear(self, service):
        valid, error = await service.validate_query("CLEAR ALL")
        assert valid is False
        assert "CLEAR" in error

    @pytest.mark.asyncio
    async def test_rejects_no_read_keyword(self, service):
        valid, error = await service.validate_query("FOOBAR { ?s ?p ?o }")
        assert valid is False
        assert "read keyword" in error.lower()

    @pytest.mark.asyncio
    async def test_warns_on_unknown_predicates(self, service, mock_shapes_service):
        """Unknown predicates trigger a warning log but don't reject the query."""
        mock_shapes_service.get_labels_for_predicates.return_value = {}
        valid, error = await service.validate_query(
            "SELECT ?s WHERE { ?s <http://unknown.org/pred> ?o }"
        )
        # Query is still valid — unknown predicates are non-blocking
        assert valid is True
        assert error is None


# ---------------------------------------------------------------------------
# Query execution tests
# ---------------------------------------------------------------------------


class TestExecuteAndFormat:
    @pytest.mark.asyncio
    async def test_returns_prose_with_iri_markers(self, service, mock_triplestore):
        """execute_and_format returns prose with [[iri|label]] markers."""
        mock_triplestore.query.return_value = {
            "results": {
                "bindings": [
                    {
                        "project": {
                            "type": "uri",
                            "value": "https://example.org/data/p1",
                        },
                        "title": {
                            "type": "literal",
                            "value": "Project Alpha",
                        },
                    },
                    {
                        "project": {
                            "type": "uri",
                            "value": "https://example.org/data/p2",
                        },
                        "title": {
                            "type": "literal",
                            "value": "Project Beta",
                        },
                    },
                ]
            }
        }
        result = await service.execute_and_format(
            "SELECT ?project ?title WHERE { ?project a <Project> ; dcterms:title ?title }"
        )
        assert isinstance(result, QueryExecutionResult)
        assert "[[https://example.org/data/p1|Project Alpha]]" in result.prose
        assert "[[https://example.org/data/p2|Project Beta]]" in result.prose
        assert "https://example.org/data/p1" in result.object_iris
        assert "https://example.org/data/p2" in result.object_iris

    @pytest.mark.asyncio
    async def test_empty_results(self, service, mock_triplestore):
        mock_triplestore.query.return_value = {"results": {"bindings": []}}
        result = await service.execute_and_format("SELECT ?s WHERE { ?s ?p ?o }")
        assert "no results" in result.prose.lower()
        assert result.object_iris == []

    @pytest.mark.asyncio
    async def test_count_result(self, service, mock_triplestore):
        mock_triplestore.query.return_value = {
            "results": {"bindings": [{"count": {"type": "literal", "value": "5"}}]}
        }
        result = await service.execute_and_format(
            "SELECT (COUNT(?s) AS ?count) WHERE { ?s a <Project> }"
        )
        assert "5" in result.prose


# ---------------------------------------------------------------------------
# SPARQL extraction tests
# ---------------------------------------------------------------------------


class TestExtractSparqlFromResponse:
    def test_extracts_from_sparql_code_block(self):
        text = """Here's a query:
```sparql
SELECT ?s WHERE { ?s a <Project> }
```
"""
        assert _extract_sparql_from_response(text) == "SELECT ?s WHERE { ?s a <Project> }"

    def test_extracts_from_sql_code_block(self):
        text = """```sql
SELECT ?count WHERE { ?s a <Note> }
```"""
        assert _extract_sparql_from_response(text) == "SELECT ?count WHERE { ?s a <Note> }"

    def test_extracts_from_generic_code_block(self):
        text = """```
SELECT ?s ?p ?o WHERE { ?s ?p ?o }
```"""
        assert _extract_sparql_from_response(text) == "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"

    def test_extracts_raw_sparql_heuristic(self):
        text = """PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT ?title WHERE {
  ?s dcterms:title ?title
}"""
        result = _extract_sparql_from_response(text)
        assert result is not None
        assert "SELECT" in result
        assert "dcterms:title" in result

    def test_returns_none_for_no_sparql(self):
        text = "I don't know how to answer that question."
        assert _extract_sparql_from_response(text) is None

    def test_ignores_mutation_in_generic_block(self):
        text = """```
INSERT DATA { <s> <p> <o> }
```"""
        # Generic code block won't match because INSERT is not a read keyword
        assert _extract_sparql_from_response(text) is None


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    def test_includes_role_and_schema(self):
        prompt = _build_system_prompt("## Types\nProject")
        assert "SPARQL assistant" in prompt
        assert "## Types" in prompt
        assert "Project" in prompt
        assert "```sparql" in prompt
        assert "[[iri|label]]" in prompt


# ---------------------------------------------------------------------------
# Self-correction loop tests
# ---------------------------------------------------------------------------


class TestGenerateSparql:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self, service):
        async def mock_llm(messages):
            return "```sparql\nSELECT (COUNT(?s) AS ?count) WHERE { ?s a <Project> }\n```"

        result = await service.generate_sparql(
            "How many projects?", "schema context", mock_llm
        )
        assert isinstance(result, SparqlGenerationResult)
        assert result.query is not None
        assert "SELECT" in result.query
        assert result.error is None
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_retries_on_first_failure_succeeds_on_second(self, service):
        call_count = 0

        async def mock_llm(messages):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "I'm not sure, here's something:\nINSERT DATA { <s> <p> <o> }"
            return "```sparql\nSELECT ?s WHERE { ?s a <Project> }\n```"

        result = await service.generate_sparql(
            "List projects", "schema context", mock_llm
        )
        assert result.query is not None
        assert result.retries == 1
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exhausts_retries(self, service):
        async def mock_llm(messages):
            return "I don't know how to write that query."

        result = await service.generate_sparql(
            "Do something impossible", "schema context", mock_llm
        )
        assert result.query is None
        assert result.error is not None
        assert result.retries == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_llm_call_exception(self, service):
        async def mock_llm(messages):
            raise RuntimeError("API timeout")

        result = await service.generate_sparql(
            "Count projects", "schema context", mock_llm
        )
        assert result.query is None
        assert "LLM call failed" in result.error
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_max_retries_is_two(self):
        """D324: max 2 retries."""
        assert MAX_RETRIES == 2


# ---------------------------------------------------------------------------
# Pydantic schema tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Additional validation tests (T05)
# ---------------------------------------------------------------------------


class TestValidateQueryExtended:
    """Extended validation tests added in T05 to cover edge cases."""

    @pytest.mark.asyncio
    async def test_mutation_keyword_inside_string_literal_is_caught(self, service):
        """Known limitation: mutation keyword check is regex-based and does
        not strip string literals first, so DELETE inside a SPARQL string
        literal is still flagged as forbidden."""
        valid, error = await service.validate_query(
            'SELECT ?s WHERE { ?s <http://example.org/desc> "to DELETE old records" }'
        )
        # This documents actual behavior — the regex catches DELETE even
        # inside quotes. A future improvement could strip string literals
        # before checking.
        assert valid is False
        assert "DELETE" in error

    @pytest.mark.asyncio
    async def test_accepts_known_predicates(self, service, mock_shapes_service):
        """Query using only predicates known to the shapes service passes
        without warnings."""
        # mock_shapes_service.get_labels_for_predicates returns labels for
        # dcterms:title and dcterms:description by default
        valid, error = await service.validate_query(
            "SELECT ?s ?title WHERE { "
            "?s <http://purl.org/dc/terms/title> ?title }"
        )
        assert valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_rejects_load(self, service):
        valid, error = await service.validate_query("LOAD <http://example.org/data>")
        assert valid is False
        assert "LOAD" in error

    @pytest.mark.asyncio
    async def test_rejects_create(self, service):
        valid, error = await service.validate_query("CREATE GRAPH <urn:test>")
        assert valid is False
        assert "CREATE" in error

    @pytest.mark.asyncio
    async def test_accepts_describe(self, service):
        valid, error = await service.validate_query(
            "DESCRIBE <https://example.org/data/p1>"
        )
        assert valid is True
        assert error is None


# ---------------------------------------------------------------------------
# Extended result formatting tests (T05)
# ---------------------------------------------------------------------------


class TestExecuteAndFormatExtended:
    """Extended formatting tests added in T05."""

    @pytest.mark.asyncio
    async def test_tabular_multiple_bindings(self, service, mock_triplestore):
        """Multi-row results produce an enumerated list."""
        mock_triplestore.query.return_value = {
            "results": {
                "bindings": [
                    {
                        "title": {"type": "literal", "value": "Alpha"},
                        "status": {"type": "literal", "value": "Active"},
                    },
                    {
                        "title": {"type": "literal", "value": "Beta"},
                        "status": {"type": "literal", "value": "Completed"},
                    },
                    {
                        "title": {"type": "literal", "value": "Gamma"},
                        "status": {"type": "literal", "value": "Draft"},
                    },
                ]
            }
        }
        result = await service.execute_and_format(
            "SELECT ?title ?status WHERE { ?s a <Project> ; dcterms:title ?title ; bpkm:status ?status }"
        )
        assert "1." in result.prose
        assert "2." in result.prose
        assert "3." in result.prose
        assert "Alpha" in result.prose
        assert "Gamma" in result.prose

    @pytest.mark.asyncio
    async def test_resolves_iris_via_label_service(self, service, mock_triplestore, mock_label_service):
        """IRI values are resolved via LabelService and rendered as [[iri|label]] markers."""
        mock_triplestore.query.return_value = {
            "results": {
                "bindings": [
                    {
                        "project": {
                            "type": "uri",
                            "value": "https://example.org/data/p1",
                        },
                        "title": {
                            "type": "literal",
                            "value": "Alpha",
                        },
                    },
                    {
                        "project": {
                            "type": "uri",
                            "value": "https://example.org/data/p2",
                        },
                        "title": {
                            "type": "literal",
                            "value": "Beta",
                        },
                    },
                ]
            }
        }
        result = await service.execute_and_format(
            "SELECT ?project ?title WHERE { ?project a <Project> ; dcterms:title ?title }"
        )
        # LabelService mock resolves p1→"Project Alpha", p2→"Project Beta"
        assert "[[https://example.org/data/p1|Project Alpha]]" in result.prose
        assert "[[https://example.org/data/p2|Project Beta]]" in result.prose
        mock_label_service.resolve_batch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_literal_only_results_have_no_iris(self, service, mock_triplestore):
        """Results with only literal values produce no object_iris."""
        mock_triplestore.query.return_value = {
            "results": {
                "bindings": [
                    {"name": {"type": "literal", "value": "Foo"}},
                    {"name": {"type": "literal", "value": "Bar"}},
                ]
            }
        }
        result = await service.execute_and_format(
            "SELECT ?name WHERE { ?s rdfs:label ?name }"
        )
        assert result.object_iris == []
        assert "Foo" in result.prose

    @pytest.mark.asyncio
    async def test_query_error_propagates(self, service, mock_triplestore):
        """When the triplestore raises an exception, execute_and_format propagates it."""
        mock_triplestore.query.side_effect = RuntimeError("SPARQL timeout")
        with pytest.raises(RuntimeError, match="SPARQL timeout"):
            await service.execute_and_format("SELECT ?s WHERE { ?s ?p ?o }")


# ---------------------------------------------------------------------------
# Extended system prompt tests (T05)
# ---------------------------------------------------------------------------


class TestBuildSystemPromptExtended:
    """Extended system prompt tests added in T05."""

    def test_includes_select_only_instructions(self):
        prompt = _build_system_prompt("schema ctx")
        # Must instruct LLM to use only read-only queries
        assert "SELECT" in prompt
        assert "INSERT" in prompt.upper() or "Never use INSERT" in prompt or "mutation" in prompt.lower()

    def test_includes_graph_clause_instruction(self):
        prompt = _build_system_prompt("schema ctx")
        # Must mention that graph scoping is automatic
        assert "graph" in prompt.lower() or "FROM" in prompt

    def test_includes_object_link_format(self):
        prompt = _build_system_prompt("schema ctx")
        assert "[[" in prompt
        assert "]]" in prompt


# ---------------------------------------------------------------------------
# Retry conversation tests (T05)
# ---------------------------------------------------------------------------


class TestRetryConversation:
    """Verify that the self-correction loop builds correct retry messages."""

    @pytest.mark.asyncio
    async def test_retry_includes_error_in_feedback(self, service):
        """When validation fails, the retry message includes the validation error."""
        captured_messages = []

        async def capture_llm(messages):
            captured_messages.append(list(messages))
            if len(captured_messages) == 1:
                return "```sparql\nINSERT DATA { <s> <p> <o> }\n```"
            return "```sparql\nSELECT ?s WHERE { ?s a <Project> }\n```"

        await service.generate_sparql("List projects", "schema ctx", capture_llm)

        # Second call should have retry feedback with the error
        assert len(captured_messages) >= 2
        retry_msgs = captured_messages[1]
        # Last user message should contain the validation error
        last_user_msg = [m for m in retry_msgs if m["role"] == "user"][-1]
        assert "forbidden mutation keyword" in last_user_msg["content"].lower() or \
               "INSERT" in last_user_msg["content"]

    @pytest.mark.asyncio
    async def test_retry_includes_original_response(self, service):
        """Retry messages include the original LLM response as assistant context."""
        captured_messages = []
        original_response = "Here's my attempt:\n```sparql\nINSERT DATA { <s> <p> <o> }\n```"

        async def capture_llm(messages):
            captured_messages.append(list(messages))
            if len(captured_messages) == 1:
                return original_response
            return "```sparql\nSELECT ?s WHERE { ?s a <Project> }\n```"

        await service.generate_sparql("List projects", "schema ctx", capture_llm)

        assert len(captured_messages) >= 2
        retry_msgs = captured_messages[1]
        assistant_msgs = [m for m in retry_msgs if m["role"] == "assistant"]
        assert len(assistant_msgs) >= 1
        assert original_response in assistant_msgs[0]["content"]


# ---------------------------------------------------------------------------
# Schema context extended tests (T05)
# ---------------------------------------------------------------------------


class TestBuildSchemaContextExtended:
    """Extended schema context tests added in T05."""

    @pytest.mark.asyncio
    async def test_includes_enum_values(
        self, mock_triplestore, mock_label_service, mock_prefix_registry
    ):
        """Schema context includes sh:in enum values when present."""
        shapes_svc = AsyncMock()
        shapes_svc.get_node_shapes.return_value = [
            NodeShapeForm(
                shape_iri="urn:shapes:TaskShape",
                target_class="https://example.org/ontology/Task",
                label="Task",
                properties=[
                    PropertyShape(
                        path="https://example.org/ontology/status",
                        name="Status",
                        datatype=None,
                        order=1.0,
                        in_values=["Active", "Completed", "Draft"],
                    ),
                ],
            ),
        ]
        svc = CopilotService(mock_triplestore, shapes_svc, mock_label_service, mock_prefix_registry)
        ctx = await svc.build_schema_context()
        assert "Active" in ctx
        assert "Completed" in ctx
        assert "Draft" in ctx
        assert "values:" in ctx

    @pytest.mark.asyncio
    async def test_includes_object_property_references(
        self, mock_triplestore, mock_label_service, mock_prefix_registry
    ):
        """Schema context includes target_class for object properties."""
        shapes_svc = AsyncMock()
        shapes_svc.get_node_shapes.return_value = [
            NodeShapeForm(
                shape_iri="urn:shapes:TaskShape",
                target_class="https://example.org/ontology/Task",
                label="Task",
                properties=[
                    PropertyShape(
                        path="https://example.org/ontology/assignedTo",
                        name="Assigned To",
                        datatype=None,
                        target_class="https://example.org/ontology/Person",
                        order=1.0,
                    ),
                ],
            ),
        ]
        svc = CopilotService(mock_triplestore, shapes_svc, mock_label_service, mock_prefix_registry)
        ctx = await svc.build_schema_context()
        assert "Assigned To" in ctx
        assert "object:" in ctx


# ---------------------------------------------------------------------------
# Pydantic schema tests
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_copilot_chat_request_schema(self):
        schema = CopilotChatRequest.model_json_schema()
        assert "messages" in schema["properties"]
        assert schema["properties"]["messages"]["type"] == "array"

    def test_copilot_message_schema(self):
        msg = CopilotMessage(role="user", content="Hello")
        assert msg.role == "user"

    def test_sparql_generation_result_defaults(self):
        result = SparqlGenerationResult()
        assert result.query is None
        assert result.error is None
        assert result.retries == 0

    def test_query_execution_result_defaults(self):
        result = QueryExecutionResult()
        assert result.bindings == []
        assert result.prose == ""
        assert result.object_iris == []
