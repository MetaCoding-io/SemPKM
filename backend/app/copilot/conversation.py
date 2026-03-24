"""ConversationService: CRUD operations for copilot conversation persistence.

All methods accept an AsyncSession and operate within the caller's
transaction scope — no internal commit/rollback.
"""

import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.copilot.models import CopilotConversation, CopilotMessage

logger = logging.getLogger(__name__)


class ConversationService:
    """Manages copilot conversation threads and messages in SQLite."""

    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: UUID,
        title: str | None = None,
    ) -> CopilotConversation:
        """Create a new conversation for the given user.

        If no title is provided, defaults to 'New Chat'. The auto-title
        logic (first user message content) is handled by add_message().
        """
        conv = CopilotConversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title or "New Chat",
        )
        db.add(conv)
        await db.flush()

        logger.info(
            "copilot.conversation.created: conversation_id=%s, user_id=%s",
            conv.id,
            user_id,
        )
        return conv

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> list[CopilotConversation]:
        """List all conversations for a user, ordered by most recently updated."""
        stmt = (
            select(CopilotConversation)
            .where(CopilotConversation.user_id == user_id)
            .order_by(CopilotConversation.updated_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Get a conversation with its messages.

        Returns a dict with conversation metadata and messages list.
        Raises ValueError if conversation not found or belongs to another user.
        """
        stmt = select(CopilotConversation).where(
            CopilotConversation.id == conversation_id,
            CopilotConversation.user_id == user_id,
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()

        if conv is None:
            raise ValueError(
                f"Conversation {conversation_id} not found for user {user_id}"
            )

        # Fetch messages ordered by creation time
        msg_stmt = (
            select(CopilotMessage)
            .where(CopilotMessage.conversation_id == conversation_id)
            .order_by(CopilotMessage.created_at.asc())
        )
        msg_result = await db.execute(msg_stmt)
        messages = list(msg_result.scalars().all())

        logger.info(
            "copilot.conversation.loaded: conversation_id=%s, message_count=%d",
            conversation_id,
            len(messages),
        )

        return {
            "id": str(conv.id),
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a conversation and its messages (cascade).

        Returns True if the conversation existed and was deleted.
        """
        # Verify ownership first
        stmt = select(CopilotConversation).where(
            CopilotConversation.id == conversation_id,
            CopilotConversation.user_id == user_id,
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()

        if conv is None:
            return False

        # Delete messages first (SQLite may not enforce FK cascades)
        await db.execute(
            delete(CopilotMessage).where(
                CopilotMessage.conversation_id == conversation_id
            )
        )
        await db.execute(
            delete(CopilotConversation).where(
                CopilotConversation.id == conversation_id
            )
        )
        await db.flush()

        logger.info(
            "copilot.conversation.deleted: conversation_id=%s, user_id=%s",
            conversation_id,
            user_id,
        )
        return True

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        role: str,
        content: str,
    ) -> CopilotMessage:
        """Add a message to a conversation and touch its updated_at.

        Auto-title: if this is the first user message and the conversation
        title is still 'New Chat', update the title to the first 50 chars
        of the message content.
        """
        # Check auto-title eligibility BEFORE adding the message
        # (SQLAlchemy auto-flushes pending adds before SELECT queries)
        should_auto_title = False
        if role == "user":
            conv_stmt = select(CopilotConversation).where(
                CopilotConversation.id == conversation_id
            )
            conv_result = await db.execute(conv_stmt)
            conv = conv_result.scalar_one_or_none()

            if conv and conv.title == "New Chat":
                count_stmt = (
                    select(CopilotMessage)
                    .where(
                        CopilotMessage.conversation_id == conversation_id,
                        CopilotMessage.role == "user",
                    )
                )
                count_result = await db.execute(count_stmt)
                existing_user_msgs = list(count_result.scalars().all())
                if len(existing_user_msgs) == 0:
                    should_auto_title = True

        msg = CopilotMessage(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        db.add(msg)

        # Touch the conversation's updated_at
        now = datetime.now(timezone.utc)
        await db.execute(
            update(CopilotConversation)
            .where(CopilotConversation.id == conversation_id)
            .values(updated_at=now)
        )

        # Apply auto-title if eligible
        if should_auto_title:
            auto_title = content[:50].strip()
            if len(content) > 50:
                auto_title += "…"
            await db.execute(
                update(CopilotConversation)
                .where(CopilotConversation.id == conversation_id)
                .values(title=auto_title)
            )
            logger.info(
                "copilot.conversation.auto_titled: conversation_id=%s, title=%s",
                conversation_id,
                auto_title,
            )

        await db.flush()

        logger.info(
            "copilot.message.saved: conversation_id=%s, role=%s",
            conversation_id,
            role,
        )
        return msg

    async def update_title(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        title: str,
    ) -> None:
        """Update a conversation's title."""
        await db.execute(
            update(CopilotConversation)
            .where(CopilotConversation.id == conversation_id)
            .values(title=title)
        )
        await db.flush()
