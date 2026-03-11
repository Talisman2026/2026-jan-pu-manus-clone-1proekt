from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="user", lazy="noload"
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    # description is stored but NEVER logged (PII / sensitive content)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="created", index=True
    )
    budget_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_actual: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # JSONB in PostgreSQL; falls back to JSON in SQLite for tests
    estimation: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sandbox_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="tasks", lazy="noload")
    steps: Mapped[list["TaskStep"]] = relationship(
        "TaskStep",
        back_populates="task",
        lazy="noload",
        order_by="TaskStep.created_at",
    )


class TaskStep(Base):
    __tablename__ = "task_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=False, index=True
    )
    tool: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="done")
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task: Mapped["Task"] = relationship(
        "Task", back_populates="steps", lazy="noload"
    )


# ---------------------------------------------------------------------------
# Valid task status values (used for validation in services)
# ---------------------------------------------------------------------------

TASK_STATUS_CREATED = "created"
TASK_STATUS_ESTIMATING = "estimating"
TASK_STATUS_ESTIMATED = "estimated"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_BUDGET_WARNING = "budget_warning"
TASK_STATUS_PAUSED = "paused"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

TERMINAL_STATUSES: frozenset[str] = frozenset(
    {TASK_STATUS_COMPLETED, TASK_STATUS_FAILED, TASK_STATUS_PAUSED}
)
# budget_warning: agent is still running but will auto-stop at cap — allow cancel
ACTIVE_STATUSES: frozenset[str] = frozenset(
    {TASK_STATUS_ESTIMATING, TASK_STATUS_ESTIMATED, TASK_STATUS_RUNNING, TASK_STATUS_BUDGET_WARNING}
)
