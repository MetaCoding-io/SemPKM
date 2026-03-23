"""Pydantic request/response schemas for the copilot chat module."""

from pydantic import BaseModel, Field


class CopilotChatRequest(BaseModel):
    """Incoming chat request from the frontend."""

    messages: list[dict] = Field(
        ..., description="Chat message history [{role, content}, ...]"
    )
    conversation_id: str | None = Field(
        None, description="Optional conversation ID for continuity"
    )
    model: str | None = Field(
        None, description="Optional LLM model override"
    )


class CopilotMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content text")


class SparqlGenerationResult(BaseModel):
    """Result of SPARQL generation from a user question."""

    query: str | None = Field(None, description="Generated SPARQL query text")
    error: str | None = Field(None, description="Error message if generation failed")
    retries: int = Field(0, description="Number of self-correction retries used")


class QueryExecutionResult(BaseModel):
    """Result of executing a SPARQL query and formatting the output."""

    bindings: list[dict] = Field(
        default_factory=list, description="Raw SPARQL result bindings"
    )
    prose: str = Field("", description="Human-readable prose answer with [[iri|label]] markers")
    object_iris: list[str] = Field(
        default_factory=list,
        description="IRIs of knowledge-graph objects found in results",
    )
