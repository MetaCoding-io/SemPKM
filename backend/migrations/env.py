"""Async Alembic environment configuration.

Uses render_as_batch=True for SQLite compatibility (Pitfall 3).
Overrides sqlalchemy.url from app config settings.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.db.base import Base

# Import all models so Alembic can detect them for autogenerate
from app.auth.models import ApiToken, InstanceConfig, Invitation, User, UserSession  # noqa: F401
from app.inference.models import InferenceTripleState  # noqa: F401
<<<<<<< HEAD
<<<<<<< HEAD
# sparql models removed — tables dropped in migration 010 (data moved to RDF)
=======
from app.sparql.models import SavedSparqlQuery, SharedQueryAccess, PromotedQueryView, SparqlQueryHistory  # noqa: F401
>>>>>>> gsd/M003/S05
=======
# sparql models removed — tables dropped in migration 010 (data moved to RDF)
>>>>>>> gsd/M005/S01
from app.favorites.models import UserFavorite  # noqa: F401

# Alembic Config object
config = context.config

# Override sqlalchemy.url from app settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run migrations with a database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (direct database connection)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
