"""SQLAlchemy ORM models for copilot conversation persistence.

Tables: copilot_conversations (chat threads per user),
copilot_messages (individual messages within a conversation),
ai_personas (AI persona definitions with system prompt templates).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CopilotConversation(Base):
    """A copilot chat conversation thread, scoped per user."""

    __tablename__ = "copilot_conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CopilotMessage(Base):
    """A single message within a copilot conversation."""

    __tablename__ = "copilot_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("copilot_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AIPersona(Base):
    """An AI persona definition with a system prompt template.

    Built-in personas are seeded on first access and cannot be
    modified or deleted. Users can create custom personas.
    Only one persona per user is active at a time (is_active=True).
    """

    __tablename__ = "ai_personas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str] = mapped_column(String(50))  # emoji or lucide icon name
    system_prompt_template: Mapped[str] = mapped_column(Text())
    model_preference: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    temperature: Mapped[float] = mapped_column(Float(), default=0.7)
    is_builtin: Mapped[bool] = mapped_column(Boolean(), default=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
