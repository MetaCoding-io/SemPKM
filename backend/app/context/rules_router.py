"""Context Rules CRUD API — manage auto-persona switching rules.

Endpoints:
- GET    /api/context/rules       — list rules for authenticated user
- POST   /api/context/rules       — create a new rule
- PUT    /api/context/rules/{id}  — update a rule
- DELETE /api/context/rules/{id}  — delete a rule
- POST   /api/context/rules/test  — evaluate rules against current context (read-only)
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.context.rules_engine import RulesEngine
from app.context.service import ContextService
from app.dependencies import get_context_service, get_rules_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context/rules", tags=["context-rules"])


# ── Request / Response models ────────────────────────────────────


class RuleCreateRequest(BaseModel):
    """Payload for POST /api/context/rules."""

    name: str = Field(..., min_length=1, max_length=255)
    conditions: dict = Field(...)
    persona_id: str = Field(..., min_length=1, max_length=36)
    priority: int = Field(default=0)
    enabled: bool = Field(default=True)


class RuleUpdateRequest(BaseModel):
    """Payload for PUT /api/context/rules/{rule_id}. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    conditions: dict | None = None
    persona_id: str | None = Field(default=None, min_length=1, max_length=36)
    priority: int | None = None
    enabled: bool | None = None


def _rule_to_dict(rule) -> dict:
    """Convert a ContextRule ORM instance to a JSON-serializable dict."""
    return {
        "id": str(rule.id),
        "user_id": str(rule.user_id),
        "name": rule.name,
        "conditions": rule.conditions or {},
        "persona_id": rule.persona_id,
        "priority": rule.priority,
        "enabled": rule.enabled,
        "created_at": rule.created_at.isoformat() if isinstance(rule.created_at, datetime) else str(rule.created_at or ""),
        "updated_at": rule.updated_at.isoformat() if isinstance(rule.updated_at, datetime) else str(rule.updated_at or ""),
    }


# ── Endpoints ────────────────────────────────────────────────────


@router.get("/")
async def list_rules(
    user: User = Depends(get_current_user_or_api),
    engine: RulesEngine = Depends(get_rules_engine),
):
    """List all context rules for the authenticated user."""
    rules = await engine.list_rules(user.id)
    return [_rule_to_dict(r) for r in rules]


@router.post("/", status_code=201)
async def create_rule(
    body: RuleCreateRequest,
    user: User = Depends(get_current_user_or_api),
    engine: RulesEngine = Depends(get_rules_engine),
):
    """Create a new context rule."""
    rule = await engine.create_rule(
        user_id=user.id,
        name=body.name,
        conditions=body.conditions,
        persona_id=body.persona_id,
        priority=body.priority,
        enabled=body.enabled,
    )
    return _rule_to_dict(rule)


@router.put("/{rule_id}")
async def update_rule(
    rule_id: uuid.UUID,
    body: RuleUpdateRequest,
    user: User = Depends(get_current_user_or_api),
    engine: RulesEngine = Depends(get_rules_engine),
):
    """Update a context rule. Only provided fields are changed."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")

    rule = await engine.update_rule(rule_id, user.id, **updates)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_dict(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID,
    user: User = Depends(get_current_user_or_api),
    engine: RulesEngine = Depends(get_rules_engine),
):
    """Delete a context rule."""
    deleted = await engine.delete_rule(rule_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return None


@router.post("/test")
async def test_rules(
    user: User = Depends(get_current_user_or_api),
    engine: RulesEngine = Depends(get_rules_engine),
    service: ContextService = Depends(get_context_service),
):
    """Evaluate rules against the user's current context. No side effects.

    Returns ``{"match": true, "persona_id": "...", "rule_name": "..."}``
    when a rule matches, or ``{"match": false}`` otherwise.
    """
    ctx = await service.get_current(user.id)
    if ctx is None:
        return {"match": False, "reason": "no_context"}

    # Build context dict from ContextData fields
    import dataclasses

    context_data = dataclasses.asdict(ctx)

    matched_persona_id = await engine.evaluate(user.id, context_data)
    if matched_persona_id:
        # Find the rule name for the response
        rules = await engine.list_rules(user.id)
        rule_name = next(
            (r.name for r in rules if r.persona_id == matched_persona_id and r.enabled),
            "unknown",
        )
        return {
            "match": True,
            "persona_id": matched_persona_id,
            "rule_name": rule_name,
        }
    return {"match": False}
