"""Dual-database async engine factory.

Supports both SQLite (local) and PostgreSQL (cloud) via the same interface.
The database URL scheme determines the driver:
  - sqlite+aiosqlite:///./data/sempkm.db (local)
  - postgresql+asyncpg://user:pass@host/dbname (cloud)
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings


def create_engine() -> AsyncEngine:
    """Create an async SQLAlchemy engine from application settings.

    For SQLite, adds check_same_thread=False to connect_args
    since async access requires this for thread safety.
    """
    connect_args: dict = {}
    if settings.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args=connect_args,
    )
