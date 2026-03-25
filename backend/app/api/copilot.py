"""Copilot router: SSE streaming chat with SPARQL generation and approval flow.

Provides ``POST /api/copilot/chat`` (SSE streaming endpoint that injects
schema context into the system prompt and proxies the LLM response with
inline SPARQL detection), ``POST /api/copilot/approve`` (executes or
rejects a SPARQL query proposed by the copilot), and conversation CRUD
endpoints for persistent chat threads.

All endpoints accept dual auth: session cookie + Bearer token via
``get_current_user_or_api``.
"""

import json
import logging
import re
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_or_api, scope_required
from app.auth.models import User
from app.auth.rate_limit import limiter
from app.copilot.context import GraphContextService
from app.copilot.conversation import ConversationService
from app.copilot.personas import AIPersonaService
from app.copilot.schemas import (
    CopilotChatRequest,
    CreatePersonaRequest,
    UpdatePersonaRequest,
)
from app.copilot.service import CopilotService, MAX_RETRIES, _build_system_prompt
from app.db.session import get_db_session
from app.services.llm import LLMConfigService

logger = logging.getLogger(__name__)

copilot_router = APIRouter(
    prefix="/api/copilot",
    tags=["copilot"],
    dependencies=[Depends(scope_required("copilot:use"))],
)

conversation_svc = ConversationService()
persona_svc = AIPersonaService()


# ---------------------------------------------------------------------------
# Conversation CRUD endpoints
# ---------------------------------------------------------------------------


class CreateConversationRequest(BaseModel):
    """Request body for creating a new conversation."""

    title: str | None = Field(None, description="Optional conversation title")


@copilot_router.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """List all conversations for the current user, most recent first."""
    convs = await conversation_svc.list_conversations(db, user.id)
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convs
    ]


@copilot_router.post("/conversations")
async def create_conversation(
    body: CreateConversationRequest,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new conversation for the current user."""
    conv = await conversation_svc.create_conversation(db, user.id, body.title)
    return {"id": str(conv.id), "title": conv.title}


@copilot_router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Get a conversation with all its messages."""
    try:
        return await conversation_svc.get_conversation(db, conversation_id, user.id)
    except ValueError:
        return JSONResponse(
            {"error": f"Conversation {conversation_id} not found"},
            status_code=404,
        )


@copilot_router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a conversation and all its messages."""
    deleted = await conversation_svc.delete_conversation(db, conversation_id, user.id)
    if not deleted:
        return JSONResponse(
            {"error": f"Conversation {conversation_id} not found"},
            status_code=404,
        )
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Persona CRUD endpoints
# ---------------------------------------------------------------------------


def _persona_to_response(p) -> dict:
    """Convert an AIPersona ORM object to a response dict."""
    return {
        "id": str(p.id),
        "name": p.name,
        "icon": p.icon,
        "system_prompt_template": p.system_prompt_template,
        "model_preference": p.model_preference,
        "temperature": p.temperature,
        "is_builtin": p.is_builtin,
        "is_active": p.is_active,
    }


@copilot_router.get("/personas")
async def list_personas(
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """List all AI personas for the current user. Seeds built-ins on first call."""
    personas = await persona_svc.list_for_user(db, user.id)
    await db.commit()
    return [_persona_to_response(p) for p in personas]


@copilot_router.post("/personas")
async def create_persona(
    body: CreatePersonaRequest,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a custom AI persona."""
    persona = await persona_svc.create(
        db,
        user_id=user.id,
        name=body.name,
        icon=body.icon,
        system_prompt_template=body.system_prompt_template,
        model_preference=body.model_preference,
        temperature=body.temperature,
    )
    await db.commit()
    return _persona_to_response(persona)


@copilot_router.put("/personas/{persona_id}")
async def update_persona(
    persona_id: UUID,
    body: UpdatePersonaRequest,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a custom persona. Built-in personas cannot be modified."""
    try:
        update_fields = body.model_dump(exclude_unset=True)
        persona = await persona_svc.update(
            db, persona_id, user.id, **update_fields
        )
        await db.commit()
        return _persona_to_response(persona)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@copilot_router.delete("/personas/{persona_id}")
async def delete_persona(
    persona_id: UUID,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a custom persona. Built-in personas cannot be deleted."""
    try:
        deleted = await persona_svc.delete(db, persona_id, user.id)
        await db.commit()
        if not deleted:
            return JSONResponse(
                {"error": f"Persona {persona_id} not found"}, status_code=404
            )
        return {"status": "deleted"}
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@copilot_router.post("/personas/{persona_id}/activate")
async def activate_persona(
    persona_id: UUID,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Set a persona as the active one for the current user."""
    try:
        persona = await persona_svc.set_active(db, user.id, persona_id)
        await db.commit()
        logger.info(
            "copilot.persona.activated: user_id=%s, persona_id=%s",
            user.id,
            persona_id,
        )
        return _persona_to_response(persona)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)


# ---------------------------------------------------------------------------
# SPARQL detection helpers
# ---------------------------------------------------------------------------

# Regex to detect the opening of a ```sparql code fence
_SPARQL_FENCE_OPEN = re.compile(r"```sparql\s*$", re.IGNORECASE | re.MULTILINE)
_FENCE_CLOSE = re.compile(r"^```\s*$", re.MULTILINE)
_JSON_FENCE_OPEN = re.compile(r"```json\s*$", re.IGNORECASE | re.MULTILINE)


def _detect_sparql_blocks(accumulated: str) -> list[tuple[str, int, int]]:
    """Detect complete ```sparql ... ``` code blocks in accumulated text.

    Returns a list of (query_text, start_char, end_char) for each block found.
    """
    blocks: list[tuple[str, int, int]] = []
    pos = 0
    while pos < len(accumulated):
        open_match = _SPARQL_FENCE_OPEN.search(accumulated, pos)
        if not open_match:
            break
        content_start = open_match.end()
        # Skip leading newline after fence opener
        if content_start < len(accumulated) and accumulated[content_start] == "\n":
            content_start += 1
        close_match = _FENCE_CLOSE.search(accumulated, content_start)
        if not close_match:
            break  # Block not yet complete
        query_text = accumulated[content_start:close_match.start()].strip()
        blocks.append((query_text, open_match.start(), close_match.end()))
        pos = close_match.end()
    return blocks


def _detect_create_object_blocks(accumulated: str) -> list[tuple[dict, int, int]]:
    """Detect complete ```json ... ``` code blocks containing create_object actions.

    Returns a list of (parsed_dict, start_char, end_char) for each valid block found.
    Only returns blocks where the JSON contains ``"action": "create_object"``.
    """
    blocks: list[tuple[dict, int, int]] = []
    pos = 0
    while pos < len(accumulated):
        open_match = _JSON_FENCE_OPEN.search(accumulated, pos)
        if not open_match:
            break
        content_start = open_match.end()
        if content_start < len(accumulated) and accumulated[content_start] == "\n":
            content_start += 1
        close_match = _FENCE_CLOSE.search(accumulated, content_start)
        if not close_match:
            break  # Block not yet complete
        raw_json = accumulated[content_start:close_match.start()].strip()
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict) and parsed.get("action") == "create_object":
                blocks.append((parsed, open_match.start(), close_match.end()))
        except json.JSONDecodeError:
            logger.warning(
                "copilot.chat.create_object_parse_error: raw=%s",
                raw_json[:200],
            )
        pos = close_match.end()
    return blocks


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _sse_event(data: str, event: str | None = None) -> str:
    """Format a single SSE event."""
    parts: list[str] = []
    if event:
        parts.append(f"event: {event}")
    parts.append(f"data: {data}")
    parts.append("")
    parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# POST /api/copilot/chat — SSE streaming endpoint
# ---------------------------------------------------------------------------


@copilot_router.post("/chat")
@limiter.limit("20/minute")
async def copilot_chat(
    request: Request,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """SSE streaming copilot chat with schema-aware system prompt.

    Receives ``CopilotChatRequest`` JSON body, builds a system prompt
    with the knowledge-graph schema context, prepends it to the user's
    messages, and proxies the streaming LLM response as SSE events.

    Detects ``\\`\\`\\`sparql`` code blocks in the streamed response and
    emits ``event: sparql_query`` SSE events with validation results
    so the frontend can render an approval widget.

    Returns ``text/event-stream`` with:
    - Standard ``data: {...}`` events (OpenAI chat completion chunks)
    - ``event: sparql_query`` events when SPARQL is detected
    - ``event: error`` events on failure
    - ``data: [DONE]`` sentinel when the stream ends
    """
    # Parse request body
    try:
        body = await request.json()
        chat_req = CopilotChatRequest(**body)
    except Exception as exc:
        logger.warning("copilot.chat.parse_error: %s", str(exc))

        async def parse_error_stream():
            yield _sse_event(json.dumps({"error": f"Invalid request: {str(exc)[:200]}"}), event="error")
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            parse_error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Fetch LLM config
    svc = LLMConfigService()
    config = await svc.get_config(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""

    if not base_url:
        logger.debug("copilot.chat.no_llm: user=%s", user.email)

        async def no_llm_stream():
            yield _sse_event(
                json.dumps({"error": "LLM not configured. Go to Settings → AI to set up your LLM provider."}),
                event="error",
            )
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            no_llm_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Build schema context via CopilotService
    copilot_svc = CopilotService(
        triplestore_client=request.app.state.triplestore_client,
        shapes_service=request.app.state.shapes_service,
        label_service=request.app.state.label_service,
        prefix_registry=request.app.state.prefix_registry,
    )
    schema_context = await copilot_svc.build_schema_context()

    # Build graph context for active object (if provided)
    graph_context_text: str | None = None
    if chat_req.active_object_iri:
        try:
            ctx_svc = GraphContextService(
                triplestore_client=request.app.state.triplestore_client,
                label_service=request.app.state.label_service,
                prefix_registry=request.app.state.prefix_registry,
            )
            neighborhood = await ctx_svc.get_neighborhood(chat_req.active_object_iri)
            graph_context_text = await ctx_svc.serialize_context(neighborhood)
            if graph_context_text:
                logger.info(
                    "copilot.chat.graph_context: iri=%s, chars=%d",
                    chat_req.active_object_iri,
                    len(graph_context_text),
                )
            else:
                logger.info(
                    "copilot.chat.graph_context: iri=%s, empty=true",
                    chat_req.active_object_iri,
                )
        except Exception as exc:
            logger.warning(
                "copilot.chat.graph_context_error: iri=%s, error=%s",
                chat_req.active_object_iri,
                str(exc),
                exc_info=True,
            )
            # Graceful degradation — proceed without graph context

    # -------------------------------------------------------------------
    # Persona lookup and system prompt construction
    # -------------------------------------------------------------------
    persona_prompt_rendered: str | None = None
    try:
        active_persona = None
        if chat_req.persona_id:
            try:
                pid = UUID(chat_req.persona_id)
                active_persona = await persona_svc.get(db, pid, user.id)
            except (ValueError, AttributeError):
                logger.warning(
                    "copilot.chat.invalid_persona_id: value=%s",
                    chat_req.persona_id,
                )

        if active_persona is None:
            # Fall back to user's active persona (seeding if needed)
            active_persona = await persona_svc.get_active(db, user.id)
            if active_persona is None:
                # Trigger seed and try again
                await persona_svc.seed_builtins(db, user.id)
                active_persona = await persona_svc.get_active(db, user.id)

        if active_persona:
            # Render the template with slot variables
            persona_prompt_rendered = active_persona.system_prompt_template.format(
                installed_models=schema_context[:200] if schema_context else "",
                type_schemas=schema_context if schema_context else "",
                current_context=graph_context_text if graph_context_text else "",
            )
            logger.info(
                "copilot.chat.persona_applied: persona_id=%s, name=%s",
                active_persona.id,
                active_persona.name,
            )
    except Exception as exc:
        logger.warning(
            "copilot.chat.persona_error: error=%s",
            str(exc),
            exc_info=True,
        )
        # Graceful degradation — proceed without persona prompt

    system_prompt = _build_system_prompt(
        schema_context,
        graph_context=graph_context_text,
        persona_prompt=persona_prompt_rendered,
    )

    # -------------------------------------------------------------------
    # Conversation persistence: load or auto-create
    # -------------------------------------------------------------------
    conversation_id: UUID | None = None
    auto_created_conversation = False
    conversation_title: str | None = None
    stored_history_messages: list[dict] = []

    if chat_req.conversation_id:
        try:
            conversation_id = UUID(chat_req.conversation_id)
        except (ValueError, AttributeError):
            logger.warning(
                "copilot.chat.invalid_conversation_id: value=%s",
                chat_req.conversation_id,
            )

    # Extract the user's latest message content for auto-titling and saving
    user_message_content = ""
    if chat_req.messages:
        for m in reversed(chat_req.messages):
            if m.get("role") == "user":
                user_message_content = m.get("content", "")
                break

    if conversation_id:
        # Load existing conversation history
        try:
            conv_data = await conversation_svc.get_conversation(db, conversation_id, user.id)
            for m in conv_data.get("messages", []):
                if m["role"] in ("user", "assistant"):
                    stored_history_messages.append(
                        {"role": m["role"], "content": m["content"]}
                    )
            logger.info(
                "copilot.chat.history_loaded: conversation_id=%s, history_count=%d",
                conversation_id,
                len(stored_history_messages),
            )
        except ValueError:
            logger.warning(
                "copilot.chat.conversation_not_found: conversation_id=%s, user_id=%s",
                conversation_id,
                user.id,
            )
            conversation_id = None  # Proceed without history
    else:
        # Auto-create a new conversation
        try:
            auto_title = user_message_content[:50].strip() if user_message_content else None
            if auto_title and len(user_message_content) > 50:
                auto_title += "…"
            conv = await conversation_svc.create_conversation(db, user.id, auto_title)
            conversation_id = conv.id
            conversation_title = conv.title
            auto_created_conversation = True
            logger.info(
                "copilot.chat.auto_created_conversation: conversation_id=%s, title=%s",
                conversation_id,
                conversation_title,
            )
        except Exception as exc:
            logger.warning(
                "copilot.chat.conversation_create_error: error=%s",
                str(exc),
                exc_info=True,
            )
            # Proceed without persistence

    # Prepare messages: system + stored history + current user messages
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(stored_history_messages)
    for msg in chat_req.messages:
        messages.append(msg)

    model = chat_req.model or config["default_model"] or "gpt-4o"
    api_key = await svc.get_decrypted_api_key(db)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages, "stream": True}

    logger.info(
        "copilot.chat.request: user=%s, model=%s, schema_context_size=%d, message_count=%d",
        user.email,
        model,
        len(schema_context),
        len(chat_req.messages),
    )

    async def event_stream():
        accumulated_content = ""
        sparql_blocks_emitted = 0
        # Track which blocks we already emitted so we don't re-emit
        emitted_block_ends: set[int] = set()

        # Emit conversation_created event if we auto-created
        if auto_created_conversation and conversation_id:
            yield _sse_event(
                json.dumps({
                    "conversation_id": str(conversation_id),
                    "title": conversation_title or "New Chat",
                }),
                event="conversation_created",
            )

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        error_body = ""
                        async for chunk in response.aiter_text():
                            error_body += chunk
                        logger.warning(
                            "copilot.chat.llm_error: status=%d, body=%s",
                            response.status_code,
                            error_body[:500],
                        )
                        yield _sse_event(
                            json.dumps({"error": f"LLM returned status {response.status_code}"}),
                            event="error",
                        )
                        yield "data: [DONE]\n\n"
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        # Forward the raw SSE line from the LLM
                        yield f"{line}\n\n"

                        # Parse the line for content accumulation
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                continue
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content_token = delta.get("content", "")
                                if content_token:
                                    accumulated_content += content_token

                                    # Check for complete SPARQL blocks
                                    blocks = _detect_sparql_blocks(accumulated_content)
                                    for query_text, _start, end in blocks:
                                        if end in emitted_block_ends:
                                            continue
                                        emitted_block_ends.add(end)
                                        sparql_blocks_emitted += 1

                                        # Validate the query
                                        valid, error = await copilot_svc.validate_query(query_text)
                                        sparql_event = {
                                            "query": query_text,
                                            "valid": valid,
                                            "error": error,
                                        }
                                        yield _sse_event(
                                            json.dumps(sparql_event),
                                            event="sparql_query",
                                        )
                                        logger.info(
                                            "copilot.chat.sparql_detected: valid=%s, error=%s",
                                            valid,
                                            error,
                                        )

                                    # Check for create_object JSON blocks
                                    co_blocks = _detect_create_object_blocks(accumulated_content)
                                    for parsed_obj, _co_start, co_end in co_blocks:
                                        if co_end in emitted_block_ends:
                                            continue
                                        emitted_block_ends.add(co_end)
                                        yield _sse_event(
                                            json.dumps(parsed_obj),
                                            event="create_object",
                                        )
                                        logger.info(
                                            "copilot.chat.create_object_detected: type=%s, properties=%s",
                                            parsed_obj.get("type", ""),
                                            list(parsed_obj.get("properties", {}).keys()),
                                        )
                            except (json.JSONDecodeError, IndexError, KeyError):
                                pass  # Not all lines are parseable JSON chunks

        except httpx.ReadTimeout:
            logger.warning("copilot.chat.timeout: user=%s", user.email)
            yield _sse_event(
                json.dumps({"error": "LLM request timed out after 300s"}),
                event="error",
            )
        except Exception as e:
            logger.warning("copilot.chat.error: %s", str(e), exc_info=True)
            yield _sse_event(
                json.dumps({"error": f"Stream error: {str(e)[:200]}"}),
                event="error",
            )

        # Save messages to conversation after stream completes
        if conversation_id and accumulated_content:
            try:
                # Save the user's message
                if user_message_content:
                    await conversation_svc.add_message(
                        db, conversation_id, "user", user_message_content
                    )
                # Save the assistant's response
                await conversation_svc.add_message(
                    db, conversation_id, "assistant", accumulated_content
                )
                await db.commit()
                logger.info(
                    "copilot.chat.messages_saved: conversation_id=%s",
                    conversation_id,
                )
            except Exception as save_exc:
                logger.warning(
                    "copilot.chat.message_save_error: conversation_id=%s, error=%s",
                    conversation_id,
                    str(save_exc),
                    exc_info=True,
                )

        # Final done sentinel (always emitted)
        yield "data: [DONE]\n\n"

        logger.info(
            "copilot.chat.complete: user=%s, sparql_detected=%d, content_len=%d",
            user.email,
            sparql_blocks_emitted,
            len(accumulated_content),
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# POST /api/copilot/approve — SPARQL query approval
# ---------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    """Request body for the SPARQL approval endpoint."""

    query: str = Field(..., description="The SPARQL query string")
    action: str = Field(..., description="One of: approve, reject, edit, retry")
    edited_query: str | None = Field(None, description="Edited query (when action=edit)")
    error: str | None = Field(None, description="Error message from previous attempt (when action=retry)")
    retry_count: int = Field(0, description="Current retry count (0-based, max 2)")


@copilot_router.post("/approve")
async def copilot_approve(
    body: ApproveRequest,
    request: Request,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Execute, reject, edit, or retry a SPARQL query proposed by the copilot.

    Actions:
    - ``approve``: validate and execute the query, return formatted results.
    - ``reject``: return ``{"status": "rejected"}``.
    - ``edit``: re-validate the edited query, then execute if valid.
    - ``retry``: feed the error back to the LLM for self-correction,
      return a new query for another approval round. Max 2 retries (3 total).
    """
    logger.info(
        "copilot.approve.request: user=%s, action=%s, query_len=%d",
        user.email,
        body.action,
        len(body.query),
    )

    if body.action == "reject":
        logger.info("copilot.approve.rejected: user=%s", user.email)
        return JSONResponse({"status": "rejected"})

    # Build CopilotService
    copilot_svc = CopilotService(
        triplestore_client=request.app.state.triplestore_client,
        shapes_service=request.app.state.shapes_service,
        label_service=request.app.state.label_service,
        prefix_registry=request.app.state.prefix_registry,
    )

    # --- Retry: self-correction via LLM ---
    if body.action == "retry":
        if body.retry_count >= MAX_RETRIES:
            logger.warning(
                "copilot.approve.max_retries: user=%s, retries=%d",
                user.email,
                body.retry_count,
            )
            return JSONResponse({
                "status": "max_retries",
                "error": "Unable to generate a valid query after 3 attempts. Try rephrasing your question.",
            })

        # Build retry prompt and call LLM
        svc = LLMConfigService()
        config = await svc.get_config(db)
        base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""

        if not base_url:
            return JSONResponse(
                {"status": "error", "error": "LLM not configured"},
                status_code=400,
            )

        api_key = await svc.get_decrypted_api_key(db)
        model = config["default_model"] or "gpt-4o"

        schema_context = await copilot_svc.build_schema_context()
        system_prompt = _build_system_prompt(schema_context)

        retry_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": f"```sparql\n{body.query}\n```"},
            {
                "role": "user",
                "content": (
                    f"The previous SPARQL query failed with this error: {body.error}\n\n"
                    "Please generate a corrected SPARQL query that fixes this issue. "
                    "Respond with the corrected query in a ```sparql code block."
                ),
            },
        ]

        llm_headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            llm_headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{base_url}/v1/chat/completions",
                    headers=llm_headers,
                    json={"model": model, "messages": retry_messages, "stream": False},
                )
                if resp.status_code != 200:
                    logger.warning(
                        "copilot.approve.retry_llm_error: status=%d",
                        resp.status_code,
                    )
                    return JSONResponse(
                        {"status": "error", "error": f"LLM returned status {resp.status_code}"},
                        status_code=502,
                    )

                result_json = resp.json()
                new_content = result_json["choices"][0]["message"]["content"]

        except httpx.ReadTimeout:
            return JSONResponse(
                {"status": "error", "error": "LLM request timed out"},
                status_code=504,
            )
        except Exception as e:
            logger.warning("copilot.approve.retry_error: %s", str(e), exc_info=True)
            return JSONResponse(
                {"status": "error", "error": f"Retry failed: {str(e)[:200]}"},
                status_code=500,
            )

        # Extract SPARQL from the LLM response
        from app.copilot.service import _extract_sparql_from_response

        new_query = _extract_sparql_from_response(new_content)
        if not new_query:
            logger.warning(
                "copilot.approve.retry_no_sparql: user=%s, attempt=%d",
                user.email,
                body.retry_count + 1,
            )
            return JSONResponse({
                "status": "retry_result",
                "new_query": None,
                "valid": False,
                "error": "LLM did not produce a SPARQL query in its response",
                "retry_count": body.retry_count + 1,
            })

        # Validate the new query
        valid, validation_error = await copilot_svc.validate_query(new_query)
        logger.info(
            "copilot.approve.retry: user=%s, attempt=%d, valid=%s",
            user.email,
            body.retry_count + 1,
            valid,
        )
        return JSONResponse({
            "status": "retry_result",
            "new_query": new_query,
            "valid": valid,
            "error": validation_error,
            "retry_count": body.retry_count + 1,
        })

    # --- Approve / Edit: execute the query ---
    # Determine which query to use
    query = body.query
    if body.action == "edit":
        if not body.edited_query:
            return JSONResponse(
                {"error": "edited_query is required when action=edit"},
                status_code=400,
            )
        query = body.edited_query

    # Validate the query
    valid, error = await copilot_svc.validate_query(query)
    if not valid:
        logger.warning(
            "copilot.approve.validation_failed: user=%s, error=%s",
            user.email,
            error,
        )
        return JSONResponse(
            {"status": "error", "error": f"Query validation failed: {error}"},
            status_code=400,
        )

    # Execute and format
    try:
        result = await copilot_svc.execute_and_format(query)
        logger.info(
            "copilot.approve.executed: user=%s, bindings=%d, iris=%d",
            user.email,
            len(result.bindings),
            len(result.object_iris),
        )
        return JSONResponse({
            "status": "approved",
            "prose": result.prose,
            "bindings": result.bindings,
            "object_iris": result.object_iris,
        })
    except Exception as e:
        logger.warning(
            "copilot.approve.execution_error: user=%s, error=%s",
            user.email,
            str(e),
            exc_info=True,
        )
        return JSONResponse(
            {"status": "error", "error": f"Query execution failed: {str(e)[:300]}"},
            status_code=500,
        )
