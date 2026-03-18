"""App platform SQLAlchemy models.

Stores app instance lifecycle state, task execution history,
user-adjusted task configuration, renderer preferences, and
approved permissions. These tables are the persistent state
surface for the entire app platform — the AppManager writes
to these models during install/start/stop/crash-recovery, and
the admin portal reads them for monitoring.

Schema source: APP-PLATFORM-DESIGN.md §11.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppInstance(Base):
    """App instance registry — one row per installed app.

    Lifecycle states: installing → stopped ⇄ running → error.
    The ``status`` column is the primary health signal.
    ``restart_count`` increments on crash recovery.
    ``error_message`` captures the last failure reason.
    """

    __tablename__ = "app_instances"

    app_id: Mapped[str] = mapped_column(Text(), primary_key=True)
    version: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(
        Text(), nullable=False, server_default="stopped"
    )
    pid: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    socket_path: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    manifest_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    restart_count: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="0"
    )


class AppTaskRun(Base):
    """Task execution history — one row per task invocation.

    Enables debugging slow or failing tasks via ``status``,
    ``duration_ms``, and ``error_message``.
    """

    __tablename__ = "app_task_runs"

    id: Mapped[int] = mapped_column(
        Integer(), primary_key=True, autoincrement=True
    )
    app_id: Mapped[str] = mapped_column(
        Text(),
        ForeignKey("app_instances.app_id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[str] = mapped_column(Text(), nullable=False)
    run_id: Mapped[str] = mapped_column(Text(), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        Text(), nullable=False, server_default="running"
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    __table_args__ = (
        Index("ix_app_task_runs_app_id_task_id", "app_id", "task_id"),
    )


class AppTaskConfig(Base):
    """User-adjusted task scheduling configuration.

    ``interval_override`` replaces the manifest default interval.
    ``paused`` suppresses task scheduling entirely.
    """

    __tablename__ = "app_task_config"

    app_id: Mapped[str] = mapped_column(
        Text(),
        ForeignKey("app_instances.app_id", ondelete="CASCADE"),
        primary_key=True,
    )
    task_id: Mapped[str] = mapped_column(Text(), primary_key=True)
    interval_override: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    paused: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="0"
    )


class AppRendererPref(Base):
    """Renderer preference overrides — maps (type_iri, mode) to an app.

    ``mode`` is 'read' or 'edit'. Only one app can claim a given
    (type_iri, mode) pair.
    """

    __tablename__ = "app_renderer_prefs"

    type_iri: Mapped[str] = mapped_column(Text(), primary_key=True)
    mode: Mapped[str] = mapped_column(Text(), primary_key=True)
    app_id: Mapped[str] = mapped_column(
        Text(),
        ForeignKey("app_instances.app_id", ondelete="CASCADE"),
        nullable=False,
    )


class AppPermission(Base):
    """Approved permissions snapshot captured at install time.

    Stores the full permissions list as JSON so the platform can
    enforce permission boundaries at runtime without re-reading
    the manifest.
    """

    __tablename__ = "app_permissions"

    app_id: Mapped[str] = mapped_column(
        Text(),
        ForeignKey("app_instances.app_id", ondelete="CASCADE"),
        primary_key=True,
    )
    permissions_json: Mapped[str] = mapped_column(Text(), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    approved_by: Mapped[str] = mapped_column(Text(), nullable=False)
