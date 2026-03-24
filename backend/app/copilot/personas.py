"""AIPersonaService: CRUD and built-in seeding for AI copilot personas.

Follows the ConversationService pattern — stateless class, all methods
accept an AsyncSession, operate within the caller's transaction scope.
"""

import logging
import uuid
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.copilot.models import AIPersona

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Built-in persona definitions
# ---------------------------------------------------------------------------

_BUILTIN_PERSONAS = [
    {
        "name": "General Assistant",
        "icon": "🤖",
        "system_prompt_template": (
            "You are a helpful general-purpose assistant for a personal knowledge management system.\n\n"
            "The user's knowledge graph contains these types and properties:\n"
            "{type_schemas}\n\n"
            "Installed models: {installed_models}\n\n"
            "{current_context}\n\n"
            "Be concise and practical. When the user asks about their data, "
            "suggest SPARQL queries or reference specific objects when possible. "
            "Provide clear, actionable answers."
        ),
        "temperature": 0.7,
        "is_active": True,  # default active persona
    },
    {
        "name": "Research Assistant",
        "icon": "🔬",
        "system_prompt_template": (
            "You are a meticulous research assistant specializing in knowledge organization "
            "and citation-based analysis.\n\n"
            "The user's knowledge graph contains these types and properties:\n"
            "{type_schemas}\n\n"
            "Installed models: {installed_models}\n\n"
            "{current_context}\n\n"
            "When answering questions:\n"
            "- Always cite specific objects from the knowledge graph using [[iri|label]] notation\n"
            "- Cross-reference related items and highlight connections\n"
            "- Structure responses with clear headings and numbered points\n"
            "- When uncertain, explicitly state assumptions and suggest verification queries\n"
            "- Prefer depth over brevity — thorough analysis is valued"
        ),
        "temperature": 0.5,
        "is_active": False,
    },
    {
        "name": "Project Manager",
        "icon": "📋",
        "system_prompt_template": (
            "You are a project management assistant focused on task tracking, "
            "deadlines, dependencies, and status reporting.\n\n"
            "The user's knowledge graph contains these types and properties:\n"
            "{type_schemas}\n\n"
            "Installed models: {installed_models}\n\n"
            "{current_context}\n\n"
            "When helping the user:\n"
            "- Focus on actionable next steps and deliverables\n"
            "- Highlight overdue tasks, approaching deadlines, and blocked items\n"
            "- Suggest task breakdowns and prioritization\n"
            "- Use status-oriented language (done, in-progress, blocked, not-started)\n"
            "- When creating objects, prefer Task types with due dates and status fields\n"
            "- Summarize project health concisely"
        ),
        "temperature": 0.6,
        "is_active": False,
    },
    {
        "name": "Writing Coach",
        "icon": "✍️",
        "system_prompt_template": (
            "You are a writing coach who helps the user draft, refine, and organize "
            "written content stored in their knowledge graph.\n\n"
            "The user's knowledge graph contains these types and properties:\n"
            "{type_schemas}\n\n"
            "Installed models: {installed_models}\n\n"
            "{current_context}\n\n"
            "When helping the user:\n"
            "- Focus on clarity, structure, and tone\n"
            "- Suggest improvements to drafts referenced from the knowledge graph\n"
            "- Help organize notes and ideas into coherent outlines\n"
            "- Offer alternative phrasings and identify redundancy\n"
            "- When creating objects, prefer Note types with rich body content\n"
            "- Be encouraging but honest about areas for improvement"
        ),
        "temperature": 0.8,
        "is_active": False,
    },
]


class AIPersonaService:
    """Manages AI copilot personas — CRUD, built-in seeding, activation."""

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    async def seed_builtins(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> int:
        """Seed the 4 built-in personas for a user if none exist.

        Returns the number of personas created (0 if already seeded).
        """
        stmt = select(AIPersona).where(
            AIPersona.user_id == user_id,
            AIPersona.is_builtin == True,  # noqa: E712
        )
        result = await db.execute(stmt)
        existing = list(result.scalars().all())

        if existing:
            return 0

        count = 0
        for defn in _BUILTIN_PERSONAS:
            persona = AIPersona(
                id=uuid.uuid4(),
                user_id=user_id,
                name=defn["name"],
                icon=defn["icon"],
                system_prompt_template=defn["system_prompt_template"],
                temperature=defn["temperature"],
                is_builtin=True,
                is_active=defn["is_active"],
            )
            db.add(persona)
            count += 1

        await db.flush()

        logger.info(
            "copilot.persona.seeded: user_id=%s, count=%d",
            user_id,
            count,
        )
        return count

    # ------------------------------------------------------------------
    # List / Get
    # ------------------------------------------------------------------

    async def list_for_user(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> list[AIPersona]:
        """List all personas for a user, seeding built-ins on first call."""
        # Lazy seed: if no personas exist, create built-ins
        count_stmt = select(AIPersona).where(AIPersona.user_id == user_id)
        count_result = await db.execute(count_stmt)
        if not list(count_result.scalars().all()):
            await self.seed_builtins(db, user_id)

        stmt = (
            select(AIPersona)
            .where(AIPersona.user_id == user_id)
            .order_by(AIPersona.is_builtin.desc(), AIPersona.name.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get(
        self,
        db: AsyncSession,
        persona_id: UUID,
        user_id: UUID,
    ) -> AIPersona | None:
        """Get a single persona by ID, scoped to user."""
        stmt = select(AIPersona).where(
            AIPersona.id == persona_id,
            AIPersona.user_id == user_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Create / Update / Delete
    # ------------------------------------------------------------------

    async def create(
        self,
        db: AsyncSession,
        user_id: UUID,
        name: str,
        icon: str,
        system_prompt_template: str,
        model_preference: str | None = None,
        temperature: float = 0.7,
    ) -> AIPersona:
        """Create a custom (non-builtin) persona."""
        persona = AIPersona(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            icon=icon,
            system_prompt_template=system_prompt_template,
            model_preference=model_preference,
            temperature=temperature,
            is_builtin=False,
            is_active=False,
        )
        db.add(persona)
        await db.flush()

        logger.info(
            "copilot.persona.created: persona_id=%s, user_id=%s, name=%s",
            persona.id,
            user_id,
            name,
        )
        return persona

    async def update(
        self,
        db: AsyncSession,
        persona_id: UUID,
        user_id: UUID,
        **fields,
    ) -> AIPersona:
        """Update a custom persona. Rejects updates to built-in personas.

        Raises ValueError if the persona is builtin or not found.
        """
        persona = await self.get(db, persona_id, user_id)
        if persona is None:
            raise ValueError(f"Persona {persona_id} not found")
        if persona.is_builtin:
            raise ValueError(
                f"Cannot modify built-in persona '{persona.name}'. "
                "Create a custom persona instead."
            )

        allowed_fields = {
            "name", "icon", "system_prompt_template",
            "model_preference", "temperature",
        }
        update_values = {k: v for k, v in fields.items() if k in allowed_fields}
        if not update_values:
            return persona

        await db.execute(
            update(AIPersona)
            .where(AIPersona.id == persona_id)
            .values(**update_values)
        )
        await db.flush()
        await db.refresh(persona)

        logger.info(
            "copilot.persona.updated: persona_id=%s, fields=%s",
            persona_id,
            list(update_values.keys()),
        )
        return persona

    async def delete(
        self,
        db: AsyncSession,
        persona_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a custom persona. Rejects deletion of built-in personas.

        Raises ValueError if the persona is builtin.
        Returns False if the persona was not found.
        """
        persona = await self.get(db, persona_id, user_id)
        if persona is None:
            return False
        if persona.is_builtin:
            raise ValueError(
                f"Cannot delete built-in persona '{persona.name}'. "
                "Built-in personas are permanent."
            )

        # If deleting the active persona, deactivate it
        if persona.is_active:
            await self._activate_default(db, user_id)

        await db.execute(
            delete(AIPersona).where(AIPersona.id == persona_id)
        )
        await db.flush()

        logger.info(
            "copilot.persona.deleted: persona_id=%s, user_id=%s",
            persona_id,
            user_id,
        )
        return True

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    async def get_active(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> AIPersona | None:
        """Return the currently active persona for the user."""
        stmt = select(AIPersona).where(
            AIPersona.user_id == user_id,
            AIPersona.is_active == True,  # noqa: E712
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def set_active(
        self,
        db: AsyncSession,
        user_id: UUID,
        persona_id: UUID,
    ) -> AIPersona:
        """Set a persona as active, deactivating the current one.

        Raises ValueError if the persona is not found.
        """
        persona = await self.get(db, persona_id, user_id)
        if persona is None:
            raise ValueError(f"Persona {persona_id} not found")

        # Deactivate all for this user
        await db.execute(
            update(AIPersona)
            .where(AIPersona.user_id == user_id)
            .values(is_active=False)
        )

        # Activate the specified one
        await db.execute(
            update(AIPersona)
            .where(AIPersona.id == persona_id)
            .values(is_active=True)
        )
        await db.flush()
        await db.refresh(persona)

        logger.info(
            "copilot.persona.activated: user_id=%s, persona_id=%s, name=%s",
            user_id,
            persona_id,
            persona.name,
        )
        return persona

    async def _activate_default(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> None:
        """Activate the General Assistant built-in as default."""
        stmt = select(AIPersona).where(
            AIPersona.user_id == user_id,
            AIPersona.is_builtin == True,  # noqa: E712
            AIPersona.name == "General Assistant",
        )
        result = await db.execute(stmt)
        default = result.scalar_one_or_none()
        if default:
            await db.execute(
                update(AIPersona)
                .where(AIPersona.id == default.id)
                .values(is_active=True)
            )
