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
    active_object_iri: str | None = Field(
        None, description="IRI of the active object tab for graph context injection"
    )
    persona_id: str | None = Field(
        None, description="Optional persona ID to use for this chat turn"
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


class PersonaResponse(BaseModel):
    """REST response for an AI persona."""

    id: str = Field(..., description="Persona UUID")
    name: str = Field(..., description="Display name")
    icon: str = Field(..., description="Emoji or lucide icon name")
    system_prompt_template: str = Field(..., description="System prompt template text")
    model_preference: str | None = Field(None, description="Preferred LLM model")
    temperature: float = Field(0.7, description="Temperature setting")
    is_builtin: bool = Field(False, description="Whether this is a built-in persona")
    is_active: bool = Field(False, description="Whether this persona is currently active")


class CreatePersonaRequest(BaseModel):
    """Request body for creating a custom persona."""

    name: str = Field(..., description="Persona display name", max_length=100)
    icon: str = Field(..., description="Emoji or lucide icon name", max_length=50)
    system_prompt_template: str = Field(..., description="System prompt template")
    model_preference: str | None = Field(None, description="Preferred LLM model")
    temperature: float = Field(0.7, description="Temperature 0.0-2.0", ge=0.0, le=2.0)


class UpdatePersonaRequest(BaseModel):
    """Request body for updating a custom persona."""

    name: str | None = Field(None, max_length=100)
    icon: str | None = Field(None, max_length=50)
    system_prompt_template: str | None = None
    model_preference: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
